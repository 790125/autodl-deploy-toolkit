# -*- coding: utf-8 -*-
import os, sys
sys.stdout.reconfigure(encoding="utf-8")
import paramiko
# NOTE: host/port 已外置为环境变量，便于在不同实例间复用。
#   AUTODL_HOST / AUTODL_PORT  （或填入 .env，见 .env.example）
c=paramiko.SSHClient(); c.set_missing_host_key_policy(paramiko.AutoAddPolicy())
c.connect(os.environ.get("AUTODL_HOST", "127.0.0.1"),
        port=int(os.environ.get("AUTODL_PORT", "22")), username="root", password=__import__("os").environ.get("AUTODL_SSH_PASSWORD", ""), timeout=40, banner_timeout=80, auth_timeout=40, allow_agent=False, look_for_keys=False)
_,out,err=c.exec_command("stat -c '%s %n' /root/autodl-tmp/ComfyUI/models/diffusion_models/minimax_h3_fl2va_pruned_bf16.safetensors /root/autodl-tmp/ComfyUI/models/text_encoders/qwen3vl_32b_minimax_h3_nvfp4_awq.safetensors /root/autodl-tmp/ComfyUI/models/vae/minimax_h3_video_vae_fp16.safetensors /root/autodl-tmp/ComfyUI/models/vae/minimax_h3_audio_vae_fp32.safetensors /root/autodl-tmp/ComfyUI/models/loras/minimax_h3_fl2v_turbo_4step_v1.0_768p_comfyui_bf16.safetensors")
print(out.read().decode())
c.close()
