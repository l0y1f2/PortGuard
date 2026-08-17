# -*- coding: utf-8 -*-
"""操作层：结束进程、防火墙封禁/解封端口。"""
from __future__ import annotations

from . import collector
from . import portlore

FW_PREFIX = "PortGuard_Block"


# --------------------------------------------------------------------------- #
# 结束进程
# --------------------------------------------------------------------------- #
def kill_process(pid: int, force: bool = True, tree: bool = False) -> dict:
    try:
        pid = int(pid)
    except (TypeError, ValueError):
        return {"ok": False, "msg": "无效的 PID"}
    if pid <= 4:
        return {"ok": False, "msg": "系统核心进程受保护，禁止结束"}

    name = ""
    try:
        if collector.psutil is not None:
            name = collector.psutil.Process(pid).name()
    except Exception:
        pass

    if portlore.kill_risk(name) == "protected":
        return {"ok": False, "msg": f"「{name}」是系统关键进程，禁止结束（会导致系统崩溃）"}

    args = ["taskkill", "/PID", str(pid)]
    if force:
        args.append("/F")
    if tree:
        args.append("/T")
    ok, out, err = collector.run_cmd(args)
    if ok:
        return {"ok": True, "msg": f"已结束进程 {name or ''} (PID {pid})".strip()}

    detail = (err or out or "").strip()
    if "拒绝访问" in detail or "Access is denied" in detail or "5" in detail:
        return {"ok": False, "need_admin": True,
                "msg": f"结束失败：权限不足，请以管理员身份重新启动 PortGuard。({detail[:120]})"}
    return {"ok": False, "msg": f"结束失败：{detail[:160] or '未知错误'}"}


# --------------------------------------------------------------------------- #
# 防火墙：封禁 / 解封端口
# --------------------------------------------------------------------------- #
def _rule_name(port: int, proto: str, direction: str) -> str:
    return f"{FW_PREFIX}_{proto.upper()}_{port}_{direction.upper()}"


def block_port(port: int, proto: str = "TCP", direction: str = "in") -> dict:
    if not collector.is_admin():
        return {"ok": False, "need_admin": True,
                "msg": "封禁端口需要管理员权限，请以管理员身份重新启动 PortGuard。"}
    try:
        port = int(port)
    except (TypeError, ValueError):
        return {"ok": False, "msg": "无效端口"}
    proto = "UDP" if proto.upper() == "UDP" else "TCP"
    dirs = ["in", "out"] if direction == "both" else [direction]
    created = []
    for d in dirs:
        rn = _rule_name(port, proto, d)
        collector.run_cmd(["netsh", "advfirewall", "firewall", "delete", "rule", f"name={rn}"])
        ok, out, err = collector.run_cmd([
            "netsh", "advfirewall", "firewall", "add", "rule",
            f"name={rn}", f"dir={d}", "action=block",
            f"protocol={proto}", f"localport={port}",
            "profile=any", "enable=yes",
        ])
        if not ok:
            return {"ok": False, "msg": f"封禁失败：{(err or out)[:160]}"}
        created.append(rn)
    return {"ok": True, "msg": f"已封禁 {proto} 端口 {port}（{'双向' if direction=='both' else direction}）",
            "rules": created}


def unblock_port(port: int, proto: str = "TCP") -> dict:
    if not collector.is_admin():
        return {"ok": False, "need_admin": True,
                "msg": "解封端口需要管理员权限，请以管理员身份重新启动 PortGuard。"}
    proto = "UDP" if proto.upper() == "UDP" else "TCP"
    removed = 0
    for d in ("in", "out"):
        rn = _rule_name(int(port), proto, d)
        ok, out, _ = collector.run_cmd(["netsh", "advfirewall", "firewall", "delete", "rule", f"name={rn}"])
        if ok and "确定" in out or "Deleted" in out or "Ok" in out:
            removed += 1
    return {"ok": True, "msg": f"已解封 {proto} 端口 {port}"}


def list_blocked() -> list[dict]:
    """列出由 PortGuard 创建的防火墙封禁规则。"""
    ok, out, _ = collector.run_powershell(
        "Get-NetFirewallRule -DisplayName 'PortGuard_Block*' -ErrorAction SilentlyContinue | "
        "ForEach-Object { $pf = $_ | Get-NetFirewallPortFilter; "
        "[pscustomobject]@{Name=$_.DisplayName; Dir=$_.Direction; Enabled=$_.Enabled; "
        "Proto=$pf.Protocol; Port=$pf.LocalPort} } | ConvertTo-Json -Compress"
    )
    rows = []
    if ok and out:
        import json
        try:
            data = json.loads(out)
            if isinstance(data, dict):
                data = [data]
            seen = set()
            for it in data:
                port = str(it.get("Port") or "")
                proto = str(it.get("Proto") or "")
                key = (port, proto)
                if key in seen:
                    continue
                seen.add(key)
                rows.append({
                    "port": int(port) if port.isdigit() else port,
                    "proto": proto,
                    "direction": str(it.get("Dir") or ""),
                    "enabled": str(it.get("Enabled")) in ("1", "True", "true"),
                    "name": it.get("Name") or "",
                })
        except Exception:
            pass
    rows.sort(key=lambda r: (str(r["port"]), r["proto"]))
    return rows
