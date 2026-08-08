"""
通用选择题组件 — 选完即出结果+解析，实时刷题模式
"""

import html as html_mod
import random
import streamlit as st


def quiz_section(questions: list[dict], quiz_key: str, num_questions: int = 10):
    """
    刷题模式选择题
    questions: [{"question": "...", "options": ["A","B","C","D"], "answer": 0, "explanation": "..."}]
    每选一题立即显示对错和解析
    """
    state_key = f"quiz_{quiz_key}"
    if state_key not in st.session_state:
        st.session_state[state_key] = {
            "started": False,
            "questions": [],
            "answers": {},
            "finished": False,
        }

    qs = st.session_state[state_key]

    # ========== 开始按钮 ==========
    if not qs["started"]:
        st.info(f"题库共 **{len(questions)}** 题，每次随机抽 **{num_questions}** 题")
        if st.button("🎯 开始刷题", key=f"start_{quiz_key}", type="primary", use_container_width=True):
            selected = random.sample(questions, min(num_questions, len(questions)))
            qs["questions"] = selected
            qs["answers"] = {}
            qs["finished"] = False
            qs["started"] = True
            st.rerun()
        return

    # ========== 实时得分统计 ==========
    answered = len(qs["answers"])
    total = len(qs["questions"])
    correct_count = sum(
        1 for i, ans in qs["answers"].items()
        if ans == qs["questions"][i]["answer"]
    )

    # 顶部得分条
    col_s1, col_s2, col_s3 = st.columns(3)
    col_s1.metric("📝 已答", f"{answered} / {total}")
    col_s2.metric("✅ 正确", f"{correct_count}")
    pct = correct_count / answered * 100 if answered > 0 else 0
    col_s3.metric("📊 正确率", f"{pct:.0f}%")
    st.progress(answered / total)
    st.divider()

    # ========== 逐题展示 ==========
    # 选项字体
    st.markdown("""
    <style>
    div[data-testid="stRadio"] label p { font-size: 14px !important; }
    div[data-testid="stRadio"] label { line-height: 1.5 !important; }
    </style>
    """, unsafe_allow_html=True)

    for i, q in enumerate(qs["questions"]):
        q_clean = q["question"].replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
        # 用 st.html 直接渲染，完全绕过 markdown 限制
        st.html(f'<p style="font-size:15px;font-weight:bold;color:#222;line-height:1.8;'
                f'white-space:normal;overflow-wrap:break-word;word-break:break-word;'
                f'max-width:100%;margin:6px 0;">{i+1}. {q_clean}</p>')

        # 选项标签
        labels = ["A", "B", "C", "D"]
        options_with_labels = [f"**{labels[j]}.** {opt}" for j, opt in enumerate(q["options"])]

        # 检查此题是否已答
        already_answered = i in qs["answers"]
        user_ans = qs["answers"].get(i)
        correct = q["answer"]

        if already_answered:
            # 已答：显示选项（disabled）+ 对错判断 + 解析
            choice_idx = user_ans
            choice_str = options_with_labels[choice_idx] if choice_idx is not None else "（未作答）"
            st.radio(
                f"q{i}",
                options_with_labels,
                index=choice_idx,
                key=f"{quiz_key}_done_{i}",
                disabled=True,
                horizontal=False,
                label_visibility="collapsed",
            )

            if user_ans == correct:
                st.success(f"✅ **正确！** 答案：{labels[correct]}. {q['options'][correct]}")
            else:
                st.error(f"❌ **你的答案：**{labels[user_ans]}. {q['options'][user_ans]}")
                st.info(f"💡 **正确答案：**{labels[correct]}. {q['options'][correct]}")

            # 始终显示解析
            explanation = q.get("explanation", "暂无解析")
            if explanation:
                st.markdown(f"""
                <div style="background:#f0f7fb; border-left:4px solid #2196F3;
                    padding:10px 16px; border-radius:8px; margin:4px 0 16px 0;
                    font-size:14px; color:#333;">
                📖 <b>解析：</b>{explanation}
                </div>
                """, unsafe_allow_html=True)

        else:
            # 未答：显示可选项
            choice = st.radio(
                f"q{i}",
                options_with_labels,
                index=None,
                key=f"{quiz_key}_q{i}",
                horizontal=False,
                label_visibility="collapsed",
            )
            if choice is not None:
                qs["answers"][i] = options_with_labels.index(choice)
                st.rerun()

        st.divider()

    # ========== 底部：全部完成 ==========
    if answered == total:
        qs["finished"] = True
        st.balloons()
        pct_final = correct_count / total * 100
        if pct_final >= 90:
            st.success(f"🎉 **太棒了！全对 {correct_count}/{total}，正确率 {pct_final:.0f}%**")
        elif pct_final >= 70:
            st.info(f"👍 **不错！{correct_count}/{total}，正确率 {pct_final:.0f}%，继续加油！**")
        elif pct_final >= 60:
            st.warning(f"📖 **还需努力！{correct_count}/{total}，正确率 {pct_final:.0f}%**")
        else:
            st.error(f"💪 **要多练习！{correct_count}/{total}，正确率 {pct_final:.0f}%**")

        col1, col2 = st.columns(2)
        with col1:
            if st.button("🔄 重新抽题", key=f"retry_{quiz_key}", use_container_width=True, type="primary"):
                qs["started"] = False
                st.rerun()
        with col2:
            if st.button("📋 错题回顾", key=f"review_{quiz_key}", use_container_width=True):
                # 只展示错题
                with st.expander("📝 错题详情", expanded=True):
                    for i in range(total):
                        if i not in qs["answers"] or qs["answers"][i] != qs["questions"][i]["answer"]:
                            q = qs["questions"][i]
                            st.markdown(f"**{i+1}. {q['question']}**")
                            st.caption(f"你的答案：{q['options'][qs['answers'].get(i, 0)]}")
                            st.success(f"正确答案：{q['options'][q['answer']]}")
                            st.info(q.get("explanation", ""))
                            st.divider()
