import pymysql
import datetime
from pymysql.err import OperationalError
import os
import logging
from open_webui.env import SRC_LOG_LEVELS

log = logging.getLogger(__name__)
log.setLevel(SRC_LOG_LEVELS["MODELS"])

WP_DB_HOST = os.getenv("WP_DB_HOST", "localhost")
WP_DB_USER = os.getenv("WP_DB_USER", "test_ai1s_top")
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
    log.info(f"get_wp_post_with_meta_by_id: {post_id}")
    try:
        connection = pymysql.connect(
            host=WP_DB_HOST,
            user=WP_DB_USER,
            password=WP_DB_PASS,
            database=WP_DB_NAME,
            charset=WP_DB_CHARSET,
            cursorclass=pymysql.cursors.DictCursor  # 关键：指定字典游标
        )
        log.info(f"get_wp_post_with_meta_by_id: {connection}")
        with connection.cursor() as cursor:
            sql = f"""
            SELECT p.ID AS ID, p.post_name AS post_name, p.post_content AS post_content, pm.meta_value AS site_description
            FROM {WP_TABLE_PREFIX}posts p
            LEFT JOIN {WP_TABLE_PREFIX}postmeta pm ON p.ID = pm.post_id AND pm.meta_key = '_sites_sescribe'
            WHERE p.ID = %s
            """
            cursor.execute(sql, (post_id,))
            result = cursor.fetchone()
            log.info(f"get_wp_post_with_meta_by_id result: {result}")
            if result:
                return dict(result)
            else:
                return None
    except OperationalError as e:
        log.info(f"get_wp_post_with_meta_by_id error: {e}")
        return None

def get_all_wp_posts_with_meta():
    try:
        connection = pymysql.connect(
            host=WP_DB_HOST,
            user=WP_DB_USER,
            password=WP_DB_PASS,
            database=WP_DB_NAME,
            charset=WP_DB_CHARSET,
            cursorclass=pymysql.cursors.DictCursor  # 关键：指定字典游标
        )
        with connection.cursor() as cursor:
            sql = f"""
            SELECT p.ID AS ID, p.post_name AS post_name, p.post_content AS post_content, pm.meta_value AS site_description
            FROM {WP_TABLE_PREFIX}posts p
            LEFT JOIN {WP_TABLE_PREFIX}postmeta pm ON p.ID = pm.post_id AND pm.meta_key = '_sites_sescribe'
            WHERE p.post_type = 'sites'
            """
            cursor.execute(sql)
            results = cursor.fetchall()
            log.info(f"get_all_wp_posts_with_meta results len: {len(results)}, head(5): {results[:5]}")
            if results:
                return [dict(result) for result in results]
            else:
                return None
    except OperationalError:
        return None
