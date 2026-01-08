from __future__ import annotations

from dotenv import load_dotenv

load_dotenv()

import json
from pathlib import Path

from pydantic_ai import DeferredToolResults, ModelMessage, ModelMessagesTypeAdapter

from pai_agent_sdk.agents.main import create_agent, stream_agent
from pai_agent_sdk.context import ModelCapability, ModelConfig, ResumableState
from pai_agent_sdk.toolsets.core.base import UserInteraction

# Session file paths
SESSION_DIR = Path(__file__).parent / ".session"
MESSAGE_HISTORY_FILE = SESSION_DIR / "message_history.json"
STATE_FILE = SESSION_DIR / "context_state.json"


def ensure_session_dir() -> None:
    """Ensure session directory exists."""
    SESSION_DIR.mkdir(parents=True, exist_ok=True)


def load_message_history() -> list[ModelMessage] | None:
    """Load message history from JSON file."""
    if not MESSAGE_HISTORY_FILE.exists():
        return None
    try:
        with open(MESSAGE_HISTORY_FILE) as f:
            data = json.load(f)
        return ModelMessagesTypeAdapter.validate_python(data)
    except (json.JSONDecodeError, ValueError) as e:
        print(f"Warning: Failed to load message history: {e}")
        return None


def save_message_history(messages_json: bytes) -> None:
    """Save message history to JSON file."""
    ensure_session_dir()
    with open(MESSAGE_HISTORY_FILE, "wb") as f:
        f.write(messages_json)
    print(f"Message history saved to {MESSAGE_HISTORY_FILE}")


def load_state() -> ResumableState | None:
    """Load context state from JSON file."""
    if not STATE_FILE.exists():
        return None
    try:
        with open(STATE_FILE) as f:
            return ResumableState.model_validate_json(f.read())
    except (json.JSONDecodeError, ValueError) as e:
        print(f"Warning: Failed to load context state: {e}")
        return None


def save_state(state: ResumableState) -> None:
    """Save context state to JSON file."""
    ensure_session_dir()
    with open(STATE_FILE, "w") as f:
        f.write(state.model_dump_json(indent=2))
    print(f"Context state saved to {STATE_FILE}")


def get_user_interaction() -> list[UserInteraction] | None:
    """Get pending user interactions (not implemented in this example)."""
    return None


def get_user_prompt() -> str:
    """Get user input from console."""
    try:
        return input("You: ").strip()
    except (EOFError, KeyboardInterrupt):
        return ""


async def main():
    # Load previous session state
    message_history: list[ModelMessage] | None = load_message_history()
    state: ResumableState | None = load_state()

    if message_history:
        print(f"Loaded {len(message_history)} messages from history")
    if state:
        print("Loaded previous context state")

    # Get user input
    user_prompt = get_user_prompt()
    if not user_prompt:
        print("No input provided, exiting.")
        return

    user_interaction: list[UserInteraction] | None = get_user_interaction()
    _deferred_tool_results: DeferredToolResults | None

    async with create_agent(
        model="openai:gpt-5.2",
        model_cfg=ModelConfig(context_window=200_000, capabilities={ModelCapability.vision}),
        state=state,
    ) as agent_runtime:
        agent = agent_runtime.agent
        if message_history and user_interaction and agent_runtime.core_toolset:
            _deferred_tool_results = await agent_runtime.core_toolset.process_hitl_call(
                user_interaction, message_history
            )
        else:
            _deferred_tool_results = None

        async with stream_agent(
            agent,
            user_prompt=user_prompt,
            ctx=agent_runtime.ctx,
            message_history=message_history,
            deferred_tool_results=_deferred_tool_results,
        ) as stream:
            async for event in stream:
                print(event)
            # Check for exceptions that occurred during streaming
            stream.raise_if_exception()
            run = stream.run

        if run:
            print(f"\nUsage: {run.usage()}")
            print(f"Messages so far: {len(run.all_messages())}")
            save_message_history(run.all_messages_json())
            new_state = agent_runtime.ctx.export_state()
            save_state(new_state)


if __name__ == "__main__":
    import asyncio

    asyncio.run(main())
