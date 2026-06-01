import sys
import os
import subprocess
import time

from PySide6.QtWidgets import QApplication, QMessageBox

from ui.welcome_page import WelcomePage
from ui.login_page import LoginPage
from ui.main_window import MainWindow


# =========================
# Backend automatique
# =========================
def get_app_dir():
    if getattr(sys, "frozen", False):
        return os.path.dirname(sys.executable)

    return os.path.abspath(os.path.dirname(__file__))


def start_backend():
    app_dir = get_app_dir()

    backend_exe = os.path.join(app_dir, "backend", "backend.exe")

    if os.path.exists(backend_exe):
        subprocess.Popen(
            [backend_exe],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            creationflags=subprocess.CREATE_NO_WINDOW
        )

        time.sleep(3)
        return

    
    
    backend_script = os.path.abspath(
        os.path.join(app_dir, "..", "backend_launcher.py")
    )

    if not os.path.exists(backend_script):
        QMessageBox.critical(
            None,
            "Backend introuvable",
            f"Impossible de trouver le backend :\n{backend_script}"
        )
        return

    subprocess.Popen(
        ["python", backend_script],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL
    )

    time.sleep(3)


class AppController:
    def __init__(self):
        self.welcome_window = None
        self.login_window = None
        self.main_window = None

        self.open_welcome()

    def open_welcome(self):
        self.welcome_window = WelcomePage()
        self.welcome_window.login_clicked.connect(self.open_login)
        self.welcome_window.create_account_clicked.connect(self.open_create_account)
        self.welcome_window.show()

    def open_login(self):
        self.login_window = LoginPage()
        self.login_window.login_success.connect(self.open_dashboard)
        self.login_window.show()

        if self.welcome_window:
            self.welcome_window.close()
            self.welcome_window = None

        if self.main_window:
            self.main_window.close()
            self.main_window = None

    def open_create_account(self):
        QMessageBox.information(
            None,
            "Créer un compte",
            "Veuillez contacter l’administrateur pour créer un compte."
        )

    def open_dashboard(self, user_data):
        self.main_window = MainWindow(user_data)

        if hasattr(self.main_window, "logout_requested"):
            self.main_window.logout_requested.connect(self.open_login)

        self.main_window.show()

        if self.login_window:
            self.login_window.close()
            self.login_window = None


if __name__ == "__main__":
    app = QApplication(sys.argv)

    start_backend()

    app.setQuitOnLastWindowClosed(False)

    controller = AppController()

    sys.exit(app.exec())