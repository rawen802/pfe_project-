import json

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QFrame, QTableWidget, QTableWidgetItem, QLineEdit,
    QComboBox, QHeaderView, QGridLayout, QScrollArea,
    QMessageBox, QFileDialog
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QColor

from services.api_client import ApiClient
from ui.config_generation_page import ConfigGenerationPage


class VlanVlsmPage(QWidget):
    def __init__(self, user_data=None, api_client=None, parent_stack=None):
        super().__init__()
        self.user_data = user_data or {}
        self.api = api_client if api_client else ApiClient()
        self.parent_stack = parent_stack

        self.stat_labels = {}
        self.report_data = None

        self.last_vlsm_rows = []
        self.last_vlan_rows = []
        self.final_plan = []

        self.setup_ui()

    def setup_ui(self):
        self.setStyleSheet("""
            QWidget { background-color: #071426; color: white; font-family: Segoe UI; }
            QLabel { background: transparent; }
            QLabel#Title { font-size: 30px; font-weight: bold; color: white; }
            QLabel#Subtitle { color: #8fb3d9; font-size: 14px; }
            QLabel#SectionTitle { color: #22c7ff; font-size: 19px; font-weight: bold; }

            QFrame.Card {
                background-color: #123052;
                border: 1px solid #2A5D91;
                border-radius: 10px;
            }

            QFrame.GreenCard {
                background-color: #123052;
                border: 1px solid #22C55E;
                border-radius: 10px;
            }

            QFrame.BlueCard {
                background-color: #123052;
                border: 1px solid #3B82F6;
                border-radius: 10px;
            }

            QLineEdit, QComboBox {
                background-color: #163B63;
                border: 1px solid #2A5D91;
                border-radius: 6px;
                padding: 8px;
                color: white;
                min-height: 22px;
            }

            QPushButton {
                border: none;
                border-radius: 7px;
                padding: 9px 14px;
                font-weight: bold;
                color: white;
            }

            QPushButton#BlueBtn { background-color: #2563eb; }
            QPushButton#GreenBtn { background-color: #16a34a; }
            QPushButton#PurpleBtn { background-color: #7c3aed; }

            QTableWidget {
                background-color: #10233F;
                border: 1px solid #2A5D91;
                border-radius: 6px;
                gridline-color: #2A5D91;
                color: white;
            }

            QHeaderView::section {
                background-color: #163B63;
                color: #22c7ff;
                padding: 8px;
                border: none;
                font-weight: bold;
            }
        """)

        root_layout = QVBoxLayout(self)
        root_layout.setContentsMargins(0, 0, 0, 0)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)

        container = QWidget()
        main_layout = QVBoxLayout(container)
        main_layout.setContentsMargins(22, 22, 22, 22)
        main_layout.setSpacing(16)

        scroll.setWidget(container)
        root_layout.addWidget(scroll)

        header = QHBoxLayout()

        title_box = QVBoxLayout()
        title = QLabel("VLAN / VLSM Planner")
        title.setObjectName("Title")

        subtitle = QLabel("Planification intelligente basée sur le rapport d’architecture réseau")
        subtitle.setObjectName("Subtitle")

        title_box.addWidget(title)
        title_box.addWidget(subtitle)

        btn_load = QPushButton("Charger le rapport découvert")
        btn_load.setObjectName("BlueBtn")
        btn_load.clicked.connect(self.load_architecture_report)

        header.addLayout(title_box)
        header.addStretch()
        header.addWidget(btn_load)
        main_layout.addLayout(header)

        top_grid = QGridLayout()
        top_grid.setSpacing(12)

        top_grid.addWidget(self.make_report_card(), 0, 0)
        top_grid.addWidget(self.make_stat_card("vlans", "VLANs existants", "0", "Actifs"), 0, 1)
        top_grid.addWidget(self.make_stat_card("zones", "Zones existantes", "0", "Détectées"), 0, 2)
        top_grid.addWidget(self.make_stat_card("subnets", "Sous-réseaux utilisés", "0", "Détectés"), 0, 3)
        top_grid.addWidget(self.make_stat_card("switches", "Switches détectés", "0", "Équipements"), 0, 4)
        top_grid.addWidget(self.make_stat_card("trunks", "Interfaces trunk", "0", "Actives"), 0, 5)

        main_layout.addLayout(top_grid)

        section1 = QLabel("1. Ressources existantes extraites du rapport")
        section1.setObjectName("SectionTitle")
        main_layout.addWidget(section1)

        existing_grid = QGridLayout()
        existing_grid.setSpacing(12)

        self.existing_vlan_table = self.create_empty_table(["VLAN ID", "Nom VLAN", "Zone", "Statut"], 210)
        self.existing_subnet_table = self.create_empty_table(["Sous-réseau", "Masque", "Zone", "Utilisation"], 210)
        self.existing_zone_table = self.create_empty_table(["Zone", "Type", "Description"], 210)
        self.switch_table = self.create_empty_table(["Type", "Nom équipement", "Rôle"], 210)

        existing_grid.addWidget(self.wrap_table("VLANs existants", self.existing_vlan_table), 0, 0)
        existing_grid.addWidget(self.wrap_table("Sous-réseaux existants", self.existing_subnet_table), 0, 1)
        existing_grid.addWidget(self.wrap_table("Zones existantes", self.existing_zone_table), 0, 2)
        existing_grid.addWidget(self.wrap_table("Switches détectés", self.switch_table), 0, 3)

        main_layout.addLayout(existing_grid)

        section2 = QLabel("2. Demandes utilisateur")
        section2.setObjectName("SectionTitle")
        main_layout.addWidget(section2)

        request_grid = QGridLayout()
        request_grid.setSpacing(12)
        request_grid.addWidget(self.make_vlsm_request_card(), 0, 0)
        request_grid.addWidget(self.make_vlan_request_card(), 0, 1)
        main_layout.addLayout(request_grid)

        section3 = QLabel("3. Résultats générés")
        section3.setObjectName("SectionTitle")
        main_layout.addWidget(section3)

        self.vlsm_result_table = self.create_empty_table(
            ["#", "Zone", "VLAN ID", "Sous-réseau", "Masque", "Passerelle", "Broadcast", "Statut"], 210
        )
        main_layout.addWidget(self.wrap_table("Résultats VLSM", self.vlsm_result_table, green=True))

        self.vlan_result_table = self.create_empty_table(
            ["#", "Zone", "VLAN ID", "Nom VLAN", "Switches", "SVI", "Trunk", "Statut"], 210
        )
        main_layout.addWidget(self.wrap_table("Résultats VLAN", self.vlan_result_table, blue=True))

        self.final_plan_table = self.create_empty_table(
            ["#", "Site/LAN", "Zone", "VLAN ID", "Nom VLAN", "Subnet", "Masque", "Gateway", "Switches", "SVI", "Trunk", "Statut"],
            230
        )
        main_layout.addWidget(self.wrap_table("Plan final VLAN / VLSM", self.final_plan_table, blue=True))

        actions = QHBoxLayout()
        actions.addStretch()

        self.btn_generate_config = QPushButton("Générer configuration Cisco")
        self.btn_generate_config.setObjectName("PurpleBtn")
        self.btn_generate_config.clicked.connect(self.go_to_config_page)

        self.btn_export_vlan_vlsm = QPushButton("Exporter le plan VLAN/VLSM")
        self.btn_export_vlan_vlsm.setObjectName("BlueBtn")
        self.btn_export_vlan_vlsm.clicked.connect(self.export_vlan_vlsm_plan)

        actions.addWidget(self.btn_generate_config)
        actions.addWidget(self.btn_export_vlan_vlsm)

        main_layout.addLayout(actions)

    def export_vlan_vlsm_plan(self):
        if not self.final_plan:
            QMessageBox.warning(self, "Plan vide", "Aucun plan VLAN/VLSM à exporter.")
            return

        path, _ = QFileDialog.getSaveFileName(
            self,
            "Exporter le plan VLAN/VLSM",
            "plan_vlan_vlsm.json",
            "JSON Files (*.json);;Text Files (*.txt)"
        )

        if not path:
            return

        try:
            with open(path, "w", encoding="utf-8") as file:
                json.dump(self.final_plan, file, indent=4, ensure_ascii=False)

            QMessageBox.information(self, "Export réussi", f"Plan exporté :\n{path}")

        except Exception as e:
            QMessageBox.critical(self, "Erreur export", f"Impossible d'exporter le plan :\n{e}")

    def go_to_config_page(self):
        if not self.final_plan:
            QMessageBox.warning(
                self,
                "Plan final vide",
                "Génère d’abord le plan final VLAN/VLSM avant de passer à la configuration."
            )
            return

        base_network = self.base_network_input.text().strip()

        if not base_network:
            QMessageBox.warning(self, "Réseau manquant", "Le réseau principal est vide.")
            return

        config_page = ConfigGenerationPage(
            final_plan=self.final_plan,
            base_network=base_network,
            report=self.report_data or {},
            parent_stack=self.parent_stack,
            api_client=self.api
        )

        if self.parent_stack:
            self.parent_stack.addWidget(config_page)
            self.parent_stack.setCurrentWidget(config_page)
        else:
            self.config_window = config_page
            self.config_window.resize(1300, 800)
            self.config_window.show()

    def make_report_card(self):
        card = QFrame()
        card.setProperty("class", "Card")
        layout = QVBoxLayout(card)

        title = QLabel("Rapport chargé")
        title.setStyleSheet("font-weight: bold; color: white;")

        self.report_label = QLabel("Aucun rapport chargé")
        self.report_label.setStyleSheet("""
            background-color: #163B63;
            border: 1px solid #2A5D91;
            border-radius: 8px;
            padding: 10px;
            color: #b9d5ff;
        """)

        layout.addWidget(title)
        layout.addWidget(self.report_label)
        return card

    def make_stat_card(self, key, title, value, desc):
        card = QFrame()
        card.setProperty("class", "Card")
        layout = QVBoxLayout(card)

        lbl_title = QLabel(title)
        lbl_title.setStyleSheet("color: white; font-weight: bold;")

        lbl_value = QLabel(str(value))
        lbl_value.setStyleSheet("color: #22c7ff; font-size: 30px; font-weight: bold;")

        lbl_desc = QLabel(desc)
        lbl_desc.setStyleSheet("color: #8fb3d9;")

        self.stat_labels[key] = lbl_value

        layout.addWidget(lbl_title)
        layout.addWidget(lbl_value)
        layout.addWidget(lbl_desc)

        return card

    def style_table(self, table, rows_count=0, min_height=190):
        table.verticalHeader().setVisible(False)
        table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        table.setAlternatingRowColors(False)
        table.setShowGrid(True)
        table.setSelectionBehavior(QTableWidget.SelectRows)
        table.setEditTriggers(QTableWidget.NoEditTriggers)
        table.setMinimumHeight(min_height)

        for i in range(rows_count):
            table.setRowHeight(i, 34)

    def create_empty_table(self, headers, min_height=190):
        table = QTableWidget()
        table.setColumnCount(len(headers))
        table.setHorizontalHeaderLabels(headers)
        table.setRowCount(0)
        self.style_table(table, 0, min_height)
        return table

    def wrap_table(self, title, table, green=False, blue=False):
        card = QFrame()

        if green:
            card.setProperty("class", "GreenCard")
        elif blue:
            card.setProperty("class", "BlueCard")
        else:
            card.setProperty("class", "Card")

        layout = QVBoxLayout(card)

        lbl = QLabel(title)
        lbl.setStyleSheet("font-weight: bold; color: white;")

        layout.addWidget(lbl)
        layout.addWidget(table)

        return card

    def clear_table(self, table):
        table.setRowCount(0)

    def add_row_to_table(self, table, values):
        row = table.rowCount()
        table.insertRow(row)
        table.setRowHeight(row, 34)

        for col, value in enumerate(values):
            item = QTableWidgetItem(str(value))
            item.setTextAlignment(Qt.AlignCenter)

            value_str = str(value)
            if value_str in ["Actif", "Alloué", "Prêt", "OK", "success", "planned", "created", "ready", "create"]:
                item.setForeground(QColor("#22c55e"))
            elif value_str in ["Déjà existant", "Non alloué", "Erreur", "Conflit", "failed"]:
                item.setForeground(QColor("#ef4444"))
            elif value_str in ["waiting_vlsm", "waiting_vlan"]:
                item.setForeground(QColor("#f59e0b"))

            table.setItem(row, col, item)

    def make_vlsm_request_card(self):
        card = QFrame()
        card.setProperty("class", "GreenCard")
        layout = QVBoxLayout(card)

        title = QLabel(" Génération VLSM")
        title.setStyleSheet("color: #22c55e; font-size: 16px; font-weight: bold;")
        layout.addWidget(title)

        line = QHBoxLayout()

        self.base_network_input = QLineEdit()
        self.base_network_input.setPlaceholderText("Réseau de base : 192.168.100.0/24")

        self.zone_vlsm_input = QLineEdit()
        self.zone_vlsm_input.setPlaceholderText("Zone à créer")

        self.hosts_input = QLineEdit()
        self.hosts_input.setPlaceholderText("Nombre d’hôtes requis")

        btn_generate = QPushButton("Générer le plan VLSM")
        btn_generate.setObjectName("GreenBtn")
        btn_generate.clicked.connect(self.generate_vlsm)

        line.addWidget(self.base_network_input)
        line.addWidget(self.zone_vlsm_input)
        line.addWidget(self.hosts_input)
        line.addWidget(btn_generate)

        layout.addLayout(line)
        return card

    def make_vlan_request_card(self):
        card = QFrame()
        card.setProperty("class", "BlueCard")
        layout = QVBoxLayout(card)

        title = QLabel("Création VLAN")
        title.setStyleSheet("color: #22c7ff; font-size: 16px; font-weight: bold;")
        layout.addWidget(title)

        line = QHBoxLayout()

        self.zone_vlan_input = QLineEdit()
        self.zone_vlan_input.setPlaceholderText("Zone métier")

        self.vlan_name_input = QLineEdit()
        self.vlan_name_input.setPlaceholderText("Nom VLAN (optionnel)")

        self.vlan_id_combo = QComboBox()
        self.vlan_id_combo.addItems(["Auto", "Manuel"])

        self.switch_combo = QComboBox()
        self.switch_combo.addItem("Sélectionner")

        btn_generate = QPushButton("Générer les VLANs")
        btn_generate.setObjectName("BlueBtn")
        btn_generate.clicked.connect(self.generate_vlan)

        line.addWidget(self.zone_vlan_input)
        line.addWidget(self.vlan_name_input)
        line.addWidget(self.vlan_id_combo)
        line.addWidget(self.switch_combo)
        line.addWidget(btn_generate)

        layout.addLayout(line)
        return card

    def set_report_data(self, report):
        if not isinstance(report, dict):
            QMessageBox.warning(self, "Rapport invalide", "Le rapport reçu n’est pas valide.")
            return

        self.report_data = report
        self.populate_from_report(report)

    def load_architecture_report(self):
        if not self.report_data:
            QMessageBox.warning(
                self,
                "Aucun rapport disponible",
                "Lance d’abord la découverte réseau."
            )
            return

        self.populate_from_report(self.report_data)
        QMessageBox.information(self, "Succès", "Rapport chargé depuis la découverte réseau.")

    def populate_from_report(self, report):
        network_context = report.get("network_context", {})
        topology = report.get("topology", {})

        vlans = network_context.get("vlans", [])
        subnets = network_context.get("subnets", [])
        zones = network_context.get("zones", [])
        trunks = network_context.get("trunks", [])
        devices = topology.get("devices", report.get("devices", []))

        self.clear_table(self.existing_vlan_table)
        self.clear_table(self.existing_subnet_table)
        self.clear_table(self.existing_zone_table)
        self.clear_table(self.switch_table)

        for vlan in vlans:
            self.add_row_to_table(self.existing_vlan_table, [
                vlan.get("vlan_id", vlan.get("id", "-")),
                vlan.get("vlan_name", vlan.get("name", "-")),
                vlan.get("zone", vlan.get("zone_name", "-")),
                vlan.get("status", "Actif")
            ])

        for subnet in subnets:
            self.add_row_to_table(self.existing_subnet_table, [
                subnet.get("subnet", subnet.get("network", "-")),
                subnet.get("mask", subnet.get("prefix", "-")),
                subnet.get("zone", subnet.get("zone_name", "-")),
                subnet.get("usage", subnet.get("utilization", "-"))
            ])

        for zone_item in zones:
            self.add_row_to_table(self.existing_zone_table, [
                zone_item.get("zone_name", zone_item.get("name", "-")),
                zone_item.get("type", "-"),
                zone_item.get("description", "-")
            ])

        self.switch_combo.clear()
        self.switch_combo.addItem("Sélectionner")

        for device in devices:
            hostname = device.get("hostname", device.get("name", "-"))
            role = device.get("role", "-")
            device_type = device.get("type", device.get("model", "-"))

            self.add_row_to_table(self.switch_table, [device_type, hostname, role])

            if hostname != "-":
                self.switch_combo.addItem(hostname)

        report_name = (
            report.get("report_name")
            or report.get("site_name")
            or report.get("name")
            or report.get("site", {}).get("site_name")
            or "Rapport architecture"
        )

        self.report_label.setText(f"{report_name}\nRapport reçu depuis le module Découverte Réseau")

        self.update_stats(
            vlan_count=len(vlans),
            zone_count=len(zones),
            subnet_count=len(subnets),
            switch_count=len(devices),
            trunk_count=len(trunks)
        )

    def update_stats(self, vlan_count, zone_count, subnet_count, switch_count, trunk_count):
        self.stat_labels["vlans"].setText(str(vlan_count))
        self.stat_labels["zones"].setText(str(zone_count))
        self.stat_labels["subnets"].setText(str(subnet_count))
        self.stat_labels["switches"].setText(str(switch_count))
        self.stat_labels["trunks"].setText(str(trunk_count))

    def extract_vlsm_rows(self, data):
        if isinstance(data, list):
            return data

        if not isinstance(data, dict):
            return []

        if isinstance(data.get("planned_subnets"), list):
            return data.get("planned_subnets")

        if isinstance(data.get("vlsm"), dict):
            vlsm = data.get("vlsm")
            if isinstance(vlsm.get("planned_subnets"), list):
                return vlsm.get("planned_subnets")

        if isinstance(data.get("data"), dict):
            nested = data.get("data")
            if isinstance(nested.get("planned_subnets"), list):
                return nested.get("planned_subnets")

            if isinstance(nested.get("vlsm"), dict):
                vlsm = nested.get("vlsm")
                if isinstance(vlsm.get("planned_subnets"), list):
                    return vlsm.get("planned_subnets")

        for key in ["allocations", "subnets", "allocated_subnets", "generated_subnets", "results", "result"]:
            value = data.get(key)
            if isinstance(value, list):
                return value

        return []

    def extract_skipped_vlsm(self, data):
        if not isinstance(data, dict):
            return []

        if isinstance(data.get("skipped_zones"), list):
            return data.get("skipped_zones")

        if isinstance(data.get("vlsm"), dict):
            skipped = data.get("vlsm", {}).get("skipped_zones", [])
            if isinstance(skipped, list):
                return skipped

        return []

    def extract_vlan_rows(self, data):
        if isinstance(data, list):
            return data

        if not isinstance(data, dict):
            return []

        vlan_result = data.get("vlan_result")
        if isinstance(vlan_result, dict):
            created = vlan_result.get("created", [])
            if isinstance(created, list):
                return created

        for key in ["created", "vlans", "created_vlans", "planned_vlans", "generated_vlans", "results", "data", "result"]:
            value = data.get(key)
            if isinstance(value, list):
                return value

        vlan_data = data.get("vlan")
        if isinstance(vlan_data, dict):
            return [vlan_data]

        return []

    def list_hostnames(self, devices):
        if not isinstance(devices, list):
            return "-"

        names = []
        for dev in devices:
            if isinstance(dev, dict):
                hostname = dev.get("hostname") or dev.get("name")
                if hostname:
                    names.append(hostname)

        return ", ".join(names) if names else "-"

    def get_site_name(self):
        if not self.report_data:
            return "LAN"

        return (
            self.report_data.get("site", {}).get("site_name")
            or self.report_data.get("site_name")
            or self.report_data.get("name")
            or "LAN"
        )

    def build_final_plan(self):
        self.final_plan = []

        if not hasattr(self, "final_plan_table"):
            return

        self.clear_table(self.final_plan_table)

        if not self.last_vlan_rows:
            return

        site_name = self.get_site_name()

        for vlan in self.last_vlan_rows:
            if not isinstance(vlan, dict):
                continue

            vlan_zone = vlan.get("zone_name") or vlan.get("zone") or "-"
            vlan_name = vlan.get("vlan_name") or vlan.get("name") or vlan_zone
            vlan_id = vlan.get("vlan_id") or vlan.get("id") or "-"

            matching_vlsm = None

            for vlsm in self.last_vlsm_rows:
                if not isinstance(vlsm, dict):
                    continue

                vlsm_name = vlsm.get("departement") or vlsm.get("zone_name") or vlsm.get("zone") or "-"
                vlsm_vlan_id = vlsm.get("vlan_id") or vlsm.get("id") or "-"

                if str(vlsm_vlan_id) == str(vlan_id):
                    matching_vlsm = vlsm
                    break

                if str(vlsm_name).lower() == str(vlan_name).lower():
                    matching_vlsm = vlsm
                    break

                if str(vlsm_name).lower() == str(vlan_zone).lower():
                    matching_vlsm = vlsm
                    break

            switches = self.list_hostnames(vlan.get("deploy_on", []))
            svi = self.list_hostnames(vlan.get("core_switches", []))

            if switches == "-" and svi != "-":
                switches = svi

            trunk = "Oui" if vlan.get("needs_trunk_update") else "Non"

            item = {
                "site": site_name,
                "zone": vlan_zone,
                "vlan_id": vlan_id,
                "vlan_name": vlan_name,
                "subnet": matching_vlsm.get("subnet", "-") if matching_vlsm else "-",
                "mask": matching_vlsm.get("mask", "-") if matching_vlsm else "-",
                "gateway": matching_vlsm.get("gateway", "-") if matching_vlsm else "-",
                "switches": switches,
                "svi": svi,
                "trunk": trunk,
                "status": "ready" if matching_vlsm else "waiting_vlsm"
            }

            self.final_plan.append(item)

        for i, item in enumerate(self.final_plan, start=1):
            self.add_row_to_table(self.final_plan_table, [
                i, item["site"], item["zone"], item["vlan_id"], item["vlan_name"],
                item["subnet"], item["mask"], item["gateway"], item["switches"],
                item["svi"], item["trunk"], item["status"]
            ])

    def update_report_after_vlan(self, rows):
        if not isinstance(self.report_data, dict):
            return

        network_context = self.report_data.setdefault("network_context", {})
        vlans = network_context.setdefault("vlans", [])
        zones = network_context.setdefault("zones", [])

        existing_pairs = {
            (
                v.get("zone") or v.get("zone_name"),
                v.get("vlan_name") or v.get("name")
            )
            for v in vlans
            if isinstance(v, dict)
        }

        existing_zone_names = {
            z.get("zone_name") or z.get("name")
            for z in zones
            if isinstance(z, dict)
        }

        for item in rows:
            if not isinstance(item, dict):
                continue

            vlan_id = item.get("vlan_id") or item.get("id")
            zone_name = item.get("zone_name") or item.get("zone")
            vlan_name = item.get("vlan_name") or item.get("name") or zone_name

            if not zone_name:
                continue

            pair = (zone_name, vlan_name)

            if pair not in existing_pairs:
                vlans.append({
                    "vlan_id": vlan_id,
                    "vlan_name": vlan_name,
                    "zone": zone_name,
                    "zone_name": zone_name,
                    "status": "Actif"
                })
                existing_pairs.add(pair)

            if zone_name not in existing_zone_names:
                zones.append({
                    "zone_name": zone_name,
                    "type": "Métier",
                    "description": "Zone générée automatiquement"
                })
                existing_zone_names.add(zone_name)

        self.update_stats(
            vlan_count=len(vlans),
            zone_count=len(zones),
            subnet_count=len(network_context.get("subnets", [])),
            switch_count=len(self.report_data.get("topology", {}).get("devices", [])),
            trunk_count=len(network_context.get("trunks", []))
        )

    def update_report_after_vlsm(self, rows):
        if not isinstance(self.report_data, dict):
            return

        network_context = self.report_data.setdefault("network_context", {})
        subnets = network_context.setdefault("subnets", [])

        existing_subnets = {
            item.get("subnet")
            for item in subnets
            if isinstance(item, dict)
        }

        for item in rows:
            if not isinstance(item, dict):
                continue

            if item.get("status") == "failed":
                continue

            subnet = item.get("subnet") or item.get("network")
            if not subnet or subnet in existing_subnets:
                continue

            zone_name = item.get("departement") or item.get("zone_name") or item.get("zone") or "-"

            subnets.append({
                "subnet": subnet,
                "mask": item.get("mask", "-"),
                "zone": zone_name,
                "zone_name": zone_name,
                "gateway": item.get("gateway", "-"),
                "broadcast": item.get("broadcast", "-"),
                "usage": f"{item.get('usable_hosts', '-')} hosts",
                "status": item.get("status", "planned")
            })

            existing_subnets.add(subnet)

        self.update_stats(
            vlan_count=len(network_context.get("vlans", [])),
            zone_count=len(network_context.get("zones", [])),
            subnet_count=len(network_context.get("subnets", [])),
            switch_count=len(self.report_data.get("topology", {}).get("devices", [])),
            trunk_count=len(network_context.get("trunks", []))
        )

        self.populate_from_report(self.report_data)

    def generate_vlsm(self):
        base_network = self.base_network_input.text().strip()
        zone = self.zone_vlsm_input.text().strip()
        hosts = self.hosts_input.text().strip()

        if not self.report_data:
            QMessageBox.warning(self, "Rapport manquant", "Charge d’abord un rapport depuis le module Découverte Réseau.")
            return

        if not base_network or not zone or not hosts:
            QMessageBox.warning(self, "Champs manquants", "Veuillez remplir le réseau, la zone et le nombre d’hôtes.")
            return

        if "/" not in base_network:
            QMessageBox.warning(self, "Réseau invalide", "Format attendu : 192.168.1.0/24")
            return

        try:
            hosts = int(hosts)
        except ValueError:
            QMessageBox.warning(self, "Erreur", "Le nombre d’hôtes doit être un entier.")
            return

        requirements = [
            {
                "zone_name": zone,
                "required_hosts": hosts
            }
        ]

        payload = {
            "user_id": self.user_data.get("id", 0),
            "report": self.report_data,
            "base_network": base_network,
            "requirements": requirements
        }

        result = self.api.generate_vlsm(payload)

        if not result.get("success"):
            QMessageBox.critical(self, "Erreur backend", result.get("error", "Erreur inconnue"))
            return

        data = result.get("data", {})

        print("=== VLSM BACKEND RESPONSE ===")
        try:
            print(json.dumps(data, indent=2, ensure_ascii=False))
        except Exception:
            print(data)
        print("============================")

        rows = self.extract_vlsm_rows(data)
        skipped = self.extract_skipped_vlsm(data)

        self.clear_table(self.vlsm_result_table)

        if not rows:
            if skipped:
                reason = "\n".join(
                    f"- {item.get('zone_name', '-')}: {item.get('reason', '-')}"
                    for item in skipped
                    if isinstance(item, dict)
                )

                QMessageBox.information(
                    self,
                    "Zone déjà planifiée",
                    "Aucun nouveau sous-réseau VLSM créé.\n\n"
                    f"{reason}\n\n"
                    "Choisis une autre zone : ADMIN, MEDICAL, SERVER, etc."
                )
            else:
                QMessageBox.warning(
                    self,
                    "Résultat vide",
                    "Aucun sous-réseau VLSM retourné."
                )

            return

        self.last_vlsm_rows.extend(rows)
        self.update_report_after_vlsm(rows)
        self.build_final_plan()

        for i, item in enumerate(rows, start=1):
            if not isinstance(item, dict):
                continue

            self.add_row_to_table(self.vlsm_result_table, [
                i,
                item.get("departement") or item.get("zone_name") or item.get("zone") or zone,
                item.get("id") or item.get("vlan_id") or "-",
                item.get("subnet") or item.get("network") or "-",
                item.get("mask") or item.get("prefix") or "-",
                item.get("gateway") or item.get("passerelle") or "-",
                item.get("broadcast") or "-",
                item.get("status") or item.get("statut") or "planned"
            ])

        failed_rows = [
            item for item in rows
            if isinstance(item, dict) and item.get("status") == "failed"
        ]

        if failed_rows:
            failed_names = ", ".join(
                item.get("departement") or item.get("zone_name") or item.get("zone") or "-"
                for item in failed_rows
            )

            QMessageBox.warning(
                self,
                "Réseau saturé",
                f"Impossible d'allouer un sous-réseau pour : {failed_names}\n\n"
                f"Le réseau {base_network} est probablement saturé.\n\n"
                "Solutions recommandées :\n"
                "- Utiliser un réseau plus grand, exemple : 192.168.3.0/23\n"
                "- ou réduire le nombre d'hôtes demandés par VLAN."
            )
        else:
            QMessageBox.information(self, "Succès", "Plan VLSM généré avec succès.")

    def generate_vlan(self):
        zone = self.zone_vlan_input.text().strip()
        vlan_name = self.vlan_name_input.text().strip()
        selected_switch = self.switch_combo.currentText().strip()

        if not self.report_data:
            QMessageBox.warning(self, "Rapport manquant", "Charge d’abord un rapport depuis le module Découverte Réseau.")
            return

        if not zone:
            QMessageBox.warning(self, "Champ manquant", "Veuillez entrer le nom de la zone.")
            return

        if selected_switch == "Sélectionner" or not selected_switch:
            QMessageBox.warning(
                self,
                "Switch manquant",
                "Veuillez sélectionner le switch cible pour créer le VLAN."
            )
            return

        if not vlan_name:
            vlan_name = zone

        def find_device_by_hostname(hostname):
            devices = self.report_data.get("topology", {}).get("devices", [])
            if not isinstance(devices, list):
                devices = []

            for dev in devices:
                if not isinstance(dev, dict):
                    continue

                dev_hostname = dev.get("hostname") or dev.get("name")
                if dev_hostname == hostname:
                    return dev

            return {
                "hostname": hostname,
                "role": "ACCESS_SWITCH",
                "trunks": []
            }

        def find_core_switch():
            devices = self.report_data.get("topology", {}).get("devices", [])
            if not isinstance(devices, list):
                devices = []

            for dev in devices:
                if not isinstance(dev, dict):
                    continue

                role = str(dev.get("role", "")).upper()
                hostname = dev.get("hostname") or dev.get("name")

                if role in ["SITE_CORE", "CORE", "CORE_SWITCH", "L3_SWITCH"] and hostname:
                    return dev

            for dev in devices:
                if not isinstance(dev, dict):
                    continue

                hostname = dev.get("hostname") or dev.get("name")
                if hostname and "CORE" in hostname.upper():
                    return dev

            return {
                "hostname": "SW-CORE",
                "role": "SITE_CORE",
                "trunks": []
            }

        payload = {
            "report": self.report_data,
            "requested_zones": [
                {
                    "zone_name": zone,
                    "vlan_name": vlan_name,
                    "required_hosts": 50,
                    "target_switch": selected_switch
                }
            ]
        }

        print("=== VLAN REQUEST PAYLOAD ===")
        try:
            print(json.dumps(payload, indent=2, ensure_ascii=False))
        except Exception:
            print(payload)
        print("============================")

        result = self.api.generate_vlans(payload)

        if not result.get("success"):
            QMessageBox.critical(self, "Erreur backend", result.get("error", "Erreur inconnue"))
            return

        data = result.get("data", {})
        rows = self.extract_vlan_rows(data)

        if not rows:
            QMessageBox.warning(
                self,
                "Résultat vide",
                "Aucun VLAN créé. Vérifie si la zone existe déjà ou si le backend a retourné skipped/errors."
            )
            return

        selected_device = find_device_by_hostname(selected_switch)
        core_device = find_core_switch()

        selected_role = selected_device.get("role") or "ACCESS_SWITCH"
        core_role = core_device.get("role") or "SITE_CORE"
        core_hostname = core_device.get("hostname") or core_device.get("name") or "SW-CORE"

        # Correction locale importante : même si le backend retourne plusieurs switches,
        # on force le résultat affiché et le plan final à respecter le switch choisi.
        corrected_rows = []
        for item in rows:
            if not isinstance(item, dict):
                continue

            corrected = dict(item)

            corrected["zone_name"] = corrected.get("zone_name") or corrected.get("zone") or zone
            corrected["vlan_name"] = corrected.get("vlan_name") or corrected.get("name") or vlan_name
            corrected["required_hosts"] = corrected.get("required_hosts") or 50

            corrected["deploy_on"] = [
                {
                    "hostname": selected_switch,
                    "role": selected_role,
                    "trunks": selected_device.get("trunks", [])
                }
            ]

            corrected["core_switches"] = [
                {
                    "hostname": core_hostname,
                    "role": core_role,
                    "trunks": core_device.get("trunks", [])
                }
            ]

            corrected["target_switch"] = selected_switch
            corrected["svi_device"] = core_hostname
            corrected["needs_svi"] = True
            corrected["needs_trunk_update"] = True

            corrected_rows.append(corrected)

        rows = corrected_rows

        print("=== VLAN CORRECTED ROWS ===")
        try:
            print(json.dumps(rows, indent=2, ensure_ascii=False))
        except Exception:
            print(rows)
        print("===========================")

        self.last_vlan_rows.extend(rows)
        self.update_report_after_vlan(rows)
        self.build_final_plan()

        start_index = self.vlan_result_table.rowCount() + 1

        for i, item in enumerate(rows, start=start_index):
            if not isinstance(item, dict):
                continue

            deploy_on = item.get("deploy_on", [])
            core_switches = item.get("core_switches", [])

            switches_list = []
            if isinstance(deploy_on, list):
                for sw in deploy_on:
                    if isinstance(sw, dict):
                        hostname = sw.get("hostname") or sw.get("name")
                        if hostname:
                            switches_list.append(hostname)
            elif isinstance(deploy_on, str):
                switches_list.append(deploy_on)

            core_list = []
            if isinstance(core_switches, list):
                for sw in core_switches:
                    if isinstance(sw, dict):
                        hostname = sw.get("hostname") or sw.get("name")
                        if hostname:
                            core_list.append(hostname)
            elif isinstance(core_switches, str):
                core_list.append(core_switches)

            svi = ", ".join(core_list) if core_list else "Aucun core"

            if switches_list:
                switches = ", ".join(switches_list)
            else:
                switches = selected_switch

            trunk = "Oui" if item.get("needs_trunk_update") else "Non"
            status = item.get("operation") or item.get("status") or item.get("statut") or "create"

            self.add_row_to_table(self.vlan_result_table, [
                i,
                item.get("zone_name") or item.get("zone") or zone,
                item.get("vlan_id") or item.get("id") or "-",
                item.get("vlan_name") or item.get("name") or vlan_name,
                switches,
                svi,
                trunk,
                status
            ])

        QMessageBox.information(self, "Succès", "VLAN généré avec succès.")
