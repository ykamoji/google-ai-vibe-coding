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
import logging
import os
from dotenv import load_dotenv

AGENT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
# Load the environment variables before initializing ADK agents
load_dotenv(os.path.join(AGENT_DIR, ".env"))

from fastapi import FastAPI, Request
from google.adk.cli.fast_api import get_fast_api_app
from google.adk.runners import Runner
from google.adk.cli.utils.service_factory import create_session_service_from_options
from google.genai import types

from expense_agent.agent import root_agent
from expense_agent.app_utils.typing import Feedback

# Use standard Python logging for console logs
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

allow_origins = (
    os.getenv("ALLOW_ORIGINS", "").split(",") if os.getenv("ALLOW_ORIGINS") else ["*"]
)


# Create the FastAPI app with ADK utilities
app: FastAPI = get_fast_api_app(
    agents_dir=AGENT_DIR,
    web=True,
    artifact_service_uri=None,
    allow_origins=allow_origins,
    session_service_uri=None,
    otel_to_cloud=False,  # Disable cloud telemetry for local testing
)
app.title = "ambient-expense-agent"
app.description = "API for interacting with the ambient expense agent"


@app.post("/")
async def pubsub_handler(request: Request):
    """Accepts Pub/Sub trigger messages and feeds them into the workflow."""
    envelope = await request.json()

    if not envelope or "message" not in envelope:
        logger.error("Invalid Pub/Sub payload received.")
        return {"error": "Bad Request: invalid Pub/Sub message format"}

    # Extract the fully-qualified subscription path and normalize to short name
    subscription_path = envelope.get("subscription", "")
    session_id = subscription_path.split("/")[-1] if subscription_path else "default_session"

    message = envelope["message"]

    logger.info(f"Processing Pub/Sub message for session: {session_id}")

    # We pass the envelope's message dictionary as a JSON string to the workflow.
    # The parse_expense node is already equipped to handle {"data": base64_payload}
    # Construct the explicit SQLite URI for the expense_agent app
    db_path = os.path.join(AGENT_DIR, "expense_agent", ".adk", "session.db")
    session_service = create_session_service_from_options(
        base_dir=AGENT_DIR,
        session_service_uri=f"sqlite:///{db_path}",
        use_local_storage=True,
    )
    runner = Runner(agent=root_agent, session_service=session_service, app_name="expense_agent")

    import json
    content_message = types.Content(
        role="user",
        parts=[types.Part.from_text(text=json.dumps(message))]
    )

    try:
        session = await session_service.get_session(
            app_name="expense_agent",
            user_id="user",
            session_id=session_id
        )
        if session is None:
            await session_service.create_session(
                session_id=session_id,
                user_id="user",
                app_name="expense_agent"
            )
    except Exception as e:
        if "NotFound" in str(type(e)):
            await session_service.create_session(
                session_id=session_id,
                user_id="user",
                app_name="expense_agent"
            )
        else:
            raise

    events = runner.run_async(
        new_message=content_message,
        user_id="user",
        session_id=session_id
    )

    # Drive the generator to pull all events through the workflow
    async for event in events:
        logger.info(f"Event output: {event}")

    return {"status": "success"}


@app.post("/feedback")
def collect_feedback(feedback: Feedback) -> dict[str, str]:
    """Collect and log feedback."""
    logger.info(f"Feedback received: {feedback.model_dump()}")
    return {"status": "success"}


if __name__ == "__main__":
    import uvicorn
    # Stand it up on port 8080 as requested
    uvicorn.run(app, host="0.0.0.0", port=8080)
