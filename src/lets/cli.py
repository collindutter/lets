"""Lets - AI-Powered Development Workspace Setup.

Quickly create isolated development environments with AI assistance for any task.
Creates a git worktree, sets up a tmux session, and launches your AI coding assistant.

Usage:
    lets "Fix issue #123"
    lets "Implement dark mode feature" --session frontend
    lets "Refactor auth module" -s dev --no-attach
"""

import os
import re
import shutil
import subprocess
import sys
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

import click
from rich.console import Console
from xdg_base_dirs import xdg_data_home

from .config import LetsSettings
from .launchers import (
    get_available_launchers,
    get_best_available_launcher,
    get_launcher,
)
from .launchers.tmux import TmuxLauncher

console = Console()


@dataclass
class WorktreeConfig:
    """Configuration for worktree and tmux setup."""

    current_dir: Path
    repo_name: str
    branch_name: str
    is_existing_branch: bool
    base_branch: str | None
    force: bool
    copy_env: bool
    env_files: tuple[str, ...]
    session: str
    task: str
    ai_tool: str
    worktree_dir: str | None
    launcher: str
    attach: bool


class Colors:
    """Terminal color codes for click.echo."""

    @staticmethod
    def success(msg: str) -> str:
        """Return success message with green styling."""
        return click.style(f"✓ {msg}", fg="green")

    @staticmethod
    def error(msg: str) -> str:
        """Return error message with red styling."""
        return click.style(f"✗ {msg}", fg="red")

    @staticmethod
    def info(msg: str) -> str:
        """Return info message with blue styling."""
        return click.style(f"→ {msg}", fg="blue")

    @staticmethod
    def warning(msg: str) -> str:
        """Return warning message with yellow styling."""
        return click.style(f"! {msg}", fg="yellow")


def run_command_with_spinner(
    cmd: list,
    spinner_text: str,
    *,
    capture_output: bool = False,
    check: bool = True,
    cwd: Path | None = None,
) -> str | None:
    """Run a command with a rich spinner."""
    with console.status(spinner_text, spinner="dots"):
        return run_command(cmd, capture_output=capture_output, check=check, cwd=cwd)


def run_command(
    cmd: list,
    *,
    capture_output: bool = False,
    check: bool = True,
    cwd: Path | None = None,
) -> str | None:
    """Run a shell command and optionally return output."""
    try:
        result = subprocess.run(
            cmd, capture_output=capture_output, text=True, check=check, cwd=cwd
        )
        if capture_output:
            return result.stdout.strip()
    except subprocess.CalledProcessError:
        if check:
            raise
        return None
    else:
        return None


def get_git_info() -> tuple[Path, str, str]:
    """Get git repository information."""
    try:
        repo_root = run_command(
            ["git", "rev-parse", "--show-toplevel"], capture_output=True
        )
    except subprocess.CalledProcessError:
        click.echo(Colors.error("Not in a git repository"))
        sys.exit(1)

    if repo_root is None:
        click.echo(Colors.error("Failed to get repository root"))
        sys.exit(1)
    repo_root = Path(repo_root)
    repo_name = repo_root.name

    # Get current branch
    current_branch = run_command(
        ["git", "branch", "--show-current"], capture_output=True
    )
    if current_branch is None:
        click.echo(Colors.error("Failed to get current branch"))
        sys.exit(1)

    return repo_root, repo_name, current_branch


