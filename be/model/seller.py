import json
import logging

import psycopg2

from be.model import error
from be.model import db_conn


class Seller(db_conn.DBConn):
    def __init__(self):
        db_conn.DBConn.__init__(self)

    def add_book(
            self,
            user_id: str,
            store_id: str,
            book_id: str,
            book_json_str: str,
            stock_level: int,
    ):
        try:
            if not self.user_id_exist(user_id):
                return error.error_non_exist_user_id(user_id)
            if not self.store_id_exist(store_id):
                return error.error_non_exist_store_id(store_id)
            if self.book_id_exist(store_id, book_id):
                return error.error_exist_book_id(book_id)

            # 插入书籍信息到 book 表
            book_data = json.loads(book_json_str)
            with self.conn.cursor() as cursor:
                cursor.execute("""
                    INSERT INTO book (book_id,title, author, content, tags, picture)
                    VALUES (%s, %s, %s, %s, %s, %s)
                    RETURNING id;
                """, (book_id, book_data.get("title"), book_data.get("author"),
                      book_data.get("content"), book_data.get("tags"), book_data.get("picture")))

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
        try:
            with self.conn.cursor() as cursor:
                cursor.execute("""
                    SELECT status
                    FROM "order"
                    WHERE order_id = %s
                    AND status IN (1, 2, 3);
                """, (order_id,))
                result = cursor.fetchone()

                if result is None:
                    return error.error_invalid_order_id(order_id)
                status = result[0]

                if status == 2 or status == 3:
                    return error.error_books_repeat_deliver()

                cursor.execute("""
                    UPDATE "order"
                    SET status = 2
                    WHERE order_id = %s;
                """, (order_id,))

                self.conn.commit()
        except Exception as e:
            logging.error(str(e))
            self.conn.rollback()
            return 530, "{}".format(str(e))
        return 200, "ok"