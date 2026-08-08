"""
考公工作台 — 完整版
左侧导航 × 11模块 × 番茄钟 × 刷题 × 公式 × 打卡 × 统计
"""

import json
import random
import calendar as cal_mod
from datetime import date, datetime, timedelta
from pathlib import Path

import streamlit as st
import streamlit.components.v1 as components
import pandas as pd
import plotly.express as px

import db

# ==================== 页面配置 ====================
st.set_page_config(page_title="考公工作台", page_icon="📖", layout="wide")
db.init_db()

DATA_DIR = Path(__file__).parent / "data"
UPLOAD_DIR = Path(__file__).parent / "uploads"
UPLOAD_DIR.mkdir(exist_ok=True)


@st.cache_data
def load_json(name):
    path = DATA_DIR / name
    return json.loads(path.read_text(encoding="utf-8")) if path.exists() else []


idioms_data   = load_json("idioms.json")
luoji_data    = load_json("luoji_quiz.json")
changshi_data = load_json("changshi_quiz.json")
zhengzhi_data = load_json("zhengzhi_quiz.json")
quotes_data   = load_json("quotes.json")
motivational  = load_json("motivational.json")

# ==================== 路由 ====================
PAGES = [
    ("🎯", "倒计时",     "countdown"),
    ("📖", "言语理解",   "yuyan"),
    ("📊", "资料分析",   "ziliao"),
    ("🧠", "逻辑判断",   "luoji"),
    ("🏛", "政治理论",   "zhengzhi"),
    ("🔢", "数量关系",   "shuliang"),
    ("💡", "常识判断",   "changshi"),
    ("📅", "打卡日历",   "calendar"),
    ("📝", "错题本",     "cuotiben"),
    ("📈", "学习统计",   "stats"),
]
if "page" not in st.session_state:
    st.session_state.page = "countdown"

today = date.today()

# ==================== 全局美化CSS ====================
st.markdown("""
<style>
/* 全局 */
.stApp { background: #f0f2f6; }
.stDivider { border-color: #e0e0e0; }

/* 侧边栏 - 深色渐变 */
[data-testid="stSidebar"] {
    background: linear-gradient(180deg, #0f0c29 0%, #302b63 50%, #24243e 100%) !important;
}
[data-testid="stSidebar"] * { color: #e0e0e0 !important; }
[data-testid="stSidebar"] button {
    background: transparent !important; border: none !important;
    text-align: left !important; padding: 10px 14px !important;
    width: 100% !important; border-radius: 8px !important;
    font-size: 14px !important; margin: 2px 0 !important;
    transition: all 0.2s !important;
}
[data-testid="stSidebar"] button:hover {
    background: rgba(255,255,255,0.08) !important;
    transform: translateX(4px);
}
[data-testid="stSidebar"] hr { border-color: rgba(255,255,255,0.1) !important; }

/* 卡片容器 */
.card {
    background: #fff; border-radius: 12px; padding: 20px;
    box-shadow: 0 1px 4px rgba(0,0,0,0.06); margin-bottom: 12px;
}

/* 指标卡 */
.metric-card {
    background: #fff; border-radius: 12px; padding: 16px; text-align: center;
    box-shadow: 0 1px 4px rgba(0,0,0,0.06);
    border-top: 3px solid #667eea;
}

/* 隐藏 */
#MainMenu, footer, header[data-testid="stHeader"] { visibility: hidden; }
</style>
""", unsafe_allow_html=True)

# ==================== 侧边栏导航 ====================
st.sidebar.markdown("""
<div style="text-align:center; padding:18px 0 10px 0;">
    <div style="font-size:36px;">📖</div>
    <div style="font-size:18px; font-weight:bold; margin-top:4px;">考公工作台</div>
    <div style="font-size:11px; color:#888; margin-top:2px;">Study Workstation</div>
</div>
""", unsafe_allow_html=True)
st.sidebar.divider()

for emoji, label, key in PAGES:
    if st.sidebar.button(f"{emoji}  {label}", key=f"nav_{key}", use_container_width=True):
        st.session_state.page = key
        st.rerun()

st.sidebar.divider()
st.sidebar.caption(f"📅 {today.strftime('%Y年%m月%d日')}")

# ==================== 顶栏 ====================
motiv_text = motivational[today.day % len(motivational)] if motivational else "加油！"

