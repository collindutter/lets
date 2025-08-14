"""Launcher implementations for different development environments."""

from __future__ import annotations

from typing import TYPE_CHECKING

from .base import WorkspaceLauncher
from .terminal import TerminalLauncher
from .tmux import TmuxLauncher

if TYPE_CHECKING:
    from pathlib import Path

    from lets.config import LetsSettings

__all__ = [
    "TerminalLauncher",
    "TmuxLauncher",
    "WorkspaceLauncher",
    "get_available_launchers",
    "get_best_available_launcher",
    "get_launcher",
]


def get_launcher(launcher_name: str, settings: LetsSettings) -> WorkspaceLauncher:
    """Get a launcher instance by name."""
    launchers = {
        "tmux": TmuxLauncher,
        "terminal": TerminalLauncher,
    }

    if launcher_name not in launchers:
        available_launchers = list(launchers.keys())
        msg = f"Unknown launcher: {launcher_name}. Available: {available_launchers}"
        raise ValueError(msg)

    return launchers[launcher_name](settings)


def get_available_launchers(settings: LetsSettings) -> list[str]:
    """Get list of available launchers on this system."""
    available = []
    for name in ["tmux", "terminal"]:
        launcher = get_launcher(name, settings)
        if launcher.is_available():
            available.append(name)
    return available


def get_best_available_launcher(settings: LetsSettings, project_path: Path) -> str:  # noqa: ARG001
    """Get the best available launcher."""
    # Check if default launcher is available
    try:
        launcher = get_launcher(settings.launcher, settings)
        if launcher.is_available():
            return settings.launcher
    except ValueError:
        pass

    # Fall back to available launchers in preference order
    for launcher_name in ["tmux", "terminal"]:
        launcher = get_launcher(launcher_name, settings)
        if launcher.is_available():
            return launcher_name

    # This should never happen since terminal is always available
    return "terminal"
