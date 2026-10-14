# -*- coding: utf-8 -*-
"""Kick NoobAI download + stop Comfy. Do not print secrets."""
import sys

import paramiko

sys.stdout.reconfigure(encoding="utf-8")

HOST = __import__("os").environ.get("AUTODL_HOST", "127.0.0.1")
PORT = int(__import__("os").environ.get("AUTODL_PORT", "22"))
USER = "root"
PASS = __import__("os").environ.get("AUTODL_SSH_PASSWORD", "")

CMD = r"""
set -euo pipefail
export PATH="/usr/bin:/root/miniconda3/bin:/root/autodl-tmp/venv_h3/bin:$PATH"
mkdir -p /root/autodl-tmp/models /root/autodl-tmp/kohya /root/autodl-tmp/dl-logs
# stop Comfy so GPU is free for training
if [ -f /root/autodl-tmp/comfy.pid ]; then
  kill "$(cat /root/autodl-tmp/comfy.pid)" 2>/dev/null || true
  rm -f /root/autodl-tmp/comfy.pid
fi
/root/miniconda3/bin/python - <<'PY' || true
import os, signal
# NOTE: host/port 已外置为环境变量，便于在不同实例间复用。
#   AUTODL_HOST / AUTODL_PORT  （或填入 .env，见 .env.example）
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

DEST=/root/autodl-tmp/models/NoobAI-XL-v1.1.safetensors
if [ -f "$DEST" ] && [ ! -f "$DEST.aria2" ]; then
  echo "noobai already $(stat -c%s "$DEST")"
else
  # try several mirrors; first that starts winning stays
  URLS="https://hf-mirror.com/Laxhar/noobai-XL-1.1/resolve/main/NoobAI-XL-v1.1.safetensors
https://hf-mirror.com/Laxhar/noobai-XL-1.1/resolve/main/noobaiXLNAIXL_epsilonPred11Version.safetensors
https://huggingface.co/Laxhar/noobai-XL-1.1/resolve/main/NoobAI-XL-v1.1.safetensors"
  ok=0
  for u in $URLS; do
    echo "HEAD $u"
    if wget --spider -q --timeout=15 "$u"; then
      echo "GET $u"
      setsid aria2c -c -x 16 -s 16 -k 8M --file-allocation=none --timeout=60 --connect-timeout=20 \
        --max-tries=0 --retry-wait=4 --check-certificate=false \
        -d /root/autodl-tmp/models -o NoobAI-XL-v1.1.safetensors \
        "$u" >>/root/autodl-tmp/dl-logs/noobai.log 2>&1 </dev/null &
      echo ARIA2 $!
      ok=1
      break
    fi
  done
  if [ "$ok" != 1 ]; then
    echo "spider failed, aria2 first url anyway"
    setsid aria2c -c -x 16 -s 16 -k 8M --file-allocation=none --timeout=60 --connect-timeout=20 \
      --max-tries=0 --retry-wait=4 --check-certificate=false \
      -d /root/autodl-tmp/models -o NoobAI-XL-v1.1.safetensors \
      "https://hf-mirror.com/Laxhar/noobai-XL-1.1/resolve/main/NoobAI-XL-v1.1.safetensors" \
      >>/root/autodl-tmp/dl-logs/noobai.log 2>&1 </dev/null &
    echo ARIA2 $!
  fi
fi
echo '=== gpu ==='
nvidia-smi -L
echo '=== venv pkgs ==='
/root/autodl-tmp/venv_h3/bin/python -c "import torch,sys; print('torch',torch.__version__,torch.cuda.is_available());
mods='transformers diffusers accelerate bitsandbytes toml voluptuous imagesize cv2 tensorboard safetensors'
import importlib
for m in mods.split():
    try:
        mod=importlib.import_module(m if m!='cv2' else 'cv2')
        print(m, getattr(mod,'__version__','ok'))
    except Exception as e:
        print(m, 'MISSING')
"
df -h /root/autodl-tmp | tail -1
echo '=== noobai now ==='
ls -lh /root/autodl-tmp/models 2>/dev/null || true
tail -5 /root/autodl-tmp/dl-logs/noobai.log 2>/dev/null || true
"""


def main():
    c = paramiko.SSHClient()
    c.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    c.connect(HOST, port=PORT, username=USER, password=PASS, timeout=40, banner_timeout=80, auth_timeout=40, allow_agent=False, look_for_keys=False)
    print("SSH_OK", flush=True)
    _, out, err = c.exec_command(CMD, timeout=90)
    print(out.read().decode("utf-8", "replace"), flush=True)
    e = err.read().decode("utf-8", "replace")
    if e.strip():
        print("STDERR", e[-1500:], flush=True)
    print("exit", out.channel.recv_exit_status(), flush=True)
    c.close()


if __name__ == "__main__":
    main()
