from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QFrame, QLineEdit, QComboBox, QTextEdit, QTableWidget,
    QTableWidgetItem, QMessageBox, QGraphicsView, QGraphicsScene,
    QGraphicsEllipseItem, QGraphicsRectItem, QSizePolicy, QScrollArea
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
        self.report = self.enrich_report_with_zones(self.normalize_report(report)) if report else {}
        self.app_state = {"report": self.report}

        self.plan = []
        self.current_policy = None
        self.acl_plan = None
        self.generated_config = None

        self.setMinimumSize(1000, 700)

        self.setup_ui()
        self.apply_style()
        self.load_report_data(self.report)

    def normalize_report(self, report):
        if not isinstance(report, dict):
            return {}

        if "data" in report and isinstance(report["data"], dict):
            report = report["data"]

        if "report" in report and isinstance(report["report"], dict):
            report = report["report"]

        return report

    def enrich_report_with_zones(self, report: dict):
        if not isinstance(report, dict):
            return {}

        report.setdefault("network_context", {})
        network_context = report["network_context"]

        existing_zones = network_context.get("zones", [])
        if isinstance(existing_zones, list) and existing_zones:
            return report

        zones = []
        seen = set()

        vlans = network_context.get("vlans", []) or []
        svis = network_context.get("svis", []) or []

        inventory_devices = report.get("inventory", {}).get("devices", []) or []

        for device in inventory_devices:
            hostname = device.get("hostname")

            for vlan in device.get("vlans", []) or []:
                item = dict(vlan)
                item.setdefault("device", hostname)
                vlans.append(item)

            for svi in device.get("svis", []) or []:
                item = dict(svi)
                item.setdefault("device", hostname)
                svis.append(item)

        def get_vlan_id(item):
            return (
                item.get("vlan_id")
                or item.get("id")
                or item.get("vlan")
                or item.get("number")
            )

        def get_vlan_name(item, vlan_id):
            return (
                item.get("zone_name")
                or item.get("vlan_name")
                or item.get("name")
                or item.get("departement")
                or item.get("department")
                or f"VLAN{vlan_id}"
            )

        def find_svi_for_vlan(vlan_id):
            for svi in svis:
                svi_vlan_id = get_vlan_id(svi)

                if str(svi_vlan_id) == str(vlan_id):
                    return svi

                interface = str(
                    svi.get("interface")
                    or svi.get("name")
                    or svi.get("svi")
                    or ""
                ).lower()

                if vlan_id and interface == f"vlan{vlan_id}".lower():
                    return svi

            return None

        for vlan in vlans:
            vlan_id = get_vlan_id(vlan)
            if not vlan_id:
                continue

            name = str(get_vlan_name(vlan, vlan_id)).upper()
            key = str(name)

            if key in seen:
                continue

            svi = find_svi_for_vlan(vlan_id)

            subnet = (
                vlan.get("subnet")
                or vlan.get("network")
                or (svi or {}).get("subnet")
                or (svi or {}).get("network")
            )

            gateway = (
                vlan.get("gateway")
                or (svi or {}).get("gateway")
                or (svi or {}).get("ip")
                or (svi or {}).get("ip_address")
            )

            gateway_device = (
                vlan.get("device")
                or (svi or {}).get("device")
                or (svi or {}).get("hostname")
            )

            zones.append({
                "zone_name": name,
                "vlan_id": vlan_id,
                "subnet": subnet or gateway,
                "gateway": gateway,
                "gateway_device": gateway_device,
                "gateway_interface": f"Vlan{vlan_id}"
            })

            seen.add(key)

        if not zones:
            for svi in svis:
                vlan_id = get_vlan_id(svi)

                interface = str(
                    svi.get("interface")
                    or svi.get("name")
                    or svi.get("svi")
                    or ""
                )

                if not vlan_id and interface.lower().startswith("vlan"):
                    vlan_id = interface.lower().replace("vlan", "").strip()

                if not vlan_id:
                    continue

                name = str(
                    svi.get("zone_name")
                    or svi.get("vlan_name")
                    or svi.get("name")
                    or f"VLAN{vlan_id}"
                ).upper()

                if name in seen:
                    continue

                zones.append({
                    "zone_name": name,
                    "vlan_id": vlan_id,
                    "subnet": svi.get("subnet") or svi.get("network") or svi.get("ip") or svi.get("ip_address"),
                    "gateway": svi.get("gateway") or svi.get("ip") or svi.get("ip_address"),
                    "gateway_device": svi.get("device") or svi.get("hostname"),
                    "gateway_interface": f"Vlan{vlan_id}"
                })

                seen.add(name)

        network_context["zones"] = zones
        return report

    def set_report(self, report: dict):
        self.report = self.enrich_report_with_zones(self.normalize_report(report))
        self.app_state["report"] = self.report
        self.load_report_data(self.report)

    def get_current_report(self):
        report = self.app_state.get("report") or self.report
        return self.enrich_report_with_zones(self.normalize_report(report))

    def extract_zones(self, report: dict):
        report = self.enrich_report_with_zones(report)
        zones = []

        for item in report.get("network_context", {}).get("zones", []):
            name = item.get("zone_name") or item.get("name")
            if name and str(name) not in zones:
                zones.append(str(name))

        return zones

    def load_report_data(self, report: dict):
        report = self.enrich_report_with_zones(self.normalize_report(report))
        self.report = report
        self.app_state["report"] = report

        zones = self.extract_zones(report)

        self.source_zone.clear()
        self.destination_zone.clear()

        if zones:
            source_items = ["ANY"] + zones
            destination_items = ["ANY"] + zones

            self.source_zone.addItems(source_items)
            self.destination_zone.addItems(destination_items)

            if len(source_items) >= 2:
                self.source_zone.setCurrentIndex(1)
                self.destination_zone.setCurrentIndex(1)
        else:
            self.source_zone.addItem("ANY")
            self.source_zone.addItem("AUCUNE_ZONE")
            self.destination_zone.addItem("ANY")
            self.destination_zone.addItem("AUCUNE_ZONE")

        self.populate_existing_acls(report)

    def setup_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setObjectName("pageScroll")
        scroll.setFrameShape(QFrame.NoFrame)

        container = QWidget()
        main = QVBoxLayout(container)
        main.setContentsMargins(24, 20, 24, 20)
        main.setSpacing(18)

        header = QHBoxLayout()

        title_box = QVBoxLayout()
        title = QLabel("ACL Intelligent Engine")
        title.setObjectName("pageTitle")

        subtitle = QLabel("Créer, analyser et générer automatiquement des ACL selon les zones réelles du report.")
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

        self.acl_name = QLineEdit()
        self.acl_name.setPlaceholderText("Ex: DENY_VLAN1_TO_VLAN50")

        self.source_zone = QComboBox()
        self.destination_zone = QComboBox()

        self.action = QComboBox()
        self.action.addItems(["deny", "permit"])

        self.protocol = QComboBox()
        self.protocol.addItems(["ip", "tcp", "udp", "icmp", "any"])

        self.port = QLineEdit()
        self.port.setPlaceholderText("Ex: 443")

        self.description = QTextEdit()
        self.description.setPlaceholderText("Ex: Interdire VLAN1 vers VLAN50")
        self.description.setMinimumHeight(90)
        self.description.setMaximumHeight(130)

        policy_card.layout.addWidget(QLabel("Nom ACL"))

        policy_card.layout.addWidget(self.acl_name)

        row1 = QHBoxLayout()
        row1.addWidget(self.input_group("Zone source", self.source_zone))
        row1.addWidget(self.input_group("Zone destination", self.destination_zone))
        policy_card.layout.addLayout(row1)

        row2 = QHBoxLayout()
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
        self.acl_table.verticalHeader().setVisible(False)
        self.acl_table.horizontalHeader().setStretchLastSection(True)
        self.acl_table.setMinimumHeight(180)

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
        self.graph.setRenderHint(QPainter.Antialiasing)

        analysis_card.layout.addWidget(self.analysis_label)
        analysis_card.layout.addWidget(self.graph, 1)
        right.addWidget(analysis_card, 5)

        cli_card = Card("4. Règle Cisco proposée")

        self.cli_preview = QTextEdit()
        self.cli_preview.setReadOnly(True)
        self.cli_preview.setObjectName("cliBox")
        self.cli_preview.setMinimumHeight(150)
        self.cli_preview.setText("! La commande Cisco sera générée ici après analyse.")

        cli_card.layout.addWidget(self.cli_preview)
        right.addWidget(cli_card, 2)

        summary_card = Card("5. Résumé du plan d’action")

        self.summary = QLabel("Action : -\nÉquipement : -\nInterface : -\nDirection : -\nRaison : -")
        self.summary.setObjectName("summaryText")
        self.summary.setWordWrap(True)

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

    def populate_existing_acls(self, report: dict):
        acl_rows = []

        for device in report.get("inventory", {}).get("devices", []):
            existing_acls = device.get("existing_acls", device.get("acls", []))

            if isinstance(existing_acls, dict):
                existing_acls = [existing_acls]

            for acl in existing_acls or []:
                if isinstance(acl, dict):
                    name = acl.get("acl_name") or acl.get("name") or "ACL"
                    rules = acl.get("rules", [])
                    count = len(rules) if isinstance(rules, list) else 0
                    acl_rows.append((str(name), f"{count} règles"))
                else:
                    acl_rows.append((str(acl), "-"))

        self.acl_table.setRowCount(len(acl_rows))

        for row, (name, count) in enumerate(acl_rows):
            self.acl_table.setItem(row, 0, QTableWidgetItem(name))
            self.acl_table.setItem(row, 1, QTableWidgetItem(count))

    def input_group(self, label, widget):
        box = QFrame()
        layout = QVBoxLayout(box)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(6)

        lbl = QLabel(label)
        lbl.setObjectName("inputLabel")

        widget.setMinimumHeight(40)

        layout.addWidget(lbl)
        layout.addWidget(widget)

        return box

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
        zones = self.extract_zones(report)

        if not report:
            self.analysis_label.setText("Erreur : aucun report réel chargé. Lance d'abord la découverte réseau.")
            self.cli_preview.setText("Aucune configuration générée : report manquant.")
            return

        if not zones:
            self.analysis_label.setText("Erreur : aucune zone trouvée dans le report.")
            self.cli_preview.setText("Aucune configuration générée : zones manquantes.")
            return

        if self.source_zone.currentText() == self.destination_zone.currentText():
            self.analysis_label.setText("Erreur : la zone source et la zone destination doivent être différentes.")
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
            return "\n\n".join(str(config) for config in rendered_configs.values()).strip()

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
        """
        Graphe ACL dynamique :
        - affiche uniquement les équipements réellement présents dans le report de découverte ;
        - n'affiche plus INTERNET ou EDGE-RTR en dur ;
        - affiche les VLANs/zones source et destination concernés par l'ACL ;
        - dessine les liens réels si le report contient topology.links.
        """
        self.scene.clear()
        self.scene.setSceneRect(0, 0, 900, 420)

        pen_link = QPen(QColor("#6FCF97"), 2)
        pen_acl = QPen(QColor("#EB5757"), 3)

        report = self.get_current_report()

        topology = report.get("topology", {}) if isinstance(report, dict) else {}
        devices = topology.get("devices", []) or []
        links = topology.get("links", []) or []

        # Construire la liste des équipements réels découverts.
        device_names = []
        for d in devices:
            if not isinstance(d, dict):
                continue

            name = (
                d.get("hostname")
                or d.get("name")
                or d.get("ip")
                or d.get("ip_address")
            )

            if name and str(name) not in device_names:
                device_names.append(str(name))

        # Ajouter l'équipement recommandé par le backend si absent du report.
        if device and str(device) not in device_names and str(device) != "-":
            device_names.insert(0, str(device))

        # Sécurité : si aucun équipement n'est trouvé, afficher un seul nœud générique.
        if not device_names:
            device_names = [str(device or "UNKNOWN_DEVICE")]

        positions = {}

        center_x = 380
        top_y = 60
        spacing_x = 190

        # Afficher les équipements découverts dynamiquement.
        for i, name in enumerate(device_names):
            x = center_x + (i - (len(device_names) - 1) / 2) * spacing_x
            y = top_y

            is_acl_device = device and str(name) == str(device)
            color = "#9B1C31" if is_acl_device else "#1D5FA7"

            self.node(name, x, y, color, "rect")
            positions[name] = (x, y)

        # Dessiner les liens physiques/logiques si présents dans le report.
        for link in links:
            if not isinstance(link, dict):
                continue

            src_dev = (
                link.get("source")
                or link.get("source_hostname")
                or link.get("source_device")
                or link.get("local_device")
                or link.get("local_hostname")
            )

            dst_dev = (
                link.get("target")
                or link.get("destination")
                or link.get("target_hostname")
                or link.get("target_device")
                or link.get("remote_device")
                or link.get("remote_hostname")
            )

            src_dev = str(src_dev) if src_dev else ""
            dst_dev = str(dst_dev) if dst_dev else ""

            if src_dev in positions and dst_dev in positions:
                x1, y1 = positions[src_dev]
                x2, y2 = positions[dst_dev]
                self.scene.addLine(x1 + 70, y1 + 62, x2 + 70, y2 + 62, pen_link)

        # Choisir l'équipement où l'ACL sera appliquée.
        acl_device = str(device) if device and str(device) in positions else device_names[0]
        acl_x, acl_y = positions.get(acl_device, (center_x, top_y))

        # Afficher les zones/VLANs concernés par l'ACL.
        # Correction : empêcher les rectangles source/destination de sortir de la scène.
        vlan_y = 280
        scene_width = 900
        node_width = 140
        margin = 40

        src_x = max(margin, acl_x - 220)
        dst_x = min(scene_width - node_width - margin, acl_x + 220)

        # Si les deux rectangles sont trop proches, on les repositionne proprement.
        if abs(dst_x - src_x) < 220:
            src_x = margin
            dst_x = scene_width - node_width - margin

        self.node(src, src_x, vlan_y, "#123D2A", "rect")
        self.node(dst, dst_x, vlan_y, "#3A2A10", "rect")

        # Liens logiques entre l'équipement ACL et les zones source/destination.
        self.scene.addLine(acl_x + 30, acl_y + 62, src_x + 70, vlan_y, pen_link)
        self.scene.addLine(acl_x + 110, acl_y + 62, dst_x + 70, vlan_y, pen_link)

        # Ligne rouge représentant l'ACL appliquée sur l'équipement recommandé.
        self.scene.addLine(acl_x - 20, acl_y + 30, acl_x + 160, acl_y + 30, pen_acl)

        acl_label = self.scene.addText("ACL")
        acl_label.setDefaultTextColor(QColor("#FFD700"))
        acl_label.setFont(QFont("Segoe UI", 9, QFont.Bold))
        acl_label.setPos(acl_x + 65, acl_y - 22)

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

            QLineEdit, QComboBox, QTextEdit {
                background-color: #10233F;
                border: 1px solid #1C3D68;
                border-radius: 10px;
                padding: 9px;
                color: #EAF2FF;
            }

            QPushButton#primaryBtn {
                background-color: #1266F1;
                color: white;
                border: none;
                border-radius: 12px;
                padding: 11px 18px;
                font-weight: bold;
            }

            QPushButton#secondaryBtn {
                background-color: #5B2FEA;
                color: white;
                border: none;
                border-radius: 12px;
                padding: 11px 18px;
                font-weight: bold;
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