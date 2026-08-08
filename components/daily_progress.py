"""
每日学习进度组件 — 计划 vs 实际，百分比展示
"""

import streamlit as st
import db
from datetime import date


def progress_section(subject: str):
    """每日学习进度区域"""
    today = date.today()

    st.caption("### 📊 今日进度")

    # 获取今日进度数据
    progress_data = db.get_progress(today, subject)
    current = progress_data[0] if progress_data else None

    planned = current["planned_minutes"] if current else 0
    completed_minutes = db.get_today_pomodoro_minutes(subject)

    # 自动同步完成时长（番茄钟记录的总和）
    db.upsert_progress(today, subject, planned, completed_minutes)

    # 设置计划时长
    col1, col2 = st.columns([3, 1])
    with col1:
        new_plan = st.number_input(
            "今日计划（分钟）", min_value=0, max_value=1440,
            value=planned, step=30, key=f"plan_{subject}"
        )
    with col2:
        if st.button("💾 保存", key=f"save_plan_{subject}"):
            db.upsert_progress(today, subject, new_plan, completed_minutes)
            st.rerun()

    # 进度百分比
    pct = (completed_minutes / new_plan * 100) if new_plan > 0 else 0
    pct = min(pct, 100)

    st.progress(pct / 100, text=f"⏱ {completed_minutes} / {new_plan} 分钟 ({pct:.0f}%)")

    if pct >= 100:
        st.success("🎉 今日计划已完成！太棒了！")
    elif pct >= 50:
        st.info("👍 进度过半，继续加油！")
    elif completed_minutes > 0:
        st.warning("📖 还有进步空间，加把劲！")
