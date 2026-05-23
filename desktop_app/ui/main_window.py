from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QMainWindow, QWidget, QHBoxLayout, QVBoxLayout,
    QLabel, QPushButton, QFrame, QStackedWidget
)

from ui.acceuil import HomePage
from ui.users_page import UsersPage
from ui.dashboard_page import DashboardPage
from ui.discovery_page import DiscoveryPage
from ui.vlan_vlsm_page import VlanVlsmPage
from ui.ai_analysis_page import AIAnalysisPage
from ui.security_analytics_page import SecurityAnalyticsPage
from ui.general_analytics import GeneralAnalyticsPage
from ui.acl_page import ACLPage
from ui.deploy_acl_page import DeployAclPage
from ui.deploy_vlan_vlsm_page import DeployVlanVlsmPage
from ui.notification_page import NotificationsPage
from ui.audit_logs_page import AuditLogsPage
from ui.reports_page import ReportsPage
from services.api_client import ApiClient


# ==================== MAPPING DES PERMISSIONS (CORRIGÉ) ====================
ROLE_PERMISSIONS = {
    "admin": [
        "manage_users", "view_dashboard", "view_alerts", "view_reports",
        "discover_site", "generate_vlsm", "create_vlan", "generate_acl",
        "render_config", "deploy_configs", "deploy_acl", "validate_ai",
        "view_analytics", "view_audit_logs", "generate_reports",
        "architecture_list", "architecture_view", "architecture_delete"
    ],
    "engineer": [
        "view_dashboard", "view_alerts", "view_reports",
        "discover_site", "generate_vlsm", "generate_acl", "create_vlan",
        "render_config", "deploy_configs", "deploy_acl", "validate_ai",
        "architecture_list", "architecture_view", "generate_reports",
        "view_audit_logs"
    ],
    "analyst": [
        "view_dashboard", "view_alerts", "view_analytics", "view_reports",
        "validate_ai", "view_audit_logs", "architecture_list", "architecture_view","discover_site"
    ],
    "viewer": [
        "view_dashboard", "view_reports", "view_alerts"
    ]
}


