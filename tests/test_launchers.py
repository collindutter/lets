"""Tests for launcher implementations."""

import subprocess
from pathlib import Path
from unittest.mock import MagicMock, call, patch

import pytest

from lets.launchers import (
    get_available_launchers,
    get_best_available_launcher,
    get_launcher,
)
from lets.launchers.base import Colors, run_command
from lets.launchers.terminal import TerminalLauncher
from lets.launchers.tmux import TmuxLauncher


class TestColors:
    """Test Colors utility class from base module."""

    def test_success_message(self) -> None:
        """Test success message formatting."""
        result = Colors.success("Operation completed")
        assert "✓ Operation completed" in result

    def test_error_message(self) -> None:
        """Test error message formatting."""
        result = Colors.error("Something went wrong")
        assert "✗ Something went wrong" in result

    def test_info_message(self) -> None:
        """Test info message formatting."""
        result = Colors.info("Processing...")
        assert "→ Processing..." in result

    def test_warning_message(self) -> None:
        """Test warning message formatting."""
        result = Colors.warning("Be careful")
        assert "! Be careful" in result


class TestRunCommand:
    """Test run_command utility function from base module."""

    def test_run_command_success_with_capture(self) -> None:
        """Test successful command execution with output capture."""
        with patch("subprocess.run") as mock_run:
            mock_result = MagicMock()
            mock_result.stdout = "test output\n"
            mock_run.return_value = mock_result

            result = run_command(["echo", "test"], capture_output=True)
            assert result == "test output"
            mock_run.assert_called_once_with(
                ["echo", "test"], capture_output=True, text=True, check=True, cwd=None
            )

    def test_run_command_success_no_capture(self) -> None:
        """Test successful command execution without output capture."""
        with patch("subprocess.run") as mock_run:
            result = run_command(["echo", "test"], capture_output=False)
            assert result is None
            mock_run.assert_called_once_with(
                ["echo", "test"], capture_output=False, text=True, check=True, cwd=None
            )

    def test_run_command_with_cwd(self) -> None:
        """Test command execution with custom working directory."""
        with patch("subprocess.run") as mock_run:
            test_path = Path("/test/path")
            run_command(["echo", "test"], cwd=test_path)
            mock_run.assert_called_once_with(
                ["echo", "test"],
                capture_output=False,
                text=True,
                check=True,
                cwd=test_path,
            )

    def test_run_command_failure_with_check(self) -> None:
        """Test command failure with check=True raises exception."""
        with patch("subprocess.run") as mock_run:
            mock_run.side_effect = subprocess.CalledProcessError(1, ["false"])
            with pytest.raises(subprocess.CalledProcessError):
                run_command(["false"], check=True)

    def test_run_command_failure_no_check(self) -> None:
        """Test command failure with check=False returns None."""
        with patch("subprocess.run") as mock_run:
            mock_run.side_effect = subprocess.CalledProcessError(1, ["false"])
            result = run_command(["false"], check=False)
            assert result is None