components.html(f"""
<div style="display:flex;align-items:center;justify-content:space-between;
    background:linear-gradient(135deg,#667eea 0%,#764ba2 100%);color:white;
    padding:12px 24px;border-radius:14px;margin-bottom:14px;flex-wrap:wrap;gap:10px;">
    <div style="font-size:28px;font-weight:bold;font-family:'Courier New',monospace;"
        id="live-clock">--:--:--</div>
    <div style="font-size:14px;opacity:0.95;font-style:italic;text-align:center;
        max-width:480px;">💬 {motiv_text}</div>
    <div style="font-size:13px;opacity:0.8;">📅 {today.strftime('%Y年%m月%d日')}</div>
</div>
<script>
(function u(){{var n=new Date();var e=document.getElementById('live-clock');
e.textContent=n.toLocaleTimeString('zh-CN',{{hour12:false}});
setTimeout(u,1000);}})();
</script>
""", height=68)

# ==================== 打卡条 ====================
col_ck, col_cb = st.columns([3, 1])
with col_ck:
    ex = db.get_checkin(today)
    if ex:
        st.success(f"✅ 今日已打卡  |  开始 {ex['start_time']}  →  结束 {ex['end_time']}")
    else:
        st.info("📌 今天还没有打卡哦，学完记得点一下～")
with col_cb:
    if not ex:
        if st.button("✅ 打卡签到", type="primary", use_container_width=True):
            now_str = datetime.now().strftime("%H:%M")
            db.do_checkin(today, now_str, now_str)
            st.rerun()

st.divider()

# ========================================================================
#                 番茄钟组件 (纯 HTML/JS)
# ========================================================================
def pomodoro_section(subject: str, default_minutes: int = 25):
    """内嵌 JS 番茄钟 — 环形圆盘进度"""
    total_sec = default_minutes * 60
    circ = round(2 * 3.14159 * 85, 1)
    today_min = db.get_today_pomodoro_minutes(subject)
    html = f"""<!DOCTYPE html><html><head><meta charset="utf-8"><style>
body{{margin:0;padding:0;display:flex;justify-content:center;font-family:'Microsoft YaHei',sans-serif;background:transparent;}}
.pc{{text-align:center;padding:8px;}}
.rc{{position:relative;width:200px;height:200px;margin:0 auto;}}
svg{{transform:rotate(-90deg);}}
.td{{position:absolute;top:50%;left:50%;transform:translate(-50%,-50%);font-size:36px;font-weight:bold;color:#333;}}
.st{{margin-top:-24px;font-size:14px;color:#888;min-height:20px;}}
.br{{display:flex;gap:8px;justify-content:center;margin-top:6px;}}
.bb{{padding:8px 18px;border:none;border-radius:20px;font-size:14px;cursor:pointer;font-weight:bold;color:white;}}
.bb:disabled{{opacity:0.4;cursor:not-allowed;}}
.bs{{background:#4CAF50;}}.bp{{background:#FF9800;}}.brr{{background:#9e9e9e;}}
.si{{margin-top:6px;font-size:13px;color:#666;}}
</style></head><body><div class="pc"><div class="rc">
<svg width="200" height="200" viewBox="0 0 200 200">
<circle cx="100" cy="100" r="85" fill="none" stroke="#e8e8e8" stroke-width="14"/>
<circle id="rg" cx="100" cy="100" r="85" fill="none" stroke="#4CAF50" stroke-width="14"
stroke-linecap="round" stroke-dasharray="{circ}" stroke-dashoffset="0"/></svg>
<div class="td" id="dp">{default_minutes}:00</div></div>
<div class="st" id="stt">准备开始</div>
<div class="br">
<button class="bb bs" id="bss" onclick="st()">开始</button>
<button class="bb bp" id="bpp" onclick="pa()" disabled>暂停</button>
<button class="bb brr" id="brr" onclick="re()">重置</button></div>
<div class="si">🍅 本次完成：<b id="cnt">0</b> 个</div>
<div class="si" style="font-size:12px;color:#aaa;">今日已专注：<b>{today_min}</b> 分钟</div></div>
<script>
var T={total_sec},C={circ},r=T,tid=null,ses=0;
var rg=document.getElementById('rg'),dp=document.getElementById('dp'),
stt=document.getElementById('stt'),bss=document.getElementById('bss'),
bpp=document.getElementById('bpp'),cnt=document.getElementById('cnt');
function up(){{var o=C*(1-r/T);rg.setAttribute('stroke-dashoffset',o);
var m=Math.floor(r/60),s=r%60;
dp.textContent=String(m).padStart(2,'0')+':'+String(s).padStart(2,'0');}}
function tk(){{if(r>0){{r--;up();if(r===0)fn();}}}}
function st(){{if(tid)return;if(r===0){{r=T;up();}}
tid=setInterval(tk,1000);stt.textContent='🔔 专注中...';rg.style.stroke='#4CAF50';
bss.disabled=true;bpp.disabled=false;}}
function pa(){{clearInterval(tid);tid=null;stt.textContent='⏸ 已暂停';
rg.style.stroke='#2196F3';bss.disabled=false;bpp.disabled=true;}}
function re(){{clearInterval(tid);tid=null;r=T;rg.style.stroke='#4CAF50';
stt.textContent='准备开始';bss.disabled=false;bpp.disabled=true;up();}}
function fn(){{clearInterval(tid);tid=null;rg.style.stroke='#FF9800';
stt.textContent='✅ 完成!';ses++;cnt.textContent=ses;bss.disabled=false;bpp.disabled=true;}}
up();
</script></body></html>"""
    components.html(html, height=330)
    total = db.get_today_pomodoro_minutes()
    if total > 0:
        st.caption(f"🔥 今日全科目专注总时长：**{total}** 分钟")


