# -*- coding: utf-8 -*-
"""端口 / 进程 / 服务 采集层。

主路径使用 psutil；若环境没有 psutil，则降级为 PowerShell 采集（只读功能可用）。
"""
from __future__ import annotations

import ctypes
import json
import os
import subprocess
import sys
import time

from . import portlore

try:
    import psutil
except Exception:  # pragma: no cover
    psutil = None

CREATE_NO_WINDOW = 0x08000000
_proc_cache: dict[int, "psutil.Process"] = {}
_svc_cache = {"ts": 0.0, "data": []}


# --------------------------------------------------------------------------- #
# 基础工具
# --------------------------------------------------------------------------- #
def is_admin() -> bool:
    try:
        return bool(ctypes.windll.shell32.IsUserAnAdmin())
    except Exception:
        return False


def run_powershell(script: str, timeout: int = 25):
    """执行 PowerShell 并返回 (ok, stdout, stderr)。"""
    try:
        r = subprocess.run(
            ["powershell", "-NoProfile", "-NonInteractive", "-ExecutionPolicy", "Bypass",
             "-Command", script],
            capture_output=True, timeout=timeout, creationflags=CREATE_NO_WINDOW,
        )
        out = r.stdout.decode("utf-8", "ignore") or r.stdout.decode("gbk", "ignore")
        err = r.stderr.decode("utf-8", "ignore") or r.stderr.decode("gbk", "ignore")
        return r.returncode == 0, out.strip(), err.strip()
    except subprocess.TimeoutExpired:
        return False, "", "PowerShell 执行超时"
    except Exception as exc:
        return False, "", str(exc)


def run_cmd(args: list[str], timeout: int = 20):
    try:
        r = subprocess.run(args, capture_output=True, timeout=timeout,
                           creationflags=CREATE_NO_WINDOW)
        out = r.stdout.decode("gbk", "ignore") if r.stdout else ""
        err = r.stderr.decode("gbk", "ignore") if r.stderr else ""
        return r.returncode == 0, out.strip(), err.strip()
    except Exception as exc:
        return False, "", str(exc)


def _fmt_uptime(created: float) -> str:
    if not created:
        return ""
    sec = max(0, int(time.time() - created))
    d, sec = divmod(sec, 86400)
    h, sec = divmod(sec, 3600)
    m, s = divmod(sec, 60)
    if d:
        return f"{d}天{h}小时"
    if h:
        return f"{h}小时{m}分"
    if m:
        return f"{m}分{s}秒"
    return f"{s}秒"


# --------------------------------------------------------------------------- #
# 进程 / 服务映射
# --------------------------------------------------------------------------- #
def _service_map() -> dict[int, list[str]]:
    """PID -> 服务名列表（用于说明 svchost 到底在跑什么）。"""
    mapping: dict[int, list[str]] = {}
    ok, out, _ = run_cmd(["tasklist", "/svc", "/fo", "csv", "/nh"])
    if ok and out:
        import csv
        import io
        for row in csv.reader(io.StringIO(out)):
            if len(row) >= 3:
                try:
                    pid = int(row[1])
                except ValueError:
                    continue
                svcs = [s.strip() for s in row[2].split(",") if s.strip() and s.strip() != "N/A"]
                if svcs:
                    mapping[pid] = svcs
    if mapping:
        return mapping
    # 兜底：PowerShell
    ok, out, _ = run_powershell(
        "Get-CimInstance Win32_Service | Where-Object {$_.ProcessId -gt 0} | "
        "Select-Object ProcessId,Name | ConvertTo-Json -Compress"
    )
    if ok and out:
        try:
            data = json.loads(out)
            if isinstance(data, dict):
                data = [data]
            for it in data:
                mapping.setdefault(int(it["ProcessId"]), []).append(it["Name"])
        except Exception:
            pass
    return mapping


