#!/usr/bin/env bash
# Fast kohya on existing venv_h3 torch. Do not reinstall torch.
set -euo pipefail
export PATH="/root/autodl-tmp/venv_h3/bin:/usr/bin:/root/miniconda3/bin:$PATH"
PY=/root/autodl-tmp/venv_h3/bin/python
export PYTHONUNBUFFERED=1
export PIP_CACHE_DIR="/root/autodl-tmp/.cache/pip"
export HF_ENDPOINT="${HF_ENDPOINT:-https://hf-mirror.com}"
export TMPDIR="/root/autodl-tmp/tmp"
mkdir -p "$TMPDIR" "$PIP_CACHE_DIR" /root/autodl-tmp/models /root/autodl-tmp/kohya \
  /root/autodl-tmp/output /root/autodl-tmp/dl-logs /root/autodl-tmp/ds

# stop Comfy (GPU for training)
if [ -f /root/autodl-tmp/comfy.pid ]; then
  kill "$(cat /root/autodl-tmp/comfy.pid)" 2>/dev/null || true
  rm -f /root/autodl-tmp/comfy.pid
fi
/root/miniconda3/bin/python - <<'PY' || true
import os, signal
for pid in os.listdir("/proc"):
    if not pid.isdigit():
        continue
    try:
        cmd=open(f"/proc/{pid}/cmdline","rb").read().replace(b"\x00", b" ").decode("utf-8","replace")
    except Exception:
        continue
    if "venv_h3" in cmd and "main.py" in cmd and "6006" in cmd:
        os.kill(int(pid), signal.SIGTERM)
        print("killed comfy", pid)
PY

echo "[$(date '+%F %T')] unzip sd-scripts + real2d"
if [ ! -f /root/autodl-tmp/kohya/sd-scripts/sdxl_train_network.py ]; then
  "$PY" - <<'PY'
import zipfile
z=zipfile.ZipFile("/root/autodl-tmp/sd-scripts-slim.zip")
z.extractall("/root/autodl-tmp/kohya")
print("sd-scripts", len(z.namelist()))
PY
fi
if [ ! -d /root/autodl-tmp/ds/real2d/1_real2d ]; then
  "$PY" - <<'PY'
import zipfile
z=zipfile.ZipFile("/root/autodl-tmp/real2d.zip")
z.extractall("/root/autodl-tmp/ds")
print("real2d", len(z.namelist()))
PY
fi

echo "[$(date '+%F %T')] kick NoobAI"
DEST=/root/autodl-tmp/models/NoobAI-XL-v1.1.safetensors
if [ -f "$DEST" ] && [ ! -f "$DEST.aria2" ]; then
  echo "noobai skip $(stat -c%s "$DEST")"
elif [ -f "$DEST.aria2" ]; then
  echo "noobai already downloading $(stat -c%s "$DEST" 2>/dev/null || echo 0)"
else
  setsid aria2c -c -x 16 -s 16 -k 8M --file-allocation=none --timeout=60 --connect-timeout=20 \
    --max-tries=0 --retry-wait=4 --check-certificate=false \
    -d /root/autodl-tmp/models -o NoobAI-XL-v1.1.safetensors \
    "https://hf-mirror.com/Laxhar/noobai-XL-1.1/resolve/main/NoobAI-XL-v1.1.safetensors" \
    >>/root/autodl-tmp/dl-logs/noobai.log 2>&1 </dev/null &
  echo "aria2 noobai pid $!"
fi

echo "[$(date '+%F %T')] pip kohya extras into venv_h3, keep torch"
cd /root/autodl-tmp/kohya/sd-scripts
"$PY" -m pip install \
  "accelerate>=0.33" \
  "diffusers>=0.32" \
  "ftfy" \
  "opencv-python-headless==4.10.0.84" \
  "einops" \
  "bitsandbytes" \
  "lion-pytorch" \
  "schedulefree" \
  "pytorch-optimizer" \
  "prodigyopt" \
  "tensorboard" \
  "toml" \
  "voluptuous" \
  "imagesize" \
  "rich" \
  "sentencepiece" \
  "safetensors"
"$PY" -m pip install -e . --no-deps

"$PY" - <<'PY'
import torch, bitsandbytes, accelerate, diffusers
print("torch", torch.__version__, "cuda", torch.cuda.is_available(), torch.cuda.get_device_name(0))
print("bnb", bitsandbytes.__version__, "acc", accelerate.__version__, "diffusers", diffusers.__version__)
assert torch.cuda.is_available()
PY

echo "[$(date '+%F %T')] wait NoobAI size 7105349958"
while true; do
  if [ -f "$DEST" ] && [ ! -f "$DEST.aria2" ]; then
    sz=$(stat -c%s "$DEST")
    echo "noobai size $sz"
    break
  fi
  echo "waiting noobai $(stat -c%s "$DEST" 2>/dev/null || echo 0)"
  sleep 15
done

echo DONE_SETUP
df -h /root/autodl-tmp | tail -1
