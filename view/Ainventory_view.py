# Ainventory_view.py — REDESIGNED (dropdown filter, search bar, back-to-dashboard)
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QTableWidget,
    QTableWidgetItem, QHeaderView, QAbstractItemView, QFrame, QDialog,
    QFormLayout, QSpinBox, QLineEdit, QTextEdit, QComboBox
)
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QFont, QColor, QIcon
from typing import List, Dict, Optional

PRIMARY = '#0076aa'
TEAL    = '#008B8B'
WHITE   = '#ffffff'
BG      = '#f4f6f8'
TEXT    = '#1a1a1a'
SUBTEXT = '#757575'
DANGER  = '#D32F2F'
WARNING = '#F57C00'
SUCCESS = '#388E3C'
BORDER  = '#E0E0E0'

# Maps dropdown text → filter key → signal name
_FILTER_OPTIONS = [
    ("All Items",    "All"),
    ("Low Stock",    "Low"),
    ("Out of Stock", "Out"),
    ("Defective",    "Defect"),
]


class ToggleTableWidget(QTableWidget):
    def mousePressEvent(self, event):
        index = self.indexAt(event.pos())
        if index.isValid():
            item = self.item(index.row(), 0)
            if item and item.isSelected():
                self.clearSelection()
                self.setCurrentItem(None)
                return
        super().mousePressEvent(event)


