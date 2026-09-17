#!/usr/bin/env bash
set -euo pipefail

PYTHON="${PYTHON:-/opt/eye-venv/bin/python}"

"$PYTHON" --version
command -v bash git gcc g++ cmake ninja make
gcc --version | head -n 1
g++ --version | head -n 1
cmake --version | head -n 1
"$PYTHON" - <<'PY'
import cv2
import numpy
import onnxruntime
import torch
import torchmcubes
import trimesh
from tsr.system import TSR
from tsr.utils import remove_background, resize_foreground

print({
    "cuda": torch.cuda.is_available(),
    "numpy": numpy.__version__,
    "opencv": cv2.__version__,
    "onnxruntime": onnxruntime.__version__,
    "torch": torch.__version__,
    "trimesh": trimesh.__version__,
})
PY
"$PYTHON" -m pip check