from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QFrame, QLineEdit, QComboBox, QTextEdit, QTableWidget,
    QTableWidgetItem, QMessageBox, QGraphicsView, QGraphicsScene, QGraphicsEllipseItem,
    QGraphicsRectItem, QSizePolicy, QScrollArea
)
from PySide6.QtCore import Qt, QPropertyAnimation, QEasingCurve
from PySide6.QtGui import QColor, QBrush, QPen, QFont, QPainter


class Card(QFrame):
    def __init__(self, title=""):
        super().__init__()
        self.setObjectName("card")
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)

        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(14, 14, 14, 14)
        self.layout.setSpacing(12)

        if title:
            lbl = QLabel(title)
            lbl.setObjectName("cardTitle")
            self.layout.addWidget(lbl)

        self.anim = QPropertyAnimation(self, b"maximumHeight")
        self.anim.setDuration(250)
        self.anim.setEasingCurve(QEasingCurve.OutCubic)


class ACLPage(QWidget):
    def __init__(self, api_client=None, report=None):
        super().__init__()

        self.api_client = api_client
        self.report = self.normalize_report(report) if report else {}
        self.app_state = {}

        self.plan = []
        self.current_policy = None
        self.acl_plan = None
        self.generated_config = None

        self.setMinimumSize(1000, 700)

        self.setup_ui()
        self.apply_style()

        # Mode réel : aucun fake report.
        # La page utilise uniquement le rapport reçu depuis Discovery.
        self.load_report_data(self.report)

    def setup_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setObjectName("pageScroll")
        scroll.setFrameShape(QFrame.NoFrame)

        container = QWidget()
        container.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)

        main = QVBoxLayout(container)
        main.setContentsMargins(24, 20, 24, 20)
        main.setSpacing(18)

        header = QHBoxLayout()
        header.setSpacing(16)

        title_box = QVBoxLayout()
        title = QLabel("ACL Intelligent Engine")
        title.setObjectName("pageTitle")

        subtitle = QLabel("Créer, analyser et générer automatiquement des ACL selon la topologie réseau.")
        subtitle.setObjectName("subtitle")

        title_box.addWidget(title)
        title_box.addWidget(subtitle)

        self.btn_analyze = QPushButton("Analyser & Générer le Plan")
        self.btn_analyze.setObjectName("primaryBtn")
        self.btn_analyze.setMinimumHeight(44)
        self.btn_analyze.clicked.connect(self.analyze_policy)

        header.addLayout(title_box)
        header.addStretch()
        header.addWidget(self.btn_analyze)
        main.addLayout(header)

        body = QHBoxLayout()
        body.setSpacing(18)

        left = QVBoxLayout()
        right = QVBoxLayout()
        left.setSpacing(18)
        right.setSpacing(18)

        policy_card = Card("1. Définir la Policy ACL")
        policy_card.setMinimumWidth(360)

        self.acl_name = QLineEdit()
        self.acl_name.setPlaceholderText("Ex: DENY_ADMIN_TO_SERVERS")

        self.source_zone = QComboBox()
        self.source_zone.addItems([])

        self.destination_zone = QComboBox()
        self.destination_zone.addItems([])

        self.action = QComboBox()
        self.action.addItems(["deny", "permit"])

        self.protocol = QComboBox()
        self.protocol.addItems(["tcp", "udp", "ip", "icmp", "any"])

        self.port = QLineEdit()
        self.port.setPlaceholderText("Ex: 443")

        self.description = QTextEdit()
        self.description.setPlaceholderText("Ex: Interdire HTTPS depuis ADMIN vers SERVERS")
        self.description.setMinimumHeight(90)
        self.description.setMaximumHeight(130)

        policy_card.layout.addWidget(QLabel("Nom ACL"))
        policy_card.layout.addWidget(self.acl_name)

        row1 = QHBoxLayout()
        row1.setSpacing(12)
        row1.addWidget(self.input_group("Zone source", self.source_zone))
        row1.addWidget(self.input_group("Zone destination", self.destination_zone))
        policy_card.layout.addLayout(row1)

        row2 = QHBoxLayout()
        row2.setSpacing(12)
        row2.addWidget(self.input_group("Action", self.action))
        row2.addWidget(self.input_group("Protocole", self.protocol))
        row2.addWidget(self.input_group("Port", self.port))
        policy_card.layout.addLayout(row2)

        policy_card.layout.addWidget(QLabel("Description"))
        policy_card.layout.addWidget(self.description)
        left.addWidget(policy_card, 3)

        existing_card = Card("2. ACL existantes sur l’équipement")

        self.acl_table = QTableWidget(0, 2)
        self.acl_table.setHorizontalHeaderLabels(["Nom ACL", "Règles"])
        self.acl_table.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.acl_table.setMinimumHeight(180)
        self.acl_table.verticalHeader().setVisible(False)
        self.acl_table.horizontalHeader().setStretchLastSection(True)

        existing_card.layout.addWidget(self.acl_table)
        left.addWidget(existing_card, 2)

        analysis_card = Card("3. Analyse intelligente & emplacement sélectionné")

        self.analysis_label = QLabel("Aucune analyse lancée.")
        self.analysis_label.setObjectName("analysisText")
        self.analysis_label.setWordWrap(True)
        self.analysis_label.setMinimumHeight(78)

        self.scene = QGraphicsScene()
        self.graph = QGraphicsView(self.scene)
        self.graph.setObjectName("graphView")
        self.graph.setMinimumHeight(330)
        self.graph.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.graph.setRenderHint(QPainter.Antialiasing)
        self.graph.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.graph.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)

        analysis_card.layout.addWidget(self.analysis_label)
        analysis_card.layout.addWidget(self.graph, 1)
        right.addWidget(analysis_card, 5)

        cli_card = Card("4. Règle Cisco proposée")

        self.cli_preview = QTextEdit()
        self.cli_preview.setReadOnly(True)
        self.cli_preview.setObjectName("cliBox")
        self.cli_preview.setMinimumHeight(150)
        self.cli_preview.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.cli_preview.setText("! La commande Cisco sera générée ici après analyse.")

        cli_card.layout.addWidget(self.cli_preview)
        right.addWidget(cli_card, 2)

        summary_card = Card("5. Résumé du plan d’action")

        self.summary = QLabel("Action : -\nÉquipement : -\nInterface : -\nDirection : -\nRaison : -")
        self.summary.setObjectName("summaryText")
        self.summary.setWordWrap(True)
        self.summary.setMinimumHeight(90)

        self.btn_validate = QPushButton("Valider & Ajouter au Plan")
        self.btn_validate.setObjectName("primaryBtn")
        self.btn_validate.setMinimumHeight(44)
        self.btn_validate.clicked.connect(self.add_to_plan)

        self.btn_go_ai = QPushButton("Passer à la validation AI")
        self.btn_go_ai.setObjectName("secondaryBtn")
        self.btn_go_ai.setMinimumHeight(44)
        self.btn_go_ai.clicked.connect(self.go_to_ai_validation)

        summary_card.layout.addWidget(self.summary)
        summary_card.layout.addWidget(self.btn_validate)
        summary_card.layout.addWidget(self.btn_go_ai)
        right.addWidget(summary_card, 2)

        body.addLayout(left, 35)
        body.addLayout(right, 65)

        main.addLayout(body, 1)

        scroll.setWidget(container)
        root.addWidget(scroll)

    def normalize_report(self, report):
        if not isinstance(report, dict):
            return {}

        if "data" in report and isinstance(report["data"], dict):
            report = report["data"]

        if "report" in report and isinstance(report["report"], dict):
            report = report["report"]

        return report

    def set_report(self, report: dict):
        self.report = self.normalize_report(report)
        self.app_state["report"] = self.report
        self.load_report_data(self.report)

    def load_report_data(self, report: dict):
        report = self.normalize_report(report)

        zones = self.extract_zones(report)
        self.source_zone.clear()
        self.destination_zone.clear()

        if zones:
            self.source_zone.addItems(zones)
            self.destination_zone.addItems(zones)
            if "ADMIN" in zones:
                self.source_zone.setCurrentText("ADMIN")
            if "SERVERS" in zones:
                self.destination_zone.setCurrentText("SERVERS")
        else:
            self.source_zone.addItem("AUCUNE_ZONE")
            self.destination_zone.addItem("AUCUNE_ZONE")

        self.populate_existing_acls(report)

    def extract_zones(self, report: dict):
        zones = []

        for item in report.get("network_context", {}).get("zones", []):
            name = item.get("zone_name") or item.get("name")
            if name and name not in zones:
                zones.append(str(name))

        for vlan in report.get("network_context", {}).get("vlans", []):
            name = vlan.get("zone_name") or vlan.get("name") or vlan.get("vlan_name")
            if name and name not in zones:
                zones.append(str(name))

        for device in report.get("inventory", {}).get("devices", []):
            for vlan in device.get("vlans", []):
                name = vlan.get("zone_name") or vlan.get("name") or vlan.get("vlan_name")
                if name and name not in zones:
                    zones.append(str(name))

        return zones

    def populate_existing_acls(self, report: dict):
        acl_rows = []

        for device in report.get("inventory", {}).get("devices", []):
            existing_acls = device.get("existing_acls", device.get("acls", []))
            if isinstance(existing_acls, dict):
                existing_acls = [existing_acls]

            for acl in existing_acls or []:
                if isinstance(acl, dict):
                    name = acl.get("acl_name") or acl.get("name") or acl.get("id") or "ACL"
                    rules = acl.get("rules", [])
                    count = len(rules) if isinstance(rules, list) else 0
                    acl_rows.append((str(name), f"{count} règles"))
                else:
                    acl_rows.append((str(acl), "-"))

        self.acl_table.setRowCount(len(acl_rows))

        if not acl_rows:
            return

        for row, (name, count) in enumerate(acl_rows):
            self.acl_table.setItem(row, 0, QTableWidgetItem(name))
            self.acl_table.setItem(row, 1, QTableWidgetItem(count))

    def input_group(self, label, widget):
        box = QFrame()
        box.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)

        layout = QVBoxLayout(box)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(6)

        lbl = QLabel(label)
        lbl.setObjectName("inputLabel")

        widget.setMinimumHeight(40)
        widget.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)

        layout.addWidget(lbl)
        layout.addWidget(widget)
        return box

    def get_current_report(self):
        if isinstance(getattr(self, "app_state", None), dict):
            report = self.app_state.get("report")
            if report:
                return self.normalize_report(report)
        return self.normalize_report(self.report)

    def build_policy(self):
        port_text = self.port.text().strip()

        try:
            port = int(port_text) if port_text else 0
        except ValueError:
            port = 0

        acl_name = self.acl_name.text().strip()
        if not acl_name:
            acl_name = (
                f"{self.action.currentText().upper()}_"
                f"{self.source_zone.currentText()}_TO_"
                f"{self.destination_zone.currentText()}"
            )
            self.acl_name.setText(acl_name)

        return {
            "operation": "create",
            "acl_name": acl_name,
            "source_site": "SITE-1",
            "destination_site": "SITE-1",
            "source_zone": self.source_zone.currentText(),
            "destination_zone": self.destination_zone.currentText(),
            "protocol": self.protocol.currentText(),
            "port": port,
            "action": self.action.currentText()
        }

    def analyze_policy(self):
        if not self.api_client:
            self.analysis_label.setText("Erreur : ApiClient non connecté.")
            return

        report = self.get_current_report()

        if not report:
            self.analysis_label.setText("Erreur : aucun report réel chargé. Lance d'abord la découverte réseau.")
            self.cli_preview.setText("Aucune configuration générée : report manquant.")
            return

        if self.source_zone.currentText() == "AUCUNE_ZONE" or self.destination_zone.currentText() == "AUCUNE_ZONE":
            self.analysis_label.setText("Erreur : aucune zone réelle trouvée dans le report de découverte.")
            self.cli_preview.setText("Aucune configuration générée : zones manquantes.")
            return

        policy = self.build_policy()
        self.current_policy = policy

        self.analysis_label.setText("Analyse ACL en cours via /generate-acl...")
        self.cli_preview.setText("Attente génération CLI...")

        result = self.api_client.process_acl(
            report=report,
            policies=[policy]
        )

        if not result.get("success"):
            self.analysis_label.setText(
                "Erreur /generate-acl :\n" + result.get("error", "Erreur inconnue")
            )
            return

        data = result.get("data", {})

        if data.get("errors"):
            self.analysis_label.setText("Erreur ACL :\n" + str(data.get("errors")))
            return

        self.acl_plan = self.extract_acl_plan(data, fallback_policy=policy)

        if not self.acl_plan:
            self.analysis_label.setText("Aucun plan ACL généré par /generate-acl.")
            return

        self.save_to_state(report=report, policy=policy)
        self.display_acl_plan()
        self.generate_commands_from_backend()

    def extract_acl_plan(self, data, fallback_policy=None):
        acl_result = data.get("acl_result")

        if isinstance(acl_result, dict):
            for key in ["created", "updated", "deleted"]:
                value = acl_result.get(key)
                if isinstance(value, list) and value:
                    return value[0]

        for key in ["created", "updated", "deleted"]:
            value = data.get(key)
            if isinstance(value, list) and value:
                return value[0]

        if isinstance(data.get("acl_plan"), dict):
            return data.get("acl_plan")

        if isinstance(data.get("plan"), dict):
            return data.get("plan")

        if fallback_policy:
            return {
                "operation": fallback_policy.get("operation", "create"),
                "device": "-",
                "acl_name": fallback_policy.get("acl_name"),
                "rules": [{
                    "action": fallback_policy.get("action"),
                    "protocol": fallback_policy.get("protocol"),
                    "source": fallback_policy.get("source_zone"),
                    "destination": fallback_policy.get("destination_zone"),
                    "port": fallback_policy.get("port")
                }],
                "apply_interface": "-",
                "apply_direction": "-",
                "reason": "Plan reçu depuis backend"
            }

        return None

    def generate_commands_from_backend(self):
        if not self.api_client:
            self.cli_preview.setText("Erreur : ApiClient non connecté.")
            return

        report = self.get_current_report()
        policy = self.current_policy or self.build_policy()

        self.cli_preview.setText("Génération des commandes Cisco via /render-acl...")

        result = self.api_client.generate_acl_commands(
            report=report,
            policies=[policy]
        )

        if not result.get("success"):
            self.cli_preview.setText(
                "Erreur /render-acl :\n" + result.get("error", "Erreur inconnue")
            )
            return

        data = result.get("data", {})
        config = self.extract_config(data)

        self.generated_config = config
        self.cli_preview.setText(config)

        self.save_to_state(report=report, policy=policy)

    def extract_config(self, data):
        rendered_configs = data.get("rendered_configs")

        if isinstance(rendered_configs, dict) and rendered_configs:
            configs = []

            for device, config in rendered_configs.items():
                configs.append(str(config))

            return "\n\n".join(configs).strip()

        config = (
            data.get("config")
            or data.get("generated_config")
            or data.get("commands")
            or data.get("cli")
            or data.get("rendered_config")
            or data.get("acl_config")
        )

        if isinstance(config, list):
            return "\n".join(str(line) for line in config)

        if config:
            return str(config)

        return "Aucune configuration Cisco générée."

    def display_acl_plan(self):
        device = self.acl_plan.get("device", "-")
        acl_name = self.acl_plan.get("acl_name", "-")
        interface = self.acl_plan.get("apply_interface") or "-"
        direction = self.acl_plan.get("apply_direction") or "-"
        reason = self.acl_plan.get("reason", "-")

        rules = self.acl_plan.get("rules", [])
        rule = rules[0] if rules else {}

        self.analysis_label.setText(
            f"Emplacement recommandé : {device}\n"
            f"Interface : {interface}\n"
            f"Direction : {str(direction).upper()}\n"
            f"Raison : {reason}"
        )

        self.summary.setText(
            f"Action : {str(rule.get('action', '-')).upper()}\n"
            f"Équipement : {device}\n"
            f"Interface : {interface}\n"
            f"ACL Name : {acl_name}\n"
            f"Direction : {str(direction).upper()}\n"
            f"Raison : {reason}"
        )

        self.draw_topology(
            self.source_zone.currentText(),
            self.destination_zone.currentText(),
            device
        )

    def save_to_state(self, report=None, policy=None):
        if not isinstance(getattr(self, "app_state", None), dict):
            return

        self.app_state["report"] = report or self.get_current_report()
        self.app_state["acl_policy"] = policy or self.current_policy
        self.app_state["acl_plan"] = self.acl_plan
        self.app_state["generated_config"] = self.generated_config
        self.app_state["user_intent"] = self.description.toPlainText().strip()

    def add_to_plan(self):
        if not self.acl_plan:
            self.analyze_policy()

        if self.acl_plan:
            self.plan.append(self.acl_plan)
            self.save_to_state()
            self.btn_validate.setText("Ajouté au plan ✓")

    def go_to_ai_validation(self):
        if not self.acl_plan:
            self.analyze_policy()

        if not self.generated_config:
            self.generate_commands_from_backend()

        self.save_to_state()

        if hasattr(self, "ai_page") and hasattr(self, "parent_stack"):
            if hasattr(self.ai_page, "load_acl_validation_data"):
                self.ai_page.load_acl_validation_data(
                    acl_plan=self.acl_plan,
                    generated_config=self.generated_config
                )
            self.parent_stack.setCurrentWidget(self.ai_page)

    def draw_topology(self, src, dst, device):
        self.scene.clear()
        self.scene.setSceneRect(0, 0, 760, 330)

        pen_blue = QPen(QColor("#2F80ED"), 2)
        pen_green = QPen(QColor("#6FCF97"), 2)
        pen_red = QPen(QColor("#EB5757"), 3)

        self.node("INTERNET", 335, 20, "#1B3A5F", "ellipse")
        self.node("EDGE-RTR", 335, 90, "#1D5FA7", "ellipse")
        self.node(device or "ACL-POINT", 320, 165, "#9B1C31", "rect")

        self.node(src, 130, 250, "#123D2A", "rect")
        self.node(dst, 520, 250, "#3A2A10", "rect")

        self.scene.addLine(380, 66, 380, 90, pen_blue)
        self.scene.addLine(380, 136, 380, 165, pen_blue)
        self.scene.addLine(325, 220, 190, 250, pen_green)
        self.scene.addLine(435, 220, 580, 250, pen_blue)
        self.scene.addLine(300, 195, 460, 195, pen_red)

        self.graph.fitInView(self.scene.sceneRect(), Qt.KeepAspectRatio)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        if hasattr(self, "graph") and hasattr(self, "scene"):
            self.graph.fitInView(self.scene.sceneRect(), Qt.KeepAspectRatio)

    def node(self, text, x, y, color, shape="rect"):
        if shape == "ellipse":
            item = QGraphicsEllipseItem(x, y, 110, 48)
        else:
            item = QGraphicsRectItem(x, y, 140, 62)

        item.setBrush(QBrush(QColor(color)))
        item.setPen(QPen(QColor("#2F80ED"), 1))
        self.scene.addItem(item)

        label = self.scene.addText(str(text))
        label.setDefaultTextColor(QColor("#EAF2FF"))
        label.setFont(QFont("Segoe UI", 9, QFont.Bold))
        label.setPos(x + 14, y + 18)

        return item

    def apply_style(self):
        self.setStyleSheet("""
            QWidget {
                background-color: #071426;
                color: #EAF2FF;
                font-family: Segoe UI;
                font-size: 13px;
            }

            QScrollArea#pageScroll {
                background-color: #071426;
                border: none;
            }

            QLabel#pageTitle {
                font-size: 28px;
                font-weight: bold;
                color: #FFFFFF;
            }

            QLabel#subtitle {
                color: #8EA4C8;
                font-size: 13px;
            }

            QLabel#cardTitle {
                color: #FFFFFF;
                font-size: 15px;
                font-weight: bold;
            }

            QLabel#inputLabel {
                color: #9BB0D1;
                font-size: 12px;
            }

            QFrame#card {
                background-color: #071426;
                border: 1px solid #1E4F80;
                border-radius: 16px;
            }

            QFrame#card:hover {
                border: 1px solid #3BB3FF;
            }

            QLineEdit, QComboBox, QTextEdit {
                background-color: #10233F;
                border: 1px solid #1C3D68;
                border-radius: 10px;
                padding: 9px;
                color: #EAF2FF;
            }

            QLineEdit:focus, QComboBox:focus, QTextEdit:focus {
                border: 1px solid #2F80ED;
            }

            QPushButton#primaryBtn {
                background-color: #1266F1;
                color: white;
                border: none;
                border-radius: 12px;
                padding: 11px 18px;
                font-weight: bold;
            }

            QPushButton#primaryBtn:hover {
                background-color: #2F80ED;
            }

            QPushButton#secondaryBtn {
                background-color: #5B2FEA;
                color: white;
                border: none;
                border-radius: 12px;
                padding: 11px 18px;
                font-weight: bold;
            }

            QPushButton#secondaryBtn:hover {
                background-color: #7046FF;
            }

            QTextEdit#cliBox {
                background-color: #10233F;
                border: 1px solid #3B82F6;
                border-radius: 12px;
                color: #B6FCD5;
                font-family: Consolas;
                font-size: 13px;
            }

            QGraphicsView#graphView {
                background-color: #10233F;
                border: 1px solid #1E4F80;
                border-radius: 14px;
            }

            QLabel#analysisText, QLabel#summaryText {
                background-color: #123052;
                border: 1px solid #3B82F6;
                border-radius: 12px;
                padding: 12px;
                color: #DCEBFF;
            }

            QTableWidget {
                background-color: #123052;
                border: 1px solid #1E4F80;
                border-radius: 10px;
                gridline-color: #1E4F80;
                color: #EAF2FF;
            }

            QHeaderView::section {
                background-color: #123052;
                color: #9BB0D1;
                padding: 8px;
                border: none;
            }
        """)