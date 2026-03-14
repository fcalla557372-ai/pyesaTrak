# login_model.py
import mysql.connector
from mysql.connector import Error


class LoginModel:
    """Model for handling login logic"""

    def __init__(self):
        self.username = ""
        self.password = ""
        self.user_data = None
        self.connection = None

    def connect_to_database(self):
        """Establish connection to MySQL database"""
        try:
            self.connection = mysql.connector.connect(
                host='127.0.0.1',
                database='pyesatrak',
                user='root',
                password=''
            )
            if self.connection.is_connected():
                return True, "Connected to database"
        except Error as e:
            return False, f"Database connection error: {str(e)}"
        return False, "Unable to connect to database"

    def validate_credentials(self, username, password):
        """
        Validate user credentials against database with plain text password
        Returns: (bool, str, dict) - (is_valid, message, user_data)
        """
        if not username or not password:
            return False, "Please enter both username and password", None

        # Connect to database
        is_connected, message = self.connect_to_database()
        if not is_connected:
            return False, message, None

        try:
            cursor = self.connection.cursor(dictionary=True)

            # Query to get user by username
            query = """
                SELECT user_id, 
                       username, 
                       password, 
                       userFname, 
                       userMname,
                       userLname, 
                       role, 
                       status
                FROM users
                WHERE username = %s 
                  AND status = 'Active'
            """

            cursor.execute(query, (username,))
            user = cursor.fetchone()
            cursor.close()

            if user:
                stored_password = user['password']

                # Plain text password comparison
                if stored_password == password:
                    self.username = username
                    self.password = password
                    self.user_data = user

                    # Build full name
                    full_name = f"{user['userFname']} {user['userMname']} {user['userLname']}".strip()

                    # Log successful login to user_logins table
                    try:
                        cursor = self.connection.cursor()
                        login_query = """
                            INSERT INTO user_logins (user_id, login_time)
                            VALUES (%s, NOW())
                        """
                        cursor.execute(login_query, (user['user_id'],))
                        self.connection.commit()
                    except Error as log_error:
                        print(f"Warning: Failed to log login: {log_error}")
                        # Don't fail login if logging fails

                    return True, f"Welcome, {full_name}!", user
                else:
                    return False, "Invalid username or password", None
            else:
                return False, "Invalid username or password", None

        except Error as e:
            print(f"Database error during login: {e}")
            return False, f"Database error: {str(e)}", None
        finally:
            if self.connection and self.connection.is_connected():
                self.connection.close()

    def reset_credentials(self):
        """Clear stored credentials"""
        self.username = ""
        self.password = ""
        self.user_data = None

    def __del__(self):
        """Cleanup database connection"""
        if self.connection and self.connection.is_connected():
            self.connection.close()