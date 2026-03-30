# Ainventory_Cont.py
from model.Ainventory_model import ProductDetailsModel
from view.Ainventory_view import ProductDetailsView, AddProductDialog, ProductDetailDialog
from PyQt6.QtWidgets import QMessageBox
from typing import Optional


class ProductDetailsController:

    def __init__(self, user_data=None):
        self.model = ProductDetailsModel()
        self.view  = ProductDetailsView()
        self.user_data = user_data
        self._add_dialog    = None
        self._detail_dialog = None
        self._connect_signals()
        self.load_all_products()
        self._populate_filter_combos()

    def _connect_signals(self):
        self.view.add_product_clicked.connect(self.handle_add_product)
        self.view.product_double_clicked.connect(self.handle_product_selected)
        self.view.filter_all_clicked.connect(self.load_all_products)
        self.view.filter_low_stock_clicked.connect(self.load_low_stock)
        self.view.filter_out_of_stock_clicked.connect(self.load_out_of_stock)
        self.view.filter_defective_clicked.connect(self.load_defective)
        self.view.filter_by_brand_clicked.connect(self.load_by_brand)
        self.view.filter_by_category_clicked.connect(self.load_by_category)

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

    def _populate_filter_combos(self):
        try:
            self.view.populate_brand_filter(self.model.get_unique_brands())
            self.view.populate_category_filter(self.model.get_unique_categories())
        except Exception as e:
            print(f'[populate_filter_combos] {e}')

    def load_by_brand(self, brand):
        self.view.display_products(self.model.get_products_by_brand(brand))

    def load_by_category(self, category):
        self.view.display_products(self.model.get_products_by_category(category))

    def handle_add_product(self):
        if self._add_dialog is not None and self._add_dialog.isVisible():
            self._add_dialog.raise_()
            self._add_dialog.activateWindow()
            return
        dialog = AddProductDialog(None)
        dialog.product_name_changed.connect(
            lambda text: dialog.set_suggested_category(self._detect_category(text)))
        dialog.confirmed.connect(self._process_add_product)
        dialog.cancelled.connect(lambda: setattr(self, '_add_dialog', None))
        dialog.confirmed.connect(lambda _: setattr(self, '_add_dialog', None))
        self._add_dialog = dialog
        dialog.show()

    def _process_add_product(self, data):
        err = self._validate_product_data(data)
        if err:
            QMessageBox.warning(self.view, "Validation Error", err)
            return
        success = self.model.add_new_product(
            product_name=data['product_name'],
            brand=data['brand'],
            model=data['model'],
            description=data['description'],
            stock_quantity=data['stock_quantity'],
            status=self._determine_product_status(data['stock_quantity']),
            user_id=self._get_current_user_id(),
            category=data.get('category'),
        )
        if success:
            QMessageBox.information(self.view, "Success",
                f"Product '{data['product_name']}' added successfully!")
            self.load_all_products()
            self._populate_filter_combos()
        else:
            QMessageBox.critical(self.view, "Error",
                "Failed to add product. Please try again.")

    def handle_product_selected(self, product_id):
        if self.view._current_mode == "defect":
            return
        product = self.model.get_product_by_id(product_id)
        if product:
            self._detail_dialog = ProductDetailDialog(product, None)
            self._detail_dialog.show()

    def _detect_category(self, text):
        return self.model._derive_category(text)

    def _validate_product_data(self, data):
        if not data['product_name']:
            return "Product Name is required."
        if len(data['product_name']) < 3:
            return "Product Name must be at least 3 characters."
        if len(data['product_name']) > 255:
            return "Product Name is too long (max 255 characters)."
        if data['brand'] and len(data['brand']) > 100:
            return "Brand name is too long (max 100 characters)."
        if data['model'] and len(data['model']) > 100:
            return "Model name is too long (max 100 characters)."
        if data['stock_quantity'] < 0:
            return "Stock quantity cannot be negative."
        if data['stock_quantity'] > 10000:
            return "Stock quantity too large (max 10,000)."
        return None

    def _determine_product_status(self, qty):
        if qty == 0:  return 'Out of Stock'
        if qty <= 10: return 'Low Stock'
        return 'Available'

    def _get_current_user_id(self):
        if self.user_data and 'user_id' in self.user_data:
            return self.user_data['user_id']
        return 1

    def show(self):    self.view.show()
    def refresh(self): self.load_all_products()

    def set_user_data(self, user_data):
        self.user_data = user_data