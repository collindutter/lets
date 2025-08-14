# Testing and Code Coverage Setup

This document describes the testing infrastructure and code coverage setup for the "lets" project.

## Overview

We've successfully added comprehensive unit testing and code coverage measurement to track progress and ensure code quality.

## Test Infrastructure

### Dependencies
- **pytest**: Modern Python testing framework
- **pytest-cov**: Coverage plugin for pytest  
- **pytest-mock**: Enhanced mocking capabilities

### Configuration Files
- `pyproject.toml`: Pytest and coverage configuration
- `.coveragerc`: Additional coverage settings
- `tests/conftest.py`: Shared test fixtures and utilities

## Test Structure

```
tests/
├── __init__.py
├── conftest.py              # Shared fixtures and test utilities
├── test_cli.py              # Tests for main CLI functionality
├── test_git_operations.py   # Tests for git operations and worktree management
└── test_models.py           # Tests for data models and utility classes
```

## Test Coverage

### Current Coverage: 42.58%

| Module | Coverage | Missing Lines |
|--------|----------|---------------|
| src/lets/cli.py | 56.15% | Core CLI functionality |
| src/lets/config.py | 73.81% | Configuration management |
| src/lets/launchers/base.py | 47.50% | Base launcher class |
| src/lets/launchers/__init__.py | 22.45% | Launcher initialization |
| src/lets/launchers/terminal.py | 14.44% | Terminal launcher |
| src/lets/launchers/tmux.py | 13.48% | Tmux launcher |
| src/lets/config_cli.py | 0.00% | Configuration CLI (not tested) |

## Test Categories

### Unit Tests (54 tests total)
- **Command execution**: Testing git commands and shell operations
- **Git operations**: Repository info, branch management, worktree creation
- **Branch naming**: AI-powered branch name generation and conflict resolution
- **Configuration**: Worktree and launcher configuration
- **Data models**: WorktreeConfig dataclass and Colors utility class
- **CLI interface**: Command-line argument parsing and dry-run mode

## Running Tests

### Basic Commands
```bash
# Run all tests
mise run test
# or
uv run pytest

# Run with coverage
mise run test:coverage
# or  
uv run pytest --cov=src --cov-report=html --cov-report=term-missing

# Run specific test categories
mise run test:unit        # Unit tests only
mise run test:integration # Integration tests only

# Generate XML coverage report (CI/CD)
mise run test:coverage-xml

# Watch mode for development
mise run test:watch
```

### Test Markers
- `@pytest.mark.unit`: Unit tests
- `@pytest.mark.integration`: Integration tests
- `@pytest.mark.slow`: Slow-running tests

## Coverage Reports

### Terminal Output
Coverage results are displayed in the terminal with missing line numbers.

### HTML Reports
Detailed HTML coverage reports are generated in `htmlcov/` directory:
```bash
open htmlcov/index.html  # Open coverage report in browser
```

### XML Reports
XML coverage reports for CI/CD integration are saved to `coverage.xml`.

## Key Test Features

### Mocking Strategy
- Git commands are mocked to avoid requiring actual git repositories
- File system operations use temporary directories
- External tools (AI assistants) are mocked for reliable testing

### Fixtures
- `temp_dir`: Temporary directory for file operations
- `mock_git_repo`: Mocked git repository environment
- `sample_worktree_config`: Sample configuration for testing

### Coverage Configuration
- Source tracking: `src/` directory
- Branch coverage: Enabled for thorough testing
- Exclusions: Test files, debug code, abstract methods
- Threshold: Currently set to 40% (adjustable)

## Future Improvements

To reach higher coverage (60-80%), consider adding tests for:

1. **Launcher modules** (`tmux.py`, `terminal.py`): 
   - Tmux session management
   - Terminal window creation
   - Process launching

2. **Configuration CLI** (`config_cli.py`):
   - Interactive setup wizard
   - Configuration validation
   - User input handling

3. **Error handling paths**:
   - Network failures
   - Permission errors
   - Invalid user inputs

4. **Integration tests**:
   - End-to-end workflows
   - Real git operations (in isolated environments)
   - Cross-platform compatibility

## Development Workflow

1. **Write tests first** (TDD approach recommended)
2. **Run tests frequently** during development
3. **Check coverage** to identify untested code paths
4. **Use watch mode** for continuous feedback
5. **Review HTML reports** for detailed coverage analysis

The testing infrastructure is now fully operational and ready to support ongoing development while measuring progress through code coverage metrics.