def generate_branch_name(
    task: str, *, ai_tool: str = "claude", verbose: bool = False
) -> str:
    """Use AI to generate a branch name from task description."""
    prompt = (
        f"Based on this task, generate a short, descriptive git branch name "
        f"(lowercase, hyphen-separated, max 30 chars, no spaces or special chars "
        f"except hyphens). Only output the branch name, nothing else. Task: {task}"
    )

    try:
        if verbose:
            click.echo(Colors.info(f"Asking {ai_tool} for branch name..."))
            result = run_command(
                [ai_tool, "-p", prompt], capture_output=True, check=False
            )
        else:
            result = run_command_with_spinner(
                [ai_tool, "-p", prompt],
                f"Asking {ai_tool} for branch name...",
                capture_output=True,
                check=False,
            )

        if result:
            # Clean up the output
            branch_name = result.strip().split("\n")[-1]  # Get last line
            branch_name = re.sub(r"[^a-z0-9-]", "", branch_name.lower())
            branch_name = branch_name[:50]  # Limit length

            min_branch_length = 3
            if len(branch_name) >= min_branch_length:
                return branch_name
    except subprocess.CalledProcessError as e:
        if verbose:
            click.echo(Colors.warning(f"AI generation failed: {e}"))

    # Fallback: try to extract issue number
    issue_match = re.search(r"#(\d+)", task)
    if issue_match:
        return f"issue-{issue_match.group(1)}"

    # Final fallback: timestamp
    return f"task-{datetime.now(UTC).strftime('%Y%m%d-%H%M%S')}"


def get_worktree_base_dir(custom_dir: str | None = None) -> Path:
    """Get the base directory for worktrees with environment variable support."""
    if custom_dir:
        return Path(custom_dir).expanduser().resolve()
    # Check environment variable
    env_dir = os.environ.get("LETS_WORKTREE_DIR")
    if env_dir:
        return Path(env_dir).expanduser().resolve()
    # Use XDG Base Directory specification for cross-platform data directory
    return xdg_data_home() / "lets" / "worktrees"


def get_base_branch(custom_base: str | None = None) -> str:
    """Determine the base branch to use for the worktree."""
    if custom_base:
        try:
            run_command(
                ["git", "rev-parse", "--verify", custom_base], capture_output=True
            )
        except subprocess.CalledProcessError:
            click.echo(
                Colors.warning(f"Branch '{custom_base}' not found, trying defaults...")
            )
        else:
            return custom_base

    # Try common base branches
    for branch in ["origin/main", "origin/master", "main", "master"]:
        try:
            run_command(["git", "rev-parse", "--verify", branch], capture_output=True)
        except subprocess.CalledProcessError:
            continue
        else:
            return branch

    # Fallback to HEAD
    click.echo(Colors.warning("Using HEAD as base branch"))
    return "HEAD"


def branch_exists(branch_name: str) -> bool:
    """Check if a branch exists locally or remotely."""
    try:
        # Check local branches
        run_command(["git", "rev-parse", "--verify", branch_name], capture_output=True)
    except subprocess.CalledProcessError:
        try:
            # Check remote branches
            run_command(
                ["git", "rev-parse", "--verify", f"origin/{branch_name}"],
                capture_output=True,
            )
        except subprocess.CalledProcessError:
            return False
        else:
            return True
    else:
        return True


def handle_branch_conflict(base_name: str) -> tuple[str, bool]:
    """Handle branch name conflicts by prompting user for choice.

    Returns:
        tuple[str, bool]: (branch_name, is_existing_branch)
    """
    if not branch_exists(base_name):
        return base_name, False

    click.echo(Colors.warning(f"Branch '{base_name}' already exists"))

    if click.confirm("Use existing branch?", default=False):
        return base_name, True

    # Generate unique name if user wants a new branch
    click.echo(Colors.info("Generating new branch name..."))

    # Try with timestamp suffix
    timestamp = datetime.now(UTC).strftime("%H%M%S")
    candidate = f"{base_name}-{timestamp}"
    if not branch_exists(candidate):
        return candidate, False

    # Try with incremental numbers
    for i in range(1, 100):
        candidate = f"{base_name}-{i}"
        if not branch_exists(candidate):
            return candidate, False

    # Final fallback with more unique timestamp
    return f"{base_name}-{datetime.now(UTC).strftime('%Y%m%d-%H%M%S')}", False


