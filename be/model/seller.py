import json
import logging

import psycopg2

from be.model import error
from be.model import db_conn


class Seller(db_conn.DBConn):
    def __init__(self):
        """
        初始化 Seller 类，继承数据库连接。
        """
        db_conn.DBConn.__init__(self)

    def add_book(
            self,
            user_id: str,
            store_id: str,
            book_id: str,
            book_json_str: str,
            stock_level: int,
    ):
        """
        向商店中添加书籍。

        :param user_id: 用户ID
        :param store_id: 商店ID
        :param book_id: 书籍ID
        :param book_json_str: 书籍信息的 JSON 字符串
        :param stock_level: 库存数量
        :return: 状态码, 消息
        """
        try:
            # 检查用户是否存在
            if not self.user_id_exist(user_id):
                return error.error_non_exist_user_id(user_id)
            # 检查商店是否存在
            if not self.store_id_exist(store_id):
                return error.error_non_exist_store_id(store_id)
            # 检查书籍是否已存在于商店中
            if self.book_id_exist(store_id, book_id):
                return error.error_exist_book_id(book_id)

            # 解析书籍信息
            book_data = json.loads(book_json_str)

            # 插入书籍信息到 book 表
            with self.conn.cursor() as cursor:
                cursor.execute("""
                    INSERT INTO book (
                        book_id, title, author, publisher, content, original_title, translator, pub_year, pages, price, currency_unit, binding, isbn, author_intro, book_intro, tags, pictures
                    ) VALUES (
                        %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s
                    );
                """, (
                    book_id,
                    book_data.get("title"),
                    book_data.get("author"),
                    book_data.get("publisher"),
                    book_data.get("content"),
                    book_data.get("original_title"),
                    book_data.get("translator"),
                    book_data.get("pub_year"),
                    book_data.get("pages"),
                    book_data.get("price"),
                    book_data.get("currency_unit"),
                    book_data.get("binding"),
                    book_data.get("isbn"),
                    book_data.get("author_intro"),
                    book_data.get("book_intro"),
                    json.dumps(book_data.get("tags", [])),  # 将 tags 转换为 JSON 字符串
                    json.dumps(book_data.get("pictures", []))  # 将 pictures 转换为 JSON 字符串
                ))

                # 更新 store 表的 books 字段
                cursor.execute("""
                    UPDATE store
                    SET books = jsonb_insert(
                        books,
                        '{0}',
                        jsonb_build_object('book_id', %s, 'stock_level', %s)
                    )
                    WHERE store_id = %s;
                """, (book_id, stock_level, store_id))

                self.conn.commit()
        except Exception as e:
            logging.error(str(e))
            self.conn.rollback()
            return 530, "{}".format(str(e))
        return 200, "ok"

    def add_stock_level(
            self, user_id: str, store_id: str, book_id: str, add_stock_level: int
    ):
        """
        增加书籍库存。

        :param user_id: 用户ID
        :param store_id: 商店ID
        :param book_id: 书籍ID
        :param add_stock_level: 增加的库存数量
        :return: 状态码, 消息
        """
        try:
            if not self.user_id_exist(user_id):
                return error.error_non_exist_user_id(user_id)
            if not self.store_id_exist(store_id):
                return error.error_non_exist_store_id(store_id)
            if not self.book_id_exist(store_id, book_id):
                return error.error_non_exist_book_id(book_id)

            with self.conn.cursor() as cursor:
                # 查找 books 数组中匹配的 book_id，并更新其 stock_level
                cursor.execute("""
                    UPDATE store
                    SET books = jsonb_set(
                        books,
                        ('{' || subquery.idx-1 || ',stock_level}')::text[],
                        to_jsonb((subquery.stock_level + %s)::int)
                    )
                    FROM (
                        SELECT idx, (value->>'stock_level')::int AS stock_level
                        FROM store,
                        jsonb_array_elements(books) WITH ORDINALITY AS book(value, idx)
                        WHERE store_id = %s
                        AND (value->>'book_id') = %s
                    ) AS subquery
                    WHERE store_id = %s;
                """, (add_stock_level, store_id, book_id, store_id))

                self.conn.commit()
        except psycopg2.Error as e:
            logging.error(str(e))
            self.conn.rollback()
            return 528, "{}".format(str(e))
        except Exception as e:
            logging.error(str(e))
            self.conn.rollback()
            return 530, "{}".format(str(e))
        return 200, "ok"

    def create_store(self, user_id: str, store_id: str) -> (int, str):
        """
        创建商店。

        :param user_id: 用户ID
        :param store_id: 商店ID
        :return: 状态码, 消息
        """
        try:
            if not self.user_id_exist(user_id):
                return error.error_non_exist_user_id(user_id)
            if self.store_id_exist(store_id):
                return error.error_exist_store_id(store_id)

            with self.conn.cursor() as cursor:
                cursor.execute("""
                    INSERT INTO store (store_id, user_id, books)
                    VALUES (%s, %s, '[]'::jsonb);
                """, (store_id, user_id))

                self.conn.commit()
        except Exception as e:
            logging.error(str(e))
            self.conn.rollback()
            return 530, "{}".format(str(e))
        return 200, "ok"

    def deliver(self, user_id: str, order_id: str) -> (int, str):
        """
        发货订单。

        :param user_id: 用户ID
        :param order_id: 订单ID
        :return: 状态码, 消息
        """
        try:
            # 使用 DictCursor 将查询结果转换为字典
            cursor = self.conn.cursor(cursor_factory=psycopg2.extras.DictCursor)

            # 查询订单信息
            cursor.execute("""
                SELECT * FROM "order"
                WHERE order_id = %s AND (status = '1' OR status = '2' OR status = '3')
            """, (order_id,))
            order = cursor.fetchone()
            if order is None:
                self.conn.rollback()
                logging.error(f"订单不存在或状态无效: {order_id}")
                return error.error_invalid_order_id(order_id)

            status = order["status"]  # 通过字段名访问

            # 检查订单状态
            if status == '2' or status == '3':
                self.conn.rollback()
                logging.error(f"订单已发货或已完成: {order_id}")
                return error.error_books_repeat_deliver()

            # 更新订单状态为已发货（状态 2）
            cursor.execute("""
                UPDATE "order"
                SET status = '2'
                WHERE order_id = %s
            """, (order_id,))
            if cursor.rowcount == 0:
                self.conn.rollback()
                logging.error(f"更新订单状态失败: {order_id}")
                return error.error_invalid_order_id(order_id)

            # 提交事务
            self.conn.commit()
            logging.info(f"发货成功: 订单 {order_id}, 用户 {user_id}")
        except Exception as e:
            self.conn.rollback()
            logging.error(f"发货异常: {str(e)}")
            return 528, "{}".format(str(e))

        return 200, "ok"