"""Tests for the main CLI module."""

import subprocess
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from click.testing import CliRunner

from lets.cli import (
    branch_exists,
    generate_branch_name,
    get_base_branch,
    get_git_info,
    get_worktree_base_dir,
    handle_branch_conflict,
    main,
    run_command,
    run_command_with_spinner,
)


class TestRunCommand:
    """Test command execution functions."""

    def test_run_command_success(self) -> None:
        """Test successful command execution."""
        with patch("subprocess.run") as mock_run:
            mock_run.return_value.stdout = "output\n"
            result = run_command(["echo", "test"], capture_output=True)
            assert result == "output"

    def test_run_command_no_capture(self) -> None:
        """Test command execution without capturing output."""
        with patch("subprocess.run"):
            result = run_command(["echo", "test"])
            assert result is None

    def test_run_command_failure(self) -> None:
        """Test command execution failure."""
        with patch("subprocess.run") as mock_run:
            mock_run.side_effect = subprocess.CalledProcessError(1, ["cmd"])
            with pytest.raises(subprocess.CalledProcessError):
                run_command(["false"], check=True)

    def test_run_command_failure_no_check(self) -> None:
        """Test command execution failure with check=False."""
        with patch("subprocess.run") as mock_run:
            mock_run.side_effect = subprocess.CalledProcessError(1, ["cmd"])
            result = run_command(["false"], check=False)
            assert result is None

    def test_run_command_with_spinner(self) -> None:
        """Test command execution with spinner."""
        with patch("lets.cli.run_command") as mock_run:
            mock_run.return_value = "output"
            result = run_command_with_spinner(
                ["echo", "test"], "Testing...", capture_output=True
            )
            assert result == "output"
            mock_run.assert_called_once_with(
                ["echo", "test"], capture_output=True, check=True, cwd=None
            )


class TestGitOperations:
    """Test git-related functions."""

    def test_get_git_info_success(self, mock_git_repo: Path) -> None:
        """Test successful git info retrieval."""
        repo_root, repo_name, current_branch = get_git_info()
        assert repo_root == mock_git_repo
        assert repo_name == "test-repo"
        assert current_branch == "main"

    def test_get_git_info_not_git_repo(self) -> None:
        """Test git info when not in a git repository."""
        with patch("lets.cli.run_command") as mock_run:
            mock_run.side_effect = subprocess.CalledProcessError(1, ["git"])
            with pytest.raises(SystemExit):
                get_git_info()

    def test_branch_exists_local(self) -> None:
        """Test branch existence check for local branch."""
        with patch("lets.cli.run_command") as mock_run:
            mock_run.return_value = "abc123"
            assert branch_exists("main") is True

    def test_branch_exists_remote(self) -> None:
        """Test branch existence check for remote branch."""
        with patch("lets.cli.run_command") as mock_run:
            # First call (local) fails, second call (remote) succeeds
            mock_run.side_effect = [subprocess.CalledProcessError(1, ["git"]), "abc123"]
            assert branch_exists("feature-branch") is True

    def test_branch_does_not_exist(self) -> None:
        """Test branch existence check when branch doesn't exist."""
        with patch("lets.cli.run_command") as mock_run:
            mock_run.side_effect = subprocess.CalledProcessError(1, ["git"])
            assert branch_exists("nonexistent") is False

    def test_get_base_branch_custom(self) -> None:
        """Test getting base branch with custom branch."""
        with patch("lets.cli.run_command") as mock_run:
            mock_run.return_value = "abc123"
            result = get_base_branch("custom-main")
            assert result == "custom-main"

    def test_get_base_branch_auto_detect_main(self) -> None:
        """Test auto-detecting main as base branch."""
        with patch("lets.cli.run_command") as mock_run:
            mock_run.return_value = "abc123"
            result = get_base_branch()
            assert result == "origin/main"

    def test_get_base_branch_fallback_head(self) -> None:
        """Test falling back to HEAD when no standard branches found."""
        with patch("lets.cli.run_command") as mock_run:
            mock_run.side_effect = subprocess.CalledProcessError(1, ["git"])
            result = get_base_branch()
            assert result == "HEAD"


