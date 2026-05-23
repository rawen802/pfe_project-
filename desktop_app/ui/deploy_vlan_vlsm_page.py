from datetime import datetime

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QWidget, QLabel, QPushButton, QTextEdit, QVBoxLayout, QHBoxLayout,
    QFrame, QTableWidget, QTableWidgetItem, QCheckBox, QMessageBox,
    QScrollArea, QFileDialog, QComboBox, QLineEdit
)


class DeployVlanVlsmPage(QWidget):
    def __init__(self, api_client=None, user_data=None):
        super().__init__()

        self.api_client = api_client
        self.user_data = user_data or {}

        self.report = {}
        self.final_plan = []
        self.generated_config = ""
        self.devices = []

        self.setup_ui()
        self.apply_style()

    def setup_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # Toute la page est placée dans un QScrollArea pour permettre
        # le défilement avec la molette de la souris quand l'écran est petit.
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        scroll.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOn)

        container = QWidget()
        container.setMinimumHeight(1200)
        root = QVBoxLayout(container)
        root.setContentsMargins(10, 10, 10, 10)
        root.setSpacing(10)

        title = QLabel("Déploiement VLAN / VLSM")
        title.setObjectName("pageTitle")

        subtitle = QLabel("Déploiement de la configuration VLAN / VLSM vers vos équipements réseau")
        subtitle.setObjectName("subtitle")

        root.addWidget(title)
        root.addWidget(subtitle)

        root.addLayout(self.create_steps())
        root.addLayout(self.create_stats())

        content = QHBoxLayout()
        content.setSpacing(10)
        content.addWidget(self.create_config_card(), 38)
        content.addWidget(self.create_devices_and_logs(), 42)
        content.addWidget(self.create_summary_card(), 20)

        root.addLayout(content)

        # Historique visible + scroll interne du tableau
        history_card = self.create_history_card()
        history_card.setMinimumHeight(220)
        history_card.setMaximumHeight(270)
        root.addWidget(history_card)

        root.addSpacing(20)

        scroll.verticalScrollBar().setSingleStep(20)
        scroll.setWidget(container)
        main_layout.addWidget(scroll)

    def create_steps(self):
        layout = QHBoxLayout()
        steps = [
            "✓ 1. Génération\nComplété",
            "✓ 2. Validation AI\nValidé",
            "3. Déploiement\nEn cours",
            "4. Résultat\nEn attente"
        ]

        for i, text in enumerate(steps):
            lbl = QLabel(text)
            lbl.setAlignment(Qt.AlignCenter)
            lbl.setObjectName("stepActive" if i < 3 else "stepIdle")
            lbl.setFixedHeight(44)
            layout.addWidget(lbl)

        return layout

    def create_stats(self):
        layout = QHBoxLayout()
        self.stat_devices = self.stat_card("Équipements ciblés", "0", "Total")
        self.stat_configs = self.stat_card("Prêtes à déployer", "0", "Prêtes")
        self.stat_status = self.stat_card("Statut global", "En attente", "Déploiement")
        self.stat_start = self.stat_card("Début", "--:--:--", "hh:mm:ss")

        layout.addWidget(self.stat_devices)
        layout.addWidget(self.stat_configs)
        layout.addWidget(self.stat_status)
        layout.addWidget(self.stat_start)

        return layout

    def stat_card(self, title, value, desc):
        card = QFrame()
        card.setObjectName("card")
        card.setMaximumHeight(62)
        layout = QVBoxLayout(card)
        layout.setContentsMargins(10, 6, 10, 6)
        layout.setSpacing(2)

        t = QLabel(title)
        t.setObjectName("smallTitle")

        v = QLabel(value)
        v.setObjectName("statValue")

        d = QLabel(desc)
        d.setObjectName("subtitle")

        layout.addWidget(t)
        layout.addWidget(v)
        layout.addWidget(d)

        return card

    def create_config_card(self):
        card = QFrame()
        card.setObjectName("card")
        card.setMinimumHeight(300)
        card.setMaximumHeight(360)
        layout = QVBoxLayout(card)
        layout.setContentsMargins(10, 8, 10, 8)
        layout.setSpacing(5)

        title = QLabel("1. Configuration à déployer")
        title.setObjectName("cardTitle")

        self.config_preview = QTextEdit()
        self.config_preview.setReadOnly(True)
        self.config_preview.setObjectName("cliBox")

        self.config_info = QLabel("Lignes : -     Taille : -")
        self.config_info.setObjectName("subtitle")

        btn_view = QPushButton("👁 Voir la configuration complète")
        btn_view.setObjectName("darkBtn")
        btn_view.clicked.connect(self.show_full_config)

        layout.addWidget(title)
        layout.addWidget(QLabel("Aperçu de la configuration"))
        layout.addWidget(self.config_preview, 1)
        layout.addWidget(self.config_info)
        layout.addWidget(btn_view)

        return card

    def create_devices_and_logs(self):
        wrapper = QFrame()
        wrapper.setObjectName("transparent")
        layout = QVBoxLayout(wrapper)
        layout.setSpacing(8)

        layout.addWidget(self.create_devices_card())
        layout.addWidget(self.create_logs_card())

        return wrapper

    def create_devices_card(self):
        card = QFrame()
        card.setObjectName("card")
        card.setMinimumHeight(150)
        card.setMaximumHeight(175)
        layout = QVBoxLayout(card)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(8)

        top = QHBoxLayout()
        title = QLabel("2. Équipements ciblés")
        title.setObjectName("cardTitle")

        btn_add = QPushButton("+ Ajouter un équipement")
        btn_add.setObjectName("blueBtn")
        btn_add.clicked.connect(self.add_manual_device)

        top.addWidget(title)
        top.addStretch()
        top.addWidget(btn_add)

        self.devices_table = QTableWidget(0, 5)
        self.devices_table.setMinimumHeight(58)
        self.devices_table.setMaximumHeight(72)
        self.devices_table.setHorizontalHeaderLabels(
            ["", "Hostname", "IP Address", "Type", "Statut"]
        )
        self.devices_table.verticalHeader().setVisible(False)
        self.devices_table.horizontalHeader().setStretchLastSection(True)

        self.selected_label = QLabel("0 équipement(s) sélectionné(s)")
        self.selected_label.setObjectName("subtitle")

        btn_remove = QPushButton("🗑 Supprimer la sélection")
        btn_remove.setObjectName("dangerBtn")
        btn_remove.clicked.connect(self.remove_selected_devices)

        bottom = QHBoxLayout()
        bottom.addWidget(self.selected_label)
        bottom.addStretch()
        bottom.addWidget(btn_remove)

        layout.addLayout(top)
        layout.addWidget(self.devices_table)
        layout.addLayout(bottom)

        return card

    def create_logs_card(self):
        card = QFrame()
        card.setObjectName("card")
        card.setMinimumHeight(150)
        card.setMaximumHeight(175)
        layout = QVBoxLayout(card)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(8)

        top = QHBoxLayout()
        title = QLabel("4. Journal de déploiement")
        title.setObjectName("cardTitle")

        btn_clear = QPushButton("Effacer")
        btn_clear.setObjectName("darkBtn")
        btn_clear.clicked.connect(self.clear_logs)

        btn_export = QPushButton("Exporter")
        btn_export.setObjectName("darkBtn")
        btn_export.clicked.connect(self.export_logs)

        top.addWidget(title)
        top.addStretch()
        top.addWidget(btn_clear)
        top.addWidget(btn_export)

        self.logs_box = QTextEdit()
        self.logs_box.setReadOnly(True)
        self.logs_box.setObjectName("logsBox")
        self.logs_box.setMinimumHeight(58)
        self.logs_box.setMaximumHeight(75)

        layout.addLayout(top)
        layout.addWidget(self.logs_box)

        return card

    def create_summary_card(self):
        card = QFrame()
        card.setObjectName("card")
        card.setMinimumHeight(300)
        card.setMaximumHeight(360)
        layout = QVBoxLayout(card)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(10)

        title = QLabel("5. Résumé du déploiement")
        title.setObjectName("cardTitle")

        self.summary_label = QLabel(
            "Réussis : 0\n"
            "En cours : 0\n"
            "En attente : 0\n"
            "Échoués : 0\n\n"
            "Équipements traités : 0 / 0"
        )

        self.deploy_btn = QPushButton("▶ Lancer le déploiement")
        self.deploy_btn.setObjectName("deployBtn")
        self.deploy_btn.clicked.connect(self.deploy_configs)

        layout.addWidget(title)
        layout.addWidget(self.summary_label)
        layout.addStretch()
        layout.addWidget(self.deploy_btn)

        return card

    def create_history_card(self):
        card = QFrame()
        card.setObjectName("card")

        layout = QVBoxLayout(card)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(8)

        top = QHBoxLayout()
        title = QLabel("6. Historique des déploiements")
        title.setObjectName("cardTitle")

        btn_history = QPushButton("Voir tout l’historique")
        btn_history.setObjectName("darkBtn")
        btn_history.clicked.connect(self.show_history)

        top.addWidget(title)
        top.addStretch()
        top.addWidget(btn_history)

        self.history_table = QTableWidget(0, 7)
        self.history_table.setHorizontalHeaderLabels([
            "ID", "Date", "Équipements", "Statut", "Résultat", "Durée", "Utilisateur"
        ])

        self.history_table.verticalHeader().setVisible(False)
        self.history_table.horizontalHeader().setStretchLastSection(True)

        # Taille normale pour que les lignes apparaissent correctement.
        self.history_table.setMinimumHeight(140)
        self.history_table.setMaximumHeight(185)

        # Scroll interne du tableau historique.
        self.history_table.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        self.history_table.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)

        layout.addLayout(top)
        layout.addWidget(self.history_table)

        return card

    def load_deploy_data(self, final_plan=None, generated_config=None, report=None):
        self.final_plan = final_plan or []
        self.generated_config = str(generated_config or "")
        self.report = report or {}

        self.config_preview.setText(self.generated_config or "Aucune configuration chargée.")

        lines = len([l for l in self.generated_config.splitlines() if l.strip()])
        size = len(self.generated_config.encode("utf-8")) / 1024
        self.config_info.setText(f"Lignes : {lines}     Taille : {size:.1f} KB")

        self.extract_devices_from_report()
        self.populate_devices_table()

        self.add_log("INFO", "Configuration VLAN/VLSM chargée pour déploiement.")

    def extract_devices_from_report(self):
        self.devices = []

        inventory_devices = self.report.get("inventory", {}).get("devices", [])
        topology_devices = self.report.get("topology", {}).get("devices", [])

        source = inventory_devices if inventory_devices else topology_devices

        for d in source:
            if not isinstance(d, dict):
                continue

            hostname = d.get("hostname") or d.get("name")
            ip = d.get("ip") or d.get("ansible_host")

            if not hostname:
                continue

            self.devices.append({
                "hostname": hostname,
                "ip": ip or "",
                "type": d.get("role") or d.get("type") or d.get("model") or "Switch",
                "username": d.get("username", ""),
                "password": d.get("password", ""),
                "enable_password": d.get("secret", d.get("enable_password", "")),
                "status": "En attente"
            })

    def populate_devices_table(self):
        self.devices_table.setRowCount(0)

        for device in self.devices:
            row = self.devices_table.rowCount()
            self.devices_table.insertRow(row)
            self.devices_table.setRowHeight(row, 24)

            check = QTableWidgetItem()
            check.setCheckState(Qt.Checked)
            self.devices_table.setItem(row, 0, check)

            self.devices_table.setItem(row, 1, QTableWidgetItem(device["hostname"]))
            self.devices_table.setItem(row, 2, QTableWidgetItem(device["ip"]))
            self.devices_table.setItem(row, 3, QTableWidgetItem(device["type"]))
            self.devices_table.setItem(row, 4, QTableWidgetItem(device["status"]))

        self.update_selected_count()

    def update_selected_count(self):
        selected = 0
        for row in range(self.devices_table.rowCount()):
            item = self.devices_table.item(row, 0)
            if item and item.checkState() == Qt.Checked:
                selected += 1

        self.selected_label.setText(f"{selected} équipement(s) sélectionné(s)")
        self.stat_devices.findChildren(QLabel)[1].setText(str(selected))
        self.stat_configs.findChildren(QLabel)[1].setText("1" if self.generated_config else "0")

    def get_selected_devices(self):
        selected = []

        for row in range(self.devices_table.rowCount()):
            check = self.devices_table.item(row, 0)
            if not check or check.checkState() != Qt.Checked:
                continue

            hostname = self.devices_table.item(row, 1).text()
            ip = self.devices_table.item(row, 2).text()

            original = next((d for d in self.devices if d["hostname"] == hostname), {})

            selected.append({
                "hostname": hostname,
                "ip": ip,
                "username": original.get("username", ""),
                "password": original.get("password", ""),
                "enable_password": original.get("enable_password", "")
            })

        return selected

    def deploy_configs(self):
        if not self.api_client:
            QMessageBox.warning(self, "API manquante", "ApiClient non connecté.")
            return

        if not self.generated_config:
            QMessageBox.warning(self, "Configuration manquante", "Aucune configuration à déployer.")
            return

        devices = self.get_selected_devices()

        if not devices:
            QMessageBox.warning(self, "Aucun équipement", "Sélectionne au moins un équipement.")
            return

        for d in devices:
            if not d["ip"] or not d["username"] or not d["password"] or not d["enable_password"]:
                QMessageBox.warning(
                    self,
                    "Identifiants manquants",
                    f"Identifiants incomplets pour {d['hostname']}."
                )
                return

        confirm = QMessageBox.question(
            self,
            "Confirmation",
            f"Lancer le déploiement réel sur {len(devices)} équipement(s) ?",
            QMessageBox.Yes | QMessageBox.No
        )

        if confirm == QMessageBox.No:
            return

        self.clear_logs()
        start = datetime.now().strftime("%H:%M:%S")
        self.stat_start.findChildren(QLabel)[1].setText(start)
        self.stat_status.findChildren(QLabel)[1].setText("En cours")

        self.add_log("INFO", "Déploiement initialisé.")
        self.add_log("INFO", "Préparation des configurations.")
        self.add_log("INFO", "Endpoint appelé : POST /deploy-network")

        try:
            if hasattr(self.api_client, "deploy_network_configs"):
                result = self.api_client.deploy_network_configs(devices)
            else:
                result = self.api_client.post("/deploy-network", {"devices": devices})

            if result.get("success"):
                self.handle_success(result.get("data", {}), devices)
            else:
                self.handle_error(result.get("error", "Erreur inconnue"), devices)

        except Exception as e:
            self.handle_error(str(e), devices)

    def handle_success(self, data, devices):
        self.add_log("SUCCESS", "Réponse backend reçue avec succès.")

        stdout = data.get("stdout")
        stderr = data.get("stderr")
        logs = data.get("logs", [])

        if stdout:
            self.add_log("INFO", stdout)
        if stderr:
            self.add_log("WARNING", stderr)
        if isinstance(logs, list):
            for log in logs:
                self.add_log("INFO", str(log))

        self.add_log("SUCCESS", "Déploiement VLAN/VLSM terminé avec succès ✓")

        total = len(devices)
        self.summary_label.setText(
            f"Réussis : {total}\n"
            f"En cours : 0\n"
            f"En attente : 0\n"
            f"Échoués : 0\n\n"
            f"Équipements traités : {total} / {total}"
        )

        self.stat_status.findChildren(QLabel)[1].setText("Terminé")

        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        self.add_history(now, total, "Terminé", f"{total} Réussi(s)", "-")

        QMessageBox.information(
            self,
            "Résultat du déploiement",
            f"Déploiement VLAN/VLSM réussi ✓\n\n"
            f"Équipements : {total}\n"
            f"Date : {now}"
        )

    def handle_error(self, error, devices):
        self.add_log("ERROR", error)
        total = len(devices)

        self.summary_label.setText(
            f"Réussis : 0\n"
            f"En cours : 0\n"
            f"En attente : 0\n"
            f"Échoués : {total}\n\n"
            f"Équipements traités : 0 / {total}"
        )

        self.stat_status.findChildren(QLabel)[1].setText("Erreur")

        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        self.add_history(now, total, "Erreur", "Échec", "-")

        QMessageBox.critical(self, "Erreur déploiement", str(error))

    def add_history(self, date, devices_count, status, result, duration):
        row = self.history_table.rowCount()
        self.history_table.insertRow(row)

        deployment_id = f"DEP-{datetime.now().strftime('%Y%m%d-%H%M%S')}"
        user = self.user_data.get("username", "utilisateur")

        values = [
            deployment_id,
            date,
            str(devices_count),
            status,
            result,
            duration,
            user
        ]

        for col, value in enumerate(values):
            item = QTableWidgetItem(str(value))
            item.setTextAlignment(Qt.AlignCenter)
            self.history_table.setItem(row, col, item)

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

    def export_logs(self):
        path, _ = QFileDialog.getSaveFileName(
            self,
            "Exporter logs",
            f"deploy_vlan_vlsm_logs_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt",
            "Text Files (*.txt)"
        )

        if not path:
            return

        with open(path, "w", encoding="utf-8") as f:
            f.write(self.logs_box.toPlainText())

        self.add_log("SUCCESS", f"Logs exportés : {path}")

    def show_full_config(self):
        QMessageBox.information(self, "Configuration complète", self.generated_config or "Vide")

    def show_history(self):
        QMessageBox.information(
            self,
            "Historique",
            f"Nombre de déploiements : {self.history_table.rowCount()}"
        )

    def add_manual_device(self):
        QMessageBox.information(
            self,
            "Saisie manuelle",
            "La saisie manuelle peut être ajoutée plus tard avec une fenêtre dédiée."
        )

    def remove_selected_devices(self):
        for row in reversed(range(self.devices_table.rowCount())):
            check = self.devices_table.item(row, 0)
            if check and check.checkState() == Qt.Checked:
                self.devices_table.removeRow(row)

        self.update_selected_count()

    def apply_style(self):
        self.setStyleSheet("""
            QWidget {
                background-color: #06111f;
                color: #EAF1FF;
                font-family: Segoe UI;
                font-size: 12px;
            }

            QLabel#pageTitle {
                font-size: 22px;
                font-weight: 900;
                color: white;
            }

            QLabel#subtitle {
                color: #9DAEC8;
            }

            QLabel#cardTitle {
                font-size: 13px;
                font-weight: 900;
                color: #60a5fa;
            }

            QLabel#smallTitle {
                color: #C5D2E8;
                font-weight: 700;
            }

            QLabel#statValue {
                font-size: 18px;
                font-weight: 900;
                color: white;
            }

            QLabel#stepActive {
                background-color: #0A192B;
                border: 1px solid #2563eb;
                border-bottom: 3px solid #8b5cf6;
                border-radius: 12px;
                color: white;
                font-weight: 800;
            }

            QLabel#stepIdle {
                background-color: #081525;
                border: 1px solid #243D5C;
                border-radius: 12px;
                color: #94a3b8;
                font-weight: 800;
            }

            QFrame#card {
                background-color: #0A192B;
                border: 1px solid #1C3352;
                border-radius: 14px;
            }

            QFrame#transparent {
                background: transparent;
                border: none;
            }

            QTextEdit#cliBox, QTextEdit#logsBox {
                background-color: #081525;
                border: 1px solid #243D5C;
                border-radius: 10px;
                color: #B6FCD5;
                font-family: Consolas;
                font-size: 12px;
            }

            QPushButton {
                background-color: #2563eb;
                border: none;
                border-radius: 9px;
                padding: 7px 12px;
                color: white;
                font-weight: 800;
            }

            QPushButton:hover {
                background-color: #1d4ed8;
            }

            QPushButton#darkBtn {
                background-color: #0D1A2C;
                border: 1px solid #2B4262;
            }

            QPushButton#blueBtn {
                background-color: #2563eb;
            }

            QPushButton#dangerBtn {
                background-color: #3b1111;
                color: #ef4444;
                border: 1px solid #7f1d1d;
            }

            QPushButton#deployBtn {
                background-color: #16a34a;
                font-size: 13px;
            }

            QPushButton#deployBtn:hover {
                background-color: #22c55e;
            }

            QTableWidget {
                background-color: #081525;
                border: 1px solid #243D5C;
                border-radius: 10px;
                gridline-color: #1E3552;
                color: white;
            }

            QHeaderView::section {
                background-color: #101F35;
                color: #C8D5EA;
                padding: 5px;
                border: none;
                font-weight: 800;
            }

            QScrollBar:vertical {
                background: #081525;
                width: 14px;
                margin: 0px;
                border-radius: 7px;
            }

            QScrollBar::handle:vertical {
                background: #334155;
                min-height: 40px;
                border-radius: 7px;
            }

            QScrollBar::handle:vertical:hover {
                background: #475569;
            }

            QScrollBar::add-line:vertical,
            QScrollBar::sub-line:vertical {
                height: 0px;
                background: none;
                border: none;
            }

            QScrollBar::add-page:vertical,
            QScrollBar::sub-page:vertical {
                background: none;
            }
        """)