class TestLauncherFactory:
    """Test launcher factory functions."""

    def test_get_launcher_tmux(self) -> None:
        """Test getting tmux launcher."""
        mock_settings = MagicMock()
        launcher = get_launcher("tmux", mock_settings)
        assert isinstance(launcher, TmuxLauncher)
        assert launcher.settings is mock_settings

    def test_get_launcher_terminal(self) -> None:
        """Test getting terminal launcher."""
        mock_settings = MagicMock()
        launcher = get_launcher("terminal", mock_settings)
        assert isinstance(launcher, TerminalLauncher)
        assert launcher.settings is mock_settings

    def test_get_launcher_invalid(self) -> None:
        """Test getting invalid launcher raises ValueError."""
        mock_settings = MagicMock()
        with pytest.raises(ValueError, match="Unknown launcher: invalid"):
            get_launcher("invalid", mock_settings)

    def test_get_available_launchers(self) -> None:
        """Test getting list of available launchers."""
        mock_settings = MagicMock()

        with patch("lets.launchers.get_launcher") as mock_get_launcher:
            mock_tmux = MagicMock()
            mock_tmux.is_available.return_value = True
            mock_terminal = MagicMock()
            mock_terminal.is_available.return_value = False

            mock_get_launcher.side_effect = [mock_tmux, mock_terminal]

            result = get_available_launchers(mock_settings)
            assert result == ["tmux"]

    def test_get_best_available_launcher_default_available(self) -> None:
        """Test getting best launcher when default is available."""
        mock_settings = MagicMock()
        mock_settings.launcher = "tmux"

        with patch("lets.launchers.get_launcher") as mock_get_launcher:
            mock_launcher = MagicMock()
            mock_launcher.is_available.return_value = True
            mock_get_launcher.return_value = mock_launcher

            result = get_best_available_launcher(mock_settings, Path("/test"))
            assert result == "tmux"

    def test_get_best_available_launcher_fallback(self) -> None:
        """Test getting best launcher with fallback."""
        mock_settings = MagicMock()
        mock_settings.launcher = "invalid"

        with patch("lets.launchers.get_launcher") as mock_get_launcher:
            # First call raises ValueError, subsequent calls return available launchers
            mock_tmux = MagicMock()
            mock_tmux.is_available.return_value = False
            mock_terminal = MagicMock()
            mock_terminal.is_available.return_value = True

            mock_get_launcher.side_effect = [ValueError(), mock_tmux, mock_terminal]

            result = get_best_available_launcher(mock_settings, Path("/test"))
            assert result == "terminal"

    def test_get_best_available_launcher_ultimate_fallback(self) -> None:
        """Test getting best launcher with ultimate fallback."""
        mock_settings = MagicMock()
        mock_settings.launcher = "tmux"

        with patch("lets.launchers.get_launcher") as mock_get_launcher:
            mock_launcher = MagicMock()
            mock_launcher.is_available.return_value = False
            mock_get_launcher.return_value = mock_launcher

            result = get_best_available_launcher(mock_settings, Path("/test"))
            assert result == "terminal"


