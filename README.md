# 🚀 Lets

Your AI-powered development companion that creates isolated git worktrees with auto-generated branch names, sets up tmux sessions, and launches your AI coding assistant for specific tasks.

## 💭 Why "Lets"?

The name comes from the natural collaboration pattern when working with AI assistants. Instead of working alone, you find yourself saying "let's do this" or "let's solve that" - acknowledging that both you and your AI assistant are contributing to the solution. This tool embodies that collaborative spirit by setting up the perfect environment for human-AI pair programming.

## ✨ Features

- 🌳 **Git Worktree Management** - Creates isolated worktrees for each task
- 🤖 **AI-Generated Branch Names** - Uses AI to generate descriptive branch names from task descriptions
- 🖥️ **Tmux Integration** - Automatically sets up tmux sessions and windows
- 📁 **Environment File Copying** - Copies `.env` files to new worktrees
- 🔀 **Branch Conflict Resolution** - Handles existing branches with interactive prompts
- ⚡ **Quick Setup** - Get from task description to coding in seconds

## 📦 Installation

### Prerequisites

- Python 3.12+
- [uv](https://docs.astral.sh/uv/) - Python package manager
- Git
- tmux
- An AI tool (default: `claude`)

### Install from GitHub

```bash
# First install uv if you haven't already
curl -LsSf https://astral.sh/uv/install.sh | sh

# Install lets directly from GitHub
uv tool install git+https://github.com/collindutter/lets
```

## 🛠️ Usage

**Important**: Make sure you're in your git repository before running `lets`. It creates worktrees in your XDG data directory (typically `~/.local/share/lets/worktrees/`).

### Basic Usage

```bash
# Start from your project directory
cd /path/to/your/project

# Now you're ready to tackle any task
lets "Fix authentication bug in issue #234"

# Work on a feature
lets "Implement dark mode for the dashboard"

# Prefer your own branch name? No problem
lets "Refactor database layer" --branch db-refactor
```

### Advanced Options

```bash
# Use a specific tmux session
lets "Debug performance issue" --session backend

# Don't attach to tmux immediately
lets "Emergency hotfix" --no-attach

# Force remove existing worktree without prompting
lets "Quick fix" --force

# Use a different AI tool
lets "Add new feature" --ai-tool cursor

# Specify base branch
lets "Hotfix production bug" --base-branch production

# Preview what would happen
lets "Major refactor" --dry-run
```

## 🔄 How It Works

1. **Branch Generation**: Uses AI to generate a descriptive branch name from your task description
2. **Worktree Creation**: Creates a new git worktree in a sibling directory
3. **Environment Setup**: Copies environment files (`.env`, `.env.local`, etc.) to the new worktree
4. **Tmux Session**: Creates or reuses a tmux session with a new window for your task
5. **AI Assistant**: Launches your AI coding assistant with the task description

## 💡 Workflow Example

```bash
# Starting from your main project directory
$ lets "Fix user login validation bug"

→ Task: Fix user login validation bug
✓ Generating branch name...
→ Branch name: fix-user-login-validation
→ Worktree: ~/.local/share/lets/worktrees/myapp-fix-user-login-validation
→ Branch: fix-user-login-validation
→ Tmux: dev:fix-user-login-validation

✓ Workspace ready!

# Your AI assistant is now running in the new tmux window
# When done, clean up:
$ git worktree remove ~/.local/share/lets/worktrees/myapp-fix-user-login-validation
```

## ⚙️ Configuration

Run the setup wizard to configure your preferences:
```bash
lets --setup
```

Configuration is stored in your XDG config directory (typically `~/.config/lets/config.toml`).

### Environment Files

By default, lets copies these files to new worktrees:
- `.env`
- `.env.local` 
- `.env.development`

Customize with:
```bash
lets "Task" --env-files .env --env-files .env.staging
```

### AI Tool

Change the default AI tool:
```bash
lets "Task" --ai-tool cursor
# or
lets "Task" --ai-tool "custom-ai-command"
```

## 📚 Commands Reference

```
Usage: lets [OPTIONS] TASK

Options:
  -s, --session TEXT          Tmux session name [default: dev]
  -b, --branch TEXT           Override branch name (default: auto-generated)
  --base-branch TEXT          Base branch for worktree (default: auto-detect)
  --ai-tool TEXT              AI tool command to use [default: claude]
  --attach/--no-attach        Attach to tmux session after setup [default: attach]
  --copy-env/--no-copy-env    Copy .env files to new worktree [default: copy-env]
  --env-files TEXT            Environment files to copy (multiple allowed)
  -f, --force                 Force remove existing worktree without prompting
  -v, --verbose               Show verbose output
  --dry-run                   Show what would be done without doing it
  --version                   Show version
  -h, --help                  Show help
```

## 🔧 Development

### Setup

```bash
# Install dependencies
mise run install

# Format code
mise run format

# Run checks
mise run check
```

### Code Quality Tools

- **Ruff**: Linting and formatting
- **Pyright**: Type checking
