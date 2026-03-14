# SIModel.py — Staff Inventory Model
import mysql.connector
from mysql.connector import Error


class InventoryModel:
    """Model for Staff inventory operations (read + stock transactions, no add product)."""

    def __init__(self):
        self.connection = None
        self.db_config = {
            'host': '127.0.0.1',
            'database': 'pyesatrak',
            'user': 'root',
            'password': ''
        }

    def connect(self):
        try:
            self.connection = mysql.connector.connect(**self.db_config)
            return self.connection.is_connected()
        except Error as e:
            print(f"Database Error: {e}")
            return False

    def get_all_products(self):
        return self.get_products_by_filter("1=1")

    def get_products_by_filter(self, where_clause):
        """Fetch products matching a WHERE clause. Uses real category column."""
        self.connect()
        try:
            cursor = self.connection.cursor(dictionary=True)
            query = (
                f"SELECT product_id, product_name, brand, model, "
                f"stock_quantity, status, "
                f"COALESCE(category, 'Other') AS category "
                f"FROM inventory WHERE {where_clause} ORDER BY product_id ASC"
            )
            cursor.execute(query)
            return cursor.fetchall()
        except Error as e:
            print(f"Error fetching products: {e}")
            return []
        finally:
            if self.connection:
                self.connection.close()

    def get_unique_brands(self) -> list:
        """Return sorted list of distinct brands in inventory."""
        self.connect()
        try:
            cursor = self.connection.cursor()
            cursor.execute(
                "SELECT DISTINCT brand FROM inventory "
                "WHERE brand IS NOT NULL AND brand != '' ORDER BY brand ASC")
            return [row[0] for row in cursor.fetchall()]
        except Exception as e:
            print(f"Error fetching brands: {e}")
            return []
        finally:
            if self.connection: self.connection.close()

    def get_unique_categories(self) -> list:
        """Return sorted list of distinct categories in inventory."""
        self.connect()
        try:
            cursor = self.connection.cursor()
            cursor.execute(
                "SELECT DISTINCT COALESCE(category, 'Other') AS category "
                "FROM inventory WHERE category IS NOT NULL AND category != '' "
                "ORDER BY category ASC")
            return [row[0] for row in cursor.fetchall()]
        except Exception as e:
            print(f"Error fetching categories: {e}")
            return []
        finally:
            if self.connection: self.connection.close()

    def get_defective_products_with_reason(self):
        """
        Fetches defect records from defective_items table.
        Each row = one unique defect report (defect_id, not product_id).
        """
        self.connect()
        try:
            cursor = self.connection.cursor(dictionary=True)
            query = """
                SELECT
                    d.defect_id,
                    i.product_id,
                    i.product_name,
                    i.brand,
                    i.model,
                    d.defective_qty,
                    CONCAT(d.defect_type,
                        CASE WHEN d.description IS NOT NULL AND d.description != ''
                             THEN CONCAT(' - ', d.description)
                             ELSE '' END
                    ) AS defect_reason,
                    DATE_FORMAT(d.reported_at, '%Y-%m-%d %H:%i') AS reported_at
                FROM defective_items d
                JOIN inventory i ON d.product_id = i.product_id
                ORDER BY d.reported_at DESC
            """
            cursor.execute(query)
            return cursor.fetchall()
        except Error as e:
            print(f"Error fetching defective products: {e}")
            return []
        finally:
            if self.connection:
                self.connection.close()

    def update_stock(self, product_id, quantity_change, transaction_type,
                     remarks, user_id, defect_type=None, defect_description=None):
        """
        Atomically updates stock, logs a transaction, and (for DEFECT)
        inserts a defective_items record.
        """
        self.connect()
        try:
            cursor = self.connection.cursor()
            self.connection.start_transaction()

            # 1. Update inventory
            cursor.execute("""
                UPDATE inventory
                SET stock_quantity = stock_quantity + %s,
                    status = CASE
                        WHEN (stock_quantity + %s) <= 0  THEN 'Out of Stock'
                        WHEN (stock_quantity + %s) <= 10 THEN 'Low Stock'
                        ELSE 'Available'
                    END,
                    updated_at = NOW()
                WHERE product_id = %s
            """, (quantity_change, quantity_change, quantity_change, product_id))

            # 2. Log transaction
            cursor.execute("""
                INSERT INTO stock_transactions
                    (product_id, transaction_type, quantity, remarks,
                     performed_by, transaction_date)
                VALUES (%s, %s, %s, %s, %s, NOW())
            """, (product_id, transaction_type, abs(quantity_change), remarks, user_id))

            # 3. If DEFECT — also insert into defective_items
            if transaction_type == 'DEFECT':
                d_type = defect_type or (remarks.split(' - ')[0] if ' - ' in remarks else remarks)
                d_desc = defect_description or (
                    remarks.split(' - ', 1)[1] if ' - ' in remarks else '')
                cursor.execute("""
                    INSERT INTO defective_items
                        (product_id, defective_qty, defect_type,
                         description, reported_by, reported_at)
                    VALUES (%s, %s, %s, %s, %s, NOW())
                """, (product_id, abs(quantity_change), d_type, d_desc, user_id))

            self.connection.commit()
            return True
        except Error as e:
            print(f"Error updating stock: {e}")
            self.connection.rollback()
            return False
        finally:
            if self.connection:
                self.connection.close()