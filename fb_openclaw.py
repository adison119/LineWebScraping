# -*- coding: utf-8 -*-
"""
ส่งรายงานไป Cliq หรือ OpenClaw
- send_report_to_cliq(message, webhook_url) — ส่งไป Cliq (ใช้ CLIQ_WEBHOOK_URL เหมือน Airtable)
- send_report_to_openclaw(message, send_openclaw_target) — ส่งไป OpenClaw/ไลน์ (เดิม)
"""
import os
import shutil
import subprocess
import sys
import time

try:
    import requests
except ImportError:
    requests = None


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


# ความยาวสูงสุดต่อข้อความที่ส่ง Cliq (แบ่งส่งหลายข้อความถ้าเกิน)
MAX_CLIQ_CHUNK = 6000


def send_report_to_cliq(message, webhook_url, chunk_size=MAX_CLIQ_CHUNK):
    """
    ส่งข้อความรายงานไป Cliq ผ่าน Webhook (endpoint เดียวกับ Airtable)
    webhook_url = CLIQ_WEBHOOK_URL จาก .env
    """
    if not message or not (webhook_url or "").strip():
        return
    if requests is None:
        print("ต้องติดตั้ง requests เพื่อส่งไป Cliq (pip install requests)", file=sys.stderr)
        return
    url = (webhook_url or "").strip()
    headers = {"Content-Type": "application/json"}
    text = message.strip()
    if chunk_size and chunk_size > 0 and len(text) > chunk_size:
        start = 0
        while start < len(text):
            end = min(start + chunk_size, len(text))
            if end < len(text):
                break_at = text.rfind("\n", start, end + 1)
                if break_at == -1:
                    break_at = text.rfind(" ", start, end + 1)
                if break_at != -1 and break_at > start:
                    end = break_at + 1
            chunk = text[start:end]
            try:
                r = requests.post(url, json={"text": chunk}, headers=headers, timeout=60)
                if r.status_code not in (200, 201, 204):
                    print(f"Cliq API {r.status_code}: {(r.text or '')[:150]}", file=sys.stderr)
            except requests.RequestException as e:
                print(f"ส่ง Cliq ไม่สำเร็จ: {e}", file=sys.stderr)
            start = end
            if start < len(text):
                time.sleep(0.3)
    else:
        try:
            r = requests.post(url, json={"text": text}, headers=headers, timeout=60)
            if r.status_code not in (200, 201, 204):
                print(f"Cliq API {r.status_code}: {(r.text or '')[:150]}", file=sys.stderr)
        except requests.RequestException as e:
            print(f"ส่ง Cliq ไม่สำเร็จ: {e}", file=sys.stderr)
