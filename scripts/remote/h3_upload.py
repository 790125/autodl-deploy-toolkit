# -*- coding: utf-8 -*-
"""Bootstrap H3 on AutoDL NMA. Do not print secrets."""
import os
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

LOCAL_ZIP = r"D:\GAME\AI-VIDEO\h3_offline_pack\ComfyUI-src.zip"
LOCAL_WF = [
    r"C:\Users\ASUS\Desktop\video_minimax_h3_i2v.json",
    r"C:\Users\ASUS\Desktop\video_minimax_h3_r2v_ready.json",
]
REMOTE_TMP = "/root/autodl-tmp"
REMOTE_ZIP = f"{REMOTE_TMP}/ComfyUI-src.zip"


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
    t = c.get_transport()
    t.set_keepalive(15)
    return c


def run(c, cmd, timeout=120):
    _, out, err = c.exec_command(cmd, timeout=timeout)
    return (
        out.read().decode("utf-8", "replace"),
        err.read().decode("utf-8", "replace"),
        out.channel.recv_exit_status(),
    )


def main():
    print("SSH", HOST, PORT, flush=True)
    c = connect()
    print("SSH_OK", flush=True)
    out, err, code = run(
        c,
        "command -v aria2c; command -v wget; command -v unzip; ls /etc/network_turbo 2>/dev/null; echo ---; nvidia-smi -L",
        timeout=20,
    )
    print(out)
    sftp = c.open_sftp()
    print("upload zip", flush=True)
    sftp.put(LOCAL_ZIP, REMOTE_ZIP)
    sftp.put(r"D:\GAME\_lora_train\_remote_h3.sh", f"{REMOTE_TMP}/install_h3.sh")
    print("upload install_h3.sh", flush=True)
    wf_dir = f"{REMOTE_TMP}/workflows"
    try:
        sftp.mkdir(wf_dir)
    except OSError:
        pass
    for p in LOCAL_WF:
        if os.path.isfile(p):
            name = os.path.basename(p)
            sftp.put(p, f"{wf_dir}/{name}")
            print("wf", name, flush=True)
    sftp.close()
    print("uploaded", flush=True)
    c.close()


if __name__ == "__main__":
    main()
