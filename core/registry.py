# -*- coding: utf-8 -*-
"""端口台账：把「这个端口是我给哪个项目留的」记下来，并自动做冲突检测。"""
from __future__ import annotations

import json
import os
import sys
import threading
import time
import uuid

_LOCK = threading.Lock()


def _resolve_data_dir():
    """冻结（单文件 EXE）后把数据放在 EXE 同目录，方便携带；
    若该目录不可写（如 Program Files），回退到 AppData。"""
    if getattr(sys, "frozen", False):
        cand = os.path.join(os.path.dirname(sys.executable), "data")
        try:
            os.makedirs(cand, exist_ok=True)
            probe = os.path.join(cand, ".writable_test")
            with open(probe, "w", encoding="utf-8") as f:
                f.write("1")
            os.remove(probe)
            return cand
        except Exception:
            pass
        return os.path.join(os.environ.get("APPDATA", os.path.expanduser("~")), "PortGuard")
    return os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data")


DATA_DIR = _resolve_data_dir()
DB_PATH = os.path.join(DATA_DIR, "registry.json")

FIELDS = ("port", "port_end", "proto", "project", "purpose", "owner", "expect", "tags", "note")


def _empty():
    return {"version": 1, "entries": []}


def load() -> dict:
    if not os.path.exists(DB_PATH):
        return _empty()
    try:
        with open(DB_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)
        if not isinstance(data, dict) or "entries" not in data:
            return _empty()
        return data
    except Exception:
        return _empty()


def save(data: dict) -> None:
    os.makedirs(DATA_DIR, exist_ok=True)
    tmp = DB_PATH + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    os.replace(tmp, DB_PATH)


def _clean(raw: dict) -> dict:
    port = int(raw.get("port") or 0)
    port_end = raw.get("port_end")
    try:
        port_end = int(port_end) if port_end not in (None, "", 0) else None
    except (TypeError, ValueError):
        port_end = None
    if port_end and port_end < port:
        port, port_end = port_end, port
    proto = str(raw.get("proto") or "ANY").upper()
    if proto not in ("TCP", "UDP", "ANY"):
        proto = "ANY"
    tags = raw.get("tags") or []
    if isinstance(tags, str):
        tags = [t.strip() for t in tags.replace("，", ",").split(",") if t.strip()]
    return {
        "port": port, "port_end": port_end, "proto": proto,
        "project": (raw.get("project") or "").strip(),
        "purpose": (raw.get("purpose") or "").strip(),
        "owner": (raw.get("owner") or "").strip(),
        "expect": (raw.get("expect") or "").strip(),
        "tags": tags[:8],
        "note": (raw.get("note") or "").strip(),
    }


def upsert(raw: dict) -> dict:
    with _LOCK:
        data = load()
        item = _clean(raw)
        if not item["port"] or not (1 <= item["port"] <= 65535):
            return {"ok": False, "msg": "端口必须在 1–65535 之间"}
        if not item["project"]:
            return {"ok": False, "msg": "请填写项目/系统名称"}
        eid = raw.get("id")
        now = time.time()
        if eid:
            for e in data["entries"]:
                if e.get("id") == eid:
                    e.update(item)
                    e["updated_at"] = now
                    save(data)
                    return {"ok": True, "msg": "已更新登记", "entry": e}
            return {"ok": False, "msg": "登记记录不存在"}
        for e in data["entries"]:
            if e["port"] == item["port"] and e.get("port_end") == item["port_end"] \
                    and e["proto"] == item["proto"]:
                return {"ok": False, "msg": f"端口 {item['port']} 已登记给「{e['project']}」，请直接编辑"}
        item["id"] = uuid.uuid4().hex[:12]
        item["created_at"] = now
        item["updated_at"] = now
        data["entries"].append(item)
        save(data)
        return {"ok": True, "msg": f"已登记端口 {item['port']}", "entry": item}


def delete(eid: str) -> dict:
    with _LOCK:
        data = load()
        before = len(data["entries"])
        data["entries"] = [e for e in data["entries"] if e.get("id") != eid]
        if len(data["entries"]) == before:
            return {"ok": False, "msg": "记录不存在"}
        save(data)
        return {"ok": True, "msg": "已删除登记"}


def quick_register_from_port(row: dict, project: str) -> dict:
    """从实时端口一键登记。"""
    return upsert({
        "port": row.get("port"), "proto": row.get("proto") or "ANY",
        "project": project, "purpose": row.get("hint") or "",
        "expect": row.get("pname") or "", "note": "由运行中的端口一键登记",
    })


# --------------------------------------------------------------------------- #
# 匹配与冲突检测
# --------------------------------------------------------------------------- #
def _match(entry: dict, port: int, proto: str) -> bool:
    lo = entry["port"]
    hi = entry.get("port_end") or lo
    if not (lo <= port <= hi):
        return False
    ep = entry.get("proto", "ANY")
    return ep == "ANY" or ep == proto


