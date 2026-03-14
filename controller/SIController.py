# SIController.py — Staff Inventory Controller
from SIModel import InventoryModel
from SIView import InventoryView, StockInDialog, StockOutDialog, DefectDialog
from PyQt6.QtWidgets import QMessageBox


class InventoryController:
    """Controller for Staff Inventory Operations."""

    def __init__(self, model, view, user_data=None):
        self.model     = model
        self.view      = view
        self.user_data = user_data

        # Track selected product (set when user clicks a row)
        self._selected_product_id = None

        # Action button signals
        self.view.stock_in_clicked.connect(lambda: self.handle_transaction('IN'))
        self.view.stock_out_clicked.connect(lambda: self.handle_transaction('OUT'))
        self.view.defect_clicked.connect(lambda: self.handle_transaction('DEFECT'))

        # Row selection signal
        self.view.product_selected.connect(self._on_product_selected)

        # Filter tab signals
        self.view.filter_all_clicked.connect(self.load_all_products)
        self.view.filter_low_stock_clicked.connect(self.load_low_stock)
        self.view.filter_out_of_stock_clicked.connect(self.load_out_of_stock)
        self.view.filter_defective_clicked.connect(self.load_defective)

        # Initial load + populate filter dropdowns
        self.load_all_products()
        self._populate_filters()

    # ── Filter methods ────────────────────────────────────────────────────────

    def _populate_filters(self):
        """Load distinct brands and categories from DB into the view dropdowns."""
        try:
            self.view.populate_brand_filter(self.model.get_unique_brands())
            self.view.populate_category_filter(self.model.get_unique_categories())
        except Exception as e:
            print(f"[_populate_filters] {e}")

    def load_all_products(self):
        products = self.model.get_all_products()
        self.view.load_table(products)
        self.view.set_active_tab("All")
        self._selected_product_id = None

    def load_low_stock(self):
        products = self.model.get_products_by_filter(
            "stock_quantity <= 10 AND stock_quantity > 0")
        self.view.load_table(products)
        self.view.set_active_tab("Low")

    def load_out_of_stock(self):
        products = self.model.get_products_by_filter("stock_quantity = 0")
        self.view.load_table(products)
        self.view.set_active_tab("Out")

    def load_defective(self):
        products = self.model.get_defective_products_with_reason()
        self.view.load_defective_table(products)
        self.view.set_active_tab("Defect")

    # ── Row selection ─────────────────────────────────────────────────────────

    def _on_product_selected(self, product_id: int):
        """Store the selected product_id for pre-filling dialogs."""
        self._selected_product_id = product_id

    # ── Transaction handler ───────────────────────────────────────────────────

    def handle_transaction(self, trans_type: str):
        all_products = self.model.get_all_products()
        if not all_products:
            QMessageBox.warning(self.view, "Inventory Empty",
                                "No products available.")
            return

        user_id = (self.user_data['user_id']
                   if self.user_data else 1)

        # Pre-select the clicked row's product if one is selected
        pid = self._selected_product_id

        if trans_type == 'IN':
            dialog = StockInDialog(all_products, self.view, preselected_id=pid)
        elif trans_type == 'OUT':
            dialog = StockOutDialog(all_products, self.view, preselected_id=pid)
        else:
            dialog = DefectDialog(all_products, self.view, preselected_id=pid)

        if not dialog.exec():
            return  # cancelled

        if trans_type == 'IN':
            pid, qty, remarks = dialog.get_data()
            success = self.model.update_stock(
                pid, qty, trans_type, remarks, user_id)

        elif trans_type == 'OUT':
            pid, qty, remarks = dialog.get_data()
            success = self.model.update_stock(
                pid, -qty, trans_type, remarks, user_id)

        else:  # DEFECT
            pid, qty, defect_type, defect_desc = dialog.get_data()
            remarks = f"{defect_type} - {defect_desc}" if defect_desc else defect_type
            success = self.model.update_stock(
                pid, -qty, trans_type, remarks, user_id,
                defect_type=defect_type, defect_description=defect_desc)

        if success:
            msg = {"IN": "Stock added successfully.",
                   "OUT": "Stock removed successfully.",
                   "DEFECT": "Defect reported successfully."}[trans_type]
            QMessageBox.information(self.view, "Success", msg)
            self.load_all_products()
        else:
            QMessageBox.critical(self.view, "Error", "Transaction failed.")

    def show(self):
        self.view.show()

# ── Extra imports for StaffMainWindow ────────────────────────────────────────
from PyQt6.QtWidgets import (QWidget, QHBoxLayout, QVBoxLayout, QLabel,
                              QPushButton, QFrame, QDialog)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont
from SIView import InventoryView

class CustomMessageBox(QDialog):
    """Frameless sign-out confirmation — identical style to Admin version."""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint | Qt.WindowType.Dialog)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setFixedSize(350, 160)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        header = QFrame()
        header.setStyleSheet("""
            QFrame { background-color: #0076aa;
                     border-top-left-radius: 10px;
                     border-top-right-radius: 10px; }
        """)
        header.setFixedHeight(40)
        hl = QHBoxLayout(header)
        hl.setContentsMargins(15, 0, 10, 0)

        title = QLabel("Sign Out")
        title.setStyleSheet(
            "color: white; font-weight: bold; font-family: Arial;"
            " font-size: 14px; border: none;")
        hl.addWidget(title)
        hl.addStretch()

        close_btn = QPushButton("✕")
        close_btn.setFixedSize(24, 24)
        close_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        close_btn.setStyleSheet("""
            QPushButton { color: white; background: transparent; border: none;
                          font-weight: bold; font-size: 14px; }
            QPushButton:hover { color: #ffcccc; }
        """)
        close_btn.clicked.connect(self.reject)
        hl.addWidget(close_btn)
        layout.addWidget(header)

        body = QFrame()
        body.setStyleSheet("""
            QFrame { background-color: white;
                     border-bottom-left-radius: 10px;
                     border-bottom-right-radius: 10px; }
        """)
        bl = QVBoxLayout(body)
        bl.setContentsMargins(20, 20, 20, 20)

        msg = QLabel("Are you sure you want to sign out?")
        msg.setAlignment(Qt.AlignmentFlag.AlignCenter)
        msg.setStyleSheet(
            "color: black; font-family: Arial; font-size: 13px; border: none;")
        bl.addWidget(msg)

        btn_row = QHBoxLayout()
        btn_row.setSpacing(20)
        btn_style = """
            QPushButton { background-color: #0076aa; color: white;
                          border-radius: 5px; padding: 6px 0;
                          font-weight: bold; font-family: Arial;
                          min-width: 90px; border: none; }
            QPushButton:hover { background-color: #005f8a; }
        """
        btn_yes = QPushButton("Yes")
        btn_yes.setStyleSheet(btn_style)
        btn_yes.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_yes.clicked.connect(self.accept)

        btn_no = QPushButton("No")
        btn_no.setStyleSheet(btn_style)
        btn_no.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_no.clicked.connect(self.reject)

        btn_row.addStretch()
        btn_row.addWidget(btn_yes)
        btn_row.addWidget(btn_no)
        btn_row.addStretch()
        bl.addLayout(btn_row)
        layout.addWidget(body)


class StaffMainWindow(QWidget):
    """
    Staff-facing main window. Replaces StaffDashboardController/View entirely.
    Shows the inventory page directly — no dashboard, no Matplotlib dependency.
    """

    def __init__(self, user_data=None):
        super().__init__()
        self.user_data = user_data
        self.setWindowTitle("PyesaTrak - Staff")
        self.setFixedSize(1280, 760)
        self.setStyleSheet("background-color: #F5F5F5; font-family: 'Segoe UI', Arial;")
        self._build_ui()
        self._init_inventory()

    # ── Layout ────────────────────────────────────────────────────────────────

    def _build_ui(self):
        root = QHBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        # Sidebar
        sidebar = QFrame()
        sidebar.setFixedWidth(240)
        sidebar.setStyleSheet("background-color: #1A1A1A; border: none;")
        sl = QVBoxLayout(sidebar)
        sl.setContentsMargins(20, 40, 20, 40)
        sl.setSpacing(8)

        app_title = QLabel("PyesaTrak")
        app_title.setFont(QFont("Segoe UI", 24, QFont.Weight.Bold))
        app_title.setStyleSheet(
            "color: white; margin-bottom: 30px; border: none;")
        app_title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        sl.addWidget(app_title)

        # Only one nav item — Inventory
        self.inv_btn = QPushButton("Inventory")
        self.inv_btn.setFixedHeight(44)
        self.inv_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.inv_btn.setFont(QFont("Segoe UI", 11, QFont.Weight.DemiBold))
        self.inv_btn.setStyleSheet("""
            QPushButton { background-color: #0076aa; color: white;
                          text-align: left; padding-left: 16px;
                          border: none; border-radius: 6px; }
        """)
        sl.addWidget(self.inv_btn)
        sl.addStretch()

        # User info chip
        if self.user_data:
            fname = self.user_data.get('userFname', '')
            lname = self.user_data.get('userLname', '')
            name  = f"{fname} {lname}".strip() or self.user_data.get('username', '')
            user_lbl = QLabel(name)
            user_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
            user_lbl.setStyleSheet(
                "color: #9E9E9E; font-size: 11px; border: none;"
                " margin-bottom: 6px;")
            sl.addWidget(user_lbl)

        sign_out = QPushButton("Sign Out")
        sign_out.setFixedHeight(44)
        sign_out.setCursor(Qt.CursorShape.PointingHandCursor)
        sign_out.setFont(QFont("Segoe UI", 11, QFont.Weight.DemiBold))
        sign_out.setStyleSheet("""
            QPushButton { background-color: #2A2A2A; color: white;
                          border: none; border-radius: 6px; }
            QPushButton:hover { background-color: #D32F2F; }
        """)
        sign_out.clicked.connect(self._handle_sign_out)
        sl.addWidget(sign_out)
        root.addWidget(sidebar)

        # Content area
        content = QWidget()
        content.setStyleSheet("background-color: #F5F5F5;")
        cl = QVBoxLayout(content)
        cl.setContentsMargins(30, 30, 30, 30)

        # Inventory view placeholder — replaced in _init_inventory
        self.inventory_view = InventoryView()
        cl.addWidget(self.inventory_view)
        root.addWidget(content)

    def _init_inventory(self):
        """Wire up the inventory controller."""
        inv_model = InventoryModel()
        self.inventory_controller = InventoryController(
            inv_model, self.inventory_view, self.user_data)

    # ── Sign-out ──────────────────────────────────────────────────────────────

    def _handle_sign_out(self):
        dlg = CustomMessageBox(self)
        if dlg.exec():
            try:
                from login_controller import LoginController
                from login_view import LoginView
                from login_model import LoginModel
                self.lc = LoginController(LoginView(), LoginModel())
                self.lc.show()
                self.close()
            except Exception as e:
                print(f"Error returning to login: {e}")

    def show(self):
        super().show()