class ProductDetailsView(QWidget):
    add_product_clicked         = pyqtSignal()
    refresh_clicked             = pyqtSignal()
    product_double_clicked      = pyqtSignal(int)
    filter_all_clicked          = pyqtSignal()
    filter_low_stock_clicked    = pyqtSignal()
    filter_out_of_stock_clicked = pyqtSignal()
    filter_defective_clicked    = pyqtSignal()
    filter_by_brand_clicked     = pyqtSignal(str)
    filter_by_category_clicked  = pyqtSignal(str)
    back_to_dashboard_clicked   = pyqtSignal()   # ← NEW

    def __init__(self):
        super().__init__()
        self._active_filter   = "All"
        self._active_category = ""    # tracks current category selection
        self._active_brand    = ""    # tracks current brand selection
        self._all_products: List[Dict] = []   # full unfiltered cache (all products)
        self._all_defects:  List[Dict] = []   # cache for defect search filtering
        self._current_mode = "normal"          # "normal" or "defect"
        self.init_ui()

    # ── FILTER DROPDOWN HELPER ────────────────────────────────────────────────
    def _on_filter_changed(self, index):
        key = _FILTER_OPTIONS[index][1]
        self._active_filter = key
        # Clear search so the new filter shows full results
        self.search_input.blockSignals(True)
        self.search_input.clear()
        self.search_input.blockSignals(False)
        signals = {
            "All":    self.filter_all_clicked,
            "Low":    self.filter_low_stock_clicked,
            "Out":    self.filter_out_of_stock_clicked,
            "Defect": self.filter_defective_clicked,
        }
        if key in signals:
            signals[key].emit()

    def set_active_tab(self, tab_key):
        """Controller calls this to sync the dropdown after KPI navigation."""
        self._active_filter = tab_key
        idx_map = {"All": 0, "Low": 1, "Out": 2, "Defect": 3, "Brand": 0, "Category": 0}
        self.filter_combo.blockSignals(True)
        self.filter_combo.setCurrentIndex(idx_map.get(tab_key, 0))
        self.filter_combo.blockSignals(False)

    # ── INIT UI ───────────────────────────────────────────────────────────────
    def init_ui(self):
        self.setWindowTitle("PyesaTrak - Admin Inventory")
        self.setStyleSheet("background-color: transparent;")

        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        card = QFrame()
        card.setStyleSheet(f"QFrame {{ background-color: {WHITE}; border-radius: 10px; border: none; }}")
        cl = QVBoxLayout(card)
        cl.setContentsMargins(20, 16, 20, 16)
        cl.setSpacing(10)

        # ── Row 1: Back button + Title ────────────────────────────────────────
        title_row = QHBoxLayout()
        title_row.setSpacing(10)

        self.btn_back = QPushButton("← Dashboard")
        self.btn_back.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_back.setFixedHeight(30)
        self.btn_back.setStyleSheet(f"""
            QPushButton {{
                background-color: transparent; color: {PRIMARY};
                border: 1px solid {PRIMARY}; border-radius: 6px;
                padding: 2px 12px; font-size: 12px; font-weight: bold;
            }}
            QPushButton:hover {{ background-color: #e8f4fb; }}
        """)
        self.btn_back.clicked.connect(self.back_to_dashboard_clicked.emit)
        title_row.addWidget(self.btn_back)

        title = QLabel("Inventory Management (Admin)")
        title.setFont(QFont("Segoe UI", 16, QFont.Weight.Bold))
        title.setStyleSheet(f"color: {TEXT}; border: none;")
        title_row.addWidget(title)
        title_row.addStretch()
        cl.addLayout(title_row)

        # ── Row 2: Search + Filter icon + Filter dropdown ─────────────────────
        ctrl_row = QHBoxLayout()
        ctrl_row.setSpacing(8)

        # Search box (rounded, with 🔍 placeholder)
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("🔍  Search")
        self.search_input.setFixedHeight(34)
        self.search_input.setMaximumWidth(280)
        self.search_input.setStyleSheet(f"""
            QLineEdit {{
                border: 1px solid {BORDER}; border-radius: 17px;
                padding: 4px 14px; color: {TEXT}; background: {WHITE};
                font-size: 13px;
            }}
            QLineEdit:focus {{ border-color: {PRIMARY}; }}
        """)
        self.search_input.textChanged.connect(self._on_search)
        ctrl_row.addWidget(self.search_input)

        # Filter label + icon
        filter_lbl = QLabel("Filter")
        filter_lbl.setStyleSheet(f"color: {TEXT}; font-weight: bold; font-size: 13px; border: none;")
        ctrl_row.addWidget(filter_lbl)

        # Filter icon (funnel emoji as label)
        funnel = QLabel("▼")
        funnel.setStyleSheet(f"color: {PRIMARY}; font-size: 13px; border: none;")
        ctrl_row.addWidget(funnel)

        # Filter dropdown
        self.filter_combo = QComboBox()
        for label, _ in _FILTER_OPTIONS:
            self.filter_combo.addItem(label)
        self.filter_combo.setFixedHeight(34)
        self.filter_combo.setFixedWidth(150)
        self.filter_combo.setStyleSheet(f"""
            QComboBox {{
                border: 1px solid {BORDER}; border-radius: 6px;
                padding: 4px 10px; color: {TEXT}; background: {WHITE};
                font-size: 13px;
            }}
            QComboBox:focus {{ border-color: {PRIMARY}; }}
            QComboBox QAbstractItemView {{
                background: {WHITE}; color: {TEXT};
                selection-background-color: #d0eaf8;
                border: 1px solid {BORDER};
            }}
        """)
        self.filter_combo.currentIndexChanged.connect(self._on_filter_changed)
        ctrl_row.addWidget(self.filter_combo)

        # ── Brand filter ─────────────────────────────────────────────────
        brand_lbl = QLabel("Brand:")
        brand_lbl.setStyleSheet(f"color: {TEXT}; font-weight: bold; font-size: 13px; border: none;")
        ctrl_row.addWidget(brand_lbl)
        self.brand_combo = QComboBox()
        self.brand_combo.addItem("All Brands")
        self.brand_combo.setFixedHeight(34)
        self.brand_combo.setFixedWidth(130)
        self.brand_combo.setStyleSheet(f"""
            QComboBox {{ border: 1px solid {BORDER}; border-radius: 6px;
                padding: 4px 10px; color: {TEXT}; background: {WHITE}; font-size: 12px; }}
            QComboBox:focus {{ border-color: {PRIMARY}; }}
            QComboBox QAbstractItemView {{ background: {WHITE}; color: {TEXT};
                selection-background-color: #d0eaf8; border: 1px solid {BORDER}; }}
        """)
        self.brand_combo.currentTextChanged.connect(self._on_brand_changed)
        ctrl_row.addWidget(self.brand_combo)

        # ── Category filter ───────────────────────────────────────────────
        cat_lbl = QLabel("Category:")
        cat_lbl.setStyleSheet(f"color: {TEXT}; font-weight: bold; font-size: 13px; border: none;")
        ctrl_row.addWidget(cat_lbl)
        self.category_combo = QComboBox()
        self.category_combo.addItem("All Categories")
        self.category_combo.setFixedHeight(34)
        self.category_combo.setFixedWidth(155)
        self.category_combo.setStyleSheet(f"""
            QComboBox {{ border: 1px solid {BORDER}; border-radius: 6px;
                padding: 4px 10px; color: {TEXT}; background: {WHITE}; font-size: 12px; }}
            QComboBox:focus {{ border-color: {PRIMARY}; }}
            QComboBox QAbstractItemView {{ background: {WHITE}; color: {TEXT};
                selection-background-color: #d0eaf8; border: 1px solid {BORDER}; }}
        """)
        self.category_combo.currentTextChanged.connect(self._on_category_changed)
        ctrl_row.addWidget(self.category_combo)

        self.btn_add = QPushButton("[+] NEW PRODUCT")
        self.btn_add.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_add.setFixedHeight(34)
        self.btn_add.setMinimumWidth(148)
        self.btn_add.setStyleSheet(f"""
            QPushButton {{ background-color: {TEAL}; color: white; font-weight: bold;
                          border-radius: 6px; padding: 4px 14px; font-size: 12px; border: none; }}
            QPushButton:hover {{ background-color: #006666; }}
        """)
        self.btn_add.clicked.connect(self.add_product_clicked.emit)
        ctrl_row.addWidget(self.btn_add)
        ctrl_row.addStretch()
        cl.addLayout(ctrl_row)

        # ── Table ──────────────────────────────────────────────────────────────
        self.product_table = ToggleTableWidget()
        self._setup_table()
        cl.addWidget(self.product_table)

        main_layout.addWidget(card)

    def _setup_table(self):
        self.product_table.verticalHeader().setVisible(False)
        self.product_table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.product_table.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.product_table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.product_table.setShowGrid(False)
        self.product_table.setFrameShape(QFrame.Shape.NoFrame)
        self.product_table.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.product_table.setAlternatingRowColors(True)
        self.product_table.setStyleSheet(f"""
            QTableWidget {{
                background-color: {WHITE}; border: none; color: {TEXT};
                font-size: 13px; outline: 0;
            }}
            QHeaderView::section {{
                background-color: {TEXT}; color: white;
                padding: 10px 8px; font-weight: bold; border: none; font-size: 12px;
            }}
            QTableWidget::item {{
                padding: 9px 8px; border-bottom: 1px solid #f0f0f0;
            }}
            QTableWidget::item:selected {{
                background-color: #d0eaf8; color: {TEXT};
            }}
            QTableWidget::item:alternate {{
                background-color: #fafafa;
            }}
        """)
        self.product_table.cellDoubleClicked.connect(self._on_cell_clicked)

    def _on_cell_clicked(self, row, col):
        item = self.product_table.item(row, 0)
        if item:
            try:
                self.product_double_clicked.emit(int(item.text()))
            except ValueError:
                pass

    def _on_search(self, text: str):
        q = text.strip().lower()
        if self._current_mode == "defect":
            self._render_defective(
                self._all_defects if not q
                else [p for p in self._all_defects
                      if q in p.get("product_name", "").lower()
                      or q in p.get("brand", "").lower()
                      or q in p.get("model", "").lower()
                      or q in p.get("defect_reason", "").lower()]
            )
        else:
            # Start from the full product cache, then apply
            # category → brand → text search in that order
            pool = self._all_products
            if self._active_category:
                pool = [p for p in pool if p.get("category") == self._active_category]
            if self._active_brand:
                pool = [p for p in pool if p.get("brand") == self._active_brand]
            if q:
                pool = [p for p in pool
                        if q in p.get("product_name", "").lower()
                        or q in p.get("brand", "").lower()
                        or q in p.get("model", "").lower()]
            self._render_products(pool)

    def _on_brand_changed(self, text: str):
        """Filter the visible table locally — no DB round-trip needed."""
        self._active_brand = text if (text and text != "All Brands") else ""
        pool = self._all_products
        if self._active_category:
            pool = [p for p in pool if p.get("category") == self._active_category]
        if self._active_brand:
            pool = [p for p in pool if p.get("brand") == self._active_brand]
        q = self.search_input.text().strip().lower()
        if q:
            pool = [p for p in pool
                    if q in p.get("product_name", "").lower()
                    or q in p.get("brand", "").lower()
                    or q in p.get("model", "").lower()]
        self._render_products(pool)

    def _on_category_changed(self, text: str):
        """
        When a category is selected:
        1. Track the active category.
        2. Repopulate brand dropdown to only brands present in that category.
        3. Reset brand selection to All Brands.
        4. Filter the table locally — no DB round-trip.
        """
        self._active_category = text if (text and text != "All Categories") else ""
        self._active_brand = ""

        # Repopulate brand dropdown for the selected category
        self.brand_combo.blockSignals(True)
        self.brand_combo.clear()
        self.brand_combo.addItem("All Brands")
        if self._active_category:
            brands_in_cat = sorted(
                {p.get("brand", "") for p in self._all_products
                 if p.get("category") == self._active_category and p.get("brand")}
            )
        else:
            brands_in_cat = sorted(
                {p.get("brand", "") for p in self._all_products if p.get("brand")}
            )
        for b in brands_in_cat:
            self.brand_combo.addItem(b)
        self.brand_combo.blockSignals(False)

        # Filter table locally
        pool = self._all_products
        if self._active_category:
            pool = [p for p in pool if p.get("category") == self._active_category]
        q = self.search_input.text().strip().lower()
        if q:
            pool = [p for p in pool
                    if q in p.get("product_name", "").lower()
                    or q in p.get("brand", "").lower()
                    or q in p.get("model", "").lower()]
        self._render_products(pool)

    # ── POPULATE FILTER COMBOS ────────────────────────────────────────────────
    def populate_brand_filter(self, brands: list):
        """Called by controller to fill the brand dropdown on initial load."""
        self.brand_combo.blockSignals(True)
        self.brand_combo.clear()
        self.brand_combo.addItem("All Brands")
        for b in brands:
            self.brand_combo.addItem(b)
        self.brand_combo.blockSignals(False)

    def populate_category_filter(self, categories: list):
        """Called by controller to fill the category dropdown on initial load."""
        self.category_combo.blockSignals(True)
        self.category_combo.clear()
        self.category_combo.addItem("All Categories")
        for c in categories:
            self.category_combo.addItem(c)
        self.category_combo.blockSignals(False)

        # ── DATA DISPLAY ─────────────────────────────────────────────────────────
    def display_products(self, products: List[Dict]):
        """
        Called by controller with the full product list (no category/brand filter).
        Stores the complete list as the source-of-truth cache, then applies any
        active category/brand/search selections locally.
        """
        self._current_mode = "normal"
        self._all_products = list(products)

        # Re-apply active filters so the view stays consistent after a refresh
        pool = self._all_products
        if self._active_category:
            pool = [p for p in pool if p.get("category") == self._active_category]
        if self._active_brand:
            pool = [p for p in pool if p.get("brand") == self._active_brand]
        q = self.search_input.text().strip().lower()
        if q:
            pool = [p for p in pool
                    if q in p.get("product_name", "").lower()
                    or q in p.get("brand", "").lower()
                    or q in p.get("model", "").lower()]
        self._render_products(pool)

    def _render_products(self, products: List[Dict]):
        self.product_table.setColumnCount(8)
        self.product_table.setHorizontalHeaderLabels(
            ["Product ID", "Product Name", "Category", "Brand", "Model", "Stock", "Status", "Date Added"])
        self.product_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.product_table.setRowCount(len(products))
        for row, p in enumerate(products):
            self.product_table.setRowHeight(row, 42)
            self.product_table.setItem(row, 0, self._make_item(str(p['product_id']), center=True))
            self.product_table.setItem(row, 1, self._make_item(p['product_name']))
            cat = p.get('category', '') or '—'
            self.product_table.setItem(row, 2, self._make_item(cat))
            self.product_table.setItem(row, 3, self._make_item(p.get('brand', '')))
            self.product_table.setItem(row, 4, self._make_item(p.get('model', '')))
            # Safely convert stock_quantity — handles None, '', or non-int values
            try:
                qty = int(p['stock_quantity'] or 0)
            except (ValueError, TypeError):
                qty = 0

            qty_item = self._make_item(str(qty), center=True)
            if qty == 0:
                qty_item.setForeground(QColor(DANGER))
                qty_item.setFont(QFont("Segoe UI", 12, QFont.Weight.Bold))
            elif qty <= 10:
                qty_item.setForeground(QColor(DANGER))
                qty_item.setFont(QFont("Segoe UI", 12, QFont.Weight.Bold))
            self.product_table.setItem(row, 5, qty_item)

            # Derive status entirely from quantity (DB enum has no 'Low Stock')
            if qty == 0:
                status = 'Out of Stock'
                st_color = DANGER
            elif qty <= 10:
                status = 'Low Stock'
                st_color = WARNING
            else:
                status = 'Available'
                st_color = SUCCESS
            st_item = self._make_item(status, center=True)
            st_item.setForeground(QColor(st_color))
            self.product_table.setItem(row, 6, st_item)

            # Date Added — show "YYYY-MM-DD HH:MM" from the formatted string
            created_raw = p.get('created_at', '') or ''
            # Handle both string (from DATE_FORMAT) and datetime objects
            if hasattr(created_raw, 'strftime'):
                created = created_raw.strftime('%Y-%m-%d %H:%M')
            else:
                created = str(created_raw)
            ts_item = self._make_item(created, center=True)
            ts_item.setForeground(QColor(SUBTEXT))
            self.product_table.setItem(row, 7, ts_item)

    def display_defective_products(self, products: List[Dict]):
        """Cache full defect list then render (allows search to re-filter)."""
        self._current_mode = "defect"
        self._all_defects = list(products)
        # Re-apply any active search query immediately
        q = self.search_input.text().strip().lower()
        filtered = (
            [p for p in products
             if q in p.get("product_name", "").lower()
             or q in p.get("brand", "").lower()
             or q in p.get("model", "").lower()
             or q in p.get("defect_reason", "").lower()]
            if q else products
        )
        self._render_defective(filtered)

    def _render_defective(self, products: List[Dict]):
        """Render a (possibly filtered) defective list into the table."""
        self.product_table.setColumnCount(6)
        self.product_table.setHorizontalHeaderLabels(
            ["Defective ID", "Product Name", "Brand", "Model", "Defective Qty", "Defect Reason"])
        self.product_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.product_table.horizontalHeader().setSectionResizeMode(5, QHeaderView.ResizeMode.ResizeToContents)
        self.product_table.setRowCount(len(products))
        for row, p in enumerate(products):
            self.product_table.setRowHeight(row, 42)
            self.product_table.setItem(row, 0, self._make_item(str(p['defect_id']), center=True))
            self.product_table.setItem(row, 1, self._make_item(p['product_name']))
            cat = p.get('category', '') or '—'
            self.product_table.setItem(row, 2, self._make_item(cat))
            self.product_table.setItem(row, 3, self._make_item(p.get('brand', '')))
            self.product_table.setItem(row, 4, self._make_item(p.get('model', '')))
            qty_item = self._make_item(str(p['defective_qty']), center=True)
            qty_item.setForeground(QColor(DANGER))
            qty_item.setFont(QFont("Segoe UI", 12, QFont.Weight.Bold))
            self.product_table.setItem(row, 5, qty_item)
            reason_item = self._make_item(p.get('defect_reason', 'N/A'))
            reason_item.setForeground(QColor(DANGER))
            self.product_table.setItem(row, 5, reason_item)

    # aliases for controller compatibility
    def load_products(self, products): self.display_products(products)
    def load_defective_table(self, products): self.display_defective_products(products)

    def _make_item(self, text: str, center: bool = False) -> QTableWidgetItem:
        item = QTableWidgetItem(text)
        if center:
            item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
        return item

    def clear_table(self): self.product_table.setRowCount(0)

    def get_selected_product_id(self) -> Optional[int]:
        row = self.product_table.currentRow()
        if row >= 0:
            item = self.product_table.item(row, 0)
            if item:
                try: return int(item.text())
                except ValueError: return None
        return None


