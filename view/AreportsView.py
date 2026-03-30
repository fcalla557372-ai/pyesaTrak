# AreportsView.py — Reports page only (Analytics lives in its own sidebar tab)
from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel,
                             QPushButton, QTableWidget, QTableWidgetItem,
                             QHeaderView, QAbstractItemView, QFrame, QComboBox,
                             QDateEdit, QDialog)
from PyQt6.QtCore import Qt, QDate, pyqtSignal
from PyQt6.QtGui import QFont, QColor

PRIMARY  = '#0076aa'
WHITE    = '#ffffff'
BG       = '#f4f6f8'
TEXT     = '#1a1a1a'
SUBTEXT  = '#757575'
DANGER   = '#D32F2F'
WARNING  = '#F57C00'
SUCCESS  = '#27ae60'
BORDER   = '#E0E0E0'


# ─────────────────────────────────────────────────────────────────────────────
#  REPORTS PAGE  (filter bar + history / generated-data table)
# ─────────────────────────────────────────────────────────────────────────────

class ReportsPage(QWidget):
    row_double_clicked = pyqtSignal(int)   # emits report_id when a history row is double-clicked

    def __init__(self):
        super().__init__()
        self.setStyleSheet("background-color: transparent;")
        self._build_ui()
        self._report_ids = []   # parallel list of report_ids matching table rows

    def _build_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(12)

        # ── Filter bar ───────────────────────────────────────────────────────
        filter_card = QFrame()
        filter_card.setStyleSheet(
            f"QFrame {{ background-color: {WHITE}; border-radius: 10px; border: 1px solid {BORDER}; }}")
        fc = QHBoxLayout(filter_card)
        fc.setContentsMargins(16, 12, 16, 12)
        fc.setSpacing(10)

        lbl_style   = f"color: {SUBTEXT}; font-weight: bold; border: none; font-size: 12px;"
        input_style = (f"padding: 5px 10px; border: 1px solid {BORDER}; border-radius: 6px;"
                       f" color: {TEXT}; background: {WHITE}; font-size: 12px;")

        fc.addWidget(self._lbl("Type:", lbl_style))
        self.report_type_combo = QComboBox()
        self.report_type_combo.addItems(
            ["Inventory Status", "Stock Movement", "Defects Report",
             "Low Stock Report", "Out of Stock Report", "Defective Stock Report",
             "User Activity"])
        self.report_type_combo.setFixedWidth(155)
        self.report_type_combo.setStyleSheet(input_style)
        fc.addWidget(self.report_type_combo)

        fc.addWidget(self._lbl("From:", lbl_style))
        self.start_date = QDateEdit()
        self.start_date.setCalendarPopup(True)
        self.start_date.setDate(QDate.currentDate().addDays(-30))
        self.start_date.setFixedWidth(120)
        self.start_date.setStyleSheet(input_style)
        fc.addWidget(self.start_date)

        fc.addWidget(self._lbl("To:", lbl_style))
        self.end_date = QDateEdit()
        self.end_date.setCalendarPopup(True)
        self.end_date.setDate(QDate.currentDate())
        self.end_date.setFixedWidth(120)
        self.end_date.setStyleSheet(input_style)
        fc.addWidget(self.end_date)

        self.generate_btn = QPushButton("Generate Report")
        self.generate_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.generate_btn.setFixedHeight(34)
        self.generate_btn.setStyleSheet(f"""
            QPushButton {{ background-color: {PRIMARY}; color: white; font-weight: bold;
                          border-radius: 6px; padding: 4px 16px; font-size: 12px; border: none; }}
            QPushButton:hover {{ background-color: #005f8a; }}
        """)
        fc.addWidget(self.generate_btn)
        fc.addStretch()

        self.export_btn = QPushButton("Export to PDF")
        self.export_btn.setEnabled(False)
        self.export_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.export_btn.setFixedHeight(34)
        self.export_btn.setStyleSheet("""
            QPushButton { background-color: #ccc; color: white; font-weight: bold;
                          border-radius: 6px; padding: 4px 14px; font-size: 12px; border: none; }
        """)
        fc.addWidget(self.export_btn)
        root.addWidget(filter_card)

        # ── Report table ─────────────────────────────────────────────────────
        table_card = QFrame()
        table_card.setStyleSheet(
            f"QFrame {{ background-color: {WHITE}; border-radius: 10px; border: 1px solid {BORDER}; }}")
        tc = QVBoxLayout(table_card)
        tc.setContentsMargins(0, 0, 0, 0)

        self.report_table = QTableWidget()
        self.report_table.setShowGrid(True)
        self.report_table.setAlternatingRowColors(True)
        self.report_table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.report_table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.report_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.report_table.verticalHeader().setVisible(False)
        self.report_table.setStyleSheet(f"""
            QTableWidget {{ border: none; background-color: {WHITE}; color: {TEXT};
                           font-size: 13px; outline: 0; border-radius: 10px; }}
            QHeaderView::section {{ background-color: {TEXT}; color: white;
                                   padding: 10px 8px; font-weight: bold; border: none; font-size: 12px; }}
            QTableWidget::item {{ padding: 9px 8px; border-bottom: 1px solid #f0f0f0; color: {TEXT}; }}
            QTableWidget::item:selected {{ background-color: #d0eaf8; color: {TEXT}; }}
            QTableWidget::item:alternate {{ background-color: #fafafa; }}
        """)
        self.report_table.cellDoubleClicked.connect(self._on_row_clicked)
        tc.addWidget(self.report_table)
        root.addWidget(table_card)

    def _lbl(self, text, style):
        lbl = QLabel(text)
        lbl.setStyleSheet(style)
        return lbl

    def load_reports(self, data):
        self._report_ids = [row.get('report_id') for row in data]
        self.report_table.clear()
        self.report_table.setColumnCount(5)
        self.report_table.setHorizontalHeaderLabels(
            ["ID", "Report Name", "Type", "Created By", "Date"])
        self.report_table.setRowCount(len(data))
        for r, row in enumerate(data):
            self.report_table.setRowHeight(r, 42)
            for c, key in enumerate(
                    ['report_id', 'report_name', 'report_type', 'requested_by', 'transaction_date']):
                val = row.get(key, '')
                item = QTableWidgetItem(str(val) if val else '')
                item.setForeground(QColor(TEXT))
                self.report_table.setItem(r, c, item)

    def display_generated_data(self, data):
        if not data:
            self.report_table.setRowCount(0)
            self.report_table.setColumnCount(0)
            self.report_table.clear()
            return

        self.export_btn.setEnabled(True)
        self.export_btn.setStyleSheet(f"""
            QPushButton {{ background-color: {DANGER}; color: white; font-weight: bold;
                          border-radius: 6px; padding: 4px 14px; font-size: 12px; border: none; }}
            QPushButton:hover {{ background-color: #a52020; }}
        """)

        columns = list(data[0].keys())
        self.report_table.clear()
        self.report_table.setColumnCount(len(columns))
        self.report_table.setHorizontalHeaderLabels(
            [c.replace('_', ' ').title() for c in columns])
        self.report_table.setRowCount(len(data))
        for r, row in enumerate(data):
            self.report_table.setRowHeight(r, 42)
            for c, key in enumerate(columns):
                val = row[key]
                if key == 'status' and not val:
                    qty = row.get('stock_quantity')
                    val = ("Available" if int(qty) > 0 else "Out of Stock") if qty is not None else "—"
                item = QTableWidgetItem(str(val) if val is not None else '')
                item.setForeground(QColor(TEXT))
                self.report_table.setItem(r, c, item)

    def _on_row_clicked(self, row, col):
        """Emit report_id for the clicked history row (not generated-data rows)."""
        if hasattr(self, '_report_ids') and row < len(self._report_ids):
            rid = self._report_ids[row]
            if rid is not None:
                self.row_double_clicked.emit(int(rid))

    def set_actions_enabled(self, enabled):
        pass


