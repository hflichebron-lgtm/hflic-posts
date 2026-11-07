#!/usr/bin/env bash
# One-time setup for tools/render.py (carousel slides) and tools/reel.py (reels).
# Installs the fonts, the free Kokoro voice (kokoro-onnx) and downloads its model files into tools/models.
set -euo pipefail
cd "$(dirname "$0")"
[ -d node_modules/@fontsource/inter ] || npm install --silent
python3 -c "import kokoro_onnx, soundfile" 2>/dev/null || pip install -q --break-system-packages kokoro-onnx soundfile
python3 -c "import playwright" 2>/dev/null || pip install -q --break-system-packages playwright
mkdir -p models
base=https://github.com/thewh1teagle/kokoro-onnx/releases/download/model-files-v1.0
for f in kokoro-v1.0.int8.onnx voices-v1.0.bin; do
  [ -s "models/$f" ] || curl -sSL -o "models/$f" "$base/$f"
done
echo "Setup done."
