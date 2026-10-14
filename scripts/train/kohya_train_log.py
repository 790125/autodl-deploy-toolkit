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
echo '=== port ==='
netstat -lntp 2>/dev/null | grep -E '6006|6007|6008' || ss -lntp | grep -E '6006|6007|6008' || true
echo '=== train pid ==='
cat /root/autodl-tmp/train.pid; ps -p $(cat /root/autodl-tmp/train.pid) -o pid,etime,cmd || true
echo '=== log tail ==='
tail -50 /root/autodl-tmp/train_real2d.log
""", timeout=25)
print(out.read().decode("utf-8","replace"))
e=err.read().decode("utf-8","replace")
if e.strip(): print("STDERR", e[:400])
c.close()
