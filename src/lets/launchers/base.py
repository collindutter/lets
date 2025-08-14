"""Abstract base class for workspace launchers."""

from __future__ import annotations

import subprocess
from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

import click

if TYPE_CHECKING:
    from pathlib import Path

    from lets.config import LetsSettings


class Colors:
    """Terminal color codes for click.echo."""

    @staticmethod
    def success(msg: str) -> str:
        """Return success message with green styling."""
        return click.style(f"✓ {msg}", fg="green")

    @staticmethod
    def error(msg: str) -> str:
        """Return error message with red styling."""
        return click.style(f"✗ {msg}", fg="red")

    @staticmethod
    def info(msg: str) -> str:
        """Return info message with blue styling."""
        return click.style(f"→ {msg}", fg="blue")

    @staticmethod
    def warning(msg: str) -> str:
        """Return warning message with yellow styling."""
        return click.style(f"! {msg}", fg="yellow")


def run_command(
    cmd: list[str],
    *,
    capture_output: bool = False,
    check: bool = True,
    cwd: Path | None = None,
) -> str | None:
    """Run a shell command and optionally return output."""
    try:
        result = subprocess.run(
            cmd, capture_output=capture_output, text=True, check=check, cwd=cwd
        )
        if capture_output:
            return result.stdout.strip()
    except subprocess.CalledProcessError:
        if check:
            raise
        return None
    else:
        return None


class WorkspaceLauncher(ABC):
    """Abstract base class for workspace launchers."""

    def __init__(self, settings: LetsSettings) -> None:
        """Initialize launcher with settings."""
        self.settings = settings

    @abstractmethod
    def is_available(self) -> bool:
        """Check if the launcher's required tools are available."""

    @abstractmethod
    def setup_workspace(
        self, worktree_path: Path, branch_name: str, task: str, ai_tool: str = "claude"
    ) -> bool:
        """Set up the workspace environment."""

    @abstractmethod
    def get_launch_instructions(
        self, worktree_path: Path, branch_name: str
    ) -> list[str]:
        """Get user-friendly instructions for accessing the workspace."""

    @abstractmethod
    def handle_attachment(self, worktree_path: Path, branch_name: str) -> None:
        """Handle post-setup attachment/launching logic."""
