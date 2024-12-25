import psycopg2
import uuid
import json
import logging
from be.model import db_conn
from be.model import error
from datetime import datetime, timedelta, timezone
from apscheduler.schedulers.background import BackgroundScheduler

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

class Buyer(db_conn.DBConn):
    def __init__(self):
        db_conn.DBConn.__init__(self)

    def new_order(
            self, user_id: str, store_id: str, id_and_count: [(str, int)]
    ) -> (int, str, str):
        order_id = ""
        try:
            if not self.user_id_exist(user_id):
                return error.error_non_exist_user_id(user_id) + (order_id,)
            if not self.store_id_exist(store_id):
                return error.error_non_exist_store_id(store_id) + (order_id,)

            uid = "{}_{}_{}".format(user_id, store_id, str(uuid.uuid1()))
            total_price = 0

            with self.conn.cursor() as cursor:
                for book_id, count in id_and_count:
                    # 检查书籍是否存在
                    cursor.execute('''
                        SELECT books FROM store 
                        WHERE store_id = %s AND books @> %s::jsonb;
                    ''', (store_id, json.dumps([{"book_id": book_id}])))
                    result = cursor.fetchone()
                    if result is None:
                        return error.error_non_exist_book_id(book_id) + (order_id,)

                    # 获取书籍信息和库存
                    cursor.execute('SELECT price FROM book WHERE book_id = %s;', (book_id,))
                    result1 = cursor.fetchone()
                    if result1 is None:
                        return error.error_non_exist_book_id(book_id) + (order_id,)

                    price = result1[0]
                    stock_level = result[0][0]["stock_level"]

                    if stock_level < count:
                        return error.error_stock_level_low(book_id) + (order_id,)

                    # 更新库存
                    cursor.execute('''
                        UPDATE store 
                        SET books = jsonb_set(
                            books,
                            ('{' || idx-1 || ',stock_level}')::text[],
                            to_jsonb((books->idx-1->>'stock_level')::int - %s)
                        )
                        FROM (
                            SELECT idx 
                            FROM store, jsonb_array_elements(books) WITH ORDINALITY arr(elem, idx)
                            WHERE store_id = %s AND elem @> %s::jsonb
                        ) sub
                        WHERE store.store_id = %s;
                    ''', (count, store_id, json.dumps({"book_id": book_id}), store_id))

                    # 插入订单详情
                    cursor.execute('''
                        INSERT INTO order_detail (order_id, book_id, count, price)
                        VALUES (%s, %s, %s, %s);
                    ''', (uid, book_id, count, price))

                    total_price += price * count

                # 插入订单
                now_time = datetime.now(timezone.utc)
                cursor.execute('''
                    INSERT INTO "order" (order_id, store_id, user_id, create_time, price, status)
                    VALUES (%s, %s, %s, %s, %s, %s);
                ''', (uid, store_id, user_id, now_time, total_price, 0))

                self.conn.commit()
                order_id = uid

        except psycopg2.Error as e:
            logging.error("528, {}".format(str(e)))
            self.conn.rollback()
            return 528, "{}".format(str(e)), ""
        except BaseException as e:
            logging.error("530, {}".format(str(e)))
            self.conn.rollback()
            return 530, "{}".format(str(e)), ""

        return 200, "ok", order_id

    def payment(self, user_id: str, password: str, order_id: str) -> (int, str):
        try:
            with self.conn.cursor() as cursor:
                # 检查订单是否存在
                cursor.execute('''
                    SELECT user_id, store_id, price 
                    FROM "order" 
                    WHERE order_id = %s AND status = 0;
                ''', (order_id,))
                result = cursor.fetchone()
                if result is None:
                    return error.error_invalid_order_id(order_id)

                buyer_id, store_id, total_price = result

                if buyer_id != user_id:
                    return error.error_authorization_fail()

                # 检查用户密码和余额
                cursor.execute('SELECT balance, password FROM "user" WHERE user_id = %s;', (buyer_id,))
                result = cursor.fetchone()
                if result is None:
                    return error.error_non_exist_user_id(buyer_id)

                balance, user_password = result
                if user_password != password:
                    return error.error_authorization_fail()

                if balance < total_price:
                    return error.error_not_sufficient_funds(order_id)

                # 扣款
                cursor.execute('''
                    UPDATE "user" 
                    SET balance = balance - %s 
                    WHERE user_id = %s AND balance >= %s;
                ''', (total_price, buyer_id, total_price))
                if cursor.rowcount == 0:
                    return error.error_not_sufficient_funds(order_id)

                # 给卖家加款
                cursor.execute('SELECT user_id FROM store WHERE store_id = %s;', (store_id,))
                seller_id = cursor.fetchone()[0]

                cursor.execute('''
                    UPDATE "user" 
                    SET balance = balance + %s 
                    WHERE user_id = %s;
                ''', (total_price, seller_id))

                # 更新订单状态
                cursor.execute('''
                    UPDATE "order" 
                    SET status = 1 
                    WHERE order_id = %s AND status = 0;
                ''', (order_id,))

                self.conn.commit()

        except psycopg2.Error as e:
            logging.error("528, {}".format(str(e)))
            self.conn.rollback()
            return 528, "{}".format(str(e))
        except BaseException as e:
            logging.error("530, {}".format(str(e)))
            self.conn.rollback()
            return 530, "{}".format(str(e))

        return 200, "ok"

    def add_funds(self, user_id, password, add_value) -> (int, str):
        try:
            with self.conn.cursor() as cursor:
                # 检查用户密码
                cursor.execute('SELECT password FROM "user" WHERE user_id = %s;', (user_id,))
                result = cursor.fetchone()
                if result is None:
                    return error.error_authorization_fail()

                if result[0] != password:
                    return error.error_authorization_fail()

                # 增加余额
                cursor.execute('''
                    UPDATE "user" 
                    SET balance = balance + %s 
                    WHERE user_id = %s;
                ''', (add_value, user_id))

                self.conn.commit()

        except psycopg2.Error as e:
            logging.error("528, {}".format(str(e)))
            self.conn.rollback()
            return 528, "{}".format(str(e))
        except BaseException as e:
            logging.error("530, {}".format(str(e)))
            self.conn.rollback()
            return 530, "{}".format(str(e))

        return 200, "ok"

    def cancel_order(self, user_id: str, order_id: str) -> (int, str):
        try:
            with self.conn.cursor() as cursor:
                # 检查订单是否存在
                cursor.execute('''
                    SELECT user_id, store_id, price 
                    FROM "order" 
                    WHERE order_id = %s AND status = 0;
                ''', (order_id,))
                result = cursor.fetchone()
                if result is None:
                    return error.error_invalid_order_id(order_id)

                buyer_id, store_id, price = result

                if buyer_id != user_id:
                    return error.error_authorization_fail()

                # 恢复库存
                cursor.execute('SELECT book_id, count FROM order_detail WHERE order_id = %s;', (order_id,))
                order_details = cursor.fetchall()

                for book_id, count in order_details:
                    cursor.execute('''
                        UPDATE store 
                        SET books = jsonb_set(
                            books,
                            ('{' || idx-1 || ',stock_level}')::text[],
                            to_jsonb((books->idx-1->>'stock_level')::int + %s)
                        )
                        FROM (
                            SELECT idx 
                            FROM store, jsonb_array_elements(books) WITH ORDINALITY arr(elem, idx)
                            WHERE store_id = %s AND elem @> %s::jsonb
                        ) sub
                        WHERE store.store_id = %s;
                    ''', (count, store_id, json.dumps({"book_id": book_id}), store_id))

                # 更新订单状态为取消
                cursor.execute('''
                    UPDATE "order" 
                    SET status = 4 
                    WHERE order_id = %s;
                ''', (order_id,))

                self.conn.commit()

        except psycopg2.Error as e:
            logging.error("528, {}".format(str(e)))
            self.conn.rollback()
            return 528, "{}".format(str(e))
        except BaseException as e:
            logging.error("530, {}".format(str(e)))
            self.conn.rollback()
            return 530, "{}".format(str(e))

        return 200, "ok"

    def check_hist_order(self, user_id: str):
        try:
            with self.conn.cursor() as cursor:
                if not self.user_id_exist(user_id):
                    return error.error_non_exist_user_id(user_id)

                ans = []

                # 查询未支付订单
                cursor.execute('''
                    SELECT order_id, store_id, price 
                    FROM "order" 
                    WHERE user_id = %s AND status = 0;
                ''', (user_id,))
                unpaid_orders = cursor.fetchall()

                for order in unpaid_orders:
                    order_id, store_id, price = order
                    cursor.execute('SELECT book_id, count, price FROM order_detail WHERE order_id = %s;', (order_id,))
                    order_details = cursor.fetchall()

                    tmp_details = []
                    for book_id, count, price in order_details:
                        tmp_details.append({
                            "book_id": book_id,
                            "count": count,
                            "price": price
                        })

                    ans.append({
                        "status": "unpaid",
                        "order_id": order_id,
                        "buyer_id": user_id,
                        "store_id": store_id,
                        "total_price": price,
                        "details": tmp_details
                    })

                # 查询已支付订单
                cursor.execute('''
                    SELECT order_id, store_id, price, status 
                    FROM "order" 
                    WHERE user_id = %s AND status IN (1, 2, 3);
                ''', (user_id,))
                paid_orders = cursor.fetchall()

                books_status_list = ["unsent", "sent but not received", "received"]
                for order in paid_orders:
                    order_id, store_id, price, status = order
                    cursor.execute('SELECT book_id, count, price FROM order_detail WHERE order_id = %s;', (order_id,))
                    order_details = cursor.fetchall()

                    tmp_details = []
                    for book_id, count, price in order_details:
                        tmp_details.append({
                            "book_id": book_id,
                            "count": count,
                            "price": price
                        })

                    ans.append({
                        "order_id": order_id,
                        "buyer_id": user_id,
                        "store_id": store_id,
                        "total_price": price,
                        "status": books_status_list[status - 1],
                        "details": tmp_details
                    })

                # 查询已取消订单
                cursor.execute('''
                    SELECT order_id, store_id, price 
                    FROM "order" 
                    WHERE user_id = %s AND status = 4;
                ''', (user_id,))
                cancelled_orders = cursor.fetchall()

                for order in cancelled_orders:
                    order_id, store_id, price = order
                    cursor.execute('SELECT book_id, count, price FROM order_detail WHERE order_id = %s;', (order_id,))
                    order_details = cursor.fetchall()

                    tmp_details = []
                    for book_id, count, price in order_details:
                        tmp_details.append({
                            "book_id": book_id,
                            "count": count,
                            "price": price
                        })

                    ans.append({
                        "status": "cancelled",
                        "order_id": order_id,
                        "buyer_id": user_id,
                        "store_id": store_id,
                        "total_price": price,
                        "details": tmp_details
                    })

        except psycopg2.Error as e:
            logging.error("528, {}".format(str(e)))
            return 528, "{}".format(str(e)), None
        except BaseException as e:
            logging.error("530, {}".format(str(e)))
            return 530, "{}".format(str(e)), None

        if not ans:
            return 200, "ok", "No orders found"
        else:
            return 200, "ok", ans

    def auto_cancel_order(self) -> (int, str):
        try:
            with self.conn.cursor() as cursor:
                wait = 20
                current_time = datetime.now(timezone.utc)
                interval = current_time - timedelta(seconds=wait)

                # 查询超时未支付订单
                cursor.execute('''
                    SELECT order_id, user_id, store_id, price 
                    FROM "order" 
                    WHERE create_time <= %s AND status = 0;
                ''', (interval,))
                orders_to_cancel = cursor.fetchall()

                for order in orders_to_cancel:
                    order_id, user_id, store_id, price = order

                    # 恢复库存
                    cursor.execute('SELECT book_id, count FROM order_detail WHERE order_id = %s;', (order_id,))
                    order_details = cursor.fetchall()

                    for book_id, count in order_details:
                        cursor.execute('''
                            UPDATE store 
                            SET books = jsonb_set(
                                books,
                                ('{' || idx-1 || ',stock_level}')::text[],
                                to_jsonb((books->idx-1->>'stock_level')::int + %s)
                            )
                            FROM (
                                SELECT idx 
                                FROM store, jsonb_array_elements(books) WITH ORDINALITY arr(elem, idx)
                                WHERE store_id = %s AND elem @> %s::jsonb
                            ) sub
                            WHERE store.store_id = %s;
                        ''', (count, store_id, json.dumps({"book_id": book_id}), store_id))

                    # 更新订单状态为取消
                    cursor.execute('''
                        UPDATE "order" 
                        SET status = 4 
                        WHERE order_id = %s;
                    ''', (order_id,))

                self.conn.commit()

        except psycopg2.Error as e:
            logging.error("528, {}".format(str(e)))
            self.conn.rollback()
            return 528, "{}".format(str(e))
        except BaseException as e:
            logging.error("530, {}".format(str(e)))
            self.conn.rollback()
            return 530, "{}".format(str(e))

        return 200, "ok"

    def is_order_cancelled(self, order_id: str) -> (int, str):
        try:
            with self.conn.cursor() as cursor:
                cursor.execute('SELECT 1 FROM "order" WHERE order_id = %s AND status = 4;', (order_id,))
                result = cursor.fetchone()
                if result is None:
                    return error.error_auto_cancel_fail(order_id)
        except psycopg2.Error as e:
            logging.error("528, {}".format(str(e)))
            return 528, "{}".format(str(e))
        except BaseException as e:
            logging.error("530, {}".format(str(e)))
            return 530, "{}".format(str(e))

        return 200, "ok"

    def search(self, keyword, store_id=None, page=1, per_page=10):
        try:
            with self.conn.cursor() as cursor:
                query = '''
                    SELECT book_id, title, author, content, tags 
                    FROM book 
                    WHERE to_tsvector(title || ' ' || author || ' ' || content || ' ' || tags) @@ to_tsquery(%s);
                '''
                params = [keyword]

                if store_id:
                    query += ' AND book_id IN (SELECT jsonb_array_elements(books)->>\'book_id\' FROM store WHERE store_id = %s);'
                    params.append(store_id)

                cursor.execute(query, params)
                result = cursor.fetchall()

                # 分页
                start = (page - 1) * per_page
                end = start + per_page
                paginated_result = result[start:end]

        except psycopg2.Error as e:
            logging.error("530, {}".format(str(e)))
            return 530, "{}".format(str(e))
        except BaseException as e:
            logging.error("530, {}".format(str(e)))
            return 530, "{}".format(str(e))

        return 200, paginated_result

    def receive(self, user_id: str, order_id: str) -> (int, str):
        try:
            with self.conn.cursor() as cursor:
                # 检查订单状态
                cursor.execute('''
                    SELECT user_id, status 
                    FROM "order" 
                    WHERE order_id = %s AND status IN (1, 2, 3);
                ''', (order_id,))
                result = cursor.fetchone()
                if result is None:
                    return error.error_invalid_order_id(order_id)

                buyer_id, status = result

                if buyer_id != user_id:
                    return error.error_authorization_fail()

                if status == 1:
                    return error.error_books_not_deliver()
                if status == 3:
                    return error.error_books_repeat_receive()

                # 更新订单状态为已收货
                cursor.execute('''
                    UPDATE "order" 
                    SET status = 3 
                    WHERE order_id = %s;
                ''', (order_id,))

                self.conn.commit()

        except psycopg2.Error as e:
            logging.error("528, {}".format(str(e)))
            self.conn.rollback()
            return 528, "{}".format(str(e))
        except BaseException as e:
            logging.error("530, {}".format(str(e)))
            self.conn.rollback()
            return 530, "{}".format(str(e))

        return 200, "ok"


scheduler = BackgroundScheduler()
scheduler.add_job(Buyer().auto_cancel_order, 'interval', id='5_second_job', seconds=5)
scheduler.start()