#!/usr/bin/env bash
# Overlay complete ComfyUI source; keep autodl-tmp weights.
set -euo pipefail
export PATH="/usr/bin:/root/miniconda3/bin:$PATH"

# Kill previous Comfy by pid file or port, not by matching this script text.
if [ -f /root/autodl-tmp/comfy.pid ]; then
  kill "$(cat /root/autodl-tmp/comfy.pid)" 2>/dev/null || true
  rm -f /root/autodl-tmp/comfy.pid
fi
python3 - <<'PY'
import os, signal, time
for pid in os.listdir("/proc"):
    if not pid.isdigit():
        continue
    try:
        cmd = open(f"/proc/{pid}/cmdline", "rb").read().replace(b"\x00", b" ").decode("utf-8", "replace")
    except Exception:
        continue
    if "venv_h3" in cmd and "main.py" in cmd and "--port 6006" in cmd:
        os.kill(int(pid), signal.SIGTERM)
        print("killed", pid, cmd[:120])
PY

SRC=/root/autodl-tmp/ComfyUI-upstream
rm -rf "$SRC"
mkdir -p /root/autodl-tmp/tmp /root/autodl-tmp/ComfyUI

clone_ok=0
# Zip is more reliable than empty git mirrors.
for zipurl in \
  "https://ghproxy.com/https://github.com/comfyanonymous/ComfyUI/archive/refs/heads/master.zip" \
  "https://github.com/comfyanonymous/ComfyUI/archive/refs/heads/master.zip" \
  "https://codeload.github.com/comfyanonymous/ComfyUI/zip/refs/heads/master"
do
  echo "wget zip $zipurl"
  rm -rf "$SRC" /root/autodl-tmp/ComfyUI-master.zip /root/autodl-tmp/tmp/ComfyUI-master
  if wget -q --timeout=60 -O /root/autodl-tmp/ComfyUI-master.zip "$zipurl" \
    && python3 - <<'PY'
import zipfile, os, shutil
zpath="/root/autodl-tmp/ComfyUI-master.zip"
if os.path.getsize(zpath) < 1000000:
    raise SystemExit("zip too small")
z=zipfile.ZipFile(zpath)
z.extractall("/root/autodl-tmp/tmp")
src=None
for name in os.listdir("/root/autodl-tmp/tmp"):
    p=os.path.join("/root/autodl-tmp/tmp", name)
    if os.path.isdir(p) and name.lower().startswith("comfyui"):
        src=p
        break
if not src:
    raise SystemExit("no extracted comfy dir")
need=os.path.join(src, "comfy/ldm/models/autoencoder.py")
if not os.path.isfile(need):
    raise SystemExit("missing autoencoder.py")
os.rename(src, "/root/autodl-tmp/ComfyUI-upstream")
print("ZIP_OK", src)
PY
  then
    clone_ok=1
    break
  fi
  echo "zip unusable $zipurl"
done

if [ "$clone_ok" != 1 ]; then
for url in \
  "https://ghproxy.com/https://github.com/comfyanonymous/ComfyUI.git" \
  "https://github.com/comfyanonymous/ComfyUI.git"
do
  echo "clone $url"
  rm -rf "$SRC"
  if git clone --depth 1 "$url" "$SRC" \
    && test -f "$SRC/comfy/ldm/models/autoencoder.py"; then
    echo "CLONE_OK $url"
    clone_ok=1
    break
  fi
  echo "clone unusable $url"
done
fi

if [ "$clone_ok" != 1 ]; then
  echo CLONE_FAIL
  exit 1
fi

if ! command -v rsync >/dev/null 2>&1; then
  apt-get install -y --no-install-recommends rsync >/dev/null
fi

rsync -a \
  --exclude '/models/' \
  --exclude '/output/' \
  --exclude '/input/' \
  --exclude '/user/' \
  --exclude '/.git/' \
  --exclude '/.venv/' \
  --exclude '/venv/' \
  "$SRC"/ /root/autodl-tmp/ComfyUI/

rm -f /root/autodl-tmp/ComfyUI/extra_model_paths.yaml
test -f /root/autodl-tmp/ComfyUI/comfy/ldm/models/autoencoder.py
echo LDM_MODELS_OK
ls -lh /root/autodl-tmp/ComfyUI/models/diffusion_models/minimax_h3_fl2va_pruned_bf16.safetensors
echo WEIGHTS_STILL_THERE

export PATH="/root/autodl-tmp/venv_h3/bin:$PATH"
export PYTORCH_CUDA_ALLOC_CONF=expandable_segments:True
cd /root/autodl-tmp/ComfyUI
nohup python main.py --listen 0.0.0.0 --port 6006 --preview-method none >/root/autodl-tmp/comfy.log 2>&1 < /dev/null &
echo $! > /root/autodl-tmp/comfy.pid
echo START "$(cat /root/autodl-tmp/comfy.pid)"
sleep 15
tail -40 /root/autodl-tmp/comfy.log
