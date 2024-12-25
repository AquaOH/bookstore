from be.model import store
import psycopg2


class DBConn:
    def __init__(self):
        # 获取 PostgreSQL 数据库连接
        self.conn = store.get_db_conn()

    def user_id_exist(self, user_id):
        cursor = self.conn.cursor()
        try:
            # 查询 user 表中是否存在指定的 user_id
            cursor.execute('SELECT 1 FROM "user" WHERE user_id = %s;', (user_id,))
            result = cursor.fetchone()
            if result is None:
                return False
            else:
                return True
        finally:
            cursor.close()

    def book_id_exist(self, store_id, book_id):
        cursor = self.conn.cursor()
        try:
            # 查询 store 表中是否存在指定的 store_id 和 book_id
            cursor.execute('''
                SELECT 1 FROM "store" 
                WHERE store_id = %s 
                AND books @> jsonb_build_array(jsonb_build_object('book_id', %s));
            ''', (store_id, book_id))
            result = cursor.fetchone()
            if result is None:
                return False
            else:
                return True
        finally:
            cursor.close()

    def store_id_exist(self, store_id):
        cursor = self.conn.cursor()
        try:
            # 查询 store 表中是否存在指定的 store_id
            cursor.execute('SELECT 1 FROM "store" WHERE store_id = %s;', (store_id,))
            result = cursor.fetchone()
            if result is None:
                return False
            else:
                return True
        finally:
            cursor.close()