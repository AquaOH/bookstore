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
        """
        创建新订单。

        :param user_id: 用户ID
        :param store_id: 商店ID
        :param id_and_count: 书籍ID和数量的列表，格式为 [(book_id, count), ...]
        :return: 状态码, 消息, 订单ID
        """
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
        """
        支付订单。

        :param user_id: 用户ID
        :param password: 用户密码
        :param order_id: 订单ID
        :return: 状态码, 消息
        """
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
        """
        为用户增加余额。

        :param user_id: 用户ID
        :param password: 用户密码
        :param add_value: 增加的金额
        :return: 状态码, 消息
        """
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
        """
        取消订单。

        :param user_id: 用户ID
        :param order_id: 订单ID
        :return: 状态码, 消息
        """
        try:
            # 使用 DictCursor 将查询结果转换为字典
            cursor = self.conn.cursor(cursor_factory=psycopg2.extras.DictCursor)

            # 查询订单信息（状态为 0）
            cursor.execute("""
                SELECT * FROM "order"
                WHERE order_id = %s AND status = '0'
            """, (order_id,))
            order = cursor.fetchone()

            if order:
                # 检查用户权限
                buyer_id = order["user_id"]
                if buyer_id != user_id:
                    self.conn.rollback()
                    logging.error(f"用户权限不足: {user_id}")
                    return error.error_authorization_fail()

                store_id = order["store_id"]
                price = order["price"]

                # 删除订单
                cursor.execute("""
                    DELETE FROM "order"
                    WHERE order_id = %s AND status = '0'
                """, (order_id,))
                if cursor.rowcount == 0:
                    self.conn.rollback()
                    logging.error(f"删除订单失败: {order_id}")
                    return error.error_invalid_order_id(order_id)
            else:
                # 查询订单信息（状态为 1、2、3）
                cursor.execute("""
                    SELECT * FROM "order"
                    WHERE order_id = %s AND status IN ('1', '2', '3')
                """, (order_id,))
                order = cursor.fetchone()

                if order:
                    # 检查用户权限
                    buyer_id = order["user_id"]
                    if buyer_id != user_id:
                        self.conn.rollback()
                        logging.error(f"用户权限不足: {user_id}")
                        return error.error_authorization_fail()

                    store_id = order["store_id"]
                    price = order["price"]

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

                    seller_id = store["user_id"]

                    # 扣减卖家余额
                    cursor.execute("""
                        UPDATE "user"
                        SET balance = balance - %s
                        WHERE user_id = %s
                    """, (price, seller_id))
                    if cursor.rowcount == 0:
                        self.conn.rollback()
                        logging.error(f"扣减卖家余额失败: {seller_id}")
                        return error.error_non_exist_user_id(seller_id)

                    # 增加买家余额
                    cursor.execute("""
                        UPDATE "user"
                        SET balance = balance + %s
                        WHERE user_id = %s
                    """, (price, buyer_id))
                    if cursor.rowcount == 0:
                        self.conn.rollback()
                        logging.error(f"增加买家余额失败: {buyer_id}")
                        return error.error_non_exist_user_id(buyer_id)

                    # 删除订单
                    cursor.execute("""
                        DELETE FROM "order"
                        WHERE order_id = %s AND status IN ('1', '2', '3')
                    """, (order_id,))
                    if cursor.rowcount == 0:
                        self.conn.rollback()
                        logging.error(f"删除订单失败: {order_id}")
                        return error.error_invalid_order_id(order_id)
                else:
                    self.conn.rollback()
                    logging.error(f"订单不存在: {order_id}")
                    return error.error_invalid_order_id(order_id)

            # 恢复库存
            cursor.execute("""
                SELECT book_id, count FROM order_detail
                WHERE order_id = %s
            """, (order_id,))
            order_details = cursor.fetchall()

            for detail in order_details:
                book_id = detail["book_id"]
                count = detail["count"]

                # 更新库存
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
                    logging.error(f"恢复库存失败: {book_id}")
                    return error.error_stock_level_low(book_id)

            # 插入取消订单记录
            cursor.execute("""
                INSERT INTO "order" (order_id, user_id, store_id, price, status)
                VALUES (%s, %s, %s, %s, '4')
            """, (order_id, user_id, store_id, price))

            # 提交事务
            self.conn.commit()
            logging.info(f"取消订单成功: 订单 {order_id}, 用户 {user_id}")
        except Exception as e:
            self.conn.rollback()
            logging.error(f"取消订单异常: {str(e)}")
            return 528, "{}".format(str(e))

        return 200, "ok"

    def check_hist_order(self, user_id: str):
        """
        查询用户的历史订单。

        :param user_id: 用户ID
        :return: 状态码, 消息, 订单列表
        """
        try:
            # 使用 DictCursor 将查询结果转换为字典
            cursor = self.conn.cursor(cursor_factory=psycopg2.extras.DictCursor)

            # 检查用户是否存在
            if not self.user_id_exist(user_id):
                return error.error_non_exist_user_id(user_id), None

            ans = []

            # 查询未支付订单
            cursor.execute("""
                SELECT * FROM "order"
                WHERE user_id = %s AND status = '0'
            """, (user_id,))
            unpaid_orders = cursor.fetchall()

            for order in unpaid_orders:
                tmp_details = []
                order_id = order["order_id"]

                # 查询订单详情
                cursor.execute("""
                    SELECT * FROM order_detail
                    WHERE order_id = %s
                """, (order_id,))
                order_details = cursor.fetchall()

                if not order_details:
                    return error.error_invalid_order_id(order_id), None

                for detail in order_details:
                    tmp_details.append({
                        "book_id": detail["book_id"],
                        "count": detail["count"],
                        "price": float(detail["price"])  # 将 Decimal 转换为 float
                    })

                ans.append({
                    "status": "unpaid",
                    "order_id": order_id,
                    "buyer_id": order["user_id"],
                    "store_id": order["store_id"],
                    "total_price": float(order["price"]),  # 将 Decimal 转换为 float
                    "details": tmp_details
                })

            # 查询已支付、已发货、已收货订单
            books_status_list = ["unsent", "sent but not received", "received"]
            cursor.execute("""
                SELECT * FROM "order"
                WHERE user_id = %s AND status IN ('1', '2', '3')
            """, (user_id,))
            paid_orders = cursor.fetchall()

            for order in paid_orders:
                tmp_details = []
                order_id = order["order_id"]

                # 查询订单详情
                cursor.execute("""
                    SELECT * FROM order_detail
                    WHERE order_id = %s
                """, (order_id,))
                order_details = cursor.fetchall()

                if not order_details:
                    return error.error_invalid_order_id(order_id), None

                for detail in order_details:
                    tmp_details.append({
                        "book_id": detail["book_id"],
                        "count": detail["count"],
                        "price": float(detail["price"])  # 将 Decimal 转换为 float
                    })

                ans.append({
                    "status": books_status_list[int(order["status"]) - 1],
                    "order_id": order_id,
                    "buyer_id": order["user_id"],
                    "store_id": order["store_id"],
                    "total_price": float(order["price"]),  # 将 Decimal 转换为 float
                    "details": tmp_details
                })

            # 查询已取消订单
            cursor.execute("""
                SELECT * FROM "order"
                WHERE user_id = %s AND status = '4'
            """, (user_id,))
            cancelled_orders = cursor.fetchall()

            for order in cancelled_orders:
                tmp_details = []
                order_id = order["order_id"]

                # 查询订单详情
                cursor.execute("""
                    SELECT * FROM order_detail
                    WHERE order_id = %s
                """, (order_id,))
                order_details = cursor.fetchall()

                if not order_details:
                    return error.error_invalid_order_id(order_id), None

                for detail in order_details:
                    tmp_details.append({
                        "book_id": detail["book_id"],
                        "count": detail["count"],
                        "price": float(detail["price"])  # 将 Decimal 转换为 float
                    })

                ans.append({
                    "status": "cancelled",
                    "order_id": order_id,
                    "buyer_id": order["user_id"],
                    "store_id": order["store_id"],
                    "total_price": float(order["price"]),  # 将 Decimal 转换为 float
                    "details": tmp_details
                })

            # 提交事务
            self.conn.commit()

            if not ans:
                return 200, "ok", "No orders found"
            else:
                return 200, "ok", ans

        except Exception as e:
            self.conn.rollback()
            logging.error(f"查询历史订单异常: {str(e)}")
            return 528, "{}".format(str(e)), None

    def auto_cancel_order(self) -> (int, str):
        """
        自动取消超时未支付的订单。

        :return: 状态码, 消息
        """
        try:
            wait = 20  # 超时时间（秒）
            current_time = datetime.now(timezone.utc)  # 使用 UTC 时间
            interval = current_time - timedelta(seconds=wait)  # 计算超时时间点

            # 使用 DictCursor 将查询结果转换为字典
            cursor = self.conn.cursor(cursor_factory=psycopg2.extras.DictCursor)

            # 查询超时未支付的订单
            cursor.execute("""
                SELECT * FROM "order"
                WHERE create_time <= %s AND status = '0'
            """, (interval,))
            orders_to_cancel = cursor.fetchall()

            for order in orders_to_cancel:
                order_id = order["order_id"]
                user_id = order["user_id"]
                store_id = order["store_id"]
                price = order["price"]

                # 删除订单
                cursor.execute("""
                    DELETE FROM "order"
                    WHERE order_id = %s AND status = '0'
                """, (order_id,))
                if cursor.rowcount == 0:
                    self.conn.rollback()
                    logging.error(f"删除订单失败: {order_id}")
                    return error.error_invalid_order_id(order_id)

                # 查询订单详情
                cursor.execute("""
                    SELECT book_id, count FROM order_detail
                    WHERE order_id = %s
                """, (order_id,))
                order_details = cursor.fetchall()

                for detail in order_details:
                    book_id = detail["book_id"]
                    count = detail["count"]

                    # 更新库存
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
                        logging.error(f"恢复库存失败: 书籍 {book_id}, 商店 {store_id}")
                        return error.error_stock_level_low(book_id)

                # 插入取消订单记录
                cursor.execute("""
                    INSERT INTO "order" (order_id, user_id, store_id, price, status)
                    VALUES (%s, %s, %s, %s, '4')
                """, (order_id, user_id, store_id, price))

            # 提交事务
            self.conn.commit()
            logging.info(f"自动取消订单成功: 共取消 {len(orders_to_cancel)} 个订单")
        except Exception as e:
            self.conn.rollback()
            logging.error(f"自动取消订单异常: {str(e)}")
            return 528, "{}".format(str(e))

        return 200, "ok"

    def is_order_cancelled(self, order_id: str) -> (int, str):
        """
        检查订单是否已取消。

        :param order_id: 订单ID
        :return: 状态码, 消息
        """
        try:
            # 使用 DictCursor 将查询结果转换为字典
            cursor = self.conn.cursor(cursor_factory=psycopg2.extras.DictCursor)

            # 查询取消订单
            cursor.execute("""
                SELECT * FROM "order"
                WHERE order_id = %s AND status = '4'
            """, (order_id,))
            result = cursor.fetchone()

            if result is None:
                logging.error(f"订单未取消: {order_id}")
                return error.error_auto_cancel_fail(order_id)
            else:
                logging.info(f"订单已取消: {order_id}")
                return 200, "ok"
        except Exception as e:
            logging.error(f"查询订单取消状态异常: {str(e)}")
            return 528, "{}".format(str(e))

    def search(self, keyword: str, store_id: str = None, page: int = 1, per_page: int = 10) -> (int, str):
        """
        根据关键字搜索书籍，支持分页和指定商店。

        :param keyword: 搜索关键字
        :param store_id: 商店ID（可选）
        :param page: 页码（从1开始）
        :param per_page: 每页显示的书籍数量
        :return: 状态码, 消息, 搜索结果
        """
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
        """
        确认收货。

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
                WHERE order_id = %s AND status IN ('1', '2', '3')
            """, (order_id,))
            result = cursor.fetchone()
            if result is None:
                self.conn.rollback()
                logging.error(f"订单不存在或状态无效: {order_id}")
                return error.error_invalid_order_id(order_id)

            buyer_id = result["user_id"]  # 通过字段名访问
            paid_status = result["status"]  # 通过字段名访问

            # 检查用户权限
            if buyer_id != user_id:
                self.conn.rollback()
                logging.error(f"用户权限不足: {user_id}")
                return error.error_authorization_fail()

            # 检查订单状态
            if paid_status == '1':
                self.conn.rollback()
                logging.error(f"订单未发货: {order_id}")
                return error.error_books_not_deliver()
            if paid_status == '3':
                self.conn.rollback()
                logging.error(f"订单已收货: {order_id}")
                return error.error_books_repeat_receive()

            # 更新订单状态为已收货（状态 3）
            cursor.execute("""
                UPDATE "order"
                SET status = '3'
                WHERE order_id = %s
            """, (order_id,))
            if cursor.rowcount == 0:
                self.conn.rollback()
                logging.error(f"更新订单状态失败: {order_id}")
                return error.error_invalid_order_id(order_id)

            # 提交事务
            self.conn.commit()
            logging.info(f"收货成功: 订单 {order_id}, 用户 {user_id}")
        except Exception as e:
            self.conn.rollback()
            logging.error(f"收货异常: {str(e)}")
            return 528, "{}".format(str(e))

        return 200, "ok"


scheduler = BackgroundScheduler()
scheduler.add_job(Buyer().auto_cancel_order, 'interval', id='5_second_job', seconds=5)
scheduler.start()