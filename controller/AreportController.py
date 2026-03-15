# AreportController.py - Updated with Analytics loading
from model.AreportModel import ReportsModel
from view.AreportsView import ReportDetailDialog, ReportExporter
from PyQt6.QtWidgets import QMessageBox, QFileDialog
from datetime import datetime


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
        self.view.row_double_clicked.connect(self.handle_report_row_clicked)
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
            elif rtype == "Low Stock Report":
                data = self.model.get_low_stock_report()
            elif rtype == "Out of Stock Report":
                data = self.model.get_out_of_stock_report()
            elif rtype == "Defective Stock Report":
                data = self.model.get_defective_stock_report(start, end)
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
        ReportExporter().generate(
            filename=filename,
            report_type=self.current_report_type,
            date_range=self.current_date_range,
            data=self.current_report_data,
            user_data=self.user_data,
        )
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