"""
番茄钟组件 — 内嵌 HTML/JS 实现实时倒计时，环形圆盘进度展示
"""

import streamlit as st
import streamlit.components.v1 as components
import db
from datetime import date


def _build_html(default_minutes: int, today_min: int) -> str:
    """构建番茄钟HTML，用 replace 注入参数，避免 format 与 JS 花括号冲突"""
    total_seconds = default_minutes * 60
    circumference = round(2 * 3.14159 * 85, 1)

    html = """<!DOCTYPE html>
<html><head><meta charset="utf-8">
<style>
    body { margin:0; padding:0; display:flex; justify-content:center;
        font-family: 'Microsoft YaHei', sans-serif; background: transparent; }
    .pc { text-align:center; padding:10px; }
    .rc { position:relative; width:200px; height:200px; margin:0 auto; }
    svg { transform:rotate(-90deg); }
    .td { position:absolute; top:50%; left:50%; transform:translate(-50%,-50%);
        font-size:36px; font-weight:bold; color:#333; }
    .st { margin-top:-26px; font-size:14px; color:#888; min-height:20px; }
    .br { display:flex; gap:8px; justify-content:center; margin-top:6px; }
    .btn { padding:8px 18px; border:none; border-radius:20px; font-size:14px;
        cursor:pointer; font-weight:bold; }
    .btn-start { background:#4CAF50; color:white; }
    .btn-pause { background:#FF9800; color:white; }
    .btn-reset { background:#e0e0e0; color:#333; }
    .btn:hover { opacity:0.85; }
    .btn:disabled { opacity:0.4; cursor:not-allowed; }
    .si { margin-top:6px; font-size:14px; color:#666; }
</style>
</head><body>
<div class="pc">
<div class="rc">
    <svg width="200" height="200" viewBox="0 0 200 200">
        <circle cx="100" cy="100" r="85" fill="none"
            stroke="#e8e8e8" stroke-width="14"/>
        <circle id="ring" cx="100" cy="100" r="85" fill="none"
            stroke="#4CAF50" stroke-width="14" stroke-linecap="round"
            stroke-dasharray="CIRC_PLACEHOLDER" stroke-dashoffset="0"/>
    </svg>
    <div class="td" id="display">MM_PLACEHOLDER:00</div>
</div>
<div class="st" id="status">准备开始</div>
<div class="br">
    <button class="btn btn-start" id="bs" onclick="start()">开始</button>
    <button class="btn btn-pause" id="bp" onclick="pause()" disabled>暂停</button>
    <button class="btn btn-reset" id="br" onclick="reset()">重置</button>
</div>
<div class="si">本次完成：<b id="count">0</b> 个</div>
<div class="si" style="font-size:12px;color:#aaa;">今日已专注：<b>TODAY_PLACEHOLDER</b> 分钟</div>
</div>
<script>
var TOTAL = TOTAL_PLACEHOLDER;
var CIRC = CIRC_PLACEHOLDER;
var remaining = TOTAL;
var timerId = null;
var sessions = 0;
var ring = document.getElementById('ring');
var display = document.getElementById('display');
var status = document.getElementById('status');
var bs = document.getElementById('bs');
var bp = document.getElementById('bp');
var countEl = document.getElementById('count');
function updateUI() {
    var offset = CIRC * (1 - remaining / TOTAL);
    ring.setAttribute('stroke-dashoffset', offset);
    var m = Math.floor(remaining / 60);
    var s = remaining % 60;
    display.textContent = String(m).padStart(2,'0') + ':' + String(s).padStart(2,'0');
}
function tick() {
    if (remaining > 0) {
        remaining--;
        updateUI();
        if (remaining === 0) { finish(); }
    }
}
function start() {
    if (timerId) return;
    if (remaining === 0) { remaining = TOTAL; updateUI(); }
    timerId = setInterval(tick, 1000);
    status.textContent = '专注中...';
    ring.style.stroke = '#4CAF50';
    bs.disabled = true; bp.disabled = false;
}
function pause() {
    clearInterval(timerId); timerId = null;
    status.textContent = '已暂停';
    ring.style.stroke = '#2196F3';
    bs.disabled = false; bp.disabled = true;
}
function reset() {
    clearInterval(timerId); timerId = null;
    remaining = TOTAL;
    ring.style.stroke = '#4CAF50';
    status.textContent = '准备开始';
    bs.disabled = false; bp.disabled = true;
    updateUI();
}
function finish() {
    clearInterval(timerId); timerId = null;
    ring.style.stroke = '#FF9800';
    status.textContent = '完成!';
    sessions++; countEl.textContent = sessions;
    bs.disabled = false; bp.disabled = true;
}
updateUI();
</script>
</body></html>"""

    return (html
        .replace("TOTAL_PLACEHOLDER", str(total_seconds))
        .replace("CIRC_PLACEHOLDER", str(circumference))
        .replace("MM_PLACEHOLDER", str(default_minutes))
        .replace("TODAY_PLACEHOLDER", str(today_min)))


def pomodoro_section(subject: str, default_minutes: int = 25):
    """番茄钟区域 — 圆盘进度 + 实时倒计时"""
    today_min = db.get_today_pomodoro_minutes(subject)
    html_str = _build_html(default_minutes, today_min)
    components.html(html_str, height=340)

    total_today = db.get_today_pomodoro_minutes()
    if total_today > 0:
        st.caption(f"🔥 今日全科目专注总时长：**{total_today}** 分钟")
    else:
        st.caption("👆 点击「开始」启动番茄钟")
