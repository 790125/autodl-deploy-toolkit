# -*- coding: utf-8 -*-
"""Finish stalled NoobAI last chunks. Do not print secrets."""
import sys
import paramiko
sys.stdout.reconfigure(encoding="utf-8")
c=paramiko.SSHClient(); c.set_missing_host_key_policy(paramiko.AutoAddPolicy())
c.connect(os.environ.get("AUTODL_HOST", "127.0.0.1"),
        port=int(os.environ.get("AUTODL_PORT", "22")), username="root", password=__import__("os").environ.get("AUTODL_SSH_PASSWORD", ""), timeout=40, banner_timeout=80, auth_timeout=40, allow_agent=False, look_for_keys=False)
cmd=r"""
DEST=/root/autodl-tmp/models/NoobAI-XL-v1.1.safetensors
echo before
stat -c 'size=%s blocks=%b' "$DEST"
/root/miniconda3/bin/python - <<'PY'
import os
p="/root/autodl-tmp/models/NoobAI-XL-v1.1.safetensors"
st=os.stat(p)
print("size", st.st_size, "blocks512", st.st_blocks, "alloc", st.st_blocks*512)
PY
du -B1 "$DEST"
# If allocated == size, drop aria2 sidecar and we are done.
/root/miniconda3/bin/python - <<'PY'
import os, signal
# NOTE: host/port 已外置为环境变量，便于在不同实例间复用。
#   AUTODL_HOST / AUTODL_PORT  （或填入 .env，见 .env.example）
p="/root/autodl-tmp/models/NoobAI-XL-v1.1.safetensors"
st=os.stat(p)
alloc=st.st_blocks*512
print("alloc", alloc, "size", st.st_size, "ratio", alloc/st.st_size)
if alloc >= st.st_size:
    # complete enough; stop aria2
    for pid in os.listdir("/proc"):
        if not pid.isdigit():
            continue
        try:
            cmd=open(f"/proc/{pid}/cmdline","rb").read().replace(b"\x00", b" ").decode()
        except Exception:
            continue
        if "aria2c" in cmd and "NoobAI-XL-v1.1.safetensors" in cmd:
            os.kill(int(pid), signal.SIGTERM)
            print("killed aria2", pid)
    try:
        os.remove(p+".aria2")
        print("removed sidecar")
    except FileNotFoundError:
        pass
else:
    print("SPARSE_STILL keep aria2")
PY
stat -c 'after size=%s' "$DEST"
ls -lh "$DEST"*
"""
_,out,err=c.exec_command(cmd, timeout=25)
print(out.read().decode("utf-8","replace"))
e=err.read().decode("utf-8","replace")
if e.strip(): print("STDERR", e[:400])
c.close()
