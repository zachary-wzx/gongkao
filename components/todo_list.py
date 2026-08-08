"""
待办事项组件
"""

import streamlit as st
import db
from datetime import date


def todo_section(subject: str):
    """待办事项区域"""
    today = date.today()

    st.caption("### 📝 待办事项")

    # 新增待办
    with st.form(key=f"todo_form_{subject}", clear_on_submit=True):
        col1, col2 = st.columns([4, 1])
        with col1:
            content = st.text_input("添加新任务", placeholder="输入待办内容...", label_visibility="collapsed")
        with col2:
            submitted = st.form_submit_button("➕ 添加", use_container_width=True)
        if submitted and content.strip():
            db.add_todo(today, subject, content.strip())
            st.rerun()

    # 显示待办列表
    todos = db.get_todos(today, subject)
    if not todos:
        st.caption("暂无待办事项")
    else:
        for todo in todos:
            col1, col2 = st.columns([0.1, 0.9])
            with col1:
                checked = st.checkbox("", value=bool(todo["completed"]),
                                      key=f"todo_{todo['id']}",
                                      on_change=lambda tid=todo["id"]: db.toggle_todo(tid))
            with col2:
                text = todo["content"]
                if todo["completed"]:
                    text = f"~~{text}~~"
                st.markdown(text)

    # 已完成数
    done = sum(1 for t in todos if t["completed"])
    total = len(todos)
    if total > 0:
        st.progress(done / total, text=f"完成 {done}/{total}")