def collect_processes(svc_map: dict[int, list[str]] | None = None) -> dict[int, dict]:
    """采集全部进程，返回 {pid: info}。"""
    if svc_map is None:
        svc_map = _service_map()
    result: dict[int, dict] = {}

    if psutil is None:
        return _collect_processes_ps(svc_map)

    alive = set()
    for proc in psutil.process_iter(["pid", "name", "username", "create_time",
                                    "memory_info", "num_threads"]):
        try:
            info = proc.info
            pid = info["pid"]
            alive.add(pid)
            cached = _proc_cache.get(pid)
            if cached is None or cached.pid != pid:
                cached = proc
                _proc_cache[pid] = proc
            try:
                cpu = round(cached.cpu_percent(None), 1)
            except Exception:
                cpu = 0.0
            try:
                exe = proc.exe() or ""
            except Exception:
                exe = ""
            try:
                cmdline = " ".join(proc.cmdline())
            except Exception:
                cmdline = ""
            name = info.get("name") or ""
            stack, kind = portlore.describe_process(name)
            mem = info.get("memory_info")
            result[pid] = {
                "pid": pid,
                "name": name,
                "exe": exe,
                "cmdline": cmdline,
                "user": (info.get("username") or "").split("\\")[-1],
                "created": info.get("create_time") or 0,
                "uptime": _fmt_uptime(info.get("create_time") or 0),
                "mem_mb": round((mem.rss if mem else 0) / 1048576, 1),
                "cpu": cpu,
                "threads": info.get("num_threads") or 0,
                "services": svc_map.get(pid, []),
                "stack": stack,
                "kind": kind,
                "risk": portlore.kill_risk(name),
                "ports": [],
            }
        except Exception:
            continue

    for dead in [p for p in _proc_cache if p not in alive]:
        _proc_cache.pop(dead, None)
    return result


def _collect_processes_ps(svc_map) -> dict[int, dict]:
    """无 psutil 时的兜底进程采集。"""
    ok, out, _ = run_powershell(
        "Get-CimInstance Win32_Process | Select-Object ProcessId,Name,ExecutablePath,"
        "CommandLine,WorkingSetSize,ThreadCount,CreationDate | ConvertTo-Json -Compress"
    )
    result: dict[int, dict] = {}
    if not (ok and out):
        return result
    try:
        data = json.loads(out)
    except Exception:
        return result
    if isinstance(data, dict):
        data = [data]
    for it in data:
        pid = int(it.get("ProcessId") or 0)
        name = it.get("Name") or ""
        stack, kind = portlore.describe_process(name)
        result[pid] = {
            "pid": pid, "name": name, "exe": it.get("ExecutablePath") or "",
            "cmdline": it.get("CommandLine") or "", "user": "", "created": 0,
            "uptime": "", "mem_mb": round((it.get("WorkingSetSize") or 0) / 1048576, 1),
            "cpu": 0.0, "threads": it.get("ThreadCount") or 0,
            "services": svc_map.get(pid, []), "stack": stack, "kind": kind,
            "risk": portlore.kill_risk(name), "ports": [],
        }
    return result


# --------------------------------------------------------------------------- #
# 端口 / 连接
# --------------------------------------------------------------------------- #
def _scope_of(ip: str) -> str:
    if ip in ("0.0.0.0", "::", "*", ""):
        return "全网可访问"
    if ip.startswith("127.") or ip == "::1":
        return "仅本机"
    return "指定网卡"


def _widest_scope(addrs: list[str]) -> str:
    scopes = {_scope_of(a) for a in addrs}
    for s in ("全网可访问", "指定网卡", "仅本机"):
        if s in scopes:
            return s
    return "仅本机"


def _norm_addr(addr) -> tuple[str, int]:
    if not addr:
        return "", 0
    if isinstance(addr, tuple):
        return (addr[0] or ""), int(addr[1] or 0)
    return (getattr(addr, "ip", "") or ""), int(getattr(addr, "port", 0) or 0)


def collect_connections() -> list[dict]:
    """采集 TCP/UDP 连接（含监听）。"""
    if psutil is None:
        return _collect_connections_ps()
    rows = []
    try:
        conns = psutil.net_connections("inet")
    except Exception:
        return _collect_connections_ps()
    for c in conns:
        lip, lport = _norm_addr(c.laddr)
        rip, rport = _norm_addr(c.raddr)
        proto = "TCP" if c.type == 1 else "UDP"
        status = c.status if c.status and c.status != "NONE" else ("LISTEN" if proto == "UDP" else "")
        rows.append({
            "proto": proto,
            "family": "IPv6" if ":" in lip else "IPv4",
            "local_ip": lip, "port": lport,
            "remote_ip": rip, "remote_port": rport,
            "status": status,
            "pid": c.pid or 0,
        })
    return rows


