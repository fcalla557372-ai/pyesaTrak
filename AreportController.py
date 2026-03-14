# AreportController.py - Updated with Analytics loading
from AreportModel import ReportsModel
from AreportsView import ReportDetailDialog
from PyQt6.QtWidgets import QMessageBox, QFileDialog
from datetime import datetime

from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_CENTER
from reportlab.lib.units import inch


class ReportsController:
    def __init__(self, user_data=None):
        self.model = ReportsModel()
        self.view = None
        self.user_data = user_data
        self.current_report_data = []
        self.current_report_type = ""
        self.current_date_range = {"start": "", "end": ""}

    def set_view(self, view):
        self.view = view
        self.view.generate_btn.clicked.connect(self.handle_generate_report)
        self.view.export_btn.clicked.connect(self.handle_export_report)
        self.view.row_clicked.connect(self.handle_report_row_clicked)
        self.load_report_history()

    def load_report_history(self):
        try:
            reports = self.model.get_all_saved_reports()
            if self.view:
                self.view.load_reports(reports)
        except Exception as e:
            print(f"Error loading history: {e}")

    def handle_generate_report(self):
        rtype = self.view.report_type_combo.currentText()
        start = self.view.start_date.date().toString("yyyy-MM-dd")
        end   = self.view.end_date.date().toString("yyyy-MM-dd")

        self.current_report_type  = rtype
        self.current_date_range   = {"start": start, "end": end}
        data = []

        try:
            if rtype == "Stock Movement":
                data = self.model.get_stock_movement(start, end)
            elif rtype == "Inventory Status":
                data = self.model.get_inventory_status()
            elif rtype == "Defects Report":
                data = self.model.get_defective_report(start, end)
            elif rtype == "User Activity":
                data = self.model.get_user_activity(start, end)

            self.current_report_data = data

            if data:
                self.view.display_generated_data(data)
                print(f"✓ Generated {len(data)} rows for {rtype}")
            else:
                self.view.display_generated_data([])
                self.show_styled_message(
                    "No Data",
                    f"No data found for {rtype} in the selected date range.",
                    "Warning")

            if data:
                self.model.save_report_entry(rtype, start, end, self.user_data,
                                             transaction_id=None)

        except Exception as e:
            print(f"Report Generation Error: {e}")
            import traceback; traceback.print_exc()
            self.show_styled_message("Error", f"Failed to generate report: {e}", "Critical")

    def handle_export_report(self):
        if not self.current_report_data:
            self.show_styled_message(
                "Error", "No data to export. Please generate a report first.", "Warning")
            return

        default_filename = (f"{self.current_report_type.replace(' ', '_')}_"
                            f"{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf")

        filename, _ = QFileDialog.getSaveFileName(
            self.view, "Save PDF Report", default_filename, "PDF Files (*.pdf)")

        if filename:
            try:
                self.generate_pdf(filename)
                self.show_styled_message(
                    "Success", f"Report exported successfully to:\n{filename}", "Info")
            except Exception as e:
                print(f"PDF Export Error: {e}")
                import traceback; traceback.print_exc()
                self.show_styled_message("Error", f"Export failed: {e}", "Critical")

    def generate_pdf(self, filename):
        doc = SimpleDocTemplate(
            filename, pagesize=letter,
            rightMargin=0.75*inch, leftMargin=0.75*inch,
            topMargin=1*inch, bottomMargin=0.75*inch)

        elements = []
        styles   = getSampleStyleSheet()

        title_style = ParagraphStyle(
            'CustomTitle', parent=styles['Heading1'],
            fontSize=24, textColor=colors.HexColor("#0076aa"),
            spaceAfter=30, alignment=TA_CENTER, fontName='Helvetica-Bold')

        header_style = ParagraphStyle(
            'CustomHeader', parent=styles['Heading2'],
            fontSize=14, textColor=colors.HexColor("#333333"),
            spaceAfter=12, fontName='Helvetica-Bold')

        elements.append(Paragraph("PyesaTrak Inventory Management System", title_style))
        elements.append(Paragraph(self.current_report_type, header_style))
        elements.append(Spacer(1, 20))

        if self.user_data:
            fname = self.user_data.get('userFname', '')
            lname = self.user_data.get('userLname', '')
            full_name = f"{fname} {lname}".strip() or self.user_data.get('username', 'Unknown')
            role      = self.user_data.get('role', 'N/A')
        else:
            full_name = "System Admin"
            role      = "Admin"

        full_name_with_role = f"{full_name} ({role})"
        transaction_datetime = datetime.now().strftime("%B %d, %Y at %I:%M %p")

        metadata = [
            ["Requested By:",    full_name_with_role],
            ["Processed By:",    full_name_with_role],
            ["Transaction Date:", transaction_datetime],
            ["Validated By:",    "_____________________"],
        ]
        if self.current_report_type != "Inventory Status":
            metadata.append([
                "Report Period:",
                f"{self.current_date_range['start']} to {self.current_date_range['end']}"
            ])
        metadata.append(["Total Records:", str(len(self.current_report_data))])

        meta_table = Table(metadata, colWidths=[2*inch, 4*inch])
        meta_table.setStyle(TableStyle([
            ('FONT',      (0, 0), (0, -1), 'Helvetica-Bold', 11),
            ('FONT',      (1, 0), (1, -1), 'Helvetica',      11),
            ('TEXTCOLOR', (0, 0), (-1,-1), colors.HexColor("#333333")),
            ('VALIGN',    (0, 0), (-1,-1), 'MIDDLE'),
            ('BOTTOMPADDING', (0,0),(-1,-1), 8),
            ('TOPPADDING',    (0,0),(-1,-1), 4),
        ]))
        elements.append(meta_table)
        elements.append(Spacer(1, 30))

        if not self.current_report_data:
            elements.append(Paragraph("No data available for this selection.", styles['Normal']))
        else:
            headers   = [k.replace('_', ' ').title() for k in self.current_report_data[0].keys()]
            data_rows = [headers]
            for row in self.current_report_data:
                data_rows.append([str(v) if v is not None else "" for v in row.values()])

            data_table = Table(data_rows)
            data_table.setStyle(TableStyle([
                ('BACKGROUND',    (0,0), (-1,0),  colors.HexColor("#0076aa")),
                ('TEXTCOLOR',     (0,0), (-1,0),  colors.whitesmoke),
                ('ALIGN',         (0,0), (-1,0),  'CENTER'),
                ('FONTNAME',      (0,0), (-1,0),  'Helvetica-Bold'),
                ('FONTSIZE',      (0,0), (-1,0),  10),
                ('BOTTOMPADDING', (0,0), (-1,0),  12),
                ('TOPPADDING',    (0,0), (-1,0),  12),
                ('BACKGROUND',    (0,1), (-1,-1), colors.white),
                ('TEXTCOLOR',     (0,1), (-1,-1), colors.black),
                ('ALIGN',         (0,1), (-1,-1), 'LEFT'),
                ('FONTNAME',      (0,1), (-1,-1), 'Helvetica'),
                ('FONTSIZE',      (0,1), (-1,-1), 9),
                ('TOPPADDING',    (0,1), (-1,-1), 6),
                ('BOTTOMPADDING', (0,1), (-1,-1), 6),
                ('GRID',          (0,0), (-1,-1), 0.5, colors.grey),
                ('VALIGN',        (0,0), (-1,-1), 'MIDDLE'),
                ('ROWBACKGROUNDS',(0,1), (-1,-1),
                 [colors.white, colors.HexColor("#f5f5f5")]),
            ]))
            elements.append(data_table)

        elements.append(Spacer(1, 40))
        elements.append(Paragraph("Validation & Approval", header_style))
        elements.append(Spacer(1, 10))

        sig_data = [
            ["Validated By:", "_____________________", "Date:", "_____________________"],
            ["", "", "", ""],
            ["Signature:",    "_____________________", "Position:", "_____________________"],
        ]
        sig_table = Table(sig_data,
                          colWidths=[1.2*inch, 2*inch, 0.8*inch, 2*inch])
        sig_table.setStyle(TableStyle([
            ('FONT', (0,0),(0,-1), 'Helvetica-Bold', 10),
            ('FONT', (2,0),(2,-1), 'Helvetica-Bold', 10),
            ('FONT', (1,0),(1,-1), 'Helvetica', 10),
            ('FONT', (3,0),(3,-1), 'Helvetica', 10),
            ('TEXTCOLOR', (0,0),(-1,-1), colors.HexColor("#333333")),
            ('VALIGN',    (0,0),(-1,-1), 'MIDDLE'),
            ('BOTTOMPADDING', (0,0),(-1,-1), 8),
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

    def handle_report_row_clicked(self, report_id: int):
        """Show detail dialog for a clicked report history row."""
        report = self.model.get_report_by_id(report_id)
        if report:
            # Keep reference so dialog isn't garbage collected.
            # Use open() (non-blocking) to avoid nested event loop conflict
            # with Matplotlib QtAgg backend on Windows (causes 0xC0000409).
            self._detail_dialog = ReportDetailDialog(report, self.view)
            self._detail_dialog.show()

    def show_styled_message(self, title, text, icon_type):
        msg = QMessageBox(self.view)
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