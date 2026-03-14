# ADBoardView.py - Admin Dashboard View
from datetime import date, timedelta
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QStackedWidget,
    QFrame, QTableWidget, QTableWidgetItem, QHeaderView, QAbstractItemView,
    QSizePolicy, QGridLayout, QScrollArea
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


# ── Updated chart: adds pandas trendline, deferred init to avoid Windows crash ──
class WeeklyLineChart(FigureCanvas):
    """Weekly stock flow with a pandas rolling-mean trendline (Stock Out)."""

    def __init__(self, width=5, height=4, dpi=100):
        self.fig = Figure(figsize=(width, height), dpi=dpi)
        self.fig.patch.set_facecolor('#FFFFFF')
        super().__init__(self.fig)
        self.axes = self.fig.add_subplot(111)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self._pending_data = []
        # Defer first draw until Qt has given the widget a real size (avoids crash)
        from PyQt6.QtCore import QTimer
        QTimer.singleShot(0, lambda: self.update_chart(self._pending_data))

    def update_chart(self, weekly_data):
        self._pending_data = weekly_data or []

        # Guard: don't draw before widget has real dimensions
        w, h = self.get_width_height()
        if w < 10 or h < 10:
            return

        today = date.today()
        days = [(today - timedelta(days=6 - i)) for i in range(7)]
        day_labels = [d.strftime('%a\n%m/%d') for d in days]

        db_map = {str(r['day']): r for r in (weekly_data or [])}
        in_vals     = [int(db_map.get(str(d), {}).get('stock_in',  0) or 0) for d in days]
        out_vals    = [int(db_map.get(str(d), {}).get('stock_out', 0) or 0) for d in days]
        defect_vals = [int(db_map.get(str(d), {}).get('defects',   0) or 0) for d in days]

        x = np.arange(7)
        self.axes.clear()
        self.axes.set_facecolor('#FFFFFF')

        self.axes.plot(x, in_vals,     color='#0076aa', linewidth=2.5,
                       marker='o', markersize=6, label='Stock In',  zorder=3)
        self.axes.plot(x, out_vals,    color='#D32F2F', linewidth=2.5,
                       marker='s', markersize=6, label='Stock Out', zorder=3)
        self.axes.plot(x, defect_vals, color='#F57C00', linewidth=2.5,
                       marker='^', markersize=6, label='Defects',   zorder=3)

        self.axes.fill_between(x, in_vals,     alpha=0.08, color='#0076aa')
        self.axes.fill_between(x, out_vals,    alpha=0.08, color='#D32F2F')
        self.axes.fill_between(x, defect_vals, alpha=0.08, color='#F57C00')

        # ── Pandas rolling-mean trendline on outflow ─────────────────────────
        if PANDAS_AVAILABLE:
            trend = (pd.Series(out_vals, dtype=float)
                     .rolling(window=3, min_periods=1).mean().to_numpy())
        else:
            coeffs = np.polyfit(x, out_vals, 1)
            trend  = np.poly1d(coeffs)(x)
        self.axes.plot(x, trend, color='#1565C0', linewidth=2,
                       linestyle='--', label='Outflow Trend', zorder=4)

        # Annotations
        for xi, (iv, ov, dv) in enumerate(zip(in_vals, out_vals, defect_vals)):
            if iv > 0:
                self.axes.annotate(str(iv), (xi, iv), textcoords='offset points',
                                   xytext=(0, 6), ha='center', fontsize=7,
                                   color='#0076aa', fontweight='bold')
            if ov > 0:
                self.axes.annotate(str(ov), (xi, ov), textcoords='offset points',
                                   xytext=(0, 6), ha='center', fontsize=7,
                                   color='#D32F2F', fontweight='bold')
            if dv > 0:
                self.axes.annotate(str(dv), (xi, dv), textcoords='offset points',
                                   xytext=(0, 6), ha='center', fontsize=7,
                                   color='#F57C00', fontweight='bold')

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

        # Solid-patch legend (no dot/line markers)
        import matplotlib.patches as mpatches
        leg_handles = [
            mpatches.Patch(facecolor='#0076aa', edgecolor='#0076aa', label='Stock In'),
            mpatches.Patch(facecolor='#D32F2F', edgecolor='#D32F2F', label='Stock Out'),
            mpatches.Patch(facecolor='#F57C00', edgecolor='#F57C00', label='Defect Report'),
        ]
        self.axes.legend(
            handles=leg_handles, fontsize=8, loc='lower center', ncol=3,
            frameon=True, framealpha=0.9, edgecolor='#E0E0E0',
            borderpad=0.4, labelspacing=0.3, bbox_to_anchor=(0.5, -0.30)
        )
        try:
            self.fig.subplots_adjust(left=0.06, right=0.97, top=0.96, bottom=0.25)
        except Exception:
            pass
        self.draw()



