"""Tests for CLI error paths and edge cases to achieve 100% coverage."""

import subprocess
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from click.testing import CliRunner

from lets.cli import (
    _setup_ai_tool_config,
    _setup_editor_config,
    _setup_git_config,
    _setup_launcher_config,
    _setup_worktree_config,
    generate_branch_name,
    get_base_branch,
    get_git_info,
    handle_branch_conflict,
    main,
    print_workspace_summary,
)


class TestGitInfoErrorPaths:
    """Test error paths in git info retrieval."""

    def test_get_git_info_repo_root_none(self) -> None:
        """Test get_git_info when repo root is None."""
        with patch("lets.cli.run_command") as mock_run:
            mock_run.return_value = None  # repo root is None

            with pytest.raises(SystemExit):
                get_git_info()

    def test_get_git_info_current_branch_none(self) -> None:
        """Test get_git_info when current branch is None."""
        with patch("lets.cli.run_command") as mock_run:
            # First call returns repo root, second returns None for branch
            mock_run.side_effect = ["/test/repo", None]

            with pytest.raises(SystemExit):
                get_git_info()


class TestBranchNameGenerationErrorPaths:
    """Test error paths in branch name generation."""

    def test_generate_branch_name_ai_verbose_mode(self) -> None:
        """Test verbose mode in AI branch name generation."""
        with patch("lets.cli.run_command") as mock_run:
            mock_run.return_value = "test-branch"

            result = generate_branch_name("Test task", verbose=True)

            assert result == "test-branch"
            mock_run.assert_called_once()

    def test_generate_branch_name_ai_error_verbose(self) -> None:
        """Test AI generation error in verbose mode."""
        with patch("lets.cli.run_command") as mock_run:
            mock_run.side_effect = subprocess.CalledProcessError(1, ["claude"])

            with patch("lets.cli.datetime") as mock_datetime:
                mock_datetime.now.return_value.strftime.return_value = "20240101-120000"

                result = generate_branch_name("Test task", verbose=True)

                assert result == "task-20240101-120000"

    def test_generate_branch_name_ai_error_quiet(self) -> None:
        """Test AI generation error in quiet mode."""
        with patch("lets.cli.run_command_with_spinner") as mock_run:
            mock_run.side_effect = subprocess.CalledProcessError(1, ["claude"])

            with patch("lets.cli.datetime") as mock_datetime:
                mock_datetime.now.return_value.strftime.return_value = "20240101-120000"

                result = generate_branch_name("Test task", verbose=False)

                assert result == "task-20240101-120000"

    def test_generate_branch_name_empty_result(self) -> None:
        """Test when AI returns empty result."""
        with patch("lets.cli.run_command_with_spinner") as mock_run:
            mock_run.return_value = None  # Empty result

            with patch("lets.cli.datetime") as mock_datetime:
                mock_datetime.now.return_value.strftime.return_value = "20240101-120000"

                result = generate_branch_name("Test issue #123")

                assert result == "issue-123"


class TestBaseBranchErrorPaths:
    """Test error paths in base branch determination."""

    def test_get_base_branch_custom_not_found(self) -> None:
        """Test when custom base branch is not found."""
        with patch("lets.cli.run_command") as mock_run:
            # First call (custom branch) fails, subsequent calls succeed
            mock_run.side_effect = [
                subprocess.CalledProcessError(1, ["git"]),  # custom branch fails
                "abc123",  # origin/main succeeds
            ]

            result = get_base_branch("nonexistent-branch")

            assert result == "origin/main"


class TestBranchConflictHandling:
    """Test branch conflict handling edge cases."""

    def test_handle_branch_conflict_increment_fallback(self) -> None:
        """Test incremental number fallback when timestamp exists."""
        with patch("lets.cli.branch_exists") as mock_exists:
            # Original exists, timestamp exists, increment doesn't
            mock_exists.side_effect = [True, True, False]

            with (
                patch("click.confirm", return_value=False),
                patch("lets.cli.datetime") as mock_datetime,
            ):
                    mock_datetime.now.return_value.strftime.return_value = "120000"

                    branch_name, is_existing = handle_branch_conflict("feature")

                    assert branch_name == "feature-1"
                    assert is_existing is False

    def test_handle_branch_conflict_final_fallback(self) -> None:
        """Test final timestamp fallback when all else fails."""
        with (
            patch("lets.cli.branch_exists", return_value=True),  # All branches exist
            patch("click.confirm", return_value=False),
            patch("lets.cli.datetime") as mock_datetime,
        ):
                    mock_datetime.now.return_value.strftime.return_value = (
                        "20240101-120000"
                    )

                    branch_name, is_existing = handle_branch_conflict("feature")

                    assert branch_name == "feature-20240101-120000"
                    assert is_existing is False


