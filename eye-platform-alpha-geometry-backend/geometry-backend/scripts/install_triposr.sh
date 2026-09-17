#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
VENV="${VENV:-$ROOT/.venv}"
SOURCE_DIR="${EYE_TRIPOSR_SOURCE:-/opt/triposr}"
TORCH_INDEX_URL="${EYE_TORCH_INDEX_URL:-https://download.pytorch.org/whl/cpu}"

if [[ ! -x "$VENV/bin/python" ]]; then
  echo "Create the Python 3.11 virtual environment before installing TripoSR." >&2
  exit 1
fi

if [[ ! -d "$SOURCE_DIR/.git" ]]; then
  git clone --depth 1 https://github.com/VAST-AI-Research/TripoSR.git "$SOURCE_DIR"
fi

"$VENV/bin/pip" install --upgrade pip setuptools
"$VENV/bin/pip" install --index-url "$TORCH_INDEX_URL" torch torchvision
"$VENV/bin/pip" install "numpy==1.26.4"
"$VENV/bin/pip" install scikit-build-core pybind11
"$VENV/bin/pip" install --no-build-isolation git+https://github.com/tatsy/torchmcubes.git
grep -Ev 'torchmcubes|^gradio$|^opencv-python-headless' "$SOURCE_DIR/requirements.txt" | "$VENV/bin/pip" install -r /dev/stdin
"$VENV/bin/pip" install "numpy==1.26.4" "opencv-python-headless==4.11.0.86"
"$VENV/bin/pip" install onnxruntime
"$VENV/bin/python" -m pip check
echo "TripoSR source is available at $SOURCE_DIR"