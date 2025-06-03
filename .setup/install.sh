#!/usr/bin/env bash
# Bootstrap a local development environment
set -euo pipefail

# Move to repo root (the parent directory of this script)
REPO_DIR="$(cd "$(dirname "$0")/.." && pwd)"
cd "$REPO_DIR"

# 1. create & activate a Python 3.11 virtual-env
python3.11 -m venv .venv
source .venv/bin/activate

# 2. upgrade base packaging tooling
python -m pip install --upgrade pip setuptools wheel

# 3. install ALL project dependencies declared in pyproject.toml
#    (runtime + tests + linting + docs)
pip install -e .

# 4. sanity checks
ruff check .
pyright
pytest -q