class MainWindow(QMainWindow):
    def __init__(self, user_data=None):
        super().__init__()

        self.user_data = user_data or {}
        self.user_role = self.user_data.get("role", "viewer").lower()
        self.username = self.user_data.get("username", "unknown")
        
        # Chargement dynamique des permissions
        self.permissions = (
            self.user_data.get("permissions",[])

        )
        print("USER_DATA =", self.user_data)
        print("PERMISSIONS =", self.permissions)

        self.page_history = []
        self.api = ApiClient()
        self.api.token = self.user_data.get("token")

        self.app_state = {
            "report": None, "acl_plan": None, "generated_config": None,
            "ai_validation": None, "deployment": None, "vlan_deployment": None,
        }

        self.setWindowTitle("NetAutoAI - Dashboard")
        self.resize(1400, 850)

        self.setup_ui()
        self.apply_role_permissions()
        self.apply_styles()

    def has_permission(self, permission: str) -> bool:
        return permission in self.permissions

    def can_open_page(self, permission: str | None) -> bool:
        if permission is None:
            return True
        return self.has_permission(permission)

    def setup_ui(self):
        central = QWidget()
        self.setCentralWidget(central)

        root = QHBoxLayout(central)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        # ==================== SIDEBAR ====================
        sidebar = QFrame()
        sidebar.setObjectName("sidebar")
        sidebar.setFixedWidth(260)

        sidebar_layout = QVBoxLayout(sidebar)
        sidebar_layout.setContentsMargins(20, 20, 20, 20)
        sidebar_layout.setSpacing(8)

        logo = QLabel("NetAutoAI")
        logo.setObjectName("logo")

        subtitle = QLabel("Network Automation Platform")
        subtitle.setObjectName("logoSub")

        self.user_label = QLabel(f"Connecté : {self.username} ({self.user_role})")
        self.user_label.setObjectName("userLabel")

        # Boutons de navigation
        self.btn_home = QPushButton("Accueil")
        self.btn_dashboard = QPushButton("Dashboard")
        self.btn_discovery = QPushButton("Découverte Réseau")
        self.btn_vlan_vlsm = QPushButton("VLAN / VLSM Planner")
        self.btn_acl = QPushButton("ACL Intelligent Engine")
        self.btn_users = QPushButton("Utilisateurs")
        self.btn_reports = QPushButton("Rapports")
        self.btn_ai = QPushButton("AI Analysis")
        self.btn_security_analytics = QPushButton("Security Analytics")
        self.btn_general_analytics = QPushButton("General Analytics")
        self.btn_notifications = QPushButton("Notifications")
        self.btn_audit_logs = QPushButton("Audit Logs")

        self.nav_buttons = [
            self.btn_home, self.btn_dashboard, self.btn_discovery, self.btn_vlan_vlsm,
            self.btn_acl, self.btn_users, self.btn_reports, self.btn_ai,
            self.btn_security_analytics, self.btn_general_analytics,
            self.btn_notifications, self.btn_audit_logs
        ]

        for btn in self.nav_buttons:
            btn.setObjectName("navButton")
            btn.setCursor(Qt.PointingHandCursor)

        # Construction sidebar
        sidebar_layout.addWidget(logo)
        sidebar_layout.addWidget(subtitle)
        sidebar_layout.addWidget(self.user_label)
        sidebar_layout.addSpacing(20)

        for btn in self.nav_buttons:
            sidebar_layout.addWidget(btn)

        sidebar_layout.addStretch()

        # ==================== CONTENT ====================
        content = QFrame()
        content.setObjectName("content")

        content_layout = QVBoxLayout(content)
        content_layout.setContentsMargins(20, 20, 20, 20)
        content_layout.setSpacing(16)

        # Topbar
        topbar = QFrame()
        topbar.setObjectName("topbar")
        topbar_layout = QHBoxLayout(topbar)
        topbar_layout.setContentsMargins(18, 12, 18, 12)

        self.page_title = QLabel("Accueil")
        self.page_title.setObjectName("topTitle")

        self.btn_back = QPushButton("Retour")
        self.btn_back.setObjectName("topButton")
        self.btn_back.clicked.connect(self.go_back)

        self.btn_reload = QPushButton("Reload")
        self.btn_reload.setObjectName("topButton")
        self.btn_reload.clicked.connect(self.reload_current_page)

        topbar_layout.addWidget(self.page_title)
        topbar_layout.addStretch()
        topbar_layout.addWidget(self.btn_back)
        topbar_layout.addWidget(self.btn_reload)

        # Stack des pages
        self.stack = QStackedWidget()

        self.page_welcome = HomePage(user_data=self.user_data, parent_stack=self.stack, main_window=self)
        self.page_dashboard_widget = DashboardPage(self.user_data)
        self.page_discovery_widget = DiscoveryPage(self.user_data)
        self.page_vlan_vlsm_widget = VlanVlsmPage(user_data=self.user_data, api_client=self.api, parent_stack=self.stack)
        self.page_acl_widget = ACLPage(api_client=self.api, report=None)
        self.page_users_widget = UsersPage(self.user_data)
        self.page_reports_widget = ReportsPage(api_client=self.api, current_user=self.user_data)
        self.page_ai_analysis = AIAnalysisPage(user_data=self.user_data, discovery_report=None, api_client=self.api)
        self.page_deploy_acl = DeployAclPage(api_client=self.api, user_data=self.user_data)
        self.page_deploy_vlan_vlsm = DeployVlanVlsmPage(api_client=self.api, user_data=self.user_data)
        self.page_security_analytics = SecurityAnalyticsPage(user_data=self.user_data)
        self.page_general_analytics = GeneralAnalyticsPage(user_data=self.user_data, api_client=self.api)
        self.page_notifications = NotificationsPage(api_client=self.api, parent=self)
        self.page_audit_logs = AuditLogsPage(api_client=self.api, user_data=self.user_data)

        for page in [
            self.page_dashboard_widget, self.page_discovery_widget, self.page_vlan_vlsm_widget,
            self.page_acl_widget, self.page_users_widget, self.page_reports_widget,
            self.page_ai_analysis, self.page_deploy_acl, self.page_deploy_vlan_vlsm,
            self.page_security_analytics, self.page_general_analytics,
            self.page_notifications, self.page_audit_logs
        ]:
            page.app_state = self.app_state

        # Liens inter-pages
        self.page_discovery_widget.vlan_vlsm_page = self.page_vlan_vlsm_widget
        self.page_discovery_widget.acl_page = self.page_acl_widget
        self.page_discovery_widget.ai_page = self.page_ai_analysis

        self.page_acl_widget.ai_page = self.page_ai_analysis
        self.page_acl_widget.parent_stack = self.stack

        self.page_vlan_vlsm_widget.ai_page = self.page_ai_analysis
        self.page_vlan_vlsm_widget.parent_stack = self.stack

        self.page_ai_analysis.deploy_acl_page = self.page_deploy_acl
        self.page_ai_analysis.deploy_vlan_vlsm_page = self.page_deploy_vlan_vlsm
        self.page_ai_analysis.parent_stack = self.stack
        self.page_ai_analysis.analytics_page = self.page_security_analytics
        self.page_dashboard_widget.ai_page = self.page_ai_analysis

        # Ajout au stack
        self.stack.addWidget(self.page_welcome)           # 0
        self.stack.addWidget(self.page_dashboard_widget)  # 1
        self.stack.addWidget(self.page_discovery_widget)  # 2
        self.stack.addWidget(self.page_vlan_vlsm_widget)  # 3
        self.stack.addWidget(self.page_acl_widget)        # 4
        self.stack.addWidget(self.page_users_widget)      # 5
        self.stack.addWidget(self.page_ai_analysis)       # 6
        self.stack.addWidget(self.page_deploy_acl)        # 7
        self.stack.addWidget(self.page_deploy_vlan_vlsm)  # 8
        self.stack.addWidget(self.page_security_analytics)# 9
        self.stack.addWidget(self.page_notifications)     # 10
        self.stack.addWidget(self.page_audit_logs)        # 11
        self.stack.addWidget(self.page_general_analytics) # 12
        self.stack.addWidget(self.page_reports_widget)    # 13

        content_layout.addWidget(topbar)
        content_layout.addWidget(self.stack)

        root.addWidget(sidebar)
        root.addWidget(content)

        # ==================== CONNEXIONS ====================
        self.btn_home.clicked.connect(lambda: self.switch_page(0, "Accueil"))
        self.btn_dashboard.clicked.connect(lambda: self.switch_page(1, "Dashboard", "view_dashboard"))
        self.btn_discovery.clicked.connect(lambda: self.switch_page(2, "Découverte Réseau", "discover_site"))
        self.btn_vlan_vlsm.clicked.connect(lambda: self.switch_page(3, "VLAN / VLSM Planner", "generate_vlsm"))
        self.btn_acl.clicked.connect(lambda: self.switch_page(4, "ACL Intelligent Engine", "generate_acl"))
        self.btn_users.clicked.connect(lambda: self.switch_page(5, "Gestion des Utilisateurs", "manage_users"))
        self.btn_reports.clicked.connect(lambda: self.switch_page(13, "Rapports", "view_reports"))
        self.btn_ai.clicked.connect(lambda: self.switch_page(6, "AI Analysis", "validate_ai"))
        self.btn_security_analytics.clicked.connect(lambda: self.switch_page(9, "Security Analytics", "view_security_analytics"))
        self.btn_general_analytics.clicked.connect(lambda: self.switch_page(12, "General Analytics", "view_general_analytics"))
        self.btn_notifications.clicked.connect(lambda: self.switch_page(10, "Notifications", "view_alerts"))
        self.btn_audit_logs.clicked.connect(lambda: self.switch_page(11, "Audit Logs", "view_audit_logs"))

        if hasattr(self.page_welcome, "login_clicked"):
            self.page_welcome.login_clicked.connect(lambda: self.switch_page(1, "Dashboard", "view_dashboard"))

        self.switch_page(0, "Accueil", add_to_history=False)

    # ======================= NAVIGATION =======================
    def switch_page(self, index: int, title: str, permission: str | None = None, add_to_history: bool = True):
        if not self.can_open_page(permission):
            self.page_title.setText("Accès refusé")
            return

        if add_to_history and self.stack.currentIndex() != index:
            self.page_history.append(self.stack.currentIndex())

        self.stack.setCurrentIndex(index)
        self.page_title.setText(title)
        self.update_active_button(index)
        self.update_navigation_buttons()

    def go_back(self):
        if not self.page_history:
            return
        last_index = self.page_history.pop()
        titles = {
            0: "Accueil", 1: "Dashboard", 2: "Découverte Réseau", 3: "VLAN / VLSM Planner",
            4: "ACL Intelligent Engine", 5: "Gestion des Utilisateurs", 6: "AI Analysis",
            7: "Déploiement ACL", 8: "Déploiement VLAN/VLSM", 9: "Security Analytics",
            10: "Notifications", 11: "Audit Logs", 12: "General Analytics", 13: "Rapports"
        }
        self.stack.setCurrentIndex(last_index)
        self.page_title.setText(titles.get(last_index, "NetAutoAI"))
        self.update_active_button(last_index)
        self.update_navigation_buttons()

    def reload_current_page(self):
        widget = self.stack.currentWidget()
        for m in ["load_data", "refresh", "load_reports", "load_logs", "refresh_data", "load_analytics"]:
            if hasattr(widget, m):
                getattr(widget, m)()
                return

    def update_active_button(self, index: int):
        mapping = {
            0: self.btn_home, 1: self.btn_dashboard, 2: self.btn_discovery,
            3: self.btn_vlan_vlsm, 4: self.btn_acl, 5: self.btn_users,
            6: self.btn_ai, 9: self.btn_security_analytics, 10: self.btn_notifications,
            11: self.btn_audit_logs, 12: self.btn_general_analytics, 13: self.btn_reports
        }
        for btn in self.nav_buttons:
            btn.setProperty("active", False)
            btn.style().unpolish(btn)
            btn.style().polish(btn)

        if active_btn := mapping.get(index):
            active_btn.setProperty("active", True)
            active_btn.style().unpolish(active_btn)
            active_btn.style().polish(active_btn)

    def update_navigation_buttons(self):
        self.btn_back.setEnabled(len(self.page_history) > 0)

    # ======================= DYNAMISME SELON RÔLE =======================
    def apply_role_permissions(self):
        """Rend l'interface dynamique selon le rôle"""
        self.btn_home.setVisible(True)

        self.btn_dashboard.setVisible(self.has_permission("view_dashboard"))
        self.btn_discovery.setVisible(self.has_permission("discover_site"))
        self.btn_vlan_vlsm.setVisible(self.has_permission("generate_vlsm"))
        self.btn_acl.setVisible(self.has_permission("generate_acl"))
        self.btn_users.setVisible(self.has_permission("manage_users"))
        self.btn_reports.setVisible(self.has_permission("view_reports"))
        self.btn_ai.setVisible(self.has_permission("validate_ai"))
        self.btn_security_analytics.setVisible(self.has_permission("view_security_analytics"))
        self.btn_general_analytics.setVisible(self.has_permission("view_general_analytics"))
        self.btn_notifications.setVisible(self.has_permission("view_alerts"))
        self.btn_audit_logs.setVisible(self.has_permission("view_audit_logs"))

        self.update_navigation_buttons()

    def apply_styles(self):
        self.setStyleSheet("""
            QWidget {
                background-color: #09111f;
                color: white;
                font-family: Arial, sans-serif;
            }
            #sidebar {
                background-color: #07101c;
                border-right: 1px solid #13253f;
            }
            #logo {
                font-size: 26px;
                font-weight: 800;
                color: #eef4ff;
            }
            #logoSub {
                color: #8ea5c9;
                font-size: 13px;
            }
            #userLabel {
                color: #9ec5ff;
                font-size: 13px;
                padding: 8px 0;
            }
            #navButton {
                text-align: left;
                padding: 14px 16px;
                border-radius: 12px;
                border: none;
                background: transparent;
                color: #dce8ff;
                font-weight: 600;
                min-height: 42px;
            }
            #navButton:hover {
                background: #0e2647;
            }
            #navButton[active="true"] {
                background-color: #2c2470;
                color: white;
                border-left: 4px solid #7c61ff;
            }
            #content { background-color: #0b1424; }
            #topbar {
                background-color: #0d1a2d;
                border: 1px solid #183252;
                border-radius: 18px;
            }
            #topTitle { font-size: 24px; font-weight: 800; }
            #topButton {
                background-color: #1e3a5f;
                border: 1px solid #334155;
                border-radius: 10px;
                color: white;
                padding: 8px 16px;
                font-weight: 700;
            }
            #topButton:hover { background-color: #2563eb; }
        """)