from be.model import store
import psycopg2


class DBConn:
    def __init__(self):
        """
        初始化数据库连接。
        """
        # 获取 PostgreSQL 数据库连接
        self.conn = store.get_db_conn()

    def user_id_exist(self, user_id):
        """
        检查用户是否存在。

        :param user_id: 用户ID
        :return: 如果用户存在返回 True，否则返回 False
        """
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
        """
        检查指定商店中是否存在指定的书籍。

        :param store_id: 商店ID
        :param book_id: 书籍ID
        :return: 如果书籍存在返回 True，否则返回 False
        """
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
        """
        检查商店是否存在。

        :param store_id: 商店ID
        :return: 如果商店存在返回 True，否则返回 False
        """
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