# -*- coding: utf-8 -*-
"""
ส่งรายงานไป openclaw — 1 ฟังก์ชัน: send_report_to_openclaw(message, send_openclaw_target)
"""
import os
import shutil
import subprocess
import sys


def _find_openclaw_cmd(openclaw_cmd=None):
    if openclaw_cmd and os.path.isfile(openclaw_cmd):
        return openclaw_cmd
    for path in ("/opt/homebrew/bin/openclaw", "/usr/local/bin/openclaw"):
        if os.path.isfile(path):
            return path
    extra_paths = os.pathsep.join([
        os.environ.get("PATH", ""),
        "/opt/homebrew/bin",
        "/usr/local/bin",
    ])
    found = shutil.which("openclaw", path=extra_paths)
    return found if found else "openclaw"


def _send_one(message, target, openclaw_cmd=None):
    if not message or not message.strip():
        return False
    cmd = _find_openclaw_cmd(openclaw_cmd)
    env = os.environ.copy()
    env.setdefault("PATH", "")
    for p in ("/opt/homebrew/bin", "/usr/local/bin"):
        if p not in env["PATH"]:
            env["PATH"] = p + os.pathsep + env["PATH"]
    try:
        result = subprocess.run(
            [cmd, "message", "send", "-t", target, "--message", message.strip()],
            capture_output=True,
            text=True,
            timeout=30,
            env=env,
        )
        if result.returncode != 0:
            if result.stderr:
                print(result.stderr.strip(), file=sys.stderr)
            print(f"[openclaw] returncode={result.returncode} target={target!r}", file=sys.stderr)
        return result.returncode == 0
    except FileNotFoundError:
        print("ไม่พบคำสั่ง openclaw — ส่งผลไปไลน์ไม่สำเร็จ", file=sys.stderr)
        return False
    except Exception as e:
        print(f"ส่ง openclaw ไม่สำเร็จ: {e}", file=sys.stderr)
        return False


def send_report_to_openclaw(message, send_openclaw_target, openclaw_cmd=None):
    """
    ส่งข้อความรายงานไป openclaw ตาม target (ถ้ามีหลายคั่น comma ส่งทีละ target)
    """
    if not message or not send_openclaw_target:
        return
    targets = [t.strip() for t in str(send_openclaw_target).split(",") if t.strip()]
    for t in targets:
        _send_one(message, t, openclaw_cmd=openclaw_cmd)
