"""Tests for git operations and worktree management."""

import subprocess
from pathlib import Path
from typing import TYPE_CHECKING
from unittest.mock import MagicMock, call, patch

if TYPE_CHECKING:
    from lets.cli import WorktreeConfig

import pytest

from lets.cli import (
    copy_env_files,
    create_worktree,
    handle_existing_worktree,
    setup_repository_info,
    setup_worktree_and_launcher,
)


class TestCreateWorktree:
    """Test worktree creation functionality."""

    def test_create_worktree_new_branch_success(self) -> None:
        """Test successful creation of worktree with new branch."""
        worktree_path = Path("/test/worktree")

        with patch("lets.cli.run_command_with_spinner") as mock_run:
            mock_run.return_value = None
            result = create_worktree(
                worktree_path, "feature-branch", "main", is_existing_branch=False
            )
            assert result is True

            # Verify git commands were called
            expected_calls = [
                call(
                    ["git", "fetch", "origin"],
                    "Fetching latest changes...",
                    capture_output=True,
                    check=False,
                ),
                call(
                    [
                        "git",
                        "worktree",
                        "add",
                        "-b",
                        "feature-branch",
                        str(worktree_path),
                        "main",
                    ],
                    "Creating worktree with new branch 'feature-branch'...",
                    capture_output=True,
                ),
                call(
                    ["git", "push", "--set-upstream", "origin", "feature-branch"],
                    "Setting up upstream tracking for 'feature-branch'...",
                    cwd=worktree_path,
                    capture_output=True,
                    check=False,
                ),
            ]
            mock_run.assert_has_calls(expected_calls)

    def test_create_worktree_existing_branch_success(self) -> None:
        """Test successful creation of worktree with existing branch."""
        worktree_path = Path("/test/worktree")

        with patch("lets.cli.run_command_with_spinner") as mock_run:
            mock_run.return_value = None
            result = create_worktree(
                worktree_path, "existing-branch", "main", is_existing_branch=True
            )
            assert result is True

            # Verify correct git commands for existing branch
            fetch_call = call(
                ["git", "fetch", "origin"],
                "Fetching latest changes...",
                capture_output=True,
                check=False,
            )
            checkout_call = call(
                ["git", "worktree", "add", str(worktree_path), "existing-branch"],
                "Creating worktree from existing branch 'existing-branch'...",
                capture_output=True,
            )
            mock_run.assert_has_calls([fetch_call, checkout_call])

    def test_create_worktree_failure(self) -> None:
        """Test worktree creation failure."""
        worktree_path = Path("/test/worktree")

        with patch("lets.cli.run_command_with_spinner") as mock_run:
            mock_run.side_effect = [
                None,  # fetch succeeds
                subprocess.CalledProcessError(
                    1, ["git", "worktree", "add"]
                ),  # worktree fails
            ]
            result = create_worktree(
                worktree_path, "feature-branch", "main", is_existing_branch=False
            )
            assert result is False

    def test_create_worktree_push_failure_fallback(self) -> None:
        """Test worktree creation with push failure but successful fallback tracking."""
        worktree_path = Path("/test/worktree")

        with patch("lets.cli.run_command_with_spinner") as mock_run:
            mock_run.side_effect = [
                None,  # fetch succeeds
                None,  # worktree creation succeeds
                subprocess.CalledProcessError(1, ["git", "push"]),  # push fails
                None,  # fallback tracking succeeds
            ]
            result = create_worktree(
                worktree_path, "feature-branch", "main", is_existing_branch=False
            )
            assert result is True

            # Verify fallback tracking was called
            fallback_call = call(
                ["git", "branch", "--set-upstream-to=origin/main", "feature-branch"],
                "Setting up local branch tracking...",
                cwd=worktree_path,
                capture_output=True,
                check=False,
            )
            assert fallback_call in mock_run.call_args_list