class TestBranchNaming:
    """Test branch name generation and conflict handling."""

    def test_generate_branch_name_success(self) -> None:
        """Test successful AI branch name generation."""
        with patch("lets.cli.run_command_with_spinner") as mock_run:
            mock_run.return_value = "fix-auth-issue"
            result = generate_branch_name("Fix authentication issue")
            assert result == "fix-auth-issue"

    def test_generate_branch_name_cleanup(self) -> None:
        """Test branch name cleanup from AI output."""
        with patch("lets.cli.run_command_with_spinner") as mock_run:
            mock_run.return_value = "Fix-Auth@Issue!123"
            result = generate_branch_name("Fix authentication issue")
            assert result == "fix-authissue123"

    def test_generate_branch_name_fallback_issue(self) -> None:
        """Test fallback to issue number extraction."""
        with patch("lets.cli.run_command_with_spinner") as mock_run:
            mock_run.return_value = "x"  # Too short
            result = generate_branch_name("Fix issue #123")
            assert result == "issue-123"

    def test_generate_branch_name_fallback_timestamp(self) -> None:
        """Test fallback to timestamp."""
        with (
            patch("lets.cli.run_command_with_spinner") as mock_run,
            patch("lets.cli.datetime") as mock_datetime,
        ):
            mock_run.return_value = "x"  # Too short
            mock_datetime.now.return_value.strftime.return_value = "20240101-120000"
            result = generate_branch_name("Some task")
            assert result == "task-20240101-120000"

    def test_handle_branch_conflict_no_conflict(self) -> None:
        """Test handling branch name when no conflict exists."""
        with patch("lets.cli.branch_exists", return_value=False):
            branch_name, is_existing = handle_branch_conflict("new-feature")
            assert branch_name == "new-feature"
            assert is_existing is False

    def test_handle_branch_conflict_use_existing(self) -> None:
        """Test choosing to use existing branch."""
        with (
            patch("lets.cli.branch_exists", return_value=True),
            patch("click.confirm", return_value=True),
        ):
            branch_name, is_existing = handle_branch_conflict("existing-feature")
            assert branch_name == "existing-feature"
            assert is_existing is True

    def test_handle_branch_conflict_generate_new(self) -> None:
        """Test generating new branch name when conflict exists."""
        with patch("lets.cli.branch_exists") as mock_exists:
            # First branch exists, timestamp variant doesn't
            mock_exists.side_effect = [True, False]
            with (
                patch("click.confirm", return_value=False),
                patch("lets.cli.datetime") as mock_datetime,
            ):
                mock_datetime.now.return_value.strftime.return_value = "120000"
                branch_name, is_existing = handle_branch_conflict("feature")
                assert branch_name == "feature-120000"
                assert is_existing is False


class TestWorktreeConfig:
    """Test worktree configuration functions."""

    def test_get_worktree_base_dir_custom(self) -> None:
        """Test getting custom worktree base directory."""
        result = get_worktree_base_dir("/custom/path")
        assert result == Path("/custom/path")

    def test_get_worktree_base_dir_env_var(self) -> None:
        """Test getting worktree base directory from environment variable."""
        with patch.dict("os.environ", {"LETS_WORKTREE_DIR": "/env/path"}):
            result = get_worktree_base_dir()
            assert result == Path("/env/path")

    def test_get_worktree_base_dir_default(self) -> None:
        """Test getting default worktree base directory."""
        with (
            patch.dict("os.environ", {}, clear=True),
            patch("lets.cli.xdg_data_home") as mock_xdg,
        ):
            mock_xdg.return_value = Path("/home/user/.local/share")
            result = get_worktree_base_dir()
            assert result == Path("/home/user/.local/share/lets/worktrees")


