"""Terminal launcher implementation."""

import os
import shutil
import subprocess
from pathlib import Path

import click

from .base import Colors, WorkspaceLauncher, run_command


class TerminalLauncher(WorkspaceLauncher):
    """Terminal-based workspace launcher."""

    def is_available(self) -> bool:
        """Check if terminal launcher is available."""
        # Check for common terminal applications
        if os.name == "posix":
            if shutil.which("open"):  # macOS
                return True
            if shutil.which("gnome-terminal") or shutil.which("xterm"):  # Linux
                return True
        elif os.name == "nt":  # Windows
            return True  # Windows Terminal or cmd should be available
        return False

    def setup_workspace(
        self,
        worktree_path: Path,
        branch_name: str,  # noqa: ARG002
        task: str,
        ai_tool: str = "claude",
    ) -> bool:
        """Setup terminal workspace."""
        if not self.is_available():
            click.echo(Colors.error("Terminal launcher is not available"))
            return False

        click.echo(Colors.success(f"Launching terminal in {worktree_path}"))

        # Escape single quotes in task description
        escaped_task = task.replace("'", "'\\''")
        ai_cmd = f"{ai_tool} --dangerously-skip-permissions '{escaped_task}'"

        try:
            # Open new terminal with claude command
            self._open_terminal_with_command(worktree_path, ai_cmd)

            # Open editor
            self._open_editor(worktree_path)

        except subprocess.CalledProcessError as e:
            click.echo(Colors.error(f"Failed to launch terminal: {e}"))
            return False
        else:
            return True

    def _open_terminal_with_command(self, worktree_path: Path, command: str) -> None:
        """Open a new terminal window and run a command in it."""
        if os.name == "posix":
            if shutil.which("open"):  # macOS
                # Use AppleScript to open Terminal and run command
                script = f"""
                tell application "Terminal"
                    do script "cd '{worktree_path}' && {command}"
                    activate
                end tell
                """
                run_command(["osascript", "-e", script])
            elif shutil.which("gnome-terminal"):  # GNOME Linux
                run_command(
                    [
                        "gnome-terminal",
                        "--working-directory",
                        str(worktree_path),
                        "--",
                        "bash",
                        "-c",
                        f"{command}; exec bash",
                    ]
                )
            elif shutil.which("xterm"):  # Fallback for Linux
                run_command(
                    ["xterm", "-e", f"cd '{worktree_path}' && {command} && exec bash"]
                )
        elif os.name == "nt":  # Windows
            # Use Windows Terminal if available, otherwise cmd
            if shutil.which("wt"):  # Windows Terminal
                run_command(
                    [
                        "wt",
                        "new-tab",
                        "--startingDirectory",
                        str(worktree_path),
                        "cmd",
                        "/k",
                        command,
                    ]
                )
            else:  # Fallback to cmd
                run_command(
                    ["start", "cmd", "/k", f"cd /d {worktree_path} && {command}"],
                    shell=True,
                )

    def _open_editor(self, worktree_path: Path) -> None:
        """Open editor for the workspace."""
        editor_cmd = self.settings.editor_command

        if not editor_cmd:
            # Try to detect common editors
            for cmd in ["code", "cursor", "subl", "atom"]:
                if shutil.which(cmd):
                    editor_cmd = cmd
                    break

        if editor_cmd:
            click.echo(Colors.success(f"Opening {editor_cmd} in {worktree_path}"))
            try:
                run_command([editor_cmd, str(worktree_path)], check=False)
            except subprocess.CalledProcessError:
                click.echo(Colors.warning(f"Failed to open {editor_cmd}"))
        else:
            click.echo(
                Colors.info(
                    "No editor configured. You can open your preferred editor manually."
                )
            )

    def get_launch_instructions(
        self,
        worktree_path: Path,
        branch_name: str,  # noqa: ARG002
    ) -> list[str]:
        """Get terminal launch instructions."""
        return [
            "Terminal should have opened automatically with claude running.",
            "Your editor should also have opened automatically.",
            "",
            "If needed, you can access your workspace at:",
            click.style(f"  cd {worktree_path}", fg="cyan"),
        ]

    def handle_attachment(self, worktree_path: Path, branch_name: str) -> None:
        """Terminal launcher doesn't need additional attachment logic."""
        # Terminal and editor open automatically during setup_workspace
