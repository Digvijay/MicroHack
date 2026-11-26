#!/usr/bin/env bash
# Runs once when the Codespace / Dev Container is created (postCreateCommand).
# Safe to re-run manually:  bash .devcontainer/post-create.sh
set -euo pipefail

HACK_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$HACK_DIR"

PYTHON_BIN="$(command -v python3 || command -v python || true)"
if [ -z "$PYTHON_BIN" ]; then
  echo "ERROR: Python is missing. Rebuild the container with the 'Azure / AI / Microsoft IQ' configuration." >&2
  exit 1
fi
"$PYTHON_BIN" --version

echo "==> Installing uv"
export PATH="$HOME/.local/bin:$PATH"
if ! command -v uv >/dev/null 2>&1; then
  "$PYTHON_BIN" -m pip install --quiet --upgrade uv \
    || curl -LsSf https://astral.sh/uv/install.sh | env UV_INSTALL_DIR="$HOME/.local/bin" UV_NO_MODIFY_PATH=1 sh
fi
grep -q 'HOME/.local/bin' "$HOME/.bashrc" 2>/dev/null || echo 'export PATH="$HOME/.local/bin:$PATH"' >> "$HOME/.bashrc"

echo "==> Installing dependencies (uv sync)"
if [ -d src/.venv ] && [ ! -w src/.venv ]; then
  sudo chown "$(id -u):$(id -g)" src/.venv
fi
( cd src && uv sync --python "$PYTHON_BIN" --link-mode=copy )
grep -q 'src/.venv/bin' "$HOME/.bashrc" 2>/dev/null || echo "export PATH=\"$HACK_DIR/src/.venv/bin:\$PATH\"" >> "$HOME/.bashrc"

echo "==> Seeding src/.env"
if [ ! -f src/.env ]; then
  cp .env.example src/.env
  echo "    Created src/.env from .env.example"
else
  echo "    src/.env already exists, leaving it unchanged"
fi

echo ""
echo "============================================================"
echo " Ready. Next steps (challenges/challenge-01.md):"
echo "   1. az login --use-device-code   (your lab account)"
echo "   2. Paste your lab values into src/.env"
echo "   3. caldova check"
echo "============================================================"