def _collect_connections_ps() -> list[dict]:
    rows = []
    ok, out, _ = run_powershell(
        "$t = Get-NetTCPConnection | Select-Object @{n='Proto';e={'TCP'}},LocalAddress,LocalPort,"
        "RemoteAddress,RemotePort,State,OwningProcess; "
        "$u = Get-NetUDPEndpoint | Select-Object @{n='Proto';e={'UDP'}},LocalAddress,LocalPort,"
        "@{n='RemoteAddress';e={''}},@{n='RemotePort';e={0}},@{n='State';e={'LISTEN'}},OwningProcess; "
        "@($t) + @($u) | ConvertTo-Json -Compress -Depth 3"
    )
    if not (ok and out):
        return rows
    try:
        data = json.loads(out)
    except Exception:
        return rows
    if isinstance(data, dict):
        data = [data]
    state_map = {2: "LISTEN", 5: "ESTABLISHED", "Listen": "LISTEN", "Established": "ESTABLISHED"}
    for it in data:
        lip = str(it.get("LocalAddress") or "")
        st = it.get("State")
        rows.append({
            "proto": it.get("Proto") or "TCP",
            "family": "IPv6" if ":" in lip else "IPv4",
            "local_ip": lip, "port": int(it.get("LocalPort") or 0),
            "remote_ip": str(it.get("RemoteAddress") or ""),
            "remote_port": int(it.get("RemotePort") or 0),
            "status": state_map.get(st, str(st or "")),
            "pid": int(it.get("OwningProcess") or 0),
        })
    return rows


# --------------------------------------------------------------------------- #
# 快照：把端口和进程组合成界面需要的形状
# --------------------------------------------------------------------------- #
def build_snapshot(include_udp: bool = True, include_conns: bool = False) -> dict:
    svc_map = _service_map()
    procs = collect_processes(svc_map)
    conns = collect_connections()

    listen_rows: dict[str, dict] = {}
    established: dict[int, int] = {}   # 端口 -> 已建立连接数
    outbound = 0

    for c in conns:
        pid = c["pid"]
        st = (c["status"] or "").upper()
        if st == "LISTEN":
            if c["proto"] == "UDP" and not include_udp:
                continue
            # 同一进程在同一端口上的 IPv4/IPv6/多网卡绑定合并成一行，界面更清爽
            key = f'{c["proto"]}|{c["port"]}|{pid}'
            if key in listen_rows:
                row = listen_rows[key]
                if c["local_ip"] not in row["addrs"]:
                    row["addrs"].append(c["local_ip"])
                    row["scope"] = _widest_scope(row["addrs"])
                    row["local_ip"] = " / ".join(row["addrs"][:3])
                if c["family"] not in row["families"]:
                    row["families"].append(c["family"])
                continue
            p = procs.get(pid, {})
            listen_rows[key] = {
                "id": key,
                "proto": c["proto"],
                "family": c["family"],
                "families": [c["family"]],
                "addrs": [c["local_ip"]],
                "local_ip": c["local_ip"],
                "port": c["port"],
                "scope": _widest_scope([c["local_ip"]]),
                "pid": pid,
                "pname": p.get("name", "" if pid else "系统"),
                "exe": p.get("exe", ""),
                "cmdline": p.get("cmdline", ""),
                "user": p.get("user", ""),
                "uptime": p.get("uptime", ""),
                "mem_mb": p.get("mem_mb", 0),
                "cpu": p.get("cpu", 0),
                "services": p.get("services", []),
                "stack": p.get("stack", ""),
                "kind": p.get("kind", "other"),
                "risk": p.get("risk", "normal"),
                "hint": portlore.describe_port(c["port"]),
                "conns": 0,
            }
        elif st == "ESTABLISHED":
            established[c["port"]] = established.get(c["port"], 0) + 1
            outbound += 1

    for row in listen_rows.values():
        row["conns"] = established.get(row["port"], 0)
        if row["pid"] in procs:
            procs[row["pid"]]["ports"].append({
                "proto": row["proto"], "port": row["port"],
                "local_ip": row["local_ip"], "scope": row["scope"],
            })

    ports = sorted(listen_rows.values(), key=lambda r: (r["port"], r["proto"]))

    proc_list = []
    for p in procs.values():
        if p["ports"]:
            item = dict(p)
            item["listen_ports"] = sorted({x["port"] for x in p["ports"]})
            proc_list.append(item)
    proc_list.sort(key=lambda p: (-len(p["listen_ports"]), p["name"].lower()))

    dev_ports = [p for p in ports if p["kind"] in ("dev", "db", "container") or
                 (1024 <= p["port"] < 49152 and p["kind"] not in ("system",))]

    snapshot = {
        "ts": time.time(),
        "admin": is_admin(),
        "engine": "psutil" if psutil else "powershell",
        "ports": ports,
        "processes": proc_list,
        "stats": {
            "listen_total": len(ports),
            "tcp": len([p for p in ports if p["proto"] == "TCP"]),
            "udp": len([p for p in ports if p["proto"] == "UDP"]),
            "public": len([p for p in ports if p["scope"] == "全网可访问"]),
            "proc_with_port": len(proc_list),
            "proc_total": len(procs),
            "dev_ports": len(dev_ports),
            "established": outbound,
        },
    }
    if include_conns:
        snapshot["connections"] = [c for c in conns if (c["status"] or "").upper() == "ESTABLISHED"]
    return snapshot


