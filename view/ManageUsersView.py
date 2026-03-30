# ManageUsersView.py — Archive only, role locked on edit, Staff-only on add
from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel,
                             QPushButton, QTableWidget, QTableWidgetItem,
                             QHeaderView, QAbstractItemView, QFrame, QComboBox,
                             QLineEdit, QDialog, QFormLayout, QSizePolicy)
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QFont, QColor

PRIMARY = '#0076aa'
WHITE   = '#ffffff'
BG      = '#f4f6f8'
TEXT    = '#1a1a1a'
SUBTEXT = '#757575'
DANGER  = '#D32F2F'
WARNING = '#F57C00'
SUCCESS = '#27ae60'
BORDER  = '#E0E0E0'
ARCHIVE = '#F57C00'


class ManageUsersView(QWidget):
    add_user_clicked     = pyqtSignal()
    edit_user_clicked    = pyqtSignal(int)
    archive_user_clicked = pyqtSignal(int)
    delete_user_clicked  = pyqtSignal(int)   # kept for compat but unused

    def __init__(self):
        super().__init__()
        self.init_ui()

    def init_ui(self):
        self.setStyleSheet("background-color: transparent;")
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        card = QFrame()
        card.setStyleSheet(f"QFrame {{ background-color: {WHITE}; border-radius: 10px; border: none; }}")
        cl = QVBoxLayout(card)
        cl.setContentsMargins(20, 16, 20, 16)
        cl.setSpacing(12)

        title = QLabel("Manage Users")
        title.setFont(QFont("Segoe UI", 16, QFont.Weight.Bold))
        title.setStyleSheet(f"color: {TEXT}; border: none;")
        cl.addWidget(title)

        ctrl = QHBoxLayout()
        ctrl.setSpacing(8)
        input_style = f"padding: 5px 10px; border: 1px solid {BORDER}; border-radius: 6px; color: {TEXT}; background: {WHITE}; font-size: 12px;"

        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Search...")
        self.search_input.setFixedWidth(180)
        self.search_input.setStyleSheet(input_style)
        ctrl.addWidget(self.search_input)

        self.role_combo = QComboBox()
        self.role_combo.addItems(["All", "Admin", "Staff"])
        self.role_combo.setFixedWidth(110)
        self.role_combo.setStyleSheet(input_style)
        ctrl.addWidget(self.role_combo)

        self.status_combo = QComboBox()
        self.status_combo.addItems(["All", "Active", "Inactive"])
        self.status_combo.setFixedWidth(110)
        self.status_combo.setStyleSheet(input_style)
        ctrl.addWidget(self.status_combo)

        ctrl.addStretch()

        self.btn_add = QPushButton("+ Add New User")
        self.btn_add.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_add.setFixedHeight(32)
        self.btn_add.setStyleSheet(f"QPushButton {{ background-color: {PRIMARY}; color: white; font-weight: bold; border-radius: 6px; padding: 4px 14px; font-size: 12px; border: none; }} QPushButton:hover {{ background-color: #005f8a; }}")
        self.btn_add.clicked.connect(self.add_user_clicked.emit)
        ctrl.addWidget(self.btn_add)
        cl.addLayout(ctrl)

        self.table = QTableWidget()
        self.table.setColumnCount(6)
        self.table.setHorizontalHeaderLabels(["ID", "Name", "Username", "Role", "Status", "Actions"])
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(5, QHeaderView.ResizeMode.Fixed)
        self.table.setColumnWidth(5, 180)
        self.table.verticalHeader().setVisible(False)
        self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.table.setShowGrid(False)
        self.table.setFrameShape(QFrame.Shape.NoFrame)
        self.table.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.table.setSelectionMode(QAbstractItemView.SelectionMode.NoSelection)
        self.table.setAlternatingRowColors(True)
        self.table.setStyleSheet(f"""
            QTableWidget {{ border: none; background-color: {WHITE}; color: {TEXT}; font-size: 13px; outline: 0; }}
            QHeaderView::section {{ background-color: {TEXT}; color: white; padding: 10px 8px; font-weight: bold; border: none; font-size: 12px; }}
            QTableWidget::item {{ padding: 9px 8px; border-bottom: 1px solid #f0f0f0; }}
            QTableWidget::item:selected {{ background-color: {WHITE}; color: {TEXT}; }}
            QTableWidget::item:alternate {{ background-color: #fafafa; }}
        """)
        cl.addWidget(self.table)
        root.addWidget(card)

    def load_data(self, users):
        self.table.clearContents()
        self.table.setRowCount(len(users))
        for row_idx, user in enumerate(users):
            self.table.setRowHeight(row_idx, 52)
            self.table.setItem(row_idx, 0, self._item(str(user['user_id']), center=True))
            full_name = f"{user.get('userFname', '')} {user.get('userLname', '')}".strip()
            self.table.setItem(row_idx, 1, self._item(full_name))
            self.table.setItem(row_idx, 2, self._item(user['username']))
            self.table.setItem(row_idx, 3, self._item(user['role'], center=True))

            status_item = self._item(user['status'], center=True)
            status_item.setForeground(QColor(SUCCESS if user['status'] == 'Active' else DANGER))
            self.table.setItem(row_idx, 4, status_item)

            container = QWidget()
            h = QHBoxLayout(container)
            h.setContentsMargins(8, 6, 8, 6)
            h.setSpacing(8)
            h.setAlignment(Qt.AlignmentFlag.AlignCenter)

            btn_edit = QPushButton("Edit")
            btn_edit.setCursor(Qt.CursorShape.PointingHandCursor)
            btn_edit.setFixedSize(70, 32)
            btn_edit.setStyleSheet(f"QPushButton {{ background-color: {PRIMARY}; color: white; border-radius: 6px; font-weight: bold; font-size: 12px; border: none; }} QPushButton:hover {{ background-color: #005f8a; }}")
            btn_edit.clicked.connect(lambda checked, u=user['user_id']: self.edit_user_clicked.emit(u))

            is_active = user['status'] == 'Active'
            btn_archive = QPushButton("Archive" if is_active else "Unarchive")
            btn_archive.setCursor(Qt.CursorShape.PointingHandCursor)
            btn_archive.setFixedSize(90, 32)
            arc_color = ARCHIVE if is_active else SUCCESS
            btn_archive.setStyleSheet(f"QPushButton {{ background-color: {arc_color}; color: white; border-radius: 6px; font-weight: bold; font-size: 12px; border: none; }} QPushButton:hover {{ background-color: {'#c46000' if is_active else '#1e8449'}; }}")
            btn_archive.clicked.connect(lambda checked, u=user['user_id']: self.archive_user_clicked.emit(u))

            h.addWidget(btn_edit)
            h.addWidget(btn_archive)
            self.table.setCellWidget(row_idx, 5, container)

    def _item(self, text, center=False):
        item = QTableWidgetItem(str(text))
        item.setForeground(QColor(TEXT))
        item.setFlags(Qt.ItemFlag.ItemIsEnabled)
        if center:
            item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
        return item

    def make_item(self, text, center=False): return self._item(text, center)