# ========================================================================
#                 待办事项组件
# ========================================================================
def todo_section(subject: str):
    st.markdown("### 📝 待办事项")
    with st.form(key=f"tdf_{subject}"):
        c1, c2 = st.columns([4, 1])
        with c1:
            ct = st.text_input("添加新任务", placeholder="输入待办内容...", label_visibility="collapsed")
        with c2:
            sub = st.form_submit_button("➕ 添加", use_container_width=True)
        if sub and ct.strip():
            db.add_todo(today, subject, ct.strip())
            st.rerun()
    todos = db.get_todos(today, subject)
    if not todos:
        st.caption("暂无待办")
    else:
        for t in todos:
            c1, c2 = st.columns([0.08, 0.92])
            with c1:
                st.checkbox("", value=bool(t["completed"]), key=f"td_{t['id']}",
                            on_change=lambda tid=t["id"]: db.toggle_todo(tid))
            with c2:
                txt = f"~~{t['content']}~~" if t["completed"] else t["content"]
                st.markdown(txt)
        done = sum(1 for t in todos if t["completed"])
        tot = len(todos)
        if tot > 0:
            st.progress(done / tot, text=f"完成 {done}/{tot}")


# ========================================================================
#                 每日进度组件
# ========================================================================
def progress_section(subject: str):
    st.markdown("### 📊 今日进度")
    pd_data = db.get_progress(today, subject)
    cur = pd_data[0] if pd_data else None
    planned = cur["planned_minutes"] if cur else 0
    completed = db.get_today_pomodoro_minutes(subject)
    db.upsert_progress(today, subject, planned, completed)
    c1, c2 = st.columns([3, 1])
    with c1:
        np = st.number_input("今日计划（分钟）", 0, 1440, planned, 30, key=f"pln_{subject}")
    with c2:
        if st.button("💾 保存", key=f"svp_{subject}"):
            db.upsert_progress(today, subject, np, completed)
            st.rerun()
    pct = min(completed / np * 100, 100) if np > 0 else 0
    st.progress(pct / 100, text=f"⏱ {completed} / {np} 分钟 ({pct:.0f}%)")
    if pct >= 100:
        st.success("🎉 今日计划已完成！")
    elif pct >= 50:
        st.info("👍 进度过半！")
    elif completed > 0:
        st.warning("📖 加把劲！")


# ========================================================================
#                 公式板块
# ========================================================================
def formula_section(subject: str):
    st.markdown("### 📐 公式速查")
    formulas = db.get_formulas(subject)
    with st.expander("➕ 新增公式"):
        with st.form(key=f"faf_{subject}"):
            fn = st.text_input("公式名称")
            fc = st.text_area("公式内容", height=80)
            if st.form_submit_button("保存") and fn.strip():
                db.add_formula(subject, fn.strip(), fc.strip())
                st.rerun()
    if not formulas:
        st.info("暂无公式，去添加吧！")
        return
    for f in formulas:
        with st.expander(f"📌 {f['name']}"):
            st.markdown(f"**{f['content']}**")
            c1, c2 = st.columns(2)
            with c1:
                nn = st.text_input("名称", value=f["name"], key=f"efn_{f['id']}")
                nc = st.text_area("内容", value=f["content"], key=f"efc_{f['id']}", height=80)
                if st.button("💾 保存", key=f"efs_{f['id']}"):
                    db.update_formula(f["id"], nn, nc); st.rerun()
            with c2:
                if st.button("🗑 删除", key=f"efd_{f['id']}"):
                    db.delete_formula(f["id"]); st.rerun()


