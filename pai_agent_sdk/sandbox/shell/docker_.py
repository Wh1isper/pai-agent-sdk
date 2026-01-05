from __future__ import annotations

import asyncio
import time
from pathlib import Path

try:
    import docker
    import docker.errors
except ImportError as e:
    raise ImportError(
        "The 'docker' package is required for DockerSandbox. Install it with: pip install pai-agent-sdk[docker]"
    ) from e

from pai_agent_sdk.sandbox.shell.base import (
    Sandbox,
    SandboxError,
    SandboxExecuteTimeoutError,
    SandboxStartTimeoutError,
)
from pai_agent_sdk.utils import run_in_threadpool

_HERE = Path(__file__).parent
DEFAULT_TEMPLATE_DIR = _HERE / "templates"
DEFAULT_DOCKERFILE = DEFAULT_TEMPLATE_DIR / "Dockerfile"
DEFAULT_IMAGE_NAME = "pai-sandbox:latest"


class DockerSandbox(Sandbox):
    """Docker-based sandbox for executing commands in isolated containers.

    This class provides a flexible Docker sandbox that can be customized with
    different Dockerfiles and image names for various use cases.

    Example:
        # Use default configuration
        sandbox = DockerSandbox()

        # Use custom image name (skip build, use existing image)
        sandbox = DockerSandbox(image_name="my-custom-image:v1", auto_build=False)

        # Use custom Dockerfile
        sandbox = DockerSandbox(dockerfile=Path("/path/to/Dockerfile"))

        # Full customization
        sandbox = DockerSandbox(
            image_name="my-sandbox:latest",
            dockerfile=Path("/path/to/Dockerfile"),
            build_context=Path("/path/to/context"),
            auto_build=True,
        )
    """

    def __init__(
        self,
        image_name: str | None = None,
        dockerfile: str | Path | None = None,
        build_context: str | Path | None = None,
        auto_build: bool = True,
    ) -> None:
        """Initialize Docker sandbox.

        Args:
            image_name: Docker image name to use. Defaults to 'pai-sandbox:latest'.
            dockerfile: Path to Dockerfile. If not provided, uses built-in default.
            build_context: Path to build context directory. If not provided,
                uses the directory containing the Dockerfile.
            auto_build: Whether to automatically build the image on start().
                Set to False if using a pre-built image.
        """
        # Docker client lazy loading to avoid connection issues during import
        self._client: docker.DockerClient | None = None

        self._image_name = image_name or DEFAULT_IMAGE_NAME
        self._auto_build = auto_build

        # Configure Dockerfile path
        if dockerfile is not None:
            self._dockerfile = Path(dockerfile)
        else:
            self._dockerfile = DEFAULT_DOCKERFILE

        # Configure build context
        if build_context is not None:
            self._build_context = Path(build_context)
        else:
            self._build_context = self._dockerfile.parent

    @property
    def image_name(self) -> str:
        """Get the Docker image name."""
        return self._image_name

    @property
    def dockerfile(self) -> Path:
        """Get the Dockerfile path."""
        return self._dockerfile

    @property
    def build_context(self) -> Path:
        """Get the build context directory."""
        return self._build_context

    @property
    def client(self) -> docker.DockerClient:
        """Get Docker client with lazy initialization."""
        if self._client is None:
            self._client = docker.from_env()
        return self._client

    def build(self, force: bool = False) -> None:
        """
        Build Docker sandbox image using docker library.

        Args:
            force: Force rebuild even if image exists.

        Raises:
            RuntimeError: If build fails
            FileNotFoundError: If Dockerfile not found
        """
        # Check if image already exists (skip build unless forced)
        if not force:
            try:
                self.client.images.get(self._image_name)
                return  # Image exists, skip build
            except docker.errors.ImageNotFound:
                pass  # Image doesn't exist, proceed with build

        # Verify Dockerfile exists
        if not self._dockerfile.exists():
            raise FileNotFoundError(f"Dockerfile not found: {self._dockerfile}")
        try:
            # Build image using docker library
            self.client.images.build(
                path=str(self._build_context),
                dockerfile=str(self._dockerfile),
                tag=self._image_name,
                rm=True,  # Remove intermediate containers
                forcerm=True,  # Always remove intermediate containers
                quiet=False,
            )

        except docker.errors.BuildError as e:
            error_msg = f"Build failed: {e}"
            raise RuntimeError(error_msg) from e
        except docker.errors.APIError as e:
            error_msg = f"Docker API error during build: {e}"
            raise RuntimeError(error_msg) from e

    async def start(
        self,
        working_dir: str | Path,
        environment: dict[str, str] | None = None,
        timeout: float | None = None,
        expire_seconds: int = 300,
    ) -> str:
        """Start the sandbox environment.

        Returns:
            Container ID
        """
        # Build image if auto_build is enabled
        if self._auto_build:
            await run_in_threadpool(self.build)

        # Prepare container environment
        container_env = {
            "EXPIRE_SECONDS": str(expire_seconds),
            "SHELL": "/bin/bash",
        }
        if environment:
            container_env.update(environment)

        # Start container with volume mount and auto cleanup
        container_id = await self._start_container(working_dir=working_dir, environment=container_env)

        # Wait for container to be ready
        await self._wait_for_ready(container_id, timeout=timeout or 30)

        return container_id

    async def stop(self, container_id: str) -> None:
        """Stop the sandbox environment.

        Args:
            container_id: The container ID returned by start()
        """

        def _stop_container() -> None:
            try:
                container = self.client.containers.get(container_id)
                container.stop(timeout=10)
            except docker.errors.NotFound as e:
                raise SandboxError(f"Container not found: {container_id}") from e
            except docker.errors.APIError as e:
                raise SandboxError(f"Failed to stop container: {e}") from e

        await run_in_threadpool(_stop_container)

    async def execute(
        self, container_id: str, command: list[str], timeout: int | None = None
    ) -> tuple[int, bytes, bytes]:
        """
        Execute a command in the sandbox environment using bash.

        Args:
            container_id: The container ID returned by start()
            command: Command to execute
            timeout: Execution timeout

        Returns:
            A tuple of (return_code, stdout, stderr)
        """

        def _exec_command() -> tuple[int, bytes, bytes]:
            try:
                container = self.client.containers.get(container_id)
                result = container.exec_run(cmd=command, stdout=True, stderr=True, demux=True)

                exit_code: int = result.exit_code
                stdout_stderr = result.output

                stdout_bytes: bytes
                stderr_bytes: bytes

                # docker-py might return (stdout, stderr) or just combined output
                if isinstance(stdout_stderr, tuple) and len(stdout_stderr) == 2:
                    out, err = stdout_stderr
                    stdout_bytes = out if out is not None else b""
                    stderr_bytes = err if err is not None else b""
                else:
                    stdout_bytes = bytes(stdout_stderr) if stdout_stderr is not None else b""
                    stderr_bytes = b""

                return (exit_code, stdout_bytes, stderr_bytes)

            except docker.errors.NotFound:
                return (1, b"", b"Container not found")
            except docker.errors.APIError as e:
                return (1, b"", str(e).encode())

        try:
            if timeout and timeout > 0:
                return await asyncio.wait_for(run_in_threadpool(_exec_command), timeout=timeout)
            else:
                return await run_in_threadpool(_exec_command)
        except TimeoutError as e:
            raise SandboxExecuteTimeoutError(f"Command timeout: {timeout}s") from e
        except Exception as e:
            raise SandboxError("Command execution failed") from e

    async def _start_container(
        self,
        working_dir: str | Path,
        environment: dict[str, str],
    ) -> str:
        """Start container and return container ID."""
        host_path = Path(working_dir).resolve()

        if not host_path.exists():
            raise SandboxError(f"Working directory does not exist: {host_path}")

        def _run_container() -> str:
            try:
                container = self.client.containers.run(
                    image=self._image_name,
                    volumes={str(host_path): {"bind": "/workspace", "mode": "rw"}},
                    working_dir="/workspace",
                    environment=environment,
                    detach=True,
                    auto_remove=True,
                    stdin_open=True,
                    tty=True,
                )
                container_id: str = container.id  # type: ignore[assignment]
                return container_id
            except docker.errors.ImageNotFound as e:
                raise SandboxError(f"Docker image not found: {self._image_name}") from e
            except docker.errors.APIError as e:
                raise SandboxError(f"Failed to start container: {e}") from e

        return await run_in_threadpool(_run_container)

    async def _wait_for_ready(self, container_id: str, timeout: float) -> None:
        """Wait for container to be ready with proper timeout and retry."""
        start_time = time.time()

        while time.time() - start_time < timeout:
            try:

                def _check_status() -> str:
                    container = self.client.containers.get(container_id)
                    container.reload()
                    return container.status

                status = await run_in_threadpool(_check_status)

                if status == "running":
                    return
                elif status in ["exited", "dead"]:
                    raise SandboxError(f"Container failed to start (status: {status})")

                await asyncio.sleep(0.5)

            except docker.errors.NotFound as e:
                if time.time() - start_time >= timeout:
                    raise SandboxStartTimeoutError(f"Container failed to start within {timeout}s") from e
                await asyncio.sleep(0.5)
            except docker.errors.APIError as e:
                if time.time() - start_time >= timeout:
                    raise SandboxStartTimeoutError(f"Container failed to start within {timeout}s") from e
                await asyncio.sleep(0.5)

        raise SandboxStartTimeoutError(f"Container failed to become ready within {timeout}s")