class TestTerminalLauncher:
    """Test TerminalLauncher implementation."""

    def setup_method(self) -> None:
        """Set up test fixtures."""
        self.mock_settings = MagicMock()
        self.launcher = TerminalLauncher(self.mock_settings)

    def test_init(self) -> None:
        """Test TerminalLauncher initialization."""
        assert self.launcher.settings is self.mock_settings

    def test_is_available_macos(self) -> None:
        """Test availability check on macOS."""
        with patch("os.name", "posix"), patch("shutil.which") as mock_which:
            mock_which.return_value = "/usr/bin/open"
            assert self.launcher.is_available() is True

    def test_is_available_linux_gnome(self) -> None:
        """Test availability check on Linux with GNOME terminal."""
        with patch("os.name", "posix"), patch("shutil.which") as mock_which:

            def which_side_effect(cmd: str) -> str | None:
                return (
                    "/usr/bin/gnome-terminal" if cmd == "gnome-terminal" else None
                )

            mock_which.side_effect = which_side_effect
            assert self.launcher.is_available() is True

    def test_is_available_linux_xterm(self) -> None:
        """Test availability check on Linux with xterm."""
        with patch("os.name", "posix"), patch("shutil.which") as mock_which:

            def which_side_effect(cmd: str) -> str | None:
                return "/usr/bin/xterm" if cmd == "xterm" else None

            mock_which.side_effect = which_side_effect
            assert self.launcher.is_available() is True

    def test_is_available_windows(self) -> None:
        """Test availability check on Windows."""
        with patch("os.name", "nt"):
            assert self.launcher.is_available() is True

    def test_is_available_unsupported(self) -> None:
        """Test availability check on unsupported system."""
        with patch("os.name", "other"):
            assert self.launcher.is_available() is False

    def test_setup_workspace_success(self) -> None:
        """Test successful workspace setup."""
        worktree_path = Path("/test/worktree")

        with (
            patch.object(self.launcher, "is_available", return_value=True),
            patch.object(self.launcher, "_open_terminal_with_command") as mock_terminal,
            patch.object(self.launcher, "_open_editor") as mock_editor,
        ):
            result = self.launcher.setup_workspace(
                worktree_path, "test-branch", "Test task", "claude"
            )

            assert result is True
            mock_terminal.assert_called_once_with(
                worktree_path,
                "claude --dangerously-skip-permissions 'Test task'",
            )
            mock_editor.assert_called_once_with(worktree_path)

    def test_setup_workspace_not_available(self) -> None:
        """Test workspace setup when launcher not available."""
        worktree_path = Path("/test/worktree")

        with patch.object(self.launcher, "is_available", return_value=False):
            result = self.launcher.setup_workspace(
                worktree_path, "test-branch", "Test task", "claude"
            )
            assert result is False

    def test_setup_workspace_task_with_quotes(self) -> None:
        """Test workspace setup with task containing single quotes."""
        worktree_path = Path("/test/worktree")

        with (
            patch.object(self.launcher, "is_available", return_value=True),
            patch.object(self.launcher, "_open_terminal_with_command") as mock_terminal,
            patch.object(self.launcher, "_open_editor"),
        ):
            self.launcher.setup_workspace(
                worktree_path, "test-branch", "Fix 'auth' issue", "claude"
            )

            expected_cmd = (
                "claude --dangerously-skip-permissions 'Fix '\\''auth'\\'' issue'"
            )
            mock_terminal.assert_called_once_with(worktree_path, expected_cmd)

    def test_setup_workspace_subprocess_error(self) -> None:
        """Test workspace setup with subprocess error."""
        worktree_path = Path("/test/worktree")

        with (
            patch.object(self.launcher, "is_available", return_value=True),
            patch.object(self.launcher, "_open_terminal_with_command") as mock_terminal,
        ):
            mock_terminal.side_effect = subprocess.CalledProcessError(1, ["cmd"])
            result = self.launcher.setup_workspace(
                worktree_path, "test-branch", "Test task", "claude"
            )
            assert result is False

    def test_open_terminal_with_command_macos(self) -> None:
        """Test opening terminal on macOS."""
        worktree_path = Path("/test/worktree")
        command = "claude --skip-permissions 'task'"

        with (
            patch("os.name", "posix"),
            patch("shutil.which", return_value="/usr/bin/open"),
            patch("lets.launchers.terminal.run_command") as mock_run,
        ):
            self.launcher._open_terminal_with_command(worktree_path, command)  # noqa: SLF001

            mock_run.assert_called_once()
            args = mock_run.call_args[0][0]
            assert args[0] == "osascript"
            assert "Terminal" in args[2]
            assert str(worktree_path) in args[2]
            assert command in args[2]

    def test_open_terminal_with_command_linux_gnome(self) -> None:
        """Test opening terminal on Linux with GNOME terminal."""
        worktree_path = Path("/test/worktree")
        command = "claude --skip-permissions 'task'"

        with patch("os.name", "posix"), patch("shutil.which") as mock_which:

            def which_side_effect(cmd: str) -> str | None:
                if cmd == "open":
                    return None
                if cmd == "gnome-terminal":
                    return "/usr/bin/gnome-terminal"
                return None

            mock_which.side_effect = which_side_effect

            with patch("lets.launchers.terminal.run_command") as mock_run:
                self.launcher._open_terminal_with_command(worktree_path, command)  # noqa: SLF001  # noqa: SLF001

                mock_run.assert_called_once_with(
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

    def test_open_terminal_with_command_linux_xterm(self) -> None:
        """Test opening terminal on Linux with xterm."""
        worktree_path = Path("/test/worktree")
        command = "claude --skip-permissions 'task'"

        with patch("os.name", "posix"), patch("shutil.which") as mock_which:

            def which_side_effect(cmd: str) -> str | None:
                if cmd in ["open", "gnome-terminal"]:
                    return None
                if cmd == "xterm":
                    return "/usr/bin/xterm"
                return None

            mock_which.side_effect = which_side_effect

            with patch("lets.launchers.terminal.run_command") as mock_run:
                self.launcher._open_terminal_with_command(worktree_path, command)  # noqa: SLF001  # noqa: SLF001

                expected_cmd = f"cd '{worktree_path}' && {command} && exec bash"
                mock_run.assert_called_once_with(["xterm", "-e", expected_cmd])

    def test_open_terminal_with_command_windows_wt(self) -> None:
        """Test opening terminal on Windows with Windows Terminal."""
        worktree_path = Path("/test/worktree")
        command = "claude --skip-permissions 'task'"

        with patch("os.name", "nt"), patch("shutil.which") as mock_which:

            def which_side_effect(cmd: str) -> str | None:
                return "/usr/bin/wt" if cmd == "wt" else None

            mock_which.side_effect = which_side_effect

            with patch("lets.launchers.terminal.run_command") as mock_run:
                self.launcher._open_terminal_with_command(worktree_path, command)  # noqa: SLF001  # noqa: SLF001

                mock_run.assert_called_once_with(
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

    def test_open_terminal_with_command_windows_cmd(self) -> None:
        """Test opening terminal on Windows with cmd fallback."""
        worktree_path = Path("/test/worktree")
        command = "claude --skip-permissions 'task'"

        with (
            patch("os.name", "nt"),
            patch("shutil.which", return_value=None),
            patch("lets.launchers.terminal.run_command") as mock_run,
        ):
            self.launcher._open_terminal_with_command(worktree_path, command)  # noqa: SLF001

            expected_cmd = f"cd /d {worktree_path} && {command}"
            mock_run.assert_called_once_with(
                ["start", "cmd", "/k", expected_cmd], shell=True
            )

    def test_open_editor_configured(self) -> None:
        """Test opening configured editor."""
        worktree_path = Path("/test/worktree")
        self.mock_settings.editor_command = "code"

        with patch("lets.launchers.terminal.run_command") as mock_run:
            self.launcher._open_editor(worktree_path)  # noqa: SLF001

            mock_run.assert_called_once_with(["code", str(worktree_path)], check=False)

    def test_open_editor_auto_detect(self) -> None:
        """Test auto-detecting editor."""
        worktree_path = Path("/test/worktree")
        self.mock_settings.editor_command = None

        with (
            patch("shutil.which") as mock_which,
            patch("lets.launchers.terminal.run_command") as mock_run,
        ):
            def which_side_effect(cmd: str) -> str | None:
                return "/usr/bin/code" if cmd == "code" else None

            mock_which.side_effect = which_side_effect

            self.launcher._open_editor(worktree_path)  # noqa: SLF001

            mock_run.assert_called_once_with(
                ["code", str(worktree_path)], check=False
            )

    def test_open_editor_none_available(self) -> None:
        """Test when no editor is available."""
        worktree_path = Path("/test/worktree")
        self.mock_settings.editor_command = None

        with (
            patch("shutil.which", return_value=None),
            patch("lets.launchers.terminal.run_command") as mock_run,
        ):
            self.launcher._open_editor(worktree_path)  # noqa: SLF001

            mock_run.assert_not_called()

    def test_open_editor_subprocess_error(self) -> None:
        """Test handling editor subprocess error."""
        worktree_path = Path("/test/worktree")
        self.mock_settings.editor_command = "code"

        with patch("lets.launchers.terminal.run_command") as mock_run:
            mock_run.side_effect = subprocess.CalledProcessError(1, ["code"])
            # Should not raise exception
            self.launcher._open_editor(worktree_path)  # noqa: SLF001

    def test_get_launch_instructions(self) -> None:
        """Test getting launch instructions."""
        worktree_path = Path("/test/worktree")
        instructions = self.launcher.get_launch_instructions(
            worktree_path, "test-branch"
        )

        assert len(instructions) > 0
        assert any("Terminal should have opened" in instr for instr in instructions)
        assert any(str(worktree_path) in instr for instr in instructions)

    def test_handle_attachment(self) -> None:
        """Test attachment handling (should be no-op)."""
        worktree_path = Path("/test/worktree")
        # Should not raise any exceptions
        self.launcher.handle_attachment(worktree_path, "test-branch")


class TestTmuxLauncher:
    """Test TmuxLauncher implementation."""

    def setup_method(self) -> None:
        """Set up test fixtures."""
        self.mock_settings = MagicMock()
        self.mock_settings.launchers.tmux.session = "lets"
        self.mock_settings.launchers.tmux.auto_attach = True
        self.mock_settings.editor_command = "vim"
        self.launcher = TmuxLauncher(self.mock_settings)

    def test_init(self) -> None:
        """Test TmuxLauncher initialization."""
        assert self.launcher.settings is self.mock_settings

    def test_is_available_true(self) -> None:
        """Test availability when tmux is available."""
        with patch("shutil.which", return_value="/usr/bin/tmux"):
            assert self.launcher.is_available() is True

    def test_is_available_false(self) -> None:
        """Test availability when tmux is not available."""
        with patch("shutil.which", return_value=None):
            assert self.launcher.is_available() is False

    def test_get_pane_base_index_custom(self) -> None:
        """Test getting custom pane base index."""
        with patch("lets.launchers.tmux.run_command") as mock_run:
            mock_run.return_value = "pane-base-index 1"
            result = self.launcher.get_pane_base_index()
            assert result == 1

    def test_get_pane_base_index_default(self) -> None:
        """Test getting default pane base index on error."""
        with patch("lets.launchers.tmux.run_command") as mock_run:
            mock_run.side_effect = subprocess.CalledProcessError(1, ["tmux"])
            result = self.launcher.get_pane_base_index()
            assert result == 0

    def test_get_pane_base_index_parse_error(self) -> None:
        """Test getting default pane base index on parse error."""
        with patch("lets.launchers.tmux.run_command") as mock_run:
            mock_run.return_value = "invalid output"
            result = self.launcher.get_pane_base_index()
            assert result == 0

    def test_setup_workspace_not_available(self) -> None:
        """Test workspace setup when tmux not available."""
        with patch.object(self.launcher, "is_available", return_value=False):
            result = self.launcher.setup_workspace(
                Path("/test"), "branch", "task", "claude"
            )
            assert result is False

    def test_setup_workspace_new_session(self) -> None:
        """Test workspace setup with new session."""
        worktree_path = Path("/test/worktree")

        with (
            patch.object(self.launcher, "is_available", return_value=True),
            patch("lets.launchers.tmux.run_command") as mock_run,
            patch.object(self.launcher, "get_pane_base_index", return_value=0),
        ):
            # has-session fails (session doesn't exist)
            mock_run.side_effect = [
                subprocess.CalledProcessError(
                    1, ["tmux", "has-session"]
                ),  # session check
                None,  # new-session
                1,  # get_pane_base_index
                None,  # split-window
                None,  # send-keys editor
                None,  # send-keys claude
                None,  # select-pane
            ]

            result = self.launcher.setup_workspace(
                worktree_path, "test-branch", "Test task", "claude"
            )

            assert result is True

            # Verify new-session call
            new_session_call = call(
                [
                    "tmux",
                    "new-session",
                    "-d",
                    "-s",
                    "lets",
                    "-n",
                    "test-branch",
                    "-c",
                    str(worktree_path),
                ]
            )
            assert new_session_call in mock_run.call_args_list

    def test_setup_workspace_existing_session(self) -> None:
        """Test workspace setup with existing session."""
        worktree_path = Path("/test/worktree")

        with (
            patch.object(self.launcher, "is_available", return_value=True),
            patch("lets.launchers.tmux.run_command") as mock_run,
            patch.object(self.launcher, "get_pane_base_index", return_value=1),
        ):
            # has-session succeeds (session exists)
            mock_run.side_effect = [
                None,  # has-session succeeds
                None,  # new-window
                None,  # split-window
                None,  # send-keys editor
                None,  # send-keys claude
                None,  # select-pane
            ]

            result = self.launcher.setup_workspace(
                worktree_path, "test-branch", "Test task", "claude"
            )

            assert result is True

            # Verify new-window call
            new_window_call = call(
                [
                    "tmux",
                    "new-window",
                    "-t",
                    "lets:",
                    "-n",
                    "test-branch",
                    "-c",
                    str(worktree_path),
                ]
            )
            assert new_window_call in mock_run.call_args_list

    def test_setup_workspace_task_with_quotes(self) -> None:
        """Test workspace setup with task containing quotes."""
        worktree_path = Path("/test/worktree")

        with (
            patch.object(self.launcher, "is_available", return_value=True),
            patch("lets.launchers.tmux.run_command") as mock_run,
            patch.object(self.launcher, "get_pane_base_index", return_value=0),
        ):
            mock_run.side_effect = [
                subprocess.CalledProcessError(1, ["tmux"]),  # session doesn't exist
                None,  # new-session
                None,  # split-window
                None,  # send-keys editor
                None,  # send-keys claude
                None,  # select-pane
            ]

            self.launcher.setup_workspace(
                worktree_path, "test-branch", "Fix 'auth' issue", "claude"
            )

            # Check that the task was properly escaped
            claude_call = None
            for call_args in mock_run.call_args_list:
                if "send-keys" in call_args[0][0] and "claude" in str(
                    call_args[0][0]
                ):
                    claude_call = call_args
                    break

            assert claude_call is not None
            expected_cmd = (
                "claude --dangerously-skip-permissions 'Fix '\\''auth'\\'' issue'"
            )
            assert expected_cmd in claude_call[0][0]

    def test_setup_workspace_custom_editor(self) -> None:
        """Test workspace setup with custom editor."""
        worktree_path = Path("/test/worktree")
        self.mock_settings.editor_command = "nvim"

        with (
            patch.object(self.launcher, "is_available", return_value=True),
            patch("lets.launchers.tmux.run_command") as mock_run,
            patch.object(self.launcher, "get_pane_base_index", return_value=0),
        ):
            mock_run.side_effect = [
                subprocess.CalledProcessError(1, ["tmux"]),  # session doesn't exist
                None,  # new-session
                None,  # split-window
                None,  # send-keys editor
                None,  # send-keys claude
                None,  # select-pane
            ]

            self.launcher.setup_workspace(
                worktree_path, "test-branch", "Test task", "claude"
            )

            # Check that nvim was used
            editor_call = None
            for call_args in mock_run.call_args_list:
                if "send-keys" in call_args[0][0] and "nvim" in str(
                    call_args[0][0]
                ):
                    editor_call = call_args
                    break

            assert editor_call is not None

    def test_setup_workspace_editor_from_env(self) -> None:
        """Test workspace setup with editor from environment."""
        worktree_path = Path("/test/worktree")
        self.mock_settings.editor_command = None

        with (
            patch.object(self.launcher, "is_available", return_value=True),
            patch("lets.launchers.tmux.run_command") as mock_run,
            patch.dict("os.environ", {"EDITOR": "emacs"}),
            patch.object(self.launcher, "get_pane_base_index", return_value=0),
        ):
            mock_run.side_effect = [
                subprocess.CalledProcessError(1, ["tmux"]),  # session doesn't exist
                None,  # new-session
                None,  # split-window
                None,  # send-keys editor
                None,  # send-keys claude
                None,  # select-pane
            ]

            self.launcher.setup_workspace(
                worktree_path, "test-branch", "Test task", "claude"
            )

            # Check that emacs was used
            editor_call = None
            for call_args in mock_run.call_args_list:
                if "send-keys" in call_args[0][0] and "emacs" in str(
                    call_args[0][0]
                ):
                    editor_call = call_args
                    break

            assert editor_call is not None

    def test_get_launch_instructions(self) -> None:
        """Test getting launch instructions."""
        worktree_path = Path("/test/worktree")
        instructions = self.launcher.get_launch_instructions(
            worktree_path, "test-branch"
        )

        assert len(instructions) > 0
        assert any("tmux attach" in instr for instr in instructions)
        assert any("test-branch" in instr for instr in instructions)

    def test_handle_attachment_disabled(self) -> None:
        """Test attachment handling when auto-attach is disabled."""
        self.mock_settings.launchers.tmux.auto_attach = False

        # Should return early without doing anything
        self.launcher.handle_attachment(Path("/test"), "branch")

    def test_handle_attachment_inside_tmux_confirm_yes(self) -> None:
        """Test attachment when already inside tmux and user confirms switch."""
        with (
            patch.dict("os.environ", {"TMUX": "tmux-session"}),
            patch("click.confirm", return_value=True),
            patch("shutil.which", return_value="/usr/bin/tmux"),
            patch("subprocess.run") as mock_run,
        ):
            mock_result = MagicMock()
            mock_result.returncode = 0
            mock_run.return_value = mock_result

            self.launcher.handle_attachment(Path("/test"), "test-branch")

            mock_run.assert_called_once_with(
                [
                    "/usr/bin/tmux",
                    "switch-client",
                    "-t",
                    "lets:test-branch",
                ],
                check=False,
                capture_output=True,
                text=True,
            )

    def test_handle_attachment_inside_tmux_confirm_no(self) -> None:
        """Test attachment when already inside tmux and user declines switch."""
        with (
            patch.dict("os.environ", {"TMUX": "tmux-session"}),
            patch("click.confirm", return_value=False),
            patch("subprocess.run") as mock_run,
        ):
            self.launcher.handle_attachment(Path("/test"), "test-branch")

            mock_run.assert_not_called()

    def test_handle_attachment_inside_tmux_switch_error(self) -> None:
        """Test attachment when switch-client fails."""
        with (
            patch.dict("os.environ", {"TMUX": "tmux-session"}),
            patch("click.confirm", return_value=True),
            patch("shutil.which", return_value="/usr/bin/tmux"),
            patch("subprocess.run") as mock_run,
        ):
            mock_result = MagicMock()
            mock_result.returncode = 1
            mock_result.stderr = "session not found"
            mock_run.return_value = mock_result

            # Should not raise exception
            self.launcher.handle_attachment(Path("/test"), "test-branch")

    def test_handle_attachment_outside_tmux_confirm_yes(self) -> None:
        """Test attachment when outside tmux and user confirms attach."""
        with (
            patch.dict("os.environ", {}, clear=True),  # Not in tmux
            patch("click.confirm", return_value=True),
            patch("shutil.which", return_value="/usr/bin/tmux"),
            patch("subprocess.run") as mock_run,
        ):
            self.launcher.handle_attachment(Path("/test"), "test-branch")

            mock_run.assert_called_once_with(
                [
                    "/usr/bin/tmux",
                    "attach",
                    "-t",
                    "lets",
                    ";",
                    "select-window",
                    "-t",
                    "test-branch",
                ],
                check=False,
            )

    def test_handle_attachment_outside_tmux_confirm_no(self) -> None:
        """Test attachment when outside tmux and user declines attach."""
        with (
            patch.dict("os.environ", {}, clear=True),  # Not in tmux
            patch("click.confirm", return_value=False),
            patch("subprocess.run") as mock_run,
        ):
            self.launcher.handle_attachment(Path("/test"), "test-branch")

            mock_run.assert_not_called()

    def test_handle_attachment_tmux_not_found(self) -> None:
        """Test attachment when tmux binary not found."""
        with (
            patch.dict("os.environ", {}, clear=True),  # Not in tmux
            patch("click.confirm", return_value=True),
            patch("shutil.which", return_value=None),
            patch("subprocess.run") as mock_run,
        ):
            self.launcher.handle_attachment(Path("/test"), "test-branch")

            mock_run.assert_not_called()
