"""Comprehensive tests for setup wizard components to achieve 100% coverage."""

from pathlib import Path
from unittest.mock import MagicMock, patch

from lets.cli import (
    _setup_ai_tool_config,
    _setup_editor_config,
    _setup_git_config,
    _setup_worktree_config,
    _validate_command_exists,
)


class TestSetupAiToolConfigComprehensive:
    """Comprehensive tests for AI tool configuration."""

    def test_setup_ai_tool_config_command_exists(self) -> None:
        """Test AI tool setup when command is available."""
        settings = MagicMock()

        with (
            patch("click.prompt", return_value="claude"),
            patch("lets.cli._validate_command_exists", return_value=True),
        ):
            _setup_ai_tool_config(settings)

            assert settings.ai_tool == "claude"

    def test_setup_ai_tool_config_command_not_exists(self) -> None:
        """Test AI tool setup when command is not available."""
        settings = MagicMock()

        with (
            patch("click.prompt", return_value="nonexistent-ai"),
            patch("lets.cli._validate_command_exists", return_value=False),
        ):
            _setup_ai_tool_config(settings)

            assert settings.ai_tool == "nonexistent-ai"


class TestSetupEditorConfigComprehensive:
    """Comprehensive tests for editor configuration."""

    def test_setup_editor_config_with_detected_accept(self) -> None:
        """Test editor setup with detected editor accepted."""
        settings = MagicMock()

        with (
            patch.dict("os.environ", {"EDITOR": "code"}),
            patch("click.confirm", return_value=True),
        ):
            _setup_editor_config(settings)

            assert settings.editor_command == "code"

    def test_setup_editor_config_with_detected_decline_custom_valid(self) -> None:
        """Test editor setup declining detected, providing valid custom."""
        settings = MagicMock()

        with (
            patch.dict("os.environ", {"EDITOR": "vim"}),
            patch("click.confirm", return_value=False),
            patch("click.prompt", return_value="emacs"),
            patch("lets.cli._validate_command_exists", return_value=True),
        ):
            _setup_editor_config(settings)

            assert settings.editor_command == "emacs"

    def test_setup_editor_config_with_detected_decline_custom_invalid(self) -> None:
        """Test editor setup declining detected, providing invalid custom."""
        settings = MagicMock()

        with (
            patch.dict("os.environ", {"EDITOR": "vim"}),
            patch("click.confirm", return_value=False),
            patch("click.prompt", return_value="nonexistent-editor"),
            patch("lets.cli._validate_command_exists", return_value=False),
        ):
            _setup_editor_config(settings)

            assert settings.editor_command == "nonexistent-editor"

    def test_setup_editor_config_no_detected_with_custom(self) -> None:
        """Test editor setup with no detected editor, custom provided."""
        settings = MagicMock()

        with (
            patch.dict("os.environ", {}, clear=True),
            patch("click.prompt", return_value="nano"),
        ):
            _setup_editor_config(settings)

            assert settings.editor_command == "nano"

    def test_setup_editor_config_no_detected_no_custom(self) -> None:
        """Test editor setup with no detected editor, no custom provided."""
        settings = MagicMock()

        with (
            patch.dict("os.environ", {}, clear=True),
            patch("click.prompt", return_value=""),
        ):
            _setup_editor_config(settings)

                # Function should complete without setting editor_command to empty
                # string


