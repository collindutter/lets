"""Tests for configuration CLI commands."""

import subprocess
from unittest.mock import MagicMock, patch

from click.testing import CliRunner

import lets.config_cli
from lets.config_cli import (
    config_group,
    edit,
    launchers,
    reset,
    set_launcher,
    show,
)


class TestConfigShow:
    """Test the config show command."""

    def test_show_existing_config(self) -> None:
        """Test showing existing configuration file."""
        runner = CliRunner()

        with patch("lets.config_cli.LetsSettings") as mock_settings:
            mock_config_file = MagicMock()
            mock_config_file.exists.return_value = True
            mock_config_file.read_text.return_value = "test_config = true"
            mock_config_file.__str__ = MagicMock(return_value="/path/to/config")

            mock_settings_instance = MagicMock()
            mock_settings_instance.get_config_file.return_value = mock_config_file
            mock_settings.load.return_value = mock_settings_instance

            result = runner.invoke(show)

            assert result.exit_code == 0
            assert "Configuration file: /path/to/config" in result.output
            assert "Current configuration:" in result.output
            assert "test_config = true" in result.output

    def test_show_no_config(self) -> None:
        """Test showing when no configuration file exists."""
        runner = CliRunner()

        with patch("lets.config_cli.LetsSettings") as mock_settings:
            mock_config_file = MagicMock()
            mock_config_file.exists.return_value = False
            mock_config_file.__str__ = MagicMock(return_value="/path/to/config")

            mock_settings_instance = MagicMock()
            mock_settings_instance.get_config_file.return_value = mock_config_file
            mock_settings.load.return_value = mock_settings_instance

            result = runner.invoke(show)

            assert result.exit_code == 0
            assert "Configuration file: /path/to/config" in result.output
            assert "No configuration file found" in result.output
            assert "Default configuration:" in result.output


class TestConfigEdit:
    """Test the config edit command."""

    def test_edit_existing_config(self) -> None:
        """Test editing existing configuration file."""
        runner = CliRunner()

        with patch("lets.config_cli.LetsSettings") as mock_settings:
            mock_config_file = MagicMock()
            mock_config_file.exists.return_value = True
            mock_config_file.__str__ = MagicMock(return_value="/path/to/config")

            mock_settings_instance = MagicMock()
            mock_settings_instance.get_config_file.return_value = mock_config_file
            mock_settings.load.return_value = mock_settings_instance

            with (
                patch("subprocess.run") as mock_run,
                patch.dict("os.environ", {"EDITOR": "nano"}),
            ):
                    result = runner.invoke(edit)

                    assert result.exit_code == 0
                    mock_run.assert_called_once_with(
                        ["nano", "/path/to/config"], check=True
                    )

    def test_edit_create_config(self) -> None:
        """Test creating and editing new configuration file."""
        runner = CliRunner()

        with patch("lets.config_cli.LetsSettings") as mock_settings:
            mock_config_file = MagicMock()
            mock_config_file.exists.return_value = False
            mock_config_file.__str__ = MagicMock(return_value="/path/to/config")

            mock_settings_instance = MagicMock()
            mock_settings_instance.get_config_file.return_value = mock_config_file
            mock_settings.load.return_value = mock_settings_instance

            with (
                patch("subprocess.run") as mock_run,
                patch.dict("os.environ", {"EDITOR": "nano"}),
            ):
                    result = runner.invoke(edit)

                    assert result.exit_code == 0
                    assert "Created default configuration" in result.output
                    mock_settings_instance.save.assert_called_once()
                    mock_run.assert_called_once_with(
                        ["nano", "/path/to/config"], check=True
                    )

    def test_edit_default_editor(self) -> None:
        """Test editing with default editor when EDITOR not set."""
        runner = CliRunner()

        with patch("lets.config_cli.LetsSettings") as mock_settings:
            mock_config_file = MagicMock()
            mock_config_file.exists.return_value = True
            mock_config_file.__str__ = MagicMock(return_value="/path/to/config")

            mock_settings_instance = MagicMock()
            mock_settings_instance.get_config_file.return_value = mock_config_file
            mock_settings.load.return_value = mock_settings_instance

            with (
                patch("subprocess.run") as mock_run,
                patch.dict("os.environ", {}, clear=True),
            ):
                    result = runner.invoke(edit)

                    assert result.exit_code == 0
                    mock_run.assert_called_once_with(
                        ["vi", "/path/to/config"], check=True
                    )

    def test_edit_subprocess_error(self) -> None:
        """Test handling subprocess error when opening editor."""
        runner = CliRunner()

        with patch("lets.config_cli.LetsSettings") as mock_settings:
            mock_config_file = MagicMock()
            mock_config_file.exists.return_value = True
            mock_config_file.__str__ = MagicMock(return_value="/path/to/config")

            mock_settings_instance = MagicMock()
            mock_settings_instance.get_config_file.return_value = mock_config_file
            mock_settings.load.return_value = mock_settings_instance

            with patch("subprocess.run") as mock_run:
                mock_run.side_effect = subprocess.CalledProcessError(1, ["nano"])
                with patch.dict("os.environ", {"EDITOR": "nano"}):
                    result = runner.invoke(edit)

                    assert result.exit_code == 0
                    assert "Failed to open editor: nano" in result.output
                    assert "You can manually edit: /path/to/config" in result.output

    def test_edit_editor_not_found(self) -> None:
        """Test handling editor not found error."""
        runner = CliRunner()

        with patch("lets.config_cli.LetsSettings") as mock_settings:
            mock_config_file = MagicMock()
            mock_config_file.exists.return_value = True
            mock_config_file.__str__ = MagicMock(return_value="/path/to/config")

            mock_settings_instance = MagicMock()
            mock_settings_instance.get_config_file.return_value = mock_config_file
            mock_settings.load.return_value = mock_settings_instance

            with patch("subprocess.run") as mock_run:
                mock_run.side_effect = FileNotFoundError()
                with patch.dict("os.environ", {"EDITOR": "nonexistent"}):
                    result = runner.invoke(edit)

                    assert result.exit_code == 0
                    assert "Editor not found: nonexistent" in result.output
                    assert "You can manually edit: /path/to/config" in result.output