# ── ADD PRODUCT DIALOG ────────────────────────────────────────────────────────
class AddProductDialog(QWidget):
    product_name_changed = pyqtSignal(str)
    confirmed            = pyqtSignal(dict)
    cancelled            = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent, Qt.WindowType.Window)
        self.setAttribute(Qt.WidgetAttribute.WA_DeleteOnClose, True)
        self.setWindowTitle("Add New Product")
        self.setFixedSize(460, 560)
        self.setStyleSheet(f"""
            QWidget {{ background-color: {WHITE}; }}
            QLabel {{ color: {TEXT}; font-weight: bold; margin-bottom: 2px; border: none; }}
            QLabel#Header {{ color: {PRIMARY}; font-size: 18px; margin-bottom: 10px; }}
            QLineEdit, QSpinBox, QTextEdit, QComboBox {{
                border: 1px solid {BORDER}; border-radius: 6px;
                padding: 7px; color: {TEXT}; background-color: {WHITE};
            }}
            QPushButton {{ border-radius: 6px; padding: 7px 18px; font-weight: bold;
                           color: white; }}
        """)
        self._init_ui()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(32, 24, 32, 24)
        layout.setSpacing(8)

        title = QLabel("Add New Product")
        title.setObjectName("Header")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(title)

        form = QFormLayout()
        form.setSpacing(10)

        self.name_input  = QLineEdit(); self.name_input.setPlaceholderText("Product name")
        self.brand_input = QLineEdit(); self.brand_input.setPlaceholderText("Brand")
        self.model_input = QLineEdit(); self.model_input.setPlaceholderText("Model")
        self.desc_input  = QTextEdit()
        self.desc_input.setPlaceholderText("Description (optional)")
        self.desc_input.setMaximumHeight(65)
        self.stock_spin  = QSpinBox(); self.stock_spin.setRange(0, 10000)

        # ── Category row: dropdown + "+ New" button + hidden custom input ──────
        self.category_input = QComboBox()
        self.category_input.setMaxVisibleItems(8)
        self.category_input.setStyleSheet(f"""
            QComboBox {{
                border: 1px solid {BORDER}; border-radius: 6px;
                padding: 7px; color: {TEXT}; background-color: {WHITE};
                font-size: 13px;
            }}
            QComboBox:focus {{ border-color: {PRIMARY}; }}
            QComboBox QAbstractItemView {{
                background-color: {WHITE}; color: {TEXT};
                selection-background-color: #d0eaf8;
                border: 1px solid {BORDER};
                outline: none;
            }}
        """)
        self.category_input.addItem("— Select Category —")
        for _cat in ["Processors (CPU)", "Graphics Cards (GPU)", "Motherboards",
                     "RAM", "Storage", "Cooling", "Cases", "Power Supply",
                     "Keyboards", "Mice", "Monitors"]:
            self.category_input.addItem(_cat)

        self._btn_new_cat = QPushButton("+ New")
        self._btn_new_cat.setFixedHeight(34)
        self._btn_new_cat.setFixedWidth(64)
        self._btn_new_cat.setCursor(Qt.CursorShape.PointingHandCursor)
        self._btn_new_cat.setStyleSheet(f"""
            QPushButton {{
                background-color: transparent; color: {PRIMARY};
                border: 1px solid {PRIMARY}; border-radius: 6px;
                font-size: 12px; font-weight: bold; padding: 2px 6px;
            }}
            QPushButton:hover {{ background-color: #e8f4fb; }}
        """)

        self._custom_cat_input = QLineEdit()
        self._custom_cat_input.setPlaceholderText("Type new category…")
        self._custom_cat_input.setFixedHeight(34)
        self._custom_cat_input.hide()

        self._btn_confirm_cat = QPushButton("✓")
        self._btn_confirm_cat.setFixedSize(34, 34)
        self._btn_confirm_cat.setCursor(Qt.CursorShape.PointingHandCursor)
        self._btn_confirm_cat.setStyleSheet(f"""
            QPushButton {{
                background-color: {PRIMARY}; color: white !important;
                border-radius: 6px; font-size: 16px; font-weight: bold; border: none;
                padding: 0px;
            }}
            QPushButton:hover {{ background-color: #005f8a; }}
        """)
        self._btn_confirm_cat.hide()

        self._btn_cancel_cat = QPushButton("✕")
        self._btn_cancel_cat.setFixedSize(34, 34)
        self._btn_cancel_cat.setCursor(Qt.CursorShape.PointingHandCursor)
        self._btn_cancel_cat.setStyleSheet("""
            QPushButton {
                background-color: #999; color: white;
                border-radius: 6px; font-size: 14px; font-weight: bold; border: none;
                padding: 0px;
            }
            QPushButton:hover { background-color: #777; }
        """)
        self._btn_cancel_cat.hide()

        # Assemble the category row widget
        cat_row_widget = QWidget()
        cat_row_widget.setStyleSheet("border: none; background: transparent;")
        cat_row = QHBoxLayout(cat_row_widget)
        cat_row.setContentsMargins(0, 0, 0, 0)
        cat_row.setSpacing(6)
        cat_row.addWidget(self.category_input)
        cat_row.addWidget(self._btn_new_cat)
        cat_row.addWidget(self._custom_cat_input)
        cat_row.addWidget(self._btn_confirm_cat)
        cat_row.addWidget(self._btn_cancel_cat)

        # Wire up new-category flow
        self._btn_new_cat.clicked.connect(self._show_new_category_input)
        self._btn_confirm_cat.clicked.connect(self._confirm_new_category)
        self._btn_cancel_cat.clicked.connect(self._cancel_new_category)
        self._custom_cat_input.returnPressed.connect(self._confirm_new_category)

        form.addRow("Product Name:", self.name_input)
        form.addRow("Category:",     cat_row_widget)
        form.addRow("Brand:",        self.brand_input)
        form.addRow("Model:",        self.model_input)
        form.addRow("Description:",  self.desc_input)
        form.addRow("Initial Stock:", self.stock_spin)
        layout.addLayout(form)

        # Auto-detect category as user types product name
        self.name_input.textChanged.connect(self._auto_detect_category)

        layout.addStretch()

        btn_row = QHBoxLayout()
        btn_row.setSpacing(10)
        cancel = QPushButton("Cancel")
        cancel.setCursor(Qt.CursorShape.PointingHandCursor)
        cancel.setStyleSheet("background-color: #ccc; color: #333;")
        cancel.clicked.connect(self._on_cancel)
        save = QPushButton("Add Product")
        save.setCursor(Qt.CursorShape.PointingHandCursor)
        save.setStyleSheet(f"background-color: {TEAL}; color: white;")
        save.clicked.connect(self._on_confirm)
        btn_row.addWidget(cancel)
        btn_row.addWidget(save)
        layout.addLayout(btn_row)

    def _show_new_category_input(self):
        """Switch from dropdown+button to text input mode."""
        self.category_input.hide()
        self._btn_new_cat.hide()
        self._custom_cat_input.clear()
        self._custom_cat_input.show()
        self._btn_confirm_cat.show()
        self._btn_cancel_cat.show()
        self._custom_cat_input.setFocus()

    def _confirm_new_category(self):
        """Add the typed category to the dropdown and select it."""
        new_cat = self._custom_cat_input.text().strip()
        if new_cat:
            # Add only if not already present
            existing = [self.category_input.itemText(i)
                        for i in range(self.category_input.count())]
            if new_cat not in existing:
                # Append at end of list
                self.category_input.addItem(new_cat)
            idx = self.category_input.findText(new_cat)
            if idx >= 0:
                self.category_input.setCurrentIndex(idx)
        self._cancel_new_category()

    def _cancel_new_category(self):
        """Return to dropdown mode without adding anything."""
        self._custom_cat_input.hide()
        self._btn_confirm_cat.hide()
        self._btn_cancel_cat.hide()
        self.category_input.show()
        self._btn_new_cat.show()

    def _auto_detect_category(self, text: str):
        """Auto-select the most likely category as the user types the product name."""
        n = text.lower()
        if any(k in n for k in ["processor", "ryzen", "core i", "core ultra"]):
            cat = "Processors (CPU)"
        elif any(k in n for k in ["graphics", "rtx", " rx ", "radeon", "gpu"]):
            cat = "Graphics Cards (GPU)"
        elif "motherboard" in n:
            cat = "Motherboards"
        elif any(k in n for k in ["ram", "ddr"]):
            cat = "RAM"
        elif any(k in n for k in ["ssd", "hdd", "nvme"]):
            cat = "Storage"
        elif any(k in n for k in ["cooler", "cooling", "aio", "fan"]):
            cat = "Cooling"
        elif any(k in n for k in ["case", "chassis"]):
            cat = "Cases"
        elif any(k in n for k in ["psu", "power supply", "watt"]):
            cat = "Power Supply"
        elif "keyboard" in n:
            cat = "Keyboards"
        elif "mouse" in n:
            cat = "Mice"
        elif any(k in n for k in ["monitor", "display"]):
            cat = "Monitors"
        else:
            return  # don't reset to placeholder if no match
        idx = self.category_input.findText(cat)
        if idx >= 0:
            self.category_input.setCurrentIndex(idx)

    def _on_confirm(self):
        """Emit confirmed signal with form data — avoids QDialog.exec() crash."""
        self.confirmed.emit(self.get_data())
        self.close()

    def _on_cancel(self):
        """Emit cancelled signal and close."""
        self.cancelled.emit()
        self.close()

    def get_data(self) -> Dict:
        cat = self.category_input.currentText()
        if cat == "— Select Category —":
            cat = ""
        return {
            'product_name':   self.name_input.text().strip(),
            'category':       cat,
            'brand':          self.brand_input.text().strip(),
            'model':          self.model_input.text().strip(),
            'description':    self.desc_input.toPlainText().strip(),
            'stock_quantity': self.stock_spin.value()
        }

    def clear_form(self):
        self.name_input.clear(); self.brand_input.clear()
        self.model_input.clear(); self.desc_input.clear()
        self.stock_spin.setValue(0)
        self.category_input.setCurrentIndex(0)
        self._cancel_new_category()  # ensure dropdown mode on reset


