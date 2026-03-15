# login_controller.py
from PyQt6.QtWidgets import QMessageBox


class LoginController:
    def __init__(self, view, model):
        self.model = model
        self.view = view
        self.current_user = None
        self.dashboard_controller = None
        self.staff_window = None

        self.view.login_attempted.connect(self.handle_login)

    def handle_login(self, username, password):
        print(f"Login attempt - Username: {username}")
        is_valid, message, user_data = self.model.validate_credentials(username, password)

        if is_valid:
            self.show_message("Success", message, is_success=True)
            self.current_user = user_data
            self.model.user_data = user_data
            self.view.clear_inputs()

            # Open the appropriate window FIRST, then close login
            self.open_dashboard()
            self.view.close()
        else:
            print(f"✗ Login failed: {message}")
            self.show_message(
                "Login Failed",
                "Invalid username or password.\nPlease check your credentials and try again.",
                is_success=False
            )
            self.view.password_input.clear()
            self.view.password_input.setFocus()

    def open_dashboard(self):
        try:
            user_role = self.current_user['role']
            username  = self.current_user['username']
            print(f"Opening dashboard for: {username} (Role: {user_role})")

            if user_role == "Admin":
                from controller.ADBoardController import DashboardController
                self.dashboard_controller = DashboardController(self.current_user)
                self.dashboard_controller.show()

            elif user_role == "Staff":
                # Staff goes straight to inventory — no dashboard
                from view.SIView import StaffMainWindow
                from model.SIModel import InventoryModel
                from controller.SIController import InventoryController
                self.staff_window = StaffMainWindow(self.current_user)
                # Wire sign-out: View emits signal, Controller handles navigation
                self.staff_window.sign_out_requested.connect(self._handle_staff_sign_out)
                inv_model = InventoryModel()
                self.staff_inv_controller = InventoryController(
                    inv_model, self.staff_window.inventory_view, self.current_user)
                self.staff_window.show()

            else:
                self.show_message(
                    "Access Denied",
                    f"No interface available for role: {user_role}",
                    is_success=False
                )
                self.view.show()

        except Exception as e:
            print(f"\n✗ ERROR opening window: {e}")
            import traceback
            traceback.print_exc()
            self.show_message(
                "Error",
                f"Failed to open application.\n\nError: {str(e)}",
                is_success=False
            )
            self.view.show()

    def show_message(self, title, message, is_success=False):
        msg_box = QMessageBox(self.view)
        msg_box.setWindowTitle(title)
        msg_box.setText(message)
        msg_box.setStyleSheet("""
            QMessageBox { background-color: #E8E8E8; }
            QMessageBox QLabel { color: #000000; font-size: 11px; font-family: Arial; padding: 5px 10px; }
            QMessageBox QPushButton {
                background-color: #0077B6; color: #FFFFFF; border: none; padding: 6px 16px;
                font-weight: bold; font-family: Arial; font-size: 11px; min-width: 65px; margin-top: 5px;
            }
            QMessageBox QPushButton:hover { background-color: #005F8F; }
        """)
        if is_success:
            msg_box.setIcon(QMessageBox.Icon.Information)
        else:
            msg_box.setIcon(QMessageBox.Icon.Warning)
        msg_box.exec()

    def _handle_staff_sign_out(self):
        """Called when Staff clicks Sign Out and confirms. Re-opens the login window."""
        try:
            from view.login_view import LoginView
            from model.login_model import LoginModel
            self.lc = LoginController(LoginView(), LoginModel())
            self.lc.show()
            if self.staff_window:
                self.staff_window.close()
        except Exception as e:
            print(f"Error returning to login: {e}")

    def show(self):
        self.view.show()