import requests
import json
import os

from PySide6.QtCore import Qt, QSize, QThread, Signal
from PySide6.QtGui import QIcon, QPixmap
from PySide6.QtWidgets import (
    QWidget, QLabel, QPushButton, QTextEdit, QVBoxLayout, QHBoxLayout,
    QFrame, QTableWidget, QTableWidgetItem, QListWidget,
    QMessageBox, QScrollArea, QTabWidget, QProgressBar, QHeaderView
)


API_URL = "http://127.0.0.1:8000"


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


ICON_SIZE = QSize(20, 20)



class APIRequestWorker(QThread):
    success = Signal(dict)
    failed = Signal(str)

    def __init__(self, method: str, url: str, payload=None, timeout: int = 180):
        super().__init__()
        self.method = method.upper()
        self.url = url
        self.payload = payload
        self.timeout = timeout

    def run(self):
        try:
            if self.method == "POST":
                response = requests.post(
                    self.url,
                    json=self.payload,
                    timeout=self.timeout
                )
            elif self.method == "GET":
                response = requests.get(
                    self.url,
                    timeout=self.timeout
                )
            else:
                self.failed.emit(f"Unsupported HTTP method: {self.method}")
                return

            if response.status_code != 200:
                self.failed.emit(response.text)
                return

            try:
                self.success.emit(response.json())
            except Exception:
                self.failed.emit("Réponse API invalide : JSON non exploitable.")

        except requests.exceptions.ReadTimeout:
            self.failed.emit(
                f"Timeout API : le backend n'a pas répondu après {self.timeout} secondes."
            )
        except requests.exceptions.ConnectionError:
            self.failed.emit(
                "Impossible de se connecter au backend FastAPI. Vérifie que uvicorn est lancé."
            )
        except Exception as e:
            self.failed.emit(str(e))


