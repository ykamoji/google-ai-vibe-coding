# ruff: noqa
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

import datetime
from zoneinfo import ZoneInfo

from pydantic import BaseModel, Field

from google.adk.agents import Agent
from google.adk.apps import App
from google.adk.models import Gemini
from google.genai import types

import os
import google.auth

_, project_id = google.auth.default()
os.environ["GOOGLE_CLOUD_PROJECT"] = project_id
os.environ["GOOGLE_CLOUD_LOCATION"] = "global"
os.environ["GOOGLE_GENAI_USE_VERTEXAI"] = "True"

REDEEMED_CODES: dict[str, set[str]] = {"WELCOME50": set(), "SUMMER20": set()}

USER_POINTS: dict[str, float] = {}
PROCESSED_PURCHASES: set[str] = set()


class AwardLoyaltyPointsInput(BaseModel):
    user_id: str = Field(..., description="The ID of the user receiving the points.")
    purchase_amount: float = Field(
        ..., description="The total amount of the successful purchase."
    )
    purchase_id: str = Field(
        ...,
        description="A unique identifier for the purchase to prevent duplicate awards.",
    )


def award_loyalty_points(request: AwardLoyaltyPointsInput) -> str:
    """Awards loyalty points to a user based on their purchase amount.

    Args:
        request: The AwardLoyaltyPointsInput containing user_id, purchase_amount, and purchase_id.

    Returns:
        A success message with the points awarded and total balance, or an error if invalid/already processed.
    """
    if request.purchase_amount <= 0:
        return "Error: Purchase amount must be greater than zero."

    if request.purchase_id in PROCESSED_PURCHASES:
        return f"Error: Loyalty points for purchase {request.purchase_id} have already been awarded."

    points_earned = request.purchase_amount * 0.10

    current_points = USER_POINTS.get(request.user_id, 0.0)
    USER_POINTS[request.user_id] = current_points + points_earned
    PROCESSED_PURCHASES.add(request.purchase_id)

    return f"Success: Awarded {points_earned} points to user {request.user_id}. Total points: {USER_POINTS[request.user_id]}."


def redeem_discount_code(code: str, user_id: str) -> str:
    """Redeems a single-use discount code for a user.

    Args:
        code: The discount code to redeem (e.g. WELCOME50, SUMMER20).
        user_id: The ID of the registered user redeeming the code.

    Returns:
        A success message or an error if the code is invalid or already redeemed.
    """
    code = code.upper()
    if code not in REDEEMED_CODES:
        return f"Error: Discount code {code} is invalid."

    if user_id in REDEEMED_CODES[code]:
        return f"Error: User {user_id} has already redeemed discount code {code}."

    REDEEMED_CODES[code].add(user_id)
    return f"Success: Discount code {code} redeemed for user {user_id}."


root_agent = Agent(
    name="root_agent",
    model=Gemini(
        model="gemini-flash-latest",
        retry_options=types.HttpRetryOptions(attempts=3),
    ),
    instruction="You are an AI shopping assistant for a retail store. You help users with their shopping experience, can redeem discount codes, and award loyalty points for purchases.",
    tools=[redeem_discount_code, award_loyalty_points],
)

app = App(
    root_agent=root_agent,
    name="app",
)