# ─────────────────────────────────────────────────────────────────────────────
#  MAIN REPORTS VIEW  (thin wrapper — no tab switcher needed any more)
# ─────────────────────────────────────────────────────────────────────────────

class ReportsView(QWidget):
    """
    Top-level widget for the Reports section.
    Analytics has its own dedicated sidebar tab (AnalyticsView / AnalyticsController).

    Controller interface (unchanged):
        view.generate_btn, view.export_btn,
        view.report_type_combo, view.start_date, view.end_date
        view.load_reports(data)
        view.display_generated_data(data)
        view.update_analytics(data)   ← kept as no-op for backward compat
    """

    def __init__(self):
        super().__init__()
        self.setStyleSheet("background-color: transparent;")
        self._build_ui()

    def _build_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(10)

        # Page title
        page_title = QLabel("Reports")
        page_title.setFont(QFont("Segoe UI", 16, QFont.Weight.Bold))
        page_title.setStyleSheet(f"color: {TEXT}; border: none;")
        root.addWidget(page_title)

        # Reports content
        self.reports_page = ReportsPage()
        root.addWidget(self.reports_page)

        # Controller aliases (backward-compatible)
        self.generate_btn      = self.reports_page.generate_btn
        self.export_btn        = self.reports_page.export_btn
        self.report_type_combo = self.reports_page.report_type_combo
        self.start_date        = self.reports_page.start_date
        self.end_date          = self.reports_page.end_date
        self.row_double_clicked = self.reports_page.row_double_clicked

    # ── Pass-throughs ─────────────────────────────────────────────────────────

    def load_reports(self, data):
        self.reports_page.load_reports(data)

    def display_generated_data(self, data):
        self.reports_page.display_generated_data(data)

    def set_actions_enabled(self, enabled):
        self.reports_page.set_actions_enabled(enabled)

    def update_analytics(self, analytics_data: dict):
        """No-op — analytics is handled by the dedicated Analytics tab."""
        pass


