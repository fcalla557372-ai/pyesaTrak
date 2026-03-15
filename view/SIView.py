# SIView.py — Staff Inventory View (No dashboard dependency)
from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel,
                              QPushButton, QTableWidget, QTableWidgetItem,
                              QHeaderView, QAbstractItemView, QFrame, QDialog,
                              QComboBox, QSpinBox, QLineEdit, QTextEdit)
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QFont, QColor

PRIMARY = '#0076aa'
WHITE   = '#ffffff'
TEXT    = '#1a1a1a'
SUBTEXT = '#757575'
DANGER  = '#D32F2F'
WARNING = '#F57C00'
SUCCESS = '#388E3C'
BORDER  = '#E0E0E0'
BG      = '#f4f6f8'


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


class InventoryView(QWidget):
    stock_in_clicked        = pyqtSignal()
    stock_out_clicked       = pyqtSignal()
    defect_clicked          = pyqtSignal()
    filter_all_clicked      = pyqtSignal()
    filter_low_stock_clicked    = pyqtSignal()
    filter_out_of_stock_clicked = pyqtSignal()
    filter_defective_clicked    = pyqtSignal()
    product_selected        = pyqtSignal(int)   # emits product_id on row click

    def __init__(self, color_scheme=None):
        super().__init__()
        self._active_filter   = "All"
        self._active_category = ""
        self._active_brand    = ""
        self._all_products    = []
        self._all_defects     = []
        self._current_mode    = "normal"
        self.init_ui()

    # ── Brand / Category handlers ─────────────────────────────────────────────
    def _on_brand_changed(self, text: str):
        self._active_brand = text if (text and text != "All Brands") else ""
        self._apply_local_filters()

    def _on_category_changed(self, text: str):
        self._active_category = text if (text and text != "All Categories") else ""
        self._active_brand = ""

        # Repopulate brand dropdown to only brands in selected category
        self.brand_combo.blockSignals(True)
        self.brand_combo.clear()
        self.brand_combo.addItem("All Brands")
        if self._active_category:
            brands = sorted({p.get("brand", "") for p in self._all_products
                             if p.get("category") == self._active_category
                             and p.get("brand")})
        else:
            brands = sorted({p.get("brand", "") for p in self._all_products
                             if p.get("brand")})
        for b in brands:
            self.brand_combo.addItem(b)
        self.brand_combo.blockSignals(False)

        self._apply_local_filters()

    def _apply_local_filters(self):
        """Apply active category + brand + search text to the cached product list."""
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

    def populate_brand_filter(self, brands: list):
        self.brand_combo.blockSignals(True)
        self.brand_combo.clear()
        self.brand_combo.addItem("All Brands")
        for b in brands:
            self.brand_combo.addItem(b)
        self.brand_combo.blockSignals(False)

    def populate_category_filter(self, categories: list):
        self.category_combo.blockSignals(True)
        self.category_combo.clear()
        self.category_combo.addItem("All Categories")
        for c in categories:
            self.category_combo.addItem(c)
        self.category_combo.blockSignals(False)

    # ── Filter dropdown helper ────────────────────────────────────────────────
    _FILTER_OPTIONS = [
        ("All Items",    "All"),
        ("Low Stock",    "Low"),
        ("Out of Stock", "Out"),
        ("Defective",    "Defect"),
    ]

    def _on_filter_changed(self, index):
        """Called when the filter dropdown selection changes."""
        key = self._FILTER_OPTIONS[index][1]
        self._active_filter = key
        self.search_input.blockSignals(True)
        self.search_input.clear()
        self.search_input.blockSignals(False)
        sig = {
            "All":    self.filter_all_clicked,
            "Low":    self.filter_low_stock_clicked,
            "Out":    self.filter_out_of_stock_clicked,
            "Defect": self.filter_defective_clicked,
        }
        sig[key].emit()

    def set_active_tab(self, tab_key):
        """Controller calls this to sync the dropdown after a programmatic filter."""
        idx_map = {"All": 0, "Low": 1, "Out": 2, "Defect": 3}
        self._active_filter = tab_key
        self.filter_combo.blockSignals(True)
        self.filter_combo.setCurrentIndex(idx_map.get(tab_key, 0))
        self.filter_combo.blockSignals(False)

    # ── UI build ──────────────────────────────────────────────────────────────
    def _lbl(self, text, style):
        """Create a styled QLabel inline."""
        l = QLabel(text)
        l.setStyleSheet(style)
        return l

    def init_ui(self):
        self.setWindowTitle("PyesaTrak - Staff Inventory")
        self.setStyleSheet("background-color: transparent;")

        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        card = QFrame()
        card.setStyleSheet(
            f"QFrame {{ background-color: {WHITE}; border-radius: 10px; border: none; }}")
        cl = QVBoxLayout(card)
        cl.setContentsMargins(20, 16, 20, 16)
        cl.setSpacing(10)

        # Title
        title = QLabel("Inventory (Staff)")
        title.setFont(QFont("Segoe UI", 16, QFont.Weight.Bold))
        title.setStyleSheet(f"color: {TEXT}; border: none;")
        cl.addWidget(title)

        # ── Row 1: Search + Filter + Brand + Category ────────────────────────
        filter_row = QHBoxLayout()
        filter_row.setSpacing(8)

        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("🔍  Search")
        self.search_input.setFixedHeight(34)
        self.search_input.setMaximumWidth(220)
        self.search_input.setStyleSheet(f"""
            QLineEdit {{
                border: 1px solid {BORDER}; border-radius: 17px;
                padding: 4px 14px; color: {TEXT}; background: {WHITE};
                font-size: 13px;
            }}
            QLineEdit:focus {{ border-color: {PRIMARY}; }}
        """)
        self.search_input.textChanged.connect(self._on_search)
        filter_row.addWidget(self.search_input)

        _combo_style = f"""
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
        """
        _lbl_style = f"color: {TEXT}; font-weight: bold; font-size: 13px; border: none;"

        filter_row.addWidget(self._lbl("Filter", _lbl_style))
        filter_row.addWidget(self._lbl("▼", f"color: {PRIMARY}; font-size: 13px; border: none;"))

        self.filter_combo = QComboBox()
        for label, _ in self._FILTER_OPTIONS:
            self.filter_combo.addItem(label)
        self.filter_combo.setFixedHeight(34)
        self.filter_combo.setFixedWidth(150)
        self.filter_combo.setStyleSheet(_combo_style)
        self.filter_combo.currentIndexChanged.connect(self._on_filter_changed)
        filter_row.addWidget(self.filter_combo)

        filter_row.addWidget(self._lbl("Brand:", _lbl_style))
        self.brand_combo = QComboBox()
        self.brand_combo.addItem("All Brands")
        self.brand_combo.setFixedHeight(34)
        self.brand_combo.setFixedWidth(140)
        self.brand_combo.setStyleSheet(_combo_style)
        self.brand_combo.currentTextChanged.connect(self._on_brand_changed)
        filter_row.addWidget(self.brand_combo)

        filter_row.addWidget(self._lbl("Category:", _lbl_style))
        self.category_combo = QComboBox()
        self.category_combo.addItem("All Categories")
        self.category_combo.setFixedHeight(34)
        self.category_combo.setFixedWidth(160)
        self.category_combo.setStyleSheet(_combo_style)
        self.category_combo.currentTextChanged.connect(self._on_category_changed)
        filter_row.addWidget(self.category_combo)

        filter_row.addStretch()
        cl.addLayout(filter_row)

        # ── Row 2: Action buttons ────────────────────────────────────────────
        btn_row = QHBoxLayout()
        btn_row.setSpacing(10)

        self.btn_in  = QPushButton("[+] Stock In")
        self.btn_out = QPushButton("[-] Stock Out")
        self.btn_def = QPushButton("[!] Report Defect")

        self.btn_in.setStyleSheet(
            f"QPushButton {{ background-color: {SUCCESS}; color: white; font-weight: bold;"
            " border-radius: 8px; padding: 8px 20px; font-size: 13px; border: none; }"
            " QPushButton:hover { background-color: #1B5E20; }")
        self.btn_out.setStyleSheet(
            f"QPushButton {{ background-color: {PRIMARY}; color: white; font-weight: bold;"
            " border-radius: 8px; padding: 8px 20px; font-size: 13px; border: none; }"
            " QPushButton:hover { background-color: #005580; }")
        self.btn_def.setStyleSheet(
            f"QPushButton {{ background-color: {DANGER}; color: white; font-weight: bold;"
            " border-radius: 8px; padding: 8px 20px; font-size: 13px; border: none; }"
            " QPushButton:hover { background-color: #A52020; }")

        for btn in [self.btn_in, self.btn_out, self.btn_def]:
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            btn.setFixedHeight(38)
            btn_row.addWidget(btn)

        btn_row.addStretch()

        self.btn_in.clicked.connect(self.stock_in_clicked.emit)
        self.btn_out.clicked.connect(self.stock_out_clicked.emit)
        self.btn_def.clicked.connect(self.defect_clicked.emit)
        cl.addLayout(btn_row)

        # ── Table ─────────────────────────────────────────────────────────────
        self.product_table = ToggleTableWidget()
        self.product_table.verticalHeader().setVisible(False)
        self.product_table.setSelectionBehavior(
            QAbstractItemView.SelectionBehavior.SelectRows)
        self.product_table.setSelectionMode(
            QAbstractItemView.SelectionMode.SingleSelection)
        self.product_table.setEditTriggers(
            QAbstractItemView.EditTrigger.NoEditTriggers)
        self.product_table.setShowGrid(False)
        self.product_table.setFrameShape(QFrame.Shape.NoFrame)
        # NoFocus would block the :selected visual state — use StrongFocus instead
        self.product_table.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        self.product_table.setAlternatingRowColors(True)
        self.product_table.cellClicked.connect(self._on_row_clicked)
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
            QTableWidget::item:alternate:selected {{
                background-color: #d0eaf8; color: {TEXT};
            }}
        """)
        cl.addWidget(self.product_table)
        main_layout.addWidget(card)

    # ── Row selection ─────────────────────────────────────────────────────────
    def _on_row_clicked(self, row, col):
        """Emit the product_id of the clicked row (normal mode only)."""
        if self._current_mode == "defect":
            return  # defect rows don't map to a stock-actionable product_id
        item = self.product_table.item(row, 0)
        if item:
            try:
                self.product_selected.emit(int(item.text()))
            except ValueError:
                pass

    def get_selected_product_id(self):
        """Returns the product_id of the currently selected row, or None."""
        r = self.product_table.currentRow()
        if r >= 0 and self._current_mode == "normal":
            item = self.product_table.item(r, 0)
            if item:
                try:
                    return int(item.text())
                except ValueError:
                    pass
        return None

    # ── Search ────────────────────────────────────────────────────────────────
    def _on_search(self, text: str):
        q = text.strip().lower()
        if self._current_mode == "defect":
            pool = self._all_defects if not q else [
                p for p in self._all_defects
                if q in p.get("product_name", "").lower()
                or q in p.get("brand", "").lower()
                or q in p.get("defect_reason", "").lower()
            ]
            self._render_defective(pool)
        else:
            # Respect active category + brand alongside text search
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

    # ── Data display ──────────────────────────────────────────────────────────
    def load_table(self, products):
        """Called by controller — replaces full product cache and re-applies filters."""
        self._current_mode = "normal"
        self._all_products = list(products)
        # Re-apply any active category/brand/search so view stays consistent
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

    def _render_products(self, products):
        cols = ["Product ID", "Product Name", "Brand", "Model", "Stock", "Status"]
        self.product_table.setColumnCount(len(cols))
        self.product_table.setHorizontalHeaderLabels(cols)
        self.product_table.horizontalHeader().setSectionResizeMode(
            QHeaderView.ResizeMode.Stretch)
        self.product_table.setRowCount(len(products))

        for row, p in enumerate(products):
            self.product_table.setRowHeight(row, 42)
            self.product_table.setItem(row, 0, self._item(str(p['product_id']), center=True))
            self.product_table.setItem(row, 1, self._item(p['product_name']))
            self.product_table.setItem(row, 2, self._item(p.get('brand', '')))
            self.product_table.setItem(row, 3, self._item(p.get('model', '')))

            try:
                qty = int(p['stock_quantity'] or 0)
            except (ValueError, TypeError):
                qty = 0
            qty_item = self._item(str(qty), center=True)
            if qty <= 10:
                qty_item.setForeground(QColor(DANGER))
                qty_item.setFont(QFont("Segoe UI", 12, QFont.Weight.Bold))
            self.product_table.setItem(row, 4, qty_item)

            if qty == 0:
                status, color = "Out of Stock", DANGER
            elif qty <= 10:
                status, color = "Low Stock", WARNING
            else:
                status, color = "Available", SUCCESS
            st_item = self._item(status, center=True)
            st_item.setForeground(QColor(color))
            self.product_table.setItem(row, 5, st_item)

    def load_defective_table(self, products):
        """Called by controller for defective view."""
        self._current_mode = "defect"
        self._all_defects = list(products)
        self._render_defective(products)

    def _render_defective(self, products):
        cols = ["Defective ID", "Product Name", "Brand", "Model",
                "Defective Qty", "Defect Reason"]
        self.product_table.setColumnCount(len(cols))
        self.product_table.setHorizontalHeaderLabels(cols)
        hh = self.product_table.horizontalHeader()
        hh.setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        hh.setSectionResizeMode(5, QHeaderView.ResizeMode.ResizeToContents)
        self.product_table.setRowCount(len(products))

        for row, p in enumerate(products):
            self.product_table.setRowHeight(row, 42)
            self.product_table.setItem(row, 0, self._item(str(p['defect_id']), center=True))
            self.product_table.setItem(row, 1, self._item(p['product_name']))
            self.product_table.setItem(row, 2, self._item(p.get('brand', '')))
            self.product_table.setItem(row, 3, self._item(p.get('model', '')))

            qty_item = self._item(str(p['defective_qty']), center=True)
            qty_item.setForeground(QColor(DANGER))
            qty_item.setFont(QFont("Segoe UI", 12, QFont.Weight.Bold))
            self.product_table.setItem(row, 4, qty_item)

            reason_item = self._item(p.get('defect_reason', 'N/A'))
            reason_item.setForeground(QColor(DANGER))
            self.product_table.setItem(row, 5, reason_item)

    def _item(self, text: str, center: bool = False) -> QTableWidgetItem:
        item = QTableWidgetItem(str(text))
        if center:
            item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
        return item

    # Keep old method name for compatibility
    def make_item(self, text, center=False):
        return self._item(text, center)

    def get_selected_product(self):
        r = self.product_table.currentRow()
        if r >= 0:
            return {
                'product_id':    int(self.product_table.item(r, 0).text()),
                'product_name':  self.product_table.item(r, 1).text(),
                'brand':         self.product_table.item(r, 2).text(),
                'model':         self.product_table.item(r, 3).text(),
                'stock_quantity': int(self.product_table.item(r, 4).text())
            }
        return None


# ── TRANSACTION DIALOGS ───────────────────────────────────────────────────────
# These use QDialog.exec() which is safe for Staff because StaffMainWindow
# has no Matplotlib — no nested event loop conflict.

_COMBO_STYLE = (
    f"QComboBox {{ border: 1px solid {BORDER}; border-radius: 8px;"
    f" padding: 8px; color: {TEXT}; background-color: {WHITE}; }}"
    f" QComboBox QAbstractItemView {{ background: {WHITE}; color: {TEXT};"
    " selection-background-color: #d0eaf8; }"
)


class BaseTransactionDialog(QDialog):
    def __init__(self, title, parent=None):
        super().__init__(parent)
        self.setWindowTitle(title)
        self.setFixedSize(420, 500)
        self.setStyleSheet(f"""
            QDialog {{ background-color: {WHITE}; }}
            QLabel {{ color: {TEXT}; font-weight: bold; margin-bottom: 2px; border: none; }}
            QLabel#Header {{ color: {PRIMARY}; font-size: 20px; margin-bottom: 15px; }}
            QLineEdit, QSpinBox, QTextEdit, QComboBox {{
                border: 1px solid {BORDER}; border-radius: 8px;
                padding: 8px; color: {TEXT}; background-color: {WHITE};
            }}
            QPushButton {{ border-radius: 8px; padding: 8px 20px;
                           font-weight: bold; color: white; }}
        """)
        self._layout = QVBoxLayout(self)
        self._layout.setContentsMargins(40, 30, 40, 30)
        self._layout.setSpacing(10)
        self.title_lbl = QLabel(title)
        self.title_lbl.setObjectName("Header")
        self.title_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._layout.addWidget(self.title_lbl)

    def add_field(self, label_text, widget):
        lbl = QLabel(label_text)
        lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._layout.addWidget(lbl)
        self._layout.addWidget(widget)
        self._layout.addSpacing(6)

    def add_buttons(self, confirm_color):
        self._layout.addStretch()
        h = QHBoxLayout()
        h.setSpacing(15)
        cancel = QPushButton("Cancel")
        cancel.setCursor(Qt.CursorShape.PointingHandCursor)
        cancel.setStyleSheet("QPushButton { background-color: #888; color: white;"
                             " border-radius: 8px; padding: 8px 20px; font-weight: bold; }")
        cancel.clicked.connect(self.reject)
        confirm = QPushButton("Confirm")
        confirm.setCursor(Qt.CursorShape.PointingHandCursor)
        confirm.setStyleSheet(
            f"QPushButton {{ background-color: {confirm_color}; color: white;"
            " border-radius: 8px; padding: 8px 20px; font-weight: bold; }")
        confirm.clicked.connect(self.accept)
        h.addWidget(cancel)
        h.addWidget(confirm)
        self._layout.addLayout(h)


class StockInDialog(BaseTransactionDialog):
    def __init__(self, product_list, parent=None, preselected_id=None):
        super().__init__("Stock In", parent)
        self.selected_product_id = None

        self.product_combo = QComboBox()
        self.product_combo.setEditable(True)
        for p in product_list:
            self.product_combo.addItem(
                f"{p['product_name']} ({p.get('brand', '')})", userData=p)
        self.product_combo.currentIndexChanged.connect(self._update_info)
        self.add_field("Select Product", self.product_combo)

        self.stock_lbl = QLabel("Current Stock: —")
        self.stock_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.stock_lbl.setStyleSheet(
            f"color: {SUBTEXT}; font-weight: normal; border: none;")
        self._layout.addWidget(self.stock_lbl)

        self.qty = QSpinBox()
        self.qty.setRange(1, 10000)
        self.qty.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.qty.setButtonSymbols(QSpinBox.ButtonSymbols.NoButtons)
        self.add_field("Add Quantity", self.qty)

        self.remarks = QLineEdit()
        self.remarks.setPlaceholderText("Remarks (optional)")
        self.remarks.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.add_field("Remarks", self.remarks)
        self.add_buttons(SUCCESS)
        self._update_info()
        if preselected_id is not None:
            self._preselect(preselected_id)

    def _preselect(self, product_id):
        for i in range(self.product_combo.count()):
            d = self.product_combo.itemData(i)
            if d and d['product_id'] == product_id:
                self.product_combo.setCurrentIndex(i)
                break

    def _update_info(self):
        idx = self.product_combo.currentIndex()
        if idx >= 0:
            data = self.product_combo.itemData(idx)
            if data:
                self.stock_lbl.setText(f"Current Stock: {data['stock_quantity']}")
                self.selected_product_id = data['product_id']

    def get_data(self):
        return self.selected_product_id, self.qty.value(), self.remarks.text()


class StockOutDialog(BaseTransactionDialog):
    def __init__(self, product_list, parent=None, preselected_id=None):
        super().__init__("Stock Out", parent)
        self.selected_product_id = None

        self.product_combo = QComboBox()
        self.product_combo.setEditable(True)
        for p in product_list:
            self.product_combo.addItem(
                f"{p['product_name']} ({p.get('brand', '')})", userData=p)
        self.product_combo.currentIndexChanged.connect(self._update_info)
        self.add_field("Select Product", self.product_combo)

        self.stock_lbl = QLabel("Current Stock: —")
        self.stock_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.stock_lbl.setStyleSheet(
            f"color: {SUBTEXT}; font-weight: normal; border: none;")
        self._layout.addWidget(self.stock_lbl)

        self.qty = QSpinBox()
        self.qty.setRange(1, 1)
        self.qty.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.qty.setButtonSymbols(QSpinBox.ButtonSymbols.NoButtons)
        self.add_field("Remove Quantity", self.qty)

        self.reason = QLineEdit()
        self.reason.setPlaceholderText("Reason")
        self.reason.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.add_field("Reason", self.reason)
        self.add_buttons(PRIMARY)
        self._update_info()
        if preselected_id is not None:
            self._preselect(preselected_id)

    def _preselect(self, product_id):
        for i in range(self.product_combo.count()):
            d = self.product_combo.itemData(i)
            if d and d['product_id'] == product_id:
                self.product_combo.setCurrentIndex(i)
                break

    def _update_info(self):
        idx = self.product_combo.currentIndex()
        if idx >= 0:
            data = self.product_combo.itemData(idx)
            if data:
                stock = data['stock_quantity']
                self.stock_lbl.setText(f"Current Stock: {stock}")
                self.selected_product_id = data['product_id']
                if stock > 0:
                    self.qty.setRange(1, stock)
                    self.qty.setEnabled(True)
                else:
                    self.qty.setRange(0, 0)
                    self.qty.setEnabled(False)

    def get_data(self):
        return self.selected_product_id, self.qty.value(), self.reason.text()


class DefectDialog(BaseTransactionDialog):
    def __init__(self, product_list, parent=None, preselected_id=None):
        super().__init__("Report Defect", parent)
        self.selected_product_id = None

        self.product_combo = QComboBox()
        self.product_combo.setEditable(True)
        for p in product_list:
            self.product_combo.addItem(
                f"{p['product_name']} ({p.get('brand', '')})", userData=p)
        self.product_combo.currentIndexChanged.connect(self._update_info)
        self.add_field("Select Product", self.product_combo)

        self.stock_lbl = QLabel("Current Stock: —")
        self.stock_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.stock_lbl.setStyleSheet(
            f"color: {SUBTEXT}; font-weight: normal; border: none;")
        self._layout.addWidget(self.stock_lbl)

        self.qty = QSpinBox()
        self.qty.setRange(1, 1)
        self.qty.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.qty.setButtonSymbols(QSpinBox.ButtonSymbols.NoButtons)
        self.add_field("Defective Qty", self.qty)

        self.defect_type = QComboBox()
        self.defect_type.addItems(["Damaged", "Expired", "Missing Parts", "Other"])
        self.add_field("Defect Type", self.defect_type)

        self.desc = QTextEdit()
        self.desc.setFixedHeight(60)
        self.desc.setPlaceholderText("Description (optional)")
        self.add_field("Description", self.desc)
        self.add_buttons(DANGER)
        self._update_info()
        if preselected_id is not None:
            self._preselect(preselected_id)

    def _preselect(self, product_id):
        for i in range(self.product_combo.count()):
            d = self.product_combo.itemData(i)
            if d and d['product_id'] == product_id:
                self.product_combo.setCurrentIndex(i)
                break

    def _update_info(self):
        idx = self.product_combo.currentIndex()
        if idx >= 0:
            data = self.product_combo.itemData(idx)
            if data:
                stock = data['stock_quantity']
                self.stock_lbl.setText(f"Current Stock: {stock}")
                self.selected_product_id = data['product_id']
                if stock > 0:
                    self.qty.setRange(1, stock)
                    self.qty.setEnabled(True)
                else:
                    self.qty.setRange(0, 0)
                    self.qty.setEnabled(False)

    def get_data(self):
        return (
            self.selected_product_id,
            self.qty.value(),
            self.defect_type.currentText(),
            self.desc.toPlainText().strip()
        )

# ── SIGN-OUT DIALOG ───────────────────────────────────────────────────────────
# Moved from SIController.py — UI construction belongs in the View layer.

from PyQt6.QtWidgets import QDialog

class CustomMessageBox(QDialog):
    """Frameless sign-out confirmation dialog."""
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


# ── STAFF MAIN WINDOW ─────────────────────────────────────────────────────────
# Moved from SIController.py — window layout belongs in the View layer.

class StaffMainWindow(QWidget):
    """
    Staff-facing main window.
    Shows the inventory page directly — no dashboard, no Matplotlib dependency.
    """
    sign_out_requested = pyqtSignal()

    def __init__(self, user_data=None):
        super().__init__()
        self.user_data = user_data
        self.setWindowTitle("PyesaTrak - Staff")
        self.setFixedSize(1280, 760)
        self.setStyleSheet("background-color: #F5F5F5; font-family: 'Segoe UI', Arial;")
        self._build_ui()

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
        app_title.setStyleSheet("color: white; margin-bottom: 30px; border: none;")
        app_title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        sl.addWidget(app_title)

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

        if self.user_data:
            fname = self.user_data.get('userFname', '')
            lname = self.user_data.get('userLname', '')
            name  = f"{fname} {lname}".strip() or self.user_data.get('username', '')
            user_lbl = QLabel(name)
            user_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
            user_lbl.setStyleSheet(
                "color: #9E9E9E; font-size: 11px; border: none; margin-bottom: 6px;")
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
        sign_out.clicked.connect(self._on_sign_out_clicked)
        sl.addWidget(sign_out)
        root.addWidget(sidebar)

        # Content area — inventory widget is inserted by SIController after init
        content = QWidget()
        content.setStyleSheet("background-color: #F5F5F5;")
        self.content_layout = QVBoxLayout(content)
        self.content_layout.setContentsMargins(30, 30, 30, 30)

        self.inventory_view = InventoryView()
        self.content_layout.addWidget(self.inventory_view)
        root.addWidget(content)

    def _on_sign_out_clicked(self):
        """Show confirmation dialog; emit signal if confirmed so Controller can act."""
        dlg = CustomMessageBox(self)
        if dlg.exec():
            self.sign_out_requested.emit()

    def show(self):
        super().show()