class TestSetupWorktreeConfigComprehensive:
    """Comprehensive tests for worktree configuration."""

    def test_setup_worktree_config_use_default(self) -> None:
        """Test worktree configuration using default directory."""
        settings = MagicMock()

        with (
            patch("click.confirm", return_value=True),
            patch("lets.cli.xdg_data_home") as mock_xdg,
        ):
            mock_xdg.return_value = Path("/home/user/.local/share")
            _setup_worktree_config(settings)

    def test_setup_worktree_config_custom_dir_exists(self) -> None:
        """Test worktree configuration with custom directory that exists."""
        settings = MagicMock()

        with (
            patch("click.confirm", return_value=False),
            patch("click.prompt", return_value="/custom/worktree"),
            patch("pathlib.Path.expanduser") as mock_expand,
        ):
            mock_path = MagicMock()
            mock_path.parent.exists.return_value = True
            mock_expand.return_value = mock_path

            _setup_worktree_config(settings)

            assert settings.worktree_base_dir == str(mock_path)

    def test_setup_worktree_config_custom_dir_create_confirmed(self) -> None:
        """Test worktree configuration creating custom directory when confirmed."""
        settings = MagicMock()

        with (
            patch("click.confirm", side_effect=[False, True]),  # Don't use default,
            # create dir
            patch("click.prompt", return_value="/custom/worktree"),
            patch("pathlib.Path.expanduser") as mock_expand,
        ):
            mock_path = MagicMock()
            mock_path.parent.exists.return_value = False  # Parent doesn't exist
            mock_expand.return_value = mock_path

            _setup_worktree_config(settings)

            assert settings.worktree_base_dir == str(mock_path)

    def test_setup_worktree_config_custom_dir_create_denied(self) -> None:
        """Test worktree configuration when directory creation is denied."""
        settings = MagicMock()

        with (
            patch("click.confirm", side_effect=[False, False]),  # Don't use default,
            # don't create
            patch("click.prompt", return_value="/custom/worktree"),
            patch("pathlib.Path.expanduser") as mock_expand,
        ):
            mock_path = MagicMock()
            mock_path.parent.exists.return_value = False
            mock_expand.return_value = mock_path

            _setup_worktree_config(settings)


class TestSetupGitConfigComprehensive:
    """Comprehensive tests for git configuration."""

    def test_setup_git_config_auto_detect(self) -> None:
        """Test git configuration with auto-detect enabled."""
        settings = MagicMock()

        with patch("click.confirm", return_value=True):
            _setup_git_config(settings)

    def test_setup_git_config_custom_branch(self) -> None:
        """Test git configuration with custom base branch."""
        settings = MagicMock()

        with (
            patch("click.confirm", return_value=False),
            patch("click.prompt", return_value="develop"),
        ):
            _setup_git_config(settings)

            assert settings.default_base_branch == "develop"


class TestValidateCommandExistsComprehensive:
    """Comprehensive tests for command validation."""

    def test_validate_command_exists_with_path(self) -> None:
        """Test command validation with full path."""
        with patch("shutil.which", return_value="/usr/bin/git"):
            result = _validate_command_exists("git")
            assert result is True

    def test_validate_command_exists_not_found(self) -> None:
        """Test command validation when command not found."""
        with patch("shutil.which", return_value=None):
            result = _validate_command_exists("nonexistent-command")
            assert result is False

    def test_validate_command_exists_empty_command(self) -> None:
        """Test command validation with empty command."""
        result = _validate_command_exists("")
        assert result is False

    def test_validate_command_exists_whitespace_command(self) -> None:
        """Test command validation with whitespace command."""
        result = _validate_command_exists("   ")
        assert result is False


class TestSetupWizardEdgeCases:
    """Test edge cases in setup wizard functions."""

    def test_setup_editor_config_with_detected_decline_empty_custom(self) -> None:
        """Test editor setup declining detected, providing empty custom."""
        settings = MagicMock()

        with (
            patch.dict("os.environ", {"EDITOR": "vim"}),
            patch("click.confirm", return_value=False),
            patch("click.prompt", return_value=""),
        ):
            _setup_editor_config(settings)

                    # Function should complete successfully

    def test_setup_ai_tool_config_default_value(self) -> None:
        """Test AI tool setup uses default value correctly."""
        settings = MagicMock()

        with (
            patch("click.prompt", return_value="claude"),  # Default value
            patch("lets.cli._validate_command_exists", return_value=True),
        ):
            _setup_ai_tool_config(settings)

            assert settings.ai_tool == "claude"

    def test_editor_config_custom_command_with_args(self) -> None:
        """Test editor config with custom command that has arguments."""
        settings = MagicMock()

        with (
            patch.dict("os.environ", {}, clear=True),
            patch("click.prompt", return_value="code --wait"),
        ):
            _setup_editor_config(settings)

            assert settings.editor_command == "code --wait"

    def test_ai_tool_config_different_commands(self) -> None:
        """Test AI tool config with different command names."""
        settings = MagicMock()

        # Test with different AI tools
        for ai_tool in ["chatgpt", "copilot", "claude"]:
            with (
                patch("click.prompt", return_value=ai_tool),
                patch("lets.cli._validate_command_exists", return_value=True),
            ):
                _setup_ai_tool_config(settings)

                assert settings.ai_tool == ai_tool
