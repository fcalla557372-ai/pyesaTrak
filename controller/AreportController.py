# controller/AreportController.py
# MVC LAYER: CONTROLLER
# Responsibilities: handle report generation/export actions, call Model,
#                   pass results to View. No SQL, no widget construction.

from model.AreportModel import ReportsModel
from view.AreportsView import ReportDetailDialog, ReportExporter
from PyQt6.QtWidgets import QFileDialog
from datetime import datetime


class ReportsController:
    def __init__(self, user_data=None):
        self.model               = ReportsModel()
        self.view                = None
        self.user_data           = user_data
        self.current_report_data = []
        self.current_report_type = ""
        self.current_date_range  = {"start": "", "end": ""}

    def set_view(self, view):
        """Injected view pattern (matches lazy-load in ADBoardController)."""
        self.view = view
        self.view.generate_btn.clicked.connect(self.handle_generate_report)
        self.view.export_btn.clicked.connect(self.handle_export_report)
        self.view.row_double_clicked.connect(self.handle_report_row_clicked)
        self.load_report_history()

    # ── READ ──────────────────────────────────────────────────────────────────

    def load_report_history(self):
        try:
            reports = self.model.get_all_saved_reports()
            if self.view:
                self.view.load_reports(reports)
        except Exception as e:
            print(f"[load_report_history] {e}")

    # ── GENERATE ──────────────────────────────────────────────────────────────

    def handle_generate_report(self):
        rtype = self.view.report_type_combo.currentText()
        start = self.view.start_date.date().toString("yyyy-MM-dd")
        end   = self.view.end_date.date().toString("yyyy-MM-dd")

        self.current_report_type = rtype
        self.current_date_range  = {"start": start, "end": end}

        try:
            data = self._fetch_report_data(rtype, start, end)
            self.current_report_data = data

            if data:
                self.view.display_generated_data(data)
                print(f"✓ Generated {len(data)} rows for {rtype}")
                # Persist report entry only when there is actual data
                self.model.save_report_entry(
                    rtype, start, end, self.user_data, transaction_id=None)
            else:
                self.view.display_generated_data([])
                self.view.show_message(
                    "No Data",
                    f"No data found for '{rtype}' in the selected date range.",
                    "Warning")

        except Exception as e:
            print(f"[handle_generate_report] {e}")
            import traceback; traceback.print_exc()
            self.view.show_message("Error", f"Failed to generate report: {e}", "Critical")

    def _fetch_report_data(self, rtype: str, start: str, end: str) -> list:
        """Delegate to the appropriate model method. No SQL here."""
        dispatch = {
            "Stock Movement":        lambda: self.model.get_stock_movement(start, end),
            "Inventory Status":      lambda: self.model.get_inventory_status(),
            "Defects Report":        lambda: self.model.get_defective_report(start, end),
            "Low Stock Report":      lambda: self.model.get_low_stock_report(),
            "Out of Stock Report":   lambda: self.model.get_out_of_stock_report(),
            "Defective Stock Report":lambda: self.model.get_defective_stock_report(start, end),
            "User Activity":         lambda: self.model.get_user_activity(start, end),
        }
        fn = dispatch.get(rtype)
        return fn() if fn else []

    # ── EXPORT ────────────────────────────────────────────────────────────────

    def handle_export_report(self):
        if not self.current_report_data:
            self.view.show_message(
                "Error", "No data to export. Please generate a report first.", "Warning")
            return

        default_filename = (
            f"{self.current_report_type.replace(' ', '_')}_"
            f"{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf")

        filename, _ = QFileDialog.getSaveFileName(
            self.view, "Save PDF Report", default_filename, "PDF Files (*.pdf)")

        if filename:
            try:
                ReportExporter().generate(
                    filename    = filename,
                    report_type = self.current_report_type,
                    date_range  = self.current_date_range,
                    data        = self.current_report_data,
                    user_data   = self.user_data,
                )
                print(f"✓ PDF exported: {filename}")
                self.view.show_message(
                    "Success", f"Report exported successfully to:\n{filename}", "Info")
            except Exception as e:
                print(f"[handle_export_report] {e}")
                import traceback; traceback.print_exc()
                self.view.show_message("Error", f"Export failed: {e}", "Critical")

    # ── DETAIL ROW ────────────────────────────────────────────────────────────

    def handle_report_row_clicked(self, report_id: int):
        """Show detail dialog for a clicked report history row."""
        report = self.model.get_report_by_id(report_id)
        if report:
            # Keep reference so dialog isn't garbage-collected.
            # Use show() (non-blocking) to avoid nested event loop conflict
            # with Matplotlib QtAgg backend on Windows (0xC0000409).
            self._detail_dialog = ReportDetailDialog(report, self.view)
            self._detail_dialog.show()