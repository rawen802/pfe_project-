from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QFrame, QTableWidget, QTableWidgetItem, QHeaderView,
    QMessageBox, QGridLayout, QProgressBar, QScrollArea
)


class GeneralAnalyticsPage(QWidget):
    def __init__(self, user_data=None, api_client=None):
        super().__init__()

        self.user_data = user_data or {}
        self.api = api_client
        self.analytics_data = {}

        self.setup_ui()
        self.apply_styles()
        self.load_analytics()

    def setup_ui(self):
        root_layout = QVBoxLayout(self)
        root_layout.setContentsMargins(0, 0, 0, 0)
        root_layout.setSpacing(0)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setObjectName("scrollArea")
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        scroll.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)

        content = QWidget()
        content.setObjectName("contentWidget")

        main_layout = QVBoxLayout(content)
        main_layout.setContentsMargins(24, 24, 24, 24)
        main_layout.setSpacing(18)

        header = QFrame()
        header.setObjectName("headerCard")
        header.setFixedHeight(120)

        header_layout = QHBoxLayout(header)
        header_layout.setContentsMargins(22, 18, 22, 18)

        title_box = QVBoxLayout()
        title_box.setSpacing(6)

        title = QLabel("General Analytics")
        title.setObjectName("title")

        subtitle = QLabel(
            "Vue globale basée sur les audit logs : utilisateurs, risques, IA et déploiements"
        )
        subtitle.setObjectName("subtitle")

        title_box.addWidget(title)
        title_box.addWidget(subtitle)

        self.refresh_btn = QPushButton("Actualiser")
        self.refresh_btn.setObjectName("primaryButton")
        self.refresh_btn.setFixedHeight(42)
        self.refresh_btn.setFixedWidth(120)

        header_layout.addLayout(title_box)
        header_layout.addStretch()
        header_layout.addWidget(self.refresh_btn)

        main_layout.addWidget(header)

        cards_grid = QGridLayout()
        cards_grid.setHorizontalSpacing(16)
        cards_grid.setVerticalSpacing(16)

        self.card_total_logs = self.create_card("Total Logs", "0")
        self.card_failed_logins = self.create_card("Failed Logins", "0")
        self.card_critical = self.create_card("Actions Critiques", "0")
        self.card_ai = self.create_card("Actions IA", "0")
        self.card_deployments = self.create_card("Déploiements", "0")
        self.card_risk = self.create_card("Risk Level", "LOW")

        cards_grid.addWidget(self.card_total_logs, 0, 0)
        cards_grid.addWidget(self.card_failed_logins, 0, 1)
        cards_grid.addWidget(self.card_critical, 0, 2)
        cards_grid.addWidget(self.card_ai, 1, 0)
        cards_grid.addWidget(self.card_deployments, 1, 1)
        cards_grid.addWidget(self.card_risk, 1, 2)

        main_layout.addLayout(cards_grid)

        risk_frame = QFrame()
        risk_frame.setObjectName("riskCard")
        risk_frame.setFixedHeight(120)

        risk_layout = QVBoxLayout(risk_frame)
        risk_layout.setContentsMargins(20, 14, 20, 14)
        risk_layout.setSpacing(8)

        risk_title = QLabel("Score de Risque")
        risk_title.setObjectName("sectionTitle")

        self.risk_score_label = QLabel("0 / 100")
        self.risk_score_label.setObjectName("riskScore")

        self.risk_bar = QProgressBar()
        self.risk_bar.setRange(0, 100)
        self.risk_bar.setValue(0)
        self.risk_bar.setTextVisible(True)
        self.risk_bar.setObjectName("riskBar")
        self.risk_bar.setFixedHeight(24)

        risk_layout.addWidget(risk_title)
        risk_layout.addWidget(self.risk_score_label)
        risk_layout.addWidget(self.risk_bar)

        main_layout.addWidget(risk_frame)

        tables_layout = QHBoxLayout()
        tables_layout.setSpacing(16)

        self.top_users_table = self.create_table(["Utilisateur", "Actions"], height=210)
        self.modules_table = self.create_table(["Module", "Nombre"], height=210)

        tables_layout.addWidget(
            self.create_table_card("Top Utilisateurs", self.top_users_table)
        )
        tables_layout.addWidget(
            self.create_table_card("Actions par Module", self.modules_table)
        )

        main_layout.addLayout(tables_layout)

        self.critical_table = self.create_table(
            ["Date", "Utilisateur", "Action", "Module", "Status"],
            height=240
        )

        main_layout.addWidget(
            self.create_table_card("Actions Critiques Récentes", self.critical_table)
        )

        main_layout.addStretch()

        scroll.setWidget(content)
        root_layout.addWidget(scroll)

        self.refresh_btn.clicked.connect(self.load_analytics)

    def create_card(self, title, value):
        card = QFrame()
        card.setObjectName("statCard")
        card.setFixedHeight(110)

        layout = QVBoxLayout(card)
        layout.setContentsMargins(20, 14, 20, 14)
        layout.setSpacing(6)

        title_label = QLabel(title)
        title_label.setObjectName("cardTitle")
        title_label.setAlignment(Qt.AlignLeft)

        value_label = QLabel(value)
        value_label.setObjectName("cardValue")
        value_label.setAlignment(Qt.AlignLeft)

        card.value_label = value_label

        layout.addWidget(title_label)
        layout.addWidget(value_label)
        layout.addStretch()

        return card

    def create_table(self, headers, height=200):
        table = QTableWidget()
        table.setObjectName("dataTable")
        table.setColumnCount(len(headers))
        table.setHorizontalHeaderLabels(headers)

        table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        table.setAlternatingRowColors(True)
        table.setEditTriggers(QTableWidget.NoEditTriggers)
        table.setSelectionBehavior(QTableWidget.SelectRows)
        table.verticalHeader().setVisible(False)
        table.setWordWrap(True)

        table.setMinimumHeight(height)
        table.setMaximumHeight(height)

        return table

    def create_table_card(self, title, table):
        card = QFrame()
        card.setObjectName("tableCard")

        layout = QVBoxLayout(card)
        layout.setContentsMargins(18, 16, 18, 16)
        layout.setSpacing(12)

        title_label = QLabel(title)
        title_label.setObjectName("sectionTitle")

        layout.addWidget(title_label)
        layout.addWidget(table)

        return card

    def load_analytics(self):
        if not self.api:
            QMessageBox.warning(self, "Erreur", "ApiClient introuvable.")
            return

        try:
            if hasattr(self.api, "get_security_analytics"):
                response = self.api.get_security_analytics()
            else:
                response = self.api.get("/security/analytics")

            if not response or not response.get("success"):
                QMessageBox.warning(
                    self,
                    "Erreur",
                    response.get("error", "Impossible de charger General Analytics.")
                )
                return

            data = response.get("data", {})
            if data.get("data"):
                data = data.get("data")

            self.analytics_data = data
            self.update_ui()

        except Exception as e:
            QMessageBox.critical(
                self,
                "Erreur",
                f"Erreur General Analytics : {str(e)}"
            )

    def update_ui(self):
        data = self.analytics_data

        total_logs = data.get("total_logs", 0)
        failed_logins = data.get("failed_logins", 0)
        critical_actions = data.get("critical_actions", 0)
        ai_actions = data.get("ai_actions", 0)
        deployments = data.get("deployments", 0)
        risk_score = data.get("risk_score", 0)
        risk_level = data.get("risk_level", "LOW")

        self.card_total_logs.value_label.setText(str(total_logs))
        self.card_failed_logins.value_label.setText(str(failed_logins))
        self.card_critical.value_label.setText(str(critical_actions))
        self.card_ai.value_label.setText(str(ai_actions))
        self.card_deployments.value_label.setText(str(deployments))
        self.card_risk.value_label.setText(str(risk_level))

        self.risk_score_label.setText(f"{risk_score} / 100")
        self.risk_bar.setValue(int(risk_score))

        self.populate_top_users(data.get("top_users", []))
        self.populate_modules(data.get("actions_by_module", []))
        self.populate_critical_actions(data.get("recent_critical_actions", []))

    def populate_top_users(self, users):
        self.top_users_table.setRowCount(len(users))

        for row, item in enumerate(users):
            username = str(item.get("username", "-"))
            count = str(item.get("action_count", 0))

            username_item = QTableWidgetItem(username)
            count_item = QTableWidgetItem(count)

            username_item.setTextAlignment(Qt.AlignCenter)
            count_item.setTextAlignment(Qt.AlignCenter)

            self.top_users_table.setItem(row, 0, username_item)
            self.top_users_table.setItem(row, 1, count_item)

        self.top_users_table.resizeRowsToContents()

    def populate_modules(self, modules):
        self.modules_table.setRowCount(len(modules))

        for row, item in enumerate(modules):
            module = str(item.get("module", "-"))
            count = str(item.get("count", 0))

            module_item = QTableWidgetItem(module)
            count_item = QTableWidgetItem(count)

            module_item.setTextAlignment(Qt.AlignCenter)
            count_item.setTextAlignment(Qt.AlignCenter)

            self.modules_table.setItem(row, 0, module_item)
            self.modules_table.setItem(row, 1, count_item)

        self.modules_table.resizeRowsToContents()

    def populate_critical_actions(self, actions):
        self.critical_table.setRowCount(len(actions))

        for row, item in enumerate(actions):
            values = [
                str(item.get("created_at", "-")),
                str(item.get("username", "-")),
                str(item.get("action", "-")),
                str(item.get("module", "-")),
                str(item.get("status", "-")),
            ]

            for col, value in enumerate(values):
                table_item = QTableWidgetItem(value)
                table_item.setTextAlignment(Qt.AlignCenter)
                self.critical_table.setItem(row, col, table_item)

        self.critical_table.resizeRowsToContents()

    def apply_styles(self):
        self.setStyleSheet("""
            QWidget {
                background-color: #0b1424;
                color: white;
                font-family: Arial, sans-serif;
            }

            QScrollArea#scrollArea {
                background-color: #0b1424;
                border: none;
            }

            QWidget#contentWidget {
                background-color: #0b1424;
            }

            QFrame#headerCard,
            QFrame#riskCard,
            QFrame#tableCard {
                background-color: #0f2138;
                border: 1px solid #24466f;
                border-radius: 18px;
            }

            QLabel#title {
                font-size: 30px;
                font-weight: 900;
                color: #ffffff;
                background: transparent;
            }

            QLabel#subtitle {
                font-size: 14px;
                color: #a8bddb;
                background: transparent;
            }

            QFrame#statCard {
                background-color: #102844;
                border: 1px solid #2d5b8d;
                border-radius: 16px;
                min-height: 110px;
                max-height: 110px;
            }

            QLabel#cardTitle {
                color: #b8c9e6;
                font-size: 15px;
                font-weight: 600;
                background: transparent;
            }

            QLabel#cardValue {
                color: #ffffff;
                font-size: 24px;
                font-weight: 900;
                background: transparent;
            }

            QLabel#sectionTitle {
                color: #ffffff;
                font-size: 18px;
                font-weight: bold;
                background: transparent;
            }

            QLabel#riskScore {
                color: #ffffff;
                font-size: 24px;
                font-weight: bold;
                background: transparent;
            }

            QProgressBar#riskBar {
                background-color: #102844;
                border: 1px solid #2d5b8d;
                border-radius: 10px;
                text-align: center;
                color: white;
                font-weight: bold;
            }

            QProgressBar#riskBar::chunk {
                background-color: #2563eb;
                border-radius: 10px;
            }

            QPushButton#primaryButton {
                background-color: #2563eb;
                color: white;
                border: none;
                border-radius: 10px;
                padding: 11px 18px;
                font-weight: bold;
            }

            QPushButton#primaryButton:hover {
                background-color: #1d4ed8;
            }

            QTableWidget#dataTable {
                background-color: #102844;
                alternate-background-color: #132f50;
                border: 1px solid #2d5b8d;
                border-radius: 12px;
                gridline-color: #264a72;
                color: white;
                font-size: 13px;
            }

            QHeaderView::section {
                background-color: #163a61;
                color: #dce8ff;
                padding: 10px;
                border: none;
                font-weight: bold;
            }

            QTableWidget::item {
                padding: 8px;
                background-color: transparent;
            }

            QTableWidget::item:selected {
                background-color: #2c2470;
                color: white;
            }

            QScrollBar:vertical {
                background: #0b1424;
                width: 12px;
                margin: 0px;
            }

            QScrollBar::handle:vertical {
                background: #2d5b8d;
                border-radius: 6px;
                min-height: 30px;
            }

            QScrollBar::handle:vertical:hover {
                background: #3b82f6;
            }

            QScrollBar::add-line:vertical,
            QScrollBar::sub-line:vertical {
                height: 0px;
            }
        """)