"""Tests for setup wizard functionality."""

from pathlib import Path
from unittest.mock import MagicMock, patch

from lets.cli import (
    _setup_ai_tool_config,
    _setup_editor_config,
    _setup_env_files_config,
    _setup_git_config,
    _setup_launcher_config,
    _setup_worktree_config,
    _show_setup_summary,
    _validate_command_exists,
    check_and_run_setup_wizard,
    handle_launcher_attachment,
    print_workspace_summary,
    run_setup_wizard,
)


class TestValidateCommandExists:
    """Test command validation function."""

    def test_validate_command_exists_true(self) -> None:
        """Test validating existing command."""
        with patch("shutil.which", return_value="/usr/bin/git"):
            assert _validate_command_exists("git") is True

    def test_validate_command_exists_false(self) -> None:
        """Test validating non-existing command."""
        with patch("shutil.which", return_value=None):
            assert _validate_command_exists("nonexistent") is False


class TestSetupLauncherConfig:
    """Test launcher configuration in setup wizard."""

    def test_setup_launcher_config_exists(self) -> None:
        """Test that _setup_launcher_config function exists."""
        # This is a basic smoke test to ensure the function is importable
        assert callable(_setup_launcher_config)


class TestSetupAIToolConfig:
    """Test AI tool configuration in setup wizard."""

    def test_setup_ai_tool_config_exists(self) -> None:
        """Test that _setup_ai_tool_config function exists."""
        assert callable(_setup_ai_tool_config)


class TestSetupEditorConfig:
    """Test editor configuration in setup wizard."""

    def test_setup_editor_config_exists(self) -> None:
        """Test that _setup_editor_config function exists."""
        assert callable(_setup_editor_config)


class TestSetupWorktreeConfig:
    """Test worktree configuration in setup wizard."""

    def test_setup_worktree_config_exists(self) -> None:
        """Test that _setup_worktree_config function exists."""
        assert callable(_setup_worktree_config)


class TestSetupEnvFilesConfig:
    """Test environment files configuration in setup wizard."""

    def test_setup_env_files_config_enabled_default(self) -> None:
        """Test enabling env files with default patterns."""
        settings = MagicMock()

        with patch(
            "click.confirm", side_effect=[True, True]
        ):  # Enable, use default patterns
            _setup_env_files_config(settings)

            assert settings.copy_env_files is True
            # Default patterns should be set in the dataclass

    def test_setup_env_files_config_enabled_custom(self) -> None:
        """Test enabling env files with custom patterns."""
        settings = MagicMock()

        with (
            patch(
                "click.confirm", side_effect=[True, False]
            ),  # Enable, custom patterns
            patch("click.prompt", return_value=".env,.env.prod"),
        ):
            _setup_env_files_config(settings)

            assert settings.copy_env_files is True
            assert settings.env_file_patterns == [".env", ".env.prod"]

    def test_setup_env_files_config_disabled(self) -> None:
        """Test disabling env files."""
        settings = MagicMock()

        with patch("click.confirm", return_value=False):  # Disable
            _setup_env_files_config(settings)

            assert settings.copy_env_files is False


class TestSetupGitConfig:
    """Test git configuration in setup wizard."""

    def test_setup_git_config_exists(self) -> None:
        """Test that _setup_git_config function exists."""
        assert callable(_setup_git_config)


class TestShowSetupSummary:
    """Test setup summary display."""

    def test_show_setup_summary_tmux(self) -> None:
        """Test showing setup summary for tmux launcher."""
        settings = MagicMock()
        settings.launcher = "tmux"
        settings.ai_tool = "claude"
        settings.editor_command = "code"
        settings.launchers.tmux.session = "dev"
        settings.launchers.tmux.auto_attach = True
        settings.copy_env_files = True
        settings.env_file_patterns = [".env", ".env.local"]

        # Should not raise exception
        _show_setup_summary(settings)

    def test_show_setup_summary_terminal(self) -> None:
        """Test showing setup summary for terminal launcher."""
        settings = MagicMock()
        settings.launcher = "terminal"
        settings.ai_tool = "claude"
        settings.editor_command = None
        settings.copy_env_files = False

        # Should not raise exception
        _show_setup_summary(settings)


