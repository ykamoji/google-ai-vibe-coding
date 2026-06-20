# ruff: noqa
import os
import google.auth
from pydantic import BaseModel
from google.genai import types

from google.adk.workflow import Workflow, node
from google.adk.events.event import Event
from google.adk.agents import LlmAgent
from google.adk.apps import App

try:
    _, project_id = google.auth.default()
    os.environ["GOOGLE_CLOUD_PROJECT"] = project_id
except Exception:
    pass
os.environ.setdefault("GOOGLE_CLOUD_LOCATION", "global")
os.environ.setdefault("GOOGLE_GENAI_USE_VERTEXAI", "False")


class ClassificationOutput(BaseModel):
    category: str
    reason: str


classifier_agent = LlmAgent(
    name="classifier_agent",
    model="gemini-3.1-flash-lite",
    instruction="""You are a customer support triage agent for a shipping company.
    Classify the user's query into one of two categories: 'shipping' or 'unrelated'.
    'shipping' includes questions about rates, tracking, delivery, returns, and shipping times.
    'unrelated' includes anything else.
    """,
    output_schema=ClassificationOutput,
)


from google.adk.events.event_actions import EventActions


@node
def routing_node(node_input: dict) -> Event:
    category = node_input.get("category", "unrelated")
    if category.lower() == "shipping":
        return Event(output=node_input, actions=EventActions(route="shipping"))
    return Event(output=node_input, actions=EventActions(route="unrelated"))


shipping_faq_agent = LlmAgent(
    name="shipping_faq_agent",
    model="gemini-3.1-flash-lite",
    instruction="""You are a shipping customer support representative.
    Answer questions about shipping rates, tracking, delivery, and returns politely.
    Make your responses about shipping rates extremely playful and enthusiastic! 🤩
    Be sure to use fun emojis, and always highlight our amazing FREE SHIPPING threshold on orders over $50! 📦✨
    If you do not know the exact answer, explain the general policy.
    """,
)


@node
def decline_handler(node_input: dict) -> Event:
    message = "I apologize, but I am a shipping customer support agent and cannot assist with unrelated queries."
    return Event(
        content=types.Content(role="model", parts=[types.Part.from_text(text=message)]),
        output=message,
    )


from google.adk.workflow import Edge, START

root_agent = Workflow(
    name="customer_support_workflow",
    edges=[
        Edge(from_node=START, to_node=classifier_agent),
        Edge(from_node=classifier_agent, to_node=routing_node),
        Edge(from_node=routing_node, to_node=shipping_faq_agent, route="shipping"),
        Edge(from_node=routing_node, to_node=decline_handler, route="unrelated"),
    ],
    description="Customer support workflow that routes queries to appropriate agents.",
)

app = App(
    root_agent=root_agent,
    name="app",
)