# ========================================================================
#                 刷题组件 (纯HTML, 选项随机化, 答案配对)
# ========================================================================
def render_quiz(questions: list, quiz_id: str, answer_verified: bool = True):
    """纯 HTML/JS 选择题 — 选项随机排列，答案正确配对"""
    if not questions:
        st.info("暂无题目")
        return

    key_st = f"qz_st_{quiz_id}"
    key_qs = f"qz_qs_{quiz_id}"

    if key_st not in st.session_state:
        st.session_state[key_st] = False

    if not st.session_state[key_st]:
        st.info(f"题库共 **{len(questions)}** 题，每次随机抽 **10** 题" +
                ("" if answer_verified else "  ⚠️ 答案仅供参考"))
        if st.button("🎯 开始刷题", key=f"st_{quiz_id}", type="primary", use_container_width=True):
            # 随机抽题，并打乱每题的选项顺序
            selected = random.sample(questions, min(10, len(questions)))
            randomized = []
            for q in selected:
                # 选项随机排列，追踪正确答案新位置
                opts_with_idx = list(enumerate(q["options"]))
                random.shuffle(opts_with_idx)
                new_opts = [o[1] for o in opts_with_idx]
                new_ans = next(i for i, (orig_idx, _) in enumerate(opts_with_idx) if orig_idx == q["answer"])
                randomized.append({
                    "question": q["question"],
                    "options": new_opts,
                    "answer": new_ans,
                    "explanation": q.get("explanation", ""),
                })
            st.session_state[key_qs] = randomized
            st.session_state[key_st] = True
            st.rerun()
        return

    qs = st.session_state[key_qs]
    if not qs:
        st.session_state[key_st] = False
        st.rerun()
        return

    labels = ["A", "B", "C", "D"]

    # 构建完整 HTML
    quiz_html = """<!DOCTYPE html><html><head><meta charset="utf-8">
<style>
*{box-sizing:border-box;margin:0;padding:0;}
body{font-family:'Microsoft YaHei',sans-serif;padding:16px;background:#f0f2f6;}
.qb{background:#fff;border-radius:12px;padding:16px 18px;margin-bottom:12px;
    box-shadow:0 1px 3px rgba(0,0,0,0.06);border-left:4px solid #667eea;}
.qt{font-size:15px;font-weight:bold;color:#222;line-height:1.8;margin-bottom:8px;}
.opt{display:block;padding:8px 12px;margin:3px 0;border-radius:8px;cursor:pointer;
    font-size:14px;line-height:1.6;border:2px solid #e8e8e8;transition:all 0.15s;
    background:#fafafa;}
.opt:hover{background:#eef1ff;border-color:#667eea;}
.opt.sel{background:#e8f0fe;border-color:#667eea;font-weight:bold;}
.opt.ok{background:#d4edda;border-color:#28a745;color:#155724;}
.opt.ng{background:#f8d7da;border-color:#dc3545;color:#721c24;}
.fb{margin-top:6px;padding:8px 12px;border-radius:8px;font-size:14px;line-height:1.6;
    display:none;}
.fb.sh{display:block;}
.fb.gd{background:#d4edda;border-left:4px solid #28a745;}
.fb.bd{background:#f8d7da;border-left:4px solid #dc3545;}
.exp{background:#f0f7fb;border-left:4px solid #2196F3;padding:8px 12px;
    border-radius:6px;margin-top:6px;font-size:13px;line-height:1.6;display:none;}
.exp.sh{display:block;}
.sb{background:#fff;border-radius:12px;padding:14px 18px;margin-bottom:14px;
    box-shadow:0 1px 3px rgba(0,0,0,0.06);text-align:center;}
.sb span{margin:0 14px;font-size:15px;}
.sb b{color:#667eea;}
.btns{text-align:center;margin-top:14px;}
.btns button{padding:10px 28px;border:none;border-radius:22px;font-size:15px;
    font-weight:bold;cursor:pointer;background:#667eea;color:white;}
.btns button:hover{opacity:0.85;}
.warn{background:#fff3cd;padding:8px 14px;border-radius:8px;text-align:center;
    font-size:13px;color:#856404;margin-bottom:12px;}
</style></head><body>"""

    if not answer_verified:
        quiz_html += '<div class="warn">⚠️ 此题库答案尚未确认，仅供参考学习</div>'

    quiz_html += '<div class="sb">'
    quiz_html += '<span>📝 已答：<b id="ac">0</b> / TOT</span>'
    quiz_html += '<span>✅ 正确：<b id="cc">0</b></span>'
    quiz_html += '<span>📊 正确率：<b id="pct">0%</b></span>'
    quiz_html += '</div>'

    for i, q in enumerate(qs):
        q_esc = (q["question"].replace("&", "&amp;").replace("<", "&lt;")
                 .replace(">", "&gt;").replace('"', "&quot;"))
        ci = q["answer"]
        exp = (q.get("explanation", "").replace("&", "&amp;").replace("<", "&lt;")
               .replace(">", "&gt;").replace('"', "&quot;"))

        quiz_html += f'<div class="qb" id="qb-{i}">'
        quiz_html += f'<div class="qt">{i+1}. {q_esc}</div>'
        for j, opt in enumerate(q["options"]):
            oe = (opt.replace("&", "&amp;").replace("<", "&lt;")
                  .replace(">", "&gt;").replace('"', "&quot;"))
            cls = "ok" if j == ci else "ng"
            quiz_html += (f'<div class="opt" id="op-{i}-{j}" '
                          f'onclick="pick({i},{j},{ci})">{labels[j]}. {oe}</div>')
        quiz_html += f'<div class="fb" id="fb-{i}"><span id="fbt-{i}"></span></div>'
        quiz_html += f'<div class="exp" id="ex-{i}">📖 解析：{exp}</div>'
        quiz_html += '</div>'

    quiz_html += f"""
<div class="btns"><button onclick="window.location.reload()">🔄 重新抽题</button></div>
<script>
var TOT={len(qs)},ans=new Set(),cor=0;
function pick(qi,oi,ci){{
if(ans.has(qi))return;ans.add(qi);
var ops=document.querySelectorAll('#qb-'+qi+' .opt');
ops.forEach(function(o){{o.style.pointerEvents='none';}});
var se=document.getElementById('op-'+qi+'-'+oi);
var ce=document.getElementById('op-'+qi+'-'+ci);
if(oi===ci){{se.classList.add('ok');cor++;}}else{{se.classList.add('ng');ce.classList.add('ok');}}
var fb=document.getElementById('fb-'+qi);
var ft=document.getElementById('fbt-'+qi);
fb.classList.add('sh');
if(oi===ci){{fb.classList.add('gd');ft.textContent='✅ 回答正确！';}}
else{{fb.classList.add('bd');ft.textContent='❌ 回答错误！正确答案：'+String.fromCharCode(65+ci);}}
document.getElementById('ex-'+qi).classList.add('sh');
document.getElementById('ac').textContent=ans.size;
document.getElementById('cc').textContent=cor;
document.getElementById('pct').textContent=Math.round(cor/ans.size*100)+'%';
if(ans.size===TOT){{
var pf=Math.round(cor/TOT*100),msg='';
if(pf>=90)msg='🎉 太棒了！';
else if(pf>=70)msg='👍 不错！继续加油！';
else if(pf>=60)msg='📖 还需努力！';
else msg='💪 要多练习哦！';
document.querySelector('.sb').innerHTML+='<br><b style=font-size:20px;>'+msg+' '+cor+'/'+TOT+'</b>';
}}}}
</script></body></html>"""

    quiz_html = quiz_html.replace("TOT", str(len(qs)))
    components.html(quiz_html, height=650, scrolling=True)

    if st.button("🔄 重新抽题", key=f"ret_{quiz_id}", use_container_width=True):
        st.session_state[key_st] = False
        st.rerun()


