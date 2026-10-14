#!/usr/bin/env bash
# MiniMax-H3 on AutoDL A800. Keep weights on autodl-tmp only.
set -euo pipefail
export PATH="/root/miniconda3/bin:$PATH"
export PYTHONUNBUFFERED=1
export PIP_CACHE_DIR="/root/autodl-tmp/.cache/pip"
export HF_ENDPOINT="${HF_ENDPOINT:-https://hf-mirror.com}"
export TMPDIR="/root/autodl-tmp/tmp"
mkdir -p "$TMPDIR" "$PIP_CACHE_DIR" /root/autodl-tmp/dl-logs /root/autodl-tmp/ComfyUI/models

if [ -f /etc/network_turbo ]; then
  # shellcheck disable=SC1091
  source /etc/network_turbo || true
fi

ROOT="/root/autodl-tmp"
COMFY="$ROOT/ComfyUI"
VENV="$ROOT/venv_h3"
LOG="$ROOT/h3_install.log"
say() { echo "[$(date '+%F %T')] $*" | tee -a "$LOG"; }

say "unzip ComfyUI"
if [ ! -f "$COMFY/main.py" ]; then
  cd "$ROOT"
  python - <<'PY'
import zipfile
z=zipfile.ZipFile("/root/autodl-tmp/ComfyUI-src.zip")
z.extractall("/root/autodl-tmp")
print("extracted", len(z.namelist()))
PY
fi
mkdir -p "$COMFY/models/diffusion_models" "$COMFY/models/text_encoders" \
  "$COMFY/models/vae" "$COMFY/models/loras" \
  "$COMFY/user/default/workflows" "$COMFY/input" "$COMFY/output"
if [ -d "$ROOT/workflows" ]; then
  cp -f "$ROOT/workflows/"*.json "$COMFY/user/default/workflows/" || true
fi

say "kick weight downloads in background"
DLDIR="$COMFY/models"
BASE="https://hf-mirror.com/Comfy-Org/MiniMax-H3/resolve/main"
kick() {
  local rel="$1"
  local dest="$DLDIR/$rel"
  mkdir -p "$(dirname "$dest")"
  if [ -f "$dest" ] && [ ! -f "$dest.aria2" ]; then
    say "skip complete $rel $(stat -c%s "$dest")"
    return 0
  fi
  if command -v aria2c >/dev/null 2>&1; then
    setsid aria2c -c -x 16 -s 16 -k 8M --file-allocation=none --timeout=60 --connect-timeout=20 \
      --max-tries=0 --retry-wait=4 --check-certificate=false \
      -d "$(dirname "$dest")" -o "$(basename "$dest")" \
      "$BASE/$rel" >>"$ROOT/dl-logs/$(basename "$rel").log" 2>&1 </dev/null &
    say "aria2 $rel pid $!"
  else
    setsid wget -c --timeout=60 --tries=0 -O "$dest" "$BASE/$rel" >>"$ROOT/dl-logs/$(basename "$rel").log" 2>&1 </dev/null &
    say "wget $rel pid $!"
  fi
}
kick diffusion_models/minimax_h3_fl2va_pruned_bf16.safetensors
kick text_encoders/qwen3vl_32b_minimax_h3_nvfp4_awq.safetensors
kick vae/minimax_h3_video_vae_fp16.safetensors
kick vae/minimax_h3_audio_vae_fp32.safetensors
kick loras/minimax_h3_fl2v_turbo_4step_v1.0_768p_comfyui_bf16.safetensors

say "venv + torch cu128"
if [ ! -x "$VENV/bin/python" ]; then
  python -m venv "$VENV"
fi
# shellcheck disable=SC1091
source "$VENV/bin/activate"
python -m pip install -U pip
python -m pip install torch==2.11.0+cu128 torchvision==0.26.0+cu128 torchaudio==2.11.0+cu128 \
  --force-reinstall --no-cache-dir -f https://mirrors.aliyun.com/pytorch-wheels/cu128/
python - <<'PY'
import torch
print("torch", torch.__version__, "cuda", torch.cuda.is_available(), torch.cuda.get_device_name(0))
assert torch.cuda.is_available()
PY

say "comfy requirements minus torch"
if [ -f "$COMFY/requirements.txt" ]; then
  grep -viE '^(torch|torchvision|torchaudio|xformers)([>=< ]|$)' "$COMFY/requirements.txt" > /tmp/comfy-req.txt || true
  if [ -s /tmp/comfy-req.txt ]; then
    python -m pip install -r /tmp/comfy-req.txt
  fi
fi

say "wait for weights"
expect() {
  local f="$1"
  local n="$2"
  local p="$DLDIR/$f"
  while true; do
    if [ -f "$p" ] && [ ! -f "$p.aria2" ]; then
      sz=$(stat -c%s "$p")
      if [ "$sz" -eq "$n" ]; then
        say "OK $f $sz"
        return 0
      fi
      say "size mismatch $f $sz want $n"
    fi
    say "waiting $f $(stat -c%s "$p" 2>/dev/null || echo 0)"
    sleep 20
  done
}
expect diffusion_models/minimax_h3_fl2va_pruned_bf16.safetensors 40225724176
expect text_encoders/qwen3vl_32b_minimax_h3_nvfp4_awq.safetensors 15687142551
expect vae/minimax_h3_video_vae_fp16.safetensors 5207808496
expect vae/minimax_h3_audio_vae_fp32.safetensors 605254808
expect loras/minimax_h3_fl2v_turbo_4step_v1.0_768p_comfyui_bf16.safetensors 1956192992

say "write start_comfy.sh"
cat > "$ROOT/start_comfy.sh" <<'EOF'
#!/usr/bin/env bash
set -euo pipefail
export PATH="/root/autodl-tmp/venv_h3/bin:$PATH"
export PYTORCH_CUDA_ALLOC_CONF=expandable_segments:True
cd /root/autodl-tmp/ComfyUI
exec python main.py --listen 0.0.0.0 --port 6006 --preview-method none
EOF
chmod +x "$ROOT/start_comfy.sh"

python -m pip cache purge || true
rm -rf "$PIP_CACHE_DIR"/* || true
say "DISK"
df -h "$ROOT"
say "DONE"
