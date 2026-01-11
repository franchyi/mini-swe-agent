import os
import subprocess
from unittest.mock import patch

import pytest

from minisweagent.environments.enroot import EnrootEnvironment, EnrootEnvironmentConfig


def is_enroot_available():
    """Check if enroot is available."""
    try:
        subprocess.run(["enroot", "version"], capture_output=True, check=True, timeout=5)
        return True
    except (subprocess.CalledProcessError, FileNotFoundError, subprocess.TimeoutExpired):
        return False


@pytest.mark.skipif(not is_enroot_available(), reason="Enroot not available")
def test_enroot_environment_config_defaults():
    """Test that EnrootEnvironmentConfig has correct default values."""
    config = EnrootEnvironmentConfig(image="docker://python:3.11")

    assert config.image == "docker://python:3.11"
    assert config.cwd == "/"
    assert config.env == {}
    assert config.forward_env == []
    assert config.timeout == 30
    assert config.executable == "enroot"
    assert config.writable is True
    assert config.root is False


@pytest.mark.slow
@pytest.mark.skipif(not is_enroot_available(), reason="Enroot not available")
def test_enroot_environment_basic_execution():
    """Test basic command execution in enroot container."""
    env = EnrootEnvironment(image="docker://python:3.11-slim")

    try:
        result = env.execute("echo 'hello world'")
        assert result["returncode"] == 0
        assert "hello world" in result["output"]
    finally:
        env.cleanup()


@pytest.mark.slow
@pytest.mark.skipif(not is_enroot_available(), reason="Enroot not available")
def test_enroot_environment_set_env_variables():
    """Test setting environment variables in the container."""
    env = EnrootEnvironment(
        image="docker://python:3.11-slim", env={"TEST_VAR": "test_value", "ANOTHER_VAR": "another_value"}
    )

    try:
        # Test single environment variable
        result = env.execute("echo $TEST_VAR")
        assert result["returncode"] == 0
        assert "test_value" in result["output"]

        # Test multiple environment variables
        result = env.execute("echo $TEST_VAR $ANOTHER_VAR")
        assert result["returncode"] == 0
        assert "test_value another_value" in result["output"]
    finally:
        env.cleanup()


@pytest.mark.slow
@pytest.mark.skipif(not is_enroot_available(), reason="Enroot not available")
def test_enroot_environment_forward_env_variables():
    """Test forwarding environment variables from host to container."""
    with patch.dict(os.environ, {"HOST_VAR": "host_value", "ANOTHER_HOST_VAR": "another_host_value"}):
        env = EnrootEnvironment(image="docker://python:3.11-slim", forward_env=["HOST_VAR", "ANOTHER_HOST_VAR"])

        try:
            # Test single forwarded environment variable
            result = env.execute("echo $HOST_VAR")
            assert result["returncode"] == 0
            assert "host_value" in result["output"]

            # Test multiple forwarded environment variables
            result = env.execute("echo $HOST_VAR $ANOTHER_HOST_VAR")
            assert result["returncode"] == 0
            assert "host_value another_host_value" in result["output"]
        finally:
            env.cleanup()


@pytest.mark.slow
@pytest.mark.skipif(not is_enroot_available(), reason="Enroot not available")
def test_enroot_environment_forward_nonexistent_env_variables():
    """Test forwarding non-existent environment variables (should be empty)."""
    env = EnrootEnvironment(image="docker://python:3.11-slim", forward_env=["NONEXISTENT_VAR"])

    try:
        result = env.execute('echo "[$NONEXISTENT_VAR]"')
        assert result["returncode"] == 0
        assert "[]" in result["output"]  # Empty variable should result in empty string
    finally:
        env.cleanup()


