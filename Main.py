# Filename: Main.py
import sys
import os

# ── Make subfolders discoverable so flat imports still work ───────────────────
_base = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(_base, 'controller'))
sys.path.insert(0, os.path.join(_base, 'model'))
sys.path.insert(0, os.path.join(_base, 'view'))

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