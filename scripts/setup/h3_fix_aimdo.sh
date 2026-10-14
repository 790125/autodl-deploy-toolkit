#!/usr/bin/env bash
set -euo pipefail
export PATH="/root/autodl-tmp/venv_h3/bin:/usr/bin:/root/miniconda3/bin:$PATH"
cd /root/autodl-tmp/ComfyUI
if [ -f /root/autodl-tmp/comfy.pid ]; then
  kill "$(cat /root/autodl-tmp/comfy.pid)" 2>/dev/null || true
  rm -f /root/autodl-tmp/comfy.pid
fi
grep -viE '^(torch|torchvision|torchaudio|xformers)([>=< ]|$)' requirements.txt > /tmp/comfy-req2.txt
python -m pip install -r /tmp/comfy-req2.txt
python - <<'PY'
import comfy_aimdo, pkgutil, os
print("comfy_aimdo", getattr(comfy_aimdo, "__version__", "?"), comfy_aimdo.__file__)
print("has malloc_graph", any(m.name=="malloc_graph" for m in pkgutil.iter_modules(comfy_aimdo.__path__)))
PY
export PYTORCH_CUDA_ALLOC_CONF=expandable_segments:True
nohup python main.py --listen 0.0.0.0 --port 6006 --preview-method none >/root/autodl-tmp/comfy.log 2>&1 < /dev/null &
echo $! > /root/autodl-tmp/comfy.pid
echo START "$(cat /root/autodl-tmp/comfy.pid)"
sleep 18
tail -50 /root/autodl-tmp/comfy.log
