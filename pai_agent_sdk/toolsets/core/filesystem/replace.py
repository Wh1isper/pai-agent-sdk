"""Replace tool for overwriting file contents."""

from functools import cache
from pathlib import Path
from typing import Annotated

from pydantic import Field
from pydantic_ai import RunContext

from pai_agent_sdk.context import AgentContext
from pai_agent_sdk.toolsets.core.base import BaseTool

_PROMPTS_DIR = Path(__file__).parent / "prompts"


@cache
def _load_instruction() -> str:
    """Load replace instruction from prompts/replace.md."""
    prompt_file = _PROMPTS_DIR / "replace.md"
    return prompt_file.read_text()


class ReplaceTool(BaseTool):
    """Tool for replacing entire file contents."""

    name = "replace"
    description = "Write or overwrite entire file content. For partial edits, use `edit` tool instead."

    def get_instruction(self, ctx: RunContext[AgentContext]) -> str | None:
        """Load instruction from prompts/replace.md."""
        return _load_instruction()

    async def call(
        self,
        ctx: RunContext[AgentContext],
        file_path: Annotated[str, Field(description="Relative path to the file to write")],
        content: Annotated[str, Field(description="Content to write to the file")],
        mode: Annotated[
            str,
            Field(
                description="'w' for write/overwrite (default), 'a' for append",
                default="w",
            ),
        ] = "w",
    ) -> str:
        """Write content to a file in the local filesystem."""
        file_operator = ctx.deps.file_operator

        if mode not in ("w", "a"):
            return f"Error: Invalid mode '{mode}'. Only 'w' and 'a' are supported."

        if mode == "w":
            await file_operator.write_file(file_path, content)
        else:
            await file_operator.append_file(file_path, content)

        return f"Successfully wrote to file: {file_path}"


__all__ = ["ReplaceTool"]
