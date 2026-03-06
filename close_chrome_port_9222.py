# -*- coding: utf-8 -*-
"""
ปิด Chrome ที่เปิดด้วย remote-debugging-port (สำหรับ LINE OA script)
รองรับหลายบัญชี: บัญชี 1 = port 9222, บัญชี 2 = 9223, ...
Usage:
  python close_chrome_port_9222.py              -> ปิด port 9222
  python close_chrome_port_9222.py --port 9223  -> ปิด port 9223
  python close_chrome_port_9222.py --all        -> ปิด 9222,9223,9224,9225 (ทุก slot ที่ใช้กับ script)
รองรับ Windows, macOS และ Linux — ใช้กับ cron บน OpenClaw ตั้งเวลาได้ เช่น 19:00
"""
import argparse
import subprocess
import sys


def get_pids_listening_on_port_windows(port):
    """คืนรายการ PID ที่กำลัง listen บน port (Windows: netstat -ano)"""
    port = int(port)
    try:
        out = subprocess.check_output(
            ["netstat", "-ano"],
            creationflags=subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0,
            text=True,
            encoding="utf-8",
            errors="replace",
        )
    except Exception as e:
        print(f"รัน netstat ไม่สำเร็จ: {e}", file=sys.stderr)
        return []

    pids = []
    for line in out.splitlines():
        line = line.strip()
        if f":{port}" not in line or "LISTENING" not in line.upper():
            continue
        parts = line.split()
        if not parts:
            continue
        pid_str = parts[-1]
        if pid_str.isdigit():
            pids.append(int(pid_str))
    return list(dict.fromkeys(pids))


def get_pids_listening_on_port_unix(port):
    """คืนรายการ PID ที่กำลัง listen บน port (macOS/Linux: lsof -ti :port)"""
    port = int(port)
    try:
        out = subprocess.check_output(
            ["lsof", "-ti", f":{port}"],
            text=True,
            encoding="utf-8",
            errors="replace",
        )
    except subprocess.CalledProcessError:
        return []
    except Exception as e:
        print(f"รัน lsof ไม่สำเร็จ: {e}", file=sys.stderr)
        return []

    pids = []
    for line in out.splitlines():
        line = line.strip()
        if line.isdigit():
            pids.append(int(line))
    return pids


def kill_pids_windows(pids):
    """ปิด process ตาม PID ด้วย taskkill (Windows)"""
    for pid in pids:
        try:
            subprocess.run(
                ["taskkill", "/F", "/PID", str(pid)],
                capture_output=True,
                timeout=10,
                creationflags=subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0,
            )
            print(f"ปิด process PID {pid} แล้ว")
        except Exception as e:
            print(f"ปิด PID {pid} ไม่สำเร็จ: {e}", file=sys.stderr)


def kill_pids_unix(pids):
    """ปิด process ตาม PID ด้วย kill (macOS/Linux)"""
    for pid in pids:
        try:
            subprocess.run(["kill", "-9", str(pid)], capture_output=True, timeout=10)
            print(f"ปิด process PID {pid} แล้ว")
        except Exception as e:
            print(f"ปิด PID {pid} ไม่สำเร็จ: {e}", file=sys.stderr)


def main():
    parser = argparse.ArgumentParser(description="ปิด Chrome ที่ใช้ port สำหรับ LINE OA script")
    parser.add_argument("--port", type=int, default=9222, help="พอร์ตที่ต้องการปิด (ค่าเริ่มต้น 9222)")
    parser.add_argument("--all", action="store_true", help="ปิดทุก port ที่ใช้กับ script: 9222,9223,9224,9225")
    args = parser.parse_args()

    if args.all:
        ports = [9222, 9223, 9224, 9225]
    else:
        ports = [args.port]

    if sys.platform == "win32":
        get_pids = get_pids_listening_on_port_windows
        kill_fn = kill_pids_windows
    elif sys.platform in ("darwin", "linux"):
        get_pids = get_pids_listening_on_port_unix
        kill_fn = kill_pids_unix
    else:
        print(f"ยังไม่รองรับระบบปฏิบัติการ: {sys.platform}", file=sys.stderr)
        sys.exit(1)

    all_pids = []
    for port in ports:
        pids = get_pids(port)
        for pid in pids:
            if pid not in all_pids:
                all_pids.append((port, pid))

    if not all_pids:
        if len(ports) == 1:
            print(f"ไม่พบ process ที่ listen บน port {ports[0]}")
        else:
            print(f"ไม่พบ process บน port {ports}")
        return

    for port, pid in all_pids:
        print(f"พบ process บน port {port}: PID {pid}")
    kill_fn([pid for _, pid in all_pids])
    print("ดำเนินการเสร็จแล้ว")


if __name__ == "__main__":
    main()
