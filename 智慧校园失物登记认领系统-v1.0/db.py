"""
数据库连接与查询辅助模块
使用 mysql-connector-python 作为驱动（仅数据库驱动，不涉及Web框架）
"""
import mysql.connector
from mysql.connector import Error

# ============ 数据库连接配置 ============
DB_CONFIG = {
    "host": "127.0.0.1",
    "port": 3306,
    "user": "root",
    "password": "wan1314xy",        # ← 请改成你自己的MySQL密码
    "database": "lost_and_found",
    "charset": "utf8mb4",
}


def get_conn():
    """获取一个新的数据库连接"""
    return mysql.connector.connect(**DB_CONFIG)


def query_one(sql, params=None):
    """查询单行，返回 dict 或 None"""
    conn = get_conn()
    try:
        cur = conn.cursor(dictionary=True)
        cur.execute(sql, params or ())
        return cur.fetchone()
    finally:
        conn.close()


def query_all(sql, params=None):
    """查询多行，返回 list[dict]"""
    conn = get_conn()
    try:
        cur = conn.cursor(dictionary=True)
        cur.execute(sql, params or ())
        return cur.fetchall()
    finally:
        conn.close()


def execute(sql, params=None):
    """执行 INSERT/UPDATE/DELETE，返回 lastrowid"""
    conn = get_conn()
    try:
        cur = conn.cursor()
        cur.execute(sql, params or ())
        conn.commit()
        return cur.lastrowid
    except Error:
        conn.rollback()
        raise
    finally:
        conn.close()
