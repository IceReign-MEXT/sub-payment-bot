import os
import psycopg2
import time

DATABASE_URL = os.environ.get("DATABASE_URL")

def get_conn():
    return psycopg2.connect(DATABASE_URL)

def add_pending_payment_request(telegram_id, plan, chain, expected_amount):
    conn = get_conn(); cur = conn.cursor()
    cur.execute(
        """
        INSERT INTO pending_payments (telegram_id, plan, chain, expected_amount, created_ts, processed)
        VALUES (%s, %s, %s, %s, %s, 0)
        """,
        (str(telegram_id), plan, chain, float(expected_amount), int(time.time()))
    )
    conn.commit(); cur.close(); conn.close()

def get_pending_payment_requests():
    conn = get_conn(); cur = conn.cursor()
    cur.execute("SELECT id, telegram_id, plan, chain, expected_amount FROM pending_payments WHERE processed=0")
    rows = cur.fetchall(); cur.close(); conn.close()
    return [{"id": r[0], "telegram_id": r[1], "plan": r[2], "chain": r[3], "expected_amount": r[4]} for r in rows]

def mark_payment_processed(pending_id, tx_hash=None):
    conn = get_conn(); cur = conn.cursor()
    if tx_hash:
        cur.execute("UPDATE pending_payments SET processed=1, tx_hash=%s WHERE id=%s", (tx_hash, pending_id))
    else:
        cur.execute("UPDATE pending_payments SET processed=1 WHERE id=%s", (pending_id,))
    conn.commit(); cur.close(); conn.close()

def add_subscription(telegram_id, plan, start_ts, expires_ts):
    conn = get_conn(); cur = conn.cursor()
    cur.execute("SELECT expires_ts FROM subscriptions WHERE telegram_id=%s ORDER BY expires_ts DESC LIMIT 1", (str(telegram_id),))
    existing_sub = cur.fetchone()
    # keep simple: always insert new subscription record
    cur.execute(
        "INSERT INTO subscriptions (telegram_id, plan, start_ts, expires_ts) VALUES (%s, %s, %s, %s)",
        (str(telegram_id), plan, int(start_ts), int(expires_ts))
    )
    conn.commit(); cur.close(); conn.close()

def get_latest_subscription(telegram_id):
    conn = get_conn(); cur = conn.cursor()
    current_time = int(time.time())
    cur.execute("SELECT plan, expires_ts FROM subscriptions WHERE telegram_id=%s AND expires_ts > %s ORDER BY expires_ts DESC LIMIT 1", (str(telegram_id), current_time))
    row = cur.fetchone(); cur.close(); conn.close()
    return {"plan": row[0], "expires_ts": row[1]} if row else None

def get_all_active_subscriptions():
    conn = get_conn(); cur = conn.cursor()
    current_time = int(time.time())
    cur.execute("SELECT telegram_id, plan, expires_ts FROM subscriptions WHERE expires_ts > %s", (current_time,))
    rows = cur.fetchall(); cur.close(); conn.close()
    return [{"telegram_id": r[0], "plan": r[1], "expires_ts": r[2]} for r in rows]
