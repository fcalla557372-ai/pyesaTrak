# model/ADBModel.py
# MVC LAYER: MODEL
# Responsibilities: DB queries for the Admin Dashboard KPIs and charts.
# Must NOT import PyQt6 or contain any UI logic.
#
# CATEGORY_SQL is imported from Ainventory_model — single source of truth.
# Any new product category keyword only needs to be added there.

import mysql.connector
from mysql.connector import Error

# Single source of truth for category SQL expression
from model.Ainventory_model import ProductDetailsModel


class DashboardModel:
    """Read-only model for Admin Dashboard aggregates."""

    def __init__(self):
        self._db_config = {
            'host':     '127.0.0.1',
            'database': 'pyesatrak',
            'user':     'root',
            'password': ''
        }

    def _connect(self):
        try:
            return mysql.connector.connect(**self._db_config)
        except Error:
            return None

    # ── KPI counts ────────────────────────────────────────────────────────────

    def get_total_products(self) -> int:
        conn = self._connect()
        if not conn: return 0
        try:
            c = conn.cursor()
            c.execute("SELECT COUNT(*) FROM inventory")
            return c.fetchone()[0]
        finally:
            conn.close()

    def get_low_stock_items_count(self) -> int:
        conn = self._connect()
        if not conn: return 0
        try:
            c = conn.cursor()
            c.execute(
                "SELECT COUNT(*) FROM inventory "
                "WHERE stock_quantity <= 10 AND stock_quantity > 0")
            return c.fetchone()[0]
        finally:
            conn.close()

    def get_out_of_stock_count(self) -> int:
        conn = self._connect()
        if not conn: return 0
        try:
            c = conn.cursor()
            c.execute("SELECT COUNT(*) FROM inventory WHERE stock_quantity = 0")
            return c.fetchone()[0]
        finally:
            conn.close()

    def get_defective_count(self) -> int:
        """Total defective units — sum of all DEFECT transaction quantities."""
        conn = self._connect()
        if not conn: return 0
        try:
            c = conn.cursor()
            c.execute(
                "SELECT COALESCE(SUM(quantity), 0) FROM stock_transactions "
                "WHERE transaction_type = 'DEFECT'")
            return int(c.fetchone()[0])
        finally:
            conn.close()

    # ── Stock flow ────────────────────────────────────────────────────────────

    def get_stock_flow_summary(self) -> dict:
        """Total IN / OUT quantities for TODAY."""
        conn = self._connect()
        if not conn: return {'in': 0, 'out': 0}
        try:
            c = conn.cursor(dictionary=True)
            c.execute("""
                SELECT
                    SUM(CASE WHEN transaction_type = 'IN'  THEN quantity ELSE 0 END) AS stock_in,
                    SUM(CASE WHEN transaction_type = 'OUT' THEN quantity ELSE 0 END) AS stock_out
                FROM stock_transactions
                WHERE DATE(transaction_date) = CURDATE()
            """)
            res = c.fetchone()
            return {
                'in':  float(res['stock_in']  or 0),
                'out': float(res['stock_out'] or 0),
            } if res else {'in': 0, 'out': 0}
        finally:
            conn.close()

    def get_weekly_stock_flow(self) -> list:
        """Daily IN / OUT / DEFECT totals for the past 7 days."""
        conn = self._connect()
        if not conn: return []
        try:
            c = conn.cursor(dictionary=True)
            c.execute("""
                SELECT
                    DATE(transaction_date) AS day,
                    SUM(CASE WHEN transaction_type = 'IN'     THEN quantity ELSE 0 END) AS stock_in,
                    SUM(CASE WHEN transaction_type = 'OUT'    THEN quantity ELSE 0 END) AS stock_out,
                    SUM(CASE WHEN transaction_type = 'DEFECT' THEN quantity ELSE 0 END) AS defects
                FROM stock_transactions
                WHERE transaction_date >= CURDATE() - INTERVAL 6 DAY
                GROUP BY DATE(transaction_date)
                ORDER BY day ASC
            """)
            return c.fetchall()
        finally:
            conn.close()

    # ── Recent activity ───────────────────────────────────────────────────────

    def get_recent_inventory_activities(self, limit: int = 10) -> list:
        conn = self._connect()
        if not conn: return []
        try:
            c = conn.cursor(dictionary=True)
            c.execute("""
                SELECT
                    t.transaction_date,
                    DATE_FORMAT(t.transaction_date, '%Y-%m-%d %H:%i') AS formatted_date,
                    t.transaction_type,
                    i.product_name,
                    u.username AS performed_by
                FROM stock_transactions t
                JOIN inventory i ON t.product_id = i.product_id
                LEFT JOIN users u ON t.performed_by = u.user_id
                ORDER BY t.transaction_date DESC
                LIMIT %s
            """, (limit,))
            return c.fetchall()
        finally:
            conn.close()

    # ── Category stock ────────────────────────────────────────────────────────

    def get_category_stock(self) -> dict:
        """
        Stock totals per category — uses the shared CATEGORY_SQL from
        ProductDetailsModel so the CASE WHEN keywords are defined once only.
        """
        conn = self._connect()
        if not conn: return {}
        try:
            c = conn.cursor(dictionary=True)
            # Import the shared SQL expression — no duplication
            category_sql = ProductDetailsModel.CATEGORY_SQL
            c.execute(f"""
                SELECT
                    ({category_sql}) AS category,
                    SUM(stock_quantity)  AS total_qty
                FROM inventory
                GROUP BY category
                ORDER BY total_qty DESC
            """)
            rows = c.fetchall()
            return {r['category']: int(r['total_qty'] or 0) for r in rows}
        except Exception as e:
            print(f"[DashboardModel.get_category_stock] {e}")
            return {}
        finally:
            conn.close()