class TestCLICommand:
    """Test the main CLI command."""

    def test_main_requires_task(self) -> None:
        """Test that main command requires a task argument."""
        runner = CliRunner()
        with patch("lets.cli.check_and_run_setup_wizard", return_value=False):
            result = runner.invoke(main, [])
            assert result.exit_code == 1
            assert "TASK argument is required" in result.output

    def test_main_setup_flag(self) -> None:
        """Test the --setup flag functionality."""
        runner = CliRunner()
        with patch("lets.cli.LetsSettings") as mock_settings:
            mock_config_file = MagicMock()
            mock_config_file.exists.return_value = False
            mock_config_file.parent.mkdir = MagicMock()
            mock_settings.get_config_file.return_value = mock_config_file
            with patch("lets.cli.run_setup_wizard") as mock_wizard:
                mock_settings_instance = MagicMock()
                mock_wizard.return_value = mock_settings_instance
                result = runner.invoke(main, ["--setup"])
                assert result.exit_code == 0
                mock_wizard.assert_called_once()

    def test_main_dry_run(self) -> None:
        """Test the --dry-run flag functionality."""
        runner = CliRunner()
        with (
            patch("lets.cli.check_and_run_setup_wizard", return_value=False),
            patch("lets.cli.LetsSettings") as mock_settings,
        ):
            mock_settings_instance = MagicMock()
            mock_settings_instance.ai_tool = "claude"
            mock_settings_instance.copy_env_files = True
            mock_settings_instance.env_file_patterns = [".env"]
            mock_settings_instance.worktree_base_dir = None
            mock_settings_instance.default_base_branch = None
            mock_settings_instance.launcher = "tmux"
            mock_settings.load.return_value = mock_settings_instance

            with (
                patch("lets.cli.setup_repository_info") as mock_setup,
                patch("lets.cli.get_best_available_launcher") as mock_launcher,
                patch("lets.cli.get_available_launchers") as mock_available,
                patch("lets.cli.get_worktree_base_dir") as mock_base_dir,
                patch("lets.cli.get_base_branch") as mock_base_branch,
            ):
                mock_setup.return_value = (
                    Path("/test"),
                    "repo",
                    "branch",
                    "main",
                    False,
                )
                mock_launcher.return_value = "tmux"
                mock_available.return_value = ["tmux"]
                mock_base_dir.return_value = Path("/test/worktrees")
                mock_base_branch.return_value = "main"
                result = runner.invoke(
                    main, ["test task", "--dry-run"]
                )
                assert result.exit_code == 0
                assert "DRY RUN MODE" in result.output
                assert "Would create worktree" in result.output

    @pytest.mark.parametrize("verbose", [True, False])
    def test_main_verbose_flag(self, verbose: bool) -> None:  # noqa: FBT001
        """Test the --verbose flag functionality."""
        runner = CliRunner()
        args = ["test task"]
        if verbose:
            args.append("--verbose")

        with (
            patch("lets.cli.check_and_run_setup_wizard", return_value=False),
            patch("lets.cli.LetsSettings"),
            patch("lets.cli.setup_repository_info") as mock_setup,
            patch("lets.cli.get_best_available_launcher") as mock_launcher,
            patch("lets.cli.get_available_launchers") as mock_available,
            patch("lets.cli.setup_worktree_and_launcher") as mock_worktree,
            patch("lets.cli.print_workspace_summary"),
            patch("lets.cli.handle_launcher_attachment"),
        ):
            mock_setup.return_value = (
                Path("/test"),
                "repo",
                "branch",
                "main",
                False,
            )
            mock_launcher.return_value = "tmux"
            mock_available.return_value = ["tmux"]
            mock_worktree.return_value = (Path("/test"), "branch")
            runner.invoke(main, args)
            # Check that verbose flag was passed to setup_repository_info
            mock_setup.assert_called_once()
            call_args = mock_setup.call_args
            assert call_args.kwargs["verbose"] == verbose

    def test_main_custom_worktree_dir(self) -> None:
        """Test the --worktree-dir flag functionality."""
        runner = CliRunner()

        with (
            patch("lets.cli.check_and_run_setup_wizard", return_value=False),
            patch("lets.cli.LetsSettings") as mock_settings,
            patch("lets.cli.setup_repository_info") as mock_setup,
            patch("lets.cli.get_best_available_launcher") as mock_launcher,
            patch("lets.cli.get_available_launchers") as mock_available,
            patch("lets.cli.setup_worktree_and_launcher") as mock_worktree,
            patch("lets.cli.print_workspace_summary"),
            patch("lets.cli.handle_launcher_attachment"),
        ):
            mock_settings_instance = MagicMock()
            mock_settings.load.return_value = mock_settings_instance

            mock_setup.return_value = (
                Path("/test"),
                "repo",
                "branch",
                "main",
                False,
            )
            mock_launcher.return_value = "tmux"
            mock_available.return_value = ["tmux"]
            mock_worktree.return_value = (Path("/test"), "branch")
            result = runner.invoke(
                main,
                [
                    "test task",
                    "--worktree-dir",
                    "/custom/worktree",
                ],
            )

            # Test runs without crashing
            assert result is not None

    def test_main_custom_base_branch(self) -> None:
        """Test the --base-branch flag functionality."""
        runner = CliRunner()

        with (
            patch("lets.cli.check_and_run_setup_wizard", return_value=False),
            patch("lets.cli.LetsSettings") as mock_settings,
            patch("lets.cli.setup_repository_info") as mock_setup,
            patch("lets.cli.get_best_available_launcher") as mock_launcher,
            patch("lets.cli.get_available_launchers") as mock_available,
            patch("lets.cli.setup_worktree_and_launcher") as mock_worktree,
            patch("lets.cli.print_workspace_summary"),
            patch("lets.cli.handle_launcher_attachment"),
        ):
            mock_settings_instance = MagicMock()
            mock_settings.load.return_value = mock_settings_instance

            mock_setup.return_value = (
                Path("/test"),
                "repo",
                "branch",
                "main",
                False,
            )
            mock_launcher.return_value = "tmux"
            mock_available.return_value = ["tmux"]
            mock_worktree.return_value = (Path("/test"), "branch")
            result = runner.invoke(
                main,
                ["test task", "--base-branch", "develop"],
            )

            assert result is not None

    def test_main_custom_env_files(self) -> None:
        """Test the --env-files flag functionality."""
        runner = CliRunner()

        with (
            patch("lets.cli.check_and_run_setup_wizard", return_value=False),
            patch("lets.cli.LetsSettings") as mock_settings,
            patch("lets.cli.setup_repository_info") as mock_setup,
            patch("lets.cli.get_best_available_launcher") as mock_launcher,
            patch("lets.cli.get_available_launchers") as mock_available,
            patch("lets.cli.setup_worktree_and_launcher") as mock_worktree,
            patch("lets.cli.print_workspace_summary"),
            patch("lets.cli.handle_launcher_attachment"),
        ):
            mock_settings_instance = MagicMock()
            mock_settings.load.return_value = mock_settings_instance

            mock_setup.return_value = (
                Path("/test"),
                "repo",
                "branch",
                "main",
                False,
            )
            mock_launcher.return_value = "tmux"
            mock_available.return_value = ["tmux"]
            mock_worktree.return_value = (Path("/test"), "branch")
            result = runner.invoke(
                main,
                [
                    "test task",
                    "--env-files",
                    ".env.test",
                    "--env-files",
                    ".env.staging",
                ],
            )

            assert result is not None

    def test_main_no_copy_env(self) -> None:
        """Test the --no-copy-env flag functionality."""
        runner = CliRunner()

        with (
            patch("lets.cli.check_and_run_setup_wizard", return_value=False),
            patch("lets.cli.LetsSettings") as mock_settings,
            patch("lets.cli.setup_repository_info") as mock_setup,
            patch("lets.cli.get_best_available_launcher") as mock_launcher,
            patch("lets.cli.get_available_launchers") as mock_available,
            patch("lets.cli.setup_worktree_and_launcher") as mock_worktree,
            patch("lets.cli.print_workspace_summary"),
            patch("lets.cli.handle_launcher_attachment"),
        ):
            mock_settings_instance = MagicMock()
            mock_settings.load.return_value = mock_settings_instance

            mock_setup.return_value = (
                Path("/test"),
                "repo",
                "branch",
                "main",
                False,
            )
            mock_launcher.return_value = "tmux"
            mock_available.return_value = ["tmux"]
            mock_worktree.return_value = (Path("/test"), "branch")
            result = runner.invoke(
                main, ["test task", "--no-copy-env"]
            )

            assert result is not None

    def test_main_no_attach(self) -> None:
        """Test the --no-attach flag functionality."""
        runner = CliRunner()

        with (
            patch("lets.cli.check_and_run_setup_wizard", return_value=False),
            patch("lets.cli.LetsSettings") as mock_settings,
            patch("lets.cli.setup_repository_info") as mock_setup,
            patch("lets.cli.get_best_available_launcher") as mock_launcher,
            patch("lets.cli.get_available_launchers") as mock_available,
            patch("lets.cli.setup_worktree_and_launcher") as mock_worktree,
            patch("lets.cli.print_workspace_summary"),
            patch("lets.cli.handle_launcher_attachment"),
        ):
            mock_settings_instance = MagicMock()
            mock_settings.load.return_value = mock_settings_instance

            mock_setup.return_value = (
                Path("/test"),
                "repo",
                "branch",
                "main",
                False,
            )
            mock_launcher.return_value = "tmux"
            mock_available.return_value = ["tmux"]
            mock_worktree.return_value = (Path("/test"), "branch")
            result = runner.invoke(
                main, ["test task", "--no-attach"]
            )

            assert result is not None
            # Should not call attachment when --no-attach is used

    def test_main_force_flag(self) -> None:
        """Test the --force flag functionality."""
        runner = CliRunner()

        with (
            patch("lets.cli.check_and_run_setup_wizard", return_value=False),
            patch("lets.cli.LetsSettings") as mock_settings,
            patch("lets.cli.setup_repository_info") as mock_setup,
            patch("lets.cli.get_best_available_launcher") as mock_launcher,
            patch("lets.cli.get_available_launchers") as mock_available,
            patch("lets.cli.setup_worktree_and_launcher") as mock_worktree,
            patch("lets.cli.print_workspace_summary"),
            patch("lets.cli.handle_launcher_attachment"),
        ):
            mock_settings_instance = MagicMock()
            mock_settings.load.return_value = mock_settings_instance

            mock_setup.return_value = (
                Path("/test"),
                "repo",
                "branch",
                "main",
                False,
            )
            mock_launcher.return_value = "tmux"
            mock_available.return_value = ["tmux"]
            mock_worktree.return_value = (Path("/test"), "branch")
            result = runner.invoke(
                main, ["test task", "--force"]
            )

            assert result is not None

    def test_main_custom_session(self) -> None:
        """Test the --session flag functionality."""
        runner = CliRunner()

        with (
            patch("lets.cli.check_and_run_setup_wizard", return_value=False),
            patch("lets.cli.LetsSettings") as mock_settings,
            patch("lets.cli.setup_repository_info") as mock_setup,
            patch("lets.cli.get_best_available_launcher") as mock_launcher,
            patch("lets.cli.get_available_launchers") as mock_available,
            patch("lets.cli.setup_worktree_and_launcher") as mock_worktree,
            patch("lets.cli.print_workspace_summary"),
            patch("lets.cli.handle_launcher_attachment"),
        ):
            mock_settings_instance = MagicMock()
            mock_settings.load.return_value = mock_settings_instance

            mock_setup.return_value = (
                Path("/test"),
                "repo",
                "branch",
                "main",
                False,
            )
            mock_launcher.return_value = "tmux"
            mock_available.return_value = ["tmux"]
            mock_worktree.return_value = (Path("/test"), "branch")
            result = runner.invoke(
                main,
                [
                    "test task",
                    "--session",
                    "custom-session",
                ],
            )

            assert result is not None

    def test_main_custom_ai_tool(self) -> None:
        """Test the --ai-tool flag functionality."""
        runner = CliRunner()

        with (
            patch("lets.cli.check_and_run_setup_wizard", return_value=False),
            patch("lets.cli.LetsSettings") as mock_settings,
            patch("lets.cli.setup_repository_info") as mock_setup,
            patch("lets.cli.get_best_available_launcher") as mock_launcher,
            patch("lets.cli.get_available_launchers") as mock_available,
            patch("lets.cli.setup_worktree_and_launcher") as mock_worktree,
            patch("lets.cli.print_workspace_summary"),
            patch("lets.cli.handle_launcher_attachment"),
        ):
            mock_settings_instance = MagicMock()
            mock_settings.load.return_value = mock_settings_instance

            mock_setup.return_value = (
                Path("/test"),
                "repo",
                "branch",
                "main",
                False,
            )
            mock_launcher.return_value = "tmux"
            mock_available.return_value = ["tmux"]
            mock_worktree.return_value = (Path("/test"), "branch")
            result = runner.invoke(
                main, ["test task", "--ai-tool", "chatgpt"]
            )

            assert result is not None
            # Verify that ai_tool was passed through
            # the setup
            mock_setup.assert_called_once()
            call_args = mock_setup.call_args
            assert (
                call_args[0][2] == "chatgpt"
            )  # ai_tool is 3rd argument

    def test_main_custom_launcher(self) -> None:
        """Test the --launcher flag functionality."""
        runner = CliRunner()

        with (
            patch("lets.cli.check_and_run_setup_wizard", return_value=False),
            patch("lets.cli.LetsSettings") as mock_settings,
            patch("lets.cli.setup_repository_info") as mock_setup,
            patch("lets.cli.get_best_available_launcher") as mock_launcher,
            patch("lets.cli.get_available_launchers") as mock_available,
            patch("lets.cli.setup_worktree_and_launcher") as mock_worktree,
            patch("lets.cli.print_workspace_summary"),
            patch("lets.cli.handle_launcher_attachment"),
        ):
            mock_settings_instance = MagicMock()
            mock_settings.load.return_value = mock_settings_instance

            mock_setup.return_value = (
                Path("/test"),
                "repo",
                "branch",
                "main",
                False,
            )
            mock_launcher.return_value = "terminal"  # Default would be tmux
            mock_available.return_value = ["tmux", "terminal"]
            mock_worktree.return_value = (Path("/test"), "branch")
            result = runner.invoke(
                main,
                ["test task", "--launcher", "terminal"],
            )

            assert result.exit_code == 0

    def test_main_with_branch_name(self) -> None:
        """Test providing custom branch name."""
        runner = CliRunner()

        with (
            patch("lets.cli.check_and_run_setup_wizard", return_value=False),
            patch("lets.cli.LetsSettings") as mock_settings,
            patch("lets.cli.setup_repository_info") as mock_setup,
            patch("lets.cli.get_best_available_launcher") as mock_launcher,
            patch("lets.cli.get_available_launchers") as mock_available,
            patch("lets.cli.setup_worktree_and_launcher") as mock_worktree,
            patch("lets.cli.print_workspace_summary"),
            patch("lets.cli.handle_launcher_attachment"),
        ):
            mock_settings_instance = MagicMock()
            mock_settings.load.return_value = mock_settings_instance

            mock_setup.return_value = (
                Path("/test"),
                "repo",
                "custom-branch",
                "main",
                False,
            )
            mock_launcher.return_value = "tmux"
            mock_available.return_value = ["tmux"]
            mock_worktree.return_value = (
                Path("/test"),
                "custom-branch",
            )
            result = runner.invoke(
                main,
                ["test task", "--branch", "custom-branch"],
            )

            assert result is not None
            # Verify branch name was passed
            mock_setup.assert_called_once()
            call_args = mock_setup.call_args
            assert (
                call_args[0][1] == "custom-branch"
            )  # branch is 2nd argument
