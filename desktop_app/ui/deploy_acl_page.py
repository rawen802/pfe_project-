from datetime import datetime

from PySide6.QtCore import Qt, QRectF
from PySide6.QtWidgets import (
    QWidget, QLabel, QPushButton, QTextEdit, QVBoxLayout, QHBoxLayout,
    QFrame, QLineEdit, QComboBox, QCheckBox, QSpinBox, QTableWidget,
    QTableWidgetItem, QMessageBox, QSizePolicy, QScrollArea, QFileDialog,
    QGraphicsView, QGraphicsScene, QGraphicsRectItem, QGraphicsEllipseItem,
    QGraphicsTextItem, QGraphicsLineItem
)
from PySide6.QtGui import QPen, QBrush, QColor, QFont


class DeployAclPage(QWidget):
    """
    Page PRO de déploiement ACL.
    Workflow :
    AI Validation -> load_deploy_data() -> DeployAclPage -> /deploy-acl-configs
    """

    def __init__(self, api_client=None, user_data=None):
        super().__init__()

        self.api_client = api_client
        self.user_data = user_data or {}

        self.acl_plan = {}
        self.generated_config = ""
        self.report = {}
        self.available_devices = []

        self.setMinimumSize(900, 620)

        self.setup_ui()
        self.apply_style()
        self.reset_page()

    # ======================================================
    # UI
    # ======================================================

    def setup_ui(self):
        page_root = QVBoxLayout(self)
        page_root.setContentsMargins(0, 0, 0, 0)
        page_root.setSpacing(0)

        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)
        self.scroll.setFrameShape(QFrame.NoFrame)
        self.scroll.setObjectName("pageScroll")
        self.scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)

        container = QWidget()
        container.setObjectName("deployContainer")

        root = QVBoxLayout(container)
        root.setContentsMargins(18, 14, 18, 14)
        root.setSpacing(14)

        root.addLayout(self.create_header())
        root.addLayout(self.create_steps())

        content = QHBoxLayout()
        content.setSpacing(12)

        self.config_card = self.create_config_card()
        self.target_card = self.create_target_card()
        self.logs_card = self.create_logs_card()

        content.addWidget(self.config_card, 34)
        content.addWidget(self.target_card, 30)
        content.addWidget(self.logs_card, 36)

        root.addLayout(content, 1)

        # Carte dynamique : topologie détectée + emplacement ACL recommandé
        self.ai_topology_card = self.create_ai_topology_card()
        root.addWidget(self.ai_topology_card)

        bottom = QHBoxLayout()
        bottom.setSpacing(12)
        bottom.addWidget(self.create_history_card(), 2)
        bottom.addWidget(self.create_quick_actions_card(), 1)

        root.addLayout(bottom)

        self.scroll.setWidget(container)
        page_root.addWidget(self.scroll)

    def create_header(self):
        layout = QHBoxLayout()

        left = QVBoxLayout()

        title = QLabel("🚀 ACL Deployment Center")
        title.setObjectName("pageTitle")

        subtitle = QLabel("Déployer la configuration ACL générée sur vos équipements Cisco")
        subtitle.setObjectName("subtitle")

        left.addWidget(title)
        left.addWidget(subtitle)

        self.agent_status = QLabel("● Agent Active")
        self.agent_status.setObjectName("agentBadge")

        username = self.user_data.get("username", "Utilisateur")
        role = self.user_data.get("role", self.user_data.get("role_name", "Connecté"))

        avatar = QLabel(username[:1].upper())
        avatar.setFixedSize(44, 44)
        avatar.setAlignment(Qt.AlignCenter)
        avatar.setObjectName("avatar")

        user_info = QLabel(f"{username}\n{role}")
        user_info.setObjectName("userInfo")

        layout.addLayout(left)
        layout.addStretch()
        layout.addWidget(self.agent_status)
        layout.addSpacing(10)
        layout.addWidget(QLabel("🔔"))
        layout.addSpacing(10)
        layout.addWidget(avatar)
        layout.addWidget(user_info)

        return layout

    def create_steps(self):
        layout = QHBoxLayout()
        layout.setSpacing(12)

        steps = [
            "✓ Génération ACL",
            "✓ Validation AI",
            "✓ Aperçu Configuration",
            "4 Déploiement",
            "5 Résultat"
        ]

        for i, step in enumerate(steps):
            lbl = QLabel(step)
            lbl.setAlignment(Qt.AlignCenter)
            lbl.setObjectName("stepActive" if i < 4 else "stepIdle")
            lbl.setMinimumHeight(42)
            layout.addWidget(lbl)

            if i < len(steps) - 1:
                line = QLabel("────")
                line.setObjectName("stepLine")
                line.setAlignment(Qt.AlignCenter)
                layout.addWidget(line)

        return layout

    def create_config_card(self):
        card = self.card("📄 1. Configuration à déployer")

        self.config_file_combo = QComboBox()
        self.config_file_combo.addItem("Aucune configuration chargée")

        file_row = QHBoxLayout()
        file_row.addWidget(self.config_file_combo, 1)

        self.btn_copy_name = QPushButton("⧉")
        self.btn_copy_name.setObjectName("smallBtn")
        self.btn_copy_name.clicked.connect(self.copy_config)
        file_row.addWidget(self.btn_copy_name)

        self.config_preview = QTextEdit()
        self.config_preview.setReadOnly(True)
        self.config_preview.setObjectName("cliBox")
        self.config_preview.setMinimumHeight(220)
        self.config_preview.setMaximumHeight(320)

        actions = QHBoxLayout()

        self.btn_copy = QPushButton("⧉ Copier")
        self.btn_copy.setObjectName("darkBtn")
        self.btn_copy.clicked.connect(self.copy_config)

        self.btn_export = QPushButton("⇩ Exporter")
        self.btn_export.setObjectName("darkBtn")
        self.btn_export.clicked.connect(self.export_config)

        self.btn_download = QPushButton("⬇ Télécharger")
        self.btn_download.setObjectName("primaryPurple")
        self.btn_download.clicked.connect(self.export_config)

        actions.addWidget(self.btn_copy)
        actions.addWidget(self.btn_export)
        actions.addWidget(self.btn_download)

        info = self.card("Informations de déploiement", compact=True)
        self.info_lines = QLabel(
            "Nombre de lignes : -\n"
            "Type de configuration : ACL\n"
            "Date de génération : -\n"
            "Généré par : -\n"
            "Hash : -"
        )
        self.info_lines.setObjectName("infoText")
        info.layout().addWidget(self.info_lines)

        card.layout().addWidget(QLabel("Fichier de configuration généré"))
        card.layout().addLayout(file_row)
        card.layout().addWidget(QLabel("Aperçu de la configuration Cisco"))
        card.layout().addWidget(self.config_preview, 1)
        card.layout().addLayout(actions)
        card.layout().addWidget(info)

        return card

    def create_target_card(self):
        """
        Carte cible simplifiée pour correspondre exactement à l'API Swagger.

        L'endpoint /deploy-acl-configs attend seulement :
        {
            "devices": [
                {
                    "hostname": "string",
                    "ip": "string",
                    "username": "string",
                    "password": "string",
                    "enable_password": "string"
                }
            ]
        }
        """
        card = self.card("🗄️ 2. Cible de déploiement")

        self.device_combo = QComboBox()
        self.device_combo.addItem("Sélectionner un équipement")
        self.device_combo.currentIndexChanged.connect(self.on_device_selected)

        self.btn_add_device = QPushButton("+ Saisie manuelle")
        self.btn_add_device.setObjectName("darkBtn")
        self.btn_add_device.clicked.connect(self.clear_device_fields)

        row = QHBoxLayout()
        row.addWidget(self.device_combo, 1)
        row.addWidget(self.btn_add_device)

        self.hostname_input = QLineEdit()
        self.ip_input = QLineEdit()
        self.username_input = QLineEdit()
        self.password_input = QLineEdit()
        self.enable_password_input = QLineEdit()

        self.hostname_input.setPlaceholderText("Ex: FW-CORE-01")
        self.ip_input.setPlaceholderText("Ex: 192.168.1.254")
        self.username_input.setPlaceholderText("Ex: admin")
        self.password_input.setPlaceholderText("Mot de passe SSH")
        self.enable_password_input.setPlaceholderText("Enable password / secret")

        self.password_input.setEchoMode(QLineEdit.Password)
        self.enable_password_input.setEchoMode(QLineEdit.Password)

        form = QVBoxLayout()
        form.setSpacing(10)

        form.addWidget(QLabel("Sélectionner l’équipement cible"))
        form.addLayout(row)
        form.addSpacing(6)
        form.addWidget(QLabel("Informations envoyées au backend"))

        form.addLayout(self.input_row("Hostname", self.hostname_input))
        form.addLayout(self.input_row("IP Address", self.ip_input))
        form.addLayout(self.input_row("Username", self.username_input))
        form.addLayout(self.input_row("Password", self.password_input))
        form.addLayout(self.input_row("Enable Password", self.enable_password_input))

        self.deploy_btn = QPushButton("🚀 Déployer réellement")
        self.deploy_btn.setObjectName("deployBtn")
        self.deploy_btn.setMinimumHeight(48)
        self.deploy_btn.clicked.connect(self.deploy_acl_config)

        warning = QLabel(
            "⚠ Déploiement réel : vérifiez l’IP, le username, le password et le enable password avant de lancer."
        )
        warning.setObjectName("warningText")
        warning.setWordWrap(True)

        api_info = QLabel(
            "Payload API : hostname, ip, username, password, enable_password"
        )
        api_info.setObjectName("infoText")
        api_info.setWordWrap(True)

        form.addSpacing(8)
        form.addWidget(api_info)
        form.addStretch()
        form.addWidget(self.deploy_btn)
        form.addWidget(warning)

        card.layout().addLayout(form)

        return card

    def create_logs_card(self):
        card = self.card("🖥️ 3. Logs de déploiement")

        top = QHBoxLayout()

        self.current_status = QLabel("● Prêt pour le déploiement")
        self.current_status.setObjectName("statusReady")

        self.btn_clear_logs = QPushButton("Vider")
        self.btn_clear_logs.setObjectName("smallBtn")
        self.btn_clear_logs.clicked.connect(self.clear_logs)

        top.addWidget(QLabel("Statut actuel"))
        top.addStretch()
        top.addWidget(self.current_status)
        top.addWidget(self.btn_clear_logs)

        self.logs_box = QTextEdit()
        self.logs_box.setReadOnly(True)
        self.logs_box.setObjectName("logsBox")
        self.logs_box.setMinimumHeight(220)
        self.logs_box.setMaximumHeight(330)

        summary = self.card("Résumé du déploiement", compact=True)

        summary_row = QHBoxLayout()

        self.summary_label = QLabel(
            "Statut : -\n"
            "Durée totale : -\n"
            "Lignes envoyées : -\n"
            "Erreurs : -\n"
            "Équipement : -\n"
            "Date : -"
        )
        self.summary_label.setObjectName("infoText")

        self.success_icon = QLabel("✓")
        self.success_icon.setAlignment(Qt.AlignCenter)
        self.success_icon.setObjectName("successIcon")

        summary_row.addWidget(self.summary_label, 1)
        summary_row.addWidget(self.success_icon)

        summary.layout().addLayout(summary_row)

        card.layout().addLayout(top)
        card.layout().addWidget(self.logs_box, 1)
        card.layout().addWidget(summary)

        return card

    def create_ai_topology_card(self):
        """
        Carte dynamique qui affiche :
        - l'emplacement ACL recommandé
        - les équipements détectés dans report["topology"]["devices"]
        - les liens détectés dans report["topology"]["links"]
        - les zones/VLAN détectées dans report["network_context"]["zones"]

        Cette partie remplace le schéma fixe INTERNET -> EDGE -> FW -> ADMIN/SERVERS.
        """
        card = self.card("🧠 3. Analyse intelligente & emplacement sélectionné")

        self.placement_label = QLabel(
            "Emplacement recommandé : -\n"
            "Interface : -\n"
            "Direction : -\n"
            "Raison : -"
        )
        self.placement_label.setObjectName("placementBox")
        self.placement_label.setWordWrap(True)
        self.placement_label.setMinimumHeight(80)

        self.topology_scene = QGraphicsScene()
        self.topology_view = QGraphicsView(self.topology_scene)
        self.topology_view.setObjectName("topologyView")
        self.topology_view.setMinimumHeight(330)
        self.topology_view.setRenderHint(self.topology_view.renderHints())
        self.topology_view.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.topology_view.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)

        card.layout().addWidget(self.placement_label)
        card.layout().addWidget(self.topology_view)

        return card

    def create_history_card(self):
        card = self.card("◉ Historique des déploiements récents")

        self.history_table = QTableWidget(0, 6)
        self.history_table.setHorizontalHeaderLabels(
            ["Date", "Équipement", "Fichier", "Statut", "Durée", "Lignes"]
        )
        self.history_table.verticalHeader().setVisible(False)
        self.history_table.horizontalHeader().setStretchLastSection(True)
        self.history_table.setMinimumHeight(95)
        self.history_table.setMaximumHeight(160)

        card.layout().addWidget(self.history_table)

        return card

    def create_quick_actions_card(self):
        card = self.card("◉ Actions rapides")

        row = QHBoxLayout()

        self.btn_history = QPushButton("◷ Voir historique")
        self.btn_history.setObjectName("darkBtn")
        self.btn_history.clicked.connect(self.show_history)

        self.btn_export_logs = QPushButton("⇩ Exporter logs")
        self.btn_export_logs.setObjectName("darkBtn")
        self.btn_export_logs.clicked.connect(self.export_logs)

        self.btn_new = QPushButton("+ Nouvelle configuration")
        self.btn_new.setObjectName("darkBtn")
        self.btn_new.clicked.connect(self.reset_page)

        row.addWidget(self.btn_history)
        row.addWidget(self.btn_export_logs)
        row.addWidget(self.btn_new)

        card.layout().addLayout(row)

        return card

    def input_row(self, label, widget):
        row = QHBoxLayout()
        lbl = QLabel(label)
        lbl.setMinimumWidth(110)
        lbl.setObjectName("inputLabel")

        widget.setMinimumHeight(34)
        row.addWidget(lbl)
        row.addWidget(widget, 1)

        return row

    def card(self, title=None, compact=False):
        frame = QFrame()
        frame.setObjectName("card")
        frame.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)

        layout = QVBoxLayout(frame)
        layout.setContentsMargins(14, 14, 14, 14)
        layout.setSpacing(10 if not compact else 6)

        if title:
            title_lbl = QLabel(title)
            title_lbl.setObjectName("cardTitle")
            layout.addWidget(title_lbl)

        return frame

    # ======================================================
    # DATA FLOW
    # ======================================================

    def load_deploy_data(self, acl_plan=None, generated_config=None, report=None):
        self.acl_plan = acl_plan or {}
        self.generated_config = self.normalize_config(generated_config)
        self.report = report or {}

        self.config_preview.setText(self.generated_config or "Aucune configuration chargée.")

        acl_name = self.acl_plan.get("acl_name", "acl_config")
        device = self.acl_plan.get("device") or self.acl_plan.get("affected_device") or ""

        self.config_file_combo.clear()
        self.config_file_combo.addItem(f"{acl_name}.cfg")

        self.hostname_input.setText(str(device))
        self.fill_device_info(device)

        line_count = len([line for line in self.generated_config.splitlines() if line.strip()])
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        user = self.user_data.get("username", "utilisateur")

        self.info_lines.setText(
            f"Nombre de lignes : {line_count}\n"
            f"Type de configuration : ACL Standard/Extended\n"
            f"Date de génération : {now}\n"
            f"Généré par : {user}\n"
            f"Hash : {abs(hash(self.generated_config))}"
        )

        self.add_log("INFO", "Configuration ACL chargée depuis AI Validation.")
        self.current_status.setText("● Prêt pour le déploiement")
        self.current_status.setObjectName("statusReady")
        self.refresh_status_style()
        self.update_ai_topology()

    def normalize_config(self, generated_config):
        if isinstance(generated_config, dict):
            return "\n\n".join(str(v) for v in generated_config.values())
        if isinstance(generated_config, list):
            return "\n".join(str(x) for x in generated_config)
        return str(generated_config or "")

    def fill_device_info(self, hostname):
        devices = []

        for d in self.report.get("inventory", {}).get("devices", []):
            if isinstance(d, dict):
                devices.append(d)

        for d in self.report.get("topology", {}).get("devices", []):
            if isinstance(d, dict):
                already = any(x.get("hostname") == d.get("hostname") for x in devices)
                if not already:
                    devices.append(d)

        self.available_devices = devices
        self.device_combo.blockSignals(True)
        self.device_combo.clear()

        found_index = -1

        for index, d in enumerate(devices):
            name = d.get("hostname", "")
            ip = d.get("ip", "")
            if name:
                self.device_combo.addItem(f"{name} ({ip})")
            if hostname and name == hostname:
                found_index = index

        if not devices:
            self.device_combo.addItem("Aucun device du report")
            self.device_combo.blockSignals(False)
            self.hostname_input.setText(str(hostname or ""))
            self.ip_input.clear()
            self.username_input.clear()
            self.password_input.clear()
            self.enable_password_input.clear()
            return

        if found_index < 0:
            found_index = 0

        self.device_combo.setCurrentIndex(found_index)
        self.device_combo.blockSignals(False)
        self.fill_device_fields(devices[found_index])

    def on_device_selected(self, index):
        devices = getattr(self, "available_devices", [])
        if 0 <= index < len(devices):
            self.fill_device_fields(devices[index])

    def fill_device_fields(self, device):
        if not isinstance(device, dict):
            return

        self.hostname_input.setText(str(device.get("hostname", "")))
        self.ip_input.setText(str(device.get("ip", "")))
        self.username_input.setText(str(device.get("username", "")))
        self.password_input.setText(str(device.get("password", "")))
        self.enable_password_input.setText(
            str(device.get("secret", device.get("enable_password", "")))
        )

    def clear_device_fields(self):
        self.hostname_input.clear()
        self.ip_input.clear()
        self.username_input.clear()
        self.password_input.clear()
        self.enable_password_input.clear()
        self.add_log("INFO", "Champs équipement vidés pour saisie manuelle.")

    def load_from_ai(self, acl_plan=None, config=None, report=None):
        self.load_deploy_data(
            acl_plan=acl_plan,
            generated_config=config,
            report=report
        )

    # ======================================================
    # DYNAMIC AI TOPOLOGY VIEW
    # ======================================================

    def update_ai_topology(self):
        """
        Met à jour le schéma selon le report détecté et le plan ACL.
        À appeler après load_deploy_data().
        """
        placement = self.extract_acl_placement()

        self.placement_label.setText(
            f"Emplacement recommandé : {placement.get('device', '-')}\n"
            f"Interface : {placement.get('interface', '-')}\n"
            f"Direction : {placement.get('direction', '-')}\n"
            f"Raison : {placement.get('reason', '-')}"
        )

        self.draw_dynamic_topology(placement)

    def extract_acl_placement(self):
        """
        Récupère l'emplacement ACL depuis plusieurs formats possibles.

        Compatible avec les réponses backend qui utilisent :
        - placement / recommended_placement
        - device / affected_device
        - interface / acl_interface
        - apply_interface / apply_direction
        - direction / reason
        """
        plan = self.acl_plan or {}
        placement = plan.get("placement") or plan.get("recommended_placement") or {}

        device = (
            placement.get("device")
            or placement.get("recommended_device")
            or placement.get("hostname")
            or plan.get("device")
            or plan.get("affected_device")
            or plan.get("recommended_device")
            or ""
        )

        interface = (
            placement.get("interface")
            or placement.get("acl_interface")
            or placement.get("apply_interface")
            or placement.get("recommended_interface")
            or plan.get("interface")
            or plan.get("acl_interface")
            or plan.get("apply_interface")
            or plan.get("recommended_interface")
            or "-"
        )

        direction = (
            placement.get("direction")
            or placement.get("apply_direction")
            or placement.get("recommended_direction")
            or plan.get("direction")
            or plan.get("apply_direction")
            or plan.get("recommended_direction")
            or "IN"
        )

        reason = (
            placement.get("reason")
            or plan.get("reason")
            or "AI placement"
        )

        if not device:
            device = self.find_best_acl_device_from_report()
            reason = "Auto: firewall/core détecté" if device else "Aucun équipement détecté"

        return {
            "device": str(device or "-"),
            "interface": str(interface or "-"),
            "direction": str(direction or "-").upper(),
            "reason": str(reason or "-")
        }

    def find_best_acl_device_from_report(self):
        devices = []
        devices.extend(self.report.get("inventory", {}).get("devices", []) or [])
        devices.extend(self.report.get("topology", {}).get("devices", []) or [])

        # priorité firewall
        for d in devices:
            if not isinstance(d, dict):
                continue
            role = str(d.get("role", "")).upper()
            hostname = d.get("hostname") or d.get("name")
            if hostname and "FIREWALL" in role:
                return hostname

        # sinon core
        for d in devices:
            if not isinstance(d, dict):
                continue
            role = str(d.get("role", "")).upper()
            hostname = d.get("hostname") or d.get("name")
            if hostname and "CORE" in role:
                return hostname

        # sinon premier device
        for d in devices:
            if isinstance(d, dict) and (d.get("hostname") or d.get("name")):
                return d.get("hostname") or d.get("name")

        return "-"

    def draw_dynamic_topology(self, placement):
        """
        Dessine automatiquement le schéma à partir du report.
        Le schéma change selon :
        - devices détectés
        - links détectés
        - zones détectées
        - équipement recommandé par l'AI
        """
        self.topology_scene.clear()
        self.topology_scene.setSceneRect(QRectF(0, 0, 900, 330))

        devices = self.get_report_devices()
        links = self.report.get("topology", {}).get("links", []) or []
        zones = self.report.get("network_context", {}).get("zones", []) or []

        if not devices and not zones:
            self.draw_empty_topology_message()
            return

        positions = self.compute_node_positions(devices, zones)

        # liens entre équipements
        for link in links:
            if not isinstance(link, dict):
                continue
            src = link.get("source") or link.get("source_hostname") or link.get("local_device")
            dst = link.get("target") or link.get("target_hostname") or link.get("remote_device")
            if src in positions and dst in positions:
                self.draw_edge(positions[src], positions[dst], "#2f80ed")

        # liens zone -> device recommandé si aucune relation détaillée n'est donnée
        recommended = placement.get("device")
        if recommended in positions:
            for zone in zones:
                zone_name = zone.get("zone_name") or zone.get("name") or zone.get("vlan_name")
                if zone_name in positions:
                    self.draw_edge(positions[zone_name], positions[recommended], "#55d68a")

        # dessiner devices
        for d in devices:
            name = d.get("hostname") or d.get("name") or "UNKNOWN"
            role = str(d.get("role", d.get("type", "UNKNOWN"))).upper()
            is_selected = name == recommended
            self.draw_device_node(name, role, positions.get(name, (450, 160)), is_selected)

        # dessiner zones
        for zone in zones:
            zone_name = zone.get("zone_name") or zone.get("name") or zone.get("vlan_name") or "ZONE"
            if zone_name in positions:
                self.draw_zone_node(zone_name, positions[zone_name])

    def get_report_devices(self):
        devices = []
        seen = set()

        for source in [
            self.report.get("inventory", {}).get("devices", []),
            self.report.get("topology", {}).get("devices", [])
        ]:
            for d in source or []:
                if not isinstance(d, dict):
                    continue
                name = d.get("hostname") or d.get("name")
                if name and name not in seen:
                    seen.add(name)
                    devices.append(d)

        return devices

    def compute_node_positions(self, devices, zones):
        positions = {}
        width = 900

        # Trier les devices par rôle pour donner une topologie lisible
        role_order = {
            "INTERNET": 0,
            "EDGE_ROUTER": 1,
            "ROUTER": 1,
            "FIREWALL_CORE": 2,
            "FIREWALL": 2,
            "CORE": 3,
            "DISTRIBUTION": 4,
            "ACCESS": 5,
            "SERVER": 6,
            "UNKNOWN": 7,
        }

        sorted_devices = sorted(
            devices,
            key=lambda d: role_order.get(str(d.get("role", d.get("type", "UNKNOWN"))).upper(), 7)
        )

        if sorted_devices:
            step = max(90, min(130, 520 // max(1, len(sorted_devices))))
            start_y = 40
            for i, d in enumerate(sorted_devices):
                name = d.get("hostname") or d.get("name") or f"DEVICE-{i+1}"
                positions[name] = (width // 2, start_y + i * step)

        # zones en bas, réparties horizontalement
        zone_names = []
        for z in zones:
            if isinstance(z, dict):
                zn = z.get("zone_name") or z.get("name") or z.get("vlan_name")
                if zn:
                    zone_names.append(zn)

        count = len(zone_names)
        if count:
            spacing = width // (count + 1)
            for i, zn in enumerate(zone_names):
                positions[zn] = (spacing * (i + 1), 285)

        return positions

    def draw_empty_topology_message(self):
        text = QGraphicsTextItem(
            "Aucune topologie détectée.\nCharge un report de discovery pour générer le schéma dynamiquement."
        )
        text.setDefaultTextColor(QColor("#cbd5e1"))
        text.setFont(QFont("Segoe UI", 12, QFont.Bold))
        text.setPos(240, 130)
        self.topology_scene.addItem(text)

    def draw_edge(self, p1, p2, color="#2f80ed"):
        x1, y1 = p1
        x2, y2 = p2
        line = QGraphicsLineItem(x1, y1, x2, y2)
        line.setPen(QPen(QColor(color), 3))
        self.topology_scene.addItem(line)

    def draw_device_node(self, name, role, pos, selected=False):
        x, y = pos
        w, h = 150, 54
        color = "#1f6feb"

        if "FIREWALL" in role:
            color = "#b91c1c"
        elif "EDGE" in role or "ROUTER" in role:
            color = "#2563eb"
        elif "CORE" in role:
            color = "#7c3aed"
        elif "SWITCH" in role or "DISTRIBUTION" in role or "ACCESS" in role:
            color = "#0f766e"

        rect = QGraphicsRectItem(x - w / 2, y - h / 2, w, h)
        rect.setBrush(QBrush(QColor(color)))
        rect.setPen(QPen(QColor("#60a5fa" if not selected else "#facc15"), 2 if not selected else 4))
        self.topology_scene.addItem(rect)

        label = QGraphicsTextItem(name)
        label.setDefaultTextColor(QColor("white"))
        label.setFont(QFont("Segoe UI", 9, QFont.Bold))
        label.setPos(x - w / 2 + 10, y - 14)
        self.topology_scene.addItem(label)

        if selected:
            marker = QGraphicsTextItem("ACL")
            marker.setDefaultTextColor(QColor("#facc15"))
            marker.setFont(QFont("Segoe UI", 9, QFont.Bold))
            marker.setPos(x + w / 2 - 36, y - h / 2 - 24)
            self.topology_scene.addItem(marker)

    def draw_zone_node(self, name, pos):
        x, y = pos
        w, h = 140, 48
        rect = QGraphicsRectItem(x - w / 2, y - h / 2, w, h)
        rect.setBrush(QBrush(QColor("#14532d")))
        rect.setPen(QPen(QColor("#22c55e"), 2))
        self.topology_scene.addItem(rect)

        label = QGraphicsTextItem(name)
        label.setDefaultTextColor(QColor("white"))
        label.setFont(QFont("Segoe UI", 9, QFont.Bold))
        label.setPos(x - w / 2 + 10, y - 13)
        self.topology_scene.addItem(label)

    # ======================================================
    # DEPLOY
    # ======================================================

    def deploy_acl_config(self):
        """
        Déploiement réel vers le backend.
        Aucun dry-run ici : cette fonction appelle directement /deploy-acl-configs.
        """
        if not self.api_client:
            QMessageBox.warning(self, "API manquante", "ApiClient non connecté.")
            return

        hostname = self.hostname_input.text().strip()
        ip = self.ip_input.text().strip()
        username = self.username_input.text().strip()
        password = self.password_input.text().strip()
        enable_password = self.enable_password_input.text().strip()

        if not hostname or not ip or not username or not password or not enable_password:
            QMessageBox.warning(
                self,
                "Champs manquants",
                "Hostname, IP, username, password et enable password sont obligatoires."
            )
            return

        confirm = QMessageBox.question(
            self,
            "Confirmation déploiement réel",
            f"Voulez-vous vraiment déployer sur {hostname} ({ip}) ?",
            QMessageBox.Yes | QMessageBox.No
        )

        if confirm == QMessageBox.No:
            self.add_log("WARNING", "Déploiement annulé par l’utilisateur.")
            return

        devices = [
            {
                "hostname": hostname,
                "ip": ip,
                "username": username,
                "password": password,
                "enable_password": enable_password
            }
        ]

        self.clear_logs()
        self.current_status.setText("● Déploiement réel en cours...")
        self.current_status.setObjectName("statusRunning")
        self.refresh_status_style()

        self.add_log("INFO", "Préparation du déploiement réel...")
        self.add_log("INFO", f"Équipement cible : {hostname} ({ip})")
        self.add_log("INFO", "Endpoint appelé : POST /deploy-acl-configs")
        self.add_log("INFO", "Payload envoyé : {'devices': [{'hostname', 'ip', 'username', 'password', 'enable_password'}]}")

        try:
            if hasattr(self.api_client, "deploy_acl_configs"):
                result = self.api_client.deploy_acl_configs(devices)
            elif hasattr(self.api_client, "deploy_aclconfig"):
                result = self.api_client.deploy_aclconfig(devices)
            else:
                raise AttributeError(
                    "Méthode manquante dans ApiClient : ajoute deploy_acl_configs(self, devices)."
                )

            data = self.normalize_api_response(result)

            if data.get("status") == "success":
                self.handle_deploy_success(data, hostname, ip)
            else:
                deployment = data.get("deployment_result", {})
                error = (
                    deployment.get("stderr")
                    or deployment.get("stdout")
                    or data.get("errors")
                    or data.get("error")
                    or result.get("error")
                    or "Erreur inconnue"
                )
                self.handle_deploy_error(str(error), hostname, ip)

        except Exception as e:
            self.handle_deploy_error(str(e), hostname, ip)

    def normalize_api_response(self, result):
        if not isinstance(result, dict):
            return {
                "status": "failed",
                "error": "Réponse API invalide."
            }

        if result.get("success") is True:
            data = result.get("data", {})
            if isinstance(data, dict):
                return data
            return {
                "status": "failed",
                "error": "Format data invalide."
            }

        if result.get("success") is False:
            return {
                "status": "failed",
                "error": result.get("error", "Erreur inconnue")
            }

        if result.get("status") in ["success", "failed"]:
            return result

        return {
            "status": "failed",
            "error": str(result)
        }

    def run_dry_run(self, hostname, ip):
        self.clear_logs()
        self.current_status.setText("● Simulation terminée")
        self.current_status.setObjectName("statusSuccess")
        self.refresh_status_style()

        line_count = len([line for line in self.generated_config.splitlines() if line.strip()])

        self.add_log("INFO", "Mode simulation actif : aucune commande réelle envoyée.")
        self.add_log("INFO", f"Équipement cible : {hostname} ({ip})")
        self.add_log("INFO", "Vérification du payload de déploiement...")
        self.add_log("SUCCESS", "Hostname, IP et credentials présents.")
        self.add_log("INFO", "Payload compatible avec Swagger : {'devices': [...]}")
        self.add_log("INFO", f"{line_count} lignes de configuration détectées.")
        self.add_log("SUCCESS", "Configuration prête pour un déploiement réel.")

        now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        self.summary_label.setText(
            f"Statut : Simulation OK\n"
            f"Durée totale : 00:00\n"
            f"Lignes envoyées : 0\n"
            f"Erreurs : 0\n"
            f"Équipement : {hostname} ({ip})\n"
            f"Date : {now}"
        )

        self.add_history(now, hostname, "Simulation OK", str(line_count))

    def handle_deploy_success(self, data, hostname, ip):
        self.add_log("SUCCESS", "Réponse backend reçue avec succès.")

        deployment = data.get("deployment_result", {})
        if isinstance(deployment, dict):
            return_code = deployment.get("return_code")
            stdout = deployment.get("stdout", "")
            stderr = deployment.get("stderr", "")

            if return_code is not None:
                self.add_log("INFO", f"Code retour Ansible : {return_code}")
            if stdout:
                self.add_log("INFO", stdout)
            if stderr:
                self.add_log("WARNING", stderr)

        logs = data.get("logs", [])
        if isinstance(logs, list):
            for log in logs:
                self.add_log("INFO", str(log))

        message = data.get("message") or data.get("detail")
        if message:
            self.add_log("INFO", str(message))

        self.add_log("SUCCESS", "Déploiement terminé avec succès ✓")

        self.current_status.setText("● Succès")
        self.current_status.setObjectName("statusSuccess")
        self.refresh_status_style()

        line_count = len([line for line in self.generated_config.splitlines() if line.strip()])
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        self.summary_label.setText(
            f"Statut : Succès\n"
            f"Durée totale : -\n"
            f"Lignes envoyées : {line_count}\n"
            f"Erreurs : 0\n"
            f"Équipement : {hostname} ({ip})\n"
            f"Date : {now}"
        )

        self.add_history(now, hostname, "Succès", str(line_count))

        QMessageBox.information(
            self,
            "Résultat du déploiement",
            f"Déploiement ACL réussi ✓\n\n"
            f"Équipement : {hostname}\n"
            f"IP : {ip}\n"
            f"Lignes envoyées : {line_count}\n"
            f"Erreurs : 0\n"
            f"Date : {now}\n\n"
            f"La configuration ACL a été envoyée avec succès."
        )

    def handle_deploy_error(self, error, hostname, ip):
        self.add_log("ERROR", str(error))

        self.current_status.setText("● Erreur")
        self.current_status.setObjectName("statusError")
        self.refresh_status_style()

        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        self.summary_label.setText(
            f"Statut : Erreur\n"
            f"Durée totale : -\n"
            f"Lignes envoyées : 0\n"
            f"Erreurs : 1\n"
            f"Équipement : {hostname} ({ip})\n"
            f"Date : {now}"
        )

        self.add_history(now, hostname, "Erreur", "0")

    # ======================================================
    # UTILITIES
    # ======================================================

    def refresh_status_style(self):
        self.current_status.style().unpolish(self.current_status)
        self.current_status.style().polish(self.current_status)

    def add_log(self, level, message):
        now = datetime.now().strftime("%H:%M:%S")

        colors = {
            "INFO": "#60a5fa",
            "SUCCESS": "#22c55e",
            "ERROR": "#ef4444",
            "WARNING": "#f59e0b"
        }

        color = colors.get(level, "#cbd5e1")
        self.logs_box.append(
            f'<span style="color:#94a3b8;">[{now}]</span> '
            f'<span style="color:{color}; font-weight:bold;">[{level}]</span> '
            f'<span style="color:#e5e7eb;">{message}</span>'
        )

    def clear_logs(self):
        self.logs_box.clear()

    def add_history(self, date, hostname, status, lines):
        row = self.history_table.rowCount()
        self.history_table.insertRow(row)

        acl_name = self.acl_plan.get("acl_name", "acl_config")
        values = [date, hostname, f"{acl_name}.cfg", status, "-", lines]

        for col, value in enumerate(values):
            self.history_table.setItem(row, col, QTableWidgetItem(str(value)))

    def copy_config(self):
        self.config_preview.selectAll()
        self.config_preview.copy()
        self.add_log("INFO", "Configuration copiée dans le presse-papiers.")

    def export_config(self):
        self.add_log("INFO", "Export local à connecter selon ton système de fichiers.")

    def export_logs(self):
        path, _ = QFileDialog.getSaveFileName(
            self,
            "Exporter les logs",
            f"deploy_acl_logs_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt",
            "Text Files (*.txt)"
        )

        if not path:
            self.add_log("WARNING", "Export logs annulé par l’utilisateur.")
            return

        try:
            logs = self.logs_box.toPlainText().strip()

            with open(path, "w", encoding="utf-8") as file:
                file.write("===== ACL DEPLOYMENT LOGS =====\n")
                file.write(f"Date export : {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
                file.write("Module : ACL Deployment Center\n")
                file.write("================================\n\n")

                if logs:
                    file.write(logs)
                    file.write("\n")
                else:
                    file.write("Aucun log disponible.\n")

            self.add_log("SUCCESS", f"Logs exportés vers : {path}")
            QMessageBox.information(self, "Export logs", f"Logs exportés avec succès :\n{path}")

        except Exception as e:
            self.add_log("ERROR", f"Erreur export logs : {e}")
            QMessageBox.critical(self, "Erreur export", str(e))

    def show_history(self):
        total = self.history_table.rowCount()

        if total == 0:
            QMessageBox.information(
                self,
                "Historique des déploiements",
                "Aucun ancien déploiement trouvé."
            )
            return

        success = 0
        errors = 0
        simulations = 0
        details = []

        for row in range(total):
            values = []
            for col in range(6):
                item = self.history_table.item(row, col)
                values.append(item.text() if item else "-")

            date, device, file_name, status, duration, lines = values

            status_lower = status.lower()
            if "succès" in status_lower or "success" in status_lower:
                success += 1
            elif "erreur" in status_lower or "error" in status_lower or "failed" in status_lower:
                errors += 1
            elif "simulation" in status_lower:
                simulations += 1

            details.append(
                f"• {date} | {device} | {file_name} | {status} | Durée: {duration} | Lignes: {lines}"
            )

        message = (
            f"Total déploiements : {total}\n"
            f"Succès : {success}\n"
            f"Erreurs : {errors}\n"
            f"Simulations : {simulations}\n\n"
            "Détails :\n" + "\n".join(details)
        )

        QMessageBox.information(self, "Historique des déploiements", message)

    def reset_page(self):
        self.acl_plan = {}
        self.generated_config = ""
        self.report = {}
        self.available_devices = []

        if hasattr(self, "config_preview"):
            self.config_preview.setText("Aucune configuration chargée.")
            self.logs_box.clear()

            self.config_file_combo.clear()
            self.config_file_combo.addItem("Aucune configuration chargée")

            self.device_combo.blockSignals(True)
            self.device_combo.clear()
            self.device_combo.addItem("Sélectionner un équipement")
            self.device_combo.blockSignals(False)

            self.hostname_input.clear()
            self.ip_input.clear()
            self.username_input.clear()
            self.password_input.clear()
            self.enable_password_input.clear()

            self.summary_label.setText(
                "Statut : -\n"
                "Durée totale : -\n"
                "Lignes envoyées : -\n"
                "Erreurs : -\n"
                "Équipement : -\n"
                "Date : -"
            )

            self.info_lines.setText(
                "Nombre de lignes : -\n"
                "Type de configuration : ACL\n"
                "Date de génération : -\n"
                "Généré par : -\n"
                "Hash : -"
            )

            self.current_status.setText("● Prêt pour le déploiement")
            self.current_status.setObjectName("statusReady")
            self.refresh_status_style()
            self.update_ai_topology()

    # ======================================================
    # STYLE
    # ======================================================

    def apply_style(self):
        self.setStyleSheet("""
            QWidget {
                background-color: #020B18;
                color: #EAF2FF;
                font-family: Segoe UI;
                font-size: 12px;
            }

            QScrollArea#pageScroll {
                background-color: #020B18;
                border: none;
            }

            QLabel#pageTitle {
                font-size: 24px;
                font-weight: 900;
                color: white;
            }

            QLabel#subtitle {
                color: #8EA4C8;
                font-size: 12px;
            }

            QLabel#cardTitle {
                color: #FFFFFF;
                font-size: 14px;
                font-weight: 900;
            }

            QLabel#agentBadge {
                background-color: #071827;
                border: 1px solid #1E3552;
                border-radius: 14px;
                padding: 9px 14px;
                color: #22c55e;
                font-weight: bold;
            }

            QLabel#avatar {
                background-color: #3E5FAE;
                border-radius: 22px;
                font-size: 20px;
                font-weight: bold;
            }

            QLabel#userInfo {
                font-weight: bold;
                color: white;
            }

            QLabel#stepActive {
                background-color: #2f236f;
                border: 1px solid #7c3aed;
                border-radius: 18px;
                color: white;
                font-weight: bold;
                padding: 7px 11px;
            }

            QLabel#stepIdle {
                background-color: #081525;
                border: 1px solid #243D5C;
                border-radius: 18px;
                color: #94a3b8;
                font-weight: bold;
                padding: 7px 11px;
            }

            QLabel#stepLine {
                color: #7c3aed;
            }

            QLabel#inputLabel {
                color: #cbd5e1;
                font-weight: 600;
            }

            QLabel#warningText {
                color: #f59e0b;
                font-weight: bold;
            }

            QLabel#infoText {
                color: #cbd5e1;
                line-height: 140%;
            }

            QLabel#successIcon {
                color: #22c55e;
                border: 4px solid #22c55e;
                border-radius: 42px;
                font-size: 36px;
                font-weight: bold;
                min-width: 68px;
                min-height: 68px;
                max-width: 68px;
                max-height: 68px;
            }

            QLabel#statusReady {
                background-color: #0B2447;
                border: 1px solid #1D4E89;
                border-radius: 8px;
                padding: 6px 10px;
                color: #93c5fd;
                font-weight: bold;
            }

            QLabel#statusRunning {
                background-color: #2a1f00;
                border: 1px solid #f59e0b;
                border-radius: 8px;
                padding: 6px 10px;
                color: #f59e0b;
                font-weight: bold;
            }

            QLabel#statusSuccess {
                background-color: #052e1b;
                border: 1px solid #22c55e;
                border-radius: 8px;
                padding: 6px 10px;
                color: #22c55e;
                font-weight: bold;
            }

            QLabel#statusError {
                background-color: #3f0a0a;
                border: 1px solid #ef4444;
                border-radius: 8px;
                padding: 6px 10px;
                color: #ef4444;
                font-weight: bold;
            }

            QFrame#card {
                background-color: #071426;
                border: 1px solid #16345C;
                border-radius: 16px;
            }

            QLineEdit, QComboBox, QSpinBox {
                background-color: #081A30;
                border: 1px solid #1C3D68;
                border-radius: 8px;
                padding: 8px;
                color: white;
            }

            QTextEdit#cliBox {
                background-color: #020812;
                border: 1px solid #214B7D;
                border-radius: 12px;
                color: #B6FCD5;
                font-family: Consolas;
                font-size: 12px;
            }

            QTextEdit#logsBox {
                background-color: #020812;
                border: 1px solid #214B7D;
                border-radius: 12px;
                color: white;
                font-family: Consolas;
                font-size: 12px;
            }

            QPushButton {
                border: none;
                border-radius: 10px;
                padding: 8px 12px;
                color: white;
                font-weight: bold;
            }

            QPushButton#darkBtn, QPushButton#smallBtn {
                background-color: #0D1A2C;
                border: 1px solid #2B4262;
            }

            QPushButton#darkBtn:hover, QPushButton#smallBtn:hover {
                background-color: #162B45;
            }

            QPushButton#primaryPurple {
                background-color: #5B2FEA;
            }

            QPushButton#deployBtn {
                background-color: #16a34a;
                font-size: 14px;
            }

            QPushButton#deployBtn:hover {
                background-color: #22c55e;
            }

            QCheckBox {
                color: #DCEBFF;
                spacing: 8px;
            }

            QTableWidget {
                background-color: #06182D;
                border: 1px solid #16345C;
                border-radius: 10px;
                gridline-color: #16345C;
                color: #EAF2FF;
            }


            QLabel#placementBox {
                background-color: #071d33;
                border: 1px solid #1D4E89;
                border-radius: 12px;
                padding: 12px;
                color: #e5e7eb;
                font-size: 13px;
            }

            QGraphicsView#topologyView {
                background-color: #020812;
                border: 1px solid #214B7D;
                border-radius: 14px;
            }
            QHeaderView::section {
                background-color: #0B1B33;
                color: #9BB0D1;
                padding: 8px;
                border: none;
                font-weight: bold;
            }
        """)