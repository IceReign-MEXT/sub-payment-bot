import sqlite3
from datetime import datetime, timedelta

DB_NAME = "subscriptions.db"

def init_db():
    """Initialize database & tables"""
    conn = sqlite3.connect(DB_NAME)
    cur = conn.cursor()
    cur.execute("""
        CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY,
            username TEXT,
            plan TEXT,
            start_date TEXT,
            end_date TEXT
        )
    """)
    conn.commit()
    conn.close()

def add_subscription(user_id: int, username: str, plan: str, days: int):
    """Add or update a user subscription"""
    conn = sqlite3.connect(DB_NAME)
    cur = conn.cursor()

    start_date = datetime.utcnow()
    end_date = start_date + timedelta(days=days)

    cur.execute("""
        INSERT OR REPLACE INTO users (user_id, username, plan, start_date, end_date)
        VALUES (?, ?, ?, ?, ?)
    """, (user_id, username, plan, start_date.isoformat(), end_date.isoformat()))

    conn.commit()
    conn.close()

def check_subscription(user_id: int):
    """Check if user has an active subscription"""
    conn = sqlite3.connect(DB_NAME)
    cur = conn.cursor()
    cur.execute("SELECT plan, end_date FROM users WHERE user_id = ?", (user_id,))
    row = cur.fetchone()
    conn.close()

    if row:
        plan, end_date = row
        if datetime.fromisoformat(end_date) > datetime.utcnow():
            return {"plan": plan, "active": True, "end_date": end_date}
        else:
            return {"plan": plan, "active": False, "end_date": end_date}
    return None

def remove_expired():
    """Remove expired subscriptions"""
    conn = sqlite3.connect(DB_NAME)
    cur = conn.cursor()
    cur.execute("DELETE FROM users WHERE end_date < ?", (datetime.utcnow().isoformat(),))
    conn.commit()
    conn.close()
