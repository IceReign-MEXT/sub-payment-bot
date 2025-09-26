import os
import psycopg2
from psycopg2 import sql
from dotenv import load_dotenv

# Load .env variables
load_dotenv()

DATABASE_URL = os.environ.get("DATABASE_URL")

if not DATABASE_URL:
    raise ValueError("DATABASE_URL not found in environment")

# SQL statements to create tables
CREATE_SUBSCRIPTIONS_TABLE = """
CREATE TABLE IF NOT EXISTS subscriptions (
    id SERIAL PRIMARY KEY,
    telegram_id BIGINT NOT NULL,
    plan VARCHAR(50) NOT NULL,
    start_ts BIGINT NOT NULL,
    expires_ts BIGINT NOT NULL
);
"""

CREATE_PENDING_PAYMENTS_TABLE = """
CREATE TABLE IF NOT EXISTS pending_payments (
    id SERIAL PRIMARY KEY,
    telegram_id BIGINT NOT NULL,
    plan VARCHAR(50) NOT NULL,
    chain VARCHAR(10) NOT NULL,
    expected_amount NUMERIC NOT NULL,
    tx_hash VARCHAR(255),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
"""

def init_db():
    try:
        conn = psycopg2.connect(DATABASE_URL)
        cur = conn.cursor()
        cur.execute(CREATE_SUBSCRIPTIONS_TABLE)
        cur.execute(CREATE_PENDING_PAYMENTS_TABLE)
        conn.commit()
        print("✅ Database tables initialized successfully!")
    except Exception as e:
        print(f"❌ Error initializing database: {e}")
    finally:
        if cur:
            cur.close()
        if conn:
            conn.close()

if __name__ == "__main__":
    init_db()
