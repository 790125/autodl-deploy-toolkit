# -*- coding: utf-8 -*-
"""Poll kohya setup. Do not print secrets."""
import sys
import paramiko
import os
# NOTE: host/port 已外置为环境变量，便于在不同实例间复用。
#   AUTODL_HOST / AUTODL_PORT  （或填入 .env，见 .env.example）
sys.stdout.reconfigure(encoding="utf-8")
c=paramiko.SSHClient(); c.set_missing_host_key_policy(paramiko.AutoAddPolicy())
c.connect(os.environ.get("AUTODL_HOST", "127.0.0.1"),
        port=int(os.environ.get("AUTODL_PORT", "22")), username="root", password=__import__("os").environ.get("AUTODL_SSH_PASSWORD", ""), timeout=40, banner_timeout=80, auth_timeout=40, allow_agent=False, look_for_keys=False)
_,out,err=c.exec_command("""
echo '=== disk ==='
df -h /root/autodl-tmp | tail -1
echo '=== noobai ==='
ls -lh /root/autodl-tmp/models 2>/dev/null || true
echo '=== procs ==='
ps -eo pid,etime,cmd | grep -E 'aria2c|kohya_setup|pip ' | grep -v grep || true
echo '=== files ==='
ls /root/autodl-tmp/kohya/sd-scripts/sdxl_train_network.py /root/autodl-tmp/ds/real2d/1_real2d 2>/dev/null | head
echo '=== log ==='
tail -40 /root/autodl-tmp/kohya_setup.log 2>/dev/null || echo NO_LOG
echo '=== noobai log ==='
tail -8 /root/autodl-tmp/dl-logs/noobai.log 2>/dev/null || true
""", timeout=30)
print(out.read().decode("utf-8","replace"))
e=err.read().decode("utf-8","replace")
if e.strip(): print("STDERR", e[:400])
c.close()
