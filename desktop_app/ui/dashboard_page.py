import os

from PySide6.QtCore import Qt, QPropertyAnimation, QEasingCurve, QParallelAnimationGroup, QSize
from PySide6.QtGui import QIcon, QPixmap
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QFrame,
    QListWidget, QListWidgetItem, QPushButton,
    QGraphicsOpacityEffect, QLineEdit, QScrollArea, QMessageBox
)

from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure

from services.api_client import ApiClient


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


ICON_SIZE = QSize(22, 22)


class PremiumCard(QFrame):
    def __init__(self, title: str = "", subtitle: str = "", icon: str = ""):
        super().__init__()
        self.setObjectName("premiumCard")

        self.main_layout = QVBoxLayout(self)
        self.main_layout.setContentsMargins(18, 18, 18, 18)
        self.main_layout.setSpacing(14)

        if title:
            header = QHBoxLayout()
            header.setSpacing(10)

            if icon:
                icon_label = QLabel()
                icon_label.setObjectName("sectionIcon")
                icon_label.setAlignment(Qt.AlignCenter)

                pixmap = QPixmap(icon_path(icon))
                if not pixmap.isNull():
                    icon_label.setPixmap(
                        pixmap.scaled(22, 22, Qt.KeepAspectRatio, Qt.SmoothTransformation)
                    )

                header.addWidget(icon_label)

            title_box = QVBoxLayout()
            title_box.setSpacing(2)

            title_label = QLabel(title)
            title_label.setObjectName("cardTitle")
            title_box.addWidget(title_label)

            if subtitle:
                subtitle_label = QLabel(subtitle)
                subtitle_label.setObjectName("cardSubtitle")
                title_box.addWidget(subtitle_label)

            header.addLayout(title_box)
            header.addStretch()
            self.main_layout.addLayout(header)

    def add_widget(self, widget):
        self.main_layout.addWidget(widget)

    def add_layout(self, layout):
        self.main_layout.addLayout(layout)


class KPIBox(QFrame):
    def __init__(self, title: str, value: str, subtitle: str, icon: str):
        super().__init__()
        self.setObjectName("kpiBox")

        layout = QVBoxLayout(self)
        layout.setContentsMargins(18, 18, 18, 18)
        layout.setSpacing(8)

        top = QHBoxLayout()
        top.setSpacing(10)

        icon_label = QLabel()
        icon_label.setObjectName("kpiIcon")
        icon_label.setAlignment(Qt.AlignCenter)

        pixmap = QPixmap(icon_path(icon))
        if not pixmap.isNull():
            icon_label.setPixmap(
                pixmap.scaled(24, 24, Qt.KeepAspectRatio, Qt.SmoothTransformation)
            )

        title_label = QLabel(title)
        title_label.setObjectName("kpiTitle")

        top.addWidget(icon_label)
        top.addWidget(title_label)
        top.addStretch()

        self.value_label = QLabel(value)
        self.value_label.setObjectName("kpiValue")

        self.subtitle_label = QLabel(subtitle)
        self.subtitle_label.setObjectName("kpiSubtitle")

        layout.addLayout(top)
        layout.addWidget(self.value_label)
        layout.addWidget(self.subtitle_label)

    def set_value(self, value: str):
        self.value_label.setText(str(value))

    def set_subtitle(self, text: str):
        self.subtitle_label.setText(text)


