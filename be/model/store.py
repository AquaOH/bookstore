import logging
import psycopg2
import psycopg2.extras
import threading
import os

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

class Store:
    def __init__(self):
        # 初始化数据库连接
        self.conn = psycopg2.connect(
            host="127.0.0.1",
            port="5432",
            user="postgres",
            password=os.getenv("DB_PASSWORD", "Aqua7296"),
            database="bookstore"
        )
        # 初始化数据表
        self.init_tables()

    def init_tables(self):
        try:
            with self.conn.cursor() as cursor:
                # 删除并重新创建 user 表
                cursor.execute('DROP TABLE IF EXISTS "user";')
                cursor.execute("""
                    CREATE TABLE "user" (
                        user_id TEXT PRIMARY KEY,  -- 用户ID为主键
                        password TEXT NOT NULL,   -- 用户密码
                        balance NUMERIC NOT NULL, -- 用户余额
                        token TEXT,               -- 用户登录令牌
                        terminal TEXT             -- 用户终端信息
                    );
                """)

                # 删除并重新创建 book 表
                cursor.execute('DROP TABLE IF EXISTS "book";')
                cursor.execute("""
                    CREATE TABLE "book" (
                        id SERIAL PRIMARY KEY,
                        book_id TEXT,    -- 书籍ID
                        title TEXT NOT NULL,      -- 书名
                        author TEXT,              -- 作者
                        content TEXT,             -- 内容
                        tags TEXT,                -- 标签
                        picture TEXT              -- 图片链接
                    );
                """)

                # 删除并重新创建 store 表
                cursor.execute('DROP TABLE IF EXISTS "store";')
                cursor.execute("""
                    CREATE TABLE "store" (
                        store_id TEXT PRIMARY KEY,  -- 商店ID为主键
                        user_id TEXT REFERENCES "user"(user_id), -- 用户ID，外键
                        books JSONB                 -- 书籍信息，使用 JSONB 类型存储
                    );
                """)

                # 删除并重新创建 order 表
                cursor.execute('DROP TABLE IF EXISTS "order";')
                cursor.execute("""
                    CREATE TABLE "order" (
                        id SERIAL PRIMARY KEY,
                        order_id TEXT ,  
                        store_id TEXT,
                        user_id TEXT,
                        status TEXT NOT NULL,      -- 订单状态
                        price NUMERIC NOT NULL     -- 订单总价
                    );
                """)

                # 删除并重新创建 order_detail 表
                cursor.execute('DROP TABLE IF EXISTS "order_detail";')
                cursor.execute("""
                    CREATE TABLE "order_detail" (
                        id SERIAL PRIMARY KEY,
                        order_id TEXT,
                        book_id TEXT,
                        price NUMERIC NOT NULL,    -- 书籍单价
                        count INTEGER NOT NULL     -- 书籍数量
                    );
                """)

                # 提交事务
                self.conn.commit()
        except psycopg2.Error as e:
            # 捕获数据库错误并记录日志
            logging.error(e)
            # 回滚事务
            self.conn.rollback()

    def get_db_conn(self):
        # 返回数据库连接对象
        return self.conn

    def close(self):
        # 关闭数据库连接
        if self.conn:
            self.conn.close()


# 全局变量，用于存储数据库实例
database_instance: Store = None
# 全局变量，用于数据库初始化的同步
init_completed_event = threading.Event()


def init_database():
    global database_instance
    if database_instance is None:
        # 初始化数据库实例
        database_instance = Store()


def get_db_conn():
    global database_instance
    if database_instance is None:
        init_database()
    return database_instance.get_db_conn()