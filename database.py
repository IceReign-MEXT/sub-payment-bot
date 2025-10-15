# database.py
import os, psycopg2
from psycopg2.extras import RealDictCursor
from urllib.parse import urlparse
from dotenv import load_dotenv

load_dotenv()
DATABASE_URL = os.getenv("DATABASE_URL")

def get_conn():
    if not DATABASE_URL:
        raise RuntimeError("DATABASE_URL not set")
    return psycopg2.connect(DATABASE_URL)

def init_db():
    sql = """
    CREATE TABLE IF NOT EXISTS users (
      id BIGINT PRIMARY KEY,
      tg_username TEXT,
      plan TEXT,
      start_ts BIGINT,
      end_ts BIGINT
    );
    CREATE TABLE IF NOT EXISTS payments (
      id SERIAL PRIMARY KEY,
      user_id BIGINT,
      chain TEXT,
      addr TEXT,
      amount TEXT,
      tx_hash TEXT,
      confirmed BOOLEAN DEFAULT FALSE,
      created_at BIGINT DEFAULT EXTRACT(EPOCH FROM now())::bigint
    );
    """
    conn = get_conn()
    with conn:
        with conn.cursor() as cur:
            cur.execute(sql)
    conn.close()

def get_user(user_id):
    conn = get_conn()
    with conn.cursor(cursor_factory=RealDictCursor) as cur:
        cur.execute("SELECT * FROM users WHERE id=%s", (user_id,))
        row = cur.fetchone()
    conn.close()
    return row

def upsert_user_subscribe(user_id, username, plan, start_ts, end_ts):
    conn = get_conn()
    with conn:
        with conn.cursor() as cur:
            cur.execute("""
            INSERT INTO users (id, tg_username, plan, start_ts, end_ts)
            VALUES (%s,%s,%s,%s,%s)
            ON CONFLICT (id) DO UPDATE SET plan=EXCLUDED.plan, start_ts=EXCLUDED.start_ts, end_ts=EXCLUDED.end_ts, tg_username=EXCLUDED.tg_username
            """, (user_id, username, plan, start_ts, end_ts))
    conn.close()

def add_payment(user_id, chain, addr, amount, tx_hash=None):
    conn = get_conn()
    with conn:
        with conn.cursor() as cur:
            cur.execute("INSERT INTO payments (user_id, chain, addr, amount, tx_hash, confirmed) VALUES (%s,%s,%s,%s,%s,%s) RETURNING id",
                        (user_id, chain, addr, str(amount), tx_hash, False))
            pid = cur.fetchone()[0]
    conn.close()
    return pid

def confirm_payment(payment_id, tx_hash=None):
    conn = get_conn()
    with conn:
        with conn.cursor() as cur:
            cur.execute("UPDATE payments SET confirmed=true, tx_hash=%s WHERE id=%s", (tx_hash, payment_id))
    conn.close()

def get_pending_payments():
    conn = get_conn()
    with conn.cursor(cursor_factory=RealDictCursor) as cur:
        cur.execute("SELECT * FROM payments WHERE confirmed=false")
        rows = cur.fetchall()
    conn.close()
    return rows
