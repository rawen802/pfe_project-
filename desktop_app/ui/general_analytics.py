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

    # ==================================================
    # UI
    # ==================================================
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

        # ================= HEADER =================
        header = QFrame()
        header.setObjectName("headerCard")
        header.setMinimumHeight(115)

        header_layout = QHBoxLayout(header)
        header_layout.setContentsMargins(24, 18, 24, 18)
        header_layout.setSpacing(16)

        title_box = QVBoxLayout()
        title_box.setSpacing(6)

        title = QLabel("General Analytics")
        title.setObjectName("title")

        subtitle = QLabel(
            "Vue globale basée sur les audit logs : utilisateurs, risques, IA et déploiements."
        )
        subtitle.setObjectName("subtitle")
        subtitle.setWordWrap(True)

        self.access_label = QLabel("")
        self.access_label.setObjectName("accessLabel")
        self.access_label.hide()

        title_box.addWidget(title)
        title_box.addWidget(subtitle)
        title_box.addWidget(self.access_label)

        self.refresh_btn = QPushButton("Actualiser")
        self.refresh_btn.setObjectName("primaryButton")
        self.refresh_btn.setFixedHeight(42)
        self.refresh_btn.setFixedWidth(130)

        header_layout.addLayout(title_box)
        header_layout.addStretch()
        header_layout.addWidget(self.refresh_btn)

        main_layout.addWidget(header)

        # ================= KPI CARDS =================
        cards_grid = QGridLayout()
        cards_grid.setHorizontalSpacing(16)
        cards_grid.setVerticalSpacing(16)

        self.card_total_logs = self.create_card("Total Logs", "0", "Toutes les actions enregistrées")
        self.card_failed_logins = self.create_card("Failed Logins", "0", "Tentatives échouées")
        self.card_critical = self.create_card("Actions Critiques", "0", "Événements sensibles")
        self.card_ai = self.create_card("Actions IA", "0", "Analyses et validations")
        self.card_deployments = self.create_card("Déploiements", "0", "Actions de déploiement")
        self.card_risk = self.create_card("Risk Level", "LOW", "Niveau global")

        cards_grid.addWidget(self.card_total_logs, 0, 0)
        cards_grid.addWidget(self.card_failed_logins, 0, 1)
        cards_grid.addWidget(self.card_critical, 0, 2)
        cards_grid.addWidget(self.card_ai, 1, 0)
        cards_grid.addWidget(self.card_deployments, 1, 1)
        cards_grid.addWidget(self.card_risk, 1, 2)

        main_layout.addLayout(cards_grid)

        # ================= RISK CARD =================
        risk_frame = QFrame()
        risk_frame.setObjectName("riskCard")
        risk_frame.setMinimumHeight(145)

        risk_layout = QVBoxLayout(risk_frame)
        risk_layout.setContentsMargins(22, 16, 22, 16)
        risk_layout.setSpacing(10)

        risk_header = QHBoxLayout()
        risk_header.setSpacing(12)

        risk_title = QLabel("Score de Risque")
        risk_title.setObjectName("sectionTitle")

        self.risk_level_badge = QLabel("LOW")
        self.risk_level_badge.setObjectName("riskBadge")
        self.risk_level_badge.setAlignment(Qt.AlignCenter)

        risk_header.addWidget(risk_title)
        risk_header.addStretch()
        risk_header.addWidget(self.risk_level_badge)

        self.risk_score_label = QLabel("0 / 100")
        self.risk_score_label.setObjectName("riskScore")

        self.risk_bar = QProgressBar()
        self.risk_bar.setRange(0, 100)
        self.risk_bar.setValue(0)
        self.risk_bar.setTextVisible(True)
        self.risk_bar.setObjectName("riskBar")
        self.risk_bar.setFixedHeight(26)

        self.risk_summary = QLabel("Aucune donnée chargée.")
        self.risk_summary.setObjectName("summaryText")
        self.risk_summary.setWordWrap(True)

        risk_layout.addLayout(risk_header)
        risk_layout.addWidget(self.risk_score_label)
        risk_layout.addWidget(self.risk_bar)
        risk_layout.addWidget(self.risk_summary)

        main_layout.addWidget(risk_frame)

        # ================= TABLES =================
        tables_layout = QHBoxLayout()
        tables_layout.setSpacing(16)

        self.top_users_table = self.create_table(["Utilisateur", "Actions"], height=220)
        self.modules_table = self.create_table(["Module", "Nombre"], height=220)

        tables_layout.addWidget(self.create_table_card("Top Utilisateurs", self.top_users_table))
        tables_layout.addWidget(self.create_table_card("Actions par Module", self.modules_table))

        main_layout.addLayout(tables_layout)

        self.critical_table = self.create_table(
            ["Date", "Utilisateur", "Action", "Module", "Status"],
            height=260
        )

        main_layout.addWidget(
            self.create_table_card("Actions Critiques Récentes", self.critical_table)
        )

        main_layout.addStretch()

        scroll.setWidget(content)
        root_layout.addWidget(scroll)

        self.refresh_btn.clicked.connect(self.load_analytics)

    def create_card(self, title, value, subtitle=""):
        card = QFrame()
        card.setObjectName("statCard")
        card.setMinimumHeight(128)

        layout = QVBoxLayout(card)
        layout.setContentsMargins(20, 16, 20, 16)
        layout.setSpacing(6)

        title_label = QLabel(title)
        title_label.setObjectName("cardTitle")
        title_label.setAlignment(Qt.AlignLeft)

        value_label = QLabel(value)
        value_label.setObjectName("cardValue")
        value_label.setAlignment(Qt.AlignLeft)

        subtitle_label = QLabel(subtitle)
        subtitle_label.setObjectName("cardSubtitle")
        subtitle_label.setWordWrap(True)

        card.value_label = value_label
        card.subtitle_label = subtitle_label

        layout.addWidget(title_label)
        layout.addWidget(value_label)
        layout.addWidget(subtitle_label)
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

    # ==================================================
    # PERMISSIONS
    # ==================================================
    def can_view_analytics(self):
        role = str(self.user_data.get("role", "")).lower()
        permissions = self.user_data.get("permissions", []) or []

        return (
            role == "admin"
            or "view_security_analytics" in permissions
            or "view_analytics" in permissions
            or "view_general_analytics" in permissions
        )

    def show_access_restricted(self):
        self.access_label.setText("Accès restreint selon vos permissions.")
        self.access_label.show()

        self.refresh_btn.setEnabled(False)

        self.card_total_logs.value_label.setText("—")
        self.card_failed_logins.value_label.setText("—")
        self.card_critical.value_label.setText("—")
        self.card_ai.value_label.setText("—")
        self.card_deployments.value_label.setText("—")
        self.card_risk.value_label.setText("—")

        self.risk_score_label.setText("—")
        self.risk_bar.setValue(0)
        self.risk_summary.setText("Votre rôle ne permet pas de consulter les statistiques générales.")

        self.top_users_table.setRowCount(0)
        self.modules_table.setRowCount(0)
        self.critical_table.setRowCount(0)

    # ==================================================
    # LOAD DATA
    # ==================================================
    def load_analytics(self):
        if not self.can_view_analytics():
            self.show_access_restricted()
            return

        self.access_label.hide()
        self.refresh_btn.setEnabled(True)

        if not self.api:
            QMessageBox.warning(self, "Erreur", "ApiClient introuvable.")
            return

        try:
            if hasattr(self.api, "get_security_analytics"):
                response = self.api.get_security_analytics()
            else:
                response = self.api.get("/security/analytics")

            if not response or not response.get("success"):
                error_message = str(
                    response.get("error", "Impossible de charger General Analytics.")
                    if isinstance(response, dict)
                    else "Impossible de charger General Analytics."
                )

                status_code = str(response.get("status_code", "")) if isinstance(response, dict) else ""

                if (
                    "403" in status_code
                    or "forbidden" in error_message.lower()
                    or "permission" in error_message.lower()
                    or "accès restreint" in error_message.lower()
                ):
                    self.show_access_restricted()
                    return

                QMessageBox.warning(self, "Erreur", error_message)
                return

            data = response.get("data", {})
            if isinstance(data, dict) and data.get("data"):
                data = data.get("data")

            self.analytics_data = data if isinstance(data, dict) else {}
            self.update_ui()

        except Exception as e:
            print("GENERAL ANALYTICS ERROR:", e)
            QMessageBox.warning(
                self,
                "Erreur",
                "Service momentanément indisponible."
            )

    # ==================================================
    # UPDATE UI
    # ==================================================
    def update_ui(self):
        data = self.analytics_data

        total_logs = int(data.get("total_logs", 0) or 0)
        failed_logins = int(data.get("failed_logins", 0) or 0)
        critical_actions = int(data.get("critical_actions", 0) or 0)
        ai_actions = int(data.get("ai_actions", 0) or 0)
        deployments = int(data.get("deployments", 0) or 0)
        risk_score = int(float(data.get("risk_score", 0) or 0))
        risk_level = str(data.get("risk_level", "LOW")).upper()

        self.card_total_logs.value_label.setText(str(total_logs))
        self.card_failed_logins.value_label.setText(str(failed_logins))
        self.card_critical.value_label.setText(str(critical_actions))
        self.card_ai.value_label.setText(str(ai_actions))
        self.card_deployments.value_label.setText(str(deployments))
        self.card_risk.value_label.setText(risk_level)

        self.risk_score_label.setText(f"{risk_score} / 100")
        self.risk_bar.setValue(max(0, min(100, risk_score)))
        self.risk_level_badge.setText(risk_level)

        self.apply_risk_style(risk_level)

        self.risk_summary.setText(
            self.build_risk_summary(
                total_logs=total_logs,
                failed_logins=failed_logins,
                critical_actions=critical_actions,
                ai_actions=ai_actions,
                deployments=deployments,
                risk_level=risk_level
            )
        )

        self.populate_top_users(data.get("top_users", []))
        self.populate_modules(data.get("actions_by_module", []))
        self.populate_critical_actions(data.get("recent_critical_actions", []))

    def build_risk_summary(
        self,
        total_logs,
        failed_logins,
        critical_actions,
        ai_actions,
        deployments,
        risk_level
    ):
        if total_logs == 0:
            return "Aucune activité enregistrée pour le moment."

        return (
            f"Le système contient {total_logs} action(s) enregistrée(s), "
            f"avec {failed_logins} tentative(s) de connexion échouée(s), "
            f"{critical_actions} action(s) critique(s), "
            f"{ai_actions} action(s) IA et {deployments} déploiement(s). "
            f"Le niveau de risque global est actuellement {risk_level}."
        )

    def apply_risk_style(self, risk_level):
        self.risk_level_badge.setProperty("level", risk_level)
        self.risk_bar.setProperty("level", risk_level)

        for widget in [self.risk_level_badge, self.risk_bar]:
            widget.style().unpolish(widget)
            widget.style().polish(widget)

    # ==================================================
    # POPULATE TABLES
    # ==================================================
    def populate_top_users(self, users):
        users = users or []
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
        modules = modules or []
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
        actions = actions or []
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

                if col == 4:
                    status_upper = value.upper()
                    if status_upper in ["FAILED", "ERROR", "CRITICAL"]:
                        table_item.setForeground(Qt.red)
                    elif status_upper in ["WARNING", "PARTIAL_SUCCESS"]:
                        table_item.setForeground(Qt.yellow)
                    elif status_upper == "SUCCESS":
                        table_item.setForeground(Qt.green)

                self.critical_table.setItem(row, col, table_item)

        self.critical_table.resizeRowsToContents()

    # ==================================================
    # STYLES
    # ==================================================
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

            QLabel {
                background: transparent;
            }

            QFrame#headerCard {
                background-color: #0d1a2d;
                border: 1px solid #183252;
                border-radius: 18px;
            }

            QLabel#title {
                color: white;
                font-size: 28px;
                font-weight: 900;
            }

            QLabel#subtitle {
                color: #9fb0c8;
                font-size: 14px;
            }

            QLabel#accessLabel {
                color: #facc15;
                font-size: 13px;
                font-weight: 700;
            }

            QPushButton#primaryButton {
                background-color: #2563eb;
                color: white;
                border: none;
                border-radius: 10px;
                font-weight: bold;
                padding: 8px 16px;
            }

            QPushButton#primaryButton:hover {
                background-color: #1d4ed8;
            }

            QPushButton#primaryButton:disabled {
                background-color: #334155;
                color: #94a3b8;
            }

            QFrame#statCard {
                background-color: #10233f;
                border: 1px solid #1e4f80;
                border-radius: 18px;
            }

            QFrame#statCard:hover {
                border: 1px solid #3bb3ff;
                background-color: #123052;
            }

            QLabel#cardTitle {
                color: #b9cbe7;
                font-size: 13px;
                font-weight: 700;
            }

            QLabel#cardValue {
                color: white;
                font-size: 28px;
                font-weight: 900;
            }

            QLabel#cardSubtitle {
                color: #8ea7cb;
                font-size: 12px;
            }

            QFrame#riskCard,
            QFrame#tableCard {
                background-color: #10233f;
                border: 1px solid #1e4f80;
                border-radius: 18px;
            }

            QLabel#sectionTitle {
                color: white;
                font-size: 17px;
                font-weight: 900;
            }

            QLabel#riskScore {
                color: #69c8ff;
                font-size: 22px;
                font-weight: 900;
            }

            QLabel#summaryText {
                color: #b9cbe7;
                font-size: 13px;
            }

            QLabel#riskBadge {
                min-width: 88px;
                max-width: 110px;
                min-height: 30px;
                border-radius: 10px;
                font-size: 12px;
                font-weight: 900;
                padding: 4px 12px;
            }

            QLabel#riskBadge[level="LOW"] {
                color: #22c55e;
                background-color: rgba(34,197,94,0.15);
                border: 1px solid #22c55e;
            }

            QLabel#riskBadge[level="MEDIUM"] {
                color: #f59e0b;
                background-color: rgba(245,158,11,0.15);
                border: 1px solid #f59e0b;
            }

            QLabel#riskBadge[level="HIGH"] {
                color: #ef4444;
                background-color: rgba(239,68,68,0.15);
                border: 1px solid #ef4444;
            }

            QProgressBar#riskBar {
                background-color: #081321;
                border: 1px solid #28476d;
                border-radius: 10px;
                color: white;
                text-align: center;
                font-weight: 800;
            }

            QProgressBar#riskBar::chunk {
                border-radius: 9px;
                background-color: #22c55e;
            }

            QProgressBar#riskBar[level="MEDIUM"]::chunk {
                background-color: #f59e0b;
            }

            QProgressBar#riskBar[level="HIGH"]::chunk {
                background-color: #ef4444;
            }

            QTableWidget#dataTable {
                background-color: #081321;
                alternate-background-color: #0c1d33;
                border: 1px solid #1c3554;
                border-radius: 12px;
                gridline-color: #1f3555;
                color: white;
                font-size: 13px;
            }

            QHeaderView::section {
                background-color: #13233b;
                color: #dce8ff;
                padding: 9px;
                border: none;
                font-weight: bold;
            }

            QTableWidget::item {
                padding: 8px;
            }

            QTableWidget::item:selected {
                background-color: #2c2470;
                color: white;
            }

            QScrollBar:vertical {
                background: #0d1a2d;
                width: 12px;
                border-radius: 6px;
            }

            QScrollBar::handle:vertical {
                background: #274569;
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
