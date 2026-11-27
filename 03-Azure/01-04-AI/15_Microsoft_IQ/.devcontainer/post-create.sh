#!/usr/bin/env bash
# Runs once when the Codespace / Dev Container is created (postCreateCommand).
# Safe to re-run manually:  bash .devcontainer/post-create.sh
# Installs Jupyter and the notebook packages (through the Microsoft package proxy)
# into .venv. The Azure CLI comes from the dev container feature.
set -euo pipefail

HACK_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$HACK_DIR"
INDEX_URL="https://packagefeedproxy.microsoft.io/pypi/simple/"

PYTHON_BIN="$(command -v python3 || command -v python || true)"
if [ -z "$PYTHON_BIN" ]; then
  echo "ERROR: Python is missing. Rebuild the container with the 'Azure / AI / Microsoft IQ' configuration." >&2
  exit 1
fi
"$PYTHON_BIN" --version

echo "==> Creating .venv and installing the notebook packages"
if [ -d .venv ] && [ ! -w .venv ]; then
  sudo chown "$(id -u):$(id -g)" .venv
fi
if [ ! -x .venv/bin/python ]; then
  "$PYTHON_BIN" -m venv .venv
fi
.venv/bin/python -m pip install --quiet --upgrade pip --index-url "$INDEX_URL"
.venv/bin/python -m pip install --quiet --index-url "$INDEX_URL" jupyter -r notebooks/requirements.txt
.venv/bin/python -m ipykernel install --user --name microsoft-iq --display-name "Python (Microsoft IQ)" >/dev/null
grep -q "$HACK_DIR/.venv/bin" "$HOME/.bashrc" 2>/dev/null || echo "export PATH=\"$HACK_DIR/.venv/bin:\$PATH\"" >> "$HOME/.bashrc"

echo ""
echo "============================================================"
echo " Ready. Next step (challenges/challenge-01.md):"
echo "   bash create-env.sh     (signs you in once and fills .env)"
echo "============================================================"