def _expect_ok(entry: dict, row: dict) -> bool:
    exp = (entry.get("expect") or "").strip().lower()
    if not exp:
        return True
    hay = f'{row.get("pname","")} {row.get("exe","")} {row.get("cmdline","")}'.lower()
    return exp in hay


def annotate(snapshot: dict) -> dict:
    """给快照里的端口打上台账信息，并汇总冲突。"""
    data = load()
    entries = data["entries"]
    issues = []

    # 端口 -> 监听者（用于识别同端口多进程）
    owners: dict[int, set] = {}
    for row in snapshot.get("ports", []):
        if row.get("pid"):
            owners.setdefault(row["port"], set()).add(row["pid"])

    for row in snapshot.get("ports", []):
        hit = next((e for e in entries if _match(e, row["port"], row["proto"])), None)
        if hit:
            ok = _expect_ok(hit, row)
            row["reg"] = {
                "id": hit["id"], "project": hit["project"], "purpose": hit["purpose"],
                "owner": hit["owner"], "tags": hit.get("tags", []), "note": hit.get("note", ""),
                "expect": hit.get("expect", ""),
            }
            row["reg_status"] = "matched" if ok else "hijacked"
            if not ok:
                issues.append({
                    "level": "high", "type": "hijacked", "port": row["port"], "proto": row["proto"],
                    "title": f'{row["proto"]} {row["port"]} 被非预期进程占用',
                    "detail": f'登记给「{hit["project"]}」（期望 {hit["expect"]}），'
                              f'实际是 {row["pname"] or "未知进程"} (PID {row["pid"]})',
                    "pid": row["pid"], "entry_id": hit["id"],
                })
        else:
            row["reg"] = None
            row["reg_status"] = "unregistered"

        if len(owners.get(row["port"], set())) > 1:
            row["multi_owner"] = True

    for port, pids in owners.items():
        if len(pids) > 1:
            names = []
            for row in snapshot.get("ports", []):
                if row["port"] == port and row["pname"] not in names:
                    names.append(row["pname"])
            issues.append({
                "level": "mid", "type": "multi", "port": port, "proto": "",
                "title": f"端口 {port} 有多个进程在监听",
                "detail": "占用者：" + "、".join(f"{n}" for n in names if n) +
                          f"（PID {', '.join(str(p) for p in sorted(pids))}）",
                "pid": 0, "entry_id": "",
            })

    # 登记了但当前空闲的
    reg_rows = []
    for e in entries:
        matched = [r for r in snapshot.get("ports", []) if _match(e, r["port"], r["proto"])]
        if not matched:
            status, holder = "idle", None
        elif all(_expect_ok(e, r) for r in matched):
            status = "occupied_ok"
            holder = {"pid": matched[0]["pid"], "pname": matched[0]["pname"]}
        else:
            bad = next(r for r in matched if not _expect_ok(e, r))
            status = "conflict"
            holder = {"pid": bad["pid"], "pname": bad["pname"]}
        item = dict(e)
        item["status"] = status
        item["holder"] = holder
        item["live_ports"] = sorted({r["port"] for r in matched})
        reg_rows.append(item)

    reg_rows.sort(key=lambda r: (r["port"], r.get("port_end") or 0))
    snapshot["registry"] = reg_rows
    snapshot["issues"] = sorted(issues, key=lambda i: 0 if i["level"] == "high" else 1)
    snapshot["stats"]["registered"] = len(entries)
    snapshot["stats"]["conflicts"] = len([i for i in issues if i["level"] == "high"])
    snapshot["stats"]["warnings"] = len([i for i in issues if i["level"] != "high"])
    snapshot["stats"]["unregistered"] = len([
        r for r in snapshot.get("ports", [])
        if r["reg_status"] == "unregistered" and 1024 <= r["port"] < 49152
        and r.get("kind") != "system"
    ])
    return snapshot


def suggest_free_ports(start: int = 8000, count: int = 5, proto: str = "TCP",
                       snapshot: dict | None = None) -> list[int]:
    """推荐可用端口：跳过正在监听的、已登记的、以及知名端口。"""
    from . import collector
    from . import portlore

    used = set()
    if snapshot is None:
        try:
            for c in collector.collect_connections():
                used.add(c["port"])
        except Exception:
            pass
    else:
        for r in snapshot.get("ports", []):
            used.add(r["port"])

    entries = load()["entries"]
    result = []
    port = max(1024, int(start))
    while port <= 65000 and len(result) < count:
        if port not in used and port not in portlore.WELL_KNOWN_PORTS \
                and not any(_match(e, port, proto) for e in entries):
            result.append(port)
        port += 1
    return result
