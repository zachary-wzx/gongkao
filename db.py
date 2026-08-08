"""
数据库模块 — 7 张表：番茄钟、待办、每日进度、每日打卡、错题本、公式、每日金句
"""

import sqlite3
from datetime import date, datetime
from pathlib import Path

DB_PATH = Path(__file__).parent / "data.db"


def get_conn() -> sqlite3.Connection:
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    return conn


def init_db():
    """建所有表"""
    with get_conn() as conn:
        conn.executescript("""
            -- 番茄钟记录
            CREATE TABLE IF NOT EXISTS pomodoro_records (
                id        INTEGER PRIMARY KEY AUTOINCREMENT,
                date      DATE NOT NULL,
                subject   TEXT NOT NULL,
                duration  INTEGER NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );

            -- 待办事项
            CREATE TABLE IF NOT EXISTS todos (
                id         INTEGER PRIMARY KEY AUTOINCREMENT,
                date       DATE NOT NULL,
                subject    TEXT NOT NULL DEFAULT '通用',
                content    TEXT NOT NULL,
                completed  INTEGER NOT NULL DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );

            -- 每日学习进度
            CREATE TABLE IF NOT EXISTS daily_progress (
                id                INTEGER PRIMARY KEY AUTOINCREMENT,
                date              DATE NOT NULL,
                subject           TEXT NOT NULL,
                planned_minutes   INTEGER NOT NULL DEFAULT 0,
                completed_minutes INTEGER NOT NULL DEFAULT 0,
                UNIQUE(date, subject)
            );

            -- 每日打卡
            CREATE TABLE IF NOT EXISTS daily_checkin (
                id         INTEGER PRIMARY KEY AUTOINCREMENT,
                date       DATE NOT NULL UNIQUE,
                start_time TEXT,
                end_time   TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );

            -- 错题本
            CREATE TABLE IF NOT EXISTS error_book (
                id         INTEGER PRIMARY KEY AUTOINCREMENT,
                subject    TEXT NOT NULL,
                question   TEXT,
                answer     TEXT,
                analysis   TEXT,
                image_path TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );

            -- 公式
            CREATE TABLE IF NOT EXISTS formulas (
                id         INTEGER PRIMARY KEY AUTOINCREMENT,
                subject    TEXT NOT NULL,
                name       TEXT NOT NULL,
                content    TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );

            -- 每日金句
            CREATE TABLE IF NOT EXISTS daily_quotes (
                id         INTEGER PRIMARY KEY AUTOINCREMENT,
                date       DATE NOT NULL UNIQUE,
                quote      TEXT NOT NULL,
                theme      TEXT
            );
        """)


# ==================== 番茄钟记录 ====================

def add_pomodoro(subject: str, duration: int, record_date: date | None = None):
    """新增一条番茄钟记录"""
    d = (record_date or date.today()).isoformat()
    with get_conn() as conn:
        conn.execute(
            "INSERT INTO pomodoro_records (date, subject, duration) VALUES (?, ?, ?)",
            (d, subject, duration)
        )


def get_pomodoro_records(start: date | None = None, end: date | None = None) -> list[dict]:
    """获取番茄钟记录"""
    sql = "SELECT * FROM pomodoro_records WHERE 1=1"
    params = []
    if start:
        sql += " AND date >= ?"; params.append(start.isoformat())
    if end:
        sql += " AND date <= ?"; params.append(end.isoformat())
    sql += " ORDER BY created_at DESC"
    with get_conn() as conn:
        return [dict(r) for r in conn.execute(sql, params).fetchall()]


def get_today_pomodoro_minutes(subject: str | None = None) -> int:
    """获取今日番茄钟总分钟数"""
    today = date.today().isoformat()
    sql = "SELECT COALESCE(SUM(duration), 0) FROM pomodoro_records WHERE date = ?"
    params = [today]
    if subject:
        sql += " AND subject = ?"
        params.append(subject)
    with get_conn() as conn:
        return conn.execute(sql, params).fetchone()[0] // 60


# ==================== 待办事项 ====================

def add_todo(todo_date: date, subject: str, content: str):
    with get_conn() as conn:
        conn.execute(
            "INSERT INTO todos (date, subject, content) VALUES (?, ?, ?)",
            (todo_date.isoformat(), subject, content)
        )


def get_todos(todo_date: date | None = None, subject: str | None = None) -> list[dict]:
    sql = "SELECT * FROM todos WHERE 1=1"
    params = []
    if todo_date:
        sql += " AND date = ?"; params.append(todo_date.isoformat())
    if subject:
        sql += " AND subject = ?"; params.append(subject)
    sql += " ORDER BY completed ASC, created_at DESC"
    with get_conn() as conn:
        return [dict(r) for r in conn.execute(sql, params).fetchall()]


def toggle_todo(todo_id: int):
    with get_conn() as conn:
        conn.execute("UPDATE todos SET completed = 1 - completed WHERE id = ?", (todo_id,))


