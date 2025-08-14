"""Tests for configuration management."""

import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

from lets.config import (
    LauncherSettings,
    LetsSettings,
    TerminalLauncherSettings,
    TmuxLauncherSettings,
)


class TestTmuxLauncherSettings:
    """Test tmux launcher settings."""

    def test_tmux_launcher_settings_defaults(self) -> None:
        """Test default tmux launcher settings."""
        settings = TmuxLauncherSettings()

        assert settings.session == "dev"
        assert settings.auto_attach is True

    def test_tmux_launcher_settings_custom(self) -> None:
        """Test custom tmux launcher settings."""
        settings = TmuxLauncherSettings(session="work", auto_attach=False)

        assert settings.session == "work"
        assert settings.auto_attach is False


class TestTerminalLauncherSettings:
    """Test terminal launcher settings."""

    def test_terminal_launcher_settings_defaults(self) -> None:
        """Test default terminal launcher settings."""
        settings = TerminalLauncherSettings()

        assert settings.terminal_command == ""

    def test_terminal_launcher_settings_custom(self) -> None:
        """Test custom terminal launcher settings."""
        settings = TerminalLauncherSettings(terminal_command="gnome-terminal")

        assert settings.terminal_command == "gnome-terminal"


class TestLauncherSettings:
    """Test launcher settings container."""

    def test_launcher_settings_defaults(self) -> None:
        """Test default launcher settings."""
        settings = LauncherSettings()

        assert isinstance(settings.tmux, TmuxLauncherSettings)
        assert isinstance(settings.terminal, TerminalLauncherSettings)
        assert settings.tmux.session == "dev"
        assert settings.terminal.terminal_command == ""


class TestLetsSettings:
    """Test main configuration settings."""

    def test_lets_settings_defaults(self) -> None:
        """Test default settings."""
        with patch("lets.config.xdg_config_home") as mock_xdg:
            mock_xdg.return_value = Path("/home/user/.config")

            settings = LetsSettings()

            assert settings.launcher == "tmux"
            assert settings.ai_tool == "claude"
            assert settings.editor_command == ""
            assert settings.worktree_base_dir == ""
            assert settings.copy_env_files is True
            assert settings.env_file_patterns == [
                ".env",
                ".env.local",
                ".env.development",
            ]
            assert settings.default_base_branch == ""
            assert isinstance(settings.launchers, LauncherSettings)

    def test_lets_settings_custom(self) -> None:
        """Test custom settings."""
        with patch("lets.config.xdg_config_home") as mock_xdg:
            mock_xdg.return_value = Path("/home/user/.config")

            settings = LetsSettings(
                launcher="terminal",
                ai_tool="chatgpt",
                editor_command="code",
                worktree_base_dir="/custom/path",
                copy_env_files=False,
                env_file_patterns=[".env.prod"],
                default_base_branch="develop",
            )

            assert settings.launcher == "terminal"
            assert settings.ai_tool == "chatgpt"
            assert settings.editor_command == "code"
            assert settings.worktree_base_dir == "/custom/path"
            assert settings.copy_env_files is False
            assert settings.env_file_patterns == [".env.prod"]
            assert settings.default_base_branch == "develop"

    def test_get_config_dir(self) -> None:
        """Test getting configuration directory."""
        with patch("lets.config.xdg_config_home") as mock_xdg:
            mock_xdg.return_value = Path("/home/user/.config")

            config_dir = LetsSettings.get_config_dir()

            assert config_dir == Path("/home/user/.config/lets")

    def test_get_config_file(self) -> None:
        """Test getting configuration file path."""
        with patch("lets.config.xdg_config_home") as mock_xdg:
            mock_xdg.return_value = Path("/home/user/.config")

            config_file = LetsSettings.get_config_file()

            assert config_file == Path("/home/user/.config/lets/config.toml")

    def test_load_creates_config_dir(self) -> None:
        """Test that load() creates config directory."""
        with patch("lets.config.xdg_config_home") as mock_xdg:
            mock_config_dir = MagicMock()
            mock_xdg.return_value = Path("/home/user/.config")

            with patch("lets.config.LetsSettings.get_config_dir") as mock_get_dir:
                mock_get_dir.return_value = mock_config_dir

                settings = LetsSettings.load()

                mock_config_dir.mkdir.assert_called_once_with(
                    parents=True, exist_ok=True
                )
                assert isinstance(settings, LetsSettings)

    def test_save_creates_config_dir_and_file(self) -> None:
        """Test that save() creates config directory and file."""
        with tempfile.TemporaryDirectory() as tmpdir:
            config_dir = Path(tmpdir) / "lets"
            config_file = config_dir / "config.toml"

            with (
                patch("lets.config.LetsSettings.get_config_dir") as mock_get_dir,
                patch("lets.config.LetsSettings.get_config_file") as mock_get_file,
            ):
                    mock_get_dir.return_value = config_dir
                    mock_get_file.return_value = config_file

                    settings = LetsSettings(launcher="terminal", ai_tool="custom")
                    settings.save()

                    # Check that directory was created
                    assert config_dir.exists()

                    # Check that file was created and contains expected content
                    assert config_file.exists()
                    content = config_file.read_text()
                    assert 'launcher = "terminal"' in content
                    assert 'ai_tool = "custom"' in content

    def test_save_with_existing_config_dir(self) -> None:
        """Test save when config directory already exists."""
        with tempfile.TemporaryDirectory() as tmpdir:
            config_dir = Path(tmpdir) / "lets"
            config_file = config_dir / "config.toml"

            # Pre-create the directory
            config_dir.mkdir(parents=True, exist_ok=True)

            with (
                patch("lets.config.LetsSettings.get_config_dir") as mock_get_dir,
                patch("lets.config.LetsSettings.get_config_file") as mock_get_file,
            ):
                    mock_get_dir.return_value = config_dir
                    mock_get_file.return_value = config_file

                    settings = LetsSettings(copy_env_files=False)
                    settings.save()

                    # Check that file was created
                    assert config_file.exists()
                    content = config_file.read_text()
                    assert "copy_env_files = false" in content
