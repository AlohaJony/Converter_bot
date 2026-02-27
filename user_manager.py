import os
import psycopg2
from psycopg2 import pool
from datetime import date
from contextlib import contextmanager
import logging
from config import DATABASE_URL

logger = logging.getLogger(__name__)

# Логируем значение DATABASE_URL для отладки
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

def deduct_tokens(user_id, amount, description):
    """Списать токены. Возвращает True, если хватило средств."""
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT balance FROM users WHERE user_id = %s FOR UPDATE", (user_id,))
            row = cur.fetchone()
            if not row or row[0] < amount:
                return False
            cur.execute(
                "UPDATE users SET balance = balance - %s WHERE user_id = %s",
                (amount, user_id)
            )
            cur.execute(
                "INSERT INTO transactions (user_id, amount, description) VALUES (%s, %s, %s)",
                (user_id, -amount, description)
            )
            return True

def check_and_use_free_limit(user_id, bot_name):
    """
    Проверяет, не превышен ли дневной бесплатный лимит.
    Если лимит не исчерпан, увеличивает счётчик и возвращает True.
    Иначе возвращает False.
    """
    today = date.today()
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT free_limit_per_day FROM prices WHERE bot_name = %s",
                (bot_name,)
            )
            price_row = cur.fetchone()
            if not price_row:
                return False
            free_limit = price_row[0]
            if free_limit <= 0:
                return False
            cur.execute(
                "SELECT usage_count FROM bot_usage WHERE user_id = %s AND bot_name = %s AND usage_date = %s",
                (user_id, bot_name, today)
            )
            usage_row = cur.fetchone()
            used = usage_row[0] if usage_row else 0
            if used < free_limit:
                if usage_row:
                    cur.execute(
                        "UPDATE bot_usage SET usage_count = usage_count + 1 WHERE user_id = %s AND bot_name = %s AND usage_date = %s",
                        (user_id, bot_name, today)
                    )
                else:
                    cur.execute(
                        "INSERT INTO bot_usage (user_id, bot_name, usage_date, usage_count) VALUES (%s, %s, %s, 1)",
                        (user_id, bot_name, today)
                    )
                return True
            else:
                return False

def get_price(bot_name):
    """Возвращает стоимость одной операции в токенах."""
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT price_per_use FROM prices WHERE bot_name = %s", (bot_name,))
            row = cur.fetchone()
            return row[0] if row else 0
