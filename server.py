# -*- coding: utf-8 -*-
"""PortGuard 本地服务：提供只读 API + 操作 API，并托管前端页面。

仅监听 127.0.0.1，避免自己成为一个对外暴露的服务。
"""
from __future__ import annotations

import ctypes
import json
import os
import sys
import threading
import time
import webbrowser
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlparse, parse_qs

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, BASE_DIR)

from core import collector, actions, registry  # noqa: E402

# 冻结（PyInstaller 单文件）后，静态资源被解压到 _MEIPASS
WEB_DIR = os.path.join(getattr(sys, "_MEIPASS", BASE_DIR), "web")
HOST = "127.0.0.1"
DEFAULT_PORT = 8770

_snap_lock = threading.Lock()


def get_snapshot(include_udp=True):
    with _snap_lock:
        snap = collector.build_snapshot(include_udp=include_udp)
        registry.annotate(snap)
        return snap


class Handler(BaseHTTPRequestHandler):
    server_version = "PortGuard/1.0"

    def log_message(self, *args):
        pass  # 静默，避免刷屏

    # ------------------------------------------------------------------ #
    def _send_json(self, obj, code=200):
        body = json.dumps(obj, ensure_ascii=False).encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)

    def _send_file(self, path):
        if not os.path.isfile(path):
            self.send_error(404)
            return
        ctype = {
            ".html": "text/html; charset=utf-8",
            ".js": "application/javascript; charset=utf-8",
            ".css": "text/css; charset=utf-8",
            ".svg": "image/svg+xml",
        }.get(os.path.splitext(path)[1], "application/octet-stream")
        with open(path, "rb") as f:
            body = f.read()
        self.send_response(200)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _read_body(self):
        length = int(self.headers.get("Content-Length") or 0)
        if not length:
            return {}
        try:
            return json.loads(self.rfile.read(length).decode("utf-8"))
        except Exception:
            return {}

    # ------------------------------------------------------------------ #
    def do_GET(self):
        parsed = urlparse(self.path)
        path = parsed.path
        q = parse_qs(parsed.query)

        if path == "/" or path == "/index.html":
            return self._send_file(os.path.join(WEB_DIR, "index.html"))
        if path.startswith("/static/"):
            return self._send_file(os.path.join(WEB_DIR, path[len("/static/"):]))

        if path == "/api/snapshot":
            udp = q.get("udp", ["1"])[0] != "0"
            return self._send_json(get_snapshot(include_udp=udp))
        if path == "/api/services":
            force = q.get("force", ["0"])[0] == "1"
            return self._send_json({"ok": True, "services": collector.collect_services(force)})
        if path == "/api/process":
            pid = int(q.get("pid", ["0"])[0] or 0)
            return self._send_json(collector.process_detail(pid))
        if path == "/api/registry":
            return self._send_json({"ok": True, **registry.load()})
        if path == "/api/blocked":
            return self._send_json({"ok": True, "rules": actions.list_blocked()})
        if path == "/api/suggest":
            start = int(q.get("start", ["8000"])[0] or 8000)
            proto = q.get("proto", ["TCP"])[0]
            return self._send_json({"ok": True,
                                    "ports": registry.suggest_free_ports(start, 6, proto)})
        if path == "/api/health":
            return self._send_json({"ok": True, "admin": collector.is_admin(),
                                    "engine": "psutil" if collector.psutil else "powershell"})
        self.send_error(404)

    def do_POST(self):
        path = urlparse(self.path).path
        body = self._read_body()

        if path == "/api/relaunch-admin":
            return self._send_json(relaunch_as_admin())
        if path == "/api/quit":
            threading.Thread(target=lambda: (time.sleep(0.2), os._exit(0))).start()
            return self._send_json({"ok": True})
        if path == "/api/kill":
            return self._send_json(actions.kill_process(
                body.get("pid"), force=body.get("force", True), tree=body.get("tree", False)))
        if path == "/api/block":
            return self._send_json(actions.block_port(
                body.get("port"), body.get("proto", "TCP"), body.get("direction", "in")))
        if path == "/api/unblock":
            return self._send_json(actions.unblock_port(
                body.get("port"), body.get("proto", "TCP")))
        if path == "/api/registry/save":
            return self._send_json(registry.upsert(body))
        if path == "/api/registry/delete":
            return self._send_json(registry.delete(body.get("id")))
        if path == "/api/registry/quick":
            return self._send_json(registry.quick_register_from_port(
                body.get("row", {}), body.get("project", "")))
        self.send_error(404)


def find_port(preferred=DEFAULT_PORT):
    import socket
    for p in [preferred] + list(range(8771, 8800)):
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        try:
            s.bind((HOST, p))
            s.close()
            return p
        except OSError:
            s.close()
    return preferred


def relaunch_as_admin():
    """用 UAC 以管理员身份重启自身；成功返回 {ok:True}。"""
    try:
        exe = sys.executable
        cwd = os.path.dirname(exe) or None
        # 冻结后 sys.executable 即本 EXE；开发模式下补上脚本路径
        params = "" if getattr(sys, "frozen", False) else f'"{os.path.abspath(__file__)}"'
        res = ctypes.windll.shell32.ShellExecuteW(0, "runas", exe, params, cwd, 1)
        if res > 32:
            threading.Thread(target=lambda: (time.sleep(0.4), os._exit(0))).start()
            return {"ok": True, "msg": "正在以管理员身份重启…"}
        return {"ok": False, "msg": "已取消提权（未以管理员运行）"}
    except Exception as e:
        return {"ok": False, "msg": f"提权失败：{e}"}


def _safe_print(*args):
    try:
        print(*args)
    except Exception:
        pass


def main():
    port = find_port()
    httpd = ThreadingHTTPServer((HOST, port), Handler)
    url = f"http://{HOST}:{port}/"
    admin = collector.is_admin()
    _safe_print("=" * 54)
    _safe_print("  PortGuard 端口 / 进程 / 服务管家")
    _safe_print("=" * 54)
    _safe_print(f"  访问地址 : {url}")
    _safe_print(f"  采集引擎 : {'psutil' if collector.psutil else 'PowerShell 兜底'}")
    _safe_print(f"  管理员权限 : {'是 ✓（可结束任意进程 / 操作防火墙）' if admin else '否（部分操作受限）'}")
    _safe_print("  关闭此程序即可停止服务。")
    _safe_print("=" * 54)
    try:
        threading.Timer(0.8, lambda: webbrowser.open(url)).start()
    except Exception:
        pass
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        _safe_print("\n已停止。")
        httpd.shutdown()


if __name__ == "__main__":
    main()
