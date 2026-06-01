import json

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QTableWidget, QTableWidgetItem, QHeaderView, QFrame,
    QLineEdit, QComboBox, QMessageBox
)


class AuditLogsPage(QWidget):
    def __init__(self, api_client=None, user_data=None):
        super().__init__()

        self.api = api_client
        self.user_data = user_data or {}
        self.logs = []

        self.setup_ui()
        self.apply_styles()
        self.apply_rbac_ui()

        if self.can_view_audit_logs():
            self.load_logs()
        else:
            self.show_restricted_access()

    def can_view_audit_logs(self):
        permissions = self.user_data.get("permissions", [])
        role = str(self.user_data.get("role", "")).lower()

        return role == "admin" or "view_audit_logs" in permissions

    def apply_rbac_ui(self):
        if not self.can_view_audit_logs():
            self.search_input.hide()
            self.status_filter.hide()
            self.module_filter.hide()
            self.refresh_btn.hide()
            self.table.hide()

    def show_restricted_access(self):
        self.logs = []
        self.table.setRowCount(0)
        self.access_label.setText("Accès restreint selon vos permissions")
        self.access_label.show()

    def clear_restricted_access(self):
        self.access_label.hide()

    def setup_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(24, 24, 24, 24)
        main_layout.setSpacing(18)

        # ================= HEADER =================
        header = QFrame()
        header.setObjectName("headerCard")

        header_layout = QVBoxLayout(header)
        header_layout.setSpacing(8)

        title = QLabel("Audit Logs")
        title.setObjectName("title")

        subtitle = QLabel(
            "Historique des actions effectuées dans l’application"
        )
        subtitle.setObjectName("subtitle")

        header_layout.addWidget(title)
        header_layout.addWidget(subtitle)

        # ================= FILTERS =================
        filters = QFrame()
        filters.setObjectName("filterCard")

        filters_layout = QHBoxLayout(filters)
        filters_layout.setContentsMargins(16, 16, 16, 16)
        filters_layout.setSpacing(12)

        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText(
            "Rechercher par action, utilisateur, module..."
        )
        self.search_input.setObjectName("searchInput")

        self.status_filter = QComboBox()
        self.status_filter.setObjectName("combo")

        self.status_filter.addItems([
            "Tous",
            "success",
            "failed",
            "warning",
            "partial_success"
        ])

        self.module_filter = QComboBox()
        self.module_filter.setObjectName("combo")
        self.module_filter.addItems(["Tous"])

        self.refresh_btn = QPushButton("Actualiser")
        self.refresh_btn.setObjectName("primaryButton")

        filters_layout.addWidget(self.search_input, 3)
        filters_layout.addWidget(self.status_filter, 1)
        filters_layout.addWidget(self.module_filter, 1)
        filters_layout.addWidget(self.refresh_btn)

        # ================= TABLE =================
        self.table = QTableWidget()
        self.table.setObjectName("auditTable")

        self.table.setColumnCount(6)

        self.table.setHorizontalHeaderLabels([
            "Date",
            "Utilisateur",
            "Action",
            "Module",
            "Status",
            "Extra"
        ])

        self.table.setWordWrap(True)
        self.table.setAlternatingRowColors(True)
        self.table.setSelectionBehavior(QTableWidget.SelectRows)
        self.table.setEditTriggers(QTableWidget.NoEditTriggers)

        header_table = self.table.horizontalHeader()

        header_table.setStretchLastSection(True)

        header_table.setSectionResizeMode(
            0,
            QHeaderView.ResizeToContents
        )

        header_table.setSectionResizeMode(
            1,
            QHeaderView.ResizeToContents
        )

        header_table.setSectionResizeMode(
            2,
            QHeaderView.ResizeToContents
        )

        header_table.setSectionResizeMode(
            3,
            QHeaderView.ResizeToContents
        )

        header_table.setSectionResizeMode(
            4,
            QHeaderView.ResizeToContents
        )

        header_table.setSectionResizeMode(
            5,
            QHeaderView.Stretch
        )

        self.table.verticalHeader().setVisible(False)

        self.access_label = QLabel("")
        self.access_label.setObjectName("accessLabel")
        self.access_label.setAlignment(Qt.AlignCenter)
        self.access_label.hide()

        main_layout.addWidget(header)
        main_layout.addWidget(filters)
        main_layout.addWidget(self.access_label)
        main_layout.addWidget(self.table)

        # ================= SIGNALS =================
        self.refresh_btn.clicked.connect(self.load_logs)

        self.search_input.textChanged.connect(
            self.apply_filters
        )

        self.status_filter.currentTextChanged.connect(
            self.apply_filters
        )

        self.module_filter.currentTextChanged.connect(
            self.apply_filters
        )

    # ==================================================
    # LOAD LOGS
    # ==================================================
    def load_logs(self):
        if not self.can_view_audit_logs():
            self.show_restricted_access()
            return

        self.clear_restricted_access()

        if not self.api:
            QMessageBox.warning(
                self,
                "Erreur",
                "ApiClient introuvable."
            )
            return

        try:
            if hasattr(self.api, "get_audit_logs"):
                response = self.api.get_audit_logs(limit=100)
            else:
                response = self.api.get("/audit/logs?limit=100")

            if not response or not response.get("success"):
                QMessageBox.warning(
                    self,
                    "Erreur",
                    response.get(
                        "error",
                        "Impossible de charger les logs."
                    )
                )
                return

            data = response.get("data", response)

            self.logs = data.get("logs", [])

            self.update_module_filter()
            self.apply_filters()

        except Exception as e:
            QMessageBox.critical(
                self,
                "Erreur",
                f"Erreur lors du chargement des audit logs : {str(e)}"
            )

    # ==================================================
    # MODULE FILTER
    # ==================================================
    def update_module_filter(self):
        current = self.module_filter.currentText()

        modules = sorted({
            log.get("module")
            for log in self.logs
            if log.get("module")
        })

        self.module_filter.blockSignals(True)

        self.module_filter.clear()
        self.module_filter.addItem("Tous")
        self.module_filter.addItems(modules)

        if current in modules:
            self.module_filter.setCurrentText(current)

        self.module_filter.blockSignals(False)

    # ==================================================
    # APPLY FILTERS
    # ==================================================
    def apply_filters(self):
        search = self.search_input.text().lower().strip()

        status = self.status_filter.currentText()
        module = self.module_filter.currentText()

        filtered_logs = []

        for log in self.logs:

            log_text = json.dumps(
                log,
                ensure_ascii=False
            ).lower()

            if search and search not in log_text:
                continue

            if status != "Tous":

                log_status = str(
                    log.get("status", "")
                ).lower().strip()

                selected_status = status.lower().strip()

                if log_status != selected_status:
                    continue

            if (
                module != "Tous"
                and str(log.get("module", "")) != module
            ):
                continue

            filtered_logs.append(log)

        self.populate_table(filtered_logs)

    # ==================================================
    # FORMAT EXTRA
    # ==================================================
    def format_extra(self, extra):

        if isinstance(extra, dict):
            return json.dumps(
                extra,
                ensure_ascii=False,
                indent=2
            )

        if isinstance(extra, list):
            return json.dumps(
                extra,
                ensure_ascii=False,
                indent=2
            )

        return str(extra or "-")

    # ==================================================
    # POPULATE TABLE
    # ==================================================
    def populate_table(self, logs):

        self.table.setRowCount(len(logs))

        for row, log in enumerate(logs):

            created_at = str(log.get("created_at", ""))
            username = str(log.get("username") or "-")
            action = str(log.get("action") or "-")
            module = str(log.get("module") or "-")
            status = str(log.get("status") or "-")

            extra_text = self.format_extra(
                log.get("extra")
            )

            values = [
                created_at,
                username,
                action,
                module,
                status,
                extra_text
            ]

            for col, value in enumerate(values):

                item = QTableWidgetItem(value)

                if col == 5:
                    item.setTextAlignment(
                        Qt.AlignLeft | Qt.AlignVCenter
                    )
                else:
                    item.setTextAlignment(Qt.AlignCenter)

                if col == 4:

                    status_upper = value.upper()

                    if status_upper == "SUCCESS":
                        item.setForeground(Qt.green)

                    elif status_upper in ["FAILED", "ERROR"]:
                        item.setForeground(Qt.red)

                    elif status_upper in [
                        "WARNING",
                        "PARTIAL_SUCCESS"
                    ]:
                        item.setForeground(Qt.yellow)

                self.table.setItem(row, col, item)

        self.table.resizeRowsToContents()

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

            QFrame#headerCard {
                background-color: #0d1a2d;
                border: 1px solid #183252;
                border-radius: 18px;
                padding: 18px;
            }

            QLabel#title {
                font-size: 28px;
                font-weight: 800;
                color: #ffffff;
            }

            QLabel#subtitle {
                font-size: 14px;
                color: #9fb0c8;
            }

            QLabel#accessLabel {
                background-color: #0d1a2d;
                border: 1px solid #183252;
                border-radius: 14px;
                padding: 28px;
                color: #9fb0c8;
                font-size: 18px;
                font-weight: bold;
            }

            QFrame#filterCard {
                background-color: #0d1a2d;
                border: 1px solid #183252;
                border-radius: 16px;
            }

            QLineEdit#searchInput {
                background-color: #111f35;
                border: 1px solid #274569;
                border-radius: 10px;
                padding: 10px 12px;
                color: white;
                font-size: 14px;
            }

            QLineEdit#searchInput:focus {
                border: 1px solid #1e88ff;
            }

            QComboBox#combo {
                background-color: #111f35;
                border: 1px solid #274569;
                border-radius: 10px;
                padding: 10px;
                color: white;
                font-size: 14px;
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

            QTableWidget#auditTable {
                background-color: #0d1a2d;
                alternate-background-color: #101f35;
                border: 1px solid #183252;
                border-radius: 14px;
                gridline-color: #1f3555;
                color: white;
                font-size: 13px;
            }

            QHeaderView::section {
                background-color: #13233b;
                color: #dce8ff;
                padding: 10px;
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