# ========================================================================
#                 通用学习模块模板
# ========================================================================
def study_module(subject: str, extra_tabs: list | None = None):
    """番茄钟 + 待办 + 进度 + 可选扩展"""
    tabs = ["🍅 番茄钟", "📝 待办事项", "📊 学习进度"]
    if extra_tabs:
        tabs += [t[0] for t in extra_tabs]
    to = st.tabs(tabs)
    with to[0]:
        pomodoro_section(subject)
    with to[1]:
        todo_section(subject)
    with to[2]:
        progress_section(subject)
    if extra_tabs:
        for idx, (_, cb) in enumerate(extra_tabs):
            with to[3 + idx]:
                cb()


# ========================================================================
#                         页面路由
# ========================================================================
page = st.session_state.page

# ----- 1. 倒计时 -----
if page == "countdown":
    st.title("🎯 考试倒计时")
    exams = [
        ("国考", date(2026, 11, 29), "🏛"),
        ("省考联考", date(2027, 3, 27), "🏢"),
        ("事业编联考", date(2027, 5, 15), "📋"),
    ]
    with st.expander("➕ 添加自定义考试"):
        cn = st.text_input("考试名称", key="cname")
        cd = st.date_input("考试日期", key="cdate", min_value=today)
        if st.button("添加") and cn:
            exams.append((cn, cd, "📌"))
    cols = st.columns(len(exams))
    for i, (name, ed, icon) in enumerate(exams):
        delta = (ed - today).days
        color = "#e74c3c" if delta <= 30 else ("#f39c12" if delta <= 100 else "#2ecc71")
        with cols[i]:
            st.markdown(f"""<div style="text-align:center;background:white;border-radius:12px;
                padding:22px;box-shadow:0 2px 8px rgba(0,0,0,0.08);">
                <div style="font-size:40px;">{icon}</div>
                <div style="font-size:16px;font-weight:bold;margin:8px 0;">{name}</div>
                <div style="font-size:44px;font-weight:bold;color:{color};">{delta}</div>
                <div style="font-size:13px;color:#999;">天</div>
                <div style="font-size:12px;color:#bbb;">{ed.strftime('%Y-%m-%d')}</div>
            </div>""", unsafe_allow_html=True)

