import os
from PySide6.QtCore import Qt, QSize
from PySide6.QtGui import QPixmap
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QFrame, QLineEdit, QComboBox, QTableWidget, QTableWidgetItem,
    QHeaderView, QMessageBox, QTextEdit
)


CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))


def find_project_root(start_dir):
    current = start_dir
    while True:
        assets_path = os.path.join(current, "assets", "icons")
        if os.path.exists(assets_path):
            return current

        parent = os.path.dirname(current)
        if parent == current:
            return start_dir

        current = parent


PROJECT_ROOT = find_project_root(CURRENT_DIR)


def icon_path(file_name: str) -> str:
    return os.path.join(PROJECT_ROOT, "assets", "icons", file_name)



class NotificationsPage(QWidget):
    def __init__(self, api_client, parent=None):
        super().__init__(parent)
        self.api_client = api_client
        self.notifications = []
        self.filtered_notifications = []
        self.setup_ui()
        self.load_notifications()

    def make_icon_label(self, icon_file: str, size: int = 28):
        label = QLabel()
        label.setObjectName("IconBox")
        label.setAlignment(Qt.AlignCenter)

        pixmap = QPixmap(icon_path(icon_file))
        if not pixmap.isNull():
            label.setPixmap(
                pixmap.scaled(size, size, Qt.KeepAspectRatio, Qt.SmoothTransformation)
            )

        return label

    def title_widget(self, text: str, icon_file: str):
        wrapper = QWidget()
        wrapper.setObjectName("TitleWidget")

        layout = QHBoxLayout(wrapper)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(14)

        layout.addWidget(self.make_icon_label(icon_file, 30))

        title = QLabel(text)
        title.setObjectName("Title")

        layout.addWidget(title)
        layout.addStretch()

        return wrapper

    def setup_ui(self):
        self.setStyleSheet("""
            QWidget {
                background-color: #071426;
                color: white;
                font-family: Segoe UI;
            }

            QLabel {
                background: transparent;
            }

            QWidget#TitleWidget {
                background: transparent;
                border: none;
            }

            QLabel#IconBox {
                background-color: #123B63;
                border: 1px solid #3BB3FF;
                border-radius: 24px;
                min-width: 48px;
                max-width: 48px;
                min-height: 48px;
                max-height: 48px;
            }

            QLabel#Title {
                font-size: 30px;
                font-weight: 800;
                color: white;
            }

            QLabel#Subtitle {
                font-size: 14px;
                color: #9fb8d8;
            }

            QFrame#Card {
                background-color: #10233F;
                border: 1px solid #1E4F80;
                border-radius: 18px;
            }

            QFrame#Card:hover {
                border: 1px solid #3BB3FF;
                background-color: #123052;
            }

            QLabel#CardTitle {
                font-size: 13px;
                font-weight: bold;
            }

            QLabel#CardValue {
                font-size: 30px;
                font-weight: 900;
                color: white;
            }

            QLabel#CardDesc {
                font-size: 12px;
                color: #9fb8d8;
            }

            QLineEdit, QComboBox {
                background-color: #10233F;
                border: 1px solid #1E4F80;
                border-radius: 10px;
                padding: 10px;
                color: white;
                font-size: 13px;
            }

            QPushButton {
                background-color: #123052;
                border: 1px solid #3BB3FF;
                border-radius: 10px;
                padding: 11px;
                color: white;
                font-weight: bold;
            }

            QPushButton:hover {
                background-color: #2563EB;
            }

            QPushButton#PrimaryButton {
                background-color: #1d4ed8;
                border: 1px solid #3b82f6;
            }

            QTableWidget {
                background-color: #10233F;
                border: 1px solid #1E4F80;
                border-radius: 14px;
                gridline-color: #1E4F80;
                selection-background-color: #123052;
                selection-color: white;
                font-size: 13px;
            }

            QHeaderView::section {
                background-color: #123052;
                color: #dce8ff;
                padding: 12px;
                border: none;
                font-weight: bold;
            }

            QTableWidget::item {
                padding: 8px;
                border-bottom: 1px solid #1E4F80;
            }

            QTextEdit {
                background: transparent;
                border: none;
                color: white;
                font-size: 13px;
                padding: 6px;
            }
        """)

        root = QVBoxLayout(self)
        root.setContentsMargins(28, 28, 28, 28)
        root.setSpacing(18)

        header = QHBoxLayout()

        left_header = QVBoxLayout()
        title = self.title_widget("Centre de notifications", "notification.png")

        subtitle = QLabel(
            "Surveillez les alertes importantes, les événements réseau et les notifications système."
        )
        subtitle.setObjectName("Subtitle")

        left_header.addWidget(title)
        left_header.addWidget(subtitle)

        header.addLayout(left_header)
        header.addStretch()

        self.btn_mark_all_read = QPushButton("Marquer comme lue")
        self.btn_mark_all_read.clicked.connect(self.mark_selected_as_read)

        self.btn_refresh = QPushButton("Actualiser")
        self.btn_refresh.setObjectName("PrimaryButton")
        self.btn_refresh.clicked.connect(self.load_notifications)

        header.addWidget(self.btn_mark_all_read)
        header.addWidget(self.btn_refresh)

        root.addLayout(header)

        cards_layout = QHBoxLayout()
        cards_layout.setSpacing(14)

        self.card_critical_value = QLabel("0")
        self.card_warning_value = QLabel("0")
        self.card_info_value = QLabel("0")
        self.card_total_value = QLabel("0")

        cards_layout.addWidget(
            self.create_stat_card("CRITIQUES", self.card_critical_value, "Nécessitent une action", "#ff4d4f")
        )
        cards_layout.addWidget(
            self.create_stat_card("AVERTISSEMENTS", self.card_warning_value, "À surveiller", "#faad14")
        )
        cards_layout.addWidget(
            self.create_stat_card("INFORMATIONS", self.card_info_value, "Événements généraux", "#3b82f6")
        )
        cards_layout.addWidget(
            self.create_stat_card("TOTAL", self.card_total_value, "Toutes notifications", "#22c55e")
        )

        root.addLayout(cards_layout)

        filters_layout = QHBoxLayout()
        filters_layout.setSpacing(12)

        self.type_filter = QComboBox()
        self.type_filter.addItems(["Tous les types", "critical", "error", "warning", "info", "success"])
        self.type_filter.currentTextChanged.connect(self.apply_filters)

        self.status_filter = QComboBox()
        self.status_filter.addItems(["Tous les statuts", "Non lu", "Lu"])
        self.status_filter.currentTextChanged.connect(self.apply_filters)

        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Rechercher dans les notifications...")
        self.search_input.textChanged.connect(self.apply_filters)

        filters_layout.addWidget(self.type_filter, 20)
        filters_layout.addWidget(self.status_filter, 20)
        filters_layout.addWidget(self.search_input, 60)

        root.addLayout(filters_layout)

        self.table = QTableWidget()
        self.table.setColumnCount(7)
        self.table.setHorizontalHeaderLabels([
            "Priorité", "Titre", "Message", "Source", "Date", "Statut", "Action"
        ])

        header_view = self.table.horizontalHeader()
        header_view.setSectionResizeMode(0, QHeaderView.ResizeToContents)
        header_view.setSectionResizeMode(1, QHeaderView.ResizeToContents)
        header_view.setSectionResizeMode(2, QHeaderView.Stretch)
        header_view.setSectionResizeMode(3, QHeaderView.ResizeToContents)
        header_view.setSectionResizeMode(4, QHeaderView.ResizeToContents)
        header_view.setSectionResizeMode(5, QHeaderView.ResizeToContents)
        header_view.setSectionResizeMode(6, QHeaderView.ResizeToContents)

        self.table.verticalHeader().setVisible(False)
        self.table.setWordWrap(True)
        self.table.setSelectionBehavior(QTableWidget.SelectRows)
        self.table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.table.setAlternatingRowColors(False)

        root.addWidget(self.table)

    def create_stat_card(self, title, value_label, desc, color):
        card = QFrame()
        card.setObjectName("Card")
        card.setMinimumHeight(115)

        layout = QVBoxLayout(card)
        layout.setContentsMargins(20, 18, 20, 18)

        title_label = QLabel(title)
        title_label.setObjectName("CardTitle")
        title_label.setStyleSheet(f"color: {color};")

        value_label.setObjectName("CardValue")

        desc_label = QLabel(desc)
        desc_label.setObjectName("CardDesc")

        layout.addWidget(title_label)
        layout.addWidget(value_label)
        layout.addWidget(desc_label)

        return card

    def call_api(self, method_name, *args):
        if hasattr(self.api_client, method_name):
            return getattr(self.api_client, method_name)(*args)

        if method_name == "get_notifications" and hasattr(self.api_client, "get_user_notifications"):
            return self.api_client.get_user_notifications()

        return {
            "success": False,
            "error": f"Méthode API manquante : {method_name}"
        }

    def load_notifications(self):
        result = self.call_api("get_notifications")

        if not result.get("success"):
            QMessageBox.warning(self, "Erreur", result.get("error", str(result)))
            return

        self.notifications = result.get("data", {}).get("notifications", [])
        self.apply_filters()
        self.update_stats()

    def apply_filters(self):
        selected_type = self.type_filter.currentText()
        selected_status = self.status_filter.currentText()
        search = self.search_input.text().lower().strip()

        self.filtered_notifications = []

        for notif in self.notifications:
            notif_type = str(notif.get("type", "info")).lower()
            title = str(notif.get("title", "")).lower()
            message = str(notif.get("message", "")).lower()
            is_read = int(notif.get("is_read", 0))

            if selected_type != "Tous les types" and notif_type != selected_type:
                continue

            if selected_status == "Non lu" and is_read == 1:
                continue

            if selected_status == "Lu" and is_read == 0:
                continue

            if search and search not in title and search not in message:
                continue

            self.filtered_notifications.append(notif)

        self.populate_table()

    def populate_table(self):
        self.table.setRowCount(len(self.filtered_notifications))

        for row, notif in enumerate(self.filtered_notifications):
            notif_type = str(notif.get("type", "info")).lower()
            title = notif.get("title") or "Notification"
            message = notif.get("message") or ""
            created_at = notif.get("created_at") or ""
            is_read = int(notif.get("is_read", 0))
            email_sent = int(notif.get("email_sent", 0))

            priority_text = self.format_priority(notif_type)
            source = self.detect_source(title, message)
            status = "Lu" if is_read else "Non lu"
            action = "Email envoyé" if email_sent else "App seulement"

            normal_values = [
                priority_text,
                title,
                source,
                created_at,
                status,
                action
            ]

            col_map = {
                0: normal_values[0],
                1: normal_values[1],
                3: normal_values[2],
                4: normal_values[3],
                5: normal_values[4],
                6: normal_values[5],
            }

            for col, value in col_map.items():
                item = QTableWidgetItem(str(value))
                item.setFlags(item.flags() ^ Qt.ItemIsEditable)

                if col == 0:
                    item.setForeground(self.priority_color(notif_type))

                if col == 5:
                    item.setForeground(Qt.green if is_read else Qt.red)

                if col == 6:
                    item.setForeground(Qt.green if email_sent else Qt.lightGray)

                self.table.setItem(row, col, item)

            message_widget = QTextEdit()
            message_widget.setPlainText(str(message))
            message_widget.setReadOnly(True)
            message_widget.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
            message_widget.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)

            self.table.setCellWidget(row, 2, message_widget)

            calculated_height = max(90, min(220, 42 + (len(str(message)) // 75) * 24))
            self.table.setRowHeight(row, calculated_height)

    def update_stats(self):
        critical = 0
        warning = 0
        info = 0

        for notif in self.notifications:
            notif_type = str(notif.get("type", "info")).lower()

            if notif_type in ["critical", "error"]:
                critical += 1
            elif notif_type == "warning":
                warning += 1
            else:
                info += 1

        self.card_critical_value.setText(str(critical))
        self.card_warning_value.setText(str(warning))
        self.card_info_value.setText(str(info))
        self.card_total_value.setText(str(len(self.notifications)))

    def format_priority(self, notif_type):
        if notif_type == "critical":
            return "CRITICAL"
        if notif_type == "error":
            return "ERROR"
        if notif_type == "warning":
            return "WARNING"
        if notif_type == "success":
            return "SUCCESS"
        return "INFO"

    def priority_color(self, notif_type):
        if notif_type in ["critical", "error"]:
            return Qt.red
        if notif_type == "warning":
            return Qt.yellow
        if notif_type == "success":
            return Qt.green
        return Qt.cyan

    def detect_source(self, title, message):
        text = f"{title} {message}".lower()

        if "découverte" in text or "joignable" in text:
            return "Découverte Réseau"
        if "vlan" in text:
            return "VLAN Planner"
        if "vlsm" in text:
            return "VLSM Planner"
        if "acl" in text:
            return "ACL Engine"
        if "déploiement" in text:
            return "Déploiement"
        if "ia" in text or "ai" in text:
            return "AI Analysis"

        return "Système"

    def mark_selected_as_read(self):
        selected_rows = self.table.selectionModel().selectedRows()

        if not selected_rows:
            QMessageBox.information(self, "Information", "Sélectionnez une notification.")
            return

        for selected in selected_rows:
            row = selected.row()
            notif = self.filtered_notifications[row]
            notification_id = notif.get("id")

            if notification_id:
                self.call_api("mark_notification_read", notification_id)

        self.load_notifications()