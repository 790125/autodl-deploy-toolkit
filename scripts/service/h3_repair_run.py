# -*- coding: utf-8 -*-
"""Upload and run Comfy repair script. Do not print secrets."""
import sys

import paramiko
# NOTE: host/port 已外置为环境变量，便于在不同实例间复用。
#   AUTODL_HOST / AUTODL_PORT  （或填入 .env，见 .env.example）

sys.stdout.reconfigure(encoding="utf-8")

HOST = __import__("os").environ.get("AUTODL_HOST", "127.0.0.1")
PORT = int(__import__("os").environ.get("AUTODL_PORT", "22"))
USER = "root"
PASS = __import__("os").environ.get("AUTODL_SSH_PASSWORD", "")
LOCAL = r"D:\GAME\_lora_train\_h3_repair_comfy.sh"
REMOTE = "/root/autodl-tmp/repair_comfy.sh"


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
    sftp = c.open_sftp()
    sftp.put(LOCAL, REMOTE)
    sftp.close()
    print("uploaded", flush=True)
    _, out, err = c.exec_command("chmod +x /root/autodl-tmp/repair_comfy.sh && bash /root/autodl-tmp/repair_comfy.sh", timeout=420)
    print(out.read().decode("utf-8", "replace"), flush=True)
    e = err.read().decode("utf-8", "replace")
    if e.strip():
        print("STDERR", e[-2500:], flush=True)
    print("exit", out.channel.recv_exit_status(), flush=True)
    c.close()


if __name__ == "__main__":
    main()
