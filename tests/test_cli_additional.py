"""Additional tests for CLI functionality to reach 80% coverage."""

from pathlib import Path
from unittest.mock import MagicMock, patch

from lets.cli import (
    Colors,
    setup_tmux,
)


class TestSetupTmux:
    """Test deprecated setup_tmux function."""

    def test_setup_tmux_warning(self) -> None:
        """Test that setup_tmux shows deprecation warning."""
        session = "test-session"
        window_name = "test-branch"
        task = "Test task"
        ai_tool = "claude"
        worktree_path = Path("/test/worktree")

        # Should issue a deprecation warning but still work
        with patch("lets.cli.TmuxLauncher") as mock_tmux_launcher:
            mock_launcher_instance = MagicMock()
            mock_launcher_instance.setup_workspace.return_value = True
            mock_tmux_launcher.return_value = mock_launcher_instance

            with patch("lets.cli.LetsSettings") as mock_settings:
                mock_settings_instance = MagicMock()
                mock_settings.return_value = mock_settings_instance

                result = setup_tmux(session, window_name, worktree_path, task, ai_tool)

                assert result is True
                mock_launcher_instance.setup_workspace.assert_called_once_with(
                    worktree_path, window_name, task, ai_tool
                )


class TestColorsCliModule:
    """Test Colors class in CLI module."""

    def test_colors_methods_exist(self) -> None:
        """Test that Colors class has all required methods."""
        # Test that methods exist and work
        success_msg = Colors.success("test")
        error_msg = Colors.error("test")
        info_msg = Colors.info("test")
        warning_msg = Colors.warning("test")

        assert "✓ test" in success_msg
        assert "✗ test" in error_msg
        assert "→ test" in info_msg
        assert "! test" in warning_msg

    def test_colors_styling(self) -> None:
        """Test that Colors methods apply click styling."""
        with patch("click.style") as mock_style:
            mock_style.return_value = "styled_text"

            result = Colors.success("test message")

            mock_style.assert_called_once_with("✓ test message", fg="green")
            assert result == "styled_text"

    def test_colors_error_styling(self) -> None:
        """Test that error method applies red styling."""
        with patch("click.style") as mock_style:
            mock_style.return_value = "styled_error"

            result = Colors.error("error message")

            mock_style.assert_called_once_with("✗ error message", fg="red")
            assert result == "styled_error"

    def test_colors_info_styling(self) -> None:
        """Test that info method applies blue styling."""
        with patch("click.style") as mock_style:
            mock_style.return_value = "styled_info"

            result = Colors.info("info message")

            mock_style.assert_called_once_with("→ info message", fg="blue")
            assert result == "styled_info"

    def test_colors_warning_styling(self) -> None:
        """Test that warning method applies yellow styling."""
        with patch("click.style") as mock_style:
            mock_style.return_value = "styled_warning"

            result = Colors.warning("warning message")

            mock_style.assert_called_once_with("! warning message", fg="yellow")
            assert result == "styled_warning"
