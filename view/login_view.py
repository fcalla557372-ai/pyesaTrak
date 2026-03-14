# login_view.py - View
from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QLabel,
                             QLineEdit, QPushButton, QMessageBox)
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QPixmap, QFont


class LoginView(QWidget):
    """View for the login window"""

    login_attempted = pyqtSignal(str, str)

    def __init__(self):
        super().__init__()
        self.init_ui()

    def init_ui(self):
        """Initialize the user interface"""
        self.setWindowTitle("PyesaTrak - Login")
        self.setFixedSize(377, 537)
        self.setStyleSheet("background-color: #E8E8E8;")

        # Main layout
        layout = QVBoxLayout()
        layout.setContentsMargins(58, 40, 58, 40)
        layout.setSpacing(0)

        # Logo
        logo_label = QLabel()
        try:
            # Try to load the actual logo
            pixmap = QPixmap("PyesatrakLOGO.png")
            if not pixmap.isNull():
                scaled_pixmap = pixmap.scaled(100, 100,
                                              Qt.AspectRatioMode.KeepAspectRatio,
                                              Qt.TransformationMode.SmoothTransformation)
                logo_label.setPixmap(scaled_pixmap)
            else:
                # Fallback to placeholder
                logo_label.setText("🔧")
                logo_label.setStyleSheet("font-size: 60px;")
        except:
            # Fallback to placeholder
            logo_label.setText("🔧")
            logo_label.setStyleSheet("font-size: 60px;")

        logo_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        logo_label.setFixedHeight(100)
        layout.addWidget(logo_label)

        layout.addSpacing(10)

        # App name
        app_name = QLabel("PyesaTrak")
        app_name.setAlignment(Qt.AlignmentFlag.AlignCenter)
        app_name.setFont(QFont("Arial", 36, QFont.Weight.Bold))
        app_name.setStyleSheet("color: #000000;")
        layout.addWidget(app_name)

        layout.addSpacing(40)

        # Username label
        username_label = QLabel("USERNAME")
        username_label.setFont(QFont("Arial", 9, QFont.Weight.Bold))
        username_label.setStyleSheet("color: #000000;")
        layout.addWidget(username_label)

        layout.addSpacing(5)

        # Username input
        self.username_input = QLineEdit()
        self.username_input.setPlaceholderText("username")
        self.username_input.setFixedHeight(50)
        self.username_input.setStyleSheet("""
            QLineEdit {
                border: 1px solid #000000;
                background-color: #FFFFFF;
                padding: 10px 15px;
                font-size: 13px;
                color: #000000;
                font-family: Arial;
            }
            QLineEdit:focus {
                border: 2px solid #0077B6;
            }
        """)
        layout.addWidget(self.username_input)

        layout.addSpacing(20)

        # Password label
        password_label = QLabel("PASSWORD")
        password_label.setFont(QFont("Arial", 9, QFont.Weight.Bold))
        password_label.setStyleSheet("color: #000000;")
        layout.addWidget(password_label)

        layout.addSpacing(5)

        # Password input
        self.password_input = QLineEdit()
        self.password_input.setPlaceholderText("••••••")
        self.password_input.setEchoMode(QLineEdit.EchoMode.Password)
        self.password_input.setFixedHeight(50)
        self.password_input.setStyleSheet("""
            QLineEdit {
                border: 1px solid #000000;
                background-color: #FFFFFF;
                padding: 10px 15px;
                font-size: 13px;
                color: #000000;
                font-family: Arial;
            }
            QLineEdit:focus {
                border: 2px solid #0077B6;
            }
        """)
        layout.addWidget(self.password_input)

        layout.addSpacing(35)

        # Login button
        self.login_button = QPushButton("Log-in")
        self.login_button.setFixedHeight(55)
        self.login_button.setFont(QFont("Arial", 13, QFont.Weight.Bold))
        self.login_button.setCursor(Qt.CursorShape.PointingHandCursor)
        self.login_button.setStyleSheet("""
            QPushButton {
                background-color: #0077B6;
                color: #FFFFFF;
                border: none;
                font-weight: bold;
                font-family: Arial;
            }
            QPushButton:hover {
                background-color: #005F8F;
            }
            QPushButton:pressed {
                background-color: #004A73;
            }
        """)
        self.login_button.clicked.connect(self.on_login_clicked)
        layout.addWidget(self.login_button)

        # Enable Enter key to trigger login
        self.password_input.returnPressed.connect(self.on_login_clicked)
        self.username_input.returnPressed.connect(self.on_login_clicked)

        self.setLayout(layout)

    def on_login_clicked(self):
        """Handle login button click"""
        username = self.username_input.text()
        password = self.password_input.text()
        self.login_attempted.emit(username, password)

    def show_message(self, title, message, is_success=False):
        """Display a message box"""
        msg_box = QMessageBox(self)
        msg_box.setWindowTitle(title)
        msg_box.setText(message)

        # Set stylesheet to ensure text is visible
        msg_box.setStyleSheet("""
            QMessageBox {
                background-color: #fffff;
                color: #000000;

            }
            QMessageBox QLabel {
                color: #000000;
                font-size: 13px;
                font-family: Arial;
            }
            QMessageBox QPushButton {
                background-color: #0077B6;
                color: #000000;
                border: none;
                padding: 8px 20px;
                font-weight: bold;
                min-width: 80px;
            }
            QMessageBox QPushButton:hover {
                background-color: #005F8F;
            }
        """)

        if is_success:
            msg_box.setIcon(QMessageBox.Icon.Information)
        else:
            msg_box.setIcon(QMessageBox.Icon.Warning)
        msg_box.exec()

    def clear_inputs(self):
        """Clear input fields"""
        self.username_input.clear()
        self.password_input.clear()
        self.username_input.setFocus()