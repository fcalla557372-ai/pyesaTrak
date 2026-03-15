# Ainventory_Cont.py - REFACTORED (Strict MVC)
"""
Controller Layer - Business Logic & Coordination
Responsibilities:
- Connect View signals to actions
- Coordinate Model and View
- Input validation
- Error handling
- User feedback (QMessageBox)
- NO database queries, NO UI widget creation
"""
from model.Ainventory_model import ProductDetailsModel
from view.Ainventory_view import ProductDetailsView, AddProductDialog, ProductDetailDialog
from PyQt6.QtWidgets import QMessageBox
from typing import Optional


class ProductDetailsController:
    """
    Controller for Admin Inventory Management.
    Coordinates between Model and View.
    """

    def __init__(self, user_data: Optional[dict] = None):
        # Initialize Model and View
        self.model = ProductDetailsModel()
        self.view = ProductDetailsView()
        self.user_data = user_data

        # Connect View signals to Controller methods
        self._connect_signals()

        # Initial data load
        self.load_all_products()
        self._populate_filter_combos()

    def _connect_signals(self):
        """Connect View signals to Controller handlers"""
        self.view.add_product_clicked.connect(self.handle_add_product)
        self.view.product_double_clicked.connect(self.handle_product_selected)

        # Filter tab signals
        self.view.filter_all_clicked.connect(self.load_all_products)
        self.view.filter_low_stock_clicked.connect(self.load_low_stock)
        self.view.filter_out_of_stock_clicked.connect(self.load_out_of_stock)
        self.view.filter_defective_clicked.connect(self.load_defective)
        self.view.filter_by_brand_clicked.connect(self.load_by_brand)
        self.view.filter_by_category_clicked.connect(self.load_by_category)

    # ============================================
    # LOAD / DISPLAY METHODS
    # ============================================

    def load_all_products(self):
        """Load and display all products"""
        products = self.model.get_all_products()
        self.view.display_products(products)
        self.view.set_active_tab("All")

    def load_low_stock(self):
        """Load and display low stock products"""
        products = self.model.get_products_by_filter(
            "stock_quantity <= 10 AND stock_quantity > 0"
        )
        self.view.display_products(products)
        self.view.set_active_tab("Low")

    def load_out_of_stock(self):
        """Load and display out of stock products"""
        products = self.model.get_products_by_filter("stock_quantity = 0")
        self.view.display_products(products)
        self.view.set_active_tab("Out")

    def load_defective(self):
        """Load and display defective products with reasons"""
        products = self.model.get_defective_products_with_reason()
        self.view.display_defective_products(products)
        self.view.set_active_tab("Defect")

    # ============================================
    # EVENT HANDLERS
    # ============================================

    def _populate_filter_combos(self):
        """Load distinct brands and categories from DB into the filter dropdowns."""
        try:
            brands = self.model.get_unique_brands()
            self.view.populate_brand_filter(brands)
            categories = self.model.get_unique_categories()
            self.view.populate_category_filter(categories)
        except Exception as e:
            print(f'[populate_filter_combos] {e}')

    def load_by_brand(self, brand: str):
        """Load products filtered by brand."""
        products = self.model.get_products_by_brand(brand)
        self.view.display_products(products)

    def load_by_category(self, category: str):
        """Load products filtered by category."""
        products = self.model.get_products_by_category(category)
        self.view.display_products(products)

    def handle_add_product(self):
        """
        Handle add product button click.
        Business logic + validation + coordination.
        """
        # Use show() instead of exec() to avoid 0xC0000409 crash with Matplotlib QtAgg
        dialog = AddProductDialog(self.view)

        # Wire product name → category auto-detection
        dialog.product_name_changed.connect(
            lambda text: dialog.set_suggested_category(self._detect_category(text))
        )

        # Wire confirmed signal — runs when user clicks Add Product
        dialog.confirmed.connect(self._process_add_product)

        # Keep reference so dialog isn't garbage collected
        self._add_dialog = dialog
        dialog.show()

    def _process_add_product(self, data: dict):
        """Process the add product form data after user confirms."""
        # VALIDATION (Controller's responsibility)
        validation_error = self._validate_product_data(data)
        if validation_error:
            QMessageBox.warning(self.view, "Validation Error", validation_error)
            return

        # BUSINESS LOGIC: Determine status based on quantity
        status = self._determine_product_status(data['stock_quantity'])

        # Get user ID
        user_id = self._get_current_user_id()

        # Delegate to Model
        success = self.model.add_new_product(
            product_name=data['product_name'],
            brand=data['brand'],
            model=data['model'],
            description=data['description'],
            stock_quantity=data['stock_quantity'],
            status=status,
            user_id=user_id,
            category=data.get('category')
        )

        # USER FEEDBACK (Controller's responsibility)
        if success:
            QMessageBox.information(
                self.view,
                "Success",
                f"Product '{data['product_name']}' added successfully!"
            )
            self.load_all_products()
            self._populate_filter_combos()
        else:
            QMessageBox.critical(
                self.view,
                "Error",
                "Failed to add product. Please try again."
            )

    def handle_product_selected(self, product_id: int):
        """Show a detail dialog for the selected product."""
        # Skip clicks on defective-tab rows (col-0 holds defect_id, not product_id)
        if self.view._current_mode == "defect":
            return
        product = self.model.get_product_by_id(product_id)
        if product:
            # Keep reference + use open() (non-blocking) to avoid nested
            # event loop conflict with Matplotlib QtAgg backend on Windows.
            self._detail_dialog = ProductDetailDialog(product, self.view)
            self._detail_dialog.show()

    # ============================================
    # VALIDATION METHODS (Business Logic)
    # ============================================

    def _validate_product_data(self, data: dict) -> Optional[str]:
        """
        Validate product data before submission.

        Args:
            data: Product data dictionary from View

        Returns:
            Error message string if invalid, None if valid
        """
        # Required fields
        if not data['product_name']:
            return "Product Name is required."

        if len(data['product_name']) < 3:
            return "Product Name must be at least 3 characters."

        if len(data['product_name']) > 255:
            return "Product Name is too long (max 255 characters)."

        # Optional fields validation
        if data['brand'] and len(data['brand']) > 100:
            return "Brand name is too long (max 100 characters)."

        if data['model'] and len(data['model']) > 100:
            return "Model name is too long (max 100 characters)."

        # Quantity validation
        if data['stock_quantity'] < 0:
            return "Stock quantity cannot be negative."

        if data['stock_quantity'] > 10000:
            return "Stock quantity too large (max 10,000)."

        return None  # All valid

    def _determine_product_status(self, stock_quantity: int) -> str:
        """
        Determine product status based on quantity.
        Business rule implemented here.

        Args:
            stock_quantity: Current stock amount

        Returns:
            Status string (Available, Low Stock, Out of Stock)
        """
        if stock_quantity == 0:
            return 'Out of Stock'
        elif stock_quantity <= 10:
            return 'Low Stock'
        else:
            return 'Available'

    def _get_current_user_id(self) -> int:
        """
        Get current user ID.

        Returns:
            User ID (defaults to 1 if no user data)
        """
        if self.user_data and 'user_id' in self.user_data:
            return self.user_data['user_id']
        return 1  # Default to admin

    # ============================================
    # PUBLIC INTERFACE METHODS
    # ============================================

    def show(self):
        """Show the view"""
        self.view.show()

    def refresh(self):
        """Refresh current view"""
        self.load_all_products()

    def set_user_data(self, user_data: dict):
        """
        Update user data.

        Args:
            user_data: Dictionary with user information
        """
        self.user_data = user_data