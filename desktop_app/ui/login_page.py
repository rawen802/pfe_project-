from PySide6.QtWidgets import (
    QWidget, QHBoxLayout, QVBoxLayout, QLabel, QLineEdit,
    QPushButton, QCheckBox, QFrame, QSizePolicy, QDialog,
    QMessageBox
)
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QFont, QPixmap
from services.api_client import ApiClient
import os


class SetupAdminDialog(QDialog):
    def __init__(self, api_client, parent=None):
        super().__init__(parent)

        self.api = api_client
        self.setWindowTitle("Créer le compte administrateur")
        self.setFixedWidth(430)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(28, 28, 28, 28)
        layout.setSpacing(14)

        title = QLabel("Premier administrateur")
        title.setObjectName("dialogTitle")

        desc = QLabel(
            "Aucun administrateur n’existe encore.\n"
            "Créez le compte admin principal de l’application."
        )
        desc.setObjectName("dialogDesc")

        self.username_input = QLineEdit()
        self.username_input.setPlaceholderText("Nom d'utilisateur")
        self.username_input.setObjectName("dialogInput")

        self.email_input = QLineEdit()
        self.email_input.setPlaceholderText("Email réel")
        self.email_input.setObjectName("dialogInput")

        self.password_input = QLineEdit()
        self.password_input.setPlaceholderText("Mot de passe")
        self.password_input.setEchoMode(QLineEdit.Password)
        self.password_input.setObjectName("dialogInput")

        self.confirm_password_input = QLineEdit()
        self.confirm_password_input.setPlaceholderText("Confirmer le mot de passe")
        self.confirm_password_input.setEchoMode(QLineEdit.Password)
        self.confirm_password_input.setObjectName("dialogInput")

        self.error_label = QLabel("")
        self.error_label.setObjectName("dialogError")
        self.error_label.setAlignment(Qt.AlignCenter)

        self.create_btn = QPushButton("Créer le compte admin")
        self.create_btn.setObjectName("dialogButton")
        self.create_btn.setFixedHeight(46)

        layout.addWidget(title)
        layout.addWidget(desc)
        layout.addSpacing(10)
        layout.addWidget(self.username_input)
        layout.addWidget(self.email_input)
        layout.addWidget(self.password_input)
        layout.addWidget(self.confirm_password_input)
        layout.addWidget(self.error_label)
        layout.addWidget(self.create_btn)

        self.create_btn.clicked.connect(self.create_admin)

        self.setStyleSheet("""
        QDialog {
            background-color: #07142a;
            color: white;
            font-family: Arial;
        }

        QLabel#dialogTitle {
            font-size: 24px;
            font-weight: bold;
            color: white;
        }

        QLabel#dialogDesc {
            color: #b6c2d6;
            font-size: 14px;
        }

        QLineEdit#dialogInput {
            background-color: #13233b;
            border: 1px solid #2b4568;
            border-radius: 10px;
            color: white;
            padding: 12px;
            font-size: 15px;
        }

        QLineEdit#dialogInput:focus {
            border: 1px solid #1e88ff;
        }

        QPushButton#dialogButton {
            background-color: #1266e3;
            color: white;
            border: none;
            border-radius: 10px;
            font-size: 16px;
            font-weight: bold;
        }

        QPushButton#dialogButton:hover {
            background-color: #1e7bff;
        }

        QLabel#dialogError {
            color: #ff4d4d;
            font-size: 13px;
        }
        """)

    def create_admin(self):
        username = self.username_input.text().strip()
        email = self.email_input.text().strip()
        password = self.password_input.text().strip()
        confirm_password = self.confirm_password_input.text().strip()

        if not username or not email or not password or not confirm_password:
            self.error_label.setText("Veuillez remplir tous les champs.")
            return

        if "@" not in email or "." not in email:
            self.error_label.setText("Veuillez entrer un email valide.")
            return

        if password != confirm_password:
            self.error_label.setText("Les mots de passe ne correspondent pas.")
            return

        payload = {
            "username": username,
            "email": email,
            "password": password,
            "role_name": "admin"
        }

        self.create_btn.setEnabled(False)
        self.create_btn.setText("Création...")

        try:
            if hasattr(self.api, "setup_admin"):
                result = self.api.setup_admin(payload)
            else:
                result = self.api.post("/auth/setup-admin", payload)

            if result and result.get("success"):
                QMessageBox.information(
                    self,
                    "Succès",
                    "Compte administrateur créé avec succès."
                )
                self.accept()
            else:
                self.error_label.setText(
                    result.get("error", "Erreur création administrateur.")
                )

        except Exception as e:
            self.error_label.setText(str(e))

        finally:
            self.create_btn.setEnabled(True)
            self.create_btn.setText("Créer le compte admin")


