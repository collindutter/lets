"""Tests for data models and utility classes."""

from dataclasses import fields
from pathlib import Path

from lets.cli import Colors, WorktreeConfig


class TestWorktreeConfig:
    """Test WorktreeConfig dataclass."""

    def test_worktree_config_creation(self) -> None:
        """Test creating a WorktreeConfig instance."""
        config = WorktreeConfig(
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

        assert config.current_dir == Path("/test")
        assert config.repo_name == "test-repo"
        assert config.branch_name == "test-branch"
        assert config.is_existing_branch is False
        assert config.base_branch == "main"
        assert config.force is False
        assert config.copy_env is True
        assert config.env_files == (".env", ".env.local")
        assert config.session == "test-session"
        assert config.task == "Test task"
        assert config.ai_tool == "claude"
        assert config.worktree_dir is None
        assert config.launcher == "tmux"
        assert config.attach is True

    def test_worktree_config_fields(self) -> None:
        """Test that WorktreeConfig has all expected fields."""
        field_names = {field.name for field in fields(WorktreeConfig)}
        expected_fields = {
            "current_dir",
            "repo_name",
            "branch_name",
            "is_existing_branch",
            "base_branch",
            "force",
            "copy_env",
            "env_files",
            "session",
            "task",
            "ai_tool",
            "worktree_dir",
            "launcher",
            "attach",
        }
        assert field_names == expected_fields

    def test_worktree_config_with_custom_worktree_dir(self) -> None:
        """Test WorktreeConfig with custom worktree directory."""
        config = WorktreeConfig(
            current_dir=Path("/test"),
            repo_name="test-repo",
            branch_name="test-branch",
            is_existing_branch=False,
            base_branch="main",
            force=False,
            copy_env=True,
            env_files=(".env",),
            session="test-session",
            task="Test task",
            ai_tool="claude",
            worktree_dir="/custom/worktree/path",
            launcher="terminal",
            attach=False,
        )

        assert config.worktree_dir == "/custom/worktree/path"
        assert config.launcher == "terminal"
        assert config.attach is False

    def test_worktree_config_immutable(self) -> None:
        """Test that WorktreeConfig is a dataclass (can be used for equality)."""
        config1 = WorktreeConfig(
            current_dir=Path("/test"),
            repo_name="test-repo",
            branch_name="test-branch",
            is_existing_branch=False,
            base_branch="main",
            force=False,
            copy_env=True,
            env_files=(".env",),
            session="test-session",
            task="Test task",
            ai_tool="claude",
            worktree_dir=None,
            launcher="tmux",
            attach=True,
        )

        config2 = WorktreeConfig(
            current_dir=Path("/test"),
            repo_name="test-repo",
            branch_name="test-branch",
            is_existing_branch=False,
            base_branch="main",
            force=False,
            copy_env=True,
            env_files=(".env",),
            session="test-session",
            task="Test task",
            ai_tool="claude",
            worktree_dir=None,
            launcher="tmux",
            attach=True,
        )

        assert config1 == config2


class TestColors:
    """Test Colors utility class."""

    def test_success_message(self) -> None:
        """Test success message formatting."""
        result = Colors.success("Operation completed")
        assert "✓ Operation completed" in result
        # We can't easily test the exact ANSI codes, but we can verify structure

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

    def test_colors_static_methods(self) -> None:
        """Test that all Colors methods are static."""
        # Should be able to call without instantiation
        Colors.success("test")
        Colors.error("test")
        Colors.info("test")
        Colors.warning("test")

    def test_colors_empty_message(self) -> None:
        """Test Colors methods with empty messages."""
        assert Colors.success("") == Colors.success("")
        assert Colors.error("") == Colors.error("")
        assert Colors.info("") == Colors.info("")
        assert Colors.warning("") == Colors.warning("")

    def test_colors_unicode_message(self) -> None:
        """Test Colors methods with unicode characters."""
        unicode_msg = "Test with 🚀 emojis and ñ accents"

        success_result = Colors.success(unicode_msg)
        error_result = Colors.error(unicode_msg)
        info_result = Colors.info(unicode_msg)
        warning_result = Colors.warning(unicode_msg)

        assert unicode_msg in success_result
        assert unicode_msg in error_result
        assert unicode_msg in info_result
        assert unicode_msg in warning_result

    def test_colors_multiline_message(self) -> None:
        """Test Colors methods with multiline messages."""
        multiline_msg = "Line 1\nLine 2\nLine 3"

        result = Colors.success(multiline_msg)
        assert "✓ " in result
        assert multiline_msg in result
