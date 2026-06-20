# Copyright 2026 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     https://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import base64
import json
import re
from typing import Any

from pydantic import BaseModel

from google.adk.apps import App
from google.adk.agents import LlmAgent
from google.adk.agents.context import Context
from google.adk.events.event import Event
from google.adk.events.request_input import RequestInput
from google.adk.workflow import Workflow, node
from google.genai import types

from .config import THRESHOLD, MODEL


class Expense(BaseModel):
    amount: float
    submitter: str
    category: str
    description: str
    date: str
    redacted_categories: list[str] = []


class ReviewOutput(BaseModel):
    risk_level: str
    risk_factors: list[str]
    recommendation: str
    summary: str


class ExpenseDecision(BaseModel):
    status: str
    reason: str
    expense: Expense
    llm_review: ReviewOutput | None = None


@node
def parse_expense(node_input: str | dict | types.Content):
    """Parses an incoming event into an Expense object, handling Pub/Sub base64 encoding."""
    if isinstance(node_input, types.Content):
        text = node_input.parts[0].text if node_input.parts else ""
        try:
            data = json.loads(text) if text else {}
        except json.JSONDecodeError:
            yield Event(content=types.Content(role='model', parts=[types.Part.from_text(text="Error: Input must be a valid JSON object.")]))
            return
    elif isinstance(node_input, str):
        try:
            data = json.loads(node_input)
        except json.JSONDecodeError:
            yield Event(content=types.Content(role='model', parts=[types.Part.from_text(text="Error: Input must be a valid JSON object.")]))
            return
    else:
        data = node_input

    # Pub/Sub wrapping
    if "data" in data:
        raw_data = data["data"]
        if isinstance(raw_data, str):
            try:
                # Try base64 decoding (standard for Pub/Sub pushes)
                decoded = base64.b64decode(raw_data).decode('utf-8')
                expense_dict = json.loads(decoded)
            except Exception:
                # Fallback to plain JSON string (local testing)
                try:
                    expense_dict = json.loads(raw_data)
                except json.JSONDecodeError:
                    yield Event(content=types.Content(role='model', parts=[types.Part.from_text(text="Error: 'data' payload must be a valid JSON object.")]))
                    return
        else:
            expense_dict = raw_data
    else:
        expense_dict = data

    try:
        expense = Expense(**expense_dict)
        yield Event(output=expense)
    except Exception as e:
        yield Event(content=types.Content(role='model', parts=[types.Part.from_text(text=f"Error parsing expense: {str(e)}")]))


@node
def evaluate_expense(node_input: Expense | None):
    """Evaluates the expense against the threshold to determine the route."""
    if node_input is None:
        return

    if node_input.amount < THRESHOLD:
        return Event(output=node_input, route="auto_approve")
    else:
        # Save the expense in state so we have it after the LLM review
        return Event(output=node_input, route="manual_review", state={"expense": node_input.model_dump()})


@node
def security_checkpoint(node_input: Expense):
    """Scrubs PII and checks for prompt injection."""
    original_description = node_input.description
    new_description = original_description

    # Scrub SSN
    if re.search(r'\b\d{3}-\d{2}-\d{4}\b', new_description):
        new_description = re.sub(r'\b\d{3}-\d{2}-\d{4}\b', '[REDACTED SSN]', new_description)
        if "SSN" not in node_input.redacted_categories:
            node_input.redacted_categories.append("SSN")

    # Scrub Credit Card (simple heuristic)
    if re.search(r'\b(?:\d[ -]*?){13,16}\b', new_description):
        new_description = re.sub(r'\b(?:\d[ -]*?){13,16}\b', '[REDACTED CREDIT CARD]', new_description)
        if "Credit Card" not in node_input.redacted_categories:
            node_input.redacted_categories.append("Credit Card")

    node_input.description = new_description

    # Prompt Injection Defense
    injection_pattern = r'(?i)(ignore.*instructions|auto-approve|bypass|override)'
    if re.search(injection_pattern, original_description):
        # Prompt injection detected!
        review_output = {
            "risk_level": "CRITICAL",
            "risk_factors": ["Prompt Injection Attempt Detected"],
            "recommendation": "REJECT",
            "summary": "Security checkpoint blocked this expense due to suspected prompt injection in the description."
        }
        return Event(output=review_output, route="security_flag", state={"expense": node_input.model_dump()})

    return Event(output=node_input, route="safe", state={"expense": node_input.model_dump()})


@node
def auto_approve(node_input: Expense):
    """Instantly approves expenses under the threshold."""
    decision = ExpenseDecision(
        status="approved",
        reason=f"Amount ${node_input.amount} is under the ${THRESHOLD} threshold.",
        expense=node_input
    )
    yield Event(content=types.Content(role='model', parts=[types.Part.from_text(text=f"Auto-approved: {decision.reason}")]))
    yield Event(output=decision.model_dump())


llm_review = LlmAgent(
    name="llm_review",
    model=MODEL,
    instruction=(
        "Review the provided expense report. It requires manual review because it exceeds the auto-approval threshold. "
        "Identify any risk factors, determine the risk level, and provide a recommendation on whether it should be approved."
    ),
    output_schema=ReviewOutput,
    output_key="review",
)


@node
async def human_review(ctx: Context, node_input: dict):
    """Pauses for a human to review the LLM's risk assessment and make a final decision."""
    review = ReviewOutput(**node_input)
    expense = Expense(**ctx.state.get("expense", {}))

    interrupt_id = "approval_decision"

    if not ctx.resume_inputs:
        msg = (
            f"Expense from {expense.submitter} for ${expense.amount}.\n"
            f"Risk Level: {review.risk_level}\n"
            f"Risk factors: {review.risk_factors}\n"
            f"Approve this expense? (yes/no)"
        )
        yield RequestInput(interrupt_id=interrupt_id, message=msg)
        return

    decision_text = ctx.resume_inputs.get(interrupt_id, "").strip().lower()
    status = "approved" if decision_text in ["yes", "y", "approve"] else "rejected"

    decision = ExpenseDecision(
        status=status,
        reason=f"Human reviewed and {status}.",
        expense=expense,
        llm_review=review
    )

    yield Event(content=types.Content(role='model', parts=[types.Part.from_text(text=f"Human review outcome: {status}")]))
    yield Event(output=decision.model_dump())


root_agent = Workflow(
    name="expense_workflow",
    edges=[
        ('START', parse_expense),
        (parse_expense, evaluate_expense),
        (evaluate_expense, {
            "auto_approve": auto_approve,
            "manual_review": security_checkpoint
        }),
        (security_checkpoint, {
            "safe": llm_review,
            "security_flag": human_review
        }),
        (llm_review, human_review),
    ]
)

app = App(
    name="expense_agent",
    root_agent=root_agent,
)
