import os
import psycopg2
from psycopg2 import pool
from datetime import date
from contextlib import contextmanager
import logging
from config import DATABASE_URL

logger = logging.getLogger(__name__)

# Выводим значение DATABASE_URL для отладки (убедимся, что оно загружено)
logger.info(f"DATABASE_URL raw value: {repr(DATABASE_URL)}")

# Создаём пул соединений
connection_pool = psycopg2.pool.SimpleConnectionPool(1, 20, dsn=DATABASE_URL)

@contextmanager
def get_connection():
    conn = connection_pool.getconn()
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        connection_pool.putconn(conn)

def get_or_create_user(user_id, username=None, first_name=None):
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "INSERT INTO users (user_id, username, first_name) VALUES (%s, %s, %s) "
                "ON CONFLICT (user_id) DO UPDATE SET "
                "username = EXCLUDED.username, first_name = EXCLUDED.first_name "
                "RETURNING balance, subscription_end",
                (user_id, username, first_name)
            )
            return cur.fetchone()

def get_balance(user_id):
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT balance FROM users WHERE user_id = %s", (user_id,))
            res = cur.fetchone()
            return res[0] if res else 0

def add_tokens(user_id, amount, description):
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "UPDATE users SET balance = balance + %s WHERE user_id = %s RETURNING balance",
                (amount, user_id)
            )
            new_balance = cur.fetchone()[0]
            cur.execute(
                "INSERT INTO transactions (user_id, amount, description) VALUES (%s, %s, %s)",
                (user_id, amount, description)
            )
            return new_balance
