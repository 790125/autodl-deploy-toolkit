# -*- coding: utf-8 -*-
"""Upload toml, start real2d train + TensorBoard. Do not print secrets."""
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


def main():
    c = paramiko.SSHClient()
    c.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    c.connect(HOST, port=PORT, username=USER, password=PASS, timeout=40, banner_timeout=80, auth_timeout=40, allow_agent=False, look_for_keys=False)
    print("SSH_OK", flush=True)
    sftp = c.open_sftp()
    sftp.put(r"D:\GAME\_lora_train\_pack\real2d_a800.toml", "/root/autodl-tmp/real2d_a800.toml")
    sftp.close()
    print("toml uploaded", flush=True)
    cmd = r"""
set -euo pipefail
export PATH="/root/autodl-tmp/venv_h3/bin:/usr/bin:/root/miniconda3/bin:$PATH"
export HF_ENDPOINT=https://hf-mirror.com
export PYTHONUNBUFFERED=1
export PYTORCH_CUDA_ALLOC_CONF=expandable_segments:True
find /root/autodl-tmp/ds/real2d -name '*.npz' -delete
echo "webp $(ls /root/autodl-tmp/ds/real2d/1_real2d/*.webp 2>/dev/null | wc -l) txt $(ls /root/autodl-tmp/ds/real2d/1_real2d/*.txt 2>/dev/null | wc -l)"
mkdir -p /root/autodl-tmp/output/logs_real2d
# TensorBoard on 6007
nohup tensorboard --logdir /root/autodl-tmp/output/logs_real2d --host 0.0.0.0 --port 6007 >/root/autodl-tmp/tb.log 2>&1 < /dev/null &
echo $! > /root/autodl-tmp/tb.pid
echo TB "$(cat /root/autodl-tmp/tb.pid)"
cd /root/autodl-tmp/kohya/sd-scripts
nohup python sdxl_train_network.py --config_file /root/autodl-tmp/real2d_a800.toml >/root/autodl-tmp/train_real2d.log 2>&1 < /dev/null &
echo $! > /root/autodl-tmp/train.pid
echo TRAIN "$(cat /root/autodl-tmp/train.pid)"
sleep 8
echo '=== tb ==='
tail -8 /root/autodl-tmp/tb.log || true
echo '=== train ==='
tail -40 /root/autodl-tmp/train_real2d.log || true
"""
    _, out, err = c.exec_command(cmd, timeout=40)
    print(out.read().decode("utf-8", "replace"), flush=True)
    e = err.read().decode("utf-8", "replace")
    if e.strip():
        print("STDERR", e[-1500:], flush=True)
    print("exit", out.channel.recv_exit_status(), flush=True)
    c.close()


if __name__ == "__main__":
    main()