# ── REPORT DETAIL WINDOW ──────────────────────────────────────────────────────
class ReportDetailDialog(QWidget):
    """
    Detail view for a saved report — uses QWidget (not QDialog) to avoid
    the nested-event-loop crash (0xC0000409) caused by QDialog.exec() /
    QDialog.open() conflicting with Matplotlib QtAgg on Windows.
    """

    def __init__(self, report: dict, parent=None):
        super().__init__(parent, Qt.WindowType.Window)
        rtype_title = str(report.get('report_type', 'Report Details') or 'Report Details')
        self.setWindowTitle(rtype_title)
        self.setFixedSize(520, 500)
        self.setAttribute(Qt.WidgetAttribute.WA_DeleteOnClose, True)
        self.setStyleSheet(f"background-color: {WHITE};")
        self._build_ui(report)

    def _build_ui(self, r: dict):
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

        report_type_display = str(r.get('report_type', 'Report Details') or 'Report Details')
        title_lbl = QLabel(report_type_display)
        title_lbl.setFont(QFont("Segoe UI", 13, QFont.Weight.Bold))
        title_lbl.setStyleSheet("color: white; border: none;")
        hl.addWidget(title_lbl)
        hl.addStretch()

        status     = str(r.get('report_status') or 'Generated')
        clr_map    = {'Generated': '#888888', 'Processed': PRIMARY,
                      'Complete': SUCCESS, 'Validated': '#388E3C'}
        badge_clr  = clr_map.get(status, '#888888')
        badge      = QLabel(f"  {status}  ")
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

        start      = str(r.get('start_date',  '') or '')
        end        = str(r.get('end_date',    '') or '')
        rtype      = str(r.get('report_type', '') or '')
        period     = f"{start} to {end}" if (start and end) else "—"

        # Type-specific description of what the report contains
        _type_descriptions = {
            "Inventory Status":      "Snapshot of current stock levels across all product categories — product ID, name, brand, model, quantity, status, and last updated.",
            "Stock Movement":        f"All Stock In, Stock Out, and Defect transactions from {start} to {end} — transaction date, type, product, brand, quantity, remarks, and processed by.",
            "Defects Report":        f"Defect incidents logged from {start} to {end} — transaction date, product name, brand, defective quantity, remarks, and reported by.",
            "Low Stock Report":      "Snapshot of all products currently at or below the low stock threshold (≤10 units) — product ID, name, brand, model, category, quantity, status.",
            "Out of Stock Report":   "Snapshot of all products currently at zero stock — product ID, name, brand, model, category, and last updated date.",
            "Defective Stock Report": f"Defective item ledger from {start} to {end} — Defect ID, reported date, product ID, name, brand, category, defective quantity, defect type, description, and reported by.",
            "User Activity":         f"Login activity log from {start} to {end} — login ID, user name, role, and login timestamp.",
        }
        report_contents = _type_descriptions.get(rtype, f"Report data for {rtype}.")

        rows = [
            ("Report ID",       str(r.get('report_id',    '') or '—')),
            ("Report Type",     rtype or '—'),
            ("Period",          period),
            ("Report Contents", report_contents),
            ("Generated On",    str(r.get('created_at',   '') or '—')),
            ("Requested By",    str(r.get('requested_by', '') or '—')),
            ("Processed By",    str(r.get('processed_by', '') or '—')),
            ("Status",          status),
        ]
        for i, (lbl_txt, val_txt) in enumerate(rows):
            row_w = QWidget()
            row_w.setStyleSheet("background: transparent; border: none;")
            rh = QHBoxLayout(row_w)
            rh.setContentsMargins(0, 7, 0, 7)
            rh.setSpacing(12)

            lbl = QLabel(lbl_txt)
            lbl.setFixedWidth(130)
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
        layout.addLayout(btn_row)# report_exporter.py — PDF export helper (View-layer concern extracted from Controller)
