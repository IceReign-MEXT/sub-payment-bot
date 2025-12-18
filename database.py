import sqlite3
from datetime import datetime, timedelta

def init_db():
    conn = sqlite3.connect('users.db')
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS users
                 (user_id INTEGER PRIMARY KEY,
                  expiry_date TEXT,
                  plan TEXT)''')
    conn.commit()
    conn.close()

def add_subscription(user_id, days, plan_name):
    conn = sqlite3.connect('users.db')
    c = conn.cursor()
    expiry = datetime.now() + timedelta(days=days)
    expiry_str = expiry.strftime('%Y-%m-%d %H:%M:%S')
    c.execute("INSERT OR REPLACE INTO users VALUES (?, ?, ?)", (user_id, expiry_str, plan_name))
    conn.commit()
    conn.close()

def check_subscription(user_id):
    conn = sqlite3.connect('users.db')
    c = conn.cursor()
    c.execute("SELECT expiry_date FROM users WHERE user_id = ?", (user_id,))
    result = c.fetchone()
    conn.close()

    if result:
        expiry = datetime.strptime(result[0], '%Y-%m-%d %H:%M:%S')
        if expiry > datetime.now():
            return True
    return False
