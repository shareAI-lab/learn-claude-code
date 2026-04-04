# UV Package Manager — Advanced Reference

Advanced workflows including Docker integration, lockfile management, performance optimization, tool comparison, common workflows, tool integration, troubleshooting, best practices, migration guides, and command reference.

## Advanced Workflows

### Pattern 12: Monorepo Support

```bash
# Project structure
# monorepo/
#   packages/
#     package-a/
#       pyproject.toml
#     package-b/
#       pyproject.toml
#   pyproject.toml (root)

# Root pyproject.toml
[tool.uv.workspace]
members = ["packages/*"]

# Install all workspace packages
uv sync

# Add workspace dependency
uv add --path ./packages/package-a
```

### Pattern 13: CI/CD Integration

```yaml
# .github/workflows/test.yml
name: Tests

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest

    steps:
      - uses: actions/checkout@v4

      - name: Install uv
        uses: astral-sh/setup-uv@v2
        with:
          enable-cache: true

      - name: Set up Python
        run: uv python install 3.12

      - name: Install dependencies
        run: uv sync --all-extras --dev

      - name: Run tests
        run: uv run pytest

      - name: Run linting
        run: |
          uv run ruff check .
          uv run black --check .
```

### Pattern 14: Docker Integration

```dockerfile
# Dockerfile
FROM python:3.12-slim

# Install uv
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

# Set working directory
WORKDIR /app

# Copy dependency files
COPY pyproject.toml uv.lock ./

# Install dependencies
RUN uv sync --frozen --no-dev

# Copy application code
COPY . .

# Run application
CMD ["uv", "run", "python", "app.py"]
```

**Optimized multi-stage build:**

```dockerfile
# Multi-stage Dockerfile
FROM python:3.12-slim AS builder

# Install uv
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

WORKDIR /app

# Install dependencies to venv
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev --no-editable

# Runtime stage
FROM python:3.12-slim

WORKDIR /app

# Copy venv from builder
COPY --from=builder /app/.venv .venv
COPY . .

# Use venv
ENV PATH="/app/.venv/bin:$PATH"

CMD ["python", "app.py"]
```

### Pattern 15: Lockfile Workflows

```bash
# Create lockfile (uv.lock)
uv lock

# Install from lockfile (exact versions)
uv sync --frozen

# Update lockfile without installing
uv lock --no-install

# Upgrade specific package in lock
uv lock --upgrade-package requests

# Check if lockfile is up to date
uv lock --check

# Export lockfile to requirements.txt
uv export --format requirements-txt > requirements.txt

# Export with hashes for security
uv export --format requirements-txt --hash > requirements.txt
```

## Performance Optimization

### Pattern 16: Using Global Cache

```bash
# UV automatically uses global cache at:
# Linux: ~/.cache/uv
# macOS: ~/Library/Caches/uv
# Windows: %LOCALAPPDATA%\uv\cache

# Clear cache
uv cache clean

# Check cache size
uv cache dir
```

### Pattern 17: Parallel Installation

```bash
# UV installs packages in parallel by default

# Control parallelism
uv pip install --jobs 4 package1 package2

# No parallel (sequential)
uv pip install --jobs 1 package
```

### Pattern 18: Offline Mode

```bash
# Install from cache only (no network)
uv pip install --offline package

# Sync from lockfile offline
uv sync --frozen --offline
```

## Comparison with Other Tools

### uv vs pip

```bash
# pip
python -m venv .venv
source .venv/bin/activate
pip install requests pandas numpy
# ~30 seconds

# uv
uv venv
uv add requests pandas numpy
# ~2 seconds (10-15x faster)
```

### uv vs poetry

```bash
# poetry
poetry init
poetry add requests pandas
poetry install
# ~20 seconds

# uv
uv init
uv add requests pandas
uv sync
# ~3 seconds (6-7x faster)
```

### uv vs pip-tools

```bash
# pip-tools
pip-compile requirements.in
pip-sync requirements.txt
# ~15 seconds

# uv
uv lock
uv sync --frozen
# ~2 seconds (7-8x faster)
```

## Common Workflows

### Pattern 19: Starting a New Project

```bash
# Complete workflow
uv init my-project
cd my-project

# Set Python version
uv python pin 3.12

# Add dependencies
uv add fastapi uvicorn pydantic

# Add dev dependencies
uv add --dev pytest black ruff mypy

# Create structure
mkdir -p src/my_project tests

# Run tests
uv run pytest

# Format code
uv run black .
uv run ruff check .
```

