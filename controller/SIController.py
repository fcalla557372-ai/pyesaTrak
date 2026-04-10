# SIController.py — Staff Inventory Controller
from model.SIModel import InventoryModel
from view.SIView import InventoryView, StockInDialog, StockOutDialog, DefectDialog


class InventoryController:
    """Controller for Staff Inventory Operations."""

    def __init__(self, model, view, user_data=None):
        self.model     = model
        self.view      = view
        self.user_data = user_data

        # Track selected product (set when user clicks a row)
        self._selected_product_id = None

        # Action button signals
        self.view.stock_in_clicked.connect(lambda: self.handle_transaction('IN'))
        self.view.stock_out_clicked.connect(lambda: self.handle_transaction('OUT'))
        self.view.defect_clicked.connect(lambda: self.handle_transaction('DEFECT'))

        # Row selection signal
        self.view.product_selected.connect(self._on_product_selected)

        # Filter tab signals
        self.view.filter_all_clicked.connect(self.load_all_products)
        self.view.filter_low_stock_clicked.connect(self.load_low_stock)
        self.view.filter_out_of_stock_clicked.connect(self.load_out_of_stock)
        self.view.filter_defective_clicked.connect(self.load_defective)

        # Initial load + populate filter dropdowns
        self.load_all_products()
        self._populate_filters()

    # ── Filter methods ────────────────────────────────────────────────────────

    def _populate_filters(self):
        """Load distinct brands and categories from DB into the view dropdowns."""
        try:
            self.view.populate_brand_filter(self.model.get_unique_brands())
            self.view.populate_category_filter(self.model.get_unique_categories())
        except Exception as e:
            print(f"[_populate_filters] {e}")

    def load_all_products(self):
        products = self.model.get_all_products()
        self.view.load_table(products)
        self.view.set_active_tab("All")
        self._selected_product_id = None

    def load_low_stock(self):
        products = self.model.get_products_by_filter(
            "stock_quantity <= 10 AND stock_quantity > 0")
        self.view.load_table(products)
        self.view.set_active_tab("Low")

    def load_out_of_stock(self):
        products = self.model.get_products_by_filter("stock_quantity = 0")
        self.view.load_table(products)
        self.view.set_active_tab("Out")

    def load_defective(self):
        products = self.model.get_defective_products_with_reason()
        self.view.load_defective_table(products)
        self.view.set_active_tab("Defect")

    # ── Row selection ─────────────────────────────────────────────────────────

    def _on_product_selected(self, product_id: int):
        """Store the selected product_id for pre-filling dialogs."""
        self._selected_product_id = product_id

    # ── Transaction handler ───────────────────────────────────────────────────

    def handle_transaction(self, trans_type: str):
        all_products = self.model.get_all_products()
        if not all_products:
            self.view.show_message("Inventory Empty", "No products available.", "warning")
            return

        user_id = self.user_data['user_id'] if self.user_data else 1
        pid     = self._selected_product_id

        if trans_type == 'IN':
            dialog = StockInDialog(all_products, self.view, preselected_id=pid)
        elif trans_type == 'OUT':
            dialog = StockOutDialog(all_products, self.view, preselected_id=pid)
        else:
            dialog = DefectDialog(all_products, self.view, preselected_id=pid)

        if not dialog.exec():
            return  # cancelled

        if trans_type == 'IN':
            pid, qty, remarks = dialog.get_data()
            success = self.model.update_stock(pid, qty, trans_type, remarks, user_id)

        elif trans_type == 'OUT':
            pid, qty, remarks = dialog.get_data()
            success = self.model.update_stock(pid, -qty, trans_type, remarks, user_id)

        else:  # DEFECT
            pid, qty, defect_type, defect_desc = dialog.get_data()
            remarks = f"{defect_type} - {defect_desc}" if defect_desc else defect_type
            success = self.model.update_stock(
                pid, -qty, trans_type, remarks, user_id,
                defect_type=defect_type, defect_description=defect_desc)

        if success:
            msg = {
                "IN":     "Stock added successfully.",
                "OUT":    "Stock removed successfully.",
                "DEFECT": "Defect reported successfully.",
            }[trans_type]
            self.view.show_message("Success", msg, "info")
            self.load_all_products()
        else:
            self.view.show_message("Error", "Transaction failed.", "critical")

    def show(self):
        self.view.show()