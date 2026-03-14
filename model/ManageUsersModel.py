# ManageUsersModel.py
import mysql.connector
from mysql.connector import Error


class ManageUsersModel:
    def __init__(self):
        self.db_config = {
            'host': '127.0.0.1',
            'database': 'pyesatrak',
            'user': 'root',
            'password': ''
        }

    def connect(self):
        try:
            return mysql.connector.connect(**self.db_config)
        except Error as e:
            print(f"Database Error: {e}")
            return None

    def get_users(self, role="All", status="All", search=""):
        conn = self.connect()
        if not conn: return []
        try:
            cursor = conn.cursor(dictionary=True)

            # Using your specific schema: userFname, userLname
            query = """
                SELECT user_id, userFname, userLname, username, role, status 
                FROM users WHERE 1=1
            """
            params = []

            if role != "All":
                query += " AND role = %s"
                params.append(role)

            if status != "All":
                query += " AND status = %s"
                params.append(status)

            if search:
                query += " AND (userFname LIKE %s OR userLname LIKE %s OR username LIKE %s)"
                search_term = f"%{search}%"
                params.extend([search_term, search_term, search_term])

            query += " ORDER BY user_id DESC"

            cursor.execute(query, tuple(params))
            return cursor.fetchall()
        finally:
            if conn: conn.close()

    def get_user_by_id(self, uid):
        conn = self.connect()
        if not conn: return None
        try:
            cursor = conn.cursor(dictionary=True)
            cursor.execute("SELECT * FROM users WHERE user_id = %s", (uid,))
            return cursor.fetchone()
        finally:
            if conn: conn.close()

    def add_user(self, data):
        conn = self.connect()
        if not conn: return False
        try:
            cursor = conn.cursor()

            # Insert using your schema
            query = """
                INSERT INTO users (userFname, userLname, username, password, role, status)
                VALUES (%s, %s, %s, %s, %s, %s)
            """
            cursor.execute(query, (
                data['userFname'],
                data['userLname'],
                data['username'],
                data['password'],  # Store password as plaintext
                data['role'],
                data['status']
            ))
            conn.commit()  # <--- CRITICAL: Saves to DB

            # Optional: Log this action to activity_log
            self.log_activity(cursor, data.get('performed_by_id', 1), f"Added user: {data['username']}")
            conn.commit()

            return True
        except Error as e:
            print(f"Error adding user: {e}")
            return False
        finally:
            if conn: conn.close()

    def update_user(self, uid, data):
        conn = self.connect()
        if not conn: return False
        try:
            cursor = conn.cursor()

            fields = []
            values = []

            # Remove empty password field to prevent overwriting
            if 'password' in data and not data['password']:
                del data['password']

            for key, val in data.items():
                fields.append(f"{key} = %s")
                values.append(val)

            values.append(uid)
            query = f"UPDATE users SET {', '.join(fields)} WHERE user_id = %s"

            cursor.execute(query, tuple(values))
            conn.commit()  # <--- CRITICAL
            return True
        except Error as e:
            print(f"Error updating user: {e}")
            return False
        finally:
            if conn: conn.close()

    def delete_user(self, uid):
        conn = self.connect()
        if not conn: return False
        try:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM users WHERE user_id = %s", (uid,))
            conn.commit()  # <--- CRITICAL
            return True
        except Error as e:
            print(f"Error deleting user: {e}")
            return False
        finally:
            if conn: conn.close()

    def log_activity(self, cursor, user_id, description):
        """Helper to insert into activity_log table"""
        try:
            query = "INSERT INTO activity_log (user_id, activity_description, activity_time) VALUES (%s, %s, NOW())"
            cursor.execute(query, (user_id, description))
        except Error:
            pass  # Fail silently for logs