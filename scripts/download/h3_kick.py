# -*- coding: utf-8 -*-
"""Start remote H3 install. Do not print secrets."""
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
    return c


def run(c, cmd, timeout=120):
    _, out, err = c.exec_command(cmd, timeout=timeout)
    return (
        out.read().decode("utf-8", "replace"),
        err.read().decode("utf-8", "replace"),
        out.channel.recv_exit_status(),
    )


def main():
    c = connect()
    print("SSH_OK", flush=True)
    out, err, code = run(
        c,
        "export DEBIAN_FRONTEND=noninteractive; apt-get update -y >/tmp/apt.log 2>&1; apt-get install -y --no-install-recommends aria2 wget unzip >>/tmp/apt.log 2>&1; command -v aria2c; echo apt_exit $?",
        timeout=180,
    )
    print(out)
    if err.strip():
        print("STDERR", err[:400])
    out, err, code = run(
        c,
        "chmod +x /root/autodl-tmp/install_h3.sh; nohup bash /root/autodl-tmp/install_h3.sh >/root/autodl-tmp/h3_install.log 2>&1 < /dev/null & echo START $!; sleep 2; head -20 /root/autodl-tmp/h3_install.log",
        timeout=20,
    )
    print(out)
    c.close()


if __name__ == "__main__":
    main()
