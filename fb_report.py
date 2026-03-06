# -*- coding: utf-8 -*-
"""
สร้างรายงานจากรายการแชท — 1 ฟังก์ชัน: build_report(all_threads, ...) -> str
"""


def build_report(all_threads, report_format="summary-once", unread_only=True, within_today_only=False):
    """
    สร้างข้อความรายงานจาก all_threads (list of dict มี sender, message, time และอาจมี _source)
    report_format: "summary-once" = ยังไม่อ่าน, "read-not-replied-today" = อ่านแล้วแต่ยังไม่ตอบ
    คืนข้อความรายงาน (string)
    """
    if report_format == "read-not-replied-today":
        lines = []
        if all_threads:
            lines.append("📋 Facebook Inbox: อ่านแล้วแต่ยังไม่ตอบ" + (" (วันนี้เท่านั้น)" if within_today_only else " (ทั้งสัปดาห์)"))
            for t in all_threads:
                msg = (t.get('message') or '')[:80]
                if len(t.get('message') or '') > 80:
                    msg += "..."
                prefix = f"[ลิงก์ {t['_source']}] " if t.get("_source") else ""
                lines.append(f"{prefix}ชื่อ: **{t['sender']}** ข้อความ: **{msg}** เวลา: **{t['time']}**")
            lines.append(f"--- รวม {len(all_threads)} รายการ ---")
        else:
            lines.append("ไม่พบรายการที่อ่านแล้วและยังไม่ตอบ")
        return "\n".join(lines)

    lines = []
    if all_threads:
        title = "📥 Facebook Inbox: ยังไม่อ่าน" + (" (วันนี้เท่านั้น)" if (unread_only and within_today_only) else "") if unread_only else "📥 Facebook Inbox: รายการแชท"
        lines.append(title)
        for t in all_threads:
            msg = (t.get('message') or '')[:80]
            if len(t.get('message') or '') > 80:
                msg += "..."
            prefix = f"[ลิงก์ {t['_source']}] " if t.get("_source") else ""
            lines.append(f"{prefix}ชื่อ: **{t['sender']}** ข้อความ: **{msg}** เวลา: **{t['time']}**")
        lines.append(f"--- รวม {len(all_threads)} รายการ ---")
    else:
        lines.append("ไม่พบรายการแชท" if not unread_only else "ไม่พบข้อความที่ยังไม่อ่าน")
    return "\n".join(lines)