class TestEnvFiles:
    """Test environment file operations."""

    def test_copy_env_files_success(self, temp_dir: Path) -> None:
        """Test successful copying of environment files."""
        source_dir = temp_dir / "source"
        dest_dir = temp_dir / "dest"
        source_dir.mkdir()
        dest_dir.mkdir()

        # Create test env files
        env_file = source_dir / ".env"
        env_local_file = source_dir / ".env.local"
        env_file.write_text("ENV=test")
        env_local_file.write_text("ENV_LOCAL=test")

        copy_env_files(source_dir, dest_dir, [".env", ".env.local", ".env.missing"])

        # Verify files were copied
        assert (dest_dir / ".env").exists()
        assert (dest_dir / ".env.local").exists()
        assert not (dest_dir / ".env.missing").exists()

        assert (dest_dir / ".env").read_text() == "ENV=test"
        assert (dest_dir / ".env.local").read_text() == "ENV_LOCAL=test"

    def test_copy_env_files_no_source_files(self, temp_dir: Path) -> None:
        """Test copying env files when source files don't exist."""
        source_dir = temp_dir / "source"
        dest_dir = temp_dir / "dest"
        source_dir.mkdir()
        dest_dir.mkdir()

        # Should not raise error when files don't exist
        copy_env_files(source_dir, dest_dir, [".env", ".env.local"])

        # No files should be created in destination
        assert not (dest_dir / ".env").exists()
        assert not (dest_dir / ".env.local").exists()


class TestExistingWorktree:
    """Test handling of existing worktree directories."""

    def test_handle_existing_worktree_force(self, temp_dir: Path) -> None:
        """Test force removal of existing worktree."""
        worktree_path = temp_dir / "repo" / "branch"
        worktree_path.mkdir(parents=True)

        with (
            patch("lets.cli.run_command_with_spinner") as mock_run,
            patch("shutil.rmtree"),
        ):
                result_path, result_branch = handle_existing_worktree(
                    worktree_path,
                    force=True,
                    branch_name="branch",
                    base_dir=temp_dir,
                    repo_name="repo",
                )

                assert result_path == worktree_path
                assert result_branch == "branch"
                mock_run.assert_called_once()
                assert "git worktree remove --force" in " ".join(
                    mock_run.call_args[0][0]
                )

    def test_handle_existing_worktree_confirm_remove(self, temp_dir: Path) -> None:
        """Test confirming removal of existing worktree."""
        worktree_path = temp_dir / "repo" / "branch"
        worktree_path.mkdir(parents=True)

        with (
            patch("lets.cli.run_command_with_spinner") as mock_run,
            patch("click.confirm", return_value=True),
        ):
                result_path, result_branch = handle_existing_worktree(
                    worktree_path,
                    force=False,
                    branch_name="branch",
                    base_dir=temp_dir,
                    repo_name="repo",
                )

                assert result_path == worktree_path
                assert result_branch == "branch"
                mock_run.assert_called_once()

    def test_handle_existing_worktree_alternative_name(self, temp_dir: Path) -> None:
        """Test using alternative name for existing worktree."""
        worktree_path = temp_dir / "repo" / "branch"
        worktree_path.mkdir(parents=True)

        with (
            patch("click.confirm", return_value=False),
            patch("lets.cli.datetime") as mock_datetime,
        ):
                mock_datetime.now.return_value.strftime.return_value = "120000"
                result_path, result_branch = handle_existing_worktree(
                    worktree_path,
                    force=False,
                    branch_name="branch",
                    base_dir=temp_dir,
                    repo_name="repo",
                )

                expected_path = temp_dir / "repo" / "branch-120000"
                assert result_path == expected_path
                assert result_branch == "branch-120000"


class TestRepositorySetup:
    """Test repository information setup."""

    def test_setup_repository_info_success(self, mock_git_repo: Path) -> None:
        """Test successful repository information setup."""
        task = "Fix authentication bug"
        branch = None
        ai_tool = "claude"
        # Ensure the mock fixture is being used
        assert mock_git_repo.name == "test-repo"

        with patch("lets.cli.generate_branch_name") as mock_generate:
            mock_generate.return_value = "fix-auth-bug"
            with patch("lets.cli.handle_branch_conflict") as mock_conflict:
                mock_conflict.return_value = ("fix-auth-bug", False)

                result = setup_repository_info(task, branch, ai_tool, verbose=False)
                current_dir, repo_name, branch_name, current_branch, is_existing = (
                    result
                )

                assert repo_name == "test-repo"
                assert branch_name == "fix-auth-bug"
                assert current_branch == "main"
                assert is_existing is False

                mock_generate.assert_called_once_with(
                    task, ai_tool=ai_tool, verbose=False
                )
                mock_conflict.assert_called_once_with("fix-auth-bug")

    def test_setup_repository_info_custom_branch(self, mock_git_repo: Path) -> None:
        """Test repository setup with custom branch name."""
        task = "Fix authentication bug"
        branch = "custom-branch"
        ai_tool = "claude"
        # Ensure the mock fixture is being used
        assert mock_git_repo.name == "test-repo"

        with (
            patch("lets.cli.generate_branch_name") as mock_generate,
            patch("lets.cli.handle_branch_conflict") as mock_conflict,
        ):
                mock_conflict.return_value = ("custom-branch", True)

                result = setup_repository_info(task, branch, ai_tool, verbose=False)
                current_dir, repo_name, branch_name, current_branch, is_existing = (
                    result
                )

                assert branch_name == "custom-branch"
                assert is_existing is True

                # Should not call generate_branch_name when branch is provided
                mock_generate.assert_not_called()
                mock_conflict.assert_called_once_with("custom-branch")


