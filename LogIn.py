# LogIn.py — alternate entry point (delegates to Main.py logic)
import sys
from PyQt6.QtWidgets import QApplication

from model.login_model import LoginModel
from view.login_view import LoginView
from controller.login_controller import LoginController


def main():
    app = QApplication(sys.argv)

    model      = LoginModel()
    view       = LoginView()
    controller = LoginController(view, model)

    controller.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()