class DashboardPage(QWidget):
    def __init__(self, user_info=None, api_client=None, main_window=None):
        super().__init__()

        self.user_info = user_info or {}
        self.user_id = self.user_info.get("id", 1)
        self.user_role = self.user_info.get("role", "viewer")
        self.token = self.user_info.get("token")
        self.main_window = main_window

        self.api_client = api_client or ApiClient()
        self.api_client.token = self.token

        self._animations = []

        self.setup_ui()
        self.apply_rbac_ui()
        self.apply_styles()

        try:
            self.load_dashboard_data()
        except Exception as e:
            print("Erreur dashboard data:", e)

        self.start_animations()

    def apply_rbac_ui(self):
        """
        Rend le dashboard dynamique selon le rôle utilisateur.

        Règles principales :
        - admin : voit tout
        - engineer : actions techniques seulement, pas santé réseau / activité IA / score IA
        - analyst : analyse et consultation, pas découverte / VLAN / VLSM / déploiement
        - viewer : consultation simple uniquement
        """
        role = str(self.user_role or self.user_info.get("role", "viewer")).lower()
        permissions = self.user_info.get("permissions", []) or []

        # Par défaut, la carte utilisateurs est réservée à l'admin.
        if role != "admin":
            self.kpi_users.hide()

        # Engineer : il gère la partie technique, pas la santé/analyse sécurité.
        if role == "engineer":
            self.kpi_score.hide()
            self.health_card.hide()
            self.ai_card.hide()
            self.btn_ai.hide()
            self.btn_monitor.hide()

        # Analyst : il consulte/analyse, mais ne fait pas la découverte ni le déploiement.
        if role == "analyst":
            self.btn_discover.hide()
            self.btn_vlan.hide()
            self.btn_vlsm.hide()
            self.btn_deploy.hide()

        # Viewer : lecture simple seulement.
        if role == "viewer":
            self.kpi_score.hide()
            self.health_card.hide()
            self.ai_card.hide()
            self.btn_discover.hide()
            self.btn_vlan.hide()
            self.btn_vlsm.hide()
            self.btn_acl.hide()
            self.btn_ai.hide()
            self.btn_deploy.hide()
            self.btn_report.hide()
            self.btn_monitor.hide()

        # Sécurité supplémentaire par permissions.
        # Même si le rôle autorise, on cache si la permission n'existe pas.
        if "discover_site" not in permissions:
            self.btn_discover.hide()

        if "create_vlan" not in permissions:
            self.btn_vlan.hide()

        if "generate_vlsm" not in permissions:
            self.btn_vlsm.hide()

        if "generate_acl" not in permissions:
            self.btn_acl.hide()

        if "validate_ai" not in permissions:
            self.btn_ai.hide()

        if "deploy_configs" not in permissions:
            self.btn_deploy.hide()

        if "generate_reports" not in permissions:
            self.btn_report.hide()

        if "view_analytics" not in permissions and "view_security_analytics" not in permissions:
            self.btn_monitor.hide()


    def setup_ui(self):
        page_layout = QVBoxLayout(self)
        page_layout.setContentsMargins(0, 0, 0, 0)
        page_layout.setSpacing(0)

        scroll = QScrollArea()
        scroll.setObjectName("dashboardScroll")
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)

        content = QWidget()
        content.setObjectName("dashboardContent")

        root = QVBoxLayout(content)
        root.setContentsMargins(18, 18, 18, 18)
        root.setSpacing(18)

        scroll.setWidget(content)
        page_layout.addWidget(scroll)

        # Barre supérieure supprimée.
        # On garde seulement un badge caché pour éviter de casser la logique notifications.
        self.notif_badge = QLabel("0")
        self.notif_badge.hide()

        self.refresh_btn = QPushButton("Actualiser")
        self.refresh_btn.setObjectName("primaryButton")
        self.refresh_btn.setIcon(QIcon(icon_path("refresh.png")))
        self.refresh_btn.setIconSize(QSize(18, 18))
        self.refresh_btn.clicked.connect(self.load_dashboard_data)

        hero = QFrame()
        hero.setObjectName("heroHeader")

        hero_layout = QHBoxLayout(hero)
        hero_layout.setContentsMargins(22, 18, 22, 18)

        left_hero = QVBoxLayout()
        left_hero.setSpacing(6)

        hero_title = QLabel("Dashboard Réseau Intelligent")
        hero_title.setObjectName("heroTitle")

        hero_subtitle = QLabel("Vue globale du backend, de l’IA, de la topologie et des notifications.")
        hero_subtitle.setObjectName("heroSubtitle")

        left_hero.addWidget(hero_title)
        left_hero.addWidget(hero_subtitle)

        # Label caché gardé pour les messages internes du dashboard.
        self.updated_label = QLabel("")
        self.updated_label.hide()

        right_hero = QHBoxLayout()
        right_hero.setSpacing(12)
        right_hero.addWidget(self.refresh_btn)

        hero_layout.addLayout(left_hero)
        hero_layout.addStretch()
        hero_layout.addLayout(right_hero)

        root.addWidget(hero)

        kpi_row = QHBoxLayout()
        kpi_row.setSpacing(16)

        self.kpi_score = KPIBox("AI Score", "0/100", "Score de sécurité", "brain.png")
        self.kpi_users = KPIBox("Utilisateurs", "0", "Visible pour admin", "user.png")
        self.kpi_alerts = KPIBox("Notifications", "0", "Événements reçus", "notification.png")
        self.kpi_role = KPIBox("Rôle actif", self.user_role, "Rôle utilisateur", "verified.png")

        kpi_row.addWidget(self.kpi_score)
        kpi_row.addWidget(self.kpi_users)
        kpi_row.addWidget(self.kpi_alerts)
        kpi_row.addWidget(self.kpi_role)

        root.addLayout(kpi_row)

        main_row = QHBoxLayout()
        main_row.setSpacing(16)

        self.topology_card = PremiumCard("Topologie / Graphe", "", "network.png")

        graph_area = QFrame()
        graph_area.setObjectName("graphArea")

        graph_layout = QVBoxLayout(graph_area)
        graph_layout.setContentsMargins(16, 16, 16, 16)
        graph_layout.setSpacing(10)

        # Carte simple et claire pour résumer le réseau détecté
        self.graph_visual = QFrame()
        self.graph_visual.setObjectName("networkSummaryMap")
        self.graph_visual.setMinimumHeight(170)

        summary_layout = QVBoxLayout(self.graph_visual)
        summary_layout.setContentsMargins(24, 20, 24, 20)
        summary_layout.setSpacing(12)

        top_summary = QHBoxLayout()
        top_summary.setSpacing(14)

        network_icon = QLabel()
        network_icon.setObjectName("networkSummaryIcon")
        network_icon.setAlignment(Qt.AlignCenter)

        pixmap = QPixmap(icon_path("network.png"))
        if not pixmap.isNull():
            network_icon.setPixmap(
                pixmap.scaled(32, 32, Qt.KeepAspectRatio, Qt.SmoothTransformation)
            )
        else:
            network_icon.setText("NET")

        title_box = QVBoxLayout()
        title_box.setSpacing(3)

        self.network_summary_title = QLabel("Réseau détecté")
        self.network_summary_title.setObjectName("networkSummaryTitle")

        self.network_summary_subtitle = QLabel("Résumé global de la découverte réseau")
        self.network_summary_subtitle.setObjectName("networkSummarySubtitle")

        title_box.addWidget(self.network_summary_title)
        title_box.addWidget(self.network_summary_subtitle)

        self.network_status_badge = QLabel("Connecté")
        self.network_status_badge.setObjectName("networkStatusBadge")
        self.network_status_badge.setAlignment(Qt.AlignCenter)

        top_summary.addWidget(network_icon)
        top_summary.addLayout(title_box)
        top_summary.addStretch()
        top_summary.addWidget(self.network_status_badge)

        info_row = QHBoxLayout()
        info_row.setSpacing(12)

        self.summary_devices_box = self.make_summary_box("0", "Équipements")
        self.summary_links_box = self.make_summary_box("0", "Liens LLDP")
        self.summary_vlans_box = self.make_summary_box("0", "VLANs")

        info_row.addWidget(self.summary_devices_box)
        info_row.addWidget(self.summary_links_box)
        info_row.addWidget(self.summary_vlans_box)

        self.core_info_label = QLabel("Core Switch : non identifié")
        self.core_info_label.setObjectName("coreInfoLabel")

        summary_layout.addLayout(top_summary)
        summary_layout.addLayout(info_row)
        summary_layout.addWidget(self.core_info_label)

        graph_layout.addWidget(self.graph_visual)

        self.topology_card.add_widget(graph_area)

        self.actions_card = PremiumCard("Centre de Contrôle", "", "centre_de_control.png")

        actions_grid = QHBoxLayout()
        actions_grid.setSpacing(18)

        left_actions = QVBoxLayout()
        left_actions.setSpacing(10)

        right_actions = QVBoxLayout()
        right_actions.setSpacing(10)

        self.btn_discover = self.make_action_button("Découvrir le réseau", "search.png")
        self.btn_vlan = self.make_action_button("Générer VLAN", "network.png")
        self.btn_vlsm = self.make_action_button("Générer VLSM", "ip.png")
        self.btn_acl = self.make_action_button("Générer ACL", "verified.png")

        self.btn_ai = self.make_action_button("Valider avec IA", "brain.png")
        self.btn_deploy = self.make_action_button("Déployer le réseau", "shuttle.png")
        self.btn_report = self.make_action_button("Générer un rapport", "report.png")
        self.btn_monitor = self.make_action_button("Ouvrir la supervision", "monitor.png")

        left_actions.addWidget(self.btn_discover)
        left_actions.addWidget(self.btn_vlan)
        left_actions.addWidget(self.btn_vlsm)
        left_actions.addWidget(self.btn_acl)

        right_actions.addWidget(self.btn_ai)
        right_actions.addWidget(self.btn_deploy)
        right_actions.addWidget(self.btn_report)
        right_actions.addWidget(self.btn_monitor)

        actions_grid.addLayout(left_actions)
        actions_grid.addLayout(right_actions)

        self.actions_card.add_layout(actions_grid)

        self.notifications_card = PremiumCard("Notifications récentes", "", "notification.png")

        notif_meta = QHBoxLayout()
        notif_meta.setSpacing(8)

        self.notif_status = QLabel("Connecté")
        self.notif_status.setObjectName("notifStatus")

        self.notif_channel = QLabel("API : /notifications")
        self.notif_channel.setObjectName("notifChannel")

        notif_meta.addWidget(self.notif_status)
        notif_meta.addWidget(self.notif_channel)
        notif_meta.addStretch()

        self.notifications_list = QListWidget()
        self.notifications_list.setObjectName("notificationsList")
        self.notifications_list.setMinimumHeight(260)

        self.notifications_card.add_layout(notif_meta)
        self.notifications_card.add_widget(self.notifications_list)

        main_row.addWidget(self.topology_card, 2)
        main_row.addWidget(self.actions_card, 2)
        main_row.addWidget(self.notifications_card, 2)

        root.addLayout(main_row)

        bottom_row = QHBoxLayout()
        bottom_row.setSpacing(16)

        self.health_card = PremiumCard("Santé du réseau", "", "health.png")
        self.ai_card = PremiumCard("Activité IA", "", "brain.png")

        self.build_health_card()
        self.build_ai_card()

        bottom_row.addWidget(self.health_card, 2)
        bottom_row.addWidget(self.ai_card, 3)

        root.addLayout(bottom_row)

        self.connect_action_buttons()

        self.animated_cards = [
            hero,
            self.kpi_score,
            self.kpi_users,
            self.kpi_alerts,
            self.kpi_role,
            self.topology_card,
            self.actions_card,
            self.notifications_card,
            self.health_card,
            self.ai_card,
        ]

    def make_summary_box(self, value: str, label: str):
        box = QFrame()
        box.setObjectName("summaryMetricBox")

        layout = QVBoxLayout(box)
        layout.setContentsMargins(10, 8, 10, 8)
        layout.setSpacing(2)

        value_label = QLabel(str(value))
        value_label.setObjectName("summaryMetricValue")
        value_label.setAlignment(Qt.AlignCenter)

        text_label = QLabel(label)
        text_label.setObjectName("summaryMetricLabel")
        text_label.setAlignment(Qt.AlignCenter)

        layout.addWidget(value_label)
        layout.addWidget(text_label)

        box.value_label = value_label
        return box

    def make_action_button(self, text, icon_file):
        btn = QPushButton(text)
        btn.setObjectName("actionButton")
        btn.setIcon(QIcon(icon_path(icon_file)))
        btn.setIconSize(ICON_SIZE)
        return btn

    def connect_action_buttons(self):
        """
        Connecte les boutons du dashboard aux vraies pages de l'application.

        Cette méthode remplace les anciens :
            print("Discovery"), print("VLAN"), ...

        Elle appelle navigate_to_page() avec plusieurs alias possibles pour
        rester compatible avec ton MainWindow même si les pages ont des noms
        légèrement différents.
        """
        self.btn_discover.clicked.connect(
            lambda: self.navigate_to_page(
                "Discovery",
                ["discovery", "discover", "network_discovery", "DiscoveryPage", "Découverte"]
            )
        )

        self.btn_vlan.clicked.connect(
            lambda: self.navigate_to_page(
                "VLAN/VLSM",
                ["vlan_vlsm", "vlan", "vlans", "VlanVlsmPage", "VLANPage"]
            )
        )

        self.btn_vlsm.clicked.connect(
            lambda: self.navigate_to_page(
                "VLAN/VLSM",
                ["vlan_vlsm", "vlsm", "VlanVlsmPage", "VLSMPage"]
            )
        )

        self.btn_acl.clicked.connect(
            lambda: self.navigate_to_page(
                "ACL",
                ["acl", "security_acl", "ACLPage", "AclPage"]
            )
        )

        self.btn_ai.clicked.connect(
            lambda: self.navigate_to_page(
                "Analyse IA",
                ["ai", "ai_analysis", "ai_validate", "AIPage", "AiPage"]
            )
        )

        self.btn_deploy.clicked.connect(
            lambda: self.navigate_to_page(
                "Déploiement",
                ["deploy", "deployment", "DeployPage", "DeploymentPage"]
            )
        )

        self.btn_report.clicked.connect(
            lambda: self.navigate_to_page(
                "Rapports",
                ["reports", "report", "ReportsPage", "ReportPage"]
            )
        )

        self.btn_monitor.clicked.connect(
            lambda: self.navigate_to_page(
                "Supervision",
                ["security_analytics", "analytics", "monitoring", "supervision", "SecurityAnalyticsPage"]
            )
        )

    def get_main_window(self):
        """
        Retourne la fenêtre principale.

        Priorité :
        1. self.main_window si elle est passée au constructeur
        2. self.window() si DashboardPage est déjà attachée à MainWindow
        """
        if self.main_window is not None:
            return self.main_window

        try:
            window = self.window()
            if window is not self:
                return window
        except Exception:
            pass

        return None

    def navigate_to_page(self, display_name, aliases):
        """
        Navigation robuste vers une page.

        Compatible avec plusieurs architectures de MainWindow :
        - show_page("page_name")
        - navigate_to_page("page_name")
        - change_page("page_name")
        - set_current_page("page_name")
        - open_page("page_name")
        - QStackedWidget + dictionnaire self.pages
        - QStackedWidget + attributs de pages
        """
        main_window = self.get_main_window()

        if main_window is None:
            QMessageBox.information(
                self,
                "Navigation",
                f"Impossible d'ouvrir la page {display_name} : fenêtre principale introuvable."
            )
            return

        # 1) Si MainWindow expose une méthode de navigation
        method_names = [
            "show_page",
            "navigate_to_page",
            "change_page",
            "set_current_page",
            "open_page",
            "go_to_page",
            "switch_page",
        ]

        for method_name in method_names:
            method = getattr(main_window, method_name, None)

            if callable(method):
                for alias in aliases:
                    try:
                        method(alias)
                        return
                    except TypeError:
                        # Certaines méthodes ne prennent peut-être pas de paramètre.
                        continue
                    except Exception:
                        # On teste l'alias suivant sans casser l'application.
                        continue

        # 2) Si MainWindow utilise un dictionnaire pages = {"discovery": widget, ...}
        pages_dict = getattr(main_window, "pages", None)

        if isinstance(pages_dict, dict):
            for alias in aliases:
                widget = pages_dict.get(alias)

                if widget is not None and self.set_stacked_widget_current(main_window, widget):
                    return

        # 3) Si MainWindow a un dictionnaire page_indexes = {"discovery": 2, ...}
        page_indexes = getattr(main_window, "page_indexes", None)

        if isinstance(page_indexes, dict):
            for alias in aliases:
                index = page_indexes.get(alias)

                if isinstance(index, int) and self.set_stacked_widget_index(main_window, index):
                    return

        # 4) Si les pages existent comme attributs : self.discovery_page, self.acl_page...
        possible_widget_attrs = []

        for alias in aliases:
            base = str(alias).lower()

            possible_widget_attrs.extend([
                base,
                f"{base}_page",
                f"page_{base}",
            ])

        for attr_name in possible_widget_attrs:
            widget = getattr(main_window, attr_name, None)

            if widget is not None and self.set_stacked_widget_current(main_window, widget):
                return

        QMessageBox.information(
            self,
            "Navigation",
            (
                f"Le bouton est connecté, mais je n'ai pas trouvé la page {display_name} "
                "dans MainWindow.\n\n"
                "Solution : ajoute dans MainWindow une méthode show_page(page_name), "
                "ou passe main_window au DashboardPage."
            )
        )

    def find_stacked_widget(self, main_window):
        """
        Cherche le QStackedWidget principal dans MainWindow avec plusieurs noms possibles.
        """
        possible_names = [
            "stack",
            "stacked_widget",
            "stackedWidget",
            "pages_stack",
            "content_stack",
            "main_stack",
            "central_stack",
        ]

        for name in possible_names:
            stack = getattr(main_window, name, None)

            if stack is not None and hasattr(stack, "setCurrentWidget"):
                return stack

        return None

    def set_stacked_widget_current(self, main_window, widget):
        stack = self.find_stacked_widget(main_window)

        if stack is None:
            return False

        try:
            stack.setCurrentWidget(widget)
            return True
        except Exception:
            return False

    def set_stacked_widget_index(self, main_window, index):
        stack = self.find_stacked_widget(main_window)

        if stack is None:
            return False

        try:
            stack.setCurrentIndex(index)
            return True
        except Exception:
            return False

    def build_health_card(self):
        health_wrap = QHBoxLayout()
        health_wrap.setSpacing(18)

        gauge_box = QFrame()
        gauge_box.setObjectName("miniPanel")

        gauge_layout = QVBoxLayout(gauge_box)
        gauge_layout.setContentsMargins(16, 16, 16, 16)

        self.health_score = QLabel("0%")
        self.health_score.setObjectName("healthScore")
        self.health_score.setAlignment(Qt.AlignCenter)

        health_global = QLabel("Global")
        health_global.setObjectName("healthGlobal")
        health_global.setAlignment(Qt.AlignCenter)

        gauge_layout.addStretch()
        gauge_layout.addWidget(self.health_score)
        gauge_layout.addWidget(health_global)
        gauge_layout.addStretch()

        legends = QVBoxLayout()
        legends.setSpacing(10)

        self.legend_healthy = QLabel("Sain 0%")
        self.legend_warning = QLabel("Avertissement 0%")
        self.legend_critical = QLabel("Critique 0%")
        self.legend_unknown = QLabel("Inconnu 0%")

        for lbl in [
            self.legend_healthy,
            self.legend_warning,
            self.legend_critical,
            self.legend_unknown
        ]:
            lbl.setObjectName("legendLabel")
            legends.addWidget(lbl)

        legends.addStretch()

        health_wrap.addWidget(gauge_box, 1)
        health_wrap.addLayout(legends, 1)

        self.health_card.add_layout(health_wrap)

    def build_ai_card(self):
        ai_graph = QFrame()
        ai_graph.setObjectName("miniPanel")

        ai_graph_layout = QVBoxLayout(ai_graph)
        ai_graph_layout.setContentsMargins(16, 16, 16, 16)

        self.ai_figure = Figure(figsize=(6, 3), dpi=100)
        self.ai_canvas = FigureCanvas(self.ai_figure)
        self.ai_canvas.setObjectName("aiCanvas")
        self.ai_canvas.setMinimumHeight(230)

        metrics = QHBoxLayout()
        metrics.setSpacing(14)

        self.ai_analyses_value = QLabel("0")
        self.ai_predictions_value = QLabel("0")
        self.ai_automations_value = QLabel("0")

        for value_widget, label in [
            (self.ai_analyses_value, "Analyses"),
            (self.ai_predictions_value, "Score moyen"),
            (self.ai_automations_value, "Dernier score")
        ]:
            box = QVBoxLayout()

            value_widget.setObjectName("miniValue")

            l = QLabel(label)
            l.setObjectName("miniLabel")

            box.addWidget(value_widget)
            box.addWidget(l)

            metrics.addLayout(box)

        ai_graph_layout.addWidget(self.ai_canvas)
        ai_graph_layout.addLayout(metrics)

        self.ai_card.add_widget(ai_graph)

    def load_dashboard_data(self):
        self.load_summary_from_backend()
        self.load_real_notifications()

    def load_summary_from_backend(self):
        result = self.call_api("get_dashboard_summary")
        print("dashboard result =", result)

        if not result.get("success"):
            print("Dashboard summary error:", result.get("error"))
            self.updated_label.setText("Backend indisponible")
            self.draw_ai_score_graph([])
            return

        payload = result.get("data", {})
        if isinstance(payload, dict) and "data" in payload and isinstance(payload.get("data"), dict):
            data = payload.get("data", {})
        else :
            data = payload    

        ai_score = self.normalize_score_value(data.get("ai_score", 0))
        users_count = int(data.get("users_count", 0) or 0)
        alerts_count = int(data.get("notifications_count", 0) or 0)
        unread_count = int(data.get("unread_notifications", 0) or 0)
        role = data.get("role", self.user_role)

        device_count = int(data.get("device_count", 0) or 0)
        link_count = int(data.get("link_count", 0) or 0)
        vlan_count = int(data.get("vlan_count", 0) or 0)

        ai_history = data.get("ai_history", [])

        self.kpi_score.set_value(f"{ai_score}/100")
        self.kpi_users.set_value(users_count if role == "admin" else "—")
        self.kpi_alerts.set_value(alerts_count)
        self.kpi_role.set_value(role)
        self.notif_badge.setText(str(unread_count))

        self.summary_devices_box.value_label.setText(str(device_count))
        self.summary_links_box.value_label.setText(str(link_count))
        self.summary_vlans_box.value_label.setText(str(vlan_count))

        if device_count > 0:
            self.network_summary_title.setText("Réseau détecté")
            self.network_summary_subtitle.setText(f"{device_count} équipements détectés dans l’architecture")
            self.network_status_badge.setText("Actif")
            self.core_info_label.setText("Core Switch : détecté depuis le rapport de découverte")
        else:
            self.network_summary_title.setText("Aucune topologie chargée")
            self.network_summary_subtitle.setText("Lance une découverte réseau pour charger les équipements")
            self.network_status_badge.setText("Vide")
            self.core_info_label.setText("Core Switch : non identifié")

        if ai_score >= 80:
            self.kpi_score.set_subtitle("Très bon niveau")
        elif ai_score >= 50:
            self.kpi_score.set_subtitle("Niveau moyen")
        else:
            self.kpi_score.set_subtitle("À améliorer")

        healthy, warning_percent, critical_percent, unknown = self.normalize_health_parts(data)

        self.health_score.setText(f"{healthy}%")
        self.legend_healthy.setText(f"Sain {healthy}%")
        self.legend_warning.setText(f"Avertissement {warning_percent}%")
        self.legend_critical.setText(f"Critique {critical_percent}%")
        self.legend_unknown.setText(f"Inconnu {unknown}%")

        values = self.normalize_score_list(ai_history)
        total_analyses = len(values)

        if values:
            avg_score = sum(values) // len(values)
            last_score = values[-1]
        else:
            avg_score = 0
            last_score = 0

        self.ai_analyses_value.setText(str(total_analyses))
        self.ai_predictions_value.setText(str(avg_score))
        self.ai_automations_value.setText(str(last_score))

        self.draw_ai_score_graph(ai_history)

        self.updated_label.setText("Données chargées")

    def normalize_health_parts(self, data: dict):
        healthy = self.normalize_score_value(data.get("healthy_percent", 0))
        warning = self.normalize_score_value(data.get("warning_percent", 0))
        critical = self.normalize_score_value(data.get("critical_percent", 0))
        unknown = self.normalize_score_value(data.get("unknown_percent", 0))

        total = healthy + warning + critical + unknown

        if total == 0:
            health_percent = self.normalize_score_value(data.get("health_percent", 0))
            return health_percent, 0, 0, max(0, 100 - health_percent)

        if total != 100:
            factor = 100 / total
            healthy = int(round(healthy * factor))
            warning = int(round(warning * factor))
            critical = int(round(critical * factor))
            unknown = max(0, 100 - healthy - warning - critical)

        total = healthy + warning + critical + unknown

        if total != 100:
            diff = 100 - total
            unknown = max(0, unknown + diff)

        return healthy, warning, critical, unknown

    def normalize_score_value(self, value):
        try:
            score = float(value or 0)
        except Exception:
            score = 0

        if 0 < score <= 1:
            score = score * 100

        return max(0, min(100, int(round(score))))

    def normalize_score_list(self, scores):
        raw_values = []

        for item in scores or []:
            try:
                value = item.get("score", 0) if isinstance(item, dict) else item
                value = float(value or 0)
                if value > 0:
                    raw_values.append(value)
            except Exception:
                pass

        if raw_values and max(raw_values) <= 1:
            raw_values = [value * 100 for value in raw_values]

        return [max(0, min(100, int(round(value)))) for value in raw_values]

    def draw_ai_score_graph(self, scores):
        self.ai_figure.clear()

        ax = self.ai_figure.add_subplot(111)
        ax.set_facecolor("#081321")
        self.ai_figure.patch.set_facecolor("#081321")

        values = self.normalize_score_list(scores)

        if not values:
            ax.text(
                0.5,
                0.5,
                "Aucune donnée IA",
                ha="center",
                va="center",
                color="white",
                fontsize=10
            )
            ax.set_xticks([])
            ax.set_yticks([])
        else:
            values = values[-15:]
            x = list(range(1, len(values) + 1))

            ax.plot(x, values, marker="o", linewidth=2)

            if len(values) > 1:
                ax.fill_between(x, values, alpha=0.2)
                ax.set_xlim(1, len(values))
            else:
                ax.set_xlim(0, 2)
                ax.set_xticks([1])

            ax.set_ylim(0, 100)
            ax.set_title("Évolution du score IA", color="white", fontsize=10, pad=8)
            ax.set_ylabel("Score", color="white", fontsize=8)
            ax.set_xlabel("Analyses", color="white", fontsize=8)
            ax.tick_params(colors="white", labelsize=8)
            ax.grid(True, alpha=0.2)

        for spine in ax.spines.values():
            spine.set_color("#1c3554")

        self.ai_figure.tight_layout()
        self.ai_canvas.draw()

    def build_topology_ascii(self, device_count: int) -> str:
        if device_count <= 0:
            return "Aucune topologie chargée"

        if device_count == 1:
            return "◎"

        if device_count <= 3:
            return "◉ ─ ◎ ─ ◉"

        if device_count <= 6:
            return (
                "    ◉       ◉\n\n"
                "  ◉    ◎    ◉\n\n"
                "    ◉       ◉"
            )

        return (
            "  ◉     ◉     ◉\n\n"
            "◉    ◉  ◎  ◉    ◉\n\n"
            "  ◉     ◉     ◉"
        )

    def load_real_notifications(self):
        self.notifications_list.clear()

        result = self.call_api("get_notifications")

        if not result.get("success"):
            self.notifications_list.addItem("Impossible de charger les notifications")
            return

        notifications = result.get("data", {}).get("notifications", [])[:6]

        if not notifications:
            item = QListWidgetItem("Aucune notification récente")
            item.setForeground(Qt.white)
            self.notifications_list.addItem(item)
            self.notif_badge.setText("0")
            return

        unread = 0

        for notif in notifications:
            level = str(notif.get("type", "info")).upper()
            title = notif.get("title", "Notification")
            message = notif.get("message", "")
            is_read = int(notif.get("is_read", 0))

            if is_read == 0:
                unread += 1

            text = f"[{level}] {title} - {message}"

            item = QListWidgetItem(text)

            if level in ["CRITICAL", "ERROR"]:
                item.setForeground(Qt.red)
                item.setIcon(QIcon(icon_path("error.png")))
            elif level == "WARNING":
                item.setForeground(Qt.yellow)
                item.setIcon(QIcon(icon_path("warning.png")))
            elif level == "SUCCESS":
                item.setForeground(Qt.green)
                item.setIcon(QIcon(icon_path("success.png")))
            else:
                item.setForeground(Qt.white)
                item.setIcon(QIcon(icon_path("notification.png")))

            self.notifications_list.addItem(item)

        self.notif_badge.setText(str(unread))

    def call_api(self, method_name, *args):
        if hasattr(self.api_client, method_name):
            return getattr(self.api_client, method_name)(*args)

        return {
            "success": False,
            "error": f"Méthode API manquante : {method_name}"
        }

    def add_notification(self, data: dict):
        notif_type = str(data.get("type", "INFO")).upper()
        message = data.get("message", "Notification reçue")

        item = QListWidgetItem(f"[{notif_type}] {message}")

        if notif_type in ["CRITICAL", "ERROR"]:
            item.setForeground(Qt.red)
            item.setIcon(QIcon(icon_path("error.png")))
        elif notif_type == "WARNING":
            item.setForeground(Qt.yellow)
            item.setIcon(QIcon(icon_path("warning.png")))
        elif notif_type == "SUCCESS":
            item.setForeground(Qt.green)
            item.setIcon(QIcon(icon_path("success.png")))
        else:
            item.setForeground(Qt.white)
            item.setIcon(QIcon(icon_path("notification.png")))

        self.notifications_list.insertItem(0, item)

        try:
            current = int(self.kpi_alerts.value_label.text())
        except Exception:
            current = 0

        self.kpi_alerts.set_value(current + 1)

        try:
            badge = int(self.notif_badge.text())
        except Exception:
            badge = 0

        self.notif_badge.setText(str(badge + 1))

        while self.notifications_list.count() > 10:
            self.notifications_list.takeItem(self.notifications_list.count() - 1)

    def start_animations(self):
        group = QParallelAnimationGroup(self)

        for widget in self.animated_cards:
            if widget.isHidden():
                continue

            effect = QGraphicsOpacityEffect(widget)
            effect.setOpacity(0.0)
            widget.setGraphicsEffect(effect)

            anim = QPropertyAnimation(effect, b"opacity", self)
            anim.setDuration(700)
            anim.setStartValue(0.0)
            anim.setEndValue(1.0)
            anim.setEasingCurve(QEasingCurve.OutCubic)

            group.addAnimation(anim)
            self._animations.append(anim)

        group.start()
        self._animations.append(group)

    def apply_styles(self):
        self.setStyleSheet("""
            QWidget {
                background-color: #061120;
                color: #edf3ff;
                font-family: Arial, sans-serif;
            }

            QLabel {
                background: transparent;
            }

            QScrollArea#dashboardScroll {
                border: none;
                background-color: #061120;
            }

            QWidget#dashboardContent {
                background-color: #061120;
            }

            QFrame#topbar {
                background-color: #081a31;
                border: 1px solid #1c3554;
                border-radius: 20px;
            }

            #topbarTitle {
                font-size: 18px;
                font-weight: 800;
                color: white;
            }

            #searchInput {
                background-color: #081321;
                border: 1px solid #1c3554;
                border-radius: 12px;
                min-width: 280px;
                min-height: 42px;
                padding: 0 14px;
                color: white;
            }

            #notifBadge {
                background-color: #e94560;
                color: white;
                min-width: 22px;
                max-width: 22px;
                min-height: 22px;
                max-height: 22px;
                border-radius: 11px;
                font-size: 11px;
                font-weight: 700;
            }

            QFrame#heroHeader {
                background-color: #08182e;
                border: 1px solid #163457;
                border-radius: 18px;
            }

            #heroTitle {
                font-size: 26px;
                font-weight: 800;
                color: white;
            }

            #heroSubtitle {
                font-size: 14px;
                color: #98afd3;
            }

            #liveBadge {
                background-color: rgba(59,179,255,0.12);
                color: #69c8ff;
                border: 1px solid #2e5f8f;
                border-radius: 10px;
                padding: 8px 12px;
                font-size: 12px;
                font-weight: 700;
            }

            #updatedLabel {
                color: #43d17a;
                font-size: 13px;
                font-weight: 700;
            }

            QFrame#premiumCard {
                background-color: #10233f;
                border: 1px solid rgba(255,255,255,0.06);
                border-radius: 20px;
            }

            QFrame#premiumCard:hover {
                border: 1px solid #3bb3ff;
            }

            QFrame#kpiBox {
                background: qlineargradient(
                    x1:0, y1:0, x2:1, y2:1,
                    stop:0 #0f2239,
                    stop:1 #122a4d
                );
                border: 1px solid rgba(255,255,255,0.07);
                border-radius: 18px;
                min-height: 112px;
            }

            #kpiIcon, #sectionIcon {
                min-width: 40px;
                max-width: 40px;
                min-height: 40px;
                max-height: 40px;
                border-radius: 20px;
                background-color: rgba(59,179,255,0.14);
            }

            #kpiTitle, #cardTitle {
                font-size: 16px;
                font-weight: 800;
                color: #dce8ff;
            }

            #cardSubtitle {
                font-size: 12px;
                color: #8ca7cf;
            }

            #kpiValue {
                font-size: 30px;
                font-weight: 800;
                color: white;
            }

            #kpiSubtitle {
                font-size: 13px;
                color: #8ea7cb;
            }

            #graphArea, #miniPanel {
                background-color: #081321;
                border: 1px solid #1c3554;
                border-radius: 16px;
            }

            #networkSummaryMap {
                background-color: #081321;
                border: 1px solid #1c3554;
                border-radius: 16px;
                min-height: 170px;
            }

            #networkSummaryIcon {
                background-color: rgba(59,179,255,0.14);
                border: 1px solid #28547a;
                border-radius: 20px;
                min-width: 44px;
                max-width: 44px;
                min-height: 44px;
                max-height: 44px;
                color: #53b6ff;
                font-size: 11px;
                font-weight: 800;
            }

            #networkSummaryTitle {
                color: white;
                font-size: 17px;
                font-weight: 900;
            }

            #networkSummarySubtitle {
                color: #9db7dc;
                font-size: 12px;
            }

            #networkStatusBadge {
                background-color: rgba(67,209,122,0.14);
                color: #43d17a;
                border: 1px solid #2c7f53;
                border-radius: 10px;
                padding: 6px 12px;
                font-size: 12px;
                font-weight: 800;
                min-width: 72px;
            }

            #summaryMetricBox {
                background-color: #0e2340;
                border: 1px solid #28476d;
                border-radius: 14px;
                min-height: 62px;
            }

            #summaryMetricValue {
                color: white;
                font-size: 22px;
                font-weight: 900;
            }

            #summaryMetricLabel {
                color: #9db7dc;
                font-size: 11px;
                font-weight: 700;
            }

            #coreInfoLabel {
                color: #69c8ff;
                font-size: 12px;
                font-weight: 700;
                padding-top: 4px;
            }

            #graphStat {
                font-size: 14px;
                font-weight: 700;
                color: white;
            }

            #graphLink {
                color: #53b6ff;
                font-size: 13px;
                font-weight: 700;
            }

            #actionButton {
                background-color: #0e2340;
                color: #e6f0ff;
                border: 1px solid #28476d;
                border-radius: 14px;
                min-height: 52px;
                max-height: 52px;
                text-align: left;
                padding: 10px 14px;
                font-weight: 700;
            }

            #actionButton:hover {
                background-color: #1a3b63;
                border: 1px solid #3bb3ff;
                color: white;
            }

            #notifStatus {
                background-color: rgba(67,209,122,0.14);
                color: #43d17a;
                border: 1px solid #2c7f53;
                border-radius: 10px;
                padding: 6px 10px;
                font-size: 12px;
                font-weight: 700;
            }

            #notifChannel {
                background-color: #0c1d33;
                color: #9db7dc;
                border: 1px solid #234362;
                border-radius: 10px;
                padding: 6px 10px;
                font-size: 12px;
            }

            QListWidget#notificationsList, QListWidget {
                background-color: #081321;
                border: 1px solid #1c3554;
                border-radius: 12px;
                color: white;
                padding: 8px;
            }

            QListWidget::item {
                padding: 10px 8px;
                border-bottom: 1px solid rgba(255,255,255,0.05);
            }

            #healthScore {
                font-size: 36px;
                font-weight: 800;
                color: #47d17a;
            }

            #healthGlobal, #legendLabel, #miniLabel {
                color: #9db7dc;
                font-size: 13px;
            }

            #miniValue {
                color: white;
                font-size: 26px;
                font-weight: 800;
            }

            #primaryButton {
                background-color: #3bb3ff;
                color: #08111f;
                border: none;
                border-radius: 12px;
                min-height: 44px;
                font-weight: 800;
                padding: 10px 20px;
            }

            #primaryButton:hover {
                background-color: #69c8ff;
            }
        """)