# ── PRODUCT DETAIL WINDOW ─────────────────────────────────────────────────────
class ProductDetailDialog(QWidget):
    """
    Detail view for an inventory product — uses QWidget (not QDialog) to avoid
    the nested-event-loop crash (0xC0000409) with Matplotlib QtAgg on Windows.
    """

    def __init__(self, product: dict, parent=None):
        super().__init__(parent, Qt.WindowType.Window)
        self.setWindowTitle("Product Details")
        self.setFixedSize(500, 500)
        self.setAttribute(Qt.WidgetAttribute.WA_DeleteOnClose, True)
        self.setStyleSheet(f"background-color: {WHITE};")
        self._build_ui(product)

    def _build_ui(self, p: dict):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(32, 24, 32, 24)
        layout.setSpacing(0)

        # ── Header strip ─────────────────────────────────────────────────────
        header = QFrame()
        header.setStyleSheet(
            f"background-color: {PRIMARY}; border-radius: 8px; border: none;")
        header.setFixedHeight(56)
        hl = QHBoxLayout(header)
        hl.setContentsMargins(20, 0, 20, 0)

        title_lbl = QLabel("Product Details")
        title_lbl.setFont(QFont("Segoe UI", 14, QFont.Weight.Bold))
        title_lbl.setStyleSheet("color: white; border: none;")
        hl.addWidget(title_lbl)
        hl.addStretch()

        try:
            qty = int(p.get('stock_quantity') or 0)
        except (ValueError, TypeError):
            qty = 0

        if qty == 0:
            badge_clr, badge_txt = DANGER,  "Out of Stock"
        elif qty <= 10:
            badge_clr, badge_txt = WARNING, "Low Stock"
        else:
            badge_clr, badge_txt = SUCCESS, "Available"

        badge = QLabel(f"  {badge_txt}  ")
        badge.setFont(QFont("Segoe UI", 10, QFont.Weight.Bold))
        badge.setStyleSheet(
            f"color: white; background-color: {badge_clr};"
            " border-radius: 10px; padding: 2px 8px; border: none;")
        hl.addWidget(badge)
        layout.addWidget(header)
        layout.addSpacing(20)

        # ── Fields card ───────────────────────────────────────────────────────
        card = QFrame()
        card.setStyleSheet(
            f"QFrame {{ background-color: #f8f9fa; border-radius: 8px;"
            f" border: 1px solid {BORDER}; }}")
        fl = QVBoxLayout(card)
        fl.setContentsMargins(20, 12, 20, 12)
        fl.setSpacing(0)

        rows = [
            ("Product ID",   str(p.get('product_id',    '') or '—')),
            ("Product Name", str(p.get('product_name',  '') or '—')),
            ("Category",     str(p.get('category',      '') or '—')),
            ("Brand",        str(p.get('brand',         '') or '—')),
            ("Model",        str(p.get('model',         '') or '—')),
            ("Description",  str(p.get('description',   '') or '—')),
            ("Stock Qty",    str(qty)),
            ("Date Added",   str(p.get('created_at',    '') or '—')),
            ("Last Updated", str(p.get('updated_at',    '') or '—')),
        ]
        for i, (lbl_txt, val_txt) in enumerate(rows):
            row_w = QWidget()
            row_w.setStyleSheet("background: transparent; border: none;")
            rh = QHBoxLayout(row_w)
            rh.setContentsMargins(0, 7, 0, 7)
            rh.setSpacing(12)

            lbl = QLabel(lbl_txt)
            lbl.setFixedWidth(120)
            lbl.setFont(QFont("Segoe UI", 10, QFont.Weight.Bold))
            lbl.setStyleSheet(f"color: {SUBTEXT}; border: none;")
            rh.addWidget(lbl)

            val = QLabel(val_txt)
            val.setFont(QFont("Segoe UI", 10))
            val.setStyleSheet(f"color: {TEXT}; border: none;")
            val.setWordWrap(True)
            rh.addWidget(val, 1)
            fl.addWidget(row_w)

            if i < len(rows) - 1:
                sep = QFrame()
                sep.setFrameShape(QFrame.Shape.HLine)
                sep.setStyleSheet(
                    f"border: none; border-top: 1px solid {BORDER};"
                    " background: transparent;")
                fl.addWidget(sep)

        layout.addWidget(card)
        layout.addStretch()

        # ── Close button ──────────────────────────────────────────────────────
        close_btn = QPushButton("Close")
        close_btn.setFixedHeight(38)
        close_btn.setFixedWidth(120)
        close_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        close_btn.setStyleSheet(
            f"QPushButton {{ background-color: {PRIMARY}; color: white;"
            " font-weight: bold; border-radius: 6px; border: none; font-size: 13px; }"
            f" QPushButton:hover {{ background-color: #005f8a; }}")
        close_btn.clicked.connect(self.close)

        btn_row = QHBoxLayout()
        btn_row.addStretch()
        btn_row.addWidget(close_btn)
        layout.addLayout(btn_row)
        layout.addLayout(btn_row)