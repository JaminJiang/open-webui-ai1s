import pymysql
import datetime
from pymysql.err import OperationalError
import os

WP_DB_HOST = os.getenv("WP_DB_HOST", "localhost")
WP_DB_USER = os.getenv("WP_DB_USER", "root")
ENV = os.getenv("ENV", "dev")
if ENV == "prod":
    WP_DB_PASS = "W@b1991116"
    WP_DB_NAME = "ai1s_top"
else:
    WP_DB_PASS = os.getenv("WP_DB_PASS", "W@b1991116")
    WP_DB_NAME = os.getenv("WP_DB_NAME", "test_ai1s_top")
WP_DB_CHARSET = os.getenv("WP_DB_CHARSET", "utf8mb4")
WP_TABLE_PREFIX = os.getenv("WP_TABLE_PREFIX", "wp_")  # 适配WP表前缀

# get post with meta from wp_posts and wp_postmeta
def get_wp_post_with_meta_by_id(post_id):
    try:
        connection = pymysql.connect(
            host=WP_DB_HOST,
            user=WP_DB_USER,
            password=WP_DB_PASS,
            database=WP_DB_NAME,
            charset=WP_DB_CHARSET,
        )
        with connection.cursor() as cursor:
            sql = f"""
            SELECT p.*, pm.meta_key, pm.meta_value
            FROM {WP_TABLE_PREFIX}posts p
            LEFT JOIN {WP_TABLE_PREFIX}postmeta pm ON p.ID = pm.post_id
            WHERE p.ID = %s
            """
            cursor.execute(sql, (post_id,))
            result = cursor.fetchone()
            if result:
                return dict(result)
            else:
                return None
    except OperationalError:
        return None

def get_all_wp_posts_with_meta():
    try:
        connection = pymysql.connect(
            host=WP_DB_HOST,
            user=WP_DB_USER,
            password=WP_DB_PASS,
            database=WP_DB_NAME,
            charset=WP_DB_CHARSET,
        )
        with connection.cursor() as cursor:
            sql = f"""
            SELECT p.*, pm.meta_key, pm.meta_value
            FROM {WP_TABLE_PREFIX}posts p
            LEFT JOIN {WP_TABLE_PREFIX}postmeta pm ON p.ID = pm.post_id
            """
            cursor.execute(sql)
            results = cursor.fetchall()
            if results:
                return [dict(result) for result in results]
            else:
                return None
    except OperationalError:
        return None
