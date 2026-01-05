from collections.abc import Generator
from contextlib import contextmanager
from datetime import datetime, timedelta
from typing import TYPE_CHECKING, Any
from uuid import uuid4

from pydantic import BaseModel, Field

if TYPE_CHECKING:
    from typing import Self


def _generate_run_id() -> str:
    return uuid4().hex


class AgentContext(BaseModel):
    run_id: str = Field(default_factory=_generate_run_id)
    parent_run_id: str | None = None
    start_at: datetime | None = None
    end_at: datetime | None = None

    deferred_tool_metadata: dict[str, dict[str, Any]] = Field(default_factory=dict)
    """Metadata for deferred tool calls, keyed by tool_call_id."""

    _agent_name: str = "main"

    @property
    def elapsed_time(self) -> timedelta | None:
        """Return elapsed time since start, or None if not started.

        If session has ended, returns the final duration.
        If session is running, returns the current elapsed time.
        """
        if self.start_at is None:
            return None
        end = self.end_at if self.end_at else datetime.now()
        return end - self.start_at

    @contextmanager
    def enter_subagent(
        self,
        agent_name: str,
        **override: Any,
    ) -> Generator["Self", None, None]:
        """Create a child context for subagent with independent timing.

        The subagent context inherits all fields but gets:
        - A new run_id
        - parent_run_id set to current run_id
        - Fresh start_at/end_at for independent timing

        Args:
            agent_name: Name of the subagent.
            **override: Additional fields to override in the subagent context.
                Subclasses can pass extra fields without overriding this method.
        """
        update: dict[str, Any] = {
            "run_id": _generate_run_id(),
            "parent_run_id": self.run_id,
            "start_at": datetime.now(),
            "end_at": None,
            **override,
        }
        new_ctx = self.model_copy(update=update)
        new_ctx._agent_name = agent_name
        try:
            yield new_ctx
        finally:
            new_ctx.end_at = datetime.now()

    async def __aenter__(self):
        self.start_at = datetime.now()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        self.end_at = datetime.now()
