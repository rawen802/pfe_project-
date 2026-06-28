from datetime import datetime

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QTextEdit, QFrame, QComboBox, QMessageBox, QFileDialog
)

from services.api_client import ApiClient


class ConfigGenerationPage(QWidget):
    def __init__(
        self,
        final_plan=None,
        base_network="",
        report=None,
        parent_stack=None,
        user_data=None,
        api_client=None,
        ai_analysis_page=None
    ):
        super().__init__()

        self.api = api_client if api_client else ApiClient()
        self.final_plan = final_plan or []
        self.base_network = base_network
        self.report = report or {}
        self.parent_stack = parent_stack
        self.user_data = user_data or {}
        self.ai_analysis_page = ai_analysis_page

        self.generated_config = ""
        self.rendered_configs = {}

        self.setup_ui()

    def setup_ui(self):
        main = QVBoxLayout(self)

        title = QLabel("Configuration Cisco")
        title.setStyleSheet("font-size: 26px; font-weight: bold; color: #e5f0ff;")
        main.addWidget(title)

        stepper = QLabel("✓ Génération → Validation AI → Déploiement")
        stepper.setStyleSheet("color: #60a5fa; padding: 10px;")
        main.addWidget(stepper)

        layout = QHBoxLayout()

        left_card = self.create_card()
        left_layout = QVBoxLayout(left_card)

        self.device_combo = QComboBox()
        self.populate_device_combo()

        btn_layout = QHBoxLayout()
        self.btn_generate = QPushButton("Générer")
        self.btn_copy = QPushButton("Copier")
        self.btn_clear = QPushButton("Effacer")

        btn_layout.addWidget(self.btn_generate)
        btn_layout.addWidget(self.btn_copy)
        btn_layout.addWidget(self.btn_clear)

        self.preview = QTextEdit()

        left_layout.addWidget(self.device_combo)
        left_layout.addLayout(btn_layout)
        left_layout.addWidget(self.preview)

        right_card = self.create_card()
        right_layout = QVBoxLayout(right_card)

        self.summary = QLabel("Statut : En attente")
        self.validation = QLabel("Validation AI : en attente")

        right_layout.addWidget(self.summary)
        right_layout.addWidget(self.validation)

        layout.addWidget(left_card, 3)
        layout.addWidget(right_card, 1)

        main.addLayout(layout)

        bottom = QHBoxLayout()
        self.btn_save = QPushButton("Enregistrer")
        self.btn_ai = QPushButton("Validation AI")

        bottom.addWidget(self.btn_save)
        bottom.addWidget(self.btn_ai)

        main.addLayout(bottom)

        self.logs = QTextEdit()
        self.logs.setMaximumHeight(100)
        main.addWidget(self.logs)

        self.apply_styles()

        self.btn_generate.clicked.connect(self.generate_config)
        self.device_combo.currentTextChanged.connect(self.on_device_changed)
        self.btn_copy.clicked.connect(self.copy_config)
        self.btn_clear.clicked.connect(self.clear)
        self.btn_save.clicked.connect(self.save)
        self.btn_ai.clicked.connect(self.go_ai)

    def clean_device_name(self, value):
        if value is None:
            return ""

        if isinstance(value, list):
            if not value:
                return ""
            value = value[0]

        if isinstance(value, dict):
            return str(value.get("hostname") or value.get("name") or "").strip()

        text = str(value).strip()

        if "," in text:
            return text.split(",")[0].strip()

        return text

    def populate_device_combo(self):
        self.device_combo.clear()

        devices = []

        for item in self.final_plan:
            if not isinstance(item, dict):
                continue

            sw = self.clean_device_name(item.get("switches"))
            svi = self.clean_device_name(item.get("svi"))

            if sw and sw not in devices:
                devices.append(sw)

            if svi and svi not in devices:
                devices.append(svi)

        if not devices:
            devices = ["Aucun équipement"]

        self.device_combo.addItems(devices)

    def refresh_device_combo_from_configs(self):
        if not isinstance(self.rendered_configs, dict) or not self.rendered_configs:
            return

        current = self.device_combo.currentText()
        config_devices = list(self.rendered_configs.keys())

        self.device_combo.blockSignals(True)
        self.device_combo.clear()
        self.device_combo.addItems(config_devices)

        if current in config_devices:
            self.device_combo.setCurrentText(current)
        elif config_devices:
            self.device_combo.setCurrentText(config_devices[0])

        self.device_combo.blockSignals(False)

    def on_device_changed(self):
        selected_device = self.device_combo.currentText()

        if isinstance(self.rendered_configs, dict) and selected_device in self.rendered_configs:
            self.generated_config = self.rendered_configs[selected_device]
            self.preview.setText(self.generated_config)

            vlan_count = len(self.final_plan)

            self.summary.setText(
                f"Statut : Généré\n"
                f"VLANs : {vlan_count}\n"
                f"Équipement : {selected_device}"
            )

            self.log(f"Configuration affichée : {selected_device}")

    def apply_styles(self):
        self.setStyleSheet("""
            QWidget {
                background-color: #07111f;
                color: #e5f0ff;
            }

            QPushButton {
                background-color: #2563eb;
                color: white;
                padding: 8px;
                border-radius: 6px;
            }

            QPushButton:hover {
                background-color: #1d4ed8;
            }

            QTextEdit {
                background-color: #08111f;
                border: 1px solid #1d4ed8;
                border-radius: 8px;
                color: #d1fae5;
            }

            QComboBox {
                background-color: #111c2f;
                border: 1px solid #2d4665;
                padding: 6px;
                color: #e5f0ff;
            }

            QLabel {
                color: #e5f0ff;
            }
        """)

    def create_card(self):
        card = QFrame()
        card.setStyleSheet("""
            QFrame {
                background: #0d1b2e;
                border: 1px solid #16466d;
                border-radius: 10px;
                padding: 10px;
            }
        """)
        return card

    def log(self, msg):
        self.logs.append(f"[{datetime.now().strftime('%H:%M:%S')}] {msg}")

    def format_payload(self):
        requested_zones = []
        requirements = []

        for item in self.final_plan:
            zone_name = (
                item.get("zone_name")
                or item.get("zone")
                or item.get("vlan_name")
                or item.get("name")
                or "UNKNOWN"
            )

            vlan_name = (
                item.get("vlan_name")
                or item.get("name")
                or zone_name
            )

            required_hosts = (
                item.get("required_hosts")
                or item.get("hosts")
                or item.get("host_count")
                or 50
            )

            try:
                required_hosts = int(required_hosts)
            except Exception:
                required_hosts = 50

            requested_zones.append({
                "zone_name": zone_name,
                "vlan_name": vlan_name,
                "required_hosts": required_hosts,
                "target_switch": item.get("switches"),
                "svi": item.get("svi")
            })

            requirements.append({
                "zone_name": zone_name,
                "required_hosts": required_hosts
            })

        return {
            "report": self.report,
            "base_network": self.base_network,
            "requested_zones": requested_zones,
            "requirements": requirements,
            "final_plan": self.final_plan
        }

    def extract_config(self, data):
        if not isinstance(data, dict):
            return None

        rendered_configs = data.get("rendered_configs")

        if isinstance(rendered_configs, dict) and rendered_configs:
            self.rendered_configs = rendered_configs
            self.refresh_device_combo_from_configs()

            selected_device = self.device_combo.currentText()

            if selected_device in rendered_configs:
                return rendered_configs[selected_device]

            first_device = next(iter(rendered_configs.keys()))
            self.device_combo.setCurrentText(first_device)
            return rendered_configs[first_device]

        config = (
            data.get("config")
            or data.get("generated_config")
            or data.get("configuration")
            or data.get("rendered_config")
            or data.get("cfg")
        )

        if config:
            self.rendered_configs = {
                self.device_combo.currentText() or "CONFIG": config
            }
            return config

        return None

    def generate_config(self):
        try:
            if not self.final_plan:
                QMessageBox.warning(self, "Erreur", "Plan vide")
                return

            if self.api is None:
                QMessageBox.critical(self, "Erreur API", "ApiClient non reçu.")
                return

            self.log("Appel API via ApiClient...")

            payload = self.format_payload()
            self.log(f"Payload envoyé : {payload}")

            result = self.api.post("/render-network", payload)

            if not result.get("success"):
                error = result.get("error", "Erreur backend")
                self.log(error)
                QMessageBox.critical(self, "Erreur backend", error)
                return

            data = result.get("data", {})
            config = self.extract_config(data)

            if not config:
                self.log(str(data))
                QMessageBox.critical(
                    self,
                    "Erreur",
                    "Aucune configuration retournée par le backend."
                )
                return

            self.generated_config = config
            self.preview.setText(config)

            vlan_count = len(self.final_plan)

            selected_device = self.device_combo.currentText()

            self.summary.setText(
                f"Statut : Généré\n"
                f"VLANs : {vlan_count}\n"
                f"Équipement : {selected_device}"
            )
            self.validation.setText("Prêt pour validation AI")

            self.log("Configuration générée avec succès")

        except Exception as e:
            self.log(str(e))
            QMessageBox.critical(self, "Erreur", str(e))

    def copy_config(self):
        if not self.generated_config:
            QMessageBox.warning(self, "Vide", "Aucune configuration à copier.")
            return

        self.preview.selectAll()
        self.preview.copy()
        self.log("Copié")

    def clear(self):
        self.preview.clear()
        self.logs.clear()
        self.generated_config = ""
        self.summary.setText("Statut : En attente")
        self.validation.setText("Validation AI : en attente")

    def save(self):
        if not self.generated_config:
            QMessageBox.warning(self, "Vide", "Aucune configuration à enregistrer.")
            return

        path, _ = QFileDialog.getSaveFileName(
            self,
            "Enregistrer configuration Cisco",
            f"{self.device_combo.currentText() or 'config'}.cfg",
            "Cisco Config (*.cfg);;Text Files (*.txt)"
        )

        if path:
            with open(path, "w", encoding="utf-8") as f:
                f.write(self.generated_config)
            self.log("Sauvegardé")

    def find_ai_analysis_page(self):
        if self.ai_analysis_page is not None:
            return self.ai_analysis_page

        main_window = self.window()

        possible_names = [
            "page_ai_analysis",       # nom utilisé dans ton MainWindow
            "ai_analysis_page",
            "page_ai_analysis_widget",
            "ai_page",
            "page_ai",
        ]

        for name in possible_names:
            page = getattr(main_window, name, None)
            if page is not None:
                return page

        return None

    def go_ai(self):
        if not self.final_plan:
            QMessageBox.warning(
                self,
                "Plan manquant",
                "Aucun plan VLAN/VLSM disponible pour la validation AI."
            )
            return

        if not self.generated_config:
            QMessageBox.warning(
                self,
                "Configuration manquante",
                "Génère d’abord la configuration avant la validation AI."
            )
            return

        ai_page = self.find_ai_analysis_page()

        if ai_page is None:
            QMessageBox.warning(
                self,
                "Page AI introuvable",
                "La page AI Analysis n’est pas connectée à ConfigGenerationPage."
            )
            return

        # Méthode recommandée ajoutée dans AIAnalysisPage.
        if hasattr(ai_page, "load_vlan_config_validation_data"):
            ai_page.load_vlan_config_validation_data(
                report=self.report,
                final_plan=self.final_plan,
                generated_config=self.generated_config,
                rendered_configs=self.rendered_configs,
                base_network=self.base_network
            )
        # Compatibilité avec une ancienne méthode possible.
        elif hasattr(ai_page, "load_vlan_validation_data"):
            ai_page.load_vlan_validation_data(
                vlan_plan=self.final_plan,
                vlsm_plan={
                    "base_network": self.base_network,
                    "generated_config": self.generated_config
                },
                report=self.report
            )
        else:
            QMessageBox.warning(
                self,
                "Méthode AI manquante",
                "Ajoute load_vlan_config_validation_data() dans AIAnalysisPage."
            )
            return

        # Navigation vers la page AI dans le QStackedWidget
        main_window = self.window()

        if self.parent_stack:
            self.parent_stack.setCurrentWidget(ai_page)
        elif hasattr(main_window, "stack"):
            main_window.stack.setCurrentWidget(ai_page)
        else:
            ai_page.show()

        # Mettre à jour le titre et le bouton actif du MainWindow si disponibles
        if hasattr(main_window, "page_title"):
            main_window.page_title.setText("AI Analysis")

        if hasattr(main_window, "update_active_button"):
            main_window.update_active_button(6)

        self.validation.setText("Validation AI : plan envoyé")
        self.log("Plan VLAN/VLSM envoyé vers AI Analysis → VLAN/VLSM Validation")