class LoginPage(QWidget):
    login_success = Signal(dict)

    def __init__(self):
        super().__init__()

        self.setWindowTitle("NetAutoAI - Login")
        self.resize(1200, 720)
        self.setObjectName("LoginPage")

        self.api = ApiClient()
        self.admin_exists = True

        main_layout = QHBoxLayout(self)
        main_layout.setContentsMargins(40, 40, 40, 40)
        main_layout.setSpacing(0)

        left_card = QFrame()
        left_card.setObjectName("leftCard")
        left_card.setFixedWidth(520)

        left_layout = QVBoxLayout(left_card)
        left_layout.setContentsMargins(45, 45, 45, 45)
        left_layout.setSpacing(18)

        logo = QLabel("NetAutoAI")
        logo.setObjectName("logo")
        logo.setFont(QFont("Arial", 28, QFont.Bold))

        subtitle = QLabel("Network Automation Platform")
        subtitle.setObjectName("subtitle")

        welcome = QLabel("Bienvenue")
        welcome.setObjectName("welcome")
        welcome.setFont(QFont("Arial", 24, QFont.Bold))

        self.desc = QLabel("Connectez-vous à votre compte")
        self.desc.setObjectName("desc")

        username_label = QLabel("Nom d’utilisateur")
        username_label.setObjectName("fieldLabel")

        self.username_input = QLineEdit()
        self.username_input.setPlaceholderText("Entrez votre nom d’utilisateur")
        self.username_input.setObjectName("input")

        password_label = QLabel("Mot de passe")
        password_label.setObjectName("fieldLabel")

        self.password_input = QLineEdit()
        self.password_input.setPlaceholderText("Entrez votre mot de passe")
        self.password_input.setEchoMode(QLineEdit.Password)
        self.password_input.setObjectName("input")

        option_layout = QHBoxLayout()

        self.remember_check = QCheckBox("Se souvenir de moi")
        self.remember_check.setChecked(True)
        self.remember_check.setObjectName("remember")

        forgot_label = QLabel("Mot de passe oublié ?")
        forgot_label.setObjectName("link")

        option_layout.addWidget(self.remember_check)
        option_layout.addStretch()
        option_layout.addWidget(forgot_label)

        self.login_btn = QPushButton("Se connecter")
        self.login_btn.setObjectName("loginButton")
        self.login_btn.setFixedHeight(54)

        self.setup_admin_btn = QPushButton("Créer le compte admin")
        self.setup_admin_btn.setObjectName("setupAdminButton")
        self.setup_admin_btn.setFixedHeight(48)
        self.setup_admin_btn.setVisible(False)

        self.error_label = QLabel("")
        self.error_label.setObjectName("error")
        self.error_label.setAlignment(Qt.AlignCenter)

        self.footer = QLabel("Pas encore de compte ? Contactez l’administrateur")
        self.footer.setObjectName("footer")
        self.footer.setAlignment(Qt.AlignCenter)

        left_layout.addWidget(logo)
        left_layout.addWidget(subtitle)
        left_layout.addSpacing(25)
        left_layout.addWidget(welcome)
        left_layout.addWidget(self.desc)
        left_layout.addSpacing(15)
        left_layout.addWidget(username_label)
        left_layout.addWidget(self.username_input)
        left_layout.addWidget(password_label)
        left_layout.addWidget(self.password_input)
        left_layout.addLayout(option_layout)
        left_layout.addWidget(self.login_btn)
        left_layout.addWidget(self.setup_admin_btn)
        left_layout.addWidget(self.error_label)
        left_layout.addSpacing(15)
        left_layout.addWidget(self.footer)
        left_layout.addStretch()

        right_card = QFrame()
        right_card.setObjectName("rightCard")
        right_card.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)

        right_layout = QVBoxLayout(right_card)
        right_layout.setAlignment(Qt.AlignCenter)
        right_layout.setSpacing(20)

        BASE_DIR = os.path.dirname(os.path.abspath(__file__))
        icon_path = os.path.join(
            BASE_DIR,
            "..",
            "..",
            "assets",
            "icones",
            "verified.png"
        )

        shield = QLabel()
        shield.setObjectName("shield")
        pixmap = QPixmap(icon_path)

        print("Icon exists:", os.path.exists(icon_path))

        pixmap = pixmap.scaled(32, 32, Qt.KeepAspectRatio, Qt.SmoothTransformation)

        shield.setPixmap(pixmap)
        shield.setAlignment(Qt.AlignCenter)

        title = QLabel("Accès sécurisé")
        title.setObjectName("securityTitle")
        title.setAlignment(Qt.AlignCenter)

        desc_right = QLabel(
            "Authentification protégée\n"
            "Gestion des rôles\n"
            "Plateforme intelligente"
        )
        desc_right.setObjectName("securityDesc")
        desc_right.setAlignment(Qt.AlignCenter)

        right_layout.addWidget(shield)
        right_layout.addWidget(title)
        right_layout.addWidget(desc_right)

        main_layout.addWidget(left_card)
        main_layout.addWidget(right_card)

        self.login_btn.clicked.connect(self.handle_login)
        self.password_input.returnPressed.connect(self.handle_login)
        self.setup_admin_btn.clicked.connect(self.open_setup_admin_dialog)

        self.apply_styles()
        self.check_admin_status()

    def check_admin_status(self):
        try:
            if hasattr(self.api, "has_admin"):
                result = self.api.has_admin()
            else:
                result = self.api.get("/auth/has-admin")

            data = result.get("data", result)

            if result and result.get("success") and data.get("has_admin") is False:
                self.admin_exists = False
                self.setup_admin_btn.setVisible(True)
                self.footer.setText("Première utilisation : créez le compte admin principal")
                self.desc.setText("Aucun admin trouvé. Créez d’abord le compte administrateur.")
            else:
                self.admin_exists = True
                self.setup_admin_btn.setVisible(False)
                self.footer.setText("Pas encore de compte ? Contactez l’administrateur")

        except Exception as e:
            print("CHECK ADMIN ERROR:", e)
            self.setup_admin_btn.setVisible(False)

    def open_setup_admin_dialog(self):
        dialog = SetupAdminDialog(self.api, self)

        if dialog.exec() == QDialog.Accepted:
            self.check_admin_status()

    def show_access_restricted_message(self):
        QMessageBox.information(
            self,
            "Accès restreint",
            "Votre rôle ne permet pas d'accéder à cette fonctionnalité."
        )

    def handle_login(self):
        username = self.username_input.text().strip()
        password = self.password_input.text().strip()

        if not username or not password:
            self.error_label.setText("Veuillez remplir tous les champs.")
            return

        self.login_btn.setEnabled(False)
        self.login_btn.setText("Connexion...")
        self.error_label.setText("")

        try:
            result = self.api.login(username, password)

            if result.get("success"):
                self.api.token = result.get("token")
                me = self.api.get_me()

                if me.get("success"):
                    user_data = {
                        "id": me["data"].get("id"),
                        "username": me["data"].get("username"),
                        "role": me["data"].get("role"),
                        "permissions": me["data"].get("permissions", []),
                        "token": result.get("token")
                    }

                    print("USER DATA =", user_data)

                    # Envoyer les informations utilisateur à l'application principale
                    self.login_success.emit(user_data)

                    # Fermer la fenêtre Login après une connexion réussie
                    # pour éviter d'avoir plusieurs fenêtres ouvertes.
                    self.close()
                    return

                else:
                    error_message = me.get("error", "")
                    status_code = me.get("status_code")

                    if (
                        status_code == 403
                        or "Accès restreint" in error_message
                        or "permissions" in error_message
                    ):
                        self.show_access_restricted_message()
                    else:
                        self.error_label.setText("Erreur récupération utilisateur")

            else:
                error_message = result.get("error", "")
                status_code = result.get("status_code")

                if (
                    status_code == 403
                    or "Accès restreint" in error_message
                    or "permissions" in error_message
                ):
                    self.show_access_restricted_message()
                else:
                    self.error_label.setText("Nom d'utilisateur ou mot de passe incorrect")

        except Exception as e:
            print("LOGIN ERROR:", e)

            error_message = str(e)

            if (
                "Accès restreint" in error_message
                or "permissions" in error_message
                or "403" in error_message
                or "Forbidden" in error_message
            ):
                self.show_access_restricted_message()
            else:
                self.error_label.setText("Erreur connexion backend")

        finally:
            self.login_btn.setEnabled(True)
            self.login_btn.setText("Se connecter")

    def apply_styles(self):
        self.setStyleSheet("""
        QWidget#LoginPage {
            background-color: #020b1a;
            color: white;
            font-family: Arial;
        }

        QFrame#leftCard {
            background-color: #07142a;
            border: 1px solid #1d3557;
            border-top-left-radius: 22px;
            border-bottom-left-radius: 22px;
        }

        QFrame#rightCard {
            background-color: #041126;
            border: 1px solid #1d3557;
            border-top-right-radius: 22px;
            border-bottom-right-radius: 22px;
        }

        QLabel#logo {
            color: #ffffff;
        }

        QLabel#subtitle {
            color: #9fb0c8;
            font-size: 16px;
        }

        QLabel#welcome {
            color: #ffffff;
        }

        QLabel#desc {
            color: #b6c2d6;
            font-size: 18px;
        }

        QLabel#fieldLabel {
            color: #ffffff;
            font-size: 15px;
            font-weight: bold;
        }

        QLineEdit#input {
            background-color: #13233b;
            border: 1px solid #2b4568;
            border-radius: 10px;
            color: white;
            padding: 14px;
            font-size: 16px;
        }

        QLineEdit#input:focus {
            border: 1px solid #1e88ff;
            background-color: #172943;
        }

        QCheckBox#remember {
            color: #dce6f5;
            font-size: 14px;
        }

        QLabel#link {
            color: #1e88ff;
            font-size: 14px;
        }

        QPushButton#loginButton {
            background-color: #1266e3;
            color: white;
            border: none;
            border-radius: 10px;
            font-size: 17px;
            font-weight: bold;
        }

        QPushButton#loginButton:hover {
            background-color: #1e7bff;
        }

        QPushButton#loginButton:disabled {
            background-color: #34495e;
            color: #bdc3c7;
        }

        QPushButton#setupAdminButton {
            background-color: #0f766e;
            color: white;
            border: none;
            border-radius: 10px;
            font-size: 15px;
            font-weight: bold;
        }

        QPushButton#setupAdminButton:hover {
            background-color: #14b8a6;
        }

        QLabel#error {
            color: #ff4d4d;
            font-size: 14px;
        }

        QLabel#footer {
            color: #9fb0c8;
            font-size: 14px;
        }

        QLabel#shield {
            font-size: 120px;
        }

        QLabel#securityTitle {
            color: white;
            font-size: 30px;
            font-weight: bold;
        }

        QLabel#securityDesc {
            color: #9fb0c8;
            font-size: 18px;
        }
        """)