from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import Awaitable, Callable
from pathlib import Path

# Type definition for the sandbox execute function
SandboxExecuteFunc = Callable[[list[str], int | None], Awaitable[tuple[int, bytes, bytes]]]


class SandboxError(Exception):
    """Base exception for sandbox-related errors."""

    pass


class SandboxTimeoutError(SandboxError):
    """Exception raised when a sandbox operation times out."""

    pass


class SandboxStartTimeoutError(SandboxTimeoutError):
    """Exception raised when starting a sandbox times out."""

    pass


class SandboxExecuteTimeoutError(SandboxTimeoutError):
    """Exception raised when a command execution in the sandbox fails."""

    pass


class Sandbox(ABC):
    @abstractmethod
    async def start(
        self,
        working_dir: str | Path,
        environment: dict[str, str] | None = None,
        timeout: float | None = None,
        expire_seconds: int = 300,
    ) -> str:
        """Start the sandbox environment.

        Returns:
            Container ID or session identifier
        """

    @abstractmethod
    async def stop(self, container_id: str) -> None:
        """Stop the sandbox environment.

        Args:
            container_id: The container ID returned by start()
        """

    @abstractmethod
    async def execute(
        self, container_id: str, command: list[str], timeout: int | None = None
    ) -> tuple[int, bytes, bytes]:
        """Execute a command in the sandbox environment.

        Args:
            container_id: The container ID returned by start()
            command: Command to execute
            timeout: Execution timeout

        Returns:
            A tuple of (return_code, stdout, stderr)
        """

    def get_executor(self, container_id: str) -> SandboxExecuteFunc:
        """Return a callable that executes commands in this sandbox.

        Args:
            container_id: The container ID returned by start()

        Returns:
            A callable that takes command and timeout parameters
        """

        async def executor(command: list[str], timeout: int | None = None) -> tuple[int, bytes, bytes]:
            """Execute a command in the sandbox.

            Args:
                command: Command to execute as a list of strings
                timeout: Execution timeout in seconds

            Returns:
                Tuple of (return_code, stdout, stderr)
            """
            return await self.execute(container_id, command, timeout)

        return executor
