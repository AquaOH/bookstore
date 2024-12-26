import uuid
import logging
from datetime import datetime, timedelta, timezone

import psycopg2

from be.model import db_conn
from be.model import error
from apscheduler.schedulers.background import BackgroundScheduler

class Buyer(db_conn.DBConn):
    def __init__(self):
        db_conn.DBConn.__init__(self)

    def new_order(self, user_id: str, store_id: str, id_and_count: [(str, int)]) -> (int, str, str):
        order_id = ""
        try:
            # 检查用户是否存在
            if not self.user_id_exist(user_id):
                return error.error_non_exist_user_id(user_id) + (order_id,)

            # 检查商店是否存在
            if not self.store_id_exist(store_id):
                return error.error_non_exist_store_id(store_id) + (order_id,)

            # 生成唯一的订单ID
            uid = "{}_{}_{}".format(user_id, store_id, str(uuid.uuid1()))
            total_price = 0

            # 遍历订单中的每本书
            for book_id, count in id_and_count:
                cursor = self.conn.cursor()

                # 查询商店的库存
                cursor.execute("""
                    SELECT elem->>'book_id' AS book_id, elem->>'stock_level' AS stock_level
                    FROM store, jsonb_array_elements(books) AS elem
                    WHERE store_id = %s AND elem->>'book_id' = %s
                """, (store_id, book_id))
                result = cursor.fetchone()

                # 检查库存是否存在
                if result is None or result["stock_level"] is None:
                    self.conn.rollback()
                    print("空的库存！！！！！！！！！")
                    return error.error_non_exist_book_id(book_id) + (order_id,)

                stock_level = int(result["stock_level"])

                # 检查库存是否足够
                if stock_level < count:
                    self.conn.rollback()
                    return error.error_stock_level_low(book_id) + (order_id,)

                # 查询书籍价格
                cursor.execute("SELECT price FROM book WHERE book_id = %s", (book_id,))
                result1 = cursor.fetchone()
                if result1 is None or result1["price"] is None:
                    self.conn.rollback()
                    print("空的价格！！！！！！！！！")
                    return error.error_non_exist_book_id(book_id) + (order_id,)

                price = result1["price"]

                # 更新库存
                cursor.execute("""
                    UPDATE store
                    SET books = jsonb_set(
                        books,
                        ('{' || idx-1 || ',stock_level}')::text[],
                        to_jsonb((sub.elem->>'stock_level')::int - %s)
                    )
                    FROM (
                        SELECT idx, elem
                        FROM store, jsonb_array_elements(books) WITH ORDINALITY arr(elem, idx)
                        WHERE store_id = %s AND elem->>'book_id' = %s
                    ) sub
                    WHERE store.store_id = %s
                """, (count, store_id, book_id, store_id))
                if cursor.rowcount == 0:
                    self.conn.rollback()
                    return error.error_stock_level_low(book_id) + (order_id,)

                # 记录订单详细信息
                cursor.execute("""
                    INSERT INTO order_detail (order_id, book_id, count, price)
                    VALUES (%s, %s, %s, %s)
                """, (uid, book_id, count, price))
                total_price += price * count

            # 插入订单信息
            now_time = datetime.now(timezone.utc)
            cursor.execute("""
                INSERT INTO "order" (order_id, store_id, user_id, create_time, price, status)
                VALUES (%s, %s, %s, %s, %s, %s)
            """, (uid, store_id, user_id, now_time, total_price, 0))
            self.conn.commit()
            order_id = uid

        except Exception as e:
            self.conn.rollback()
            logging.error(f"Error in new_order: {str(e)}")
            return 528, "{}".format(str(e)), ""

        return 200, "ok", order_id

    def payment(self, user_id: str, password: str, order_id: str) -> (int, str):
        try:
            # 使用 DictCursor 将查询结果转换为字典
            cursor = self.conn.cursor(cursor_factory=psycopg2.extras.DictCursor)

            # 查询订单信息
            cursor.execute("""
                SELECT * FROM "order"
                WHERE order_id = %s AND status = '0'
            """, (order_id,))
            order = cursor.fetchone()
            if order is None:
                self.conn.rollback()
                logging.error(f"订单不存在或状态无效: {order_id}")
                return error.error_invalid_order_id(order_id)

            buyer_id = order["user_id"]  # 通过字段名访问
            store_id = order["store_id"]  # 通过字段名访问
            total_price = order["price"]  # 通过字段名访问

            # 检查用户权限
            if buyer_id != user_id:
                self.conn.rollback()
                logging.error(f"用户权限不足: {user_id}")
                return error.error_authorization_fail()

            # 查询用户信息
            cursor.execute("""
                SELECT * FROM "user"
                WHERE user_id = %s
            """, (buyer_id,))
            user = cursor.fetchone()
            if user is None:
                self.conn.rollback()
                logging.error(f"用户不存在: {buyer_id}")
                return error.error_non_exist_user_id(buyer_id)

            balance = user["balance"]  # 通过字段名访问
            if password != user["password"]:  # 通过字段名访问
                self.conn.rollback()
                logging.error(f"密码错误: {user_id}")
                return error.error_authorization_fail()

            # 检查用户余额
            if balance < total_price:
                self.conn.rollback()
                logging.error(f"余额不足: {buyer_id}, 余额: {balance}, 订单金额: {total_price}")
                return error.error_not_sufficient_funds(order_id)

            # 查询商店信息
            cursor.execute("""
                SELECT * FROM "store"
                WHERE store_id = %s
            """, (store_id,))
            store = cursor.fetchone()
            if store is None:
                self.conn.rollback()
                logging.error(f"商店不存在: {store_id}")
                return error.error_non_exist_store_id(store_id)

            seller_id = store["user_id"]  # 通过字段名访问

            # 检查卖家是否存在
            cursor.execute("""
                SELECT * FROM "user"
                WHERE user_id = %s
            """, (seller_id,))
            if cursor.fetchone() is None:
                self.conn.rollback()
                logging.error(f"卖家不存在: {seller_id}")
                return error.error_non_exist_user_id(seller_id)

            # 扣款
            cursor.execute("""
                UPDATE "user"
                SET balance = balance - %s
                WHERE user_id = %s AND balance >= %s
            """, (total_price, buyer_id, total_price))
            if cursor.rowcount == 0:
                self.conn.rollback()
                logging.error(f"扣款失败: {buyer_id}, 余额: {balance}, 订单金额: {total_price}")
                return error.error_not_sufficient_funds(order_id)

            # 付款给卖家
            cursor.execute("""
                UPDATE "user"
                SET balance = balance + %s
                WHERE user_id = %s
            """, (total_price, seller_id))
            if cursor.rowcount == 0:
                self.conn.rollback()
                logging.error(f"付款给卖家失败: {seller_id}")
                return error.error_non_exist_user_id(seller_id)

            # 更新订单状态
            cursor.execute("""
                UPDATE "order"
                SET status = '1'
                WHERE order_id = %s AND status = '0'
            """, (order_id,))
            if cursor.rowcount == 0:
                self.conn.rollback()
                logging.error(f"更新订单状态失败: {order_id}")
                return error.error_invalid_order_id(order_id)

            # 提交事务
            self.conn.commit()
            logging.info(f"支付成功: 订单 {order_id}, 用户 {buyer_id}, 金额 {total_price}")
        except Exception as e:
            self.conn.rollback()
            logging.error(f"支付异常: {str(e)}")
            return 528, "{}".format(str(e))

        return 200, "ok"

    def add_funds(self, user_id: str, password: str, add_value: int) -> (int, str):
        try:
            self.conn.cursor_factory = psycopg2.extras.DictCursor  # 配置游标返回字典
            cursor = self.conn.cursor()
            cursor.execute("SELECT * FROM \"user\" WHERE user_id = %s", (user_id,))
            result = cursor.fetchone()
            if result is None:
                self.conn.rollback()
                return error.error_authorization_fail()

            # 使用字段名访问查询结果
            if result["password"] != password:
                self.conn.rollback()
                return error.error_authorization_fail()

            cursor.execute("""
                UPDATE "user"
                SET balance = balance + %s
                WHERE user_id = %s
            """, (add_value, user_id))

            if cursor.rowcount == 0:
                self.conn.rollback()
                return error.error_non_exist_user_id(user_id)

            self.conn.commit()
            return 200, "ok"
        except Exception as e:
            self.conn.rollback()
            logging.error(f"Error in add_funds: {str(e)}")
            return 528, "{}".format(str(e))

    def cancel_order(self, user_id: str, order_id: str) -> (int, str):
        try:
            cursor = self.conn.cursor()
            cursor.execute("""
                SELECT * FROM "order"
                WHERE order_id = %s AND status = 0
            """, (order_id,))
            result = cursor.fetchone()
            if result:
                buyer_id = result["user_id"]
                if buyer_id != user_id:
                    self.conn.rollback()
                    return error.error_authorization_fail()
                store_id = result["store_id"]
                price = result["price"]

                cursor.execute("""
                    DELETE FROM "order"
                    WHERE order_id = %s AND status = 0
                """, (order_id,))
                if cursor.rowcount == 0:
                    self.conn.rollback()
                    return error.error_invalid_order_id(order_id)

                cursor.execute("""
                    SELECT book_id, count FROM order_detail
                    WHERE order_id = %s
                """, (order_id,))
                order_details = cursor.fetchall()
                for detail in order_details:
                    book_id = detail["book_id"]
                    count = detail["count"]
                    cursor.execute("""
                        UPDATE store
                        SET books = jsonb_set(
                            books,
                            ('{' || idx-1 || ',stock_level}')::text[],
                            to_jsonb((books->>idx-1->>'stock_level')::int + %s)
                        )
                        FROM (
                            SELECT idx
                            FROM store, jsonb_array_elements(books) WITH ORDINALITY arr(elem, idx)
                            WHERE store_id = %s AND elem->>'book_id' = %s
                        ) sub
                        WHERE store.store_id = %s
                    """, (count, store_id, book_id, store_id))
                    if cursor.rowcount == 0:
                        self.conn.rollback()
                        return error.error_stock_level_low(book_id)

                cursor.execute("""
                    INSERT INTO "order" (order_id, user_id, store_id, price, status)
                    VALUES (%s, %s, %s, %s, 4)
                """, (order_id, user_id, store_id, price))
                self.conn.commit()
            else:
                cursor.execute("""
                    SELECT * FROM "order"
                    WHERE order_id = %s AND status IN (1, 2, 3)
                """, (order_id,))
                result = cursor.fetchone()
                if result:
                    buyer_id = result["user_id"]
                    if buyer_id != user_id:
                        self.conn.rollback()
                        return error.error_authorization_fail()
                    store_id = result["store_id"]
                    price = result["price"]

                    cursor.execute("""
                        UPDATE "user"
                        SET balance = balance - %s
                        WHERE user_id = (SELECT user_id FROM store WHERE store_id = %s)
                    """, (price, store_id))
                    if cursor.rowcount == 0:
                        self.conn.rollback()
                        return error.error_non_exist_user_id(buyer_id)

                    cursor.execute("""
                        UPDATE "user"
                        SET balance = balance + %s
                        WHERE user_id = %s
                    """, (price, buyer_id))
                    if cursor.rowcount == 0:
                        self.conn.rollback()
                        return error.error_non_exist_user_id(buyer_id)

                    cursor.execute("""
                        DELETE FROM "order"
                        WHERE order_id = %s AND status IN (1, 2, 3)
                    """, (order_id,))
                    if cursor.rowcount == 0:
                        self.conn.rollback()
                        return error.error_invalid_order_id(order_id)

                    cursor.execute("""
                        INSERT INTO "order" (order_id, user_id, store_id, price, status)
                        VALUES (%s, %s, %s, %s, 4)
                    """, (order_id, user_id, store_id, price))
                    self.conn.commit()
                else:
                    self.conn.rollback()
                    return error.error_invalid_order_id(order_id)
        except Exception as e:
            self.conn.rollback()
            return 528, "{}".format(str(e))
        return 200, "ok"

    def check_hist_order(self, user_id: str):
        try:
            if not self.user_id_exist(user_id):
                return error.error_non_exist_user_id(user_id)
            ans = []
            cursor = self.conn.cursor()
            cursor.execute("""
                SELECT * FROM "order"
                WHERE user_id = %s AND status = 0
            """, (user_id,))
            unpaid_orders = cursor.fetchall()
            for order in unpaid_orders:
                tmp_details = []
                order_id = order["order_id"]
                cursor.execute("""
                    SELECT book_id, count, price FROM order_detail
                    WHERE order_id = %s
                """, (order_id,))
                order_details = cursor.fetchall()
                for detail in order_details:
                    tmp_details.append({
                        "book_id": detail["book_id"],
                        "count": detail["count"],
                        "price": detail["price"]
                    })
                ans.append({
                    "status": "unpaid",
                    "order_id": order_id,
                    "buyer_id": order["user_id"],
                    "store_id": order["store_id"],
                    "total_price": order["price"],
                    "details": tmp_details
                })

            cursor.execute("""
                SELECT * FROM "order"
                WHERE user_id = %s AND status IN (1, 2, 3)
            """, (user_id,))
            paid_orders = cursor.fetchall()
            books_status_list = ["unsent", "sent but not received", "received"]
            for order in paid_orders:
                tmp_details = []
                order_id = order["order_id"]
                cursor.execute("""
                    SELECT book_id, count, price FROM order_detail
                    WHERE order_id = %s
                """, (order_id,))
                order_details = cursor.fetchall()
                for detail in order_details:
                    tmp_details.append({
                        "book_id": detail["book_id"],
                        "count": detail["count"],
                        "price": detail["price"]
                    })
                ans.append({
                    "order_id": order_id,
                    "buyer_id": order["user_id"],
                    "store_id": order["store_id"],
                    "total_price": order["price"],
                    "status": books_status_list[order["status"] - 1],
                    "details": tmp_details
                })

            cursor.execute("""
                SELECT * FROM "order"
                WHERE user_id = %s AND status = 4
            """, (user_id,))
            cancelled_orders = cursor.fetchall()
            for order in cancelled_orders:
                tmp_details = []
                order_id = order["order_id"]
                cursor.execute("""
                    SELECT book_id, count, price FROM order_detail
                    WHERE order_id = %s
                """, (order_id,))
                order_details = cursor.fetchall()
                for detail in order_details:
                    tmp_details.append({
                        "book_id": detail["book_id"],
                        "count": detail["count"],
                        "price": detail["price"]
                    })
                ans.append({
                    "status": "cancelled",
                    "order_id": order_id,
                    "buyer_id": order["user_id"],
                    "store_id": order["store_id"],
                    "total_price": order["price"],
                    "details": tmp_details
                })

        except Exception as e:
            self.conn.rollback()
            return 528, "{}".format(str(e)), None
        if not ans:
            return 200, "ok", "No orders found"
        else:
            return 200, "ok", ans

    def auto_cancel_order(self) -> (int, str):
        try:
            wait = 20  # 超时时间（秒）
            current_time = datetime.now(timezone.utc)
            interval = current_time - timedelta(seconds=wait)
            cursor = self.conn.cursor()

            # 查询超时未支付的订单
            cursor.execute("""
                SELECT * FROM "order"
                WHERE create_time <= %s AND status = 0
            """, (interval,))
            orders_to_cancel = cursor.fetchall()

            # 遍历需要取消的订单
            for order in orders_to_cancel:
                order_id = order["order_id"]
                store_id = order["store_id"]

                # 恢复库存
                cursor.execute("""
                    SELECT book_id, count FROM order_detail
                    WHERE order_id = %s
                """, (order_id,))
                order_details = cursor.fetchall()
                for detail in order_details:
                    book_id = detail["book_id"]
                    count = detail["count"]
                    cursor.execute("""
                        UPDATE store
                        SET books = jsonb_set(
                            books,
                            ('{' || idx-1 || ',stock_level}')::text[],
                            to_jsonb((elem->>'stock_level')::int + %s)
                        )
                        FROM (
                            SELECT idx, elem
                            FROM store, jsonb_array_elements(books) WITH ORDINALITY arr(elem, idx)
                            WHERE store_id = %s AND elem->>'book_id' = %s
                        ) sub
                        WHERE store.store_id = %s
                    """, (count, store_id, book_id, store_id))
                    if cursor.rowcount == 0:
                        self.conn.rollback()
                        return error.error_stock_level_low(book_id)

                # 更新订单状态为已取消（状态 4）
                cursor.execute("""
                    UPDATE "order"
                    SET status = 4
                    WHERE order_id = %s AND status = 0
                """, (order_id,))
                if cursor.rowcount == 0:
                    self.conn.rollback()
                    return error.error_invalid_order_id(order_id)

            self.conn.commit()
        except Exception as e:
            self.conn.rollback()
            return 528, "{}".format(str(e))
        return 200, "ok"

    def search(self, keyword: str, store_id: str = None, page: int = 1, per_page: int = 10) -> (int, str):
        try:
            cursor = self.conn.cursor()
            query = """
                SELECT * FROM book
                WHERE to_tsvector('english', book_intro || ' ' || content) @@ to_tsquery('english', %s)
            """
            params = [keyword]
            if store_id:
                query += " AND book_id IN (SELECT jsonb_array_elements(books)->>'book_id' FROM store WHERE store_id = %s)"
                params.append(store_id)

            query += " OFFSET %s LIMIT %s"
            params.extend([(page - 1) * per_page, per_page])

            cursor.execute(query, params)
            result = cursor.fetchall()
            return 200, result
        except Exception as e:
            self.conn.rollback()
            return 530, "{}".format(str(e))

    def receive(self, user_id: str, order_id: str) -> (int, str):
        try:
            cursor = self.conn.cursor()
            cursor.execute("""
                SELECT * FROM "order"
                WHERE order_id = %s AND status IN (1, 2, 3)
            """, (order_id,))
            result = cursor.fetchone()
            if result is None:
                self.conn.rollback()
                return error.error_invalid_order_id(order_id)
            buyer_id = result["user_id"]
            paid_status = result["status"]

            if buyer_id != user_id:
                self.conn.rollback()
                return error.error_authorization_fail()
            if paid_status == 1:
                self.conn.rollback()
                return error.error_books_not_deliver()
            if paid_status == 3:
                self.conn.rollback()
                return error.error_books_repeat_receive()

            cursor.execute("""
                UPDATE "order"
                SET status = 3
                WHERE order_id = %s
            """, (order_id,))
            self.conn.commit()
        except Exception as e:
            self.conn.rollback()
            return 528, "{}".format(str(e))
        return 200, "ok"


scheduler = BackgroundScheduler()
scheduler.add_job(Buyer().auto_cancel_order, 'interval', id='5_second_job', seconds=5)
scheduler.start()