class UserFormDialog(QDialog):
    """
    Add mode  (user_data=None) : Role fixed to 'Staff' (label, not dropdown).
    Edit mode (user_data=dict) : Role is read-only label — cannot be changed.
    """
    def __init__(self, parent=None, user_data=None):
        super().__init__(parent)
        self._is_edit = user_data is not None
        self._role_value = user_data.get('role', 'Staff') if user_data else 'Staff'

        self.setWindowTitle("User Details")
        self.setFixedSize(420, 490)
        self.setStyleSheet(f"""
            QDialog {{ background-color: {WHITE}; }}
            QLabel {{ font-weight: bold; color: {TEXT}; font-size: 12px; border: none; }}
            QLineEdit, QComboBox {{
                padding: 7px 10px; border: 1px solid {BORDER};
                border-radius: 6px; color: {TEXT}; background-color: {WHITE}; font-size: 12px;
            }}
        """)
        self._init_ui(user_data)

    def _init_ui(self, user_data):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(30, 24, 30, 24)
        layout.setSpacing(12)

        header = QLabel("Edit User" if self._is_edit else "Add User")
        header.setFont(QFont("Segoe UI", 15, QFont.Weight.Bold))
        header.setStyleSheet(f"color: {PRIMARY}; margin-bottom: 4px; border: none;")
        header.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(header)

        form = QFormLayout()
        form.setSpacing(10)
        form.setLabelAlignment(Qt.AlignmentFlag.AlignRight)

        self.fname_edit = QLineEdit()
        self.lname_edit = QLineEdit()
        self.user_edit  = QLineEdit()
        self.pass_edit  = QLineEdit()
        self.pass_edit.setEchoMode(QLineEdit.EchoMode.Password)
        self.pass_edit.setPlaceholderText("Leave blank to keep current" if self._is_edit else "")

        form.addRow("First Name:", self.fname_edit)
        form.addRow("Last Name:",  self.lname_edit)
        form.addRow("Username:",   self.user_edit)
        form.addRow("Password:",   self.pass_edit)

        # Role: always a read-only label (Staff locked on add, original role on edit)
        role_display_text = self._role_value  # "Staff" on add; actual role on edit
        role_lbl = QLabel(role_display_text)
        role_lbl.setStyleSheet(f"""
            padding: 7px 10px; border: 1px solid {BORDER};
            border-radius: 6px; color: {SUBTEXT}; background-color: #f9f9f9;
            font-size: 12px; font-weight: normal;
        """)
        tooltip = "Role cannot be changed after account creation." if self._is_edit else "Only Staff accounts can be added."
        role_lbl.setToolTip(tooltip)
        form.addRow("Role:", role_lbl)

        self.status_combo = QComboBox()
        self.status_combo.addItems(["Active", "Inactive"])
        form.addRow("Status:", self.status_combo)

        layout.addLayout(form)
        layout.addStretch()

        if user_data:
            self.fname_edit.setText(user_data.get('userFname', ''))
            self.lname_edit.setText(user_data.get('userLname', ''))
            self.user_edit.setText(user_data.get('username', ''))
            self.status_combo.setCurrentText(user_data.get('status', 'Active'))

        btn_row = QHBoxLayout()
        btn_row.setSpacing(10)

        cancel = QPushButton("Cancel")
        cancel.setFixedHeight(38)
        cancel.setCursor(Qt.CursorShape.PointingHandCursor)
        cancel.setStyleSheet("background-color: #ccc; color: #333; border-radius: 6px; font-weight: bold; border: none;")
        cancel.clicked.connect(self.reject)

        save = QPushButton("Save User")
        save.setFixedHeight(38)
        save.setCursor(Qt.CursorShape.PointingHandCursor)
        save.setStyleSheet(f"background-color: {PRIMARY}; color: white; border-radius: 6px; font-weight: bold; border: none;")
        save.clicked.connect(self.accept)

        btn_row.addWidget(cancel)
        btn_row.addWidget(save)
        layout.addLayout(btn_row)

    def get_data(self):
        return {
            'userFname': self.fname_edit.text().strip(),
            'userLname': self.lname_edit.text().strip(),
            'username':  self.user_edit.text().strip(),
            'password':  self.pass_edit.text(),
            'role':      self._role_value,
            'status':    self.status_combo.currentText()
        }