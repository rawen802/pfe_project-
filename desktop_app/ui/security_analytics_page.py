import os
import requests

from PySide6.QtCore import Qt
from PySide6.QtGui import QPixmap
from PySide6.QtWidgets import (
    QWidget, QLabel, QPushButton, QVBoxLayout, QHBoxLayout,
    QFrame, QGridLayout, QTableWidget, QTableWidgetItem
)

from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure


API_URL = os.getenv("API_URL", "http://127.0.0.1:8000")
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


def safe_int(value, default=0):
    try:
        return int(value or default)
    except Exception:
        return default


class SecurityAnalyticsPage(QWidget):
    def __init__(self, user_data=None, api_client=None):
        super().__init__()

        self.user_data = user_data or {}
        self.api_client = api_client
        self.app_state = {}

        self.current_analysis = None
        self.current_report = {}
        self.history_scores = []
        self.component_scores = {}

        self.setup_ui()
        self.load_score_history()
        self.refresh_dashboard()

    def setup_ui(self):
        self.setStyleSheet("""
            QWidget {
                background-color: #071426;
                color: #EAF1FF;
                font-family: Segoe UI;
                font-size: 13px;
            }

            QLabel {
                background: transparent;
            }

            QWidget#titleWidget {
                background: transparent;
                border: none;
            }

            QLabel#iconBox {
                background-color: #123B63;
                border: 1px solid #3BB3FF;
                border-radius: 22px;
                min-width: 44px;
                max-width: 44px;
                min-height: 44px;
                max-height: 44px;
            }

            QFrame#card {
                background-color: #10233F;
                border: 1px solid #1E4F80;
                border-radius: 14px;
            }

            QFrame#card:hover {
                border: 1px solid #3BB3FF;
            }

            QLabel#title {
                font-size: 26px;
                font-weight: 900;
                color: white;
            }

            QLabel#subtitle {
                color: #9DAEC8;
                font-size: 14px;
            }

            QLabel#cardTitle {
                font-size: 16px;
                font-weight: 800;
                color: white;
            }

            QLabel#bigNumber {
                font-size: 28px;
                font-weight: 900;
                color: white;
            }

            QLabel#smallText {
                color: #AAB8D0;
                font-size: 12px;
            }

            QPushButton {
                background-color: #744CFF;
                border: none;
                border-radius: 9px;
                padding: 10px 18px;
                color: white;
                font-weight: 800;
            }

            QPushButton:hover {
                background-color: #8B68FF;
            }

            QTableWidget {
                background-color: #0E2340;
                border: 1px solid #1E4F80;
                border-radius: 10px;
                gridline-color: #1E3552;
                color: white;
            }

            QHeaderView::section {
                background-color: #123052;
                color: #C8D5EA;
                padding: 8px;
                border: none;
                font-weight: 800;
            }
        """)

        root = QVBoxLayout(self)
        root.setContentsMargins(18, 18, 18, 18)
        root.setSpacing(16)

        root.addLayout(self.create_header())

        summary_grid = QGridLayout()
        summary_grid.setSpacing(14)

        self.global_score_label = QLabel("-")
        self.elements_label = QLabel("-")
        self.issues_label = QLabel("-")
        self.critical_label = QLabel("-")
        self.last_analysis_label = QLabel("En attente")

        summary_grid.addWidget(self.create_metric_card("Score de Sécurité Global", self.global_score_label, "/100", "Dernière analyse IA"), 0, 0)
        summary_grid.addWidget(self.create_metric_card("Éléments analysés", self.elements_label, "", "Devices, VLANs, ACLs, liens"), 0, 1)
        summary_grid.addWidget(self.create_metric_card("Problèmes détectés", self.issues_label, "", "Issues retournées par l’IA"), 0, 2)
        summary_grid.addWidget(self.create_metric_card("Risques critiques", self.critical_label, "", "Sévérité HIGH"), 0, 3)
        summary_grid.addWidget(self.create_metric_card("Dernière analyse", self.last_analysis_label, "", "État actuel"), 0, 4)

        root.addLayout(summary_grid)

        charts_grid = QGridLayout()
        charts_grid.setSpacing(14)

        self.component_chart = self.create_chart_card("Niveau de sécurité par composant")
        self.severity_chart = self.create_chart_card("Répartition des problèmes par sévérité")
        self.history_chart = self.create_chart_card("Historique du score global")

        charts_grid.addWidget(self.component_chart["frame"], 0, 0, 1, 2)
        charts_grid.addWidget(self.severity_chart["frame"], 0, 2)
        charts_grid.addWidget(self.history_chart["frame"], 1, 0, 1, 2)
        charts_grid.addWidget(self.create_detail_table_card(), 1, 2)

        root.addLayout(charts_grid)

    def make_icon_label(self, icon_file: str, size: int = 26):
        label = QLabel()
        label.setObjectName("iconBox")
        label.setAlignment(Qt.AlignCenter)

        path = icon_path(icon_file)
        pixmap = QPixmap(path)

        if pixmap.isNull():
            print(f"[ICON ERROR] Icon not found or invalid: {path}")
        else:
            label.setPixmap(pixmap.scaled(size, size, Qt.KeepAspectRatio, Qt.SmoothTransformation))

        return label

    def title_widget(self, text: str, icon_file: str):
        wrapper = QWidget()
        wrapper.setObjectName("titleWidget")

        layout = QHBoxLayout(wrapper)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(12)

        layout.addWidget(self.make_icon_label(icon_file, 26))

        title = QLabel(text)
        title.setObjectName("title")

        layout.addWidget(title)
        layout.addStretch()

        return wrapper

    def create_header(self):
        layout = QHBoxLayout()

        left = QVBoxLayout()

        title = self.title_widget("Security Analytics", "bar-chart.png")
        subtitle = QLabel("Analyse statistique dynamique basée sur les vrais résultats IA et le vrai rapport réseau")
        subtitle.setObjectName("subtitle")

        left.addWidget(title)
        left.addWidget(subtitle)

        self.btn_refresh = QPushButton("Actualiser")
        self.btn_refresh.setFixedWidth(140)
        self.btn_refresh.clicked.connect(self.refresh_from_real_sources)

        layout.addLayout(left)
        layout.addStretch()
        layout.addWidget(self.btn_refresh)

        return layout

    def create_metric_card(self, title, value_label, suffix, subtitle):
        frame = QFrame()
        frame.setObjectName("card")
        frame.setMinimumHeight(135)

        layout = QVBoxLayout(frame)
        layout.setContentsMargins(16, 14, 16, 14)

        t = QLabel(title)
        t.setObjectName("cardTitle")

        value_row = QHBoxLayout()
        value_label.setObjectName("bigNumber")
        value_label.setMinimumWidth(70)
        value_label.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)

        suffix_label = QLabel(suffix)
        suffix_label.setObjectName("smallText")

        value_row.addWidget(value_label)
        value_row.addWidget(suffix_label)
        value_row.addStretch()

        sub = QLabel(subtitle)
        sub.setObjectName("smallText")

        layout.addWidget(t)
        layout.addStretch()
        layout.addLayout(value_row)
        layout.addWidget(sub)

        return frame

    def create_chart_card(self, title):
        frame = QFrame()
        frame.setObjectName("card")

        layout = QVBoxLayout(frame)
        layout.setContentsMargins(16, 14, 16, 14)

        label = QLabel(title)
        label.setObjectName("cardTitle")

        figure = Figure(figsize=(5.6, 3.4))
        canvas = FigureCanvas(figure)

        layout.addWidget(label)
        layout.addWidget(canvas)

        return {"frame": frame, "figure": figure, "canvas": canvas}

    def create_detail_table_card(self):
        frame = QFrame()
        frame.setObjectName("card")

        layout = QVBoxLayout(frame)
        layout.setContentsMargins(16, 14, 16, 14)

        title = QLabel("Détail des problèmes par composant")
        title.setObjectName("cardTitle")

        self.detail_table = QTableWidget()
        self.detail_table.setColumnCount(4)
        self.detail_table.setHorizontalHeaderLabels(["Composant", "Problèmes", "Sévérité max", "Score"])
        self.detail_table.verticalHeader().setVisible(False)
        self.detail_table.horizontalHeader().setStretchLastSection(True)

        layout.addWidget(title)
        layout.addWidget(self.detail_table)

        return frame

    def set_app_state(self, app_state: dict):
        if isinstance(app_state, dict):
            self.app_state = app_state
        self.refresh_from_real_sources()

    def load_discovery_report(self, report: dict):
        self.current_report = self.normalize_report(report)
        self.refresh_dashboard()

    def load_ai_analysis(self, analysis: dict, report: dict = None):
        self.current_analysis = self.normalize_analysis(analysis)

        if report:
            self.current_report = self.normalize_report(report)
        else:
            resolved_report = self.resolve_current_report()
            if resolved_report:
                self.current_report = resolved_report

        if isinstance(self.app_state, dict):
            self.app_state["ai_validation"] = self.current_analysis
            if self.current_report:
                self.app_state["report"] = self.current_report

        self.load_score_history()
        self.refresh_dashboard()

    def refresh_from_real_sources(self):
        if isinstance(self.app_state, dict):
            report = self.app_state.get("report")
            if report:
                self.current_report = self.normalize_report(report)

            possible_analysis = (
                self.app_state.get("ai_validation")
                or self.app_state.get("last_ai_analysis")
                or self.app_state.get("analysis")
                or self.app_state.get("security_analysis")
            )

            if possible_analysis:
                self.current_analysis = self.normalize_analysis(possible_analysis)

        self.load_score_history()
        self.refresh_dashboard()

    def normalize_report(self, report):
        if not isinstance(report, dict):
            return {}

        if isinstance(report.get("data"), dict):
            report = report["data"]

        if isinstance(report.get("report"), dict):
            report = report["report"]

        return report

    def normalize_analysis(self, data):
        if not isinstance(data, dict):
            return None

        if isinstance(data.get("data"), dict):
            nested = data["data"]

            if isinstance(nested.get("analysis"), dict):
                return nested["analysis"]

            if "issues" in nested or "score" in nested or "security_score" in nested:
                return nested

        if isinstance(data.get("analysis"), dict):
            return data["analysis"]

        if "issues" in data or "score" in data or "security_score" in data:
            return data

        return None

    def has_analysis(self):
        return isinstance(self.current_analysis, dict)

    def classify_issue_component(self, issue):
        issue_type = str(issue.get("type", "")).lower()
        description = str(issue.get("description", "")).lower()
        recommended_fix = str(issue.get("recommended_fix", "")).lower()
        affected = str(issue.get("affected_component", issue.get("component", ""))).lower()

        text = f"{issue_type} {description} {recommended_fix} {affected}"

        if "acl" in text or "access-list" in text or "permit" in text or "deny" in text:
            return "ACLs"

        if "vlan" in text or "vlsm" in text or "svi" in text or "gateway" in text or "segmentation" in text:
            return "VLANs"

        if "topology" in text or "link" in text or "trunk" in text or "neighbor" in text:
            return "Topology"

        if "routing" in text or "route" in text or "inter-vlan" in text or "ospf" in text:
            return "Routing"

        if "device" in text or "unreachable" in text or "ssh" in text or "management" in text:
            return "Devices"

        return "Devices"

    def severity_penalty(self, severity):
        severity = str(severity).lower()

        if severity == "high":
            return 25

        if severity == "medium":
            return 15

        return 5

    def compute_component_scores(self):
        if not self.has_analysis():
            return {}

        issues = self.current_analysis.get("issues", []) or []
        ai_score = self.current_analysis.get("security_score", self.current_analysis.get("score", None))

        scores = {
            "VLANs": 100,
            "ACLs": 100,
            "Devices": 100,
            "Topology": 100,
            "Routing": 100,
        }

        for issue in issues:
            if not isinstance(issue, dict):
                continue

            component = self.classify_issue_component(issue)
            severity = issue.get("severity", "low")

            if component in scores:
                scores[component] -= self.severity_penalty(severity)

        for key in scores:
            scores[key] = max(0, min(100, safe_int(scores[key])))

        if ai_score is not None:
            scores["Global"] = max(0, min(100, safe_int(ai_score)))
        else:
            scores["Global"] = safe_int(sum(scores.values()) / len(scores))

        self.component_scores = scores
        return scores

    def resolve_current_report(self):
        """
        Récupère le vrai rapport réseau depuis plusieurs sources possibles.
        Cela évite que Security Analytics affiche 0 éléments quand l'analyse IA
        arrive sans le rapport réseau.
        """
        if isinstance(self.current_report, dict) and self.current_report:
            return self.normalize_report(self.current_report)

        if isinstance(self.app_state, dict):
            report = self.app_state.get("report")
            if isinstance(report, dict) and report:
                return self.normalize_report(report)

        try:
            main_window = self.window()
        except Exception:
            main_window = None

        if main_window is not None:
            for attr in ["app_state", "shared_state", "state"]:
                state = getattr(main_window, attr, None)
                if isinstance(state, dict):
                    report = state.get("report")
                    if isinstance(report, dict) and report:
                        return self.normalize_report(report)

            for page_name in [
                "page_ai_analysis",
                "ai_analysis_page",
                "page_ai",
                "ai_page",
                "page_discovery",
                "discovery_page",
                "page_discovery_network",
            ]:
                page = getattr(main_window, page_name, None)
                if page is None:
                    continue

                if hasattr(page, "get_current_report"):
                    try:
                        report = page.get_current_report()
                        if isinstance(report, dict) and report:
                            return self.normalize_report(report)
                    except Exception:
                        pass

                for attr in ["discovery_report", "current_report", "report"]:
                    report = getattr(page, attr, None)
                    if isinstance(report, dict) and report:
                        return self.normalize_report(report)

                state = getattr(page, "app_state", None)
                if isinstance(state, dict):
                    report = state.get("report")
                    if isinstance(report, dict) and report:
                        return self.normalize_report(report)

        return {}

    def refresh_dashboard(self):
        resolved_report = self.resolve_current_report()
        if resolved_report:
            self.current_report = resolved_report

        if not self.has_analysis():
            self.show_empty_state()
            self.draw_history_chart()
            return

        issues = self.current_analysis.get("issues", []) or []
        scores = self.compute_component_scores()
        global_score = scores.get("Global", 0)

        critical_count = sum(
            1 for issue in issues
            if isinstance(issue, dict)
            and str(issue.get("severity", "")).lower() == "high"
        )

        self.global_score_label.setText(str(global_score))
        self.issues_label.setText(str(len(issues)))
        self.critical_label.setText(str(critical_count))
        self.elements_label.setText(str(self.estimate_elements_count()))
        self.last_analysis_label.setText(self.get_risk_level(global_score))

        self.apply_global_score_color(global_score)
        self.draw_component_chart(scores)
        self.draw_severity_chart(issues)
        self.draw_history_chart(global_score)
        self.fill_detail_table(issues, scores)

    def show_empty_state(self):
        self.global_score_label.setText("-")
        self.issues_label.setText("-")
        self.critical_label.setText("-")
        self.elements_label.setText(str(self.estimate_elements_count()) if self.current_report else "-")
        self.last_analysis_label.setText("En attente")
        self.global_score_label.setStyleSheet("color: #EAF1FF; font-size: 28px; font-weight: 900;")

        self.draw_empty_chart(self.component_chart, "Aucune analyse IA reçue")
        self.draw_empty_chart(self.severity_chart, "Aucune donnée")
        self.draw_history_chart()
        self.detail_table.setRowCount(0)

    def estimate_elements_count(self):
        report = self.resolve_current_report()

        if report:
            self.current_report = report

        if not isinstance(report, dict) or not report:
            return 0

        summary = report.get("summary", {}) if isinstance(report.get("summary", {}), dict) else {}
        topology = report.get("topology", {}) if isinstance(report.get("topology", {}), dict) else {}
        network_context = report.get("network_context", {}) if isinstance(report.get("network_context", {}), dict) else {}
        inventory = report.get("inventory", {}) if isinstance(report.get("inventory", {}), dict) else {}

        topology_devices = topology.get("devices", []) or []
        inventory_devices = inventory.get("devices", []) or []
        links = topology.get("links", []) or []

        vlans = network_context.get("vlans", []) or []
        subnets = network_context.get("subnets", []) or []

        acl_count = 0
        for device in inventory_devices:
            if not isinstance(device, dict):
                continue

            existing_acls = device.get("existing_acls", device.get("acls", []))

            if isinstance(existing_acls, list):
                acl_count += len(existing_acls)
            elif isinstance(existing_acls, dict):
                acl_count += len(existing_acls)

        if acl_count == 0:
            network_acls = network_context.get("acls", []) or []
            if isinstance(network_acls, list):
                acl_count = len(network_acls)
            elif isinstance(network_acls, dict):
                acl_count = len(network_acls)

        device_count = (
            safe_int(summary.get("device_count"))
            or len(topology_devices)
            or len(inventory_devices)
        )

        vlan_count = (
            safe_int(summary.get("vlan_count"))
            or len(vlans)
            or self.count_vlans_from_inventory(inventory_devices)
        )

        subnet_count = (
            safe_int(summary.get("subnet_count"))
            or len(subnets)
        )

        return device_count + vlan_count + subnet_count + acl_count + len(links)

    def count_vlans_from_inventory(self, devices):
        count = 0

        if not isinstance(devices, list):
            return 0

        for device in devices:
            if not isinstance(device, dict):
                continue

            vlans = device.get("vlans", [])
            if isinstance(vlans, list):
                count += len(vlans)
            elif isinstance(vlans, dict):
                count += len(vlans)

        return count

    def get_risk_level(self, score):
        score = safe_int(score)

        if score < 40:
            return "CRITICAL"

        if score < 70:
            return "MODERATE"

        return "SAFE"

    def apply_global_score_color(self, score):
        score = safe_int(score)

        if score >= 80:
            color = "#22c55e"
        elif score >= 50:
            color = "#facc15"
        else:
            color = "#ef4444"

        self.global_score_label.setStyleSheet(
            f"color: {color}; font-size: 28px; font-weight: 900;"
        )

    def draw_empty_chart(self, chart, message):
        fig = chart["figure"]
        fig.clear()

        ax = fig.add_subplot(111)
        ax.set_facecolor("#10233F")
        fig.patch.set_facecolor("#10233F")

        ax.text(
            0.5,
            0.5,
            message,
            ha="center",
            va="center",
            color="#9DAEC8",
            fontsize=14,
            fontweight="bold"
        )

        ax.set_xticks([])
        ax.set_yticks([])

        for spine in ax.spines.values():
            spine.set_color("#1C3352")

        fig.subplots_adjust(left=0.08, right=0.96, top=0.92, bottom=0.12)
        chart["canvas"].draw()

    def draw_component_chart(self, scores):
        if not scores:
            self.draw_empty_chart(self.component_chart, "Aucune analyse IA reçue")
            return

        fig = self.component_chart["figure"]
        fig.clear()

        ax = fig.add_subplot(111)

        components = ["VLANs", "ACLs", "Devices", "Topology", "Routing", "Global"]
        values = [safe_int(scores.get(component, 0)) for component in components]
        colors = [self.score_color(value) for value in values]

        x = list(range(len(components)))

        ax.bar(x, values, color=colors, width=0.72)
        ax.set_ylim(0, 110)
        ax.set_ylabel("Score (%)")
        ax.set_xticks(x)
        ax.set_xticklabels(components, rotation=20, ha="right", fontsize=9)
        ax.tick_params(axis="x", colors="white", pad=8)
        ax.tick_params(axis="y", colors="white")
        ax.set_facecolor("#10233F")
        fig.patch.set_facecolor("#10233F")
        ax.yaxis.label.set_color("white")

        for spine in ax.spines.values():
            spine.set_color("#1C3352")

        for index, value in enumerate(values):
            ax.text(
                index,
                min(value + 3, 106),
                str(value),
                ha="center",
                va="bottom",
                color="white",
                fontsize=9,
                fontweight="bold"
            )

        fig.subplots_adjust(left=0.10, right=0.98, top=0.90, bottom=0.28)
        self.component_chart["canvas"].draw()

    def draw_severity_chart(self, issues):
        if not issues:
            self.draw_empty_chart(self.severity_chart, "Aucun problème détecté")
            return

        fig = self.severity_chart["figure"]
        fig.clear()

        ax = fig.add_subplot(111)

        high = sum(
            1 for issue in issues
            if isinstance(issue, dict)
            and str(issue.get("severity", "")).lower() == "high"
        )

        medium = sum(
            1 for issue in issues
            if isinstance(issue, dict)
            and str(issue.get("severity", "")).lower() == "medium"
        )

        low = sum(
            1 for issue in issues
            if isinstance(issue, dict)
            and str(issue.get("severity", "")).lower() == "low"
        )

        values = []
        labels = []
        colors = []

        if high:
            values.append(high)
            labels.append("High")
            colors.append("#ef4444")

        if medium:
            values.append(medium)
            labels.append("Medium")
            colors.append("#facc15")

        if low:
            values.append(low)
            labels.append("Low")
            colors.append("#22c55e")

        if not values:
            self.draw_empty_chart(self.severity_chart, "Aucun problème détecté")
            return

        ax.pie(
            values,
            labels=labels,
            autopct="%1.0f%%",
            startangle=90,
            colors=colors,
            textprops={
                "color": "white",
                "fontsize": 9
            }
        )

        ax.set_facecolor("#10233F")
        fig.patch.set_facecolor("#10233F")
        fig.subplots_adjust(left=0.04, right=0.96, top=0.96, bottom=0.04)
        self.severity_chart["canvas"].draw()

    def draw_history_chart(self, global_score=None):
        fig = self.history_chart["figure"]
        fig.clear()

        ax = fig.add_subplot(111)

        scores = self.history_scores[-7:]

        if not scores and global_score is not None:
            scores = [safe_int(global_score)]

        if not scores:
            ax.set_facecolor("#10233F")
            fig.patch.set_facecolor("#10233F")

            ax.text(
                0.5,
                0.5,
                "Aucun historique disponible",
                ha="center",
                va="center",
                color="#9DAEC8",
                fontsize=14,
                fontweight="bold"
            )

            ax.set_xticks([])
            ax.set_yticks([])

            for spine in ax.spines.values():
                spine.set_color("#1C3352")

            self.history_chart["canvas"].draw()
            return

        x = list(range(1, len(scores) + 1))

        ax.plot(x, scores, marker="o", color="#38bdf8")
        ax.fill_between(x, scores, alpha=0.2, color="#38bdf8")

        ax.set_ylim(0, 100)
        ax.set_ylabel("Score")
        ax.set_xlabel("Analyses")
        ax.set_facecolor("#10233F")
        fig.patch.set_facecolor("#10233F")
        ax.tick_params(colors="white")
        ax.xaxis.label.set_color("white")
        ax.yaxis.label.set_color("white")

        for spine in ax.spines.values():
            spine.set_color("#1C3352")

        fig.subplots_adjust(left=0.10, right=0.98, top=0.92, bottom=0.18)
        self.history_chart["canvas"].draw()

    def score_color(self, value):
        value = safe_int(value)

        if value >= 80:
            return "#22c55e"

        if value >= 50:
            return "#facc15"

        return "#ef4444"

    def fill_detail_table(self, issues, scores):
        component_data = {
            "VLANs": {"count": 0, "max_severity": "-"},
            "ACLs": {"count": 0, "max_severity": "-"},
            "Devices": {"count": 0, "max_severity": "-"},
            "Topology": {"count": 0, "max_severity": "-"},
            "Routing": {"count": 0, "max_severity": "-"},
        }

        severity_rank = {
            "-": 0,
            "low": 1,
            "medium": 2,
            "high": 3
        }

        for issue in issues:
            if not isinstance(issue, dict):
                continue

            component = self.classify_issue_component(issue)
            severity = str(issue.get("severity", "low")).lower()

            if component not in component_data:
                component = "Devices"

            component_data[component]["count"] += 1

            if severity_rank.get(severity, 1) > severity_rank.get(component_data[component]["max_severity"], 0):
                component_data[component]["max_severity"] = severity

        self.detail_table.setRowCount(len(component_data))

        for row, (component, data) in enumerate(component_data.items()):
            self.detail_table.setItem(row, 0, QTableWidgetItem(component))
            self.detail_table.setItem(row, 1, QTableWidgetItem(str(data["count"])))
            self.detail_table.setItem(row, 2, QTableWidgetItem(str(data["max_severity"]).upper()))
            self.detail_table.setItem(row, 3, QTableWidgetItem(str(scores.get(component, "-"))))

    def load_score_history(self):
        user_id = self.user_data.get("id", 1)

        try:
            headers = {}

            if self.api_client and hasattr(self.api_client, "get_headers"):
                headers = self.api_client.get_headers()

            response = requests.get(
                f"{API_URL}/ai/score-history/{user_id}",
                headers=headers,
                timeout=10
            )

            if response.status_code != 200:
                self.history_scores = []
                return

            data = response.json()
            history = data.get("history", [])

            if not isinstance(history, list):
                self.history_scores = []
                return

            self.history_scores = [
                safe_int(item.get("score", 0))
                for item in history
                if isinstance(item, dict)
            ]

        except Exception as e:
            print(f"[SecurityAnalytics] load_score_history error: {e}")
            self.history_scores = []