# --------------------------------------------------------------------------- #
# Windows 服务
# --------------------------------------------------------------------------- #
def collect_services(force: bool = False) -> list[dict]:
    now = time.time()
    if not force and _svc_cache["data"] and now - _svc_cache["ts"] < 20:
        return _svc_cache["data"]

    rows = []
    if psutil is not None:
        try:
            for svc in psutil.win_service_iter():
                try:
                    d = svc.as_dict()
                except Exception:
                    continue
                rows.append({
                    "name": d.get("name") or "",
                    "display": d.get("display_name") or "",
                    "status": d.get("status") or "",
                    "start_type": d.get("start_type") or "",
                    "pid": d.get("pid") or 0,
                    "binpath": d.get("binpath") or "",
                    "username": d.get("username") or "",
                    "description": (d.get("description") or "")[:400],
                })
        except Exception:
            rows = []

    if not rows:
        ok, out, _ = run_powershell(
            "Get-CimInstance Win32_Service | Select-Object Name,DisplayName,State,StartMode,"
            "ProcessId,PathName,StartName,Description | ConvertTo-Json -Compress"
        )
        if ok and out:
            try:
                data = json.loads(out)
                if isinstance(data, dict):
                    data = [data]
                for it in data:
                    rows.append({
                        "name": it.get("Name") or "",
                        "display": it.get("DisplayName") or "",
                        "status": (it.get("State") or "").lower(),
                        "start_type": (it.get("StartMode") or "").lower(),
                        "pid": int(it.get("ProcessId") or 0),
                        "binpath": it.get("PathName") or "",
                        "username": it.get("StartName") or "",
                        "description": (it.get("Description") or "")[:400],
                    })
            except Exception:
                pass

    # 关联端口
    snap_ports: dict[int, list[int]] = {}
    try:
        for c in collect_connections():
            if (c["status"] or "").upper() == "LISTEN" and c["pid"]:
                snap_ports.setdefault(c["pid"], []).append(c["port"])
    except Exception:
        pass
    for r in rows:
        r["ports"] = sorted(set(snap_ports.get(r["pid"], [])))

    rows.sort(key=lambda r: (r["status"] != "running", r["display"].lower() or r["name"].lower()))
    _svc_cache["ts"] = now
    _svc_cache["data"] = rows
    return rows


def process_detail(pid: int) -> dict:
    """单个进程的详细信息（详情面板用）。"""
    if psutil is None:
        return {"pid": pid, "error": "当前环境缺少 psutil，无法读取详情"}
    try:
        p = psutil.Process(pid)
    except Exception as exc:
        return {"pid": pid, "error": f"进程不存在或无权访问：{exc}"}

    def safe(fn, default=""):
        try:
            return fn()
        except Exception:
            return default

    name = safe(p.name)
    stack, kind = portlore.describe_process(name)
    conns = []
    for c in safe(lambda: p.net_connections("inet"), []):
        lip, lport = _norm_addr(c.laddr)
        rip, rport = _norm_addr(c.raddr)
        conns.append({
            "proto": "TCP" if c.type == 1 else "UDP",
            "local": f"{lip}:{lport}", "remote": f"{rip}:{rport}" if rip else "",
            "status": c.status if c.status != "NONE" else "LISTEN",
        })
    parent = safe(p.parent, None)
    children = [{"pid": c.pid, "name": safe(c.name)} for c in safe(lambda: p.children(), [])[:30]]
    mem = safe(p.memory_info, None)
    return {
        "pid": pid,
        "name": name,
        "exe": safe(p.exe),
        "cmdline": " ".join(safe(lambda: p.cmdline(), [])),
        "cwd": safe(p.cwd),
        "user": safe(p.username).split("\\")[-1],
        "created": safe(p.create_time, 0),
        "uptime": _fmt_uptime(safe(p.create_time, 0)),
        "mem_mb": round((mem.rss if mem else 0) / 1048576, 1),
        "cpu": safe(lambda: round(p.cpu_percent(None), 1), 0.0),
        "threads": safe(p.num_threads, 0),
        "status": safe(p.status),
        "nice": str(safe(p.nice, "")),
        "parent": {"pid": parent.pid, "name": safe(parent.name)} if parent else None,
        "children": children,
        "connections": conns,
        "stack": stack, "kind": kind,
        "risk": portlore.kill_risk(name),
        "services": _service_map().get(pid, []),
        "open_files": [f.path for f in safe(lambda: p.open_files(), [])[:40]],
    }
