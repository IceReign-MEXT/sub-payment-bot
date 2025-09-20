import sqlite3
import time

DATABASE_PATH = "subscriptions.db" # The database file will be created in your project directory

def init_db():
    """Initializes the database tables if they don't exist."""
    conn = sqlite3.connect(DATABASE_PATH)
    c = conn.cursor()

    # Table for pending payment requests
    c.execute("""
    CREATE TABLE IF NOT EXISTS pending_payments (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        telegram_id TEXT NOT NULL,
        plan TEXT NOT NULL,
        chain TEXT NOT NULL,
        expected_amount REAL NOT NULL,
        created_ts INTEGER NOT NULL,
        processed INTEGER DEFAULT 0,
        tx_hash TEXT -- To store the transaction hash if provided or found
    )
    """)

    # Table for active subscriptions
    c.execute("""
    CREATE TABLE IF NOT EXISTS subscriptions (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        telegram_id TEXT NOT NULL,
        plan TEXT NOT NULL,
        start_ts INTEGER NOT NULL,
        expires_ts INTEGER NOT NULL
    )
    """)
    conn.commit()
    conn.close()

def add_pending_payment_request(telegram_id, plan, chain, expected_amount):
    """Adds a new pending payment request to the database."""
    conn = sqlite3.connect(DATABASE_PATH)
    c = conn.cursor()
    c.execute(
        "INSERT INTO pending_payments (telegram_id, plan, chain, expected_amount, created_ts) VALUES (?, ?, ?, ?, ?)",
        (str(telegram_id), plan, chain, float(expected_amount), int(time.time()))
    )
    conn.commit()
    conn.close()

def get_pending_payment_requests():
    """Retrieves all unprocessed pending payment requests."""
    conn = sqlite3.connect(DATABASE_PATH)
    c = conn.cursor()
    c.execute("SELECT id, telegram_id, plan, chain, expected_amount FROM pending_payments WHERE processed=0")
    rows = c.fetchall()
    conn.close()
    # Return as a list of dictionaries for easier access
    return [{"id": r[0], "telegram_id": r[1], "plan": r[2], "chain": r[3], "expected_amount": r[4]} for r in rows]

def mark_payment_processed(pending_id, tx_hash=None):
    """Marks a pending payment as processed and stores the transaction hash."""
    conn = sqlite3.connect(DATABASE_PATH)
    c = conn.cursor()
    if tx_hash:
        c.execute("UPDATE pending_payments SET processed=1, tx_hash=? WHERE id=?", (tx_hash, pending_id))
    else:
        c.execute("UPDATE pending_payments SET processed=1 WHERE id=?", (pending_id,))
    conn.commit()
    conn.close()

def add_subscription(telegram_id, plan, start_ts, expires_ts):
    """Adds a new subscription or extends an existing one if the plan is higher/lifetime."""
    conn = sqlite3.connect(DATABASE_PATH)
    c = conn.cursor()
    
    # Check for existing subscription for the user
    c.execute("SELECT expires_ts FROM subscriptions WHERE telegram_id=? ORDER BY expires_ts DESC LIMIT 1", (str(telegram_id),))
    existing_sub = c.fetchone()

    # If an existing subscription is found, ensure the new one doesn't shorten it
    if existing_sub and expires_ts < existing_sub[0]:
        # This logic can be more complex, e.g., if a user buys a lifetime plan, it overrides.
        # For simplicity, we just add a new one, but you might want to update the existing.
        pass # Or handle extending/upgrading logic

    c.execute(
        "INSERT INTO subscriptions (telegram_id, plan, start_ts, expires_ts) VALUES (?, ?, ?, ?)",
        (str(telegram_id), plan, int(start_ts), int(expires_ts))
    )
    conn.commit()
    conn.close()

def get_latest_subscription(telegram_id):
    """Retrieves the latest active subscription for a user."""
    conn = sqlite3.connect(DATABASE_PATH)
    c = conn.cursor()
    current_time = int(time.time())
    c.execute(
        "SELECT plan, expires_ts FROM subscriptions WHERE telegram_id=? AND expires_ts > ? ORDER BY expires_ts DESC LIMIT 1",
        (str(telegram_id), current_time)
    )
    row = c.fetchone()
    conn.close()
    if row:
        return {"plan": row[0], "expires_ts": row[1]}
    return None

def get_all_active_subscriptions():
    """Retrieves all currently active subscriptions."""
    conn = sqlite3.connect(DATABASE_PATH)
    c = conn.cursor()
    current_time = int(time.time())
    c.execute(
        "SELECT telegram_id, plan, expires_ts FROM subscriptions WHERE expires_ts > ?",
        (current_time,)
    )
    rows = c.fetchall()
    conn.close()
    return [{"telegram_id": r[0], "plan": r[1], "expires_ts": r[2]} for r in rows]

