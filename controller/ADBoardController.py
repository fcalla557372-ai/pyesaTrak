
from model.ADBModel import DashboardModel
from controller.ManageUsersController import ManageUsersController
from controller.Ainventory_Cont import ProductDetailsController
from controller.AreportController import ReportsController
from view.AreportsView import ReportsView

from PyQt6.QtWidgets import QWidget
from PyQt6.QtCore import QTimer


class DashboardController:
    PAGE_DASHBOARD = 0
    PAGE_USERS     = 1
    PAGE_INVENTORY = 2
    PAGE_REPORTS   = 3

    def __init__(self, user_data=None):
        from view.ADBoardView import DashboardView

        self.model     = DashboardModel()
        self.view      = DashboardView()
        self.user_data = user_data

        # Sub-controllers (eagerly created so pages are stable before display)
        self.users_controller   = ManageUsersController(self.user_data)
        self.product_controller = ProductDetailsController(self.user_data)

        # Reports page uses a lightweight placeholder swapped on first visit
        self._report_placeholder = QWidget()
        self.reports_controller  = None

        self._build_stacked_pages()

        # Wire back-button on inventory view
        self.product_controller.view.back_to_dashboard_clicked.connect(
            self.handle_dashboard)

        # Navigation signals
        self.view.dashboard_clicked.connect(self.handle_dashboard)
        self.view.manage_users_clicked.connect(self.handle_manage_users)
        self.view.product_stock_clicked.connect(self.handle_product_stock)
        self.view.reports_clicked.connect(self.handle_reports)

        # Action signals
        self.view.sign_out_clicked.connect(self.handle_sign_out)
        self.view.refresh_analytics_clicked.connect(self.refresh_dashboard)

        # KPI click-throughs → filter navigation
        self.view.kpi_low_stock_clicked.connect(self.filter_low_stock_view)
        self.view.kpi_out_of_stock_clicked.connect(self.filter_out_of_stock_view)
        self.view.kpi_defective_clicked.connect(self.filter_defective_view)

        self.view.activity_double_clicked.connect(self.show_activity_details)

        self.recent_activities_data  = []
        self._dashboard_initialized  = False

        # Defer initial load — avoids Matplotlib crash before window is shown
        QTimer.singleShot(200, self.refresh_dashboard)

    # ── Page registration ─────────────────────────────────────────────────────

    def _build_stacked_pages(self):
        sw = self.view.stacked_widget
        while sw.count() > 1:
            w = sw.widget(sw.count() - 1)
            sw.removeWidget(w)
            w.deleteLater()

        sw.addWidget(self.users_controller.view)    # index 1
        sw.addWidget(self.product_controller.view)  # index 2
        sw.addWidget(self._report_placeholder)      # index 3 — swapped on first visit

    # ── Data refresh ──────────────────────────────────────────────────────────

    def refresh_dashboard(self):
        self._dashboard_initialized = True
        print("Refreshing Dashboard Data…")
        data = {
            'total_products':     self.model.get_total_products(),
            'low_stock_count':    self.model.get_low_stock_items_count(),
            'out_of_stock_count': self.model.get_out_of_stock_count(),
            'defective_count':    self.model.get_defective_count(),
            'stock_flow':         self.model.get_stock_flow_summary(),
            'weekly_flow':        self.model.get_weekly_stock_flow(),
            'recent_activities':  self.model.get_recent_inventory_activities(10),
            'category_stock':     self.model.get_category_stock(),
        }
        self.view.update_analytics(data)
        self.recent_activities_data = data['recent_activities']

    # ── Navigation handlers ───────────────────────────────────────────────────

    def handle_dashboard(self):
        self.view.show_dashboard_page()
        if self._dashboard_initialized:
            self.refresh_dashboard()
        self._dashboard_initialized = True

    def handle_manage_users(self):
        self.view.show_manage_users_page()
        self.users_controller.refresh_data()

    def handle_product_stock(self):
        self.view.show_product_page()
        self.product_controller.view.set_active_tab("All")
        self.product_controller.load_all_products()

    def handle_reports(self):
        if self.reports_controller is None:
            report_view = ReportsView()
            self.reports_controller = ReportsController(self.user_data)
            self.reports_controller.set_view(report_view)
            sw = self.view.stacked_widget
            sw.removeWidget(self._report_placeholder)
            self._report_placeholder.deleteLater()
            sw.insertWidget(self.PAGE_REPORTS, report_view)
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

    # ── Activity detail ───────────────────────────────────────────────────────

    def show_activity_details(self, row_index: int):
        if row_index < 0 or row_index >= len(self.recent_activities_data):
            return
        activity = self.recent_activities_data[row_index]
        # View owns all widget construction — controller only passes data
        self.view.show_activity_details_dialog(activity)

    # ── Sign-out ──────────────────────────────────────────────────────────────

    def handle_sign_out(self):
        """View shows confirmation dialog; controller acts on the result."""
        if not self.view.confirm_sign_out():
            return
        try:
            from controller.login_controller import LoginController
            from view.login_view import LoginView
            from model.login_model import LoginModel

            self.lc = LoginController(LoginView(), LoginModel())
            self.lc.show()
            self.view.close()
        except Exception as e:
            print(f"[handle_sign_out] Error: {e}")

    def show(self):
        self.view.show()