#!/usr/bin/env bash
# Simple wrapper around pip-audit for dependency vulnerability scanning
set -euo pipefail

if ! command -v pip-audit >/dev/null 2>&1; then
    echo "pip-audit not found. Install with 'pip install pip-audit'" >&2
    exit 1
fi

pip-audit "$@"
