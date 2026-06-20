import json
import os
import uuid

from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
from google.genai import types

from expense_agent.agent import root_agent

DATASET_PATH = "tests/eval/datasets/basic-dataset.json"
OUTPUT_PATH = "artifacts/traces/generated_traces.json"

def main():
    from dotenv import load_dotenv
    load_dotenv()

    os.makedirs(os.path.dirname(OUTPUT_PATH), exist_ok=True)

    with open(DATASET_PATH, "r") as f:
        dataset = json.load(f)

    session_service = InMemorySessionService()

    graded_dataset = {"eval_cases": []}

    for case in dataset.get("eval_cases", []):
        case_id = case["eval_case_id"]
        print(f"Generating trace for case: {case_id}")

        # New session for each eval case
        session_id = str(uuid.uuid4())
        session = session_service.create_session_sync(
            session_id=session_id, user_id="eval_user", app_name="ambient-expense-agent"
        )

        runner = Runner(agent=root_agent, session_service=session_service, app_name="ambient-expense-agent")

        events_collected = []

        # Prepare initial message
        prompt_content = types.Content(
            role=case["prompt"]["role"],
            parts=[types.Part.from_text(text=case["prompt"]["parts"][0]["text"])]
        )

        print("  Running initial prompt...")
        for event in runner.run(new_message=prompt_content, user_id="eval_user", session_id=session_id):
            events_collected.append(event)

        last_event = events_collected[-1] if events_collected else None

        # Check if the workflow paused for a RequestInput (human review)
        interrupted = False
        if last_event and last_event.content and last_event.content.parts:
            for part in last_event.content.parts:
                if part.function_call and part.function_call.name == "adk_request_input":
                    interrupted = True
                    args = part.function_call.args
                    message_str = args.get("message", "")

                    # Automate the decision based on the message content
                    is_critical = "CRITICAL" in message_str
                    decision = "no" if is_critical else "yes"
                    print(f"  Intercepted human review. Decision: {decision}")

                    resume_content = types.Content(
                        role="user",
                        parts=[types.Part.from_function_response(
                            name="adk_request_input",
                            response={"id": args.get("interruptId", "approval_decision"), "response": decision}
                        )]
                    )

                    print("  Resuming runner with decision...")
                    for event in runner.run(new_message=resume_content, user_id="eval_user", session_id=session_id):
                        events_collected.append(event)
                    break

        # Now, construct the AgentData trace format
        turns = []
        current_turn_events = []

        # We fetch the events directly from the session object to get the full ordered trace
        # The session.get_events() returns raw Event objects
        try:
            # We can use the events we collected since they are the emitted events.
            # Convert them to the standard format
            for event in events_collected:
                if event.content:
                    # author is event.author
                    current_turn_events.append({
                        "author": event.author,
                        "content": event.content.model_dump(mode="json", exclude_none=True)
                    })

            if current_turn_events:
                turns.append({
                    "turn_index": 0,
                    "events": current_turn_events
                })
        except Exception as e:
            print(f"Error formatting trace: {e}")

        graded_case = {
            "eval_case_id": case_id,
            "agent_data": {
                "agents": {
                    "expense_workflow": {
                        "agent_id": "expense_workflow"
                    }
                },
                "turns": turns
            }
        }
        graded_dataset["eval_cases"].append(graded_case)
        print("  Trace generation complete.")

    with open(OUTPUT_PATH, "w") as f:
        json.dump(graded_dataset, f, indent=2)
    print(f"\\nWrote traces to {OUTPUT_PATH}")

if __name__ == "__main__":
    main()
