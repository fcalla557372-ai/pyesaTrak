# Ainventory_model.py
import mysql.connector
from mysql.connector import Error


class ProductDetailsModel:
    # ── Shared category SQL expression ───────────────────────────────────────
    # Used in SELECT queries to derive a readable category from product_name.
    # Add new WHEN clauses here to support future product types automatically.
    CATEGORY_SQL = """
        CASE
            WHEN LOWER(product_name) LIKE '%processor%'
              OR LOWER(product_name) LIKE '%ryzen%'
              OR LOWER(product_name) LIKE '%core i%'
              OR LOWER(product_name) LIKE '%core ultra%'
            THEN 'Processors (CPU)'
            WHEN LOWER(product_name) LIKE '%graphics%'
              OR LOWER(product_name) LIKE '%rtx%'
              OR LOWER(product_name) LIKE '% rx %'
              OR LOWER(product_name) LIKE '%radeon%'
            THEN 'Graphics Cards (GPU)'
            WHEN LOWER(product_name) LIKE '%motherboard%'
            THEN 'Motherboards'
            WHEN LOWER(product_name) LIKE '%ram%'
              OR LOWER(product_name) LIKE '%ddr%'
            THEN 'RAM'
            WHEN LOWER(product_name) LIKE '%ssd%'
              OR LOWER(product_name) LIKE '%hdd%'
              OR LOWER(product_name) LIKE '%nvme%'
            THEN 'Storage'
            WHEN LOWER(product_name) LIKE '%cooler%'
              OR LOWER(product_name) LIKE '%cooling%'
              OR LOWER(product_name) LIKE '%aio%'
            THEN 'Cooling'
            WHEN LOWER(product_name) LIKE '%case%'
              OR LOWER(product_name) LIKE '%chassis%'
            THEN 'Cases'
            WHEN LOWER(product_name) LIKE '%psu%'
              OR LOWER(product_name) LIKE '%power supply%'
            THEN 'Power Supply'
            WHEN LOWER(product_name) LIKE '%keyboard%'
            THEN 'Keyboards'
            WHEN LOWER(product_name) LIKE '%mouse%'
            THEN 'Mouse'
            WHEN LOWER(product_name) LIKE '%monitor%'
              OR LOWER(product_name) LIKE '%display%'
            THEN 'Monitors'
            ELSE 'Other'
        END
    """

    @staticmethod
    def _derive_category(product_name: str) -> str:
        """Derive a category string from a product name. Used when adding new products."""
        n = product_name.lower()
        if any(k in n for k in ['processor', 'ryzen', 'core i', 'core ultra']):
            return 'Processors (CPU)'
        if any(k in n for k in ['graphics', 'rtx', ' rx ', 'radeon']):
            return 'Graphics Cards (GPU)'
        if 'motherboard' in n:
            return 'Motherboards'
        if any(k in n for k in ['ram', 'ddr']):
            return 'RAM'
        if any(k in n for k in ['ssd', 'hdd', 'nvme']):
            return 'Storage'
        if any(k in n for k in ['cooler', 'cooling', 'aio', 'fan']):
            return 'Cooling'
        if any(k in n for k in ['case', 'chassis']):
            return 'Cases'
        if any(k in n for k in ['psu', 'power supply', 'watt']):
            return 'Power Supply'
        if 'keyboard' in n:
            return 'Keyboards'
        if 'mouse' in n:
            return 'Mouse'
        if any(k in n for k in ['monitor', 'display']):
            return 'Monitors'
        return 'Other'

    def __init__(self):
        self.connection = None

    def connect_to_database(self):
        try:
            self.connection = mysql.connector.connect(
                host='127.0.0.1',
                database='pyesatrak',
                user='root',
                password=''
            )
            if self.connection.is_connected():
                return True, "Connected"
        except Error as e:
            return False, str(e)
        return False, "Failed"

    def get_all_products(self):
        """Fetch all products (Default view)"""
        # Equivalent to filtering where 1=1 (always true)
        return self.get_products_by_filter("1=1")

    def get_products_by_filter(self, where_clause):
        """
        Fetch products based on a custom SQL WHERE clause.
        Uses the real `category` column — no CASE WHEN computation needed.
        """
        self.connect_to_database()
        try:
            cursor = self.connection.cursor(dictionary=True)
            query = (
                f"SELECT product_id, product_name, brand, model, stock_quantity, status, "
                f"COALESCE(category, 'Other') AS category, "
                f"DATE_FORMAT(created_at, '%Y-%m-%d %H:%i') AS created_at "
                f"FROM inventory WHERE {where_clause} ORDER BY product_id ASC"
            )
            cursor.execute(query)
            return cursor.fetchall()
        except Error as e:
            print(f"Error fetching filtered products: {e}")
            return []
        finally:
            if self.connection and self.connection.is_connected():
                self.connection.close()

    # --- DEFECTIVE ITEMS: query from defective_items table ---
    def get_defective_products_with_reason(self):
        """
        Fetches defect records from the defective_items table.
        Each row has its own unique defect_id and shows only the
        reported defective_qty — NOT the remaining inventory stock.
        """
        self.connect_to_database()
        try:
            cursor = self.connection.cursor(dictionary=True)
            query = """
                SELECT 
                    d.defect_id,
                    i.product_id,
                    i.product_name,
                    i.brand,
                    i.model,
                    (CASE
                        WHEN LOWER(i.product_name) LIKE '%processor%' OR LOWER(i.product_name) LIKE '%ryzen%' OR LOWER(i.product_name) LIKE '%core i%' THEN 'Processors (CPU)'
                        WHEN LOWER(i.product_name) LIKE '%graphics%' OR LOWER(i.product_name) LIKE '%rtx%' OR LOWER(i.product_name) LIKE '%radeon%' THEN 'Graphics Cards (GPU)'
                        WHEN LOWER(i.product_name) LIKE '%motherboard%' THEN 'Motherboards'
                        WHEN LOWER(i.product_name) LIKE '%ram%' OR LOWER(i.product_name) LIKE '%ddr%' THEN 'RAM'
                        WHEN LOWER(i.product_name) LIKE '%ssd%' OR LOWER(i.product_name) LIKE '%hdd%' OR LOWER(i.product_name) LIKE '%nvme%' THEN 'Storage'
                        WHEN LOWER(i.product_name) LIKE '%cooler%' OR LOWER(i.product_name) LIKE '%aio%' THEN 'Cooling'
                        WHEN LOWER(i.product_name) LIKE '%case%' THEN 'Cases'
                        WHEN LOWER(i.product_name) LIKE '%keyboard%' THEN 'Keyboards'
                        WHEN LOWER(i.product_name) LIKE '%mouse%' THEN 'Mouse'
                        WHEN LOWER(i.product_name) LIKE '%monitor%' THEN 'Monitors'
                        ELSE 'Other'
                    END) AS category,
                    d.defective_qty,
                    CONCAT(d.defect_type, CASE WHEN d.description IS NOT NULL AND d.description != '' THEN CONCAT(' - ', d.description) ELSE '' END) AS defect_reason,
                    d.reported_at
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
            if self.connection and self.connection.is_connected():
                self.connection.close()

    def add_new_product(self, product_name, brand, model, description,
                        stock_quantity, status=None, user_id=1, category=None):
        self.connect_to_database()
        try:
            cursor = self.connection.cursor()
            qty = int(stock_quantity)

            # DB enum only has 'Available' and 'Out of Stock' — Low Stock is not valid
            if not status or status == 'Low Stock':
                status = 'Out of Stock' if qty == 0 else 'Available'

            # 1. Use provided category or derive from product name
            if not category or category == "Other":
                category = ProductDetailsModel._derive_category(product_name)
            cursor.execute("""
                INSERT INTO inventory
                    (product_name, brand, model, description,
                     stock_quantity, status, category, created_at, updated_at)
                VALUES (%s, %s, %s, %s, %s, %s, %s, NOW(), NOW())
            """, (product_name, brand, model, description, qty, status, category))

            new_product_id = cursor.lastrowid

            # 2. Log initial stock as IN transaction so dashboard & reports reflect it
            if qty > 0:
                cursor.execute("""
                    INSERT INTO stock_transactions
                        (product_id, transaction_type, quantity, remarks,
                         performed_by, transaction_date)
                    VALUES (%s, 'IN', %s, 'Initial stock - Product added', %s, NOW())
                """, (new_product_id, qty, user_id))

            self.connection.commit()
            return True
        except Error as err:
            print(f"Error adding product: {err}")
            return False
        finally:
            if self.connection and self.connection.is_connected():
                self.connection.close()

    def get_unique_brands(self) -> list:
        """Return sorted list of distinct brands for the filter dropdown."""
        self.connect_to_database()
        try:
            cursor = self.connection.cursor()
            cursor.execute(
                "SELECT DISTINCT brand FROM inventory WHERE brand IS NOT NULL AND brand != '' ORDER BY brand ASC")
            return [row[0] for row in cursor.fetchall()]
        except Exception as e:
            print(f"Error fetching brands: {e}")
            return []
        finally:
            if self.connection and self.connection.is_connected():
                self.connection.close()

    def get_unique_categories(self) -> list:
        """Return sorted list of distinct categories from the real category column."""
        self.connect_to_database()
        try:
            cursor = self.connection.cursor()
            cursor.execute(
                "SELECT DISTINCT COALESCE(category, 'Other') AS category "
                "FROM inventory WHERE category IS NOT NULL AND category != '' "
                "ORDER BY category ASC"
            )
            return [row[0] for row in cursor.fetchall()]
        except Exception as e:
            print(f"Error fetching categories: {e}")
            return []
        finally:
            if self.connection and self.connection.is_connected():
                self.connection.close()

    def get_products_by_brand(self, brand: str) -> list:
        """Filter inventory by exact brand name (parameterized — SQL-injection safe)."""
        self.connect_to_database()
        try:
            cursor = self.connection.cursor(dictionary=True)
            query = (
                "SELECT product_id, product_name, brand, model, stock_quantity, status, "
                "COALESCE(category, 'Other') AS category, "
                "DATE_FORMAT(created_at, '%Y-%m-%d %H:%i') AS created_at "
                "FROM inventory WHERE brand = %s ORDER BY product_id ASC"
            )
            cursor.execute(query, (brand,))
            return cursor.fetchall()
        except Exception as e:
            print(f"Error filtering by brand: {e}")
            return []
        finally:
            if self.connection and self.connection.is_connected():
                self.connection.close()

    def get_products_by_category(self, category: str) -> list:
        """Filter inventory by the real category column (parameterized)."""
        self.connect_to_database()
        try:
            cursor = self.connection.cursor(dictionary=True)
            query = (
                "SELECT product_id, product_name, brand, model, stock_quantity, status, "
                "COALESCE(category, 'Other') AS category, "
                "DATE_FORMAT(created_at, '%Y-%m-%d %H:%i') AS created_at "
                "FROM inventory WHERE category = %s ORDER BY product_id ASC"
            )
            cursor.execute(query, (category,))
            return cursor.fetchall()
        except Exception as e:
            print(f"Error filtering by category: {e}")
            return []
        finally:
            if self.connection and self.connection.is_connected():
                self.connection.close()


    def get_product_by_id(self, product_id: int) -> dict:
        """Fetch full details of a single product by ID."""
        self.connect_to_database()
        try:
            cursor = self.connection.cursor(dictionary=True)
            cursor.execute(
                "SELECT product_id, product_name, brand, model, description, "
                "stock_quantity, status, COALESCE(category, 'Other') AS category, "
                "DATE_FORMAT(created_at, '%Y-%m-%d %H:%i') AS created_at, "
                "DATE_FORMAT(updated_at, '%Y-%m-%d %H:%i') AS updated_at "
                "FROM inventory WHERE product_id = %s",
                (product_id,)
            )
            return cursor.fetchone() or {}
        except Exception as e:
            print(f"Error fetching product by id: {e}")
            return {}
        finally:
            if self.connection and self.connection.is_connected():
                self.connection.close()

    def update_stock(self, product_id, quantity_change, transaction_type, remarks, user_id,
                     defect_type=None, defect_description=None):
        self.connect_to_database()
        try:
            cursor = self.connection.cursor()
            self.connection.start_transaction()

            # 1. Update Inventory Table
            update_query = """
                UPDATE inventory 
                SET stock_quantity = stock_quantity + %s,
                    status = CASE 
                        WHEN (stock_quantity + %s) <= 0 THEN 'Out of Stock'
                        WHEN (stock_quantity + %s) <= 10 THEN 'Low Stock'
                        ELSE 'Available'
                    END,
                    updated_at = NOW()
                WHERE product_id = %s
            """
            cursor.execute(update_query, (quantity_change, quantity_change, quantity_change, product_id))

            # 2. Log Transaction
            log_query = """
                INSERT INTO stock_transactions 
                (product_id, transaction_type, quantity, remarks, performed_by, transaction_date)
                VALUES (%s, %s, %s, %s, %s, NOW())
            """
            cursor.execute(log_query, (product_id, transaction_type, abs(quantity_change), remarks, user_id))

            # 3. If DEFECT — also create a separate defective_items record with unique defect_id
            if transaction_type == 'DEFECT':
                d_type = defect_type if defect_type else remarks.split(' - ')[0]
                d_desc = defect_description if defect_description else (
                    remarks.split(' - ', 1)[1] if ' - ' in remarks else '')
                defect_query = """
                    INSERT INTO defective_items (product_id, defective_qty, defect_type, description, reported_by, reported_at)
                    VALUES (%s, %s, %s, %s, %s, NOW())
                """
                cursor.execute(defect_query, (product_id, abs(quantity_change), d_type, d_desc, user_id))

            self.connection.commit()
            return True
        except Error as err:
            print(f"Error updating stock: {err}")
            self.connection.rollback()
            return False
        finally:
            if self.connection and self.connection.is_connected():
                self.connection.close()