# ── Category Bar Chart ────────────────────────────────────────────────────────
class CategoryBarChart(FigureCanvas):
    """
    Bar chart showing total stock per product category.
    Dynamically built from whatever categories the DB returns —
    new product types appear automatically with no code changes.
    """
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

        labels = list(data.keys())
        values = list(data.values())

        # Colour palette — cycles for any number of categories
        palette = ['#0076aa', '#27ae60', '#7B1FA2', '#F57C00',
                   '#D32F2F', '#00BCD4', '#FF5722', '#607D8B',
                   '#E91E63', '#795548', '#9C27B0', '#3F51B5']
        colors = [palette[i % len(palette)] for i in range(len(labels))]

        bars = self.axes.bar(labels, values, color=colors, width=0.55,
                             zorder=3, edgecolor='none')

        max_v = max(values) if values else 1
        for bar, val in zip(bars, values):
            self.axes.text(
                bar.get_x() + bar.get_width() / 2,
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
        self.axes.grid(axis='y', color='#F0F0F0', linewidth=0.8,
                       linestyle='--', zorder=0)
        self.axes.set_axisbelow(True)

        try:
            self.fig.tight_layout(pad=0.8)
        except Exception:
            pass
        self.draw()


# ── DashboardView — ORIGINAL sidebar + structure, redesigned dashboard page ──
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
        # ── ORIGINAL colour palette & fonts ──────────────────────────────────
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
        self.header_font    = QFont('Segoe UI', 26, QFont.Weight.Normal)
        self.sub_header_font= QFont('Segoe UI', 14, QFont.Weight.DemiBold)
        self.kpi_value_font = QFont('Segoe UI', 36, QFont.Weight.Bold)
        self.kpi_label_font = QFont('Segoe UI', 11, QFont.Weight.Normal)
        self.btn_font       = QFont('Segoe UI', 11, QFont.Weight.DemiBold)
        self.init_ui()

    # ── ORIGINAL init_ui (sidebar unchanged) ─────────────────────────────────
    def init_ui(self):
        self.setWindowTitle('PyesaTrak - Admin Dashboard')
        self.setFixedSize(1280, 760)
        self.setStyleSheet(
            f"background-color: {self.COLORS['bg_gray']}; font-family: 'Segoe UI', Arial;")

        main_layout = QHBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # ── ORIGINAL SIDEBAR ─────────────────────────────────────────────────
        sidebar = QFrame()
        sidebar.setFixedWidth(240)
        sidebar.setStyleSheet(
            f"background-color: {self.COLORS['black']}; border: none;")
        sidebar_layout = QVBoxLayout(sidebar)
        sidebar_layout.setContentsMargins(20, 40, 20, 40)
        sidebar_layout.setSpacing(8)

        app_title = QLabel('PyesaTrak')
        app_title.setFont(QFont('Segoe UI', 24, QFont.Weight.Bold))
        app_title.setStyleSheet(
            f"color: {self.COLORS['white']}; margin-bottom: 30px; border: none;")
        app_title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        sidebar_layout.addWidget(app_title)

        self.dashboard_btn     = self.create_nav_btn('Dashboard')
        self.manage_users_btn  = self.create_nav_btn('Manage Users')
        self.product_stock_btn = self.create_nav_btn('Inventory')
        self.reports_btn       = self.create_nav_btn('Reports')

        self.dashboard_btn.clicked.connect(self.dashboard_clicked.emit)
        self.manage_users_btn.clicked.connect(self.manage_users_clicked.emit)
        self.product_stock_btn.clicked.connect(self.product_stock_clicked.emit)
        self.reports_btn.clicked.connect(self.reports_clicked.emit)

        for btn in [self.dashboard_btn, self.manage_users_btn,
                    self.product_stock_btn, self.reports_btn]:
            sidebar_layout.addWidget(btn)
        sidebar_layout.addStretch()

        self.sign_out_btn = QPushButton('Sign Out')
        self.sign_out_btn.setFixedHeight(44)
        self.sign_out_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.sign_out_btn.setFont(self.btn_font)
        self.sign_out_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: #2A2A2A;
                color: {self.COLORS['white']};
                border: none;
                border-radius: 6px;
            }}
            QPushButton:hover {{ background-color: {self.COLORS['danger']}; }}
        """)
        self.sign_out_btn.clicked.connect(self.sign_out_clicked.emit)
        sidebar_layout.addWidget(self.sign_out_btn)
        main_layout.addWidget(sidebar)

        # ── CONTENT AREA ─────────────────────────────────────────────────────
        content_area = QWidget()
        content_layout = QVBoxLayout(content_area)
        content_layout.setContentsMargins(30, 30, 30, 30)

        self.stacked_widget = QStackedWidget()
        self.dashboard_page = self.create_dashboard_page()
        self.stacked_widget.addWidget(self.dashboard_page)  # 0
        self.stacked_widget.addWidget(QWidget())             # 1 – Manage Users
        self.stacked_widget.addWidget(QWidget())             # 2 – Inventory
        self.stacked_widget.addWidget(QWidget())             # 3 – Reports

        content_layout.addWidget(self.stacked_widget)
        main_layout.addWidget(content_area)

        self.update_button_styles(self.dashboard_btn)

    # ── ORIGINAL nav helpers ──────────────────────────────────────────────────
    def create_nav_btn(self, text):
        btn = QPushButton(text)
        btn.setFixedHeight(44)
        btn.setCursor(Qt.CursorShape.PointingHandCursor)
        btn.setFont(self.btn_font)
        btn.setStyleSheet(f"""
            QPushButton {{
                background-color: transparent;
                color: #9E9E9E;
                text-align: left;
                padding-left: 16px;
                border: none;
                border-radius: 6px;
            }}
            QPushButton:hover {{
                background-color: #2A2A2A;
                color: {self.COLORS['white']};
            }}
        """)
        return btn

    def update_button_styles(self, active_btn):
        buttons = [self.dashboard_btn, self.manage_users_btn,
                   self.product_stock_btn, self.reports_btn]
        for btn in buttons:
            if btn == active_btn:
                btn.setStyleSheet(f"""
                    background-color: {self.COLORS['primary']};
                    color: {self.COLORS['white']};
                    text-align: left;
                    padding-left: 16px;
                    border: none;
                    border-radius: 6px;
                """)
            else:
                btn.setStyleSheet(f"""
                    background-color: transparent;
                    color: #9E9E9E;
                    text-align: left;
                    padding-left: 16px;
                    border: none;
                    border-radius: 6px;
                """)

    # ── ORIGINAL page-switch methods ─────────────────────────────────────────
    def show_dashboard_page(self):
        self.stacked_widget.setCurrentIndex(0)
        self.update_button_styles(self.dashboard_btn)

    def show_manage_users_page(self):
        self.stacked_widget.setCurrentIndex(1)
        self.update_button_styles(self.manage_users_btn)

    def show_product_page(self):
        self.stacked_widget.setCurrentIndex(2)
        self.update_button_styles(self.product_stock_btn)

    def show_reports_page(self):
        self.stacked_widget.setCurrentIndex(3)
        self.update_button_styles(self.reports_btn)


    # ── REDESIGNED dashboard page (reference screenshots) ────────────────────
    def create_dashboard_page(self):
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(20)

        # Header
        header_row = QHBoxLayout()
        title = QLabel('Admin Overview')
        title.setFont(self.header_font)
        title.setStyleSheet(
            f"color: {self.COLORS['text_primary']}; border: none;")

        today_lbl = QLabel(date.today().strftime('%A, %B %d, %Y'))
        today_lbl.setFont(QFont('Segoe UI', 11))
        today_lbl.setStyleSheet(
            f"color: {self.COLORS['text_secondary']}; border: none;")

        ref_btn = QPushButton('↻ Refresh')
        ref_btn.setFixedSize(110, 38)
        ref_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        ref_btn.setFont(self.btn_font)
        ref_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {self.COLORS['white']};
                color: {self.COLORS['text_primary']};
                border: 1px solid {self.COLORS['border']};
                border-radius: 6px;
            }}
            QPushButton:hover {{
                background-color: {self.COLORS['primary']};
                color: {self.COLORS['white']};
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

        # ── KPI Cards — 2 × 2 grid ───────────────────────────────────────────
        kpi_grid = QGridLayout()
        kpi_grid.setSpacing(16)

        self.card_prod, self.lbl_prod = self.create_borderless_kpi(
            'Total Products', '0', 'All items in inventory',
            self.COLORS['text_secondary'], clickable=False,
            accent=self.COLORS['primary'])

        self.card_inflow, self.lbl_inflow = self.create_borderless_kpi(
            'Weekly Inflow', '+0', 'Total stock received',
            self.COLORS['success'], clickable=False,
            accent=self.COLORS['success'])

        self.card_out, self.lbl_out = self.create_borderless_kpi(
            'Weekly Outflow', '-0', 'Total stock dispatched',
            self.COLORS['danger'], clickable=True,
            on_click=lambda: self.kpi_out_of_stock_clicked.emit(),
            accent=self.COLORS['danger'])

        self.card_low, self.lbl_low = self.create_borderless_kpi(
            'Low Stock Alerts', '0', 'Items below threshold',
            self.COLORS['warning'], clickable=True,
            on_click=lambda: self.kpi_low_stock_clicked.emit(),
            accent=self.COLORS['warning'])

        kpi_grid.addWidget(self.card_prod,   0, 0)
        kpi_grid.addWidget(self.card_inflow, 0, 1)
        kpi_grid.addWidget(self.card_out,    1, 0)
        kpi_grid.addWidget(self.card_low,    1, 1)
        layout.addLayout(kpi_grid)

        # ── Chart (full width) ───────────────────────────────────────────────
        flow_frame = QFrame()
        flow_frame.setMinimumHeight(340)
        flow_frame.setStyleSheet(f"""
            QFrame {{
                background-color: {self.COLORS['white']};
                border: 1px solid {self.COLORS['border']};
                border-radius: 8px;
            }}
        """)
        flow_layout = QVBoxLayout(flow_frame)
        flow_layout.setContentsMargins(24, 20, 24, 20)

        flow_title = QLabel('Stock Flow & Pandas Trendline')
        flow_title.setFont(self.sub_header_font)
        flow_title.setStyleSheet(
            f"color: {self.COLORS['text_primary']}; border: none;")
        flow_layout.addWidget(flow_title)

        self.flow_chart = WeeklyLineChart(width=8, height=4.5)
        self.flow_chart.setMinimumHeight(280)
        flow_layout.addWidget(self.flow_chart, 1)
        layout.addWidget(flow_frame)

        # ── Stock Distribution by Category ───────────────────────────────────
        cat_frame = QFrame()
        cat_frame.setMinimumHeight(280)
        cat_ss = (
            "QFrame {"
            "background-color: " + self.COLORS['white'] + ";"
            "border: 1px solid " + self.COLORS['border'] + ";"
            "border-radius: 8px;"
            "}"
        )
        cat_frame.setStyleSheet(cat_ss)
        cat_layout_v = QVBoxLayout(cat_frame)
        cat_layout_v.setContentsMargins(24, 20, 24, 16)
        cat_layout_v.setSpacing(6)

        cat_title = QLabel("Stock Distribution by Category")
        cat_title.setFont(self.sub_header_font)
        cat_title.setStyleSheet(
            "color: " + self.COLORS["text_primary"] + "; border: none;")
        cat_layout_v.addWidget(cat_title)

        self.category_chart = CategoryBarChart()
        self.category_chart.setMinimumHeight(220)
        cat_layout_v.addWidget(self.category_chart, 1)
        layout.addWidget(cat_frame)

        # ── Recent Activity (full width, scroll pane) ─────────────────────────
        act_container = QFrame()
        act_container.setStyleSheet(f"""
            QFrame {{
                background-color: {self.COLORS['white']};
                border: 1px solid {self.COLORS['border']};
                border-radius: 8px;
            }}
        """)
        act_outer = QVBoxLayout(act_container)
        act_outer.setContentsMargins(24, 20, 24, 20)
        act_outer.setSpacing(10)

        act_title = QLabel('Recent Activity')
        act_title.setFont(self.sub_header_font)
        act_title.setStyleSheet(
            f"color: {self.COLORS['text_primary']}; border: none;")
        act_outer.addWidget(act_title)

        # Scroll area wrapping the table
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFixedHeight(220)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll.setStyleSheet("QScrollArea { border: none; background: transparent; }")

        self.activity_table = QTableWidget()
        self.activity_table.setColumnCount(4)
        self.activity_table.setHorizontalHeaderLabels(['Date', 'Type', 'Product', 'User'])
        self.activity_table.horizontalHeader().setSectionResizeMode(
            QHeaderView.ResizeMode.Stretch)
        self.activity_table.verticalHeader().setVisible(False)
        self.activity_table.setSelectionMode(
            QAbstractItemView.SelectionMode.NoSelection)
        self.activity_table.setEditTriggers(
            QAbstractItemView.EditTrigger.NoEditTriggers)
        self.activity_table.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.activity_table.setShowGrid(False)
        self.activity_table.setAlternatingRowColors(True)
        self.activity_table.setSizePolicy(
            QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.activity_table.setStyleSheet(f"""
            QTableWidget {{
                border: none;
                background-color: {self.COLORS['white']};
                color: {self.COLORS['text_primary']};
                font-family: 'Segoe UI';
                font-size: 11px;
            }}
            QHeaderView::section {{
                background-color: {self.COLORS['bg_gray']};
                color: {self.COLORS['text_secondary']};
                font-weight: 600;
                border: none;
                padding: 8px;
                text-transform: uppercase;
                font-size: 10px;
                letter-spacing: 0.5px;
            }}
            QTableWidget::item {{
                padding: 10px 8px;
                border-bottom: 1px solid {self.COLORS['border']};
                border-left: none;
                border-right: none;
                border-top: none;
            }}
            QTableWidget::item:selected {{
                background-color: {self.COLORS['white']};
                color: {self.COLORS['text_primary']};
            }}
            QTableWidget::item:hover {{
                background-color: {self.COLORS['white']};
            }}
            QTableWidget::item:alternate {{
                background-color: #fafafa;
            }}
        """)
        self.activity_table.cellDoubleClicked.connect(
            lambda r, c: self.activity_double_clicked.emit(r))

        scroll.setWidget(self.activity_table)
        act_outer.addWidget(scroll)
        layout.addWidget(act_container)
        layout.addStretch()

        # Wrap in scroll area so dashboard scrolls if window is small
        scroll_outer = QScrollArea()
        scroll_outer.setWidget(page)
        scroll_outer.setWidgetResizable(True)
        scroll_outer.setFrameShape(QFrame.Shape.NoFrame)
        scroll_outer.setStyleSheet(
            "QScrollArea { border: none; background-color: " + self.COLORS['bg_gray'] + "; }")
        return scroll_outer

    # ── UPDATED create_borderless_kpi: accent bottom border + right-aligned value
    def create_borderless_kpi(self, title, value, subtitle, status_color,
                               clickable=False, on_click=None, accent=None):
        card = QFrame()
        card.setFixedHeight(140)
        accent_color = accent or self.COLORS['border']

        base_style = f"""
            QFrame {{
                background-color: {self.COLORS['white']};
                border: none;
                border-radius: 8px;
                border-bottom: 3px solid {accent_color};
            }}
        """
        hover_style = f"""
            QFrame {{
                background-color: {self.COLORS['white']};
                border: none;
                border-radius: 8px;
                border-bottom: 3px solid {accent_color};
            }}
            QFrame:hover {{ background-color: #FAFAFA; }}
        """
        card.setStyleSheet(hover_style if clickable else base_style)
        if clickable:
            card.setCursor(Qt.CursorShape.PointingHandCursor)
            if on_click:
                card.mousePressEvent = lambda e: on_click()

        card_layout = QVBoxLayout(card)
        card_layout.setContentsMargins(20, 20, 20, 16)
        card_layout.setSpacing(4)

        title_label = QLabel(title.upper())
        title_label.setFont(self.kpi_label_font)
        title_label.setAlignment(Qt.AlignmentFlag.AlignLeft)
        title_label.setStyleSheet(f"""
            color: {self.COLORS['text_secondary']};
            background-color: transparent;
            border: none;
            letter-spacing: 0.5px;
        """)
        card_layout.addWidget(title_label)

        value_label = QLabel(value)
        value_label.setFont(self.kpi_value_font)
        value_label.setAlignment(Qt.AlignmentFlag.AlignRight |
                                  Qt.AlignmentFlag.AlignVCenter)
        value_label.setStyleSheet(f"""
            color: {status_color};
            background-color: transparent;
            border: none;
            font-weight: 700;
        """)
        card_layout.addWidget(value_label)

        subtitle_label = QLabel(subtitle)
        subtitle_label.setFont(QFont('Segoe UI', 10))
        subtitle_label.setAlignment(Qt.AlignmentFlag.AlignLeft)
        subtitle_label.setStyleSheet(f"""
            color: {self.COLORS['text_secondary']};
            background-color: transparent;
            border: none;
        """)
        card_layout.addWidget(subtitle_label)
        card_layout.addStretch()

        return card, value_label

    # ── update_analytics: populates all dashboard widgets ────────────────────
    def update_analytics(self, data):
        self.lbl_prod.setText(str(data.get('total_products', 0)))

        weekly = data.get('weekly_flow', [])
        w_in  = sum(int(r.get('stock_in',  0) or 0) for r in weekly)
        w_out = sum(int(r.get('stock_out', 0) or 0) for r in weekly)
        self.lbl_inflow.setText(f'+{w_in}')
        self.lbl_out.setText(f'-{w_out}')
        self.lbl_low.setText(str(data.get('low_stock_count', 0)))

        self.flow_chart.update_chart(weekly)

        # Category bar chart — pass live DB data
        category_data = data.get('category_stock', {})
        if hasattr(self, 'category_chart'):
            self.category_chart.update_chart(category_data)

        acts = data.get('recent_activities', [])
        self.activity_table.setRowCount(len(acts))
        for r, a in enumerate(acts):
            date_item = QTableWidgetItem(str(a.get('formatted_date', '')))
            date_item.setFlags(Qt.ItemFlag.ItemIsEnabled)
            self.activity_table.setItem(r, 0, date_item)

            type_item = QTableWidgetItem(str(a.get('transaction_type', '')))
            type_item.setFlags(Qt.ItemFlag.ItemIsEnabled)
            t = a.get('transaction_type', '')
            if t == 'IN':
                type_item.setForeground(QColor(self.COLORS['success']))
            elif t == 'OUT':
                type_item.setForeground(QColor(self.COLORS['danger']))
            elif t == 'DEFECT':
                type_item.setForeground(QColor(self.COLORS['warning']))
            self.activity_table.setItem(r, 1, type_item)

            prod_item = QTableWidgetItem(str(a.get('product_name', '')))
            prod_item.setFlags(Qt.ItemFlag.ItemIsEnabled)
            self.activity_table.setItem(r, 2, prod_item)

            user_item = QTableWidgetItem(str(a.get('performed_by', '')))
            user_item.setFlags(Qt.ItemFlag.ItemIsEnabled)
            self.activity_table.setItem(r, 3, user_item)

    def show(self):
        super().show()