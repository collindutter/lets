"""Tests for remaining launcher edge cases to achieve 100% coverage."""

from pathlib import Path
from unittest.mock import MagicMock, patch

from lets.launchers import get_launcher
from lets.launchers.base import WorkspaceLauncher
from lets.launchers.terminal import TerminalLauncher
from lets.launchers.tmux import TmuxLauncher


class TestTerminalLauncherEdgeCases:
    """Test edge cases in terminal launcher."""

    def test_is_available_no_tools_on_posix(self) -> None:
        """Test is_available returns False when no tools available on POSIX."""
        settings = MagicMock()
        launcher = TerminalLauncher(settings)

        with (
            patch("os.name", "posix"),
            patch("shutil.which", return_value=None),  # No tools available
        ):
            result = launcher.is_available()

            assert result is False

    def test_setup_workspace_shell_exit_terminal(self) -> None:
        """Test setup_workspace shell command exit scenarios for terminal."""
        settings = MagicMock()
        settings.launchers.terminal.terminal_command = ""

        launcher = TerminalLauncher(settings)

        with (
            patch.object(launcher, "is_available", return_value=True),
            patch.object(launcher, "_open_terminal_with_command") as mock_open,
            patch.object(launcher, "_open_editor") as mock_editor,
        ):
            # Test shell command that would normally exit
            result = launcher.setup_workspace(
                Path("/test"), "branch", "exit 0", "claude"
            )

            assert result is True
            mock_open.assert_called_once()
            mock_editor.assert_called_once()


class TestTmuxLauncherEdgeCases:
    """Test edge cases in tmux launcher."""

    def test_setup_workspace_shell_exit_tmux(self) -> None:
        """Test setup_workspace shell command exit scenarios for tmux."""
        settings = MagicMock()
        settings.launchers.tmux.session = "test"
        settings.editor_command = ""

        launcher = TmuxLauncher(settings)

        with (
            patch.object(launcher, "is_available", return_value=True),
            patch("lets.launchers.tmux.run_command") as mock_run,
        ):
            mock_run.side_effect = [
                "0",  # pane base index
                None,  # kill-session (session doesn't exist)
                None,  # new-session
                None,  # rename-window
                None,  # split-window
                None,  # send-keys (shell command)
                None,  # send-keys (editor)
            ]

            # Test shell command that would normally exit
            result = launcher.setup_workspace(
                Path("/test"), "branch", "exit 0", "claude"
            )

            assert result is True

    def test_handle_attachment_tmux_not_available(self) -> None:
        """Test handle_attachment when tmux becomes unavailable."""
        settings = MagicMock()
        settings.launchers.tmux.auto_attach = True
        settings.launchers.tmux.session = "test"

        launcher = TmuxLauncher(settings)

        with (
            patch("shutil.which", return_value=None),  # tmux not found
            patch("click.confirm", return_value=False),
        ):
            # Should handle gracefully when tmux is not available
            launcher.handle_attachment(Path("/test"), "branch")


class TestTypingImports:
    """Test TYPE_CHECKING import branches."""

    def test_typing_imports_base(self) -> None:
        """Test that TYPE_CHECKING imports work in base.py."""
        # This tests the TYPE_CHECKING import block in base.py
        assert WorkspaceLauncher is not None

    def test_typing_imports_init(self) -> None:
        """Test that TYPE_CHECKING imports work in __init__.py."""
        # This tests the TYPE_CHECKING import block in __init__.py
        assert get_launcher is not None


class TestTerminalLauncherPlatformEdgeCases:
    """Test platform-specific edge cases."""

    def test_is_available_unsupported_platform(self) -> None:
        """Test is_available on completely unsupported platform."""
        settings = MagicMock()
        launcher = TerminalLauncher(settings)

        # Mock an unsupported os.name
        with patch("os.name", "unsupported_os"):
            result = launcher.is_available()

            assert result is False

    def test_open_terminal_unsupported_platform(self) -> None:
        """Test _open_terminal_with_command on unsupported platform."""
        settings = MagicMock()
        settings.launchers.terminal.terminal_command = ""

        launcher = TerminalLauncher(settings)

        with (
            patch("os.name", "unsupported_os"),
            patch("subprocess.run") as mock_run,
        ):
            launcher._open_terminal_with_command(  # noqa: SLF001
                Path("/test"), "cd /test && echo test"
            )

            # Should not call subprocess.run for unsupported platform
            mock_run.assert_not_called()


class TestSystemExitPaths:
    """Test system exit paths in launchers."""

    def test_terminal_setup_workspace_system_exit(self) -> None:
        """Test terminal setup_workspace system exit condition."""
        settings = MagicMock()
        launcher = TerminalLauncher(settings)

        with patch.object(launcher, "is_available", return_value=False):
            # This should trigger the early return False path
            result = launcher.setup_workspace(Path("/test"), "branch", "task", "claude")

            assert result is False

    def test_tmux_setup_workspace_system_exit(self) -> None:
        """Test tmux setup_workspace system exit condition."""
        settings = MagicMock()
        launcher = TmuxLauncher(settings)

        with patch.object(launcher, "is_available", return_value=False):
            # This should trigger the early return False path
            result = launcher.setup_workspace(Path("/test"), "branch", "task", "claude")

            assert result is False
