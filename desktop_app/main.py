import sys
from PySide6.QtWidgets import QApplication, QMessageBox

from ui.welcome_page import WelcomePage
from ui.login_page import LoginPage
from ui.main_window import MainWindow



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

    def open_create_account(self):
        QMessageBox.information(
            None,
            "Créer un compte",
            "Veuillez contacter l’administrateur pour créer un compte."
        )

    def open_dashboard(self, user_data):
        self.main_window = MainWindow(user_data)
        self.main_window.show()

        if self.login_window:
            self.login_window.close()


if __name__ == "__main__":
    app = QApplication(sys.argv)
    controller = AppController()
    sys.exit(app.exec())