def delete_todo(todo_id: int):
    with get_conn() as conn:
        conn.execute("DELETE FROM todos WHERE id = ?", (todo_id,))


# ==================== 每日进度 ====================

def upsert_progress(progress_date: date, subject: str, planned_minutes: int, completed_minutes: int):
    with get_conn() as conn:
        conn.execute("""
            INSERT INTO daily_progress (date, subject, planned_minutes, completed_minutes)
            VALUES (?, ?, ?, ?)
            ON CONFLICT(date, subject) DO UPDATE SET
                planned_minutes = excluded.planned_minutes,
                completed_minutes = excluded.completed_minutes
        """, (progress_date.isoformat(), subject, planned_minutes, completed_minutes))


def get_progress(progress_date: date, subject: str | None = None) -> list[dict]:
    sql = "SELECT * FROM daily_progress WHERE date = ?"
    params = [progress_date.isoformat()]
    if subject:
        sql += " AND subject = ?"; params.append(subject)
    with get_conn() as conn:
        return [dict(r) for r in conn.execute(sql, params).fetchall()]


# ==================== 每日打卡 ====================

def do_checkin(check_date: date, start_time: str, end_time: str):
    with get_conn() as conn:
        conn.execute("""
            INSERT INTO daily_checkin (date, start_time, end_time)
            VALUES (?, ?, ?)
            ON CONFLICT(date) DO UPDATE SET
                start_time = excluded.start_time,
                end_time = excluded.end_time
        """, (check_date.isoformat(), start_time, end_time))


def get_checkin(check_date: date) -> dict | None:
    with get_conn() as conn:
        row = conn.execute(
            "SELECT * FROM daily_checkin WHERE date = ?", (check_date.isoformat(),)
        ).fetchone()
        return dict(row) if row else None


def get_all_checkins(start: date | None = None, end: date | None = None) -> list[dict]:
    sql = "SELECT * FROM daily_checkin WHERE 1=1"
    params = []
    if start:
        sql += " AND date >= ?"; params.append(start.isoformat())
    if end:
        sql += " AND date <= ?"; params.append(end.isoformat())
    sql += " ORDER BY date DESC"
    with get_conn() as conn:
        return [dict(r) for r in conn.execute(sql, params).fetchall()]


# ==================== 错题本 ====================

def add_error(subject: str, question: str, answer: str, analysis: str, image_path: str = ""):
    with get_conn() as conn:
        conn.execute(
            "INSERT INTO error_book (subject, question, answer, analysis, image_path) VALUES (?, ?, ?, ?, ?)",
            (subject, question, answer, analysis, image_path)
        )


def get_errors(subject: str | None = None) -> list[dict]:
    sql = "SELECT * FROM error_book WHERE 1=1"
    params = []
    if subject and subject != "全部":
        sql += " AND subject = ?"; params.append(subject)
    sql += " ORDER BY created_at DESC"
    with get_conn() as conn:
        return [dict(r) for r in conn.execute(sql, params).fetchall()]


def update_error(error_id: int, subject: str, question: str, answer: str, analysis: str, image_path: str = ""):
    with get_conn() as conn:
        conn.execute(
            "UPDATE error_book SET subject=?, question=?, answer=?, analysis=?, image_path=? WHERE id=?",
            (subject, question, answer, analysis, image_path, error_id)
        )


def delete_error(error_id: int):
    with get_conn() as conn:
        conn.execute("DELETE FROM error_book WHERE id = ?", (error_id,))


# ==================== 公式 ====================

def add_formula(subject: str, name: str, content: str):
    with get_conn() as conn:
        conn.execute(
            "INSERT INTO formulas (subject, name, content) VALUES (?, ?, ?)",
            (subject, name, content)
        )


def get_formulas(subject: str) -> list[dict]:
    with get_conn() as conn:
        return [dict(r) for r in conn.execute(
            "SELECT * FROM formulas WHERE subject = ? ORDER BY id", (subject,)
        ).fetchall()]


def update_formula(formula_id: int, name: str, content: str):
    with get_conn() as conn:
        conn.execute("UPDATE formulas SET name=?, content=? WHERE id=?", (name, content, formula_id))


def delete_formula(formula_id: int):
    with get_conn() as conn:
        conn.execute("DELETE FROM formulas WHERE id = ?", (formula_id,))


# ==================== 每日金句 ====================

def get_today_quote() -> dict | None:
    today = date.today().isoformat()
    with get_conn() as conn:
        row = conn.execute("SELECT * FROM daily_quotes WHERE date = ?", (today,)).fetchone()
        return dict(row) if row else None


def add_quote(quote_date: date, quote: str, theme: str):
    with get_conn() as conn:
        conn.execute(
            "INSERT OR REPLACE INTO daily_quotes (date, quote, theme) VALUES (?, ?, ?)",
            (quote_date.isoformat(), quote, theme)
        )