@pytest.mark.slow
@pytest.mark.skipif(not is_enroot_available(), reason="Enroot not available")
def test_enroot_environment_combined_env_and_forward():
    """Test both setting and forwarding environment variables together."""
    with patch.dict(os.environ, {"HOST_VAR": "from_host"}):
        env = EnrootEnvironment(
            image="docker://python:3.11-slim", env={"SET_VAR": "from_config"}, forward_env=["HOST_VAR"]
        )

        try:
            result = env.execute("echo $SET_VAR $HOST_VAR")
            assert result["returncode"] == 0
            assert "from_config from_host" in result["output"]
        finally:
            env.cleanup()


@pytest.mark.slow
@pytest.mark.skipif(not is_enroot_available(), reason="Enroot not available")
def test_enroot_environment_env_override_forward():
    """Test that explicitly set env variables take precedence over forwarded ones."""
    with patch.dict(os.environ, {"CONFLICT_VAR": "from_host"}):
        env = EnrootEnvironment(
            image="docker://python:3.11-slim", env={"CONFLICT_VAR": "from_config"}, forward_env=["CONFLICT_VAR"]
        )

        try:
            result = env.execute("echo $CONFLICT_VAR")
            assert result["returncode"] == 0
            # The explicitly set env should take precedence (comes after forwarded in command)
            assert "from_config" in result["output"]
        finally:
            env.cleanup()


@pytest.mark.slow
@pytest.mark.skipif(not is_enroot_available(), reason="Enroot not available")
def test_enroot_environment_custom_cwd():
    """Test executing commands in a custom working directory."""
    env = EnrootEnvironment(image="docker://python:3.11-slim", cwd="/tmp")

    try:
        result = env.execute("pwd")
        assert result["returncode"] == 0
        assert "/tmp" in result["output"]
    finally:
        env.cleanup()


@pytest.mark.slow
@pytest.mark.skipif(not is_enroot_available(), reason="Enroot not available")
def test_enroot_environment_cwd_parameter_override():
    """Test that the cwd parameter in execute() overrides the config cwd."""
    env = EnrootEnvironment(image="docker://python:3.11-slim", cwd="/")

    try:
        result = env.execute("pwd", cwd="/tmp")
        assert result["returncode"] == 0
        assert "/tmp" in result["output"]
    finally:
        env.cleanup()


@pytest.mark.slow
@pytest.mark.skipif(not is_enroot_available(), reason="Enroot not available")
def test_enroot_environment_command_failure():
    """Test that command failures are properly captured."""
    env = EnrootEnvironment(image="docker://python:3.11-slim")

    try:
        result = env.execute("exit 42")
        assert result["returncode"] == 42
    finally:
        env.cleanup()


@pytest.mark.slow
@pytest.mark.skipif(not is_enroot_available(), reason="Enroot not available")
def test_enroot_environment_timeout():
    """Test that the timeout configuration is respected."""
    env = EnrootEnvironment(image="docker://python:3.11-slim", timeout=1)

    try:
        # This should timeout and raise TimeoutExpired
        with pytest.raises(subprocess.TimeoutExpired):
            env.execute("sleep 5")
    finally:
        env.cleanup()


@pytest.mark.slow
@pytest.mark.skipif(not is_enroot_available(), reason="Enroot not available")
def test_enroot_environment_writable():
    """Test that writable mode allows writing to the container filesystem."""
    env = EnrootEnvironment(image="docker://python:3.11-slim", writable=True)

    try:
        # Create a file in the container
        result = env.execute("echo 'test content' > /tmp/test_file.txt && cat /tmp/test_file.txt")
        assert result["returncode"] == 0
        assert "test content" in result["output"]
    finally:
        env.cleanup()


@pytest.mark.slow
@pytest.mark.skipif(not is_enroot_available(), reason="Enroot not available")
def test_enroot_environment_get_template_vars():
    """Test that get_template_vars returns the config as a dict."""
    env = EnrootEnvironment(image="docker://python:3.11-slim", cwd="/tmp", env={"KEY": "VALUE"})

    try:
        template_vars = env.get_template_vars()
        assert template_vars["image"] == "docker://python:3.11-slim"
        assert template_vars["cwd"] == "/tmp"
        assert template_vars["env"] == {"KEY": "VALUE"}
    finally:
        env.cleanup()
