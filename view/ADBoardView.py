# view/ADBoardView.py
# MVC LAYER: VIEW
# Responsibilities: build and display all UI. Expose user actions as signals.
# Must NOT import models, write SQL, or contain business logic.

from datetime import date, timedelta
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QStackedWidget,
    QFrame, QTableWidget, QTableWidgetItem, QHeaderView, QAbstractItemView,
    QSizePolicy, QGridLayout, QScrollArea, QDialog, QMessageBox
)
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QFont, QColor

import matplotlib
import matplotlib.ticker
matplotlib.use('QtAgg')
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure
import numpy as np

try:
    import pandas as pd
    PANDAS_AVAILABLE = True
except ImportError:
    PANDAS_AVAILABLE = False

# ── Colour constants (project palette) ───────────────────────────────────────
PRIMARY = '#0076aa'
WHITE   = '#ffffff'
BG      = '#f4f6f8'
TEXT    = '#1a1a1a'
SUBTEXT = '#757575'
DANGER  = '#D32F2F'
WARNING = '#F57C00'
SUCCESS = '#27ae60'
BORDER  = '#E0E0E0'


# ─────────────────────────────────────────────────────────────────────────────
#  Sign-out confirmation dialog  (moved from ADBoardController — VIEW concern)
# ─────────────────────────────────────────────────────────────────────────────
class SignOutDialog(QDialog):
    """Frameless confirmation dialog for sign-out. Returns True on 'Yes'."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint | Qt.WindowType.Dialog)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setFixedSize(350, 160)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # ── Header ────────────────────────────────────────────────────────────
        header = QFrame()
        header.setStyleSheet(f"""
            QFrame {{
                background-color: {PRIMARY};
                border-top-left-radius: 10px;
                border-top-right-radius: 10px;
            }}
        """)
        header.setFixedHeight(40)
        hl = QHBoxLayout(header)
        hl.setContentsMargins(15, 0, 10, 0)

        title = QLabel("Sign Out")
        title.setStyleSheet(
            f"color: white; font-weight: bold; font-family: Segoe UI;"
            f" font-size: 14px; border: none;")
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

        # ── Body ──────────────────────────────────────────────────────────────
        body = QFrame()
        body.setStyleSheet(f"""
            QFrame {{
                background-color: {WHITE};
                border-bottom-left-radius: 10px;
                border-bottom-right-radius: 10px;
            }}
        """)
        bl = QVBoxLayout(body)
        bl.setContentsMargins(20, 20, 20, 20)

        msg = QLabel("Are you sure you want to sign out?")
        msg.setAlignment(Qt.AlignmentFlag.AlignCenter)
        msg.setStyleSheet(f"color: {TEXT}; font-family: Segoe UI; font-size: 13px; border: none;")
        bl.addWidget(msg)

        btn_row = QHBoxLayout()
        btn_row.setSpacing(20)
        btn_style = f"""
            QPushButton {{
                background-color: {PRIMARY}; color: white; border-radius: 5px;
                padding: 6px 0; font-weight: bold; font-family: Segoe UI;
                min-width: 90px; border: none;
            }}
            QPushButton:hover {{ background-color: #005f8a; }}
        """
        yes_btn = QPushButton("Yes")
        yes_btn.setStyleSheet(btn_style)
        yes_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        yes_btn.clicked.connect(self.accept)

        no_btn = QPushButton("No")
        no_btn.setStyleSheet(btn_style)
        no_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        no_btn.clicked.connect(self.reject)

        btn_row.addStretch()
        btn_row.addWidget(yes_btn)
        btn_row.addWidget(no_btn)
        btn_row.addStretch()
        bl.addLayout(btn_row)
        layout.addWidget(body)


# ── Weekly Line Chart ─────────────────────────────────────────────────────────
class WeeklyLineChart(FigureCanvas):
    """Weekly stock flow with a pandas rolling-mean trendline (Stock Out)."""

    def __init__(self, width=5, height=4, dpi=100):
        self.fig = Figure(figsize=(width, height), dpi=dpi)
        self.fig.patch.set_facecolor('#FFFFFF')
        super().__init__(self.fig)
        self.axes = self.fig.add_subplot(111)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self._pending_data = []
        from PyQt6.QtCore import QTimer
        QTimer.singleShot(0, lambda: self.update_chart(self._pending_data))

    def update_chart(self, weekly_data):
        self._pending_data = weekly_data or []
        w, h = self.get_width_height()
        if w < 10 or h < 10:
            return

        today      = date.today()
        days       = [(today - timedelta(days=6 - i)) for i in range(7)]
        day_labels = [d.strftime('%a\n%m/%d') for d in days]

        db_map      = {str(r['day']): r for r in (weekly_data or [])}
        in_vals     = [int(db_map.get(str(d), {}).get('stock_in',  0) or 0) for d in days]
        out_vals    = [int(db_map.get(str(d), {}).get('stock_out', 0) or 0) for d in days]
        defect_vals = [int(db_map.get(str(d), {}).get('defects',   0) or 0) for d in days]

        x = np.arange(7)
        self.axes.clear()
        self.axes.set_facecolor('#FFFFFF')

        self.axes.plot(x, in_vals,     color='#0076aa', linewidth=2.5, marker='o', markersize=6, label='Stock In',  zorder=3)
        self.axes.plot(x, out_vals,    color='#D32F2F', linewidth=2.5, marker='s', markersize=6, label='Stock Out', zorder=3)
        self.axes.plot(x, defect_vals, color='#F57C00', linewidth=2.5, marker='^', markersize=6, label='Defects',   zorder=3)

        self.axes.fill_between(x, in_vals,     alpha=0.08, color='#0076aa')
        self.axes.fill_between(x, out_vals,    alpha=0.08, color='#D32F2F')
        self.axes.fill_between(x, defect_vals, alpha=0.08, color='#F57C00')

        if PANDAS_AVAILABLE:
            trend = (pd.Series(out_vals, dtype=float)
                     .rolling(window=3, min_periods=1).mean().to_numpy())
        else:
            coeffs = np.polyfit(x, out_vals, 1)
            trend  = np.poly1d(coeffs)(x)
        self.axes.plot(x, trend, color='#1565C0', linewidth=2,
                       linestyle='--', label='Outflow Trend', zorder=4)

        for xi, (iv, ov, dv) in enumerate(zip(in_vals, out_vals, defect_vals)):
            if iv > 0:
                self.axes.annotate(str(iv), (xi, iv), textcoords='offset points',
                                   xytext=(0, 6), ha='center', fontsize=7, color='#0076aa', fontweight='bold')
            if ov > 0:
                self.axes.annotate(str(ov), (xi, ov), textcoords='offset points',
                                   xytext=(0, 6), ha='center', fontsize=7, color='#D32F2F', fontweight='bold')
            if dv > 0:
                self.axes.annotate(str(dv), (xi, dv), textcoords='offset points',
                                   xytext=(0, 6), ha='center', fontsize=7, color='#F57C00', fontweight='bold')

        self.axes.set_xticks(x)
        self.axes.set_xticklabels(day_labels, fontsize=8, color='#666666')
        self.axes.tick_params(axis='y', labelsize=8, colors='#999999')
        self.axes.yaxis.set_major_locator(matplotlib.ticker.MaxNLocator(integer=True, nbins=4))
        for sp in ['top', 'right']:
            self.axes.spines[sp].set_visible(False)
        for sp in ['left', 'bottom']:
            self.axes.spines[sp].set_color('#E0E0E0')
            self.axes.spines[sp].set_linewidth(0.8)
        self.axes.grid(axis='y', color='#F0F0F0', linewidth=0.8, linestyle='--')
        self.axes.set_axisbelow(True)

        import matplotlib.patches as mpatches
        leg_handles = [
            mpatches.Patch(facecolor='#0076aa', edgecolor='#0076aa', label='Stock In'),
            mpatches.Patch(facecolor='#D32F2F', edgecolor='#D32F2F', label='Stock Out'),
            mpatches.Patch(facecolor='#F57C00', edgecolor='#F57C00', label='Defect Report'),
        ]
        self.axes.legend(handles=leg_handles, fontsize=8, loc='lower center', ncol=3,
                         frameon=True, framealpha=0.9, edgecolor='#E0E0E0',
                         borderpad=0.4, labelspacing=0.3, bbox_to_anchor=(0.5, -0.30))
        try:
            self.fig.subplots_adjust(left=0.06, right=0.97, top=0.96, bottom=0.25)
        except Exception:
            pass
        self.draw()


# ── Category Bar Chart ────────────────────────────────────────────────────────
class CategoryBarChart(FigureCanvas):
    def __init__(self):
        self.fig = Figure(figsize=(8, 3.0), dpi=100)
        self.fig.patch.set_facecolor('#FFFFFF')
        super().__init__(self.fig)
        self.axes = self.fig.add_subplot(111)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self._pending_data = {}
        from PyQt6.QtCore import QTimer
        QTimer.singleShot(0, lambda: self.update_chart(self._pending_data))

    def update_chart(self, data: dict):
        self._pending_data = data or {}
        w, h = self.get_width_height()
        if w < 10 or h < 10:
            return

        self.axes.clear()
        self.axes.set_facecolor('#FFFFFF')

        if not data:
            self.axes.text(0.5, 0.5, 'No category data', ha='center', va='center',
                           transform=self.axes.transAxes, color='#757575', fontsize=10)
            self.draw()
            return

        labels  = list(data.keys())
        values  = list(data.values())
        palette = ['#0076aa','#27ae60','#7B1FA2','#F57C00',
                   '#D32F2F','#00BCD4','#FF5722','#607D8B',
                   '#E91E63','#795548','#9C27B0','#3F51B5']
        colors  = [palette[i % len(palette)] for i in range(len(labels))]
        bars    = self.axes.bar(labels, values, color=colors, width=0.55, zorder=3, edgecolor='none')

        max_v = max(values) if values else 1
        for bar, val in zip(bars, values):
            self.axes.text(bar.get_x() + bar.get_width() / 2,
                           bar.get_height() + max_v * 0.02,
                           str(val), ha='center', va='bottom',
                           fontsize=7.5, color='#1a1a1a', fontweight='bold')

        self.axes.tick_params(axis='x', labelsize=7.5, colors='#555', rotation=15)
        self.axes.tick_params(axis='y', labelsize=7.5, colors='#aaa')
        self.axes.yaxis.set_major_locator(matplotlib.ticker.MaxNLocator(integer=True, nbins=5))
        for sp in ['top', 'right']:
            self.axes.spines[sp].set_visible(False)
        for sp in ['left', 'bottom']:
            self.axes.spines[sp].set_color('#E0E0E0')
        self.axes.grid(axis='y', color='#F0F0F0', linewidth=0.8, linestyle='--', zorder=0)
        self.axes.set_axisbelow(True)
        try:
            self.fig.tight_layout(pad=0.8)
        except Exception:
            pass
        self.draw()


# ── DashboardView ─────────────────────────────────────────────────────────────
class DashboardView(QWidget):
    dashboard_clicked         = pyqtSignal()
    manage_users_clicked      = pyqtSignal()
    product_stock_clicked     = pyqtSignal()
    reports_clicked           = pyqtSignal()
    sign_out_clicked          = pyqtSignal()
    refresh_analytics_clicked = pyqtSignal()
    kpi_low_stock_clicked     = pyqtSignal()
    kpi_out_of_stock_clicked  = pyqtSignal()
    kpi_defective_clicked     = pyqtSignal()
    activity_double_clicked   = pyqtSignal(int)

    def __init__(self):
        super().__init__()
        self.COLORS = {
            'primary':        '#0076aa',
            'secondary':      '#4FC3F7',
            'black':          '#1A1A1A',
            'bg_gray':        '#F5F5F5',
            'white':          '#FFFFFF',
            'danger':         '#D32F2F',
            'warning':        '#F57C00',
            'success':        '#388E3C',
            'purple':         '#7B1FA2',
            'text_primary':   '#212121',
            'text_secondary': '#757575',
            'border':         '#E0E0E0',
        }
        self.header_font     = QFont('Segoe UI', 26, QFont.Weight.Normal)
        self.sub_header_font = QFont('Segoe UI', 14, QFont.Weight.DemiBold)
        self.kpi_value_font  = QFont('Segoe UI', 36, QFont.Weight.Bold)
        self.kpi_label_font  = QFont('Segoe UI', 11, QFont.Weight.Normal)
        self.btn_font        = QFont('Segoe UI', 11, QFont.Weight.DemiBold)
        self.init_ui()

    def init_ui(self):
        self.setWindowTitle('PyesaTrak - Admin Dashboard')
        self.setFixedSize(1280, 760)
        self.setStyleSheet(
            f"background-color: {self.COLORS['bg_gray']}; font-family: 'Segoe UI', Arial;")

        main_layout = QHBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # ── Sidebar ───────────────────────────────────────────────────────────
        sidebar = QFrame()
        sidebar.setFixedWidth(240)
        sidebar.setStyleSheet(
            f"background-color: {self.COLORS['black']}; border: none;")
        sl = QVBoxLayout(sidebar)
        sl.setContentsMargins(20, 40, 20, 40)
        sl.setSpacing(8)

        app_title = QLabel('PyesaTrak')
        app_title.setFont(QFont('Segoe UI', 24, QFont.Weight.Bold))
        app_title.setStyleSheet(
            f"color: {self.COLORS['white']}; margin-bottom: 30px; border: none;")
        app_title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        sl.addWidget(app_title)

        self.dashboard_btn     = self._nav_btn('Dashboard')
        self.manage_users_btn  = self._nav_btn('Manage Users')
        self.product_stock_btn = self._nav_btn('Inventory')
        self.reports_btn       = self._nav_btn('Reports')

        self.dashboard_btn.clicked.connect(self.dashboard_clicked.emit)
        self.manage_users_btn.clicked.connect(self.manage_users_clicked.emit)
        self.product_stock_btn.clicked.connect(self.product_stock_clicked.emit)
        self.reports_btn.clicked.connect(self.reports_clicked.emit)

        for btn in [self.dashboard_btn, self.manage_users_btn,
                    self.product_stock_btn, self.reports_btn]:
            sl.addWidget(btn)
        sl.addStretch()

        self.sign_out_btn = QPushButton('Sign Out')
        self.sign_out_btn.setFixedHeight(44)
        self.sign_out_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.sign_out_btn.setFont(self.btn_font)
        self.sign_out_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: #2A2A2A; color: {self.COLORS['white']};
                border: none; border-radius: 6px;
            }}
            QPushButton:hover {{ background-color: {self.COLORS['danger']}; }}
        """)
        self.sign_out_btn.clicked.connect(self.sign_out_clicked.emit)
        sl.addWidget(self.sign_out_btn)
        main_layout.addWidget(sidebar)

        # ── Content area ──────────────────────────────────────────────────────
        content_area = QWidget()
        cl = QVBoxLayout(content_area)
        cl.setContentsMargins(30, 30, 30, 30)

        self.stacked_widget = QStackedWidget()
        self.dashboard_page = self._create_dashboard_page()
        self.stacked_widget.addWidget(self.dashboard_page)  # 0
        self.stacked_widget.addWidget(QWidget())             # 1 – Manage Users placeholder
        self.stacked_widget.addWidget(QWidget())             # 2 – Inventory placeholder
        self.stacked_widget.addWidget(QWidget())             # 3 – Reports placeholder

        cl.addWidget(self.stacked_widget)
        main_layout.addWidget(content_area)
        self._update_button_styles(self.dashboard_btn)

    # ── Nav helpers ───────────────────────────────────────────────────────────

    def _nav_btn(self, text):
        btn = QPushButton(text)
        btn.setFixedHeight(44)
        btn.setCursor(Qt.CursorShape.PointingHandCursor)
        btn.setFont(self.btn_font)
        btn.setStyleSheet(f"""
            QPushButton {{
                background-color: transparent; color: #9E9E9E;
                text-align: left; padding-left: 16px;
                border: none; border-radius: 6px;
            }}
            QPushButton:hover {{
                background-color: #2A2A2A; color: {self.COLORS['white']};
            }}
        """)
        return btn

    def _update_button_styles(self, active_btn):
        for btn in [self.dashboard_btn, self.manage_users_btn,
                    self.product_stock_btn, self.reports_btn]:
            if btn == active_btn:
                btn.setStyleSheet(f"""
                    background-color: {self.COLORS['primary']}; color: {self.COLORS['white']};
                    text-align: left; padding-left: 16px; border: none; border-radius: 6px;
                """)
            else:
                btn.setStyleSheet(f"""
                    background-color: transparent; color: #9E9E9E;
                    text-align: left; padding-left: 16px; border: none; border-radius: 6px;
                """)

    # ── Page-switch ───────────────────────────────────────────────────────────

    def show_dashboard_page(self):
        self.stacked_widget.setCurrentIndex(0)
        self._update_button_styles(self.dashboard_btn)

    def show_manage_users_page(self):
        self.stacked_widget.setCurrentIndex(1)
        self._update_button_styles(self.manage_users_btn)

    def show_product_page(self):
        self.stacked_widget.setCurrentIndex(2)
        self._update_button_styles(self.product_stock_btn)

    def show_reports_page(self):
        self.stacked_widget.setCurrentIndex(3)
        self._update_button_styles(self.reports_btn)

    # ── View-owned dialogs (called by controller, never by model) ─────────────

    def confirm_sign_out(self) -> bool:
        """Show sign-out confirmation. Returns True if user confirms."""
        dialog = SignOutDialog(self)
        return dialog.exec() == QDialog.DialogCode.Accepted

    def show_activity_details_dialog(self, activity: dict):
        """
        Render an activity detail popup.
        Controller passes the activity dict; view builds the widget.
        """
        msg = QMessageBox(self)
        msg.setWindowTitle("Activity Details")
        details = (
            f"Transaction Date: {activity.get('formatted_date', '')}\n"
            f"Type:             {activity.get('transaction_type', '')}\n"
            f"Product:          {activity.get('product_name', '')}\n"
            f"Performed By:     {activity.get('performed_by', '')}"
        )
        msg.setText(details)
        msg.setIcon(QMessageBox.Icon.Information)
        msg.setStyleSheet("QMessageBox { background-color: white; } QLabel { color: black; }")
        msg.exec()

    def show_message(self, title: str, text: str, icon_type: str = "Info"):
        """
        Generic styled message box for controller feedback.
        icon_type: 'Info' | 'Warning' | 'Critical'
        """
        msg = QMessageBox(self)
        msg.setWindowTitle(title)
        msg.setText(text)
        icon_map = {
            "Info":     QMessageBox.Icon.Information,
            "Warning":  QMessageBox.Icon.Warning,
            "Critical": QMessageBox.Icon.Critical,
        }
        msg.setIcon(icon_map.get(icon_type, QMessageBox.Icon.NoIcon))
        msg.setStyleSheet("""
            QMessageBox { background-color: white; }
            QMessageBox QLabel { color: black; font-size: 12px; }
            QMessageBox QPushButton {
                background-color: #0076aa; color: white;
                padding: 5px 15px; border-radius: 4px; min-width: 70px;
            }
            QMessageBox QPushButton:hover { background-color: #005580; }
        """)
        msg.exec()

    # ── Dashboard page builder ────────────────────────────────────────────────

    def _create_dashboard_page(self):
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(20)

        # Header row
        header_row = QHBoxLayout()
        title = QLabel('Admin Overview')
        title.setFont(self.header_font)
        title.setStyleSheet(f"color: {self.COLORS['text_primary']}; border: none;")

        today_lbl = QLabel(date.today().strftime('%A, %B %d, %Y'))
        today_lbl.setFont(QFont('Segoe UI', 11))
        today_lbl.setStyleSheet(f"color: {self.COLORS['text_secondary']}; border: none;")

        ref_btn = QPushButton('↻ Refresh')
        ref_btn.setFixedSize(110, 38)
        ref_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        ref_btn.setFont(self.btn_font)
        ref_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {self.COLORS['white']}; color: {self.COLORS['text_primary']};
                border: 1px solid {self.COLORS['border']}; border-radius: 6px;
            }}
            QPushButton:hover {{
                background-color: {self.COLORS['primary']}; color: {self.COLORS['white']};
                border: 1px solid {self.COLORS['primary']};
            }}
        """)
        ref_btn.clicked.connect(self.refresh_analytics_clicked.emit)

        header_row.addWidget(title)
        header_row.addStretch()
        header_row.addWidget(today_lbl)
        header_row.addSpacing(16)
        header_row.addWidget(ref_btn)
        layout.addLayout(header_row)

        # KPI grid
        kpi_grid = QGridLayout()
        kpi_grid.setSpacing(16)

        self.card_prod,   self.lbl_prod   = self._kpi_card('Total Products',         '0', 'All items in inventory',     self.COLORS['text_secondary'], clickable=False, accent=self.COLORS['primary'])
        self.card_inflow, self.lbl_inflow = self._kpi_card('Weekly Inflow',           '+0','Total stock received',        self.COLORS['success'],        clickable=False, accent=self.COLORS['success'])
        self.card_out,    self.lbl_out    = self._kpi_card('Out of Stock Products',   '0', 'Products with zero stock',   self.COLORS['danger'],         clickable=True,  accent=self.COLORS['danger'],  on_click=lambda: self.kpi_out_of_stock_clicked.emit())
        self.card_low,    self.lbl_low    = self._kpi_card('Low Stock Alerts',        '0', 'Items below threshold',      self.COLORS['warning'],        clickable=True,  accent=self.COLORS['warning'], on_click=lambda: self.kpi_low_stock_clicked.emit())
        self.card_def,    self.lbl_def    = self._kpi_card('Defective Items',         '0', 'Total defects reported',     self.COLORS['purple'],         clickable=True,  accent=self.COLORS['purple'],  on_click=lambda: self.kpi_defective_clicked.emit())

        kpi_grid.addWidget(self.card_prod,   0, 0)
        kpi_grid.addWidget(self.card_inflow, 0, 1)
        kpi_grid.addWidget(self.card_out,    0, 2)
        kpi_grid.addWidget(self.card_low,    1, 0)
        kpi_grid.addWidget(self.card_def,    1, 1)
        layout.addLayout(kpi_grid)

        # Weekly flow chart
        flow_frame = QFrame()
        flow_frame.setMinimumHeight(340)
        flow_frame.setStyleSheet(f"QFrame {{ background-color: {self.COLORS['white']}; border: 1px solid {self.COLORS['border']}; border-radius: 8px; }}")
        fl = QVBoxLayout(flow_frame)
        fl.setContentsMargins(24, 20, 24, 20)
        flow_title = QLabel('Stock Flow & Pandas Trendline')
        flow_title.setFont(self.sub_header_font)
        flow_title.setStyleSheet(f"color: {self.COLORS['text_primary']}; border: none;")
        fl.addWidget(flow_title)
        self.flow_chart = WeeklyLineChart(width=8, height=4.5)
        self.flow_chart.setMinimumHeight(280)
        fl.addWidget(self.flow_chart, 1)
        layout.addWidget(flow_frame)

        # Category bar chart
        cat_frame = QFrame()
        cat_frame.setMinimumHeight(280)
        cat_frame.setStyleSheet(f"QFrame {{ background-color: {self.COLORS['white']}; border: 1px solid {self.COLORS['border']}; border-radius: 8px; }}")
        cl2 = QVBoxLayout(cat_frame)
        cl2.setContentsMargins(24, 20, 24, 16)
        cl2.setSpacing(6)
        cat_title = QLabel("Stock Distribution by Category")
        cat_title.setFont(self.sub_header_font)
        cat_title.setStyleSheet(f"color: {self.COLORS['text_primary']}; border: none;")
        cl2.addWidget(cat_title)
        self.category_chart = CategoryBarChart()
        self.category_chart.setMinimumHeight(220)
        cl2.addWidget(self.category_chart, 1)
        layout.addWidget(cat_frame)

        # Recent activity table
        act_frame = QFrame()
        act_frame.setStyleSheet(f"QFrame {{ background-color: {self.COLORS['white']}; border: 1px solid {self.COLORS['border']}; border-radius: 8px; }}")
        al = QVBoxLayout(act_frame)
        al.setContentsMargins(24, 20, 24, 20)
        al.setSpacing(10)

        act_title = QLabel('Recent Activity')
        act_title.setFont(self.sub_header_font)
        act_title.setStyleSheet(f"color: {self.COLORS['text_primary']}; border: none;")
        al.addWidget(act_title)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFixedHeight(220)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll.setStyleSheet("QScrollArea { border: none; background: transparent; }")

        self.activity_table = QTableWidget()
        self.activity_table.setColumnCount(4)
        self.activity_table.setHorizontalHeaderLabels(['Date', 'Type', 'Product', 'User'])
        self.activity_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.activity_table.verticalHeader().setVisible(False)
        self.activity_table.setSelectionMode(QAbstractItemView.SelectionMode.NoSelection)
        self.activity_table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.activity_table.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.activity_table.setShowGrid(False)
        self.activity_table.setAlternatingRowColors(True)
        self.activity_table.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.activity_table.setStyleSheet(f"""
            QTableWidget {{ border: none; background-color: {self.COLORS['white']}; color: {self.COLORS['text_primary']}; font-family: 'Segoe UI'; font-size: 11px; }}
            QHeaderView::section {{ background-color: {self.COLORS['bg_gray']}; color: {self.COLORS['text_secondary']}; font-weight: 600; border: none; padding: 8px; font-size: 10px; }}
            QTableWidget::item {{ padding: 10px 8px; border-bottom: 1px solid {self.COLORS['border']}; }}
            QTableWidget::item:selected {{ background-color: {self.COLORS['white']}; color: {self.COLORS['text_primary']}; }}
            QTableWidget::item:alternate {{ background-color: #fafafa; }}
        """)
        self.activity_table.cellDoubleClicked.connect(
            lambda r, c: self.activity_double_clicked.emit(r))

        scroll.setWidget(self.activity_table)
        al.addWidget(scroll)
        layout.addWidget(act_frame)
        layout.addStretch()

        scroll_outer = QScrollArea()
        scroll_outer.setWidget(page)
        scroll_outer.setWidgetResizable(True)
        scroll_outer.setFrameShape(QFrame.Shape.NoFrame)
        scroll_outer.setStyleSheet(
            f"QScrollArea {{ border: none; background-color: {self.COLORS['bg_gray']}; }}")
        return scroll_outer

    def _kpi_card(self, title, value, subtitle, status_color,
                  clickable=False, on_click=None, accent=None):
        card  = QFrame()
        card.setFixedHeight(140)
        ac    = accent or self.COLORS['border']
        base  = f"QFrame {{ background-color: {self.COLORS['white']}; border: none; border-radius: 8px; border-bottom: 3px solid {ac}; }}"
        hover = base + f" QFrame:hover {{ background-color: #FAFAFA; }}"
        card.setStyleSheet(hover if clickable else base)
        if clickable:
            card.setCursor(Qt.CursorShape.PointingHandCursor)
            if on_click:
                card.mousePressEvent = lambda e: on_click()

        cl = QVBoxLayout(card)
        cl.setContentsMargins(20, 20, 20, 16)
        cl.setSpacing(4)

        t = QLabel(title.upper())
        t.setFont(self.kpi_label_font)
        t.setAlignment(Qt.AlignmentFlag.AlignLeft)
        t.setStyleSheet(f"color: {self.COLORS['text_secondary']}; background-color: transparent; border: none; letter-spacing: 0.5px;")
        cl.addWidget(t)

        v = QLabel(value)
        v.setFont(self.kpi_value_font)
        v.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        v.setStyleSheet(f"color: {status_color}; background-color: transparent; border: none; font-weight: 700;")
        cl.addWidget(v)

        s = QLabel(subtitle)
        s.setFont(QFont('Segoe UI', 10))
        s.setAlignment(Qt.AlignmentFlag.AlignLeft)
        s.setStyleSheet(f"color: {self.COLORS['text_secondary']}; background-color: transparent; border: none;")
        cl.addWidget(s)
        cl.addStretch()
        return card, v

    # ── Analytics update ──────────────────────────────────────────────────────

    def update_analytics(self, data: dict):
        self.lbl_prod.setText(str(data.get('total_products', 0)))
        weekly = data.get('weekly_flow', [])
        w_in   = sum(int(r.get('stock_in', 0) or 0) for r in weekly)
        self.lbl_inflow.setText(f'+{w_in}')
        self.lbl_out.setText(str(data.get('out_of_stock_count', 0)))
        self.lbl_low.setText(str(data.get('low_stock_count', 0)))
        self.lbl_def.setText(str(data.get('defective_count', 0)))
        self.flow_chart.update_chart(weekly)
        if hasattr(self, 'category_chart'):
            self.category_chart.update_chart(data.get('category_stock', {}))

        acts = data.get('recent_activities', [])
        self.activity_table.setRowCount(len(acts))
        for r, a in enumerate(acts):
            for col, key in enumerate(['formatted_date', 'transaction_type', 'product_name', 'performed_by']):
                item = QTableWidgetItem(str(a.get(key, '')))
                item.setFlags(Qt.ItemFlag.ItemIsEnabled)
                if key == 'transaction_type':
                    color_map = {'IN': self.COLORS['success'], 'OUT': self.COLORS['danger'], 'DEFECT': self.COLORS['warning']}
                    item.setForeground(QColor(color_map.get(a.get(key, ''), self.COLORS['text_primary'])))
                self.activity_table.setItem(r, col, item)

    def show(self):
        super().show()