### Pattern 20: Maintaining Existing Project

```bash
# Clone repository
git clone https://github.com/user/project.git
cd project

# Install dependencies (creates venv automatically)
uv sync

# Install with dev dependencies
uv sync --all-extras

# Update dependencies
uv lock --upgrade

# Run application
uv run python app.py

# Run tests
uv run pytest

# Add new dependency
uv add new-package

# Commit updated files
git add pyproject.toml uv.lock
git commit -m "Add new-package dependency"
```

## Tool Integration

### Pattern 21: Pre-commit Hooks

```yaml
# .pre-commit-config.yaml
repos:
  - repo: local
    hooks:
      - id: uv-lock
        name: uv lock
        entry: uv lock
        language: system
        pass_filenames: false

      - id: ruff
        name: ruff
        entry: uv run ruff check --fix
        language: system
        types: [python]

      - id: black
        name: black
        entry: uv run black
        language: system
        types: [python]
```

### Pattern 22: VS Code Integration

```json
// .vscode/settings.json
{
  "python.defaultInterpreterPath": "${workspaceFolder}/.venv/bin/python",
  "python.terminal.activateEnvironment": true,
  "python.testing.pytestEnabled": true,
  "python.testing.pytestArgs": ["-v"],
  "python.linting.enabled": true,
  "python.formatting.provider": "black",
  "[python]": {
    "editor.defaultFormatter": "ms-python.black-formatter",
    "editor.formatOnSave": true
  }
}
```

## Troubleshooting

### Common Issues

```bash
# Issue: uv not found
# Solution: Add to PATH or reinstall
echo 'export PATH="$HOME/.cargo/bin:$PATH"' >> ~/.bashrc

# Issue: Wrong Python version
# Solution: Pin version explicitly
uv python pin 3.12
uv venv --python 3.12

# Issue: Dependency conflict
# Solution: Check resolution
uv lock --verbose

# Issue: Cache issues
# Solution: Clear cache
uv cache clean

# Issue: Lockfile out of sync
# Solution: Regenerate
uv lock --upgrade
```

## Best Practices

### Project Setup

1. **Always use lockfiles** for reproducibility
2. **Pin Python version** with .python-version
3. **Separate dev dependencies** from production
4. **Use uv run** instead of activating venv
5. **Commit uv.lock** to version control
6. **Use --frozen in CI** for consistent builds
7. **Leverage global cache** for speed
8. **Use workspace** for monorepos
9. **Export requirements.txt** for compatibility
10. **Keep uv updated** for latest features

### Performance Tips

```bash
# Use frozen installs in CI
uv sync --frozen

# Use offline mode when possible
uv sync --offline

# Parallel operations (automatic)
# uv does this by default

# Reuse cache across environments
# uv shares cache globally

# Use lockfiles to skip resolution
uv sync --frozen  # skips resolution
```

## Migration Guide

### From pip + requirements.txt

```bash
# Before
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

# After
uv venv
uv pip install -r requirements.txt
# Or better:
uv init
uv add -r requirements.txt
```

### From Poetry

```bash
# Before
poetry install
poetry add requests

# After
uv sync
uv add requests

# Keep existing pyproject.toml
# uv reads [project] and [tool.poetry] sections
```

### From pip-tools

```bash
# Before
pip-compile requirements.in
pip-sync requirements.txt

# After
uv lock
uv sync --frozen
```

## Command Reference

### Essential Commands

```bash
# Project management
uv init [PATH]              # Initialize project
uv add PACKAGE              # Add dependency
uv remove PACKAGE           # Remove dependency
uv sync                     # Install dependencies
uv lock                     # Create/update lockfile

# Virtual environments
uv venv [PATH]              # Create venv
uv run COMMAND              # Run in venv

# Python management
uv python install VERSION   # Install Python
uv python list              # List installed Pythons
uv python pin VERSION       # Pin Python version

# Package installation (pip-compatible)
uv pip install PACKAGE      # Install package
uv pip uninstall PACKAGE    # Uninstall package
uv pip freeze               # List installed
uv pip list                 # List packages

# Utility
uv cache clean              # Clear cache
uv cache dir                # Show cache location
uv --version                # Show version
```