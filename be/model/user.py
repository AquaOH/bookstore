import jwt
import time
import logging
from be.model import error
from be.model import db_conn


# 编码 JWT
def jwt_encode(user_id: str, terminal: str) -> str:
    encoded = jwt.encode(
        {"user_id": user_id, "terminal": terminal, "timestamp": time.time()},
        key=user_id,
        algorithm="HS256",
    )
    return encoded


# 解码 JWT
def jwt_decode(encoded_token, user_id: str) -> str:
    decoded = jwt.decode(encoded_token, key=user_id, algorithms="HS256")
    return decoded


class User(db_conn.DBConn):
    token_lifetime: int = 3600  # token 有效期，3600 秒

    def __init__(self):
        db_conn.DBConn.__init__(self)

    def __check_token(self, user_id, db_token, token) -> bool:
        try:
            if db_token != token:
                return False
            jwt_text = jwt_decode(encoded_token=token, user_id=user_id)
            ts = jwt_text["timestamp"]
            if ts is not None:
                now = time.time()
                if self.token_lifetime > now - ts >= 0:
                    return True
        except jwt.exceptions.InvalidSignatureError as e:
            logging.error(str(e))
            return False

    def register(self, user_id: str, password: str):
        try:
            terminal = "terminal_{}".format(str(time.time()))
            token = jwt_encode(user_id, terminal)
            with self.conn.cursor() as cursor:
                cursor.execute("""
                    INSERT INTO "user" (user_id, password, balance, token, terminal)
                    VALUES (%s, %s, %s, %s, %s);
                """, (user_id, password, 0, token, terminal))
                self.conn.commit()
        except Exception as e:
            logging.error(str(e))
            self.conn.rollback()
            return error.error_exist_user_id(user_id)
        return 200, "ok"

    def check_token(self, user_id: str, token: str) -> (int, str):
        with self.conn.cursor() as cursor:
            cursor.execute("SELECT token FROM \"user\" WHERE user_id = %s;", (user_id,))
            result = cursor.fetchone()
            if result is None:
                return error.error_authorization_fail()
            db_token = result[0]
            if not self.__check_token(user_id, db_token, token):
                return error.error_authorization_fail()
        return 200, "ok"

    def check_password(self, user_id: str, password: str) -> (int, str):
        with self.conn.cursor() as cursor:
            cursor.execute("SELECT password FROM \"user\" WHERE user_id = %s;", (user_id,))
            result = cursor.fetchone()
            if result is None:
                return error.error_authorization_fail()
            if result[0] != password:
                return error.error_authorization_fail()
        return 200, "ok"

    def login(self, user_id: str, password: str, terminal: str) -> (int, str, str):
        token = ""
        try:
            code, message = self.check_password(user_id, password)
            if code != 200:
                return code, message, ""

            token = jwt_encode(user_id, terminal)
            with self.conn.cursor() as cursor:
                cursor.execute("""
                    UPDATE "user"
                    SET token = %s, terminal = %s
                    WHERE user_id = %s;
                """, (token, terminal, user_id))
                self.conn.commit()
        except BaseException as e:
            logging.error(str(e))
            self.conn.rollback()
            return 528, "{}".format(str(e)), ""
        return 200, "ok", token

    def logout(self, user_id: str, token: str) -> (int, str):
        try:
            code, message = self.check_token(user_id, token)
            if code != 200:
                return code, message
            terminal = "terminal_{}".format(str(time.time()))
            dummy_token = jwt_encode(user_id, terminal)
            with self.conn.cursor() as cursor:
                cursor.execute("""
                    UPDATE "user"
                    SET token = %s, terminal = %s
                    WHERE user_id = %s;
                """, (dummy_token, terminal, user_id))
                self.conn.commit()
        except BaseException as e:
            logging.error(str(e))
            self.conn.rollback()
            return 528, "{}".format(str(e))
        return 200, "ok"

    def unregister(self, user_id: str, password: str) -> (int, str):
        try:
            code, message = self.check_password(user_id, password)
            if code != 200:
                return code, message
            with self.conn.cursor() as cursor:
                cursor.execute("""
                    DELETE FROM "user"
                    WHERE user_id = %s AND password = %s;
                """, (user_id, password))
                self.conn.commit()
                if cursor.rowcount == 1:
                    return 200, "ok"
                else:
                    return error.error_authorization_fail()
        except BaseException as e:
            logging.error(str(e))
            self.conn.rollback()
            return 530, "{}".format(str(e))

    def change_password(self, user_id: str, old_password: str, new_password: str) -> (int, str):
        try:
            code, message = self.check_password(user_id, old_password)
            if code != 200:
                return code, message
            terminal = "terminal_{}".format(str(time.time()))
            token = jwt_encode(user_id, terminal)
            with self.conn.cursor() as cursor:
                cursor.execute("""
                    UPDATE "user"
                    SET password = %s, token = %s, terminal = %s
                    WHERE user_id = %s AND password = %s;
                """, (new_password, token, terminal, user_id, old_password))
                self.conn.commit()
                if cursor.rowcount == 0:
                    return error.error_authorization_fail()
        except BaseException as e:
            logging.error(str(e))
            self.conn.rollback()
            return 528, "{}".format(str(e))
        return 200, "ok"