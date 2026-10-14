# -*- coding: utf-8 -*-
"""Inspect remote Comfy tree. Do not print secrets."""
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
echo '=== extra yaml ==='
ls -la /root/autodl-tmp/ComfyUI/extra_model_paths.yaml /root/autodl-tmp/ComfyUI/extra_model_paths.yaml.example 2>/dev/null || true
echo '=== comfy/ldm ==='
ls -la /root/autodl-tmp/ComfyUI/comfy/ldm 2>/dev/null || echo MISSING_LDM
echo '=== comfy top ==='
ls /root/autodl-tmp/ComfyUI/comfy | head
echo '=== find models dir ==='
find /root/autodl-tmp/ComfyUI/comfy -maxdepth 3 -type d -name models -print
echo '=== count py ==='
find /root/autodl-tmp/ComfyUI/comfy -name '*.py' | wc -l
echo '=== zip listing ldm ==='
python - <<'PY'
import zipfile
z=zipfile.ZipFile('/root/autodl-tmp/ComfyUI-src.zip')
names=[n for n in z.namelist() if 'ldm' in n or 'extra_model' in n]
print('zip_ldm', len(names))
print('\n'.join(names[:40]))
PY
"""
    _, out, err = c.exec_command(cmd, timeout=40)
    print(out.read().decode("utf-8", "replace"))
    e = err.read().decode("utf-8", "replace")
    if e.strip():
        print("STDERR", e[:500])
    c.close()


if __name__ == "__main__":
    main()
