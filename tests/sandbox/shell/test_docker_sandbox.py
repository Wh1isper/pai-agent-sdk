"""
Tests for DockerSandbox implementation.

This module tests the core functionality of DockerSandbox including
the improved _wait_for_ready method, file mounting, and stateless behavior.
"""

from pathlib import Path

import pytest

from pai_agent_sdk.sandbox.shell import SandboxError, SandboxStartTimeoutError
from pai_agent_sdk.sandbox.shell.docker_ import DockerSandbox


@pytest.fixture
def sandbox() -> DockerSandbox:
    """Create DockerSandbox instance."""
    return DockerSandbox()


def create_test_file(work_dir: Path, filename: str, content: str) -> Path:
    """Create a test file in the working directory."""
    file_path = work_dir / filename
    file_path.write_text(content)
    return file_path


async def test_docker_sandbox_basic_workflow(sandbox: DockerSandbox, tmp_path: Path) -> None:
    """Test basic start -> execute -> stop workflow with tmp files."""
    # Create test files in temporary directory
    create_test_file(tmp_path, "test.txt", "Hello from host!")
    script_file = create_test_file(tmp_path, "script.sh", "#!/bin/bash\necho 'Script executed'")
    script_file.chmod(0o755)

    container_id = None
    try:
        # Start container with temporary directory mounted
        container_id = await sandbox.start(
            working_dir=tmp_path, environment={"TEST_VAR": "test_value"}, timeout=15, expire_seconds=120
        )

        # Verify container ID is returned
        assert isinstance(container_id, str)
        assert len(container_id) > 0

        # Test file reading from mounted directory
        return_code, stdout, stderr = await sandbox.execute(container_id, ["cat", "test.txt"], timeout=10)
        assert return_code == 0
        assert stdout.decode().strip() == "Hello from host!"

        # Test environment variable
        return_code, stdout, stderr = await sandbox.execute(
            container_id, ["/bin/bash", "-c", "echo $TEST_VAR"], timeout=10
        )
        assert return_code == 0
        assert stdout.decode().strip() == "test_value"

        # Test working directory
        return_code, stdout, _stderr = await sandbox.execute(container_id, ["pwd"], timeout=10)
        assert return_code == 0
        assert stdout.decode().strip() == "/workspace"

    finally:
        if container_id:
            await sandbox.stop(container_id)


async def test_wait_for_ready_improved(sandbox: DockerSandbox, tmp_path: Path) -> None:
    """Test improved _wait_for_ready method behavior."""
    create_test_file(tmp_path, "ready_test.txt", "Ready test content")

    # Test: Normal startup with sufficient timeout
    container_id = None
    try:
        container_id = await sandbox.start(
            working_dir=tmp_path,
            environment={"READY_TEST": "1"},
            timeout=15,  # Sufficient timeout
            expire_seconds=60,
        )

        # Verify container is actually ready by executing a command
        return_code, stdout, _stderr = await sandbox.execute(container_id, ["echo", "Container ready"], timeout=5)
        assert return_code == 0
        assert "Container ready" in stdout.decode()

        # Test _wait_for_ready directly with non-existent container (should timeout)
        with pytest.raises(SandboxStartTimeoutError):
            await sandbox._wait_for_ready("nonexistent_container_id", timeout=1)

    finally:
        if container_id:
            await sandbox.stop(container_id)


async def test_volume_mounting(sandbox: DockerSandbox, tmp_path: Path) -> None:
    """Test file mounting between host and container."""
    # Create host file
    create_test_file(tmp_path, "host_file.txt", "Content from host")

    container_id = None
    try:
        container_id = await sandbox.start(working_dir=tmp_path, timeout=15, expire_seconds=60)

        # Test 1: Host file -> Container read
        return_code, stdout, stderr = await sandbox.execute(container_id, ["cat", "host_file.txt"], timeout=10)
        assert return_code == 0
        assert stdout.decode().strip() == "Content from host"

        # Test 2: Container create file -> Host visible
        return_code, stdout, stderr = await sandbox.execute(
            container_id, ["sh", "-c", "echo 'Created in container' | tee container_file.txt > /dev/null"], timeout=10
        )
        assert return_code == 0

        # Verify file appears on host
        container_file = tmp_path / "container_file.txt"
        assert container_file.exists()
        # The file should contain at least some content (even if just newline)
        assert container_file.stat().st_size > 0

        # Test 3: Verify working directory is correctly mounted
        return_code, stdout, _stderr = await sandbox.execute(container_id, ["ls", "-la"], timeout=10)
        assert return_code == 0
        files_output = stdout.decode()
        assert "host_file.txt" in files_output
        assert "container_file.txt" in files_output

    finally:
        if container_id:
            await sandbox.stop(container_id)


async def test_stateless_behavior(sandbox: DockerSandbox, tmp_path: Path) -> None:
    """Test stateless container management."""
    create_test_file(tmp_path, "stateless_test.txt", "Stateless test")

    container_id1 = None
    container_id2 = None

    try:
        # Start first container
        container_id1 = await sandbox.start(
            working_dir=tmp_path, environment={"CONTAINER": "1"}, timeout=15, expire_seconds=60
        )

        # Start second container
        container_id2 = await sandbox.start(
            working_dir=tmp_path, environment={"CONTAINER": "2"}, timeout=15, expire_seconds=60
        )

        # Verify different container IDs
        assert container_id1 != container_id2
        assert isinstance(container_id1, str)
        assert isinstance(container_id2, str)

        # Test both containers are independent
        return_code1, stdout1, _stderr1 = await sandbox.execute(
            container_id1, ["/bin/bash", "-c", "echo $CONTAINER"], timeout=10
        )
        return_code2, stdout2, _stderr2 = await sandbox.execute(
            container_id2, ["/bin/bash", "-c", "echo $CONTAINER"], timeout=10
        )

        assert return_code1 == 0
        assert return_code2 == 0
        assert stdout1.decode().strip() == "1"
        assert stdout2.decode().strip() == "2"

        # Stop first container, second should still work
        await sandbox.stop(container_id1)
        container_id1 = None

        return_code2, stdout2, _stderr2 = await sandbox.execute(container_id2, ["echo", "Still running"], timeout=10)
        assert return_code2 == 0
        assert "Still running" in stdout2.decode()

    finally:
        # Cleanup
        if container_id1:
            await sandbox.stop(container_id1)
        if container_id2:
            await sandbox.stop(container_id2)


async def test_error_handling(sandbox: DockerSandbox) -> None:
    """Test error handling for invalid scenarios."""
    # Test 1: Invalid container ID for stop
    with pytest.raises(SandboxError):
        await sandbox.stop("nonexistent_container_id")

    # Test 2: Invalid container ID for execute
    # Execute method returns error code instead of raising exception
    return_code, _stdout, _stderr = await sandbox.execute("nonexistent_container_id", ["echo", "test"], timeout=5)
    # Should return non-zero exit code for invalid container
    assert return_code != 0

    # Test 3: Test _wait_for_ready with non-existent container
    with pytest.raises(SandboxStartTimeoutError):
        await sandbox._wait_for_ready("nonexistent_container_id", timeout=3)
