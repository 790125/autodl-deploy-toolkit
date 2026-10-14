# -*- coding: utf-8 -*-
"""Upload kohya packs and run setup. Do not print secrets."""
import sys

import paramiko
# NOTE: host/port 已外置为环境变量，便于在不同实例间复用。
#   AUTODL_HOST / AUTODL_PORT  （或填入 .env，见 .env.example）

sys.stdout.reconfigure(encoding="utf-8")

HOST = __import__("os").environ.get("AUTODL_HOST", "127.0.0.1")
PORT = int(__import__("os").environ.get("AUTODL_PORT", "22"))
USER = "root"
PASS = __import__("os").environ.get("AUTODL_SSH_PASSWORD", "")

FILES = [
    (r"D:\GAME\_lora_train\_pack\sd-scripts-slim.zip", "/root/autodl-tmp/sd-scripts-slim.zip"),
    (r"D:\GAME\_lora_train\_pack\real2d.zip", "/root/autodl-tmp/real2d.zip"),
    (r"D:\GAME\_lora_train\_kohya_setup.sh", "/root/autodl-tmp/kohya_setup.sh"),
]


def main():
    c = paramiko.SSHClient()
    c.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    c.connect(HOST, port=PORT, username=USER, password=PASS, timeout=40, banner_timeout=80, auth_timeout=40, allow_agent=False, look_for_keys=False)
    print("SSH_OK", flush=True)
    sftp = c.open_sftp()
    for loc, rem in FILES:
        print("put", rem, flush=True)
        sftp.put(loc, rem)
    sftp.close()
    _, out, err = c.exec_command(
        "chmod +x /root/autodl-tmp/kohya_setup.sh && nohup bash /root/autodl-tmp/kohya_setup.sh >/root/autodl-tmp/kohya_setup.log 2>&1 < /dev/null & echo START $!; sleep 2; head -30 /root/autodl-tmp/kohya_setup.log",
        timeout=40,
    )
    print(out.read().decode("utf-8", "replace"), flush=True)
    e = err.read().decode("utf-8", "replace")
    if e.strip():
        print("STDERR", e[-800:], flush=True)
    c.close()


if __name__ == "__main__":
    main()
