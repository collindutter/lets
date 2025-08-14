"""Tmux launcher implementation."""

import os
import shutil
import subprocess
from pathlib import Path

import click

from .base import Colors, WorkspaceLauncher, run_command


class TmuxLauncher(WorkspaceLauncher):
    """Tmux-based workspace launcher."""

    def is_available(self) -> bool:
        """Check if tmux is available."""
        return shutil.which("tmux") is not None

    def get_pane_base_index(self) -> int:
        """Get the tmux pane-base-index setting."""
        try:
            result = run_command(
                ["tmux", "show-option", "-g", "pane-base-index"], capture_output=True
            )
            if result:
                # Output format: "pane-base-index 1"
                return int(result.strip().split()[-1])
        except (subprocess.CalledProcessError, ValueError, IndexError):
            pass
        return 0  # Default tmux pane-base-index

    def setup_workspace(
        self, worktree_path: Path, branch_name: str, task: str, ai_tool: str = "claude"
    ) -> bool:
        """Setup tmux session with split panes for editor and claude."""
        if not self.is_available():
            click.echo(Colors.error("tmux is not installed"))
            return False

        session = self.settings.launchers.tmux.session
        window_name = f"{branch_name}"

        # Check if session exists, create if not
        try:
            run_command(["tmux", "has-session", "-t", session], capture_output=True)
            session_exists = True
        except subprocess.CalledProcessError:
            session_exists = False

        if not session_exists:
            click.echo(Colors.success(f"Creating tmux session: {session}"))
            # Create session with the window
            run_command(
                [
                    "tmux",
                    "new-session",
                    "-d",
                    "-s",
                    session,
                    "-n",
                    window_name,
                    "-c",
                    str(worktree_path),
                ]
            )
        else:
            click.echo(Colors.success(f"Using existing tmux session: {session}"))
            # Create window in existing session
            click.echo(Colors.success(f"Creating tmux window: {window_name}"))
            run_command(
                [
                    "tmux",
                    "new-window",
                    "-t",
                    f"{session}:",
                    "-n",
                    window_name,
                    "-c",
                    str(worktree_path),
                ]
            )

        # Get pane base index to handle both 0-based and 1-based configurations
        base_index = self.get_pane_base_index()
        left_pane = base_index
        right_pane = base_index + 1

        # Split window vertically (editor left, claude right)
        click.echo(
            Colors.success("Creating split panes: editor (left) and claude (right)")
        )
        run_command(
            [
                "tmux",
                "split-window",
                "-t",
                f"{session}:{window_name}",
                "-h",
                "-c",
                str(worktree_path),
            ]
        )

        # Start editor in left pane
        editor = self.settings.editor_command or os.environ.get("EDITOR", "vim")
        run_command(
            [
                "tmux",
                "send-keys",
                "-t",
                f"{session}:{window_name}.{left_pane}",
                editor,
                "Enter",
            ]
        )

        # Escape single quotes in task description and start claude in right pane
        escaped_task = task.replace("'", "'\\''")
        ai_cmd = f"{ai_tool} --dangerously-skip-permissions '{escaped_task}'"
        run_command(
            [
                "tmux",
                "send-keys",
                "-t",
                f"{session}:{window_name}.{right_pane}",
                ai_cmd,
                "Enter",
            ]
        )

        # Select the claude pane initially
        run_command(
            ["tmux", "select-pane", "-t", f"{session}:{window_name}.{right_pane}"]
        )

        return True

    def get_launch_instructions(
        self,
        worktree_path: Path,  # noqa: ARG002
        branch_name: str,
    ) -> list[str]:
        """Get tmux launch instructions."""
        session = self.settings.launchers.tmux.session
        window_name = f"{branch_name}"
        return [
            "To attach to the session:",
            click.style(f"  tmux attach -t {session}", fg="cyan"),
            "",
            "To go directly to this window:",
            click.style(
                f"  tmux attach -t {session} \\; select-window -t {window_name}",
                fg="cyan",
            ),
            "",
            "Split panes: Editor (left) | Claude (right)",
            "Switch between panes: Ctrl+b then arrow keys",
        ]

    def handle_attachment(
        self,
        worktree_path: Path,  # noqa: ARG002
        branch_name: str,
    ) -> None:
        """Handle tmux session attachment logic."""
        if not self.settings.launchers.tmux.auto_attach:
            return

        session = self.settings.launchers.tmux.session
        window_name = f"{branch_name}"
        click.echo()

        # Check if we're already in tmux
        if os.environ.get("TMUX"):
            click.echo(Colors.warning("Already inside tmux session"))
            if click.confirm("Switch to workspace window?", default=True):
                tmux_path = shutil.which("tmux")
                if tmux_path:
                    # Use switch-client to change to the target session and window
                    result = subprocess.run(
                        [
                            tmux_path,
                            "switch-client",
                            "-t",
                            f"{session}:{window_name}",
                        ],
                        check=False,
                        capture_output=True,
                        text=True,
                    )
                    if result.returncode != 0:
                        error_msg = result.stderr.strip()
                        click.echo(
                            Colors.error(f"Failed to switch window: {error_msg}")
                        )
        elif click.confirm("Attach to tmux session now?", default=True):
            tmux_path = shutil.which("tmux")
            if tmux_path:
                subprocess.run(
                    [
                        tmux_path,
                        "attach",
                        "-t",
                        session,
                        ";",
                        "select-window",
                        "-t",
                        window_name,
                    ],
                    check=False,
                )
