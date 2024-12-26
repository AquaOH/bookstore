import logging
import psycopg2
import psycopg2.extras
import threading
import os

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

class Store:
    def __init__(self):
        """
        初始化 Store 类，连接 PostgreSQL 数据库并初始化数据表。
        """
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
        """
        初始化数据库表结构，包括 user、book、store、order 和 order_detail 表。
        如果表已存在，则先删除再重新创建。
        """
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

                # 在 user_id 上创建唯一升序索引（主键已自动创建索引）
                cursor.execute('CREATE UNIQUE INDEX idx_user_id ON "user" (user_id);')

                # 删除并重新创建 book 表
                cursor.execute('DROP TABLE IF EXISTS "book";')
                cursor.execute("""
                    CREATE TABLE "book" (
                        id SERIAL PRIMARY KEY,
                        book_id TEXT NOT NULL,    -- 书籍ID
                        title TEXT NOT NULL,             -- 书名
                        author TEXT,                     -- 作者
                        publisher TEXT,                  -- 出版社
                        content TEXT,                    -- 内容
                        original_title TEXT,             -- 原书名
                        translator TEXT,                 -- 译者
                        pub_year TEXT,                   -- 出版年份
                        pages INTEGER,                   -- 页数
                        price INTEGER,                   -- 价格
                        currency_unit TEXT,              -- 货币单位
                        binding TEXT,                    -- 装帧
                        isbn TEXT,                -- ISBN号
                        author_intro TEXT,               -- 作者简介
                        book_intro TEXT,                 -- 书籍简介
                        tags JSONB,                      -- 标签（JSON数组）
                        pictures JSONB                   -- 图片链接（JSON数组）
                    );
                """)

                # 在 title 上创建普通索引
                cursor.execute('CREATE INDEX idx_title ON "book" (title);')

                # 在 tags 上创建 GIN 索引
                cursor.execute('CREATE INDEX idx_tags ON "book" USING GIN (tags);')

                # 在 book_intro 上创建 GIN 索引，支持全文搜索
                cursor.execute("""
                    CREATE INDEX idx_book_intro ON "book" USING GIN (to_tsvector('english', book_intro));
                """)

                # 在 content 上创建 GIN 索引，支持全文搜索
                cursor.execute("""
                    CREATE INDEX idx_content ON "book" USING GIN (to_tsvector('english', content));
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

                # 在 store_id 上创建唯一升序索引（主键已自动创建索引）
                cursor.execute('CREATE UNIQUE INDEX idx_store_id ON "store" (store_id);')

                # 删除并重新创建 order 表
                cursor.execute('DROP TABLE IF EXISTS "order";')
                cursor.execute("""
                    CREATE TABLE "order" (
                        id SERIAL PRIMARY KEY,
                        order_id TEXT,  
                        store_id TEXT,
                        user_id TEXT,
                        create_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP, -- 订单创建时间
                        price NUMERIC NOT NULL,    -- 订单总价
                        status TEXT NOT NULL     -- 订单状态
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
        """
        获取数据库连接对象。

        :return: 数据库连接对象
        """
        return self.conn

    def close(self):
        """
        关闭数据库连接。
        """
        if self.conn:
            self.conn.close()


# 全局变量，用于存储数据库实例
database_instance: Store = None
# 全局变量，用于数据库初始化的同步
init_completed_event = threading.Event()


def init_database():
    """
    初始化数据库实例。
    """
    global database_instance
    if database_instance is None:
        # 初始化数据库实例
        database_instance = Store()


def get_db_conn():
    """
    获取数据库连接对象。如果数据库实例未初始化，则先初始化。

    :return: 数据库连接对象
    """
    global database_instance
    if database_instance is None:
        init_database()
    return database_instance.get_db_conn()