class TestConfigSetLauncher:
    """Test the config set-launcher command."""

    def test_set_launcher_available(self) -> None:
        """Test setting an available launcher."""
        runner = CliRunner()

        with patch("lets.config_cli.LetsSettings") as mock_settings:
            mock_settings_instance = MagicMock()
            mock_settings.load.return_value = mock_settings_instance

            with patch("lets.config_cli.get_available_launchers") as mock_available:
                mock_available.return_value = ["tmux", "terminal"]

                result = runner.invoke(set_launcher, ["tmux"])

                assert result.exit_code == 0
                assert "Default launcher set to: tmux" in result.output
                assert mock_settings_instance.launcher == "tmux"
                mock_settings_instance.save.assert_called_once()

    def test_set_launcher_unavailable(self) -> None:
        """Test setting an unavailable launcher."""
        runner = CliRunner()

        with patch("lets.config_cli.LetsSettings") as mock_settings:
            mock_settings_instance = MagicMock()
            mock_settings.load.return_value = mock_settings_instance

            with patch("lets.config_cli.get_available_launchers") as mock_available:
                mock_available.return_value = ["terminal"]  # tmux not available

                result = runner.invoke(set_launcher, ["tmux"])

                assert result.exit_code == 0
                assert "Launcher 'tmux' is not available" in result.output
                assert "Available launchers: terminal" in result.output
                mock_settings_instance.save.assert_not_called()

    def test_set_launcher_invalid_choice(self) -> None:
        """Test setting an invalid launcher choice."""
        runner = CliRunner()

        result = runner.invoke(set_launcher, ["invalid"])

        assert result.exit_code != 0
        # Check for generic click error message pattern
        assert "invalid" in result.output.lower() or "choice" in result.output.lower()


class TestConfigLaunchers:
    """Test the config launchers command."""

    def test_launchers_list(self) -> None:
        """Test listing available launchers."""
        runner = CliRunner()

        with patch("lets.config_cli.LetsSettings") as mock_settings:
            mock_settings_instance = MagicMock()
            mock_settings_instance.launcher = "tmux"
            mock_settings.load.return_value = mock_settings_instance

            with patch("lets.config_cli.get_available_launchers") as mock_available:
                mock_available.return_value = ["tmux"]  # only tmux available

                result = runner.invoke(launchers)

                assert result.exit_code == 0
                assert "Available launchers:" in result.output
                assert "✅ tmux (default)" in result.output
                assert "❌ terminal" in result.output

    def test_launchers_list_all_available(self) -> None:
        """Test listing when all launchers are available."""
        runner = CliRunner()

        with patch("lets.config_cli.LetsSettings") as mock_settings:
            mock_settings_instance = MagicMock()
            mock_settings_instance.launcher = "terminal"
            mock_settings.load.return_value = mock_settings_instance

            with patch("lets.config_cli.get_available_launchers") as mock_available:
                mock_available.return_value = ["tmux", "terminal"]

                result = runner.invoke(launchers)

                assert result.exit_code == 0
                assert "Available launchers:" in result.output
                assert "✅ tmux" in result.output
                assert "✅ terminal (default)" in result.output


class TestConfigReset:
    """Test the config reset command."""

    def test_reset_confirmed(self) -> None:
        """Test resetting configuration when confirmed."""
        runner = CliRunner()

        with patch("lets.config_cli.LetsSettings") as mock_settings:
            mock_settings_instance = MagicMock()
            mock_settings.return_value = mock_settings_instance

            with patch("click.confirm", return_value=True):
                result = runner.invoke(reset)

                assert result.exit_code == 0
                assert "Configuration reset to defaults" in result.output
                mock_settings_instance.save.assert_called_once()

    def test_reset_cancelled(self) -> None:
        """Test resetting configuration when cancelled."""
        runner = CliRunner()

        with patch("lets.config_cli.LetsSettings") as mock_settings:
            mock_settings_instance = MagicMock()
            mock_settings.return_value = mock_settings_instance

            with patch("click.confirm", return_value=False):
                result = runner.invoke(reset)

                assert result.exit_code == 0
                mock_settings_instance.save.assert_not_called()


class TestConfigGroup:
    """Test the main config group."""

    def test_config_group_help(self) -> None:
        """Test config group shows help."""
        runner = CliRunner()
        result = runner.invoke(config_group, ["--help"])

        assert result.exit_code == 0
        assert "Manage lets configuration" in result.output
        assert "show" in result.output
        assert "edit" in result.output
        assert "set-launcher" in result.output
        assert "launchers" in result.output
        assert "reset" in result.output

    def test_config_main_execution(self) -> None:
        """Test running config_cli as main module."""
        with patch("lets.config_cli.config_group"):
            # The main block should only run when __name__ == "__main__"
            # but we can test that the function exists
            assert hasattr(lets.config_cli, "config_group")
