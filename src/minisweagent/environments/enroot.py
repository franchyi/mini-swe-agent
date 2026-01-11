#!/usr/bin/env python3

import logging
import os
import shutil
import subprocess
import tempfile
import uuid
from pathlib import Path
from typing import Any

from pydantic import BaseModel


class EnrootEnvironmentConfig(BaseModel):
    image: str
    """Container image URI (e.g., docker://python:3.11-slim)."""
    cwd: str = "/"
    """Working directory in which to execute commands."""
    env: dict[str, str] = {}
    """Environment variables to set in the container."""
    forward_env: list[str] = []
    """Environment variables to forward to the container."""
    timeout: int = 30
    """Timeout for executing commands in the container."""
    executable: str = os.getenv("MSWEA_ENROOT_EXECUTABLE", "enroot")
    """Path to the enroot executable."""
    import_timeout: int = 300
    """Timeout in seconds for importing images."""
    create_timeout: int = 120
    """Timeout in seconds for creating containers."""
    writable: bool = True
    """Make the container root filesystem writable."""
    root: bool = False
    """Run as root inside the container."""


class EnrootEnvironment:
    def __init__(
        self, *, config_class: type = EnrootEnvironmentConfig, logger: logging.Logger | None = None, **kwargs
    ):
        """Enroot environment for HPC clusters. See `EnrootEnvironmentConfig` for kwargs."""
        self.logger = logger or logging.getLogger("minisweagent.environment")
        self.config = config_class(**kwargs)
        self.container_name: str | None = None
        self.sqsh_path: Path | None = None
        self._setup_container()

    def _setup_container(self):
        """Import image and create container."""
        # Generate unique names
        unique_id = uuid.uuid4().hex[:8]
        self.container_name = f"minisweagent-{unique_id}"

        # Create a temp directory for the sqsh file
        self.temp_dir = Path(tempfile.mkdtemp(prefix="minisweagent-enroot-"))

        # Import the image to create a .sqsh file
        sqsh_filename = f"{self.container_name}.sqsh"
        self.sqsh_path = self.temp_dir / sqsh_filename

        self.logger.debug(f"Importing image {self.config.image} to {self.sqsh_path}")
        try:
            subprocess.run(
                [self.config.executable, "import", "-o", str(self.sqsh_path), self.config.image],
                check=True,
                capture_output=True,
                timeout=self.config.import_timeout,
            )
        except subprocess.CalledProcessError as e:
            self.logger.error(f"Failed to import image {self.config.image}: stdout={e.stdout}, stderr={e.stderr}")
            raise

        # Create the container from the sqsh file
        self.logger.debug(f"Creating container {self.container_name} from {self.sqsh_path}")
        try:
            subprocess.run(
                [self.config.executable, "create", "-n", self.container_name, str(self.sqsh_path)],
                check=True,
                capture_output=True,
                timeout=self.config.create_timeout,
            )
        except subprocess.CalledProcessError as e:
            self.logger.error(
                f"Failed to create container {self.container_name}: stdout={e.stdout}, stderr={e.stderr}"
            )
            raise

        self.logger.info(f"Created enroot container {self.container_name}")

    def get_template_vars(self) -> dict[str, Any]:
        return self.config.model_dump()

    def execute(self, command: str, cwd: str = "", *, timeout: int | None = None) -> dict[str, Any]:
        """Execute a command in the enroot container and return the result as a dict."""
        assert self.container_name, "Container not created"

        cmd = [self.config.executable, "start"]

        # Add writable flag if needed
        if self.config.writable:
            cmd.append("--rw")

        # Add root flag if needed
        if self.config.root:
            cmd.append("--root")

        # Add forwarded environment variables
        for key in self.config.forward_env:
            if (value := os.getenv(key)) is not None:
                cmd.extend(["--env", f"{key}={value}"])

        # Add configured environment variables (these take precedence)
        for key, value in self.config.env.items():
            cmd.extend(["--env", f"{key}={value}"])

        cmd.append(self.container_name)

        # Handle working directory by wrapping command with cd
        work_dir = cwd or self.config.cwd
        if work_dir and work_dir != "/":
            full_command = f"cd {work_dir} && {command}"
        else:
            full_command = command

        cmd.extend(["bash", "-c", full_command])

        result = subprocess.run(
            cmd,
            text=True,
            timeout=timeout or self.config.timeout,
            encoding="utf-8",
            errors="replace",
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
        )
        return {"output": result.stdout, "returncode": result.returncode}

    def cleanup(self):
        """Remove the enroot container and temporary files."""
        if getattr(self, "container_name", None) is not None:
            try:
                subprocess.run(
                    [self.config.executable, "remove", "-f", self.container_name],
                    capture_output=True,
                    timeout=30,
                )
                self.logger.debug(f"Removed enroot container {self.container_name}")
            except (subprocess.CalledProcessError, subprocess.TimeoutExpired) as e:
                self.logger.warning(f"Failed to remove container {self.container_name}: {e}")

        # Clean up the temp directory with sqsh file
        if getattr(self, "temp_dir", None) is not None:
            shutil.rmtree(self.temp_dir, ignore_errors=True)

    def __del__(self):
        """Cleanup container when object is destroyed."""
        self.cleanup()