class TestWorktreeAndLauncherSetup:
    """Test complete worktree and launcher setup."""

    def test_setup_worktree_and_launcher_success(
        self, sample_worktree_config: "WorktreeConfig", temp_dir: Path
    ) -> None:
        """Test successful worktree and launcher setup."""
        config = sample_worktree_config
        config.current_dir = temp_dir

        with (
            patch("lets.cli.get_worktree_base_dir") as mock_base_dir,
            patch("lets.cli.get_base_branch") as mock_base_branch,
            patch("lets.cli.create_worktree") as mock_create,
            patch("lets.cli.copy_env_files") as mock_copy_env,
            patch("lets.cli.LetsSettings"),
            patch("lets.cli.get_launcher") as mock_launcher,
        ):
            mock_base_dir.return_value = temp_dir / "worktrees"
            mock_base_branch.return_value = "main"
            mock_create.return_value = True
            mock_launcher_instance = MagicMock()
            mock_launcher_instance.setup_workspace.return_value = True
            mock_launcher.return_value = mock_launcher_instance

            result_path, result_branch = setup_worktree_and_launcher(config)

            expected_path = (
                temp_dir
                / "worktrees"
                / config.repo_name
                / config.branch_name
            )
            assert result_path == expected_path
            assert result_branch == config.branch_name

            mock_create.assert_called_once()
            mock_copy_env.assert_called_once()
            mock_launcher_instance.setup_workspace.assert_called_once()

    def test_setup_worktree_and_launcher_worktree_failure(
        self, sample_worktree_config: "WorktreeConfig", temp_dir: Path
    ) -> None:
        """Test worktree setup failure."""
        config = sample_worktree_config

        with patch("lets.cli.get_worktree_base_dir") as mock_base_dir:
            mock_base_dir.return_value = temp_dir / "worktrees"
            with patch("lets.cli.get_base_branch") as mock_base_branch:
                mock_base_branch.return_value = "main"
                with patch("lets.cli.create_worktree") as mock_create:
                    mock_create.return_value = False
                    with pytest.raises(SystemExit):
                        setup_worktree_and_launcher(config)

    def test_setup_worktree_and_launcher_existing_directory(
        self, sample_worktree_config: "WorktreeConfig", temp_dir: Path
    ) -> None:
        """Test setup with existing worktree directory."""
        config = sample_worktree_config

        # Create existing directory
        worktree_path = temp_dir / "worktrees" / config.repo_name / config.branch_name
        worktree_path.mkdir(parents=True)

        with (
            patch("lets.cli.get_worktree_base_dir") as mock_base_dir,
            patch("lets.cli.handle_existing_worktree") as mock_handle,
            patch("lets.cli.get_base_branch") as mock_base_branch,
            patch("lets.cli.create_worktree") as mock_create,
            patch("lets.cli.copy_env_files"),
            patch("lets.cli.LetsSettings"),
            patch("lets.cli.get_launcher") as mock_launcher,
        ):
            mock_base_dir.return_value = temp_dir / "worktrees"
            mock_handle.return_value = (worktree_path, config.branch_name)
            mock_base_branch.return_value = "main"
            mock_create.return_value = True
            mock_launcher_instance = MagicMock()
            # Break up long line
            mock_launcher_instance.setup_workspace.return_value = True
            mock_launcher.return_value = mock_launcher_instance

            result_path, result_branch = setup_worktree_and_launcher(config)

            mock_handle.assert_called_once()
            assert result_path == worktree_path
            assert result_branch == config.branch_name