class AIAnalysisPage(QWidget):
    def __init__(self, user_data=None, discovery_report=None, api_client=None):
        super().__init__()

        # Mode réel : pas de fake report et pas de données réseau simulées.
        # La page peut être créée vide, puis recevoir le vrai report via load_discovery_report().
        self.user_data = user_data or {}
        self.api_client = api_client
        self.discovery_report = self.normalize_report(discovery_report) if discovery_report else {}

        self.app_state = {}
        self.analytics_page = None

        self.current_fixes = []
        self.acl_fixes = []
        self.vlan_fixes = []
        self.api_workers = []

        self.intent_validated = False
        self.user_intents = []

        self.setup_ui()
        self.update_snapshot_from_report()
        self.load_score_history()
        self.clear_global_view()

    def setup_ui(self):
        self.apply_style()

        root = QVBoxLayout(self)
        root.setContentsMargins(14, 14, 14, 14)
        root.setSpacing(14)

        root.addLayout(self.create_header())

        self.tabs = QTabWidget()
        self.tabs.setObjectName("aiTabs")

        self.global_tab = self.create_global_tab()
        self.acl_tab = self.create_acl_tab()
        self.vlan_tab = self.create_vlan_tab()

        self.tabs.addTab(self.global_tab, "1. Global Network Analysis")
        self.tabs.addTab(self.acl_tab, "2. ACL Validation")
        self.tabs.addTab(self.vlan_tab, "3. VLAN / VLSM Validation")

        root.addWidget(self.tabs)

    def create_header(self):
        layout = QHBoxLayout()
        left = QVBoxLayout()

        title = QLabel("AI Validation Center")
        title.setObjectName("title")

        subtitle = QLabel("Validation intelligente et analyse de votre infrastructure réseau")
        subtitle.setObjectName("subtitle")

        left.addWidget(title)
        left.addWidget(subtitle)

        self.status_label = QLabel("Agent Active")
        self.status_label.setObjectName("statusBadge")

        username = self.user_data.get("username", "Utilisateur")
        role = self.user_data.get("role", self.user_data.get("role_name", "Connecté"))

        avatar = QLabel(username[:1].upper())
        avatar.setAlignment(Qt.AlignCenter)
        avatar.setFixedSize(44, 44)
        avatar.setObjectName("avatar")

        user_info = QLabel(f"{username}\n{role}")
        user_info.setStyleSheet("font-weight: 800; color: white;")

        layout.addLayout(left)
        layout.addStretch()
        layout.addWidget(self.status_label)
        layout.addSpacing(12)
        layout.addWidget(self.make_icon_label("notification.png", 22))
        layout.addSpacing(12)
        layout.addWidget(avatar)
        layout.addWidget(user_info)

        return layout

    # ======================================================
    # TAB 1 : GLOBAL NETWORK ANALYSIS
    # ======================================================

    def create_global_tab(self):
        page = QWidget()
        root = QHBoxLayout(page)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(14)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)

        content = QWidget()
        main = QVBoxLayout(content)
        main.setContentsMargins(0, 10, 0, 10)
        main.setSpacing(14)

        top = QHBoxLayout()
        top.setSpacing(14)
        top.addWidget(self.create_user_intent_card(), 1)
        top.addWidget(self.create_snapshot_card(), 2)

        main.addLayout(top)
        main.addWidget(self.create_results_card())
        main.addWidget(self.create_fix_card())
        main.addStretch()

        scroll.setWidget(content)

        root.addWidget(scroll, 3)
        root.addWidget(self.create_right_panel(), 1)

        return page

    def create_user_intent_card(self):
        frame = self.card()
        frame.setMinimumHeight(330)

        layout = frame.layout()

        row = QHBoxLayout()
        title_row = self.title_row("User Intent", "brain.png")

        self.intent_status = QLabel("0 intent")
        self.intent_status.setObjectName("warningBadge")

        row.addLayout(title_row)
        row.addStretch()
        row.addWidget(self.intent_status)

        self.intent_input = QTextEdit()
        self.intent_input.setPlaceholderText(
            "Exemples :\n"
            "- Bloquer FTP entre VLANs\n"
            "- Autoriser HTTP/HTTPS vers les serveurs\n"
            "- Isoler les caméras\n"
            "- Détecter les ACL trop permissives"
        )
        self.intent_input.setMinimumHeight(80)

        btn_row = QHBoxLayout()

        self.btn_add_intent = QPushButton("Ajouter Intent")
        self.btn_add_intent.clicked.connect(self.add_intent)

        self.btn_validate_intent = QPushButton("Valider")
        self.btn_validate_intent.clicked.connect(self.validate_intent)

        self.btn_clear_intents = QPushButton("Vider")
        self.btn_clear_intents.setObjectName("darkButton")
        self.btn_clear_intents.clicked.connect(self.clear_intents)

        btn_row.addWidget(self.btn_add_intent)
        btn_row.addWidget(self.btn_validate_intent)
        btn_row.addWidget(self.btn_clear_intents)

        self.intent_list = QListWidget()
        self.intent_list.setMinimumHeight(100)

        self.btn_auto_intent = QPushButton("Auto Intent")
        self.btn_auto_intent.setObjectName("darkButton")
        self.btn_auto_intent.clicked.connect(self.auto_fill_intent)

        layout.addLayout(row)
        layout.addWidget(self.intent_input)
        layout.addLayout(btn_row)
        layout.addWidget(self.intent_list)
        layout.addWidget(self.btn_auto_intent)

        return frame

    def create_snapshot_card(self):
        frame = self.card()
        frame.setMinimumHeight(250)

        layout = frame.layout()

        title = self.title_widget("Network Snapshot", "network.png")

        metrics = QHBoxLayout()
        metrics.setSpacing(10)

        self.devices_value = QLabel("0")
        self.vlans_value = QLabel("0")
        self.acls_value = QLabel("0")

        metrics.addWidget(self.metric_card("Devices", self.devices_value, "network.png"))
        metrics.addWidget(self.metric_card("VLANs", self.vlans_value, "centre_de_control.png"))
        metrics.addWidget(self.metric_card("ACLs", self.acls_value, "verified.png"))

        self.topology_label = QLabel()
        self.topology_label.setAlignment(Qt.AlignCenter)
        self.topology_label.setMinimumHeight(120)
        self.topology_label.setObjectName("topologyBox")

        layout.addWidget(title)
        layout.addLayout(metrics)
        layout.addWidget(self.topology_label)

        return frame

    def create_results_card(self):
        frame = self.card()

        layout = frame.layout()

        title = self.title_widget("AI Analysis Results", "brain.png")

        self.results_table = QTableWidget()
        self.results_table.setColumnCount(4)
        self.results_table.setHorizontalHeaderLabels(["Issue", "Type", "Severity", "Description"])
        self.results_table.setMinimumHeight(260)

        # Affichage complet du texte : plus de "..."
        self.results_table.setWordWrap(True)
        self.results_table.setTextElideMode(Qt.ElideNone)

        self.results_table.verticalHeader().setVisible(False)
        self.results_table.verticalHeader().setSectionResizeMode(QHeaderView.ResizeToContents)

        header = self.results_table.horizontalHeader()
        header.setSectionResizeMode(QHeaderView.Interactive)
        header.setStretchLastSection(False)

        self.results_table.setColumnWidth(0, 280)   # Issue
        self.results_table.setColumnWidth(1, 210)   # Type
        self.results_table.setColumnWidth(2, 120)   # Severity
        self.results_table.setColumnWidth(3, 900)   # Description complète

        self.results_table.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        self.results_table.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)

        layout.addWidget(title)
        layout.addWidget(self.results_table)

        return frame

    def create_fix_card(self):
        frame = self.card()

        layout = frame.layout()

        content = QHBoxLayout()
        content.setSpacing(18)

        left = QVBoxLayout()

        title = self.title_widget("Recommended Cisco CLI Fix", "verified.png")

        self.fix_box = QTextEdit()
        self.fix_box.setReadOnly(True)
        self.fix_box.setMinimumHeight(130)

        left.addWidget(title)
        left.addWidget(self.fix_box)

        right = QVBoxLayout()

        exp_title = QLabel("Explanation")
        exp_title.setObjectName("cardTitle")

        self.explanation_box = QTextEdit()
        self.explanation_box.setReadOnly(True)
        self.explanation_box.setMinimumHeight(100)

        buttons = QHBoxLayout()

        self.btn_apply = QPushButton("Apply Fix")
        self.btn_apply.clicked.connect(self.apply_fix)

        self.btn_export = QPushButton("Export Config")
        self.btn_export.setObjectName("darkButton")

        buttons.addWidget(self.btn_apply)
        buttons.addWidget(self.btn_export)

        right.addWidget(exp_title)
        right.addWidget(self.explanation_box)
        right.addStretch()
        right.addLayout(buttons)

        content.addLayout(left, 2)
        content.addLayout(right, 1)
        layout.addLayout(content)

        return frame

    def create_right_panel(self):
        wrapper = QFrame()
        wrapper.setObjectName("rightPanel")

        panel = QVBoxLayout(wrapper)
        panel.setContentsMargins(10, 10, 10, 10)
        panel.setSpacing(12)

        run_btn = QPushButton("Run Global AI Analysis  →")
        run_btn.setObjectName("runAIButton")
        run_btn.setMinimumHeight(44)
        run_btn.setMaximumHeight(48)
        run_btn.clicked.connect(self.run_ai_validation)

        panel.addWidget(run_btn)
        panel.addWidget(self.create_alerts_card())
        panel.addWidget(self.create_recent_card())
        panel.addStretch()

        return wrapper

    def create_alerts_card(self):
        frame = self.card()
        frame.setObjectName("rightInfoCard")
        frame.setMinimumHeight(150)
        frame.setMaximumHeight(190)

        layout = frame.layout()

        title = self.title_widget("Live Alerts", "siren.png")

        self.alerts_list = QListWidget()
        self.alerts_list.setMinimumHeight(95)
        self.alerts_list.setMaximumHeight(115)
        self.alerts_list.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)

        layout.addWidget(title)
        layout.addWidget(self.alerts_list)

        return frame

    def create_recent_card(self):
        frame = self.card()
        frame.setObjectName("rightInfoCard")
        frame.setMinimumHeight(230)
        frame.setMaximumHeight(280)

        layout = frame.layout()

        title = self.title_widget("Recent Analyses", "bar-chart.png")

        self.recent_list = QListWidget()
        self.recent_list.setMinimumHeight(160)
        self.recent_list.setMaximumHeight(190)
        self.recent_list.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)

        layout.addWidget(title)
        layout.addWidget(self.recent_list)

        return frame

    # ======================================================
    # TAB 2 : ACL VALIDATION
    # ======================================================

    def create_acl_tab(self):
        page = QWidget()
        layout = QHBoxLayout(page)
        layout.setContentsMargins(0, 10, 0, 10)
        layout.setSpacing(14)

        left = QVBoxLayout()
        center = QVBoxLayout()
        right = QVBoxLayout()

        context = self.card("Contexte ACL")
        self.acl_context_box = QTextEdit()
        self.acl_context_box.setReadOnly(True)
        self.acl_context_box.setText("Aucune ACL chargée depuis ACL Intelligent Engine.")
        context.layout().addWidget(self.acl_context_box)

        result_card = self.card("Résultat Validation ACL")
        self.acl_score = QProgressBar()
        self.acl_score.setRange(0, 100)
        self.acl_score.setValue(0)

        self.acl_status = QLabel("Statut : -")
        self.acl_status.setObjectName("statusText")

        result_card.layout().addWidget(self.acl_score)
        result_card.layout().addWidget(self.acl_status)

        left.addWidget(context, 2)
        left.addWidget(result_card, 1)

        config_card = self.card("Configuration ACL générée")
        self.acl_config_box = QTextEdit()
        self.acl_config_box.setReadOnly(True)
        self.acl_config_box.setText("Aucune configuration ACL reçue.")
        config_card.layout().addWidget(self.acl_config_box)

        fix_card = self.card("Corrections ACL proposées")
        self.acl_fix_box = QTextEdit()
        self.acl_fix_box.setReadOnly(True)
        fix_card.layout().addWidget(self.acl_fix_box)

        buttons = QHBoxLayout()

        self.btn_acl_validate = QPushButton("Valider ACL avec AI")
        self.btn_acl_validate.clicked.connect(self.run_acl_validation)

        self.btn_acl_apply = QPushButton("Appliquer corrections ACL")
        self.btn_acl_apply.clicked.connect(self.apply_acl_fix)

        self.btn_go_deploy_acl = QPushButton("Passer au déploiement ACL")
        self.btn_go_deploy_acl.setObjectName("deployButton")
        self.btn_go_deploy_acl.clicked.connect(self.go_to_acl_deploy)

        buttons.addWidget(self.btn_acl_validate)
        buttons.addWidget(self.btn_acl_apply)
        buttons.addWidget(self.btn_go_deploy_acl)

        center.addWidget(config_card, 2)
        center.addWidget(fix_card, 2)
        center.addLayout(buttons)

        checks_card = self.card("Analyse ACL")
        self.acl_checks_list = QListWidget()
        self.acl_checks_list.addItem("En attente de validation ACL")
        checks_card.layout().addWidget(self.acl_checks_list)

        right.addWidget(checks_card)

        layout.addLayout(left, 1)
        layout.addLayout(center, 2)
        layout.addLayout(right, 1)

        return page

    # ======================================================
    # TAB 3 : VLAN / VLSM VALIDATION
    # ======================================================

    def create_vlan_tab(self):
        page = QWidget()
        layout = QHBoxLayout(page)
        layout.setContentsMargins(0, 10, 0, 10)
        layout.setSpacing(14)

        left = QVBoxLayout()
        center = QVBoxLayout()
        right = QVBoxLayout()

        plan_card = self.card("Plan VLAN / VLSM soumis")
        self.vlan_plan_box = QTextEdit()
        self.vlan_plan_box.setReadOnly(True)
        self.vlan_plan_box.setText("Aucun plan VLAN/VLSM reçu.")
        plan_card.layout().addWidget(self.vlan_plan_box)

        score_card = self.card("Résultat Validation VLAN/VLSM")
        self.vlan_score = QProgressBar()
        self.vlan_score.setRange(0, 100)
        self.vlan_score.setValue(0)

        self.vlan_status = QLabel("Statut : -")
        self.vlan_status.setObjectName("statusText")

        score_card.layout().addWidget(self.vlan_score)
        score_card.layout().addWidget(self.vlan_status)

        left.addWidget(plan_card, 2)
        left.addWidget(score_card, 1)

        checks_card = self.card("Vérifications détaillées")
        self.vlan_checks_list = QListWidget()
        self.vlan_checks_list.addItem("En attente de validation VLAN/VLSM")
        checks_card.layout().addWidget(self.vlan_checks_list)

        fixes_card = self.card("Corrections VLAN/VLSM proposées")
        self.vlan_fix_box = QTextEdit()
        self.vlan_fix_box.setReadOnly(True)
        fixes_card.layout().addWidget(self.vlan_fix_box)

        buttons = QHBoxLayout()

        self.btn_vlan_validate = QPushButton("Valider VLAN/VLSM avec AI")
        self.btn_vlan_validate.clicked.connect(self.run_vlan_validation)

        self.btn_vlan_apply = QPushButton("Appliquer corrections VLAN")
        self.btn_vlan_apply.clicked.connect(self.apply_vlan_fix)

        self.btn_go_deploy_vlan = QPushButton("Passer au déploiement VLAN/VLSM")
        self.btn_go_deploy_vlan.setObjectName("deployButton")
        self.btn_go_deploy_vlan.clicked.connect(self.go_to_vlan_deployment)

        buttons.addWidget(self.btn_vlan_validate)
        buttons.addWidget(self.btn_vlan_apply)
        buttons.addWidget(self.btn_go_deploy_vlan)

        center.addWidget(checks_card, 2)
        center.addWidget(fixes_card, 2)
        center.addLayout(buttons)

        summary_card = self.card("Résumé")
        self.vlan_summary_list = QListWidget()
        self.vlan_summary_list.addItem("Total VLANs : -")
        self.vlan_summary_list.addItem("Chevauchements : -")
        self.vlan_summary_list.addItem("Gateways : -")
        summary_card.layout().addWidget(self.vlan_summary_list)

        right.addWidget(summary_card)

        layout.addLayout(left, 1)
        layout.addLayout(center, 2)
        layout.addLayout(right, 1)

        return page

    # ======================================================
    # GLOBAL API
    # ======================================================


    def run_ai_validation(self):
        report = self.get_current_report()
        final_intent = self.get_final_user_intent()

        if not report:
            QMessageBox.warning(
                self,
                "Report réel manquant",
                "Aucun report réel chargé. Lance d'abord la découverte réseau puis réouvre l'analyse AI."
            )
            return

        if not final_intent:
            QMessageBox.warning(
                self,
                "Intention réelle manquante",
                "Ajoute une intention réelle avant de lancer l'analyse globale."
            )
            return

        payload = {
            "user_id": self.user_data.get("id", 1),
            "user_input_text": final_intent,
            "discovery_report": report
        }

        self.start_api_post(
            endpoint="/ai/validate",
            payload=payload,
            timeout=180,
            status_text="Analyse globale en cours...",
            success_callback=self.on_global_ai_success
        )

    def display_analysis(self, analysis):
        issues = analysis.get("issues", [])
        fixes = analysis.get("fixes", [])
        score = analysis.get("security_score", analysis.get("score", 0))

        self.results_table.setRowCount(len(issues))

        for row, issue in enumerate(issues):
            severity = issue.get("severity", "").upper()
            icon = self.severity_icon(severity)
            description = issue.get("description", "")
            issue_type = issue.get("type", "")

            issue_item = QTableWidgetItem(f"{icon} {description}")
            type_item = QTableWidgetItem(issue_type)
            severity_item = QTableWidgetItem(severity)
            description_item = QTableWidgetItem(description)

            # Tooltips : même si l'utilisateur réduit une colonne, le texte complet reste accessible au survol
            issue_item.setToolTip(description)
            type_item.setToolTip(issue_type)
            severity_item.setToolTip(severity)
            description_item.setToolTip(description)

            self.results_table.setItem(row, 0, issue_item)
            self.results_table.setItem(row, 1, type_item)
            self.results_table.setItem(row, 2, severity_item)
            self.results_table.setItem(row, 3, description_item)

        self.results_table.resizeRowsToContents()

        self.alerts_list.clear()

        if issues:
            for issue in issues:
                severity = issue.get("severity", "low").upper()
                icon = self.severity_icon(severity)
                desc = issue.get("description", "")
                self.alerts_list.addItem(f"{icon} {severity} {desc[:60]}")
        else:
            self.alerts_list.addItem("Aucun problème détecté")

        self.current_fixes = fixes
        self.fix_box.setText(self.format_fixes_as_cli(fixes))
        self.explanation_box.setText(self.format_fix_explanations(fixes))

        self.recent_list.insertItem(0, f"●   Now        {score}/100        {self.risk_label(score)}")

        if self.analytics_page is not None:
            self.analytics_page.load_ai_analysis(analysis)
            print("SECURITY ANALYTICS UPDATED ")

    def extract_analysis_payload(self, data):
        """
        Accepte plusieurs formats de réponse backend :
        - {"data": {"analysis": {...}}}
        - {"analysis": {...}}
        - {"issues": [...], "fixes": [...], "score": ...}
        """
        if not isinstance(data, dict):
            return {}

        if isinstance(data.get("data"), dict):
            nested = data["data"]
            if isinstance(nested.get("analysis"), dict):
                return nested["analysis"]
            if "issues" in nested or "fixes" in nested or "score" in nested or "security_score" in nested:
                return nested

        if isinstance(data.get("analysis"), dict):
            return data["analysis"]

        if "issues" in data or "fixes" in data or "score" in data or "security_score" in data:
            return data

        return {}

    def apply_fix(self):
        self.send_apply_fix(self.current_fixes)

    # ======================================================
    # ACL VALIDATION
    # ======================================================

    def load_acl_validation_data(self, acl_plan, generated_config, report=None):
        if report:
            self.load_discovery_report(report)

        self.app_state["acl_plan"] = acl_plan
        self.app_state["generated_config"] = generated_config

        self.tabs.setCurrentIndex(1)

        self.acl_context_box.setText(str(acl_plan))
        self.acl_config_box.setText(str(generated_config))
        self.acl_fix_box.setText("Clique sur 'Valider ACL avec AI' pour analyser uniquement cette ACL.")
        self.acl_checks_list.clear()
        self.acl_checks_list.addItem("En attente de validation ACL")
        self.acl_score.setValue(0)
        self.acl_status.setText("Statut : -")


    def run_acl_validation(self):
        report = self.get_current_report()
        acl_plan = self.app_state.get("acl_plan")
        generated_config = self.app_state.get("generated_config")

        if not report:
            QMessageBox.warning(self, "Report manquant", "Lance d'abord la découverte réseau avant la validation ACL.")
            return

        if not acl_plan or not generated_config:
            QMessageBox.warning(self, "ACL manquante", "Aucune ACL générée n’est disponible.")
            return

        payload = {
            "user_id": self.user_data.get("id", 1),
            "user_input_text": (
                "MODE STRICT ACL_VALIDATION_ONLY.\n"
                "Tu dois analyser UNIQUEMENT la configuration ACL fournie dans generated_config.\n"
                "Interdiction de proposer des corrections VLAN, VLSM, SVI, trunk, gateway ou hardware.\n"
                "Les fixes doivent concerner seulement : syntaxe ACL, direction in/out, ordre des règles, conflit ACL, règle trop permissive, ajout log.\n"
                "Si tu détectes un problème VLAN/SVI/global, mets-le seulement dans observations, jamais dans fixes."
            ),
            "discovery_report": report,
            "acl_plan": acl_plan,
            "generated_config": generated_config
        }

        self.start_api_post(
            endpoint="/ai/validate",
            payload=payload,
            timeout=180,
            status_text="Validation ACL en cours...",
            success_callback=self.on_acl_ai_success
        )

    def display_acl_analysis(self, analysis):
        raw_issues = analysis.get("issues", [])
        raw_fixes = analysis.get("fixes", [])

        issues = self.filter_acl_only_issues(raw_issues)
        fixes = self.filter_acl_only_fixes(raw_fixes)

        acl_plan = self.app_state.get("acl_plan")
        generated_config = self.app_state.get("generated_config")

        # Score local intelligent pour ACL uniquement.
        # On ne prend PAS le score global backend ici.
        score = self.calculate_acl_score(
            acl_plan=acl_plan,
            generated_config=generated_config,
            issues=issues,
            fixes=fixes
        )

        status = self.status_from_score(score)

        self.acl_fixes = fixes
        self.acl_score.setValue(int(score))
        self.apply_progress_color(self.acl_score, score)
        self.acl_status.setText(f"Statut : {status} | Score ACL : {score}/100")

        self.acl_checks_list.clear()

        if issues:
            for issue in issues:
                self.acl_checks_list.addItem(
                    f"{self.severity_icon(issue.get('severity', '').upper())} "
                    f"{issue.get('type', 'Issue')} - {issue.get('description', '')[:100]}"
                )
        else:
            if score >= 85:
                self.acl_checks_list.addItem("Configuration ACL sécurisée")
            elif score >= 65:
                self.acl_checks_list.addItem("Configuration ACL acceptable mais améliorable")
            else:
                self.acl_checks_list.addItem("Configuration ACL risquée")
            if raw_issues:
                self.acl_checks_list.addItem("Problèmes globaux ignorés dans ce mode ACL")

        if fixes:
            self.acl_fix_box.setText(self.format_fixes_as_cli(fixes))
        else:
            self.acl_fix_box.setText("Aucune correction ACL proposée.")

    def calculate_acl_score(self, acl_plan, generated_config, issues=None, fixes=None):
        """
        Score intelligent local pour l'onglet ACL Validation.
        Objectif : évaluer uniquement la règle ACL générée, sans utiliser le score global réseau.
        """
        score = 100
        issues = issues or []
        fixes = fixes or []

        acl_plan = acl_plan if isinstance(acl_plan, dict) else {}
        generated_config = str(generated_config or "")

        text = (
            str(acl_plan) + "\n" +
            generated_config + "\n" +
            str(issues) + "\n" +
            str(fixes)
        ).lower()

        # Règle trop permissive
        if "permit ip any any" in text or "allow_all" in text:
            score -= 35

        if "too permissive" in text or "trop permissive" in text:
            score -= 25

        # Direction manquante ou inconnue
        direction = acl_plan.get("apply_direction")
        if not direction or str(direction).lower() in ["-", "none", "null", "unknown"]:
            score -= 15

        # Pas de log dans la config générée
        if " log" not in generated_config.lower():
            score -= 10

        # Port manquant pour TCP/UDP
        rules = acl_plan.get("rules", [])
        if isinstance(rules, list) and rules:
            rule = rules[0]
            protocol = str(rule.get("protocol", "")).lower()
            port = rule.get("port")

            if protocol in ["tcp", "udp"] and port in [0, None, "0", "", "None"]:
                score -= 10

            action = str(rule.get("action", "")).lower()
            if action not in ["permit", "deny"]:
                score -= 10
        else:
            score -= 15

        # Device manquant
        device = acl_plan.get("device")
        if not device or str(device).lower() in ["-", "none", "null", "unknown"]:
            score -= 10

        # Syntaxe Cisco minimale absente
        if "ip access-list extended" not in generated_config.lower():
            score -= 15

        # Issues ACL filtrées
        for issue in issues:
            severity = str(issue.get("severity", "")).lower()
            if severity == "high":
                score -= 15
            elif severity == "medium":
                score -= 8
            elif severity == "low":
                score -= 3

        return max(0, min(100, int(score)))

    def status_from_score(self, score):
        if score >= 85:
            return "OK"
        if score >= 65:
            return "WARNING"
        return "RISK"

    def apply_progress_color(self, progress_bar, score):
        if score >= 85:
            color = "#22c55e"
        elif score >= 65:
            color = "#f59e0b"
        else:
            color = "#ef4444"

        progress_bar.setStyleSheet(f"""
            QProgressBar {{
                background-color: #0E2340;
                border: 1px solid #243D5C;
                border-radius: 8px;
                text-align: center;
                height: 24px;
                color: white;
                font-weight: bold;
            }}
            QProgressBar::chunk {{
                background-color: {color};
                border-radius: 8px;
            }}
        """)

    def filter_acl_only_issues(self, issues):
        forbidden = [
            "vlan", "vlsm", "svi", "gateway", "trunk", "hardware",
            "eol", "end-of-life", "switch", "router", "topology"
        ]
        allowed = ["acl", "access-list", "access list", "direction", "in/out", "permit", "deny", "log"]

        clean = []
        for issue in issues:
            text = " ".join([
                str(issue.get("type", "")),
                str(issue.get("description", "")),
                str(issue.get("recommended_fix", "")),
                str(issue.get("affected_device", "")),
                str(issue.get("affected_vlan", ""))
            ]).lower()

            if any(word in text for word in forbidden) and not any(word in text for word in allowed):
                continue

            if any(word in text for word in allowed):
                clean.append(issue)

        return clean

    def filter_acl_only_fixes(self, fixes):
        forbidden = [
            "vlan", "vlsm", "svi", "gateway", "trunk", "ip address",
            "interface vlan", "switchport", "hardware", "eol", "end-of-life"
        ]
        allowed = ["access-list", "ip access-list", "access-group", "permit", "deny", "log", "remark"]

        clean = []
        for fix in fixes:
            commands = " ".join(str(cmd) for cmd in fix.get("commands", [])).lower()
            issue = str(fix.get("issue", "")).lower()
            explanation = str(fix.get("explanation", "")).lower()
            text = f"{issue} {commands} {explanation}"

            if any(word in text for word in forbidden):
                continue

            if any(word in text for word in allowed):
                clean.append(fix)

        return clean

    def apply_acl_fix(self):
        self.send_apply_fix(self.acl_fixes)

    def go_to_acl_deploy(self):
        """
        Ouvre la page de déploiement ACL après validation AI.
        Cette méthode suppose que MainWindow a injecté :
        - self.deploy_acl_page
        - self.parent_stack
        """
        acl_plan = self.app_state.get("acl_plan")
        generated_config = self.app_state.get("generated_config")
        report = self.get_current_report()

        if not acl_plan:
            QMessageBox.warning(
                self,
                "ACL manquante",
                "Aucun plan ACL disponible. Retourne à ACL Intelligent Engine et génère une ACL."
            )
            return

        if not generated_config:
            QMessageBox.warning(
                self,
                "Configuration manquante",
                "Aucune configuration Cisco générée n’est disponible pour le déploiement."
            )
            return

        if not hasattr(self, "deploy_acl_page") or self.deploy_acl_page is None:
            QMessageBox.warning(
                self,
                "Page déploiement non connectée",
                "La page DeployAclPage n’est pas encore connectée dans main_window.py."
            )
            return

        if not hasattr(self, "parent_stack") or self.parent_stack is None:
            QMessageBox.warning(
                self,
                "Stack non connecté",
                "Le QStackedWidget parent n’est pas encore connecté dans main_window.py."
            )
            return

        self.deploy_acl_page.load_deploy_data(
            acl_plan=acl_plan,
            generated_config=generated_config,
            report=report
        )

        self.parent_stack.setCurrentWidget(self.deploy_acl_page)

    # ======================================================
    # VLAN VALIDATION
    # ======================================================

    def load_vlan_config_validation_data(self, report=None, final_plan=None, generated_config=None, rendered_configs=None, base_network=None):
        """
        Reçoit les données depuis ConfigGenerationPage après génération Cisco.
        Cette méthode ouvre directement l'onglet VLAN/VLSM Validation et garde
        la configuration générée pour l'envoyer ensuite vers la page de déploiement.
        """
        if report:
            self.load_discovery_report(report)

        final_plan = final_plan or []
        generated_config = str(generated_config or "")
        vlsm_plan = self.extract_vlsm_from_final_plan(final_plan)

        self.app_state["vlan_plan"] = final_plan
        self.app_state["vlsm_plan"] = vlsm_plan
        self.app_state["final_plan"] = final_plan
        self.app_state["generated_vlan_config"] = generated_config
        self.app_state["rendered_configs"] = rendered_configs or {}
        self.app_state["base_network"] = base_network

        self.tabs.setCurrentIndex(2)

        self.vlan_plan_box.setText(
            "PLAN FINAL VLAN / VLSM + CONFIGURATION CISCO REÇUS\n"
            "=================================================\n\n"
            "PLAN FINAL :\n"
            f"{self.format_vlan_vlsm_plan_for_display(final_plan)}\n\n"
            "CONFIGURATION CISCO :\n"
            f"{generated_config if generated_config else 'Aucune configuration Cisco reçue.'}"
        )

        self.vlan_checks_list.clear()
        self.vlan_checks_list.addItem("Plan VLAN/VLSM reçu depuis Configuration Cisco")
        self.vlan_checks_list.addItem("Configuration Cisco prête pour validation")
        self.vlan_checks_list.addItem("Prêt pour validation intelligente")

        if base_network:
            self.vlan_checks_list.addItem(f"Réseau principal : {base_network}")

        self.vlan_fix_box.setText("Clique sur 'Valider VLAN/VLSM avec AI' pour analyser ce plan avant déploiement.")
        self.vlan_score.setValue(0)
        self.vlan_status.setText("Statut : Plan + config reçus - en attente de validation AI")
        self.update_vlan_summary(final_plan, vlsm_plan, [])

    def load_vlan_validation_data(self, vlan_plan=None, vlsm_plan=None, report=None):
        if report:
            self.load_discovery_report(report)

        self.app_state["vlan_plan"] = vlan_plan
        self.app_state["vlsm_plan"] = vlsm_plan

        self.tabs.setCurrentIndex(2)
        self.vlan_plan_box.setText(f"VLAN PLAN:\n{vlan_plan}\n\nVLSM PLAN:\n{vlsm_plan}")
        self.vlan_checks_list.clear()
        self.vlan_checks_list.addItem("En attente de validation VLAN/VLSM")
        self.vlan_fix_box.clear()
        self.vlan_score.setValue(0)
        self.vlan_status.setText("Statut : -")

    def load_vlan_vlsm_plan(self, report=None, final_plan=None, base_network=None):
        """
        Fonction appelée directement depuis VlanVlsmPage quand l'utilisateur clique
        sur le bouton "Validation AI".

        Elle reçoit le vrai report de découverte et le plan final VLAN/VLSM,
        puis ouvre automatiquement l'onglet 3 : VLAN / VLSM Validation.
        """
        if report:
            self.load_discovery_report(report)

        final_plan = final_plan or []
        vlsm_plan = self.extract_vlsm_from_final_plan(final_plan)

        self.app_state["vlan_plan"] = final_plan
        self.app_state["vlsm_plan"] = vlsm_plan
        self.app_state["final_plan"] = final_plan
        self.app_state["base_network"] = base_network

        self.tabs.setCurrentIndex(2)

        self.vlan_plan_box.setText(
            "PLAN FINAL VLAN / VLSM REÇU DEPUIS VLAN / VLSM PLANNER\n"
            "=====================================================\n\n"
            + self.format_vlan_vlsm_plan_for_display(final_plan)
        )

        self.vlan_checks_list.clear()
        self.vlan_checks_list.addItem("Plan VLAN/VLSM reçu depuis le module VLAN/VLSM Planner")
        self.vlan_checks_list.addItem("Prêt pour validation intelligente")

        if base_network:
            self.vlan_checks_list.addItem(f"Réseau principal : {base_network}")

        self.vlan_fix_box.setText("Clique sur 'Valider VLAN/VLSM avec AI' pour analyser ce plan.")
        self.vlan_score.setValue(0)
        self.vlan_status.setText("Statut : Plan reçu - en attente de validation AI")
        self.update_vlan_summary(final_plan, vlsm_plan, [])

    def extract_vlsm_from_final_plan(self, final_plan):
        """
        Extrait la partie VLSM depuis le plan final généré par VlanVlsmPage.
        Le backend AI reçoit ainsi un vlan_plan et un vlsm_plan séparés.
        """
        rows = []

        if not isinstance(final_plan, list):
            return rows

        for item in final_plan:
            if not isinstance(item, dict):
                continue

            rows.append({
                "site": item.get("site", "LAN"),
                "zone_name": item.get("zone", "-"),
                "vlan_id": item.get("vlan_id", "-"),
                "vlan_name": item.get("vlan_name", "-"),
                "subnet": item.get("subnet", "-"),
                "mask": item.get("mask", "-"),
                "gateway": item.get("gateway", "-"),
                "status": item.get("status", "-")
            })

        return rows

    def format_vlan_vlsm_plan_for_display(self, final_plan):
        """
        Affiche le plan final d'une manière lisible pour l'utilisateur et le jury.
        """
        if not final_plan:
            return "Aucun plan VLAN/VLSM reçu."

        try:
            return json.dumps(final_plan, indent=4, ensure_ascii=False)
        except Exception:
            return str(final_plan)


    def run_vlan_validation(self):
        report = self.get_current_report()
        vlan_plan = self.app_state.get("vlan_plan")
        vlsm_plan = self.app_state.get("vlsm_plan")

        if not report:
            QMessageBox.warning(self, "Report manquant", "Lance d'abord la découverte réseau avant la validation VLAN/VLSM.")
            return

        if not vlan_plan and not vlsm_plan:
            QMessageBox.warning(self, "Plan manquant", "Aucun plan VLAN/VLSM n’est disponible.")
            return

        payload = {
            "user_id": self.user_data.get("id", 1),
            "user_input_text": (
                "MODE STRICT VLAN_VLSM_VALIDATION_ONLY.\n"
                "Valide uniquement le plan VLAN/VLSM fourni.\n"
                "Vérifie uniquement : chevauchement IP, gateways, trunk, SVI, cohérence VLAN, masque, broadcast, plages IP.\n"
                "Ne propose pas de corrections ACL sauf si elles sont directement nécessaires au plan VLAN/VLSM."
            ),
            "discovery_report": report,
            "vlan_plan": vlan_plan,
            "vlsm_plan": vlsm_plan
        }

        self.start_api_post(
            endpoint="/ai/validate",
            payload=payload,
            timeout=180,
            status_text="Validation VLAN/VLSM en cours...",
            success_callback=self.on_vlan_ai_success
        )

    def display_vlan_analysis(self, analysis):
        issues = analysis.get("issues", [])
        fixes = analysis.get("fixes", [])

        vlan_plan = self.app_state.get("vlan_plan")
        vlsm_plan = self.app_state.get("vlsm_plan")
        report = self.get_current_report()

        # Score local intelligent pour VLAN/VLSM uniquement.
        # Le score global backend reste réservé à l'onglet Global Network Analysis.
        score = self.calculate_vlan_vlsm_score(
            vlan_plan=vlan_plan,
            vlsm_plan=vlsm_plan,
            report=report,
            issues=issues,
            fixes=fixes
        )

        status = self.status_from_score(score)

        self.vlan_fixes = fixes
        self.vlan_score.setValue(int(score))
        self.apply_progress_color(self.vlan_score, score)
        self.vlan_status.setText(f"Statut : {status} | Score VLAN/VLSM : {score}/100")

        self.vlan_checks_list.clear()

        if issues:
            for issue in issues:
                self.vlan_checks_list.addItem(
                    f"{self.severity_icon(issue.get('severity', '').upper())} "
                    f"{issue.get('type', 'Issue')} - {issue.get('description', '')[:100]}"
                )
        else:
            self.vlan_checks_list.addItem("Aucun problème critique VLAN/VLSM détecté")

        self.update_vlan_summary(vlan_plan, vlsm_plan, issues)

        if fixes:
            self.vlan_fix_box.setText(self.format_fixes_as_cli(fixes))
        else:
            self.vlan_fix_box.setText("Aucune correction VLAN/VLSM proposée.")

    def calculate_vlan_vlsm_score(self, vlan_plan=None, vlsm_plan=None, report=None, issues=None, fixes=None):
        """
        Score intelligent local pour l'onglet VLAN/VLSM Validation.
        Il vérifie la cohérence du plan VLAN/VLSM, indépendamment du score global réseau.
        """
        score = 100
        issues = issues or []
        fixes = fixes or []
        report = self.normalize_report(report or {})

        text = (
            str(vlan_plan or "") + "\n" +
            str(vlsm_plan or "") + "\n" +
            str(issues) + "\n" +
            str(fixes)
        ).lower()

        if not vlan_plan and not vlsm_plan:
            return 0

        # Chevauchement IP / overlap
        if "overlap" in text or "chevauchement" in text or "conflict" in text or "conflit" in text:
            score -= 30

        # Gateway manquante
        if "missing gateway" in text or "gateway manqu" in text or "passerelle manqu" in text:
            score -= 20

        # SVI manquant
        if "missing svi" in text or "svi manqu" in text or "sans svi" in text:
            score -= 15

        # Trunk manquant / VLAN non autorisé sur trunk
        if "trunk" in text and ("missing" in text or "manqu" in text or "not allowed" in text or "non autoris" in text):
            score -= 15

        # Masque / broadcast / subnet incohérent
        if "mask" in text or "masque" in text or "broadcast" in text:
            if "invalid" in text or "incorrect" in text or "invalide" in text or "incorrecte" in text:
                score -= 15

        # VLAN ID dupliqué
        if "duplicate vlan" in text or "id vlan dupli" in text or "vlan duplicate" in text:
            score -= 20

        # Pénalité selon les issues retournées par l'IA
        for issue in issues:
            severity = str(issue.get("severity", "")).lower()
            if severity == "high":
                score -= 15
            elif severity == "medium":
                score -= 8
            elif severity == "low":
                score -= 3

        return max(0, min(100, int(score)))

    def update_vlan_summary(self, vlan_plan=None, vlsm_plan=None, issues=None):
        issues = issues or []
        vlan_count = self.count_items(vlan_plan)
        vlsm_count = self.count_items(vlsm_plan)

        issue_text = str(issues).lower()
        overlap_detected = "oui" if ("overlap" in issue_text or "chevauchement" in issue_text) else "non"

        self.vlan_summary_list.clear()
        self.vlan_summary_list.addItem(f"Total VLANs : {vlan_count}")
        self.vlan_summary_list.addItem(f"Sous-réseaux VLSM : {vlsm_count}")
        self.vlan_summary_list.addItem(f"Chevauchements : {overlap_detected}")

    def count_items(self, value):
        if isinstance(value, list):
            return len(value)
        if isinstance(value, dict):
            for key in ["vlans", "vlan_plan", "vlsm", "subnets", "plans", "results"]:
                if isinstance(value.get(key), list):
                    return len(value.get(key))
            return 1 if value else 0
        return 0

    def apply_vlan_fix(self):
        self.send_apply_fix(self.vlan_fixes)

    def go_to_vlan_deployment(self):
        """
        Passe de l'onglet VLAN/VLSM Validation vers la page de déploiement VLAN/VLSM.
        La page de déploiement doit être connectée dans MainWindow avec l'un de ces noms :
        - page_deploy_vlan_vlsm
        - page_deploy_network
        - deploy_vlan_vlsm_page
        """
        vlan_plan = self.app_state.get("vlan_plan") or self.app_state.get("final_plan")
        generated_config = self.app_state.get("generated_vlan_config") or self.app_state.get("generated_config")
        report = self.get_current_report()

        if not vlan_plan:
            QMessageBox.warning(
                self,
                "Plan manquant",
                "Aucun plan VLAN/VLSM disponible. Retourne au module VLAN/VLSM et génère le plan."
            )
            return

        if not generated_config:
            QMessageBox.warning(
                self,
                "Configuration manquante",
                "Aucune configuration Cisco générée n’est disponible. Retourne à la page Configuration Cisco."
            )
            return

        main_window = self.window()
        deploy_page = None

        possible_names = [
            "page_deploy_vlan_vlsm",
            "page_deploy_network",
            "deploy_vlan_vlsm_page",
            "deploy_network_page",
            "page_deploy_vlan",
        ]

        for name in possible_names:
            page = getattr(main_window, name, None)
            if page is not None:
                deploy_page = page
                break

        if deploy_page is None:
            QMessageBox.warning(
                self,
                "Page déploiement non connectée",
                "La page de déploiement VLAN/VLSM n’est pas encore connectée dans main_window.py."
            )
            return

        if hasattr(deploy_page, "load_deploy_data"):
            deploy_page.load_deploy_data(
                final_plan=vlan_plan,
                generated_config=generated_config,
                rendered_configs=self.app_state.get("rendered_configs", {}),
                report=report
            )
        else:
            QMessageBox.warning(
                self,
                "Méthode manquante",
                "La page de déploiement doit contenir load_deploy_data(final_plan, generated_config, report)."
            )
            return

        if hasattr(main_window, "stack"):
            main_window.stack.setCurrentWidget(deploy_page)

        if hasattr(main_window, "page_title"):
            main_window.page_title.setText("Déploiement VLAN/VLSM")

        if hasattr(main_window, "update_active_button"):
            # La page de déploiement n'est pas forcément dans le menu, donc on évite une erreur si l'index n'existe pas.
            try:
                main_window.update_active_button(main_window.stack.currentIndex())
            except Exception:
                pass

    

    # ======================================================
    # ASYNC API WORKERS
    # ======================================================

    def start_api_post(self, endpoint, payload, timeout, status_text, success_callback):
        if not hasattr(self, "api_workers"):
            self.api_workers = []

        self.status_label.setText(status_text)

        worker = APIRequestWorker(
            method="POST",
            url=f"{API_URL}{endpoint}",
            payload=payload,
            timeout=timeout
        )

        self.api_workers.append(worker)

        worker.success.connect(success_callback)
        worker.failed.connect(self.on_api_request_failed)
        worker.finished.connect(lambda: self.cleanup_api_worker(worker))
        worker.start()

    def cleanup_api_worker(self, worker):
        try:
            if hasattr(self, "api_workers") and worker in self.api_workers:
                self.api_workers.remove(worker)
        except Exception:
            pass

    def on_api_request_failed(self, error_message):
        self.status_label.setText("Agent Active")
        QMessageBox.critical(self, "Erreur", str(error_message))

    def on_global_ai_success(self, data):
        analysis = self.extract_analysis_payload(data)

        if not analysis:
            QMessageBox.warning(
                self,
                "Réponse AI vide",
                "Le backend a répondu, mais aucun bloc analysis exploitable n'a été trouvé."
            )
            self.status_label.setText("Agent Active")
            return

        self.display_analysis(analysis)
        self.load_score_history()
        self.status_label.setText("Agent Active")

    def on_acl_ai_success(self, data):
        analysis = self.extract_analysis_payload(data)

        if not analysis:
            QMessageBox.warning(
                self,
                "Réponse AI vide",
                "Le backend a répondu, mais aucun bloc analysis ACL exploitable n'a été trouvé."
            )
            self.status_label.setText("Agent Active")
            return

        self.display_acl_analysis(analysis)
        self.status_label.setText("Agent Active")

    def on_vlan_ai_success(self, data):
        analysis = self.extract_analysis_payload(data)

        if not analysis:
            QMessageBox.warning(
                self,
                "Réponse AI vide",
                "Le backend a répondu, mais aucun bloc analysis VLAN/VLSM exploitable n'a été trouvé."
            )
            self.status_label.setText("Agent Active")
            return

        self.display_vlan_analysis(analysis)
        self.status_label.setText("Agent Active")

    def on_apply_fix_success(self, data):
        self.status_label.setText("Agent Active")
        QMessageBox.information(
            self,
            "Succès",
            "Corrections appliquées avec succès sur le switch."
        )


    # ======================================================
    # COMMON HELPERS
    # ======================================================

    def get_current_report(self):
        if isinstance(self.app_state, dict):
            report = self.app_state.get("report")
            if report:
                return self.normalize_report(report)
        return self.normalize_report(self.discovery_report)

    def send_apply_fix(self, fixes):
        if not fixes:
            QMessageBox.warning(
                self,
                "Aucune correction",
                "Aucune correction IA disponible."
            )
            return

        report = self.get_current_report()

        if not report:
            QMessageBox.warning(
                self,
                "Report manquant",
                "Aucun report réseau chargé. Lance d'abord la découverte réseau."
            )
            return

        # IMPORTANT : les identifiants sont stockés dans inventory.devices,
        # alors que topology.devices contient surtout les infos d'affichage.
        inventory_devices = report.get("inventory", {}).get("devices", [])
        topology_devices = report.get("topology", {}).get("devices", [])
        core_device = report.get("site", {}).get("core_device", {})

        devices = inventory_devices if inventory_devices else topology_devices

        if not devices:
            QMessageBox.warning(
                self,
                "Équipement manquant",
                "Aucun équipement trouvé dans le rapport de découverte."
            )
            return

        # Choisir le premier équipement joignable du rapport réel
        selected_device = None
        for device in devices:
            if device.get("reachable", True):
                selected_device = device
                break

        if selected_device is None:
            selected_device = devices[0]

        # Si le device choisi vient de topology.devices et n'a pas les credentials,
        # on cherche le même hostname/ip dans inventory.devices.
        selected_hostname = selected_device.get("hostname")
        selected_ip = selected_device.get("ip")

        if (not selected_device.get("username") or not selected_device.get("password")) and inventory_devices:
            for inv_device in inventory_devices:
                same_hostname = selected_hostname and inv_device.get("hostname") == selected_hostname
                same_ip = selected_ip and inv_device.get("ip") == selected_ip
                if same_hostname or same_ip:
                    selected_device = inv_device
                    break

        device_ip = selected_device.get("ip") or core_device.get("ip")
        username = (
            selected_device.get("username")
            or core_device.get("username")
        )
        password = (
            selected_device.get("password")
            or core_device.get("password")
        )
        secret = (
            selected_device.get("secret")
            or core_device.get("secret")
            or password
        )

        # Debug utile dans le terminal frontend
        print("\n========== APPLY FIX DEBUG ==========")
        print("SELECTED DEVICE =", selected_device)
        print("CORE DEVICE =", core_device)
        print("IP =", device_ip)
        print("USERNAME =", username)
        print("PASSWORD PRESENT =", bool(password))
        print("SECRET PRESENT =", bool(secret))
        print("=====================================\n")

        if not device_ip:
            QMessageBox.critical(
                self,
                "IP manquante",
                "Impossible d'appliquer le fix : l'adresse IP du switch est manquante dans le rapport."
            )
            return

        if not username or not password:
            QMessageBox.critical(
                self,
                "Identifiants manquants",
                "Impossible d'appliquer le fix : username/password absents du rapport de découverte.\n\n"
                "Solution : refais une Nouvelle découverte après avoir corrigé le backend pour stocker les identifiants."
            )
            return

        reply = QMessageBox.question(
            self,
            "Confirmation",
            f"Voulez-vous vraiment appliquer ces corrections sur {selected_device.get('hostname', device_ip)} ?",
            QMessageBox.Yes | QMessageBox.No
        )

        if reply == QMessageBox.No:
            return

        payload = {
            "confirm": True,
            "user_id": self.user_data.get("id", 1),
            "device": {
                "ip": device_ip,
                "username": username,
                "password": password,
                "secret": secret
            },
            "fixes": fixes
        }

        print("APPLY FIX PAYLOAD =", payload)

        self.start_api_post(
            endpoint="/ai/apply-fix",
            payload=payload,
            timeout=180,
            status_text="Application des corrections en cours...",
            success_callback=self.on_apply_fix_success
        )


    def format_fixes_as_cli(self, fixes):
        if not fixes:
            return "Aucune correction proposée."

        lines = []

        for index, fix in enumerate(fixes, start=1):
            device = fix.get("device", fix.get("affected_device", "SW-CORE-1"))
            commands = fix.get("commands", [])

            lines.append("! ===============================")
            lines.append(f"! FIX {index} - DEVICE: {device}")
            lines.append("! ===============================")

            if commands:
                for cmd in commands:
                    lines.append(str(cmd))
            else:
                lines.append("! Aucune commande disponible")

            lines.append("")

        return "\n".join(lines).strip()

    def format_fix_explanations(self, fixes):
        if not fixes:
            return "Aucune explication disponible."

        explanations = []

        for index, fix in enumerate(fixes, start=1):
            explanations.append(
                f"Fix {index}:\n{fix.get('explanation', 'Aucune explication disponible.')}"
            )

        return "\n\n".join(explanations)

    def make_icon_label(self, icon_file: str, size: int = 22):
        label = QLabel()
        label.setObjectName("iconBox")
        label.setAlignment(Qt.AlignCenter)

        pixmap = QPixmap(icon_path(icon_file))
        if not pixmap.isNull():
            label.setPixmap(
                pixmap.scaled(size, size, Qt.KeepAspectRatio, Qt.SmoothTransformation)
            )

        return label

    def title_widget(self, text: str, icon_file: str):
        wrapper = QWidget()
        wrapper.setObjectName("titleWidget")

        layout = QHBoxLayout(wrapper)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(12)

        layout.addWidget(self.make_icon_label(icon_file, 24))

        title = QLabel(text)
        title.setObjectName("cardTitle")

        layout.addWidget(title)
        layout.addStretch()

        return wrapper

    def title_row(self, text: str, icon_file: str):
        layout = QHBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(10)

        layout.addWidget(self.make_icon_label(icon_file, 22))

        title = QLabel(text)
        title.setObjectName("cardTitle")

        layout.addWidget(title)
        return layout

    def card(self, title=None):
        frame = QFrame()
        frame.setObjectName("card")
        layout = QVBoxLayout(frame)
        layout.setContentsMargins(16, 14, 16, 14)
        layout.setSpacing(10)

        if title:
            lbl = QLabel(title)
            lbl.setObjectName("cardTitle")
            layout.addWidget(lbl)

        return frame

    def metric_card(self, label, value_label, icon):
        frame = QFrame()
        frame.setObjectName("metricCard")

        layout = QHBoxLayout(frame)
        layout.setContentsMargins(12, 10, 12, 10)

        left = QVBoxLayout()

        l = QLabel(label)
        l.setObjectName("metricLabel")

        value_label.setObjectName("metricValue")

        left.addWidget(l)
        left.addWidget(value_label)

        ic = self.make_icon_label(icon, 24)

        layout.addLayout(left)
        layout.addStretch()
        layout.addWidget(ic)

        return frame

    def reset_intent_status_style(self):
        self.intent_status.setObjectName("warningBadge")
        self.intent_status.style().unpolish(self.intent_status)
        self.intent_status.style().polish(self.intent_status)

    def set_valid_intent_status_style(self):
        self.intent_status.setObjectName("successBadge")
        self.intent_status.style().unpolish(self.intent_status)
        self.intent_status.style().polish(self.intent_status)

    def add_intent(self):
        text = self.intent_input.toPlainText().strip()

        if not text:
            QMessageBox.warning(self, "Intent vide", "Veuillez saisir une intention.")
            return

        self.user_intents.append(text)
        self.intent_list.addItem(text)
        self.intent_input.clear()

        self.intent_validated = False
        self.intent_status.setText(f"{len(self.user_intents)} intent(s)")
        self.reset_intent_status_style()

    def clear_intents(self):
        self.user_intents = []
        self.intent_list.clear()
        self.intent_input.clear()
        self.intent_validated = False
        self.intent_status.setText("0 intent")
        self.reset_intent_status_style()

    def validate_intent(self):
        text = self.intent_input.toPlainText().strip()

        if text:
            self.add_intent()

        if not self.user_intents:
            QMessageBox.warning(self, "Intent vide", "Veuillez ajouter au moins une intention.")
            return

        self.intent_validated = True
        self.intent_status.setText(f"Validé ({len(self.user_intents)})")
        self.set_valid_intent_status_style()

    def auto_fill_intent(self):
        QMessageBox.information(
            self,
            "Mode réel actif",
            "Auto Intent est désactivé en mode réel.\nSaisis une intention réelle liée au report de découverte."
        )

    def get_final_user_intent(self):
        if self.user_intents:
            return "\n".join([f"- {intent}" for intent in self.user_intents])

        text = self.intent_input.toPlainText().strip()
        if not text:
            return None

        return text

    def normalize_report(self, report):
        if not isinstance(report, dict):
            return {}

        if "data" in report and isinstance(report["data"], dict):
            report = report["data"]

        if "report" in report and isinstance(report["report"], dict):
            report = report["report"]

        return report

    def set_user_data(self, user_data: dict):
        self.user_data = user_data or {}
        username = self.user_data.get("username", "Utilisateur")
        self.status_label.setText("Agent Active")
        # Le header user_info est créé localement dans create_header ; pour garder simple,
        # on met surtout à jour les données utilisées par les appels API.

    def set_app_state(self, app_state: dict):
        if isinstance(app_state, dict):
            self.app_state = app_state
            report = self.app_state.get("report")
            if report:
                self.load_discovery_report(report)

    def has_real_report(self):
        report = self.get_current_report()
        return isinstance(report, dict) and bool(report)

    def load_discovery_report(self, report: dict):
        self.discovery_report = self.normalize_report(report)
        self.app_state["report"] = self.discovery_report
        self.update_snapshot_from_report()

        if self.discovery_report:
            self.alerts_list.clear()
            self.alerts_list.addItem("Report de découverte réel chargé")

    def update_snapshot_from_report(self):
        report = self.get_current_report()

        if not report:
            self.devices_value.setText("0")
            self.vlans_value.setText("0")
            self.acls_value.setText("0")
            self.topology_label.setText("Aucun report chargé")
            return

        summary = report.get("summary", {})

        topology_devices = report.get("topology", {}).get("devices", []) or []
        inventory_devices = report.get("inventory", {}).get("devices", []) or []
        network_context = report.get("network_context", {}) or {}

        device_count = summary.get("device_count") or len(topology_devices) or len(inventory_devices)

        vlan_count = (
            summary.get("vlan_count")
            or len(network_context.get("vlans", []) or [])
            or self.count_vlans_from_devices(inventory_devices)
            or self.count_vlans_from_devices(topology_devices)
        )

        # Important :
        # Les ACL découvertes sont stockées dans inventory.devices[*].existing_acls.
        # topology.devices ne contient souvent que les infos d'affichage.
        acl_count = 0

        for device in inventory_devices:
            if not isinstance(device, dict):
                continue

            existing_acls = device.get("existing_acls", device.get("acls", []))

            if isinstance(existing_acls, list):
                acl_count += len(existing_acls)
            elif isinstance(existing_acls, dict):
                acl_count += len(existing_acls)

        # Fallback si le backend stocke aussi les ACL ailleurs.
        if acl_count == 0:
            acl_count = (
                summary.get("acl_count")
                or len(network_context.get("acls", []) or [])
                or self.count_acls_from_devices(topology_devices)
            )

        self.devices_value.setText(str(device_count))
        self.vlans_value.setText(str(vlan_count))
        self.acls_value.setText(str(acl_count))
        self.topology_label.setText(self.build_topology_text(report))

        print("AI SNAPSHOT ACL COUNT =", acl_count)

    def count_vlans_from_devices(self, devices):
        count = 0
        for device in devices:
            vlans = device.get("vlans", [])
            if isinstance(vlans, list):
                count += len(vlans)
        return count

    def count_acls_from_devices(self, devices):
        count = 0
        for device in devices:
            acls = device.get("existing_acls", device.get("acls", []))
            if isinstance(acls, list):
                count += len(acls)
        return count

    def build_topology_text(self, report=None):
        report = self.normalize_report(report or self.get_current_report())
        devices = report.get("topology", {}).get("devices", [])

        if not devices:
            return "Aucune topologie chargée"

        core = devices[0].get("hostname", "CORE-SW")
        others = devices[1:4]

        text = f"{core}\n\n"

        if others:
            text += "     ".join([f"{d.get('hostname', 'UNKNOWN')}" for d in others])
        else:
            text += "Aucun voisin découvert"

        return text

    def load_score_history(self):
        user_id = self.user_data.get("id", 1)

        try:
            response = requests.get(f"{API_URL}/ai/score-history/{user_id}", timeout=20)

            self.recent_list.clear()

            if response.status_code != 200:
                self.recent_list.addItem("Aucun historique disponible")
                return

            data = response.json()
            history = data.get("history", [])

            if not history:
                self.recent_list.addItem("Aucune analyse récente")
                return

            for item in history[-6:][::-1]:
                score = item.get("score", 0)
                timestamp = item.get("timestamp", "")
                self.recent_list.addItem(f"●   {timestamp}        {score}/100        {self.risk_label(score)}")

        except Exception:
            self.recent_list.clear()
            self.recent_list.addItem("Historique indisponible")

    def clear_global_view(self):
        self.results_table.setRowCount(0)
        self.alerts_list.clear()
        self.alerts_list.addItem("Aucune alerte IA pour le moment")
        self.fix_box.setText("Aucune correction proposée.")
        self.explanation_box.setText("Aucune explication disponible.")

    def severity_icon(self, severity):
        if severity == "HIGH":
            return "[HIGH]"
        if severity == "MEDIUM":
            return "[MEDIUM]"
        return "[LOW]"

    def risk_label(self, score):
        if score >= 80:
            return "Low Risk"
        if score >= 50:
            return "Moderate Risk"
        return "High Risk"

    def apply_style(self):
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

            QFrame#card {
                background-color: #10233F;
                border: 1px solid #1C3352;
                border-radius: 14px;
            }

            QFrame#metricCard {
                background-color: #123052;
                border: 1px solid #203855;
                border-radius: 10px;
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
                font-size: 17px;
                font-weight: 800;
                color: white;
            }

            QLabel#metricLabel {
                color: #C5D2E8;
                font-weight: 600;
            }

            QLabel#metricValue {
                font-size: 28px;
                font-weight: 900;
                color: white;
            }

            QLabel#topologyBox {
                background-color: #0E2340;
                border-radius: 10px;
                color: #8BD7FF;
                font-size: 14px;
                font-weight: 800;
            }

            QLabel#iconBox {
                background-color: #123B63;
                border: 1px solid #3BB3FF;
                border-radius: 21px;
                min-width: 42px;
                max-width: 42px;
                min-height: 42px;
                max-height: 42px;
            }

            QWidget#titleWidget {
                background-color: transparent;
                border: none;
            }

            QLabel#statusBadge {
                background-color: #0E2340;
                border: 1px solid #1E3552;
                border-radius: 18px;
                padding: 9px 18px;
                color: white;
                font-weight: 800;
            }

            QLabel#avatar {
                background-color: #3E5FAE;
                border-radius: 22px;
                font-size: 20px;
                font-weight: 900;
            }

            QLabel#warningBadge {
                color: #facc15;
                font-weight: bold;
                background-color: #0E2340;
                border: 1px solid #334155;
                border-radius: 8px;
                padding: 6px 10px;
            }

            QLabel#successBadge {
                color: #22c55e;
                font-weight: bold;
                background-color: #0B3B2A;
                border: 1px solid #14532d;
                border-radius: 8px;
                padding: 6px 10px;
            }

            QLabel#statusText {
                font-size: 16px;
                font-weight: 800;
                color: #C7F9CC;
            }

            QTextEdit {
                background-color: #0E2340;
                border: 1px solid #243D5C;
                border-radius: 9px;
                padding: 10px;
                color: white;
                font-size: 14px;
            }

            QPushButton#runAIButton {
                background: qlineargradient(
                    x1:0, y1:0, x2:1, y2:0,
                    stop:0 #2563EB,
                    stop:0.55 #3B82F6,
                    stop:1 #6D5BFF
                );
                border: 1px solid #69C8FF;
                border-radius: 18px;
                padding: 16px 26px;
                color: white;
                font-size: 15px;
                font-weight: 900;
                min-height: 64px;
                text-align: center;
            }

            QPushButton#runAIButton:hover {
                background: qlineargradient(
                    x1:0, y1:0, x2:1, y2:0,
                    stop:0 #3B82F6,
                    stop:0.55 #60A5FA,
                    stop:1 #7C6DFF
                );
                border: 1px solid #93D8FF;
            }

            QPushButton#runAIButton:pressed {
                background-color: #1D4ED8;
                border: 1px solid #3BB3FF;
            }

            QPushButton {
                background-color: #744CFF;
                border: none;
                border-radius: 9px;
                padding: 10px 18px;
                color: white;
                font-weight: 800;
                text-align: center;
            }

            QPushButton:hover {
                background-color: #8B68FF;
            }

            QPushButton#darkButton {
                background-color: #123052;
                border: 1px solid #2B4262;
                color: white;
            }

            QPushButton#deployButton {
                background-color: #16a34a;
                border: none;
                color: white;
                font-weight: 900;
            }

            QPushButton#deployButton:hover {
                background-color: #22c55e;
            }

            QTableWidget {
                background-color: #0E2340;
                border: 1px solid #243D5C;
                border-radius: 10px;
                gridline-color: #1E3552;
                color: white;
                font-size: 13px;
            }

            QTableWidget::item {
                padding: 8px;
            }

            QHeaderView::section {
                background-color: #123052;
                color: #C8D5EA;
                padding: 8px;
                border: none;
                font-weight: 800;
            }

            QListWidget {
                background-color: #0E2340;
                border: 1px solid #243D5C;
                border-radius: 8px;
                color: white;
                padding: 6px;
            }

            QTabWidget::pane {
                border: 1px solid #1C3352;
                border-radius: 14px;
                background-color: #071426;
                padding: 8px;
            }

            QTabBar::tab {
                background-color: #10233F;
                color: #BFD1F1;
                padding: 14px 26px;
                border: 1px solid #1C3352;
                min-width: 230px;
                font-weight: 800;
            }

            QTabBar::tab:selected {
                background-color: #2563EB;
                color: white;
                border-bottom: 3px solid #8B5CF6;
            }

            QProgressBar {
                background-color: #0E2340;
                border: 1px solid #243D5C;
                border-radius: 8px;
                text-align: center;
                height: 24px;
            }

            QProgressBar::chunk {
                background-color: #22c55e;
                border-radius: 8px;
            }

            QFrame#rightPanel {
                background-color: transparent;
                border: none;
            }

            QFrame#rightInfoCard {
                background: qlineargradient(
                    x1:0, y1:0, x2:1, y2:1,
                    stop:0 #0F2A4A,
                    stop:1 #0A1E36
                );
                border: 1px solid #1E4F80;
                border-radius: 16px;
            }

            QFrame#rightInfoCard:hover {
                border: 1px solid #3BB3FF;
            }

            QPushButton#runAIButton {
                background: qlineargradient(
                    x1:0, y1:0, x2:1, y2:0,
                    stop:0 #2563EB,
                    stop:0.55 #3B82F6,
                    stop:1 #6D5BFF
                );
                border: 1px solid #69C8FF;
                border-radius: 14px;
                padding: 12px 18px;
                color: white;
                font-size: 14px;
                font-weight: 900;
                min-height: 58px;
                text-align: center;
            }

            QPushButton#runAIButton:hover {
                background: qlineargradient(
                    x1:0, y1:0, x2:1, y2:0,
                    stop:0 #3B82F6,
                    stop:0.55 #60A5FA,
                    stop:1 #7C6DFF
                );
                border: 1px solid #93D8FF;
            }

            QLabel#iconBox {
                background-color: #164A7A;
                border: 1px solid #3BB3FF;
                border-radius: 22px;
                min-width: 44px;
                max-width: 44px;
                min-height: 44px;
                max-height: 44px;
            }

            QListWidget {
                background-color: #0B2340;
                border: 1px solid #1E4F80;
                border-radius: 12px;
                color: white;
                padding: 8px;
            }

            QListWidget::item {
                background-color: transparent;
                border-bottom: 1px solid rgba(105,200,255,0.08);
                padding: 7px 8px;
                color: #DDEBFF;
            }

            QListWidget::item:hover {
                background-color: #123052;
                border-radius: 8px;
            }


            QPushButton#runAIButton {
                background: qlineargradient(
                    x1:0, y1:0, x2:1, y2:0,
                    stop:0 #2563EB,
                    stop:0.6 #3B82F6,
                    stop:1 #6D5BFF
                );
                border: 1px solid #69C8FF;
                border-radius: 12px;
                padding: 8px 14px;
                color: white;
                font-size: 13px;
                font-weight: 900;
                min-height: 44px;
                max-height: 48px;
                text-align: center;
            }

            QPushButton#runAIButton:hover {
                background: qlineargradient(
                    x1:0, y1:0, x2:1, y2:0,
                    stop:0 #3B82F6,
                    stop:0.6 #60A5FA,
                    stop:1 #7C6DFF
                );
                border: 1px solid #93D8FF;
            }

            QFrame#rightInfoCard {
                background-color: #10233F;
                border: 1px solid #1E4F80;
                border-radius: 16px;
            }

            QListWidget {
                background-color: #0E2340;
                border: 1px solid #1E4F80;
                border-radius: 12px;
                color: white;
                padding: 6px;
            }

            QListWidget::item {
                background-color: transparent;
                border-bottom: 1px solid rgba(105,200,255,0.10);
                padding: 6px 8px;
                color: #DDEBFF;
                min-height: 22px;
            }

            QScrollBar:vertical {
                background: #0E2340;
                width: 8px;
                margin: 2px;
                border-radius: 4px;
            }

            QScrollBar::handle:vertical {
                background: #3B82F6;
                min-height: 24px;
                border-radius: 4px;
            }

            QScrollBar::add-line:vertical,
            QScrollBar::sub-line:vertical {
                height: 0px;
                background: transparent;
            }

        """)