def create_worktree(
    worktree_path: Path,
    branch_name: str,
    base_branch: str,
    *,
    is_existing_branch: bool = False,
) -> bool:
    """Create a new git worktree."""
    try:
        # Fetch latest changes
        run_command_with_spinner(
            ["git", "fetch", "origin"],
            "Fetching latest changes...",
            capture_output=True,
            check=False,
        )

        # Create the worktree
        if is_existing_branch:
            # Checkout existing branch
            run_command_with_spinner(
                [
                    "git",
                    "worktree",
                    "add",
                    str(worktree_path),
                    branch_name,
                ],
                f"Creating worktree from existing branch '{branch_name}'...",
                capture_output=True,
            )
        else:
            # Create new branch
            run_command_with_spinner(
                [
                    "git",
                    "worktree",
                    "add",
                    "-b",
                    branch_name,
                    str(worktree_path),
                    base_branch,
                ],
                f"Creating worktree with new branch '{branch_name}'...",
                capture_output=True,
            )

            # Set up upstream tracking for new branches
            try:
                run_command_with_spinner(
                    ["git", "push", "--set-upstream", "origin", branch_name],
                    f"Setting up upstream tracking for '{branch_name}'...",
                    cwd=worktree_path,
                    capture_output=True,
                    check=False,
                )
            except subprocess.CalledProcessError:
                # If push fails, set up tracking without pushing
                run_command_with_spinner(
                    ["git", "branch", "--set-upstream-to=origin/main", branch_name],
                    "Setting up local branch tracking...",
                    cwd=worktree_path,
                    capture_output=True,
                    check=False,
                )
    except subprocess.CalledProcessError as e:
        error_msg = str(e)
        if "already exists" in error_msg:
            click.echo(Colors.error(f"Branch '{branch_name}' already exists"))
            click.echo(
                Colors.info("This should not happen with unique name generation")
            )
        else:
            click.echo(Colors.error(f"Failed to create worktree: {e}"))
        return False
    else:
        return True


# Legacy tmux function - now handled by TmuxLauncher
# Kept for compatibility during migration
def setup_tmux(
    session: str,
    window_name: str,
    worktree_path: Path,
    task: str,
    ai_tool: str = "claude",
) -> bool:
    """Setup tmux session and window - DEPRECATED: Use TmuxLauncher instead."""
    settings = LetsSettings.load()
    settings.launchers.tmux.session = session
    launcher = TmuxLauncher(settings)
    return launcher.setup_workspace(worktree_path, window_name, task, ai_tool)


def copy_env_files(source_dir: Path, dest_dir: Path, env_files: list) -> None:
    """Copy environment files to new worktree."""
    for env_file in env_files:
        source_file = source_dir / env_file
        if source_file.exists():
            dest_file = dest_dir / env_file
            shutil.copy2(source_file, dest_file)
            click.echo(Colors.info(f"Copied {env_file} to new worktree"))


def handle_existing_worktree(
    worktree_path: Path,
    *,
    force: bool,
    branch_name: str,
    base_dir: Path,
    repo_name: str,
) -> tuple[Path, str]:
    """Handle existing worktree directory."""
    if force:
        click.echo(
            Colors.warning(f"Force removing existing directory: {worktree_path}")
        )
        run_command_with_spinner(
            ["git", "worktree", "remove", "--force", str(worktree_path)],
            "Removing existing worktree...",
            capture_output=True,
            check=False,
        )
        if worktree_path.exists():
            shutil.rmtree(worktree_path)
    else:
        click.echo(Colors.error(f"Directory already exists: {worktree_path}"))
        if click.confirm("Remove existing directory and continue?", default=False):
            run_command_with_spinner(
                ["git", "worktree", "remove", "--force", str(worktree_path)],
                "Removing existing worktree...",
                capture_output=True,
                check=False,
            )
            if worktree_path.exists():
                shutil.rmtree(worktree_path)
        else:
            # Use alternative name
            branch_name = f"{branch_name}-{datetime.now(UTC).strftime('%H%M%S')}"
            worktree_path = base_dir / repo_name / branch_name
            click.echo(Colors.info(f"Using alternative: {branch_name}"))

    return worktree_path, branch_name


