from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QLabel, QFrame, QHBoxLayout,
    QPushButton, QTableWidget, QTableWidgetItem,
    QInputDialog, QMessageBox, QLineEdit, QComboBox,
    QHeaderView
)

from services.api_client import ApiClient


class UsersPage(QWidget):
    def __init__(self, user_data=None):
        super().__init__()

        self.user_data = user_data or {}
        self.token = self.user_data.get("token")
        self.all_users = []

        self.api = ApiClient()
        self.api.token = self.token

        self.setup_ui()
        self.apply_styles()

        permissions = self.user_data.get("permissions", [])

        if "manage_users" in permissions:
            self.load_users()
        else:
            print("UsersPage skipped: permission missing")

    def setup_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(24, 24, 24, 24)
        root.setSpacing(18)

        header = QHBoxLayout()

        title_box = QVBoxLayout()
        title = QLabel("Gestion des Utilisateurs")
        title.setObjectName("pageTitle")

        subtitle = QLabel("Gérez les utilisateurs, rôles, emails et permissions d’accès à la plateforme.")
        subtitle.setObjectName("subTitle")

        title_box.addWidget(title)
        title_box.addWidget(subtitle)

        self.add_btn = QPushButton("+  Créer un utilisateur")
        self.add_btn.setObjectName("primaryButton")

        header.addLayout(title_box)
        header.addStretch()
        header.addWidget(self.add_btn)

        root.addLayout(header)

        stats = QHBoxLayout()
        stats.setSpacing(14)

        self.total_card_value = QLabel("0")
        self.admin_card_value = QLabel("0")
        self.active_card_value = QLabel("0")
        self.inactive_card_value = QLabel("0")

        stats.addWidget(self.create_stat_card("Total utilisateurs", self.total_card_value, "Tous les utilisateurs", "#0B3B75"))
        stats.addWidget(self.create_stat_card("Administrateurs", self.admin_card_value, "Accès complet", "#3A236D"))
        stats.addWidget(self.create_stat_card("Utilisateurs actifs", self.active_card_value, "Comptes actifs", "#0B4A35"))
        stats.addWidget(self.create_stat_card("Inactifs", self.inactive_card_value, "Comptes désactivés", "#4A2028"))

        root.addLayout(stats)

        filters = QHBoxLayout()
        filters.setSpacing(12)

        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Rechercher par nom, email ou ID...")
        self.search_input.textChanged.connect(self.apply_filters)

        self.role_filter = QComboBox()
        self.role_filter.addItems(["Tous les rôles", "admin", "engineer", "analyst", "viewer"])
        self.role_filter.currentTextChanged.connect(self.apply_filters)

        self.refresh_btn = QPushButton("Actualiser")
        self.refresh_btn.setObjectName("secondaryButton")
        self.refresh_btn.clicked.connect(self.load_users)

        filters.addWidget(self.search_input, 3)
        filters.addWidget(self.role_filter, 1)
        filters.addWidget(self.refresh_btn)

        root.addLayout(filters)

        table_card = QFrame()
        table_card.setObjectName("card")
        table_layout = QVBoxLayout(table_card)
        table_layout.setContentsMargins(14, 14, 14, 14)

        self.table = QTableWidget(0, 6)
        self.table.setHorizontalHeaderLabels([
            "ID", "Nom d'utilisateur", "Email réel", "Rôle", "Statut", "Actions"
        ])
        self.table.setSelectionBehavior(QTableWidget.SelectRows)
        self.table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.table.verticalHeader().setVisible(False)
        self.table.horizontalHeader().setStretchLastSection(True)
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)

        table_layout.addWidget(self.table)
        root.addWidget(table_card)

        actions = QHBoxLayout()

        self.role_btn = QPushButton("Modifier rôle")
        self.role_btn.setObjectName("secondaryButton")

        self.delete_btn = QPushButton("Supprimer utilisateur")
        self.delete_btn.setObjectName("dangerButton")

        actions.addStretch()
        actions.addWidget(self.role_btn)
        actions.addWidget(self.delete_btn)

        root.addLayout(actions)

        self.add_btn.clicked.connect(self.add_user)
        self.role_btn.clicked.connect(self.update_role)
        self.delete_btn.clicked.connect(self.delete_user)

    def create_stat_card(self, title, value_label, subtitle, color):
        frame = QFrame()
        frame.setObjectName("statCard")
        frame.setStyleSheet(f"""
            QFrame#statCard {{
                background-color: {color};
                border: 1px solid rgba(255,255,255,0.10);
                border-radius: 14px;
            }}

            QFrame#statCard:hover {{
                border: 2px solid #60A5FA;
            }}

            QFrame#statCard QLabel {{
                background: transparent;
            }}
        """)

        layout = QVBoxLayout(frame)
        layout.setContentsMargins(16, 14, 16, 14)

        t = QLabel(title)
        t.setObjectName("statTitle")

        value_label.setObjectName("statValue")

        s = QLabel(subtitle)
        s.setObjectName("statSub")

        layout.addWidget(t)
        layout.addStretch()
        layout.addWidget(value_label)
        layout.addWidget(s)

        return frame

    def load_users(self):
        permissions = self.user_data.get("permissions", [])

        if "manage_users" not in permissions:
            print("UsersPage load_users blocked: permission missing")
            return

        result = self.api.get_users()

        if not result["success"]:
            QMessageBox.critical(self, "Erreur", result["error"])
            return

        data = result["data"]

        if isinstance(data, dict):
            self.all_users = data.get("users", [])
        else:
            self.all_users = data

        self.update_stats()
        self.apply_filters()

    def update_stats(self):
        total = len(self.all_users)
        admins = 0
        active = 0
        inactive = 0

        for user in self.all_users:
            role = user.get("role") or user.get("role_name") or "viewer"
            status = user.get("status", "actif")

            if role == "admin":
                admins += 1

            if status in ["actif", "active", True, 1]:
                active += 1
            else:
                inactive += 1

        self.total_card_value.setText(str(total))
        self.admin_card_value.setText(str(admins))
        self.active_card_value.setText(str(active))
        self.inactive_card_value.setText(str(inactive))

    def apply_filters(self):
        search = self.search_input.text().lower().strip()
        role_filter = self.role_filter.currentText()

        filtered = []

        for user in self.all_users:
            username = str(user.get("username", "")).lower()
            email = str(user.get("email", "") or "").lower()
            role = user.get("role") or user.get("role_name") or "viewer"
            user_id = str(user.get("id", "")).lower()

            match_search = (
                search in username
                or search in email
                or search in user_id
            )

            match_role = (
                role_filter == "Tous les rôles"
                or role == role_filter
            )

            if match_search and match_role:
                filtered.append(user)

        self.fill_table(filtered)

    def fill_table(self, users):
        self.table.setRowCount(0)

        for row, user in enumerate(users):
            self.table.insertRow(row)

            role = user.get("role") or user.get("role_name") or "viewer"
            status = user.get("status", "actif")
            email = user.get("email") or ""

            self.table.setItem(row, 0, QTableWidgetItem(str(user.get("id", ""))))
            self.table.setItem(row, 1, QTableWidgetItem(user.get("username", "")))
            self.table.setItem(row, 2, QTableWidgetItem(email))
            self.table.setItem(row, 3, QTableWidgetItem(role))
            self.table.setItem(row, 4, QTableWidgetItem(str(status)))

            actions_item = QTableWidgetItem("Modifier / Supprimer")
            actions_item.setTextAlignment(Qt.AlignCenter)
            self.table.setItem(row, 5, actions_item)

    def add_user(self):
        username, ok = QInputDialog.getText(self, "Ajouter utilisateur", "Nom d'utilisateur :")
        if not ok or not username.strip():
            return

        email, ok = QInputDialog.getText(self, "Ajouter utilisateur", "Email réel de l'utilisateur :")
        if not ok or not email.strip():
            QMessageBox.warning(self, "Attention", "L'email est obligatoire.")
            return

        if "@" not in email or "." not in email:
            QMessageBox.warning(self, "Attention", "Veuillez entrer un email valide.")
            return

        password, ok = QInputDialog.getText(self, "Ajouter utilisateur", "Mot de passe :")
        if not ok or not password.strip():
            return

        role, ok = QInputDialog.getItem(
            self,
            "Ajouter utilisateur",
            "Rôle :",
            ["admin", "engineer", "analyst", "viewer"],
            3,
            False
        )
        if not ok:
            return

        payload = {
            "username": username.strip(),
            "password": password.strip(),
            "role_name": role,
            "email": email.strip()
        }

        result = self.api.create_user(payload)

        if result["success"]:
            QMessageBox.information(self, "Succès", "Utilisateur ajouté avec succès.")
            self.load_users()
        else:
            QMessageBox.critical(self, "Erreur", result["error"])

    def update_role(self):
        selected_row = self.table.currentRow()

        if selected_row < 0:
            QMessageBox.warning(self, "Attention", "Sélectionnez un utilisateur.")
            return

        user_id = self.table.item(selected_row, 0).text()
        current_role = self.table.item(selected_row, 3).text()

        roles = ["admin", "engineer", "analyst", "viewer"]
        default_index = roles.index(current_role) if current_role in roles else 3

        role, ok = QInputDialog.getItem(
            self,
            "Modifier rôle",
            "Nouveau rôle :",
            roles,
            default_index,
            False
        )

        if not ok:
            return

        payload = {
            "role_name": role
        }

        result = self.api.update_user_role(user_id, payload)

        if result["success"]:
            QMessageBox.information(self, "Succès", "Rôle modifié avec succès.")
            self.load_users()
        else:
            QMessageBox.critical(self, "Erreur", result["error"])

    def delete_user(self):
        selected_row = self.table.currentRow()

        if selected_row < 0:
            QMessageBox.warning(self, "Attention", "Sélectionnez un utilisateur.")
            return

        user_id = self.table.item(selected_row, 0).text()
        username = self.table.item(selected_row, 1).text()

        confirm = QMessageBox.question(
            self,
            "Confirmation",
            f"Voulez-vous vraiment supprimer l'utilisateur '{username}' ?",
            QMessageBox.Yes | QMessageBox.No
        )

        if confirm != QMessageBox.Yes:
            return

        result = self.api.delete_user(user_id)

        if result["success"]:
            QMessageBox.information(self, "Succès", "Utilisateur supprimé avec succès.")
            self.load_users()
        else:
            QMessageBox.critical(self, "Erreur", result["error"])

    def apply_styles(self):
        self.setStyleSheet("""
            QWidget {
                background-color: #06111f;
                color: white;
                font-family: Segoe UI, Arial, sans-serif;
                font-size: 13px;
            }

            #pageTitle {
                font-size: 28px;
                font-weight: 900;
                color: white;
                background: transparent;
            }

            #subTitle {
                color: #9DAEC8;
                font-size: 13px;
                background: transparent;
            }

            #card {
                background-color: #0A192B;
                border: 1px solid #1C3352;
                border-radius: 16px;
            }

            QFrame#statCard QLabel {
                background: transparent;
            }

            #statTitle {
                color: #E5EDFF;
                font-size: 13px;
                font-weight: 700;
                background: transparent;
            }

            #statValue {
                font-size: 34px;
                font-weight: 900;
                color: white;
                background: transparent;
            }

            #statSub {
                color: #D0DBF5;
                font-size: 12px;
                background: transparent;
            }

            #primaryButton, #secondaryButton, #dangerButton {
                min-height: 38px;
                border-radius: 10px;
                font-weight: 800;
                padding: 8px 14px;
            }

            #primaryButton {
                background-color: #2563EB;
                color: white;
                border: none;
            }

            #primaryButton:hover {
                background-color: #3B82F6;
            }

            #secondaryButton {
                background-color: #0D1A2C;
                color: white;
                border: 1px solid #2B4262;
            }

            #secondaryButton:hover {
                border: 1px solid #60A5FA;
            }

            #dangerButton {
                background-color: #EF4444;
                color: white;
                border: none;
            }

            #dangerButton:hover {
                background-color: #DC2626;
            }

            QLineEdit, QComboBox {
                background-color: #081525;
                border: 1px solid #243D5C;
                border-radius: 10px;
                padding: 10px;
                color: white;
            }

            QLineEdit:hover, QComboBox:hover {
                border: 1px solid #60A5FA;
            }

            QTableWidget {
                background-color: #081525;
                border: 1px solid #243D5C;
                border-radius: 12px;
                color: white;
                gridline-color: #1E3552;
                selection-background-color: #243B6B;
            }

            QHeaderView::section {
                background-color: #101F35;
                color: #C8D5EA;
                border: none;
                padding: 10px;
                font-weight: 800;
            }
        """)