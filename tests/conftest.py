"""Pytest configuration and shared fixtures."""

import tempfile
from collections.abc import Generator
from pathlib import Path
from unittest.mock import MagicMock

import pytest
from _pytest.monkeypatch import MonkeyPatch

from lets import cli
from lets.cli import WorktreeConfig


@pytest.fixture
def temp_dir() -> Generator[Path, None, None]:
    """Create a temporary directory for testing."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)


@pytest.fixture
def mock_git_repo(temp_dir: Path, monkeypatch: MonkeyPatch) -> Path:
    """Mock a git repository for testing."""
    repo_root = temp_dir / "test-repo"
    repo_root.mkdir()

    # Mock git commands
    def mock_run_command(cmd: list[str], **_kwargs: object) -> str | None:
        if cmd == ["git", "rev-parse", "--show-toplevel"]:
            return str(repo_root)
        if cmd == ["git", "branch", "--show-current"]:
            return "main"
        if cmd == ["git", "rev-parse", "--verify", "origin/main"]:
            return "abc123"
        if (cmd[0] == "git" and "fetch" in cmd) or (
            cmd[0] == "git" and "worktree" in cmd
        ):
            return None
        return None

    monkeypatch.setattr(cli, "run_command", mock_run_command)
    monkeypatch.setattr(cli, "run_command_with_spinner", mock_run_command)

    return repo_root


@pytest.fixture
def mock_console() -> MagicMock:
    """Mock rich console for testing."""
    return MagicMock()


@pytest.fixture
def sample_worktree_config() -> WorktreeConfig:
    """Sample WorktreeConfig for testing."""
    return WorktreeConfig(
        current_dir=Path("/test"),
        repo_name="test-repo",
        branch_name="test-branch",
        is_existing_branch=False,
        base_branch="main",
        force=False,
        copy_env=True,
        env_files=(".env", ".env.local"),
        session="test-session",
        task="Test task",
        ai_tool="claude",
        worktree_dir=None,
        launcher="tmux",
        attach=True,
    )
