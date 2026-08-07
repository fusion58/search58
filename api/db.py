import os
import psycopg2
from psycopg2 import pool

_pool = None

def get_pool():
    global _pool
    if _pool is None:
        _pool = psycopg2.pool.ThreadedConnectionPool(
            minconn=2,
            maxconn=10,
            host=os.environ.get('POSTGRES_HOST', 'postgres'),
            port=int(os.environ.get('POSTGRES_PORT', '5432')),
            user=os.environ.get('POSTGRES_USER', 'postgres'),
            password=os.environ['POSTGRES_PASSWORD'],
            dbname=os.environ.get('POSTGRES_DB', 'buscador'),
        )
    return _pool

def run_sql(sql, params=()):
    p = get_pool()
    conn = p.getconn()
    try:
        with conn.cursor() as cur:
            cur.execute(sql, params)
            rows = cur.fetchall()
        conn.commit()
        return rows
    except Exception:
        conn.rollback()
        raise
    finally:
        p.putconn(conn)