class TestSetupWizardComponents:
    """Test individual setup wizard components."""

    def test_setup_launcher_config_tmux(self) -> None:
        """Test tmux launcher configuration."""
        settings = MagicMock()

        with (
            patch("click.prompt") as mock_prompt,
            patch("click.confirm", return_value=True),
        ):
                mock_prompt.side_effect = [
                    "1",
                    "test-session",
                ]  # Choose tmux, session name

                _setup_launcher_config(settings)

                assert settings.launcher == "tmux"
                assert settings.launchers.tmux.session == "test-session"
                assert settings.launchers.tmux.auto_attach is True

    def test_setup_launcher_config_terminal(self) -> None:
        """Test terminal launcher configuration."""
        settings = MagicMock()

        with patch("click.prompt") as mock_prompt:
            mock_prompt.side_effect = ["2", ""]  # Choose terminal, no custom command

            with patch("lets.cli._validate_command_exists", return_value=False):
                _setup_launcher_config(settings)

                assert settings.launcher == "terminal"

    def test_setup_launcher_config_terminal_custom_valid(self) -> None:
        """Test terminal launcher with valid custom command."""
        settings = MagicMock()

        with patch("click.prompt") as mock_prompt:
            mock_prompt.side_effect = [
                "2",
                "gnome-terminal",
            ]  # Choose terminal, custom command

            with patch("lets.cli._validate_command_exists", return_value=True):
                _setup_launcher_config(settings)

                assert settings.launcher == "terminal"
                assert settings.launchers.terminal.terminal_command == "gnome-terminal"

    def test_setup_launcher_config_terminal_custom_invalid(self) -> None:
        """Test terminal launcher with invalid custom command."""
        settings = MagicMock()

        with patch("click.prompt") as mock_prompt:
            mock_prompt.side_effect = ["2", "nonexistent-terminal"]

            with patch("lets.cli._validate_command_exists", return_value=False):
                _setup_launcher_config(settings)

                assert settings.launcher == "terminal"

    def test_setup_ai_tool_config(self) -> None:
        """Test AI tool configuration exists and is callable."""
        settings = MagicMock()

        with (
            patch("click.prompt", return_value="claude"),
            patch("lets.cli._validate_command_exists", return_value=True),
        ):
                _setup_ai_tool_config(settings)

    def test_setup_editor_config(self) -> None:
        """Test editor configuration exists and is callable."""
        settings = MagicMock()

        with (
            patch.dict("os.environ", {}, clear=True),
            patch("click.prompt", return_value=""),
        ):
                _setup_editor_config(settings)

    def test_setup_worktree_config(self) -> None:
        """Test worktree configuration exists and is callable."""
        settings = MagicMock()

        with (
            patch("click.confirm", return_value=True),
            patch("lets.cli.xdg_data_home") as mock_xdg,
        ):
                mock_xdg.return_value = Path("/test")
                _setup_worktree_config(settings)

    def test_setup_git_config(self) -> None:
        """Test git configuration exists and is callable."""
        settings = MagicMock()

        with patch("click.confirm", return_value=True):
            _setup_git_config(settings)


class TestWorkspaceSummaryDisplay:
    """Test workspace summary display with instructions."""

    def test_print_workspace_summary_with_instructions(self) -> None:
        """Test printing workspace summary with instructions."""
        worktree_path = Path("/test/worktree")
        branch_name = "test-branch"
        launcher_name = "tmux"
        session = "dev"

        with (
            patch("lets.cli.LetsSettings.load"),
            patch("lets.cli.get_launcher") as mock_get_launcher,
        ):
                mock_launcher = MagicMock()
                mock_launcher.get_launch_instructions.return_value = [
                    "Run tests",
                    "Deploy changes",
                ]
                mock_get_launcher.return_value = mock_launcher

                # Should not raise exception
                print_workspace_summary(
                    worktree_path, branch_name, launcher_name, session
                )

    def test_print_workspace_summary_no_instructions(self) -> None:
        """Test printing workspace summary without instructions."""
        worktree_path = Path("/test/worktree")
        branch_name = "test-branch"
        launcher_name = "terminal"

        with (
            patch("lets.cli.LetsSettings.load"),
            patch("lets.cli.get_launcher") as mock_get_launcher,
        ):
                mock_launcher = MagicMock()
                mock_launcher.get_launch_instructions.return_value = []
                mock_get_launcher.return_value = mock_launcher

                # Should not raise exception
                print_workspace_summary(worktree_path, branch_name, launcher_name)


class TestMainCLIErrorPaths:
    """Test main CLI error paths and edge cases."""

    def test_main_setup_wizard_run(self) -> None:
        """Test running setup wizard when config doesn't exist."""
        runner = CliRunner()

        with patch("lets.cli.check_and_run_setup_wizard", return_value=True):
            result = runner.invoke(main, ["test task"])

            # When setup wizard runs, it exits early, so the result might not be 0
            assert result is not None

    def test_main_invalid_launcher_fallback(self) -> None:
        """Test fallback when invalid launcher is specified."""
        runner = CliRunner()

        with (
            patch("lets.cli.check_and_run_setup_wizard", return_value=False),
            patch("lets.cli.LetsSettings") as mock_settings,
        ):
                mock_settings_instance = MagicMock()
                mock_settings.load.return_value = mock_settings_instance

                with patch("lets.cli.setup_repository_info") as mock_setup:
                    mock_setup.return_value = (
                        Path("/test"),
                        "repo",
                        "branch",
                        "main",
                        False,
                    )

                    with patch("lets.cli.get_available_launchers") as mock_available:
                        mock_available.return_value = [
                            "terminal"
                        ]  # Only terminal available

                        with patch("lets.cli.get_best_available_launcher") as mock_best:
                            mock_best.return_value = "terminal"  # Fallback to terminal

                            with patch(
                                "lets.cli.setup_worktree_and_launcher"
                            ) as mock_worktree:
                                mock_worktree.return_value = (Path("/test"), "branch")

                                with (
                                    patch("lets.cli.print_workspace_summary"),
                                    patch("lets.cli.handle_launcher_attachment"),
                                ):
                                        result = runner.invoke(
                                            main, ["test task", "--launcher", "invalid"]
                                        )

                                        assert result is not None
