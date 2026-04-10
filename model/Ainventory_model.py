# model/Ainventory_model.py
# MVC LAYER: MODEL
# Responsibilities: DB queries, CRUD, business rules, validation.
# Must NOT import or reference any PyQt6 / UI widgets.

import mysql.connector
from mysql.connector import Error
from typing import Optional


class ProductDetailsModel:
    """
    All inventory business logic lives here.
    Controllers call these methods; they never write SQL or validate data
    themselves.
    """

    # ── Shared category SQL expression ───────────────────────────────────────
    # Single source of truth — imported by ADBModel and AreportModel so the
    # CASE WHEN block is never duplicated.
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
              OR LOWER(product_name) LIKE '%fan%'
            THEN 'Cooling'
            WHEN LOWER(product_name) LIKE '%case%'
              OR LOWER(product_name) LIKE '%chassis%'
            THEN 'Cases'
            WHEN LOWER(product_name) LIKE '%psu%'
              OR LOWER(product_name) LIKE '%power supply%'
              OR LOWER(product_name) LIKE '%watt%'
            THEN 'Power Supply'
            WHEN LOWER(product_name) LIKE '%keyboard%'
            THEN 'Keyboards'
            WHEN LOWER(product_name) LIKE '%mouse%'
            THEN 'Mice'
            WHEN LOWER(product_name) LIKE '%monitor%'
              OR LOWER(product_name) LIKE '%display%'
            THEN 'Monitors'
            ELSE 'Other'
        END
    """

    # ── Business Rules ────────────────────────────────────────────────────────

    @staticmethod
    def determine_status(qty: int) -> str:
        """
        Business rule: map a stock quantity to its human-readable status.
        Single source of truth — used by both add and update paths.
        NOTE: DB enum currently only has 'Available' / 'Out of Stock'.
              Run the ALTER TABLE in pyesatrak.sql to add 'Low Stock'.
        """
        if qty <= 0:  return 'Out of Stock'
        if qty <= 10: return 'Low Stock'
        return 'Available'

    @staticmethod
    def validate_product_data(data: dict) -> Optional[str]:
        """
        Business rule: validate product fields before insert/update.
        Returns an error message string on failure, or None on success.
        Controllers must call this and show the returned message via the View.
        """
        name = data.get('product_name', '').strip()
        if not name:
            return "Product Name is required."
        if len(name) < 3:
            return "Product Name must be at least 3 characters."
        if len(name) > 255:
            return "Product Name is too long (max 255 characters)."

        brand = data.get('brand', '') or ''
        if len(brand) > 100:
            return "Brand name is too long (max 100 characters)."

        model_field = data.get('model', '') or ''
        if len(model_field) > 100:
            return "Model name is too long (max 100 characters)."

        qty = data.get('stock_quantity', 0)
        if not isinstance(qty, int) or qty < 0:
            return "Stock quantity cannot be negative."
        if qty > 10_000:
            return "Stock quantity too large (max 10,000)."

        return None  # All good

    @staticmethod
    def derive_category(product_name: str) -> str:
        """
        Business rule: infer category from product name keywords.
        Python-side mirror of CATEGORY_SQL for use at insert time.
        """
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
            return 'Mice'
        if any(k in n for k in ['monitor', 'display']):
            return 'Monitors'
        return 'Other'

    # ── DB Connection ─────────────────────────────────────────────────────────

    def __init__(self):
        self.connection = None
        self._db_config = {
            'host':     '127.0.0.1',
            'database': 'pyesatrak',
            'user':     'root',
            'password': ''
        }

    def _connect(self):
        """Internal: open a fresh connection. Callers must close it in finally."""
        try:
            conn = mysql.connector.connect(**self._db_config)
            if conn.is_connected():
                return conn
        except Error as e:
            print(f"[ProductDetailsModel] DB connection error: {e}")
        return None

    # ── READ ──────────────────────────────────────────────────────────────────

    def get_all_products(self) -> list:
        return self.get_products_by_filter("1=1")

    def get_products_by_filter(self, where_clause: str) -> list:
        conn = self._connect()
        if not conn:
            return []
        try:
            cursor = conn.cursor(dictionary=True)
            cursor.execute(
                f"SELECT product_id, product_name, brand, model, stock_quantity, status, "
                f"COALESCE(category, 'Other') AS category, "
                f"DATE_FORMAT(created_at, '%Y-%m-%d %H:%i') AS created_at "
                f"FROM inventory WHERE {where_clause} ORDER BY product_id ASC"
            )
            return cursor.fetchall()
        except Error as e:
            print(f"[get_products_by_filter] {e}")
            return []
        finally:
            conn.close()

    def get_product_by_id(self, product_id: int) -> dict:
        conn = self._connect()
        if not conn:
            return {}
        try:
            cursor = conn.cursor(dictionary=True)
            cursor.execute(
                "SELECT product_id, product_name, brand, model, description, "
                "stock_quantity, status, COALESCE(category, 'Other') AS category, "
                "DATE_FORMAT(created_at, '%Y-%m-%d %H:%i') AS created_at, "
                "DATE_FORMAT(updated_at, '%Y-%m-%d %H:%i') AS updated_at "
                "FROM inventory WHERE product_id = %s",
                (product_id,)
            )
            return cursor.fetchone() or {}
        except Error as e:
            print(f"[get_product_by_id] {e}")
            return {}
        finally:
            conn.close()

    def get_defective_products_with_reason(self) -> list:
        conn = self._connect()
        if not conn:
            return []
        try:
            cursor = conn.cursor(dictionary=True)
            cursor.execute("""
                SELECT
                    d.defect_id,
                    i.product_id,
                    i.product_name,
                    i.brand,
                    i.model,
                    COALESCE(i.category, 'Other') AS category,
                    d.defective_qty,
                    CONCAT(d.defect_type,
                        CASE WHEN d.description IS NOT NULL AND d.description != ''
                             THEN CONCAT(' - ', d.description) ELSE '' END
                    ) AS defect_reason,
                    d.reported_at
                FROM defective_items d
                JOIN inventory i ON d.product_id = i.product_id
                ORDER BY d.reported_at DESC
            """)
            return cursor.fetchall()
        except Error as e:
            print(f"[get_defective_products_with_reason] {e}")
            return []
        finally:
            conn.close()

    def get_unique_brands(self) -> list:
        conn = self._connect()
        if not conn:
            return []
        try:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT DISTINCT brand FROM inventory "
                "WHERE brand IS NOT NULL AND brand != '' ORDER BY brand ASC"
            )
            return [row[0] for row in cursor.fetchall()]
        except Error as e:
            print(f"[get_unique_brands] {e}")
            return []
        finally:
            conn.close()

    def get_unique_categories(self) -> list:
        conn = self._connect()
        if not conn:
            return []
        try:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT DISTINCT COALESCE(category, 'Other') AS category "
                "FROM inventory WHERE category IS NOT NULL AND category != '' "
                "ORDER BY category ASC"
            )
            return [row[0] for row in cursor.fetchall()]
        except Error as e:
            print(f"[get_unique_categories] {e}")
            return []
        finally:
            conn.close()

    def get_products_by_brand(self, brand: str) -> list:
        conn = self._connect()
        if not conn:
            return []
        try:
            cursor = conn.cursor(dictionary=True)
            cursor.execute(
                "SELECT product_id, product_name, brand, model, stock_quantity, status, "
                "COALESCE(category, 'Other') AS category, "
                "DATE_FORMAT(created_at, '%Y-%m-%d %H:%i') AS created_at "
                "FROM inventory WHERE brand = %s ORDER BY product_id ASC",
                (brand,)
            )
            return cursor.fetchall()
        except Error as e:
            print(f"[get_products_by_brand] {e}")
            return []
        finally:
            conn.close()

    def get_products_by_category(self, category: str) -> list:
        conn = self._connect()
        if not conn:
            return []
        try:
            cursor = conn.cursor(dictionary=True)
            cursor.execute(
                "SELECT product_id, product_name, brand, model, stock_quantity, status, "
                "COALESCE(category, 'Other') AS category, "
                "DATE_FORMAT(created_at, '%Y-%m-%d %H:%i') AS created_at "
                "FROM inventory WHERE category = %s ORDER BY product_id ASC",
                (category,)
            )
            return cursor.fetchall()
        except Error as e:
            print(f"[get_products_by_category] {e}")
            return []
        finally:
            conn.close()

    # ── CREATE ────────────────────────────────────────────────────────────────

    def add_new_product(self, product_name: str, brand: str, model: str,
                        description: str, stock_quantity: int,
                        user_id: int = 1, category: str = None) -> bool:
        """
        INSERT a new product and log its initial stock as an IN transaction.
        Status and category are derived here (business rules) — not by the caller.
        """
        conn = self._connect()
        if not conn:
            return False
        try:
            cursor = conn.cursor()
            qty    = int(stock_quantity)
            status = self.determine_status(qty)

            # DB enum currently lacks 'Low Stock' — coerce until ALTER runs
            if status == 'Low Stock':
                status = 'Available'

            if not category or category == 'Other':
                category = self.derive_category(product_name)

            cursor.execute("""
                INSERT INTO inventory
                    (product_name, brand, model, description,
                     stock_quantity, status, category, created_at, updated_at)
                VALUES (%s, %s, %s, %s, %s, %s, %s, NOW(), NOW())
            """, (product_name, brand, model, description, qty, status, category))

            new_id = cursor.lastrowid

            if qty > 0:
                cursor.execute("""
                    INSERT INTO stock_transactions
                        (product_id, transaction_type, quantity, remarks,
                         performed_by, transaction_date)
                    VALUES (%s, 'IN', %s, 'Initial stock - Product added', %s, NOW())
                """, (new_id, qty, user_id))

            conn.commit()
            return True
        except Error as e:
            print(f"[add_new_product] {e}")
            conn.rollback()
            return False
        finally:
            conn.close()

    # ── UPDATE ────────────────────────────────────────────────────────────────

    def update_stock(self, product_id: int, quantity_change: int,
                     transaction_type: str, remarks: str, user_id: int,
                     defect_type: str = None, defect_description: str = None) -> bool:
        """
        Atomically: update inventory qty + status, log transaction, optionally
        insert defective_items record. All in one DB transaction.
        """
        conn = self._connect()
        if not conn:
            return False
        try:
            cursor = conn.cursor()
            conn.start_transaction()

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

            cursor.execute("""
                INSERT INTO stock_transactions
                    (product_id, transaction_type, quantity, remarks,
                     performed_by, transaction_date)
                VALUES (%s, %s, %s, %s, %s, NOW())
            """, (product_id, transaction_type, abs(quantity_change), remarks, user_id))

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

            conn.commit()
            return True
        except Error as e:
            print(f"[update_stock] {e}")
            conn.rollback()
            return False
        finally:
            conn.close()


    _derive_category        = staticmethod(lambda name: ProductDetailsModel.derive_category(name))
    _determine_product_status = staticmethod(lambda qty: ProductDetailsModel.determine_status(qty))