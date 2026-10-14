# -*- coding: utf-8 -*-
"""Local 6066 -> west Comfy 6006. TCP_NODELAY for WebSocket."""
import socket
import sys
import threading

import paramiko
# NOTE: host/port 已外置为环境变量，便于在不同实例间复用。
#   AUTODL_HOST / AUTODL_PORT  （或填入 .env，见 .env.example）

sys.stdout.reconfigure(encoding="utf-8")

HOST = __import__("os").environ.get("AUTODL_HOST", "127.0.0.1")
PORT = int(__import__("os").environ.get("AUTODL_PORT", "22"))
USER = "root"
PASS = __import__("os").environ.get("AUTODL_SSH_PASSWORD", "")

client = paramiko.SSHClient()
client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
client.connect(
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
transport = client.get_transport()
transport.set_keepalive(15)
transport.default_window_size = 2 * 1024 * 1024
transport.packetizer.REKEY_BYTES = pow(2, 40)
print("SSH_OK", HOST, PORT, flush=True)

local = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
local.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
try:
    local.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
except Exception:
    pass
local.bind(("127.0.0.1", 6066))
local.listen(64)
print("LISTEN 127.0.0.1:6066", flush=True)


def pipe(src, dst):
    try:
        while True:
            data = src.recv(256 * 1024)
            if not data:
                break
            dst.sendall(data)
    except Exception:
        pass
    for s in (src, dst):
        try:
            s.close()
        except Exception:
            pass


while True:
    conn, addr = local.accept()
    try:
        conn.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
        chan = transport.open_channel("direct-tcpip", ("127.0.0.1", 6006), addr)
        try:
            chan.set_combine_stderr(False)
        except Exception:
            pass
    except Exception as e:
        print("FWD_FAIL", type(e).__name__, flush=True)
        conn.close()
        continue
    threading.Thread(target=pipe, args=(conn, chan), daemon=True).start()
    threading.Thread(target=pipe, args=(chan, conn), daemon=True).start()
