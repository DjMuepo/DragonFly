#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
VENV="$ROOT/.venv"
SOURCE_DIR="${EYE_TRIPOSR_SOURCE:-/opt/triposr}"

if [[ ! -x "$VENV/bin/python" ]]; then
  echo "Create the Python 3.11 virtual environment before installing TripoSR." >&2
  exit 1
fi

if [[ ! -d "$SOURCE_DIR/.git" ]]; then
  git clone --depth 1 https://github.com/VAST-AI-Research/TripoSR.git "$SOURCE_DIR"
fi

"$VENV/bin/pip" install --upgrade pip setuptools
"$VENV/bin/pip" install torch torchvision
"$VENV/bin/pip" install -r "$SOURCE_DIR/requirements.txt"
echo "TripoSR source is available at $SOURCE_DIR"