def setup_repository_info(
    task: str, branch: str | None, ai_tool: str, *, verbose: bool
) -> tuple[Path, str, str, str, bool]:
    """Get repository info and handle branch name generation."""
    repo_root, repo_name, current_branch = get_git_info()
    current_dir = Path.cwd()

    click.echo(Colors.info(f"Task: {task}"))

    # Generate or use provided branch name
    branch_name = branch or generate_branch_name(task, ai_tool=ai_tool, verbose=verbose)

    # Handle branch conflicts
    branch_name, is_existing_branch = handle_branch_conflict(branch_name)

    click.echo(Colors.info(f"Branch name: {branch_name}"))
    if is_existing_branch:
        click.echo(Colors.info("Using existing branch"))

    return current_dir, repo_name, branch_name, current_branch, is_existing_branch


def setup_worktree_and_launcher(config: WorktreeConfig) -> tuple[Path, str]:
    """Create worktree and setup launcher environment."""
    # Get base directory for worktrees
    base_dir = get_worktree_base_dir(config.worktree_dir)
    worktree_path = base_dir / config.repo_name / config.branch_name
    branch_name = config.branch_name
    # Ensure the repository directory exists
    worktree_path.parent.mkdir(parents=True, exist_ok=True)

    # Check if path exists
    if worktree_path.exists():
        worktree_path, branch_name = handle_existing_worktree(
            worktree_path,
            force=config.force,
            branch_name=branch_name,
            base_dir=base_dir,
            repo_name=config.repo_name,
        )

    # Get base branch
    base_branch = get_base_branch(config.base_branch)

    # Create worktree
    if not create_worktree(
        worktree_path,
        branch_name,
        base_branch,
        is_existing_branch=config.is_existing_branch,
    ):
        sys.exit(1)

    # Copy env files
    if config.copy_env:
        copy_env_files(config.current_dir, worktree_path, list(config.env_files))

    # Load settings and get backend
    settings = LetsSettings.load()

    # Use session setting for tmux launcher
    if config.launcher == "tmux":
        settings.launchers.tmux.session = config.session
        settings.launchers.tmux.auto_attach = config.attach

    launcher = get_launcher(config.launcher, settings)

    # Setup launcher
    if not launcher.setup_workspace(
        worktree_path, branch_name, config.task, config.ai_tool
    ):
        click.echo(
            Colors.warning(
                f"{config.launcher.title()} setup failed, but worktree was "
                "created successfully"
            )
        )

    return worktree_path, branch_name


def handle_launcher_attachment(
    launcher_name: str, worktree_path: Path, branch_name: str, session: str
) -> None:
    """Handle launcher-specific attachment logic."""
    settings = LetsSettings.load()
    settings.launchers.tmux.session = session  # For tmux compatibility

    launcher = get_launcher(launcher_name, settings)
    launcher.handle_attachment(worktree_path, branch_name)


def _validate_command_exists(command: str) -> bool:
    """Check if a command exists in PATH."""
    return shutil.which(command) is not None


def print_workspace_summary(
    worktree_path: Path, branch_name: str, launcher_name: str, session: str = "dev"
) -> None:
    """Print workspace setup summary."""
    click.echo()
    click.echo(Colors.success("Workspace ready!"))
    click.echo()
    click.echo(Colors.info(f"Worktree: {worktree_path}"))
    click.echo(Colors.info(f"Branch: {branch_name}"))
    click.echo(Colors.info(f"Launcher: {launcher_name}"))

    # Get launcher-specific instructions
    settings = LetsSettings.load()
    settings.launchers.tmux.session = session  # For tmux compatibility
    launcher = get_launcher(launcher_name, settings)
    instructions = launcher.get_launch_instructions(worktree_path, branch_name)

    if instructions:
        click.echo()
        for instruction in instructions:
            click.echo(instruction)

    click.echo()
    click.echo("When you're done, remove the worktree:")
    click.echo(click.style(f"  git worktree remove {worktree_path}", fg="cyan"))


def _setup_launcher_config(settings: LetsSettings) -> None:
    """Configure launcher settings in the setup wizard."""
    click.echo(Colors.info("[1/6] Workspace Launcher"))
    click.echo("Choose how you want to launch your development environments:")
    click.echo("  1. tmux - Terminal multiplexer (recommended for power users)")
    click.echo("  2. terminal - New terminal window (simpler, works everywhere)")
    click.echo()

    launcher_choice = click.prompt(
        "Select launcher",
        type=click.Choice(["1", "2"], case_sensitive=False),
        default="1",
    )

    if launcher_choice == "1":
        settings.launcher = "tmux"
        click.echo(Colors.success("✓ Selected: tmux"))

        # Tmux-specific settings
        click.echo()
        click.echo(Colors.info("Tmux session configuration:"))
        default_session = click.prompt(
            "Default tmux session name", default="dev", type=str
        )
        settings.launchers.tmux.session = default_session

        auto_attach = click.confirm(
            "Auto-attach to tmux session after setup?", default=True
        )
        settings.launchers.tmux.auto_attach = auto_attach

    else:
        settings.launcher = "terminal"
        click.echo(Colors.success("✓ Selected: terminal"))

        # Terminal-specific settings
        click.echo()
        click.echo(Colors.info("Terminal command (leave empty for auto-detection):"))
        terminal_cmd = click.prompt(
            "Custom terminal command", default="", type=str, show_default=False
        )
        if terminal_cmd and _validate_command_exists(terminal_cmd.split()[0]):
            settings.launchers.terminal.terminal_command = terminal_cmd
        elif terminal_cmd:
            click.echo(
                Colors.warning(
                    f"Command '{terminal_cmd}' not found, using auto-detection"
                )
            )


def _setup_ai_tool_config(settings: LetsSettings) -> None:
    """Configure AI tool settings in the setup wizard."""
    click.echo()
    click.echo(Colors.info("[2/6] AI Tool"))
    click.echo("Choose your AI assistant for generating branch names:")
    click.echo("Examples: claude, chatgpt, copilot")

    ai_tool = click.prompt("AI tool command", default="claude", type=str)
    if _validate_command_exists(ai_tool):
        settings.ai_tool = ai_tool
        click.echo(Colors.success(f"✓ AI tool set to: {ai_tool}"))
    else:
        click.echo(
            Colors.warning(f"Command '{ai_tool}' not found, but will use it anyway")
        )
        settings.ai_tool = ai_tool


def _setup_editor_config(settings: LetsSettings) -> None:
    """Configure editor settings in the setup wizard."""
    click.echo()
    click.echo(Colors.info("[3/6] Editor"))
    detected_editor = os.environ.get("EDITOR", "")
    if detected_editor:
        click.echo(Colors.info(f"Detected editor from $EDITOR: {detected_editor}"))
        use_detected = click.confirm("Use this editor?", default=True)
        if use_detected:
            settings.editor_command = detected_editor
            click.echo(Colors.success(f"✓ Using editor: {detected_editor}"))
        else:
            custom_editor = click.prompt(
                "Enter your preferred editor command", type=str, default=""
            )
            if custom_editor and _validate_command_exists(custom_editor.split()[0]):
                settings.editor_command = custom_editor
                click.echo(Colors.success(f"✓ Editor set to: {custom_editor}"))
            elif custom_editor:
                click.echo(
                    Colors.warning(
                        f"Editor '{custom_editor}' not found, but will use it anyway"
                    )
                )
                settings.editor_command = custom_editor
    else:
        click.echo(Colors.info("No editor detected in $EDITOR environment variable"))
        custom_editor = click.prompt(
            "Enter your preferred editor command (or leave empty)", type=str, default=""
        )
        if custom_editor:
            settings.editor_command = custom_editor
            click.echo(Colors.success(f"✓ Editor set to: {custom_editor}"))


def _setup_worktree_config(settings: LetsSettings) -> None:
    """Configure worktree settings in the setup wizard."""
    click.echo()
    click.echo(Colors.info("[4/6] Worktree Storage"))

    default_dir = xdg_data_home() / "lets" / "worktrees"
    click.echo(f"Default worktree directory: {default_dir}")

    use_default_dir = click.confirm("Use default directory?", default=True)
    if not use_default_dir:
        custom_dir = click.prompt("Enter custom worktree directory", type=str)
        custom_path = Path(custom_dir).expanduser()
        if custom_path.parent.exists() or click.confirm(
            f"Create directory {custom_path.parent}?", default=True
        ):
            settings.worktree_base_dir = str(custom_path)
            click.echo(Colors.success(f"✓ Worktree directory set to: {custom_path}"))
        else:
            click.echo(Colors.info("Using default directory"))
    else:
        click.echo(Colors.success(f"✓ Using default directory: {default_dir}"))