# ----- 2. 言语理解 -----
elif page == "yuyan":
    st.title("📖 言语理解")
    study_module("言语理解", [
        ("📝 成语辨析", lambda: render_quiz(idioms_data, "yuyan_qz", answer_verified=True)),
    ])

# ----- 3. 资料分析 -----
elif page == "ziliao":
    st.title("📊 资料分析")
    study_module("资料分析", [
        ("📐 公式速查", lambda: formula_section("资料分析")),
    ])

# ----- 4. 逻辑判断 -----
elif page == "luoji":
    st.title("🧠 逻辑判断")
    study_module("逻辑判断", [
        ("📝 刷题练习", lambda: render_quiz(luoji_data, "luoji_qz", answer_verified=True)),
    ])

# ----- 5. 政治理论 -----
elif page == "zhengzhi":
    st.title("🏛 政治理论")
    study_module("政治理论", [
        ("📰 时政预测", lambda: render_quiz(zhengzhi_data, "zhengzhi_qz", answer_verified=True)),
    ])

# ----- 6. 数量关系 -----
elif page == "shuliang":
    st.title("🔢 数量关系")
    study_module("数量关系", [
        ("📐 公式速查", lambda: formula_section("数量关系")),
    ])

# ----- 7. 常识判断 -----
elif page == "changshi":
    st.title("💡 常识判断")
    study_module("常识判断", [
        ("📚 常识预测", lambda: render_quiz(changshi_data, "changshi_qz", answer_verified=False)),
    ])