class TestRunSetupWizard:
    """Test the complete setup wizard."""

    def test_run_setup_wizard_complete(self) -> None:
        """Test running the complete setup wizard."""
        with (
            patch("lets.cli._setup_launcher_config") as mock_launcher,
            patch("lets.cli._setup_ai_tool_config") as mock_ai,
            patch("lets.cli._setup_editor_config") as mock_editor,
            patch("lets.cli._setup_worktree_config") as mock_worktree,
            patch("lets.cli._setup_env_files_config") as mock_env,
            patch("lets.cli._setup_git_config") as mock_git,
            patch("lets.cli._show_setup_summary") as mock_summary,
        ):
            result = run_setup_wizard()

            # Verify all config steps were called
            mock_launcher.assert_called_once()
            mock_ai.assert_called_once()
            mock_editor.assert_called_once()
            mock_worktree.assert_called_once()
            mock_env.assert_called_once()
            mock_git.assert_called_once()
            mock_summary.assert_called_once()

            # Should return LetsSettings instance
            assert result is not None


class TestCheckAndRunSetupWizard:
    """Test the setup wizard check and run logic."""

    def test_check_and_run_setup_wizard_config_exists(self) -> None:
        """Test when configuration file already exists."""
        with patch("lets.cli.LetsSettings") as mock_settings:
            mock_config_file = MagicMock()
            mock_config_file.exists.return_value = True
            mock_settings.get_config_file.return_value = mock_config_file

            result = check_and_run_setup_wizard()

            assert result is False

    def test_check_and_run_setup_wizard_no_config(self) -> None:
        """Test when no configuration file exists."""
        with patch("lets.cli.LetsSettings") as mock_settings:
            mock_config_file = MagicMock()
            mock_config_file.exists.return_value = False
            mock_config_file.parent.mkdir = MagicMock()
            mock_settings.get_config_file.return_value = mock_config_file

            mock_settings_instance = MagicMock()

            with patch("lets.cli.run_setup_wizard") as mock_wizard:
                mock_wizard.return_value = mock_settings_instance

                result = check_and_run_setup_wizard()

                assert result is True
                mock_wizard.assert_called_once()
                mock_config_file.parent.mkdir.assert_called_once_with(
                    parents=True, exist_ok=True
                )
                mock_settings_instance.save.assert_called_once()


class TestPrintWorkspaceSummary:
    """Test workspace summary printing."""

    def test_print_workspace_summary(self) -> None:
        """Test printing workspace summary."""
        worktree_path = Path("/test/worktree")
        branch_name = "test-branch"
        launcher_name = "tmux"
        session = "dev"

        # Should not raise exception
        print_workspace_summary(worktree_path, branch_name, launcher_name, session)


class TestHandleLauncherAttachment:
    """Test launcher attachment handling."""

    def test_handle_launcher_attachment_tmux(self) -> None:
        """Test handling tmux launcher attachment."""
        launcher_name = "tmux"
        worktree_path = Path("/test/worktree")
        branch_name = "test-branch"
        session = "test-session"

        with patch("lets.cli.LetsSettings") as mock_settings:
            mock_settings_instance = MagicMock()
            mock_settings.load.return_value = mock_settings_instance

            with patch("lets.cli.get_launcher") as mock_get_launcher:
                mock_launcher = MagicMock()
                mock_get_launcher.return_value = mock_launcher

                handle_launcher_attachment(
                    launcher_name, worktree_path, branch_name, session
                )

                mock_get_launcher.assert_called_once()
                mock_launcher.handle_attachment.assert_called_once_with(
                    worktree_path, branch_name
                )

    def test_handle_launcher_attachment_terminal(self) -> None:
        """Test handling terminal launcher attachment."""
        launcher_name = "terminal"
        worktree_path = Path("/test/worktree")
        branch_name = "test-branch"
        session = "test-session"

        with patch("lets.cli.LetsSettings") as mock_settings:
            mock_settings_instance = MagicMock()
            mock_settings.load.return_value = mock_settings_instance

            with patch("lets.cli.get_launcher") as mock_get_launcher:
                mock_launcher = MagicMock()
                mock_get_launcher.return_value = mock_launcher

                handle_launcher_attachment(
                    launcher_name, worktree_path, branch_name, session
                )

                mock_launcher.handle_attachment.assert_called_once_with(
                    worktree_path, branch_name
                )
