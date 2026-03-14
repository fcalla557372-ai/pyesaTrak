# Filename: Main.py
import sys
from PyQt6.QtWidgets import QApplication

from login_model import LoginModel
from login_view import LoginView
from login_controller import LoginController


def main():
    app = QApplication(sys.argv)

    model      = LoginModel()
    view       = LoginView()
    controller = LoginController(view, model)

    controller.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()