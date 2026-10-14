import select
import socket
import threading

import paramiko
# NOTE: host/port 已外置为环境变量，便于在不同实例间复用。
#   AUTODL_HOST / AUTODL_PORT  （或填入 .env，见 .env.example）

HOST = __import__("os").environ.get("AUTODL_HOST", "127.0.0.1")
PORT = int(__import__("os").environ.get("AUTODL_PORT", "22"))
USER = "root"
PASSWORD = __import__("os").environ.get("AUTODL_SSH_PASSWORD", "")
LOCAL_PORT = 6066
REMOTE_HOST = "127.0.0.1"
REMOTE_PORT = 6006


def pipe(src, dst):
    try:
        while True:
            data = src.recv(32768)
            if not data:
                break
            dst.sendall(data)
    except Exception:
        pass
    try:
        src.close()
    except Exception:
        pass
    try:
        dst.close()
    except Exception:
        pass


def handle(client, transport):
    try:
        chan = transport.open_channel(
            "direct-tcpip",
            (REMOTE_HOST, REMOTE_PORT),
            client.getpeername(),
        )
    except Exception as e:
        print("open_channel fail", e)
        client.close()
        return
    t1 = threading.Thread(target=pipe, args=(client, chan), daemon=True)
    t2 = threading.Thread(target=pipe, args=(chan, client), daemon=True)
    t1.start()
    t2.start()


def main():
    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    client.connect(HOST, port=PORT, username=USER, password=PASSWORD, timeout=30, banner_timeout=30)
    transport = client.get_transport()
    transport.set_keepalive(30)
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    sock.bind(("127.0.0.1", LOCAL_PORT))
    sock.listen(32)
    print(f"TUNNEL_READY http://127.0.0.1:{LOCAL_PORT}", flush=True)
    while transport.is_active():
        r, _, _ = select.select([sock], [], [], 1.0)
        if sock in r:
            conn, _addr = sock.accept()
            threading.Thread(target=handle, args=(conn, transport), daemon=True).start()


if __name__ == "__main__":
    main()