def _setup_env_files_config(settings: LetsSettings) -> None:
    """Configure environment files settings in the setup wizard."""
    click.echo()
    click.echo(Colors.info("[5/6] Environment Files"))
    click.echo("Configure automatic copying of environment files to new worktrees.")

    copy_env = click.confirm("Copy environment files to new worktrees?", default=True)
    settings.copy_env_files = copy_env

    if copy_env:
        click.echo("Default environment files: .env, .env.local, .env.development")
        use_default_patterns = click.confirm("Use default file patterns?", default=True)
        if not use_default_patterns:
            patterns_input = click.prompt(
                "Enter comma-separated file patterns",
                default=".env,.env.local,.env.development",
            )
            patterns = [p.strip() for p in patterns_input.split(",") if p.strip()]
            settings.env_file_patterns = patterns
            click.echo(
                Colors.success(f"✓ Environment file patterns: {', '.join(patterns)}")
            )
        else:
            click.echo(Colors.success("✓ Using default environment file patterns"))
    else:
        click.echo(Colors.success("✓ Environment file copying disabled"))


def _setup_git_config(settings: LetsSettings) -> None:
    """Configure git settings in the setup wizard."""
    click.echo()
    click.echo(Colors.info("[6/6] Git Configuration"))
    click.echo("Configure default base branch for new worktrees.")

    use_auto_detect = click.confirm(
        "Auto-detect base branch (main/master)?", default=True
    )
    if not use_auto_detect:
        base_branch = click.prompt("Default base branch", default="main", type=str)
        settings.default_base_branch = base_branch
        click.echo(Colors.success(f"✓ Default base branch: {base_branch}"))
    else:
        click.echo(Colors.success("✓ Using auto-detection for base branch"))


def _show_setup_summary(settings: LetsSettings) -> None:
    """Show setup completion summary."""
    click.echo()
    click.echo("=" * 50)
    click.echo(Colors.success("🎉 Configuration Complete!"))
    click.echo("=" * 50)
    click.echo()
    click.echo("Summary of your settings:")
    click.echo(f"  Launcher: {settings.launcher}")
    click.echo(f"  AI Tool: {settings.ai_tool}")
    if settings.editor_command:
        click.echo(f"  Editor: {settings.editor_command}")
    if settings.launcher == "tmux":
        click.echo(f"  Tmux Session: {settings.launchers.tmux.session}")
        click.echo(f"  Auto-attach: {settings.launchers.tmux.auto_attach}")
    click.echo(f"  Environment Files: {'Yes' if settings.copy_env_files else 'No'}")
    if settings.copy_env_files:
        click.echo(f"  File Patterns: {', '.join(settings.env_file_patterns)}")
    click.echo()


def run_setup_wizard() -> LetsSettings:
    """Run the interactive setup wizard for first-time configuration."""
    click.echo()
    click.echo(Colors.info("🚀 Welcome to lets!"))
    click.echo(Colors.info("Let's set up your configuration for the best experience."))
    click.echo(Colors.info("This wizard will walk you through the key settings."))
    click.echo()

    # Initialize with defaults
    settings = LetsSettings()

    # Run each configuration step
    _setup_launcher_config(settings)
    _setup_ai_tool_config(settings)
    _setup_editor_config(settings)
    _setup_worktree_config(settings)
    _setup_env_files_config(settings)
    _setup_git_config(settings)

    # Show completion summary
    _show_setup_summary(settings)

    return settings


