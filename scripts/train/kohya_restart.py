# -*- coding: utf-8 -*-
"""Kill miniconda pip setup, keep aria2, restart venv_h3 setup. No secrets in stdout beyond status."""
import sys
import time

import paramiko

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
    kill = r"""
/root/miniconda3/bin/python - <<'PY'
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
    if "aria2c" in cmd:
        continue
    if "kohya_setup.sh" in cmd or ("pip install" in cmd and "accelerate" in cmd):
        try:
            os.kill(int(pid), signal.SIGTERM)
            print("killed", pid, cmd[:140])
        except Exception as e:
            print("killfail", pid, e)
PY
"""
    _, out, err = c.exec_command(kill, timeout=20)
    print(out.read().decode("utf-8", "replace"), flush=True)
    sftp = c.open_sftp()
    sftp.put(r"D:\GAME\_lora_train\_kohya_setup.sh", "/root/autodl-tmp/kohya_setup.sh")
    sftp.close()
    print("script uploaded", flush=True)
    _, out, err = c.exec_command(
        "chmod +x /root/autodl-tmp/kohya_setup.sh; nohup bash /root/autodl-tmp/kohya_setup.sh >/root/autodl-tmp/kohya_setup.log 2>&1 < /dev/null & echo START $!",
        timeout=15,
    )
    print(out.read().decode("utf-8", "replace"), flush=True)
    e = err.read().decode("utf-8", "replace")
    if e.strip():
        print("STDERR", e[-600:], flush=True)
    time.sleep(3)
    _, out, err = c.exec_command("tail -15 /root/autodl-tmp/kohya_setup.log", timeout=15)
    print(out.read().decode("utf-8", "replace"), flush=True)
    c.close()


if __name__ == "__main__":
    main()