# ----- 8. 打卡日历 -----
if page == "calendar":
    st.title("📅 打卡日历")

    ex = db.get_checkin(today)

    # 打卡区域
    col_a, col_b, col_c, col_d = st.columns([2, 2, 1.5, 2])
    with col_a:
        st_t = st.text_input("⏰ 开始学习", value=ex["start_time"] if ex else "08:00", key="st")
    with col_b:
        ed_t = st.text_input("🌙 结束学习", value=ex["end_time"] if ex else "22:00", key="et")
    with col_c:
        st.write("")
        if not ex:
            if st.button("✅ 打卡", type="primary", use_container_width=True):
                db.do_checkin(today, st_t, ed_t)
                st.toast("🎉 打卡成功！", icon="✅")
                st.rerun()
        else:
            st.success("已打卡 ✅")
    with col_d:
        if ex:
            st.metric("今日学习", f"{ex['start_time']}~{ex['end_time']}")
        else:
            st.info("今天还没打卡哦")

    st.divider()

    # ---- 用 components.html 渲染完整日历 HTML ----
    y, m = today.year, today.month
    month_name = f"{y}年{m}月"
    md = cal_mod.monthrange(y, m)[1]
    start_weekday = cal_mod.monthrange(y, m)[0]  # 0=Mon
    start_sun = (start_weekday + 1) % 7  # Sun=0

    cks = db.get_all_checkins(date(y, m, 1), date(y, m, md))
    cd_map = {}
    for c in cks:
        cd_map[c["date"]] = c  # date -> {start_time, end_time}

    # 构建日历格子HTML
    cells_html = ""
    # 空白填充
    for _ in range(start_sun):
        cells_html += '<div class="cell empty"></div>'

    for d in range(1, md + 1):
        ds = f"{y}-{m:02d}-{d:02d}"
        is_today = (date(y, m, d) == today)
        is_checked = (ds in cd_map)

        if is_checked:
            info = cd_map[ds]
            cls = "cell checked"
            inner = f'<span class="day">{d}</span><span class="time">{info["start_time"]}</span>'
        elif is_today:
            cls = "cell today"
            inner = f'<span class="day">{d}</span><span class="label">今天</span>'
        else:
            cls = "cell normal"
            inner = f'<span class="day">{d}</span>'

        cells_html += f'<div class="{cls}">{inner}</div>'

    cal_html = f"""<!DOCTYPE html><html><head><meta charset="utf-8">
<style>
* {{ box-sizing:border-box; margin:0; padding:0; }}
body {{ font-family:'Microsoft YaHei',sans-serif; background:transparent; padding:0; }}
.cal-container {{ max-width:700px; margin:0 auto; }}
.month-title {{ text-align:center; font-size:22px; font-weight:bold; color:#333; padding:10px 0 16px 0; }}
.weekdays {{ display:grid; grid-template-columns:repeat(7,1fr); gap:6px; text-align:center; margin-bottom:6px; }}
.weekdays div {{ font-weight:bold; font-size:13px; color:#666; padding:4px; }}
.weekdays div:first-child, .weekdays div:last-child {{ color:#e74c3c; }}
.grid {{ display:grid; grid-template-columns:repeat(7,1fr); gap:6px; }}
.cell {{ border-radius:10px; padding:10px 4px; text-align:center; min-height:52px;
    display:flex; flex-direction:column; justify-content:center; align-items:center;
    transition:all 0.2s; cursor:default; }}
.cell .day {{ font-size:16px; font-weight:600; }}
.cell .time {{ font-size:10px; color:#fff; margin-top:2px; opacity:0.9; }}
.cell .label {{ font-size:10px; color:#667eea; margin-top:2px; font-weight:bold; }}
.cell.empty {{ background:transparent; }}
.cell.normal {{ background:#f5f6f8; color:#555; }}
.cell.normal:hover {{ background:#e8ecf1; }}
.cell.today {{ background:#667eea; color:white; box-shadow:0 2px 8px rgba(102,126,234,0.4); }}
.cell.today .day {{ font-size:18px; }}
.cell.checked {{ background:#4CAF50; color:white; box-shadow:0 2px 6px rgba(76,175,80,0.3); }}
.cell.checked .day {{ font-size:18px; }}
.legend {{ display:flex; gap:20px; justify-content:center; margin-top:16px; font-size:13px; color:#666; }}
.legend-item {{ display:flex; align-items:center; gap:6px; }}
.legend-dot {{ width:12px; height:12px; border-radius:4px; }}
</style></head><body>
<div class="cal-container">
<div class="month-title">📆 {month_name}</div>
<div class="weekdays">
    <div>日</div><div>一</div><div>二</div><div>三</div><div>四</div><div>五</div><div>六</div>
</div>
<div class="grid">{cells_html}</div>
<div class="legend">
    <div class="legend-item"><div class="legend-dot" style="background:#667eea;"></div>今天</div>
    <div class="legend-item"><div class="legend-dot" style="background:#4CAF50;"></div>已打卡</div>
    <div class="legend-item"><div class="legend-dot" style="background:#f5f6f8;"></div>未打卡</div>
</div>
</div>
</body></html>"""

    components.html(cal_html, height=380)