def check_and_run_setup_wizard() -> bool:
    """Check if setup wizard should run and run it if needed.

    Returns:
        bool: True if wizard was run, False if not needed
    """
    config_file = LetsSettings.get_config_file()

    if not config_file.exists():
        click.echo(Colors.info("No configuration found. Running first-time setup..."))

        # Run the setup wizard
        settings = run_setup_wizard()

        # Create config directory and save settings
        config_file.parent.mkdir(parents=True, exist_ok=True)
        settings.save()

        # Show completion message
        click.echo()
        click.echo(Colors.success("✨ Setup complete!"))
        click.echo(Colors.info(f"Configuration saved to: {config_file}"))
        click.echo(Colors.info("You can edit this file anytime to customize settings."))
        click.echo()

        return True

    return False


@click.command(name="lets")
@click.argument("task", metavar="TASK", required=False)
@click.option(
    "-s",
    "--session",
    default="dev",
    help="Tmux session name (tmux backend only)",
    show_default=True,
)
@click.option("-b", "--branch", help="Override branch name (default: auto-generated)")
@click.option("--base-branch", help="Base branch for worktree (default: auto-detect)")
@click.option(
    "--ai-tool", default="claude", help="AI tool command to use", show_default=True
)
@click.option(
    "--launcher",
    help="Launcher to use (tmux, terminal). Default: auto-detect or config",
)
@click.option(
    "--attach/--no-attach",
    default=True,
    help="Auto-attach/launch after setup (backend-dependent)",
)
@click.option(
    "--copy-env/--no-copy-env", default=True, help="Copy .env files to new worktree"
)
@click.option(
    "--env-files",
    multiple=True,
    default=[".env", ".env.local", ".env.development"],
    help="Environment files to copy (can be specified multiple times)",
)
@click.option(
    "-f",
    "--force",
    is_flag=True,
    help="Force remove existing worktree without prompting",
)
@click.option("-v", "--verbose", is_flag=True, help="Show verbose output")
@click.option(
    "--dry-run", is_flag=True, help="Show what would be done without actually doing it"
)
@click.option(
    "--worktree-dir",
    help="Base directory for worktrees (default: platform-specific data directory)",
)
@click.option(
    "--setup",
    is_flag=True,
    help="Run the interactive setup wizard",
)
@click.version_option(version="1.0.0", prog_name="lets")
@click.help_option("-h", "--help")
def main(  # noqa: PLR0913
    task: str | None,
    session: str,
    branch: str | None,
    base_branch: str | None,
    ai_tool: str,
    launcher: str | None,
    attach: bool,  # noqa: FBT001
    copy_env: bool,  # noqa: FBT001
    env_files: tuple[str, ...],
    force: bool,  # noqa: FBT001
    verbose: bool,  # noqa: FBT001
    dry_run: bool,  # noqa: FBT001
    worktree_dir: str | None,
    setup: bool,  # noqa: FBT001
) -> None:
    """Lets - Quickly create an AI-assisted development workspace for any task.

    TASK: The problem to solve or feature to implement.

    This tool creates an isolated git worktree with an auto-generated branch name,
    sets up a tmux session, and launches your AI coding assistant with the task
    description.

    Examples:
    # Solve a GitHub issue
    lets "Fix authentication bug in issue #234"

    # Tackle a specific bug report
    lets "Memory leak in user session handling"

    # Implement a new feature
    lets "Add OAuth2 integration for Google login"

    # Work on a feature in a specific session
    lets "Implement dark mode" --session frontend

    # Handle performance improvements
    lets "Optimize database queries for user dashboard"

    # Address security vulnerabilities
    lets "Fix XSS vulnerability in comment system"

    # Use a custom branch name
    lets "Refactor database layer" --branch db-refactor

    # Work on documentation
    lets "Update API documentation for v2 endpoints"

    # Don't attach to tmux immediately
    lets "Debug performance issue" --no-attach

    # Handle technical debt
    lets "Remove deprecated jQuery dependencies"

    # Force remove existing worktree
    lets "Emergency hotfix" --force

    # Work on testing
    lets "Add integration tests for payment flow"

    # Preview what would happen
    lets "Major refactor" --dry-run

    """
    # Handle --setup flag first
    if setup:
        config_file = LetsSettings.get_config_file()
        if config_file.exists():
            click.echo(Colors.warning("Configuration file already exists."))
            if not click.confirm("Do you want to reconfigure?", default=False):
                click.echo(Colors.info("Setup cancelled."))
                return

        # Run the setup wizard
        settings = run_setup_wizard()

        # Create config directory and save settings
        config_file.parent.mkdir(parents=True, exist_ok=True)
        settings.save()

        # Show completion message
        click.echo()
        click.echo(Colors.success("✨ Setup complete!"))
        click.echo(Colors.info(f"Configuration saved to: {config_file}"))
        click.echo(Colors.info("You can edit this file anytime to customize settings."))
        return

    # Run setup wizard if no config exists (first-time use)
    wizard_ran = check_and_run_setup_wizard()
    if wizard_ran and not click.confirm("Continue with current task?", default=True):
        click.echo(
            Colors.info("Setup complete. Run 'lets --help' for usage information.")
        )
        return

    # Validate task is provided when not using --setup
    if not task:
        click.echo(Colors.error("TASK argument is required (unless using --setup)"))
        click.echo("Run 'lets --help' for usage information")
        sys.exit(1)

    if dry_run:
        click.echo(Colors.warning("DRY RUN MODE - No changes will be made"))

    # Load settings
    settings = LetsSettings.load()

    # Use config values as defaults if not explicitly provided via CLI
    # Note: We need to check if values were explicitly provided vs using Click defaults
    effective_ai_tool = settings.ai_tool if ai_tool == "claude" else ai_tool
    effective_copy_env = settings.copy_env_files if copy_env is True else copy_env
    effective_env_files = (
        tuple(settings.env_file_patterns)
        if env_files == (".env", ".env.local", ".env.development")
        else env_files
    )
    effective_worktree_dir = worktree_dir or settings.worktree_base_dir or None
    effective_base_branch = base_branch or settings.default_base_branch or None

    # Setup repository info and branch name
    current_dir, repo_name, branch_name, current_branch, is_existing_branch = (
        setup_repository_info(task, branch, effective_ai_tool, verbose=verbose)
    )

    # Determine launcher to use
    selected_launcher = (
        launcher
        or settings.launcher
        or get_best_available_launcher(settings, current_dir)
    )

    # Validate launcher exists
    available_launchers = get_available_launchers(settings)
    if selected_launcher not in available_launchers:
        click.echo(Colors.error(f"Launcher '{selected_launcher}' is not available"))
        click.echo(
            Colors.info(f"Available launchers: {', '.join(available_launchers)}")
        )
        sys.exit(1)

    click.echo(Colors.info(f"Using launcher: {selected_launcher}"))

    # Handle dry run mode
    if dry_run:
        base_dir = get_worktree_base_dir(effective_worktree_dir)
        worktree_path = base_dir / repo_name / branch_name
        click.echo(Colors.info(f"Would create worktree at: {worktree_path}"))
        click.echo(
            Colors.info(
                f"Would use base branch: {get_base_branch(effective_base_branch)}"
            )
        )
        click.echo(Colors.info(f"Would use launcher: {selected_launcher}"))
        cmd_preview = f"{effective_ai_tool} --dangerously-skip-permissions '{task}'"
        click.echo(Colors.info(f"Would run: {cmd_preview}"))
        return

    # Setup worktree and backend
    config = WorktreeConfig(
        current_dir=current_dir,
        repo_name=repo_name,
        branch_name=branch_name,
        is_existing_branch=is_existing_branch,
        base_branch=effective_base_branch,
        force=force,
        copy_env=effective_copy_env,
        env_files=effective_env_files,
        session=session,
        task=task,
        ai_tool=effective_ai_tool,
        worktree_dir=effective_worktree_dir,
        launcher=selected_launcher,
        attach=attach,
    )
    worktree_path, branch_name = setup_worktree_and_launcher(config)

    # Print summary
    print_workspace_summary(worktree_path, branch_name, selected_launcher, session)

    # Handle backend attachment
    handle_launcher_attachment(selected_launcher, worktree_path, branch_name, session)


if __name__ == "__main__":
    main()
