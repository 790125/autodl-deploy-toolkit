# -*- coding: utf-8 -*-
import sys, paramiko
import os
# NOTE: host/port 已外置为环境变量，便于在不同实例间复用。
#   AUTODL_HOST / AUTODL_PORT  （或填入 .env，见 .env.example）
sys.stdout.reconfigure(encoding="utf-8")
c=paramiko.SSHClient(); c.set_missing_host_key_policy(paramiko.AutoAddPolicy())
c.connect(os.environ.get("AUTODL_HOST", "127.0.0.1"),
        port=int(os.environ.get("AUTODL_PORT", "22")), username="root", password=__import__("os").environ.get("AUTODL_SSH_PASSWORD", ""), timeout=40, banner_timeout=80, auth_timeout=40, allow_agent=False, look_for_keys=False)
_,out,err=c.exec_command("""
rm -f /root/autodl-tmp/models/NoobAI-XL-v1.1.safetensors.aria2
ps -eo pid,cmd | grep aria2 | grep -v grep || echo NO_ARIA2
stat -c '%s' /root/autodl-tmp/models/NoobAI-XL-v1.1.safetensors
sleep 16
tail -8 /root/autodl-tmp/kohya_setup.log
""", timeout=30)
print(out.read().decode("utf-8","replace"))
c.close()