# ----- 10. 错题本 -----
if page == "cuotiben":
    st.title("📝 错题本")
    SUBJECTS = ["全部", "言语理解", "资料分析", "逻辑判断", "政治理论", "数量关系", "常识判断", "申论", "其他"]
    fs = st.selectbox("筛选科目", SUBJECTS, key="ef")
    af = None if fs == "全部" else fs
    errors = db.get_errors(af)
    with st.expander("➕ 记录新错题"):
        with st.form("efm"):
            es = st.selectbox("科目", SUBJECTS[1:], key="es")
            eq = st.text_area("题目", height=100, key="eq")
            ea = st.text_input("答案", key="ea")
            exx = st.text_area("解析", height=80, key="exx")
            eim = st.file_uploader("上传图片", type=["png","jpg","jpeg"], key="eim")
            if st.form_submit_button("💾 保存"):
                imp = ""
                if eim:
                    imp = str(UPLOAD_DIR / eim.name)
                    with open(imp, "wb") as f:
                        f.write(eim.getbuffer())
                db.add_error(es, eq, ea, exx, imp)
                st.rerun()
    if not errors:
        st.info("暂无错题，做题时遇到错题记得记录哦～")
    else:
        st.caption(f"共 **{len(errors)}** 道错题")
        for err in errors:
            with st.expander(f"📌 [{err['subject']}] {err['question'][:50]}..."):
                st.markdown(f"**题目：** {err['question']}")
                st.markdown(f"**答案：** {err['answer']}")
                st.markdown(f"**解析：** {err['analysis']}")
                if err.get("image_path"):
                    st.image(err["image_path"], width=300)
                if st.button("🗑 删除", key=f"de_{err['id']}"):
                    db.delete_error(err["id"]); st.rerun()

# ----- 11. 学习统计 -----
if page == "stats":
    st.title("📈 学习统计")

    tr = db.get_pomodoro_records(today, today)
    t_min = sum(r["duration"] for r in tr) // 60
    t_pm = len(tr)

    ws = today - timedelta(days=today.weekday())
    w_min = sum(r["duration"] for r in db.get_pomodoro_records(ws, today)) // 60

    ms = date(today.year, today.month, 1)
    m_min = sum(r["duration"] for r in db.get_pomodoro_records(ms, today)) // 60

    c1, c2, c3, c4 = st.columns(4)
    c1.markdown(f"""<div class="metric-card" style="border-top-color:#e74c3c;">
        <div style="font-size:28px;">🍅</div>
        <div style="font-size:28px;font-weight:bold;">{t_pm}</div>
        <div style="font-size:13px;color:#999;">今日番茄数</div></div>""", unsafe_allow_html=True)
    c2.markdown(f"""<div class="metric-card" style="border-top-color:#667eea;">
        <div style="font-size:28px;">⏱</div>
        <div style="font-size:28px;font-weight:bold;">{t_min}</div>
        <div style="font-size:13px;color:#999;">今日专注(分钟)</div></div>""", unsafe_allow_html=True)
    c3.markdown(f"""<div class="metric-card" style="border-top-color:#f39c12;">
        <div style="font-size:28px;">📅</div>
        <div style="font-size:28px;font-weight:bold;">{w_min}</div>
        <div style="font-size:13px;color:#999;">本周累计(分钟)</div></div>""", unsafe_allow_html=True)
    c4.markdown(f"""<div class="metric-card" style="border-top-color:#2ecc71;">
        <div style="font-size:28px;">📆</div>
        <div style="font-size:28px;font-weight:bold;">{m_min}</div>
        <div style="font-size:13px;color:#999;">本月累计(分钟)</div></div>""", unsafe_allow_html=True)

    st.divider()
    st.subheader("📊 7日专注趋势")
    td_data = []
    for i in range(6, -1, -1):
        d = today - timedelta(days=i)
        mm = sum(r["duration"] for r in db.get_pomodoro_records(d, d)) // 60
        td_data.append({"日期": d.strftime("%m/%d"), "分钟": mm})
    fig = px.bar(pd.DataFrame(td_data), x="日期", y="分钟", color_discrete_sequence=["#667eea"])
    fig.update_layout(height=280, margin=dict(l=10, r=10, t=10, b=10))
    st.plotly_chart(fig, use_container_width=True)

    st.divider()
    all_c = db.get_all_checkins()
    cd_set = {date.fromisoformat(c["date"]) for c in all_c}
    streak = 0
    d = today
    while d in cd_set:
        streak += 1
        d -= timedelta(days=1)
    st.metric("🔥 连续打卡", f"{streak} 天")
