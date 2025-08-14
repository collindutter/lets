"""Configuration management using Pydantic Settings."""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING, Literal

if TYPE_CHECKING:
    pass

import tomli_w
from pydantic import BaseModel, Field
from pydantic_settings import (
    BaseSettings,
    PydanticBaseSettingsSource,
    SettingsConfigDict,
    TomlConfigSettingsSource,
)
from xdg_base_dirs import xdg_config_home


class TmuxLauncherSettings(BaseModel):
    """Settings for tmux launcher."""

    session: str = Field(default="dev", description="Tmux session name")
    auto_attach: bool = Field(
        default=True, description="Automatically attach to tmux session"
    )


class TerminalLauncherSettings(BaseModel):
    """Settings for terminal launcher."""

    terminal_command: str = Field(
        default="", description="Command to open new terminal (empty = auto-detect)"
    )


class LauncherSettings(BaseModel):
    """Container for all launcher settings."""

    tmux: TmuxLauncherSettings = Field(default_factory=TmuxLauncherSettings)
    terminal: TerminalLauncherSettings = Field(default_factory=TerminalLauncherSettings)


class LetsSettings(BaseSettings):
    """Main configuration for lets tool."""

    model_config = SettingsConfigDict(
        env_prefix="LETS_",
        case_sensitive=False,
    )

    # Core settings
    launcher: Literal["tmux", "terminal"] = Field(
        default="tmux", description="Launcher to use for workspaces"
    )

    # AI tool configuration
    ai_tool: str = Field(
        default="claude", description="Default AI tool command to use for branch naming"
    )

    # Editor configuration (shared across launchers)
    editor_command: str = Field(
        default="",
        description="Editor command to use (empty = auto-detect from $EDITOR)",
    )

    # Worktree configuration
    worktree_base_dir: str = Field(
        default="",
        description="Base directory for worktrees (empty = use XDG data dir)",
    )

    # Environment file settings
    copy_env_files: bool = Field(
        default=True, description="Copy environment files to new worktrees by default"
    )
    env_file_patterns: list[str] = Field(
        default_factory=lambda: [".env", ".env.local", ".env.development"],
        description="Environment file patterns to copy",
    )

    # Git settings
    default_base_branch: str = Field(
        default="", description="Default base branch (empty = auto-detect)"
    )

    # Launcher-specific settings
    launchers: LauncherSettings = Field(default_factory=lambda: LauncherSettings())

    @classmethod
    def settings_customise_sources(
        cls,
        settings_cls: type[BaseSettings],
        init_settings: PydanticBaseSettingsSource,
        env_settings: PydanticBaseSettingsSource,
        dotenv_settings: PydanticBaseSettingsSource,
        file_secret_settings: PydanticBaseSettingsSource,
    ) -> tuple[PydanticBaseSettingsSource, ...]:
        """Customize settings sources to load from TOML config file."""
        return (
            init_settings,
            env_settings,
            TomlConfigSettingsSource(settings_cls, str(cls.get_config_file())),
            dotenv_settings,
            file_secret_settings,
        )

    @classmethod
    def get_config_dir(cls) -> Path:
        """Get the configuration directory."""
        return xdg_config_home() / "lets"

    @classmethod
    def get_config_file(cls) -> Path:
        """Get the configuration file path."""
        return cls.get_config_dir() / "config.toml"

    @classmethod
    def load(cls) -> LetsSettings:
        """Load settings from config file and environment."""
        # Ensure config directory exists
        config_dir = cls.get_config_dir()
        config_dir.mkdir(parents=True, exist_ok=True)

        # Pydantic Settings automatically handles loading from TOML file and env vars
        return cls()

    def save(self) -> None:
        """Save current settings to config file."""
        config_dir = self.get_config_dir()
        config_dir.mkdir(parents=True, exist_ok=True)

        config_file = self.get_config_file()

        # Convert to dictionary for TOML serialization
        data = self.model_dump()

        with config_file.open("wb") as f:
            tomli_w.dump(data, f)
