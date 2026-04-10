# controller/Ainventory_Cont.py
# MVC LAYER: CONTROLLER
# Responsibilities: receive user input signals, call Model methods,
#                   pass results to View. No SQL, no Qt widget construction.

from model.Ainventory_model import ProductDetailsModel
from view.Ainventory_view import ProductDetailsView, AddProductDialog, ProductDetailDialog


class ProductDetailsController:
    """
    Coordinates between ProductDetailsModel and ProductDetailsView.
    - Calls model for data and business-rule evaluation.
    - Passes results (or error messages) to the view for display.
    - Contains NO raw SQL, NO validation logic, NO Qt widget construction.
    """

    def __init__(self, user_data=None):
        self.model     = ProductDetailsModel()
        self.view      = ProductDetailsView()
        self.user_data = user_data
        self._add_dialog    = None
        self._detail_dialog = None
        self._connect_signals()
        self.load_all_products()
        self._populate_filter_combos()

    # ── Signal wiring ─────────────────────────────────────────────────────────

    def _connect_signals(self):
        self.view.add_product_clicked.connect(self.handle_add_product)
        self.view.product_double_clicked.connect(self.handle_product_selected)
        self.view.filter_all_clicked.connect(self.load_all_products)
        self.view.filter_low_stock_clicked.connect(self.load_low_stock)
        self.view.filter_out_of_stock_clicked.connect(self.load_out_of_stock)
        self.view.filter_defective_clicked.connect(self.load_defective)
        self.view.filter_by_brand_clicked.connect(self.load_by_brand)
        self.view.filter_by_category_clicked.connect(self.load_by_category)

    # ── Navigation / filter handlers ──────────────────────────────────────────

    def load_all_products(self):
        self.view.display_products(self.model.get_all_products())
        self.view.set_active_tab("All")

    def load_low_stock(self):
        self.view.display_products(
            self.model.get_products_by_filter("stock_quantity <= 10 AND stock_quantity > 0"))
        self.view.set_active_tab("Low")

    def load_out_of_stock(self):
        self.view.display_products(
            self.model.get_products_by_filter("stock_quantity = 0"))
        self.view.set_active_tab("Out")

    def load_defective(self):
        self.view.display_defective_products(
            self.model.get_defective_products_with_reason())
        self.view.set_active_tab("Defect")

    def load_by_brand(self, brand: str):
        self.view.display_products(self.model.get_products_by_brand(brand))

    def load_by_category(self, category: str):
        self.view.display_products(self.model.get_products_by_category(category))

    def _populate_filter_combos(self):
        try:
            self.view.populate_brand_filter(self.model.get_unique_brands())
            self.view.populate_category_filter(self.model.get_unique_categories())
        except Exception as e:
            print(f"[_populate_filter_combos] {e}")

    # ── Add product flow ──────────────────────────────────────────────────────

    def handle_add_product(self):
        # Guard: if dialog is alive and visible, bring it to front.
        # Wrapped in try/except because closing with the X button destroys
        # the underlying Qt C++ object while self._add_dialog still holds
        # the Python wrapper — calling .isVisible() on a dead object raises
        # RuntimeError which cascades into a 0xC0000409 heap-corruption crash.
        try:
            if self._add_dialog is not None and self._add_dialog.isVisible():
                self._add_dialog.raise_()
                self._add_dialog.activateWindow()
                return
        except RuntimeError:
            # Qt C++ object already deleted (user closed with X) — reset and proceed
            self._add_dialog = None

        dialog = AddProductDialog(None)

        # Suggest a category whenever the product name changes.
        # derive_category() is a MODEL method — controller mediates the call.
        dialog.product_name_changed.connect(
            lambda text: dialog.set_suggested_category(
                self.model.derive_category(text)))

        dialog.confirmed.connect(self._process_add_product)

        # destroyed() fires for ALL close paths: Cancel button, Add Product button,
        # AND the X (window close) button.
        # AddProductDialog is a QWidget (not QDialog) so it has no finished() signal.
        # WA_DeleteOnClose (set in AddProductDialog.__init__) ensures destroyed()
        # is always emitted when the window is closed by any means.
        dialog.destroyed.connect(lambda: setattr(self, '_add_dialog', None))

        self._add_dialog = dialog
        dialog.show()

    def _process_add_product(self, data: dict):
        """
        Validate via Model → on failure, tell View to show the error.
        On success, call Model to persist, then refresh View.
        """
        # ── Validation lives in the Model, not here ───────────────────────────
        error = self.model.validate_product_data(data)
        if error:
            self.view.show_message("Validation Error", error, "warning")
            return

        success = self.model.add_new_product(
            product_name  = data['product_name'],
            brand         = data['brand'],
            model         = data['model'],
            description   = data['description'],
            stock_quantity= data['stock_quantity'],
            user_id       = self._get_current_user_id(),
            category      = data.get('category'),
        )

        if success:
            self.view.show_message(
                "Success",
                f"Product '{data['product_name']}' added successfully!",
                "info")
            self.load_all_products()
            self._populate_filter_combos()
        else:
            self.view.show_message(
                "Error",
                "Failed to add product. Please try again.",
                "critical")

    # ── Detail view ───────────────────────────────────────────────────────────

    def handle_product_selected(self, product_id: int):
        if self.view._current_mode == "defect":
            return
        product = self.model.get_product_by_id(product_id)
        if product:
            self._detail_dialog = ProductDetailDialog(product, None)
            self._detail_dialog.show()

    # ── Helpers ───────────────────────────────────────────────────────────────

    def _get_current_user_id(self) -> int:
        if self.user_data and 'user_id' in self.user_data:
            return self.user_data['user_id']
        return 1

    def set_user_data(self, user_data):
        self.user_data = user_data

    def show(self):
        self.view.show()

    def refresh(self):
        self.load_all_products()