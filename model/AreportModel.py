# AreportModel.py - Updated with Analytics Data Methods
import mysql.connector
from mysql.connector import Error


class ReportsModel:
    def __init__(self):
        self.db_config = {
            'host': '127.0.0.1',
            'database': 'pyesatrak',
            'user': 'root',
            'password': ''
        }

    def connect(self):
        try:
            conn = mysql.connector.connect(**self.db_config)
            if conn.is_connected():
                return conn
            return None
        except Error as e:
            print(f"Error connecting to DB: {e}")
            return None

    # ─────────────────────────────────────────────────────────────────────────
    #  ANALYTICS DATA METHODS (new)
    # ─────────────────────────────────────────────────────────────────────────

    def get_analytics_kpis(self):
        """
        Returns dict with:
            total_qty   - sum of all stock_quantity
            low_count   - products with 0 < qty <= 10
            out_count   - products with qty = 0
            defect_pct  - (total defective units / total stock) * 100
        """
        conn = self.connect()
        if not conn:
            return {'total_qty': 0, 'low_count': 0, 'out_count': 0, 'defect_pct': 0.0}
        try:
            c = conn.cursor()
            c.execute("SELECT COALESCE(SUM(stock_quantity), 0) FROM inventory")
            total_qty = int(c.fetchone()[0])

            c.execute("SELECT COUNT(*) FROM inventory WHERE stock_quantity <= 10 AND stock_quantity > 0")
            low_count = int(c.fetchone()[0])

            c.execute("SELECT COUNT(*) FROM inventory WHERE stock_quantity = 0")
            out_count = int(c.fetchone()[0])

            c.execute("SELECT COALESCE(SUM(quantity), 0) FROM stock_transactions WHERE transaction_type = 'DEFECT'")
            defect_units = int(c.fetchone()[0])

            defect_pct = round((defect_units / total_qty * 100), 1) if total_qty > 0 else 0.0
            return {'total_qty': total_qty, 'low_count': low_count,
                    'out_count': out_count, 'defect_pct': defect_pct}
        except Error as e:
            print(f"Error fetching analytics KPIs: {e}")
            return {'total_qty': 0, 'low_count': 0, 'out_count': 0, 'defect_pct': 0.0}
        finally:
            conn.close()

    def get_category_stock(self):
        """
        Groups inventory by inferred category using product name keywords.
        Returns: { 'Processors (CPU)': 200, 'Graphics Cards (GPU)': 36, ... }
        """
        conn = self.connect()
        if not conn:
            return {}
        try:
            c = conn.cursor(dictionary=True)
            query = """
                SELECT
                    CASE
                        WHEN LOWER(product_name) LIKE '%processor%'
                          OR LOWER(product_name) LIKE '%ryzen%'
                          OR LOWER(product_name) LIKE '%core i%'
                          THEN 'Processors (CPU)'
                        WHEN LOWER(product_name) LIKE '%graphics%'
                          OR LOWER(product_name) LIKE '%rtx%'
                          OR LOWER(product_name) LIKE '%rx %'
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
                        ELSE 'Other'
                    END AS category,
                    SUM(stock_quantity) AS total_stock
                FROM inventory
                GROUP BY category
                ORDER BY total_stock DESC
            """
            c.execute(query)
            rows = c.fetchall()
            return {row['category']: int(row['total_stock']) for row in rows
                    if int(row['total_stock']) > 0}
        except Error as e:
            print(f"Error fetching category stock: {e}")
            return {}
        finally:
            conn.close()

    def get_cpu_brand_stock(self):
        """Brand breakdown for CPU products. Returns: { 'Intel': 176, 'AMD': 24 }"""
        conn = self.connect()
        if not conn:
            return {}
        try:
            c = conn.cursor(dictionary=True)
            query = """
                SELECT brand, SUM(stock_quantity) AS total
                FROM inventory
                WHERE LOWER(product_name) LIKE '%processor%'
                   OR LOWER(product_name) LIKE '%ryzen%'
                   OR LOWER(product_name) LIKE '%core i%'
                GROUP BY brand
                ORDER BY total DESC
            """
            c.execute(query)
            return {row['brand']: int(row['total']) for row in c.fetchall()
                    if int(row['total']) > 0}
        except Error as e:
            print(f"Error fetching CPU brand stock: {e}")
            return {}
        finally:
            conn.close()

    def get_gpu_brand_stock(self):
        """Brand breakdown for GPU products. Returns: { 'NVIDIA': 6, 'AMD': 24 }"""
        conn = self.connect()
        if not conn:
            return {}
        try:
            c = conn.cursor(dictionary=True)
            query = """
                SELECT brand, SUM(stock_quantity) AS total
                FROM inventory
                WHERE LOWER(product_name) LIKE '%graphics%'
                   OR LOWER(product_name) LIKE '%rtx%'
                   OR LOWER(product_name) LIKE '%rx %'
                GROUP BY brand
                ORDER BY total DESC
            """
            c.execute(query)
            return {row['brand']: int(row['total']) for row in c.fetchall()
                    if int(row['total']) > 0}
        except Error as e:
            print(f"Error fetching GPU brand stock: {e}")
            return {}
        finally:
            conn.close()

    def get_critical_items(self, limit=10):
        """Items that are out of stock or critically low (qty <= 5), with category label."""
        conn = self.connect()
        if not conn:
            return []
        try:
            c = conn.cursor(dictionary=True)
            query = """
                SELECT
                    product_id, product_name, brand, model, stock_quantity,
                    CASE
                        WHEN LOWER(product_name) LIKE '%processor%'
                          OR LOWER(product_name) LIKE '%ryzen%'
                          OR LOWER(product_name) LIKE '%core i%'
                          THEN 'CPU'
                        WHEN LOWER(product_name) LIKE '%graphics%'
                          OR LOWER(product_name) LIKE '%rtx%'
                          OR LOWER(product_name) LIKE '%rx %'
                          THEN 'GPU'
                        WHEN LOWER(product_name) LIKE '%motherboard%'
                          THEN 'Motherboard'
                        WHEN LOWER(product_name) LIKE '%ram%'
                          OR LOWER(product_name) LIKE '%ddr%'
                          THEN 'RAM'
                        WHEN LOWER(product_name) LIKE '%ssd%'
                          OR LOWER(product_name) LIKE '%nvme%'
                          OR LOWER(product_name) LIKE '%hdd%'
                          THEN 'Storage'
                        ELSE 'Other'
                    END AS category
                FROM inventory
                WHERE stock_quantity <= 5
                ORDER BY stock_quantity ASC, product_name ASC
                LIMIT %s
            """
            c.execute(query, (limit,))
            return c.fetchall()
        except Error as e:
            print(f"Error fetching critical items: {e}")
            return []
        finally:
            conn.close()

    def get_all_analytics(self):
        """Convenience: fetch all analytics data in one call."""
        return {
            'kpis':           self.get_analytics_kpis(),
            'category_stock': self.get_category_stock(),
            'cpu_brands':     self.get_cpu_brand_stock(),
            'gpu_brands':     self.get_gpu_brand_stock(),
            'critical_items': self.get_critical_items(),
        }

    # ─────────────────────────────────────────────────────────────────────────
    #  EXISTING METHODS (unchanged)
    # ─────────────────────────────────────────────────────────────────────────

    def get_all_saved_reports(self):
        conn = self.connect()
        if not conn: return []
        try:
            cursor = conn.cursor(dictionary=True)
            query = """
                SELECT 
                    r.report_id, r.report_name, r.report_type,
                    r.start_date, r.end_date,
                    r.created_at as transaction_date, r.report_status,
                    CONCAT(req.userFname, ' ', req.userLname) as requested_by,
                    CONCAT(proc.userFname, ' ', proc.userLname) as processed_by,
                    CONCAT(val.userFname, ' ', val.userLname) as validated_by,
                    r.validated_at
                FROM saved_reports r
                LEFT JOIN users req  ON r.requested_by = req.user_id
                LEFT JOIN users proc ON r.processed_by = proc.user_id
                LEFT JOIN users val  ON r.validated_by  = val.user_id
                ORDER BY r.created_at DESC
            """
            cursor.execute(query)
            return cursor.fetchall()
        except Error as e:
            print(f"Error fetching saved reports: {e}")
            return []
        finally:
            if conn: conn.close()

    def get_report_by_id(self, report_id: int) -> dict:
        """Fetch full details of a single saved report by ID."""
        conn = self.connect()
        if not conn: return {}
        try:
            cursor = conn.cursor(dictionary=True)
            query = """
                SELECT
                    r.report_id, r.report_name, r.report_type,
                    r.start_date, r.end_date,
                    DATE_FORMAT(r.created_at, '%Y-%m-%d %H:%i') AS created_at,
                    r.report_status,
                    CONCAT(req.userFname,  ' ', req.userLname)  AS requested_by,
                    CONCAT(proc.userFname, ' ', proc.userLname) AS processed_by,
                    CONCAT(val.userFname,  ' ', val.userLname)  AS validated_by,
                    DATE_FORMAT(r.validated_at, '%Y-%m-%d %H:%i') AS validated_at
                FROM saved_reports r
                LEFT JOIN users req  ON r.requested_by = req.user_id
                LEFT JOIN users proc ON r.processed_by = proc.user_id
                LEFT JOIN users val  ON r.validated_by  = val.user_id
                WHERE r.report_id = %s
            """
            cursor.execute(query, (report_id,))
            return cursor.fetchone() or {}
        except Exception as e:
            print(f"Error fetching report by id: {e}")
            return {}
        finally:
            if conn: conn.close()

    def save_report_entry(self, rtype, start, end, user_data, transaction_id=None):
        conn = self.connect()
        if not conn: return False
        try:
            cursor = conn.cursor()
            report_name = f"{rtype} ({start} to {end})"
            user_id = user_data.get('user_id') if isinstance(user_data, dict) else None
            query = """
                INSERT INTO saved_reports 
                (report_name, report_type, start_date, end_date,
                 requested_by, processed_by, transaction_id, created_at, report_status)
                VALUES (%s, %s, %s, %s, %s, %s, %s, NOW(), 'Processed')
            """
            cursor.execute(query, (report_name, rtype, start, end,
                                   user_id, user_id, transaction_id))
            conn.commit()
            return True
        except Error as e:
            print(f"Error saving report log: {e}")
            return False
        finally:
            if conn: conn.close()

    def validate_report(self, report_id, validator_user_id):
        conn = self.connect()
        if not conn: return False
        try:
            cursor = conn.cursor()
            cursor.execute("""
                UPDATE saved_reports 
                SET validated_by = %s, validated_at = NOW(), report_status = 'Validated'
                WHERE report_id = %s
            """, (validator_user_id, report_id))
            conn.commit()
            return True
        except Error as e:
            print(f"Error validating report: {e}")
            return False
        finally:
            if conn: conn.close()

    def get_stock_movement(self, start, end):
        conn = self.connect()
        if not conn: return []
        try:
            cursor = conn.cursor(dictionary=True)
            query = """
                SELECT 
                    DATE_FORMAT(t.transaction_date, '%Y-%m-%d %H:%i') as transaction_date,
                    t.transaction_type, i.product_name, i.brand,
                    t.quantity, t.remarks,
                    CONCAT(u.userFname, ' ', u.userLname) as processed_by
                FROM stock_transactions t
                JOIN inventory i ON t.product_id = i.product_id
                LEFT JOIN users u ON t.performed_by = u.user_id
                WHERE t.transaction_date BETWEEN %s AND %s
                ORDER BY t.transaction_date DESC
            """
            cursor.execute(query, (f"{start} 00:00:00", f"{end} 23:59:59"))
            return cursor.fetchall()
        except Error as e:
            print(f"Error fetching Stock Movement: {e}")
            return []
        finally:
            if conn: conn.close()

    def get_inventory_status(self):
        conn = self.connect()
        if not conn: return []
        try:
            cursor = conn.cursor(dictionary=True)
            cursor.execute("""
                SELECT product_id, product_name, brand, model,
                       stock_quantity, status,
                       DATE_FORMAT(updated_at, '%Y-%m-%d %H:%i') as last_updated
                FROM inventory ORDER BY product_id ASC
            """)
            return cursor.fetchall()
        except Error as e:
            print(f"Error fetching Inventory Status: {e}")
            return []
        finally:
            if conn: conn.close()

    def get_defective_report(self, start, end):
        conn = self.connect()
        if not conn: return []
        try:
            cursor = conn.cursor(dictionary=True)
            query = """
                SELECT 
                    DATE_FORMAT(t.transaction_date, '%Y-%m-%d %H:%i') as transaction_date,
                    i.product_name, i.brand, t.quantity as defective_qty,
                    t.remarks,
                    CONCAT(u.userFname, ' ', u.userLname) as reported_by
                FROM stock_transactions t
                JOIN inventory i ON t.product_id = i.product_id
                LEFT JOIN users u ON t.performed_by = u.user_id
                WHERE t.transaction_type = 'DEFECT'
                  AND t.transaction_date BETWEEN %s AND %s
                ORDER BY t.transaction_date DESC
            """
            cursor.execute(query, (f"{start} 00:00:00", f"{end} 23:59:59"))
            return cursor.fetchall()
        except Error as e:
            print(f"Error fetching Defective Report: {e}")
            return []
        finally:
            if conn: conn.close()

    def get_user_activity(self, start, end):
        conn = self.connect()
        if not conn: return []
        try:
            cursor = conn.cursor(dictionary=True)
            query = """
                SELECT l.login_id,
                       CONCAT(u.userFname, ' ', u.userLname) as user_name,
                       u.role,
                       DATE_FORMAT(l.login_time, '%Y-%m-%d %H:%i') as login_time
                FROM user_logins l
                JOIN users u ON l.user_id = u.user_id
                WHERE l.login_time BETWEEN %s AND %s
                ORDER BY l.login_time DESC
            """
            cursor.execute(query, (f"{start} 00:00:00", f"{end} 23:59:59"))
            return cursor.fetchall()
        except Error as e:
            print(f"Error fetching User Activity: {e}")
            return []
        finally:
            if conn: conn.close()