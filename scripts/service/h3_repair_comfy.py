# -*- coding: utf-8 -*-
"""Repair incomplete Comfy source, keep weights. Do not print secrets."""
import sys
import time

import paramiko
# NOTE: host/port 已外置为环境变量，便于在不同实例间复用。
#   AUTODL_HOST / AUTODL_PORT  （或填入 .env，见 .env.example）

sys.stdout.reconfigure(encoding="utf-8")

HOST = __import__("os").environ.get("AUTODL_HOST", "127.0.0.1")
PORT = int(__import__("os").environ.get("AUTODL_PORT", "22"))
USER = "root"
PASS = __import__("os").environ.get("AUTODL_SSH_PASSWORD", "")

CMD = r"""
set -euo pipefail
export PATH="/root/miniconda3/bin:$PATH"
pkill -f '/root/autodl-tmp/ComfyUI/main.py' || true
SRC=/root/autodl-tmp/ComfyUI-upstream
rm -rf "$SRC"
mkdir -p /root/autodl-tmp/tmp
# Prefer ghproxy then github
if git clone --depth 1 https://ghproxy.com/https://github.com/comfyanonymous/ComfyUI.git "$SRC"; then
  echo CLONE_OK ghproxy
elif git clone --depth 1 https://github.com/comfyanonymous/ComfyUI.git "$SRC"; then
  echo CLONE_OK github
else
  echo CLONE_FAIL
  exit 1
fi
# Overlay source onto existing install; do not touch downloaded weights.
rsync -a --delete \
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
ls /root/autodl-tmp/ComfyUI/models/diffusion_models | head
echo WEIGHTS_STILL_THERE
# restart
export PATH="/root/autodl-tmp/venv_h3/bin:$PATH"
export PYTORCH_CUDA_ALLOC_CONF=expandable_segments:True
cd /root/autodl-tmp/ComfyUI
nohup python main.py --listen 0.0.0.0 --port 6006 --preview-method none >/root/autodl-tmp/comfy.log 2>&1 < /dev/null &
echo START $!
sleep 12
tail -30 /root/autodl-tmp/comfy.log
"""


def main():
    c = paramiko.SSHClient()
    c.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    c.connect(
        HOST,
        port=PORT,
        username=USER,
        password=PASS,
        timeout=40,
        banner_timeout=80,
        auth_timeout=40,
        allow_agent=False,
        look_for_keys=False,
    )
    print("SSH_OK", flush=True)
    _, out, err = c.exec_command(CMD, timeout=180)
    print(out.read().decode("utf-8", "replace"), flush=True)
    e = err.read().decode("utf-8", "replace")
    if e.strip():
        print("STDERR", e[-2000:], flush=True)
    print("exit", out.channel.recv_exit_status(), flush=True)
    c.close()


if __name__ == "__main__":
    main()