"""
Presentation Layer Helper
Responsibilities:
- Build and style the PDF document
- Format data rows for export
- NO database queries, NO business logic
"""
from datetime import datetime

from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_CENTER
from reportlab.lib.units import inch


class ReportExporter:
    """Handles all PDF generation logic for inventory reports."""

    def generate(self, filename: str, report_type: str, date_range: dict,
                 data: list, user_data: dict | None) -> None:
        """
        Build and save a PDF report to disk.

        Args:
            filename:    Full output path for the PDF file.
            report_type: Human-readable report name (e.g. 'Stock Movement').
            date_range:  Dict with 'start' and 'end' date strings.
            data:        List of row dicts from the model.
            user_data:   Current user dict (may be None).
        """
        doc = SimpleDocTemplate(
            filename, pagesize=letter,
            rightMargin=0.75 * inch, leftMargin=0.75 * inch,
            topMargin=1 * inch, bottomMargin=0.75 * inch)

        elements = []
        styles = getSampleStyleSheet()

        title_style = ParagraphStyle(
            'CustomTitle', parent=styles['Heading1'],
            fontSize=24, textColor=colors.HexColor("#0076aa"),
            spaceAfter=30, alignment=TA_CENTER, fontName='Helvetica-Bold')

        header_style = ParagraphStyle(
            'CustomHeader', parent=styles['Heading2'],
            fontSize=14, textColor=colors.HexColor("#333333"),
            spaceAfter=12, fontName='Helvetica-Bold')

        elements.append(Paragraph("PyesaTrak Inventory Management System", title_style))
        elements.append(Paragraph(report_type, header_style))
        elements.append(Spacer(1, 20))

        # ── Metadata block ────────────────────────────────────────────────────
        if user_data:
            fname = user_data.get('userFname', '')
            lname = user_data.get('userLname', '')
            full_name = f"{fname} {lname}".strip() or user_data.get('username', 'Unknown')
            role = user_data.get('role', 'N/A')
        else:
            full_name = "System Admin"
            role = "Admin"

        full_name_with_role = f"{full_name} ({role})"
        transaction_datetime = datetime.now().strftime("%B %d, %Y at %I:%M %p")

        metadata = [
            ["Requested By:",     full_name_with_role],
            ["Processed By:",     full_name_with_role],
            ["Transaction Date:", transaction_datetime],
            ["Validated By:",     "_____________________"],
        ]
        if report_type not in ("Inventory Status", "Low Stock Report", "Out of Stock Report"):
            metadata.append([
                "Report Period:",
                f"{date_range['start']} to {date_range['end']}"
            ])
        metadata.append(["Total Records:", str(len(data))])

        meta_table = Table(metadata, colWidths=[2 * inch, 4 * inch])
        meta_table.setStyle(TableStyle([
            ('FONT',          (0, 0), (0, -1), 'Helvetica-Bold', 11),
            ('FONT',          (1, 0), (1, -1), 'Helvetica',      11),
            ('TEXTCOLOR',     (0, 0), (-1, -1), colors.HexColor("#333333")),
            ('VALIGN',        (0, 0), (-1, -1), 'MIDDLE'),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
            ('TOPPADDING',    (0, 0), (-1, -1), 4),
        ]))
        elements.append(meta_table)
        elements.append(Spacer(1, 30))

        # ── Data table ────────────────────────────────────────────────────────
        if not data:
            elements.append(Paragraph("No data available for this selection.", styles['Normal']))
        else:
            headers = [k.replace('_', ' ').title() for k in data[0].keys()]
            data_rows = [headers]
            for row in data:
                data_rows.append([str(v) if v is not None else "" for v in row.values()])

            data_table = Table(data_rows)
            data_table.setStyle(TableStyle([
                ('BACKGROUND',    (0, 0), (-1, 0),  colors.HexColor("#0076aa")),
                ('TEXTCOLOR',     (0, 0), (-1, 0),  colors.whitesmoke),
                ('ALIGN',         (0, 0), (-1, 0),  'CENTER'),
                ('FONTNAME',      (0, 0), (-1, 0),  'Helvetica-Bold'),
                ('FONTSIZE',      (0, 0), (-1, 0),  10),
                ('BOTTOMPADDING', (0, 0), (-1, 0),  12),
                ('TOPPADDING',    (0, 0), (-1, 0),  12),
                ('BACKGROUND',    (0, 1), (-1, -1), colors.white),
                ('TEXTCOLOR',     (0, 1), (-1, -1), colors.black),
                ('ALIGN',         (0, 1), (-1, -1), 'LEFT'),
                ('FONTNAME',      (0, 1), (-1, -1), 'Helvetica'),
                ('FONTSIZE',      (0, 1), (-1, -1), 9),
                ('TOPPADDING',    (0, 1), (-1, -1), 6),
                ('BOTTOMPADDING', (0, 1), (-1, -1), 6),
                ('GRID',          (0, 0), (-1, -1), 0.5, colors.grey),
                ('VALIGN',        (0, 0), (-1, -1), 'MIDDLE'),
                ('ROWBACKGROUNDS', (0, 1), (-1, -1),
                 [colors.white, colors.HexColor("#f5f5f5")]),
            ]))
            elements.append(data_table)

        # ── Signature block ───────────────────────────────────────────────────
        elements.append(Spacer(1, 40))
        elements.append(Paragraph("Validation & Approval", header_style))
        elements.append(Spacer(1, 10))

        sig_data = [
            ["Validated By:", "_____________________", "Date:",     "_____________________"],
            ["",              "",                       "",          ""],
            ["Signature:",    "_____________________", "Position:", "_____________________"],
        ]
        sig_table = Table(sig_data, colWidths=[1.2 * inch, 2 * inch, 0.8 * inch, 2 * inch])
        sig_table.setStyle(TableStyle([
            ('FONT',          (0, 0), (0, -1), 'Helvetica-Bold', 10),
            ('FONT',          (2, 0), (2, -1), 'Helvetica-Bold', 10),
            ('FONT',          (1, 0), (1, -1), 'Helvetica',      10),
            ('FONT',          (3, 0), (3, -1), 'Helvetica',      10),
            ('TEXTCOLOR',     (0, 0), (-1, -1), colors.HexColor("#333333")),
            ('VALIGN',        (0, 0), (-1, -1), 'MIDDLE'),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
        ]))
        elements.append(sig_table)
        elements.append(Spacer(1, 30))
        elements.append(Paragraph(
            "<i>This is a computer-generated report from PyesaTrak Inventory Management System. "
            "All data is accurate as of the transaction date listed above.</i>",
            ParagraphStyle('Footer', parent=styles['Normal'],
                           fontSize=8, textColor=colors.grey, alignment=TA_CENTER)
        ))

        doc.build(elements)
        print(f"✓ PDF exported: {filename}")