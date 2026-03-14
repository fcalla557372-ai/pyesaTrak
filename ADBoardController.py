# Filename: ADBoardController.py
from ADBModel import DashboardModel
from PyQt6.QtWidgets import (QMessageBox, QDialog, QVBoxLayout, QHBoxLayout,
                              QLabel, QPushButton, QFrame, QWidget)
from PyQt6.QtCore import Qt

from ManageUsersController import ManageUsersController
from Ainventory_Cont import ProductDetailsController
from AreportController import ReportsController
from AreportsView import ReportsView


# ─────────────────────────────────────────────────────────────────────────────
#  Sign-out confirmation dialog
# ─────────────────────────────────────────────────────────────────────────────
class CustomMessageBox(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint | Qt.WindowType.Dialog)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setFixedSize(350, 160)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # Header
        self.header = QFrame()
        self.header.setStyleSheet("""
            QFrame {
                background-color: #0076aa;
                border-top-left-radius: 10px;
                border-top-right-radius: 10px;
            }
        """)
        self.header.setFixedHeight(40)
        header_layout = QHBoxLayout(self.header)
        header_layout.setContentsMargins(15, 0, 10, 0)

        title = QLabel("Sign Out")
        title.setStyleSheet(
            "color: white; font-weight: bold; font-family: Arial; font-size: 14px; border: none;")
        header_layout.addWidget(title)
        header_layout.addStretch()

        close_btn = QPushButton("✕")
        close_btn.setFixedSize(24, 24)
        close_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        close_btn.setStyleSheet("""
            QPushButton { color: white; background: transparent; border: none;
                          font-weight: bold; font-size: 14px; }
            QPushButton:hover { color: #ffcccc; }
        """)
        close_btn.clicked.connect(self.reject)
        header_layout.addWidget(close_btn)
        layout.addWidget(self.header)

        # Body
        self.body = QFrame()
        self.body.setStyleSheet("""
            QFrame {
                background-color: white;
                border-bottom-left-radius: 10px;
                border-bottom-right-radius: 10px;
            }
        """)
        body_layout = QVBoxLayout(self.body)
        body_layout.setContentsMargins(20, 20, 20, 20)

        msg = QLabel("Are you sure you want to sign out?")
        msg.setAlignment(Qt.AlignmentFlag.AlignCenter)
        msg.setStyleSheet("color: black; font-family: Arial; font-size: 13px; border: none;")
        body_layout.addWidget(msg)

        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(20)
        btn_style = """
            QPushButton {
                background-color: #0076aa; color: white; border-radius: 5px;
                padding: 6px 0; font-weight: bold; font-family: Arial;
                min-width: 90px; border: none;
            }
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

        btn_layout.addStretch()
        btn_layout.addWidget(btn_yes)
        btn_layout.addWidget(btn_no)
        btn_layout.addStretch()
        body_layout.addLayout(btn_layout)
        layout.addWidget(self.body)


# ─────────────────────────────────────────────────────────────────────────────
#  Dashboard Controller
# ─────────────────────────────────────────────────────────────────────────────
class DashboardController:
    # Page index constants — keep in sync with _build_stacked_pages()
    PAGE_DASHBOARD   = 0
    PAGE_USERS       = 1
    PAGE_INVENTORY   = 2
    PAGE_REPORTS     = 3

    def __init__(self, user_data=None):
        from ADBoardView import DashboardView

        self.model     = DashboardModel()
        self.view      = DashboardView()
        self.user_data = user_data

        # Sub-controllers (created eagerly so pages are stable before display)
        self.users_controller   = ManageUsersController(self.user_data)
        self.product_controller = ProductDetailsController(self.user_data)

        # ── Register all pages NOW — no removeWidget/insertWidget ever ────────
        # Reports page is a plain QWidget placeholder — replaced lazily on first visit
        # to avoid constructing QDateEdit/QComboBox widgets before the window is shown,
        # which causes 0xC0000409 heap corruption on Windows with Matplotlib present.
        self._report_placeholder = QWidget()
        self.reports_controller  = None

        self._build_stacked_pages()

        # ── Wire back-button on inventory view ────────────────────────────────
        self.product_controller.view.back_to_dashboard_clicked.connect(
            self.handle_dashboard)

        # ── Navigation signals ────────────────────────────────────────────────
        self.view.dashboard_clicked.connect(self.handle_dashboard)
        self.view.manage_users_clicked.connect(self.handle_manage_users)
        self.view.product_stock_clicked.connect(self.handle_product_stock)
        self.view.reports_clicked.connect(self.handle_reports)

        # ── Action signals ────────────────────────────────────────────────────
        self.view.sign_out_clicked.connect(self.handle_sign_out)
        self.view.refresh_analytics_clicked.connect(self.refresh_dashboard)

        # ── KPI click-throughs ────────────────────────────────────────────────
        self.view.kpi_low_stock_clicked.connect(self.filter_low_stock_view)
        self.view.kpi_out_of_stock_clicked.connect(self.filter_out_of_stock_view)
        self.view.kpi_defective_clicked.connect(self.filter_defective_view)

        self.view.activity_double_clicked.connect(self.show_activity_details)

        self.recent_activities_data = []
        self.refresh_dashboard()

    # ── Page registration ─────────────────────────────────────────────────────

    def _build_stacked_pages(self):
        """
        Add all pages to the stacked widget at construction time.
        Reports uses a lightweight QWidget placeholder (index 3) that gets
        swapped for the real ReportsView on first visit — this avoids
        constructing QDateEdit/QComboBox before the window is shown, which
        causes the 0xC0000409 heap corruption on Windows with Matplotlib.
        """
        sw = self.view.stacked_widget

        # Remove any stubs the view pre-added at indices 1+
        while sw.count() > 1:
            w = sw.widget(sw.count() - 1)
            sw.removeWidget(w)
            w.deleteLater()

        sw.addWidget(self.users_controller.view)    # index 1
        sw.addWidget(self.product_controller.view)  # index 2
        sw.addWidget(self._report_placeholder)      # index 3 — swapped on first visit

    # ── Data refresh ──────────────────────────────────────────────────────────

    def refresh_dashboard(self):
        print("Refreshing Dashboard Data...")
        data = {
            'total_products':    self.model.get_total_products(),
            'low_stock_count':   self.model.get_low_stock_items_count(),
            'out_of_stock_count':self.model.get_out_of_stock_count(),
            'defective_count':   self.model.get_defective_count(),
            'stock_flow':        self.model.get_stock_flow_summary(),
            'weekly_flow':       self.model.get_weekly_stock_flow(),
            'recent_activities': self.model.get_recent_inventory_activities(10),
            'category_stock':    self.model.get_category_stock(),
        }
        self.view.update_analytics(data)
        self.recent_activities_data = data['recent_activities']

    # ── Navigation handlers ───────────────────────────────────────────────────

    def handle_dashboard(self):
        self.view.show_dashboard_page()
        self.refresh_dashboard()

    def handle_manage_users(self):
        self.view.show_manage_users_page()
        self.users_controller.refresh_data()

    def handle_product_stock(self):
        self.view.show_product_page()
        self.product_controller.view.set_active_tab("All")
        self.product_controller.load_all_products()

    def handle_reports(self):
        if self.reports_controller is None:
            # First visit — now safe to create ReportsView (window is already shown)
            report_view = ReportsView()
            self.reports_controller = ReportsController(self.user_data)
            self.reports_controller.set_view(report_view)
            # Swap placeholder for real view at index 3
            sw = self.view.stacked_widget
            sw.removeWidget(self._report_placeholder)
            self._report_placeholder.deleteLater()
            sw.insertWidget(3, report_view)
        self.view.show_reports_page()

    # ── KPI filter navigation ─────────────────────────────────────────────────

    def filter_low_stock_view(self):
        self.view.show_product_page()
        self.product_controller.view.set_active_tab("Low")
        self.product_controller.load_low_stock()

    def filter_out_of_stock_view(self):
        self.view.show_product_page()
        self.product_controller.view.set_active_tab("Out")
        self.product_controller.load_out_of_stock()

    def filter_defective_view(self):
        self.view.show_product_page()
        self.product_controller.view.set_active_tab("Defect")
        self.product_controller.load_defective()

    # ── Activity detail dialog ────────────────────────────────────────────────

    def show_activity_details(self, row_index):
        if row_index < 0 or row_index >= len(self.recent_activities_data):
            return
        activity = self.recent_activities_data[row_index]
        details = (
            f"Transaction Date: {activity.get('formatted_date')}\n"
            f"Type: {activity.get('transaction_type')}\n"
            f"Product: {activity.get('product_name')}\n"
            f"Performed By: {activity.get('performed_by')}\n"
        )
        msg = QMessageBox(self.view)
        msg.setWindowTitle("Activity Details")
        msg.setText(details)
        msg.setIcon(QMessageBox.Icon.Information)
        msg.setStyleSheet("background-color: white; color: black;")
        msg.exec()

    # ── Sign-out ──────────────────────────────────────────────────────────────

    def handle_sign_out(self):
        dialog = CustomMessageBox(self.view)
        if dialog.exec():
            try:
                from login_controller import LoginController
                from login_view import LoginView
                from login_model import LoginModel

                # Open login first, then close dashboard
                self.lc = LoginController(LoginView(), LoginModel())
                self.lc.show()
                self.view.close()
            except Exception as e:
                print(f"Error returning to login: {e}")

    def show(self):
        self.view.show()