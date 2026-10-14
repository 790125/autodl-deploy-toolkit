# -*- coding: utf-8 -*-
"""Poll remote H3 install. Do not print secrets."""
import sys

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
    cmd = r"""
echo '=== disk ==='
df -h /root/autodl-tmp | tail -1
echo '=== du ==='
du -sb /root/autodl-tmp/ComfyUI/models /root/autodl-tmp/venv_h3 2>/dev/null
echo '=== files logical vs allocated ==='
find /root/autodl-tmp/ComfyUI/models -type f ! -name '*.aria2' -printf '%s %b %p\n' 2>/dev/null | sort
echo '=== aria2 ==='
ps -eo pid,etime,pcpu,cmd | grep -E 'aria2c|pip |install_h3' | grep -v grep || true
echo '=== pip fd / tmp ==='
ls -lh /proc/1590/fd 2>/dev/null | head -20 || true
ls -lh /root/autodl-tmp/tmp /tmp 2>/dev/null | head -20 || true
echo '=== dl-log tails ==='
for f in /root/autodl-tmp/dl-logs/*.log; do echo "-- $f"; tail -3 "$f"; done 2>/dev/null
echo '=== log tail ==='
tail -40 /root/autodl-tmp/h3_install.log
"""
    _, out, err = c.exec_command(cmd, timeout=40)
    print(out.read().decode("utf-8", "replace"))
    e = err.read().decode("utf-8", "replace")
    if e.strip():
        print("STDERR", e[:400])
    c.close()


if __name__ == "__main__":
    main()
