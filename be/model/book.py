import psycopg2

from be.model import db_conn
import json
import logging
from psycopg2 import extras

class Book(db_conn.DBConn):

    def __init__(self):
        db_conn.DBConn.__init__(self)
        self.conn.cursor_factory = extras.DictCursor  # 使用 DictCursor

    def search_title_in_store(self, title: str, store_id: str, page_num: int, page_size: int):
        try:
            with self.conn.cursor() as cursor:
                # 查询书籍信息
                cursor.execute("""
                    SELECT * FROM book
                    WHERE title = %s
                    ORDER BY id
                    LIMIT %s OFFSET %s;
                """, (title, page_size, (page_num - 1) * page_size))
                result_list = cursor.fetchall()

                # 如果指定了 store_id，过滤出该商店中的书籍
                if store_id:
                    books_in_store = []
                    for book in result_list:
                        cursor.execute("""
                            SELECT 1 FROM store
                            WHERE store_id = %s AND books @> jsonb_build_array(jsonb_build_object('book_id', %s));
                        """, (store_id, book['book_id']))
                        if cursor.fetchone():
                            books_in_store.append(book)
                    result_list = books_in_store

                if not result_list:
                    return 501, f"{title} book not exist", []
                return 200, "ok", result_list

        except Exception as e:
            logging.error(str(e))
            self.conn.rollback()
            return 530, "{}".format(str(e)), []

    def search_title(self, title: str, page_num: int, page_size: int):
        return self.search_title_in_store(title, "", page_num, page_size)

    def search_tag_in_store(self, tag: str, store_id: str, page_num: int, page_size: int):
        try:
            with self.conn.cursor() as cursor:
                # 查询书籍信息
                cursor.execute("""
                    SELECT * FROM book
                    WHERE tags @> %s
                    ORDER BY id
                    LIMIT %s OFFSET %s;
                """, (json.dumps([tag]), page_size, (page_num - 1) * page_size))
                result_list = cursor.fetchall()

                # 如果指定了 store_id，过滤出该商店中的书籍
                if store_id:
                    books_in_store = []
                    for book in result_list:
                        cursor.execute("""
                            SELECT 1 FROM store
                            WHERE store_id = %s AND books @> jsonb_build_array(jsonb_build_object('book_id', %s));
                        """, (store_id, book['book_id']))
                        if cursor.fetchone():
                            books_in_store.append(book)
                    result_list = books_in_store

                if not result_list:
                    return 501, f"{tag} book not exist", []
                return 200, "ok", result_list

        except Exception as e:
            logging.error(str(e))
            self.conn.rollback()
            return 530, "{}".format(str(e)), []

    def search_tag(self, tag: str, page_num: int, page_size: int):
        return self.search_tag_in_store(tag, "", page_num, page_size)

    def search_content_in_store(self, content: str, store_id: str, page_num: int, page_size: int):
        cursor = self.conn.cursor(cursor_factory=psycopg2.extras.DictCursor)

        # 全文搜索查询（同时匹配 book_intro 和 content 字段）
        query = """
        SELECT * FROM book
        WHERE to_tsvector('english', book_intro || ' ' || content) @@ to_tsquery('english', %s)
        OFFSET %s LIMIT %s
        """
        content_query = " & ".join(content.split())  # 预处理 content
        logging.info(
            f"Executing full-text search query: {query} with params: {content_query}, {(page_num - 1) * page_size}, {page_size}")
        cursor.execute(query, (content_query, (page_num - 1) * page_size, page_size))
        result_list = cursor.fetchall()
        logging.info(f"Full-text search result: {result_list}")

        if store_id:
            # 查询指定商店中的书籍
            store_query = """
            SELECT store_id
            FROM store
            WHERE store_id = %s AND EXISTS (
                SELECT 1
                FROM jsonb_array_elements(books) AS book
                WHERE book->>'book_id' = %s
            )
            """
            books_in_store = []
            for book in result_list:
                logging.info(f"Checking if book {book['book_id']} exists in store {store_id}")
                cursor.execute(store_query, (store_id, book["book_id"]))
                store_result = cursor.fetchone()
                logging.info(f"Store query result for book {book['book_id']}: {store_result}")
                if store_result:  # 判断查询结果是否为空
                    books_in_store.append(book)
            result_list = books_in_store

        if len(result_list) == 0:
            logging.warning(f"No books found for content: {content} in store: {store_id}")
            return 501, f"{content} book not exist", []
        return 200, "ok", result_list

    def search_content(self, content: str, page_num: int, page_size: int):
        return self.search_content_in_store(content, "", page_num, page_size)

    def search_author_in_store(self, author: str, store_id: str, page_num: int, page_size: int):
        try:
            with self.conn.cursor() as cursor:
                # 查询书籍信息
                cursor.execute("""
                    SELECT * FROM book
                    WHERE author = %s
                    ORDER BY id
                    LIMIT %s OFFSET %s;
                """, (author, page_size, (page_num - 1) * page_size))
                result_list = cursor.fetchall()

                # 如果指定了 store_id，过滤出该商店中的书籍
                if store_id:
                    books_in_store = []
                    for book in result_list:
                        cursor.execute("""
                            SELECT 1 FROM store
                            WHERE store_id = %s AND books @> jsonb_build_array(jsonb_build_object('book_id', %s));
                        """, (store_id, book['book_id']))
                        if cursor.fetchone():
                            books_in_store.append(book)
                    result_list = books_in_store

                if not result_list:
                    return 501, f"{author} book not exist", []
                return 200, "ok", result_list

        except Exception as e:
            logging.error(str(e))
            self.conn.rollback()
            return 530, "{}".format(str(e)), []

    def search_author(self, author: str, page_num: int, page_size: int):
        return self.search_author_in_store(author, "", page_num, page_size)