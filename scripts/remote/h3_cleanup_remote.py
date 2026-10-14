# -*- coding: utf-8 -*-
"""Remote cleanup after H3 is up. Do not print secrets."""
import sys

import paramiko

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
rm -rf /root/autodl-tmp/ComfyUI-upstream /root/autodl-tmp/ComfyUI-master.zip /root/autodl-tmp/tmp/ComfyUI-master
ls /root/autodl-tmp/ComfyUI/user/default/workflows
python3 - <<'PY'
import os
# NOTE: host/port 已外置为环境变量，便于在不同实例间复用。
#   AUTODL_HOST / AUTODL_PORT  （或填入 .env，见 .env.example）
base="/root/autodl-tmp/ComfyUI/models"
files=[
"diffusion_models/minimax_h3_fl2va_pruned_bf16.safetensors",
"text_encoders/qwen3vl_32b_minimax_h3_nvfp4_awq.safetensors",
"vae/minimax_h3_video_vae_fp16.safetensors",
"vae/minimax_h3_audio_vae_fp32.safetensors",
"loras/minimax_h3_fl2v_turbo_4step_v1.0_768p_comfyui_bf16.safetensors",
]
want={
"diffusion_models/minimax_h3_fl2va_pruned_bf16.safetensors":40225724176,
"text_encoders/qwen3vl_32b_minimax_h3_nvfp4_awq.safetensors":15687142551,
"vae/minimax_h3_video_vae_fp16.safetensors":5207808496,
"vae/minimax_h3_audio_vae_fp32.safetensors":605254808,
"loras/minimax_h3_fl2v_turbo_4step_v1.0_768p_comfyui_bf16.safetensors":1956192992,
}
ok=True
for f in files:
    p=os.path.join(base,f)
    sz=os.path.getsize(p)
    print(sz, f, "OK" if sz==want[f] else "BAD")
    ok = ok and sz==want[f]
print("ALL_OK" if ok else "SIZE_BAD")
PY
df -h /root/autodl-tmp | tail -1
tail -5 /root/autodl-tmp/comfy.log
"""
    _, out, err = c.exec_command(cmd, timeout=60)
    print(out.read().decode("utf-8", "replace"))
    e = err.read().decode("utf-8", "replace")
    if e.strip():
        print("STDERR", e[:400])
    c.close()


if __name__ == "__main__":
    main()
