"""
工具函数 — 连续天数计算、CSV 导出等
"""

import csv
import io
from datetime import date, timedelta
from collections import defaultdict

import db


def calc_streak(dates: list[date]) -> int:
    """计算从今天往前的连续打卡天数"""
    if not dates:
        return 0
    dates_set = {d for d in dates}
    today = date.today()
    streak = 0
    d = today
    while d in dates_set:
        streak += 1
        d -= timedelta(days=1)
    return streak


def calc_monthly_stats() -> list[dict]:
    """按月汇总打卡次数和总时长"""
    rows = db.get_all_checkins()
    monthly: dict[str, dict] = defaultdict(lambda: {"days": 0, "hours": 0.0})
    for r in rows:
        month_key = r["date"][:7]  # "2026-08"
        monthly[month_key]["days"] += 1
        monthly[month_key]["hours"] += r["hours"]
    return [
        {"月份": m, "打卡天数": v["days"], "学习时长(h)": round(v["hours"], 1)}
        for m, v in sorted(monthly.items(), reverse=True)
    ]


def calc_subject_distribution() -> list[dict]:
    """按科目统计学习时长分布"""
    rows = db.get_all_checkins()
    dist: dict[str, float] = defaultdict(float)
    for r in rows:
        dist[r["subject"]] += r["hours"]
    return [{"subject": k, "hours": round(v, 1)} for k, v in dist.items()]


def export_csv_str() -> str:
    """将所有打卡记录导出为 CSV 字符串"""
    rows = db.get_all_checkins()
    output = io.StringIO()
    writer = csv.DictWriter(output, fieldnames=["id", "date", "hours", "subject", "note"])
    writer.writeheader()
    for r in rows:
        writer.writerow(r)
    return output.getvalue()


def get_year_checkins(year: int) -> list[dict]:
    """获取某一年全年的打卡记录（用于热力图）"""
    start = date(year, 1, 1)
    end = date(year, 12, 31)
    return db.get_all_checkins(start, end)
