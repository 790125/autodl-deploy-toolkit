# -*- coding: utf-8 -*-
"""Start remote Comfy. Do not print secrets."""
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
    _, out, err = c.exec_command(
        "cd /root/autodl-tmp && nohup bash ./start_comfy.sh >/root/autodl-tmp/comfy.log 2>&1 < /dev/null & echo START $!",
        timeout=15,
    )
    print(out.read().decode("utf-8", "replace"), flush=True)
    e = err.read().decode("utf-8", "replace")
    if e.strip():
        print("STDERR", e[:400], flush=True)
    time.sleep(8)
    _, out, err = c.exec_command("tail -40 /root/autodl-tmp/comfy.log; ss -lntp | grep 6006 || true", timeout=20)
    print(out.read().decode("utf-8", "replace"), flush=True)
    e = err.read().decode("utf-8", "replace")
    if e.strip():
        print("STDERR", e[:400], flush=True)
    c.close()


if __name__ == "__main__":
    main()
