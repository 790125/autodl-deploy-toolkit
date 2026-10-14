# -*- coding: utf-8 -*-
"""AutoDL NMA H3 helper. Do not print secrets."""
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


def connect():
    last = None
    for _ in range(4):
        c = paramiko.SSHClient()
        c.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        try:
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
            return c
        except Exception as e:
            last = e
            time.sleep(2)
    raise last


def run(c, cmd, timeout=60):
    _, out, err = c.exec_command(cmd, timeout=timeout)
    return (
        out.read().decode("utf-8", "replace"),
        err.read().decode("utf-8", "replace"),
        out.channel.recv_exit_status(),
    )


INSPECT = r"""
echo =====HOST=====
hostname; date
echo =====GPU=====
nvidia-smi --query-gpu=name,memory.total,memory.used --format=csv
echo =====DISK=====
df -h / /root/autodl-tmp 2>/dev/null; df -h | head
echo =====MEM=====
free -h | head -2
echo =====PY=====
export PATH="/root/miniconda3/bin:$PATH"
python -V 2>/dev/null || true
which python
echo =====EXIST=====
ls -la /root /root/autodl-tmp 2>/dev/null | head -40
echo =====CUDA=====
ls /usr/local | grep -i cuda || true
"""


def main():
    print("SSH_TRY", HOST, PORT, flush=True)
    c = connect()
    print("SSH_OK", flush=True)
    out, err, code = run(c, INSPECT, timeout=40)
    sys.stdout.write(out)
    if err.strip():
        print("STDERR", err[:500])
    print("exit", code, flush=True)
    c.close()


if __name__ == "__main__":
    main()
