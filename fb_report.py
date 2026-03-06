# -*- coding: utf-8 -*-
"""
สร้างรายงานจากรายการแชท — 1 ฟังก์ชัน: build_report(all_threads, ...) -> str
"""
from collections import OrderedDict


def _group_by_source(threads):
    """จัดกลุ่ม threads ตาม _source คืน OrderedDict {source_key: [threads]}"""
    groups = OrderedDict()
    for t in threads:
        key = t.get("_source") or "link_1"
        groups.setdefault(key, []).append(t)
    return groups


def _format_thread(t):
    msg = (t.get("message") or "")[:80]
    if len(t.get("message") or "") > 80:
        msg += "..."
    return f"ชื่อ: **{t['sender']}** ข้อความ: **{msg}** เวลา: **{t['time']}**"


def _build_grouped(threads, title, empty_msg):
    """สร้างรายงานแบบจัดกลุ่มตามลิงก์"""
    if not threads:
        return empty_msg

    lines = [title]
    groups = _group_by_source(threads)
    total_links = len(groups)

    for idx, (source_key, items) in enumerate(groups.items(), start=1):
        lines.append(f"ลิงก์ที่ {idx}/{total_links}:")
        for t in items:
            lines.append(f"  {_format_thread(t)}")

    lines.append(f"--- รวม {len(threads)} รายการ ---")
    return "\n".join(lines)


def build_report(all_threads, report_format="summary-once", unread_only=True, within_today_only=False):
    """
    สร้างข้อความรายงานจาก all_threads (list of dict มี sender, message, time และอาจมี _source)
    report_format: "summary-once" = ยังไม่อ่าน, "read-not-replied-today" = อ่านแล้วแต่ยังไม่ตอบ
    """
    if report_format == "read-not-replied-today":
        period = " (วันนี้เท่านั้น)" if within_today_only else " (ทั้งสัปดาห์)"
        return _build_grouped(
            all_threads,
            title=f"📋 Facebook Inbox: อ่านแล้วแต่ยังไม่ตอบ{period}",
            empty_msg="ไม่พบรายการที่อ่านแล้วและยังไม่ตอบ",
        )

    today_suffix = " (วันนี้เท่านั้น)" if (unread_only and within_today_only) else ""
    title = f"📥 Facebook Inbox: ยังไม่อ่าน{today_suffix}" if unread_only else "📥 Facebook Inbox: รายการแชท"
    return _build_grouped(
        all_threads,
        title=title,
        empty_msg="ไม่พบข้อความที่ยังไม่อ่าน" if unread_only else "ไม่พบรายการแชท",
    )
