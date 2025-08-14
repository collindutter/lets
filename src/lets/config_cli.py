"""Configuration management CLI commands."""

from __future__ import annotations

import os
import subprocess
from typing import Literal, cast

import click

from .config import LetsSettings
from .launchers import get_available_launchers


@click.group(name="config")
def config_group() -> None:
    """Manage lets configuration."""


@config_group.command()
def show() -> None:
    """Show current configuration."""
    settings = LetsSettings.load()
    config_file = settings.get_config_file()

    click.echo(f"Configuration file: {config_file}")
    click.echo()

    if config_file.exists():
        click.echo("Current configuration:")
        click.echo(config_file.read_text())
    else:
        click.echo("No configuration file found. Using defaults.")
        click.echo()
        click.echo("Default configuration:")
        click.echo("# Default settings will be created when needed")


@config_group.command()
def edit() -> None:
    """Open configuration file in default editor."""
    settings = LetsSettings.load()
    config_file = settings.get_config_file()

    # Ensure config file exists
    if not config_file.exists():
        settings.save()
        click.echo(f"Created default configuration at: {config_file}")

    # Try to open with editor
    editor = os.environ.get("EDITOR", "vi")
    try:
        subprocess.run([editor, str(config_file)], check=True)
    except subprocess.CalledProcessError:
        click.echo(f"Failed to open editor: {editor}")
        click.echo(f"You can manually edit: {config_file}")
    except FileNotFoundError:
        click.echo(f"Editor not found: {editor}")
        click.echo(f"You can manually edit: {config_file}")


@config_group.command()
@click.argument("launcher", type=click.Choice(["tmux", "terminal"]))
def set_launcher(launcher: str) -> None:
    """Set the default launcher."""
    settings = LetsSettings.load()

    # Check if launcher is available
    available = get_available_launchers(settings)
    if launcher not in available:
        click.echo(f"❌ Launcher '{launcher}' is not available on this system")
        click.echo(f"Available launchers: {', '.join(available)}")
        return

    settings.launcher = cast("Literal['tmux', 'terminal']", launcher)
    settings.save()
    click.echo(f"✅ Default launcher set to: {launcher}")


@config_group.command()
def launchers() -> None:
    """List available launchers."""
    settings = LetsSettings.load()
    available = get_available_launchers(settings)

    click.echo("Available launchers:")
    for launcher_name in ["tmux", "terminal"]:
        status = "✅" if launcher_name in available else "❌"
        default_marker = " (default)" if launcher_name == settings.launcher else ""
        click.echo(f"  {status} {launcher_name}{default_marker}")


@config_group.command()
def reset() -> None:
    """Reset configuration to defaults."""
    if not click.confirm("This will reset all configuration to defaults. Continue?"):
        return

    settings = LetsSettings()
    settings.save()
    click.echo("✅ Configuration reset to defaults")


if __name__ == "__main__":
    config_group()
