from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton,
    QGraphicsView, QGraphicsScene, QGraphicsItem,
    QGraphicsTextItem, QGraphicsLineItem, QLabel, QFrame,
    QGraphicsDropShadowEffect, QLineEdit, QFormLayout,
    QDialog, QScrollArea, QTabWidget, QTableWidget,
    QTableWidgetItem, QHeaderView, QComboBox, QMessageBox
)
from PySide6.QtCore import Qt, QRectF, QTimer, QSize, QThread, Signal
from PySide6.QtGui import QBrush, QColor, QPen, QPainter, QIcon

from services.api_client import ApiClient
from services.websocket_client import NotificationWebSocketClient

import os


BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def get_notification_icon_path():
    possible_paths = [
        os.path.join(BASE_DIR, "assets", "icons", "notification.png"),
        os.path.join(BASE_DIR, "assets", "icones", "notification.png"),
    ]

    for path in possible_paths:
        if os.path.exists(path):
            return path

    return None


icon_path = get_notification_icon_path()


def normalize_device_role(device: dict) -> str:
    """
    Normalise le rôle affiché dans la topologie.

    Objectif principal :
    - Un routeur découvert via pfSense/LLDP peut arriver côté frontend avec
      role absent, UNKNOWN ou NODE.
    - On force alors ROUTER à partir du hostname/model/platform.
    - Les switches SW-* restent SWITCH/ACCESS_SWITCH/CORE_SWITCH et ne sont
      pas transformés en ROUTER même s'ils annoncent une capability Router.
    """
    if not isinstance(device, dict):
        return "UNKNOWN"

    role = str(device.get("role") or "").strip().upper()
    hostname = str(device.get("hostname") or device.get("name") or "").strip()
    model = str(device.get("model") or "").strip()
    platform = str(device.get("platform") or device.get("vendor") or "").strip()

    hostname_upper = hostname.upper()
    text = f"{hostname} {model} {platform} {role}".lower()

    # Priorité aux switches : un switch L3 peut annoncer Router en LLDP,
    # mais visuellement il doit rester SWITCH.
    if hostname_upper.startswith("SW-") or "switch" in text or "catalyst" in text:
        if "core" in hostname_upper.lower() or "core" in text:
            return "CORE_SWITCH"
        if "distribution" in text or "dist" in text:
            return "DISTRIBUTION_SWITCH"
        if "access" in text:
            return "ACCESS_SWITCH"
        return "SWITCH"

    # Firewalls.
    if "firewall" in text or "pfsense" in text or "opnsense" in text or "freebsd" in text:
        return "FIREWALL"

    # Routeurs.
    if (
        role in ["ROUTER", "EDGE_ROUTER"]
        or hostname_upper.startswith("R-")
        or hostname_upper.startswith("R1")
        or "router" in text
        or "internet" in text
        or "7206" in text
        or "7200" in text
        or "2811" in text
        or "1921" in text
        or "2901" in text
        or "2911" in text
        or "1941" in text
        or "4331" in text
    ):
        return "ROUTER"

    if role and role not in ["UNKNOWN", "NODE", "NONE", "NULL", "-"]:
        return role

    return "UNKNOWN"



class DiscoveryWorker(QThread):
    finished_signal = Signal(dict)
    error_signal = Signal(str)

    def __init__(self, api, payload):
        super().__init__()
        self.api = api
        self.payload = payload

    def run(self):
        try:
            result = self.api.discover_network(self.payload)
            self.finished_signal.emit(result)
        except Exception as e:
            self.error_signal.emit(str(e))


class GraphView(QGraphicsView):
    def __init__(self):
        super().__init__()
        self.setRenderHint(QPainter.Antialiasing)
        self.setDragMode(QGraphicsView.ScrollHandDrag)
        self.setTransformationAnchor(QGraphicsView.AnchorUnderMouse)
        self.setResizeAnchor(QGraphicsView.AnchorUnderMouse)

    def wheelEvent(self, event):
        factor = 1.15 if event.angleDelta().y() > 0 else 1 / 1.15
        self.scale(factor, factor)


class LinkItem(QGraphicsLineItem):
    def __init__(self, node1, node2):
        super().__init__()
        self.node1 = node1
        self.node2 = node2
        self.setPen(QPen(QColor("#22c55e"), 2))
        self.setZValue(-1)
        self.update_position()

        node1.links.append(self)
        node2.links.append(self)

    def update_position(self):
        self.setLine(
            self.node1.pos().x(),
            self.node1.pos().y(),
            self.node2.pos().x(),
            self.node2.pos().y()
        )


class NodeItem(QGraphicsItem):
    def __init__(self, x, y, device, on_click_callback=None):
        super().__init__()

        self.device = device
        self.links = []
        self.on_click_callback = on_click_callback

        self.hostname = device.get("hostname", "device")
        self.role = normalize_device_role(device)
        self.device["role"] = self.role
        self.reachable = device.get("reachable", False)

        self.base_color = self.get_role_color()
        self.border_color = QColor("#ffffff")
        self.pulse_state = False

        self.setPos(x, y)
        self.setAcceptHoverEvents(True)

        self.setFlag(QGraphicsItem.ItemIsMovable, True)
        self.setFlag(QGraphicsItem.ItemIsSelectable, True)
        self.setFlag(QGraphicsItem.ItemSendsGeometryChanges, True)

        self.label = QGraphicsTextItem(self.hostname, self)
        self.label.setDefaultTextColor(Qt.white)
        self.label.setPos(-42, -10)

        self.setToolTip(self.build_tooltip())

        if self.reachable:
            self.add_glow()
        else:
            self.start_down_pulse()

    def boundingRect(self):
        shape = self.get_shape_type()

        if shape == "switch":
            return QRectF(-48, -28, 96, 56)

        if shape == "firewall":
            return QRectF(-38, -38, 76, 76)

        return QRectF(-38, -38, 76, 76)

    def paint(self, painter, option, widget=None):
        painter.setRenderHint(QPainter.Antialiasing)

        brush = QBrush(self.base_color)
        pen = QPen(self.border_color, 2)

        if self.isSelected():
            pen = QPen(QColor("#facc15"), 3)

        painter.setBrush(brush)
        painter.setPen(pen)

        shape = self.get_shape_type()

        if shape == "switch":
            painter.drawRoundedRect(QRectF(-48, -28, 96, 56), 12, 12)
            painter.drawText(QRectF(-42, 8, 84, 18), Qt.AlignCenter, "SWITCH")

        elif shape == "firewall":
            painter.drawRoundedRect(QRectF(-38, -38, 76, 76), 8, 8)
            painter.drawText(QRectF(-35, 12, 70, 18), Qt.AlignCenter, "FW")

        elif shape == "router":
            painter.drawEllipse(QRectF(-38, -38, 76, 76))
            painter.drawText(QRectF(-35, 12, 70, 18), Qt.AlignCenter, "RTR")

        else:
            painter.drawEllipse(QRectF(-35, -35, 70, 70))
            painter.drawText(QRectF(-32, 12, 64, 18), Qt.AlignCenter, "NODE")

    def get_shape_type(self):
        role = self.role.upper()

        if "FIREWALL" in role:
            return "firewall"
        if "ROUTER" in role:
            return "router"
        if "SWITCH" in role or "CORE" in role or "DISTRIBUTION" in role or "ACCESS" in role:
            return "switch"

        return "unknown"

    def get_role_color(self):
        if not self.reachable:
            return QColor("#6b7280")

        role_colors = {
            "SITE_CORE": "#2563eb",
            "CORE": "#2563eb",
            "CORE_SWITCH": "#2563eb",
            "DISTRIBUTION": "#7c3aed",
            "DISTRIBUTION_SWITCH": "#7c3aed",
            "ACCESS": "#06b6d4",
            "ACCESS_SWITCH": "#06b6d4",
            "ROUTER": "#22c55e",
            "EDGE_ROUTER": "#22c55e",
            "FIREWALL": "#ef4444",
            "FIREWALL_CORE": "#ef4444",
            "SERVER": "#f97316",
            "UNKNOWN": "#64748b"
        }

        return QColor(role_colors.get(self.role, "#64748b"))

    def build_tooltip(self):
        vlans = self.device.get("vlans", [])
        acls = self.device.get("existing_acls", [])

        vlan_count = len(vlans) if isinstance(vlans, list) else 0
        acl_count = len(acls) if isinstance(acls, list) else 0
        status = "Joignable" if self.reachable else "Non joignable"

        return (
            f"Hostname : {self.device.get('hostname', '-')}\n"
            f"IP : {self.device.get('ip', '-')}\n"
            f"Rôle : {self.device.get('role', '-')}\n"
            f"Modèle : {self.device.get('model', '-')}\n"
            f"État : {status}\n"
            f"VLANs : {vlan_count}\n"
            f"ACLs : {acl_count}"
        )

    def add_glow(self):
        glow = QGraphicsDropShadowEffect()
        glow.setBlurRadius(24)
        glow.setColor(self.base_color)
        glow.setOffset(0, 0)
        self.setGraphicsEffect(glow)

    def start_down_pulse(self):
        self.timer = QTimer()
        self.timer.timeout.connect(self.toggle_down_pulse)
        self.timer.start(650)

    def stop_timer(self):
        """
        Arrête le timer du NodeItem avant la suppression de la scène.

        Correction du bug :
        RuntimeError: libshiboken: Internal C++ object (NodeItem) already deleted
        """
        try:
            if hasattr(self, "timer") and self.timer:
                self.timer.stop()
                self.timer.deleteLater()
                self.timer = None
        except RuntimeError:
            self.timer = None

    def toggle_down_pulse(self):
        try:
            self.pulse_state = not self.pulse_state
            self.border_color = QColor("#ef4444") if self.pulse_state else QColor("#ffffff")
            self.update()
        except RuntimeError:
            self.stop_timer()

    def mark_alert(self):
        self.base_color = QColor("#ef4444")
        self.border_color = QColor("#facc15")
        self.add_glow()
        self.update()

    def itemChange(self, change, value):
        if change == QGraphicsItem.ItemPositionChange:
            for link in self.links:
                link.update_position()

        return super().itemChange(change, value)

    def mousePressEvent(self, event):
        if self.on_click_callback:
            self.on_click_callback(self.device)

        super().mousePressEvent(event)


class DiscoveryPage(QWidget):
    def __init__(self, user_data=None):
        super().__init__()

        self.user_data = user_data or {}

        self.api = ApiClient()
        self.api.token = self.user_data.get("token")

        self.user_id = self.user_data.get("id", 1)
        self.node_map = {}
        self.current_report = {}
        self.discovery_report = {}
        self.last_discovery_payload = None
        self.discovery_worker = None

        # Ces références seront reliées depuis main_window.py
        # Exemple : self.discovery_page.acl_page = self.acl_page
        self.vlan_vlsm_page = None
        self.ai_page = None
        self.acl_page = None

        self.notifications = []
        self.unread_notifications = 0
        self.websocket_status = "Déconnecté"

        self.ws_client = NotificationWebSocketClient(self.user_id)
        self.ws_client.message_received.connect(self.on_notification_received)
        self.ws_client.status_changed.connect(self.on_ws_status_changed)
        self.ws_client.connect_to_server()

        self.setup_ui()
        self.apply_rbac_ui()
        self.show_start_message()

        permissions = self.user_data.get("permissions", [])

        if "architecture_list" in permissions:
            self.load_saved_sites()
        else:
            self.report_status.setText("Accès restreint selon vos permissions")
            self.report_text.setText(
                "Vous n'avez pas la permission de consulter les architectures sauvegardées."
            )


    def apply_rbac_ui(self):
        """
        Applique les permissions RBAC côté interface.

        Important :
        - On cache les boutons non autorisés.
        - Les actions restent aussi protégées dans les fonctions.

        Règle demandée :
        - Le rôle analyst ne doit jamais voir le bouton "Nouvelle découverte",
          même si la permission discover_site existe encore dans le token.
        """
        permissions = self.user_data.get("permissions", [])
        role = self.user_data.get("role", "").lower()

        # Cacher le bouton de découverte pour l'analyst
        if role == "analyst":
            self.btn_discover.hide()
        elif "discover_site" not in permissions:
            self.btn_discover.hide()

        if "architecture_delete" not in permissions:
            self.btn_delete_site.hide()

        if "architecture_list" not in permissions:
            self.btn_refresh.hide()
            self.site_selector.hide()

    def setup_ui(self):
        self.setStyleSheet("""
            QWidget {
                background-color: #020617;
                color: white;
            }
            QPushButton {
                background-color: #0f172a;
                color: white;
                border: 1px solid #1e293b;
                border-radius: 8px;
                padding: 8px;
            }
            QPushButton:hover {
                background-color: #1e293b;
            }
            QLineEdit, QComboBox {
                background-color: #0f172a;
                color: white;
                border: 1px solid #334155;
                border-radius: 7px;
                padding: 8px;
            }
        """)

        main_layout = QVBoxLayout(self)
        main_layout.setSpacing(10)

        header = QFrame()
        header.setStyleSheet("""
            QFrame {
                background-color: #07111f;
                border: 1px solid #143150;
                border-radius: 14px;
                padding: 8px;
            }
        """)
        header_layout = QHBoxLayout(header)

        title_box = QVBoxLayout()

        title = QLabel("Graph Network Explorer")
        title.setStyleSheet("font-size: 18px; font-weight: bold; color: white;")

        self.subtitle_label = QLabel("Topologie du site : -")
        self.subtitle_label.setStyleSheet("color: #94a3b8; font-size: 12px;")

        title_box.addWidget(title)
        title_box.addWidget(self.subtitle_label)

        header_layout.addLayout(title_box)
        header_layout.addStretch()

        self.site_selector = QComboBox()
        self.site_selector.setFixedWidth(260)
        self.site_selector.currentIndexChanged.connect(self.load_selected_site)
        header_layout.addWidget(QLabel("Site sauvegardé :"))
        header_layout.addWidget(self.site_selector)

        self.btn_delete_site = QPushButton("Supprimer")
        self.btn_delete_site.setFixedHeight(36)
        self.btn_delete_site.clicked.connect(self.delete_selected_site)
        header_layout.addWidget(self.btn_delete_site)

        self.ws_status_dot = QLabel("●")
        self.ws_status_dot.setStyleSheet("color: #ef4444; font-size: 16px;")
        header_layout.addWidget(self.ws_status_dot)

        self.ws_status_text = QLabel("Déconnecté")
        self.ws_status_text.setStyleSheet("color: #94a3b8; font-size: 12px;")
        header_layout.addWidget(self.ws_status_text)

        self.btn_discover = QPushButton("Nouvelle découverte")
        self.btn_discover.setFixedHeight(36)
        self.btn_discover.clicked.connect(self.open_discovery_dialog)
        header_layout.addWidget(self.btn_discover)

        self.btn_refresh = QPushButton("Actualiser")
        self.btn_refresh.setFixedHeight(36)
        self.btn_refresh.clicked.connect(self.refresh_graph)
        header_layout.addWidget(self.btn_refresh)

        self.notification_button = QPushButton()
        self.notification_button.setFixedSize(42, 42)
        self.notification_button.setCursor(Qt.PointingHandCursor)

        if icon_path:
            self.notification_button.setIcon(QIcon(icon_path))
            self.notification_button.setIconSize(QSize(28, 28))
        else:
            self.notification_button.setText("🔔")

        self.notification_button.setStyleSheet("""
            QPushButton {
                background-color: #0f172a;
                border: 1px solid #334155;
                border-radius: 12px;
                color: white;
                font-size: 20px;
            }
        """)

        self.notification_badge = QLabel("0", self.notification_button)
        self.notification_badge.setFixedSize(18, 18)
        self.notification_badge.setAlignment(Qt.AlignCenter)
        self.notification_badge.move(26, 0)
        self.notification_badge.setStyleSheet("""
            QLabel {
                background-color: #ef4444;
                color: white;
                border-radius: 9px;
                font-size: 10px;
                font-weight: bold;
            }
        """)
        self.notification_badge.hide()

        self.notification_button.clicked.connect(self.show_notifications_popup)
        header_layout.addWidget(self.notification_button)

        main_layout.addWidget(header)

        body_layout = QHBoxLayout()
        body_layout.setSpacing(10)
        main_layout.addLayout(body_layout, 4)

        left_panel = QFrame()
        left_panel.setFixedWidth(230)
        left_panel.setStyleSheet("""
            QFrame {
                background-color: #07111f;
                border: 1px solid #102a43;
                border-radius: 10px;
            }
        """)
        left_layout = QVBoxLayout(left_panel)

        left_title = QLabel("Équipements")
        left_title.setStyleSheet("font-size: 14px; font-weight: bold;")
        left_layout.addWidget(left_title)

        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Rechercher un équipement...")
        self.search_input.textChanged.connect(self.filter_device_list)
        left_layout.addWidget(self.search_input)

        self.device_scroll = QScrollArea()
        self.device_scroll.setWidgetResizable(True)
        self.device_scroll.setStyleSheet("border: none;")

        self.device_list_widget = QWidget()
        self.device_list_layout = QVBoxLayout(self.device_list_widget)
        self.device_list_layout.setSpacing(6)

        self.device_scroll.setWidget(self.device_list_widget)
        left_layout.addWidget(self.device_scroll)

        body_layout.addWidget(left_panel)

        center_panel = QFrame()
        center_panel.setStyleSheet("""
            QFrame {
                background-color: #07111f;
                border: 1px solid #102a43;
                border-radius: 10px;
            }
        """)
        center_layout = QVBoxLayout(center_panel)

        graph_toolbar = QHBoxLayout()

        self.site_label = QLabel("Site : -")
        self.site_label.setStyleSheet("color: #cbd5e1; font-weight: bold;")
        graph_toolbar.addWidget(self.site_label)

        graph_toolbar.addStretch()

        self.zoom_label = QLabel("Zoom : molette souris")
        self.zoom_label.setStyleSheet("color: #94a3b8; font-size: 11px;")
        graph_toolbar.addWidget(self.zoom_label)

        center_layout.addLayout(graph_toolbar)

        self.scene = QGraphicsScene()
        self.scene.setBackgroundBrush(QBrush(QColor("#06101d")))
        self.scene.setSceneRect(0, 0, 1000, 650)

        self.view = GraphView()
        self.view.setScene(self.scene)
        self.view.setStyleSheet("""
            QGraphicsView {
                border: 1px solid #1e293b;
                background-color: #06101d;
            }
        """)
        center_layout.addWidget(self.view, 1)

        legend = QLabel("● Router   ● Core   ● Distribution   ● Access   ● Firewall   ● Server   ─ Lien actif")
        legend.setStyleSheet("color: #94a3b8; font-size: 11px;")
        center_layout.addWidget(legend)

        body_layout.addWidget(center_panel, 1)

        self.info_panel = QFrame()
        self.info_panel.setFixedWidth(340)
        self.info_panel.setStyleSheet("""
            QFrame {
                background-color: #07111f;
                border: 1px solid #102a43;
                border-radius: 10px;
            }
            QLabel {
                color: white;
                font-size: 13px;
            }
        """)

        info_layout = QVBoxLayout(self.info_panel)

        self.info_title = QLabel("Détails de l’équipement")
        self.info_title.setStyleSheet("font-size: 16px; font-weight: bold; color: #38bdf8;")
        info_layout.addWidget(self.info_title)

        self.info_hostname = QLabel("Hostname : -")
        self.info_ip = QLabel("IP : -")
        self.info_role = QLabel("Rôle : -")
        self.info_model = QLabel("Modèle : -")
        self.info_status = QLabel("État : -")
        self.info_vlans = QLabel("VLANs : -")
        self.info_acls = QLabel("ACLs : -")

        info_layout.addWidget(self.info_hostname)
        info_layout.addWidget(self.info_ip)
        info_layout.addWidget(self.info_role)
        info_layout.addWidget(self.info_model)
        info_layout.addWidget(self.info_status)
        info_layout.addWidget(self.info_vlans)
        info_layout.addWidget(self.info_acls)

        self.tabs = QTabWidget()
        self.tabs.setStyleSheet("""
            QTabWidget::pane {
                border: 1px solid #102a43;
                background: #07111f;
            }
            QTabBar::tab {
                background: #0f172a;
                color: #cbd5e1;
                padding: 7px;
                margin-right: 3px;
                border-radius: 6px;
            }
            QTabBar::tab:selected {
                color: #38bdf8;
                border-bottom: 2px solid #38bdf8;
            }
            QTableWidget {
                background-color: #07111f;
                color: white;
                gridline-color: #1e293b;
                border: none;
            }
            QHeaderView::section {
                background-color: #0f172a;
                color: #cbd5e1;
                padding: 6px;
                border: none;
            }
        """)

        self.interfaces_table = QTableWidget()
        self.interfaces_table.setColumnCount(4)
        self.interfaces_table.setHorizontalHeaderLabels(["Interface", "Statut", "VLAN", "Débit"])
        self.interfaces_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)

        self.neighbors_table = QTableWidget()
        self.neighbors_table.setColumnCount(3)
        self.neighbors_table.setHorizontalHeaderLabels(["Voisin", "Interface", "Port"])
        self.neighbors_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)

        self.vlan_table = QTableWidget()
        self.vlan_table.setColumnCount(2)
        self.vlan_table.setHorizontalHeaderLabels(["VLAN", "Nom"])
        self.vlan_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)

        self.extra_info = QLabel("Sélectionne un équipement")
        self.extra_info.setWordWrap(True)
        self.extra_info.setStyleSheet("color: #cbd5e1; padding: 8px;")

        self.tabs.addTab(self.interfaces_table, "Interfaces")
        self.tabs.addTab(self.neighbors_table, "Voisins")
        self.tabs.addTab(self.vlan_table, "VLANs")
        self.tabs.addTab(self.extra_info, "Informations")

        info_layout.addWidget(self.tabs)
        info_layout.addStretch()

        body_layout.addWidget(self.info_panel)

        self.report_panel = QFrame()
        self.report_panel.setFixedHeight(190)
        self.report_panel.setStyleSheet("""
            QFrame {
                background-color: #07111f;
                border: 1px solid #102a43;
                border-radius: 10px;
            }
        """)

        report_layout = QVBoxLayout(self.report_panel)

        report_header = QHBoxLayout()

        report_title = QLabel("Rapport d’architecture")
        report_title.setStyleSheet("font-size: 15px; font-weight: bold; color: #38bdf8;")
        report_header.addWidget(report_title)
        report_header.addStretch()

        self.report_status = QLabel("Aucun rapport")
        self.report_status.setStyleSheet("color: #94a3b8;")
        report_header.addWidget(self.report_status)

        report_layout.addLayout(report_header)

        self.report_text = QLabel("Lance une découverte pour afficher le rapport.")
        self.report_text.setWordWrap(True)
        self.report_text.setStyleSheet("color: #cbd5e1; font-size: 12px;")
        report_layout.addWidget(self.report_text)

        main_layout.addWidget(self.report_panel)

    def send_report_to_connected_pages(self, report):
        """
        Envoie le report Discovery vers les autres pages.

        Objectif :
        DiscoveryPage -> VLAN/VLSM Page
        DiscoveryPage -> ACLPage
        DiscoveryPage -> AI Page

        Comme ça, quand tu fais une vraie découverte ou quand tu charges
        une architecture sauvegardée, toutes les pages utilisent le même
        report réel.
        """
        if not isinstance(report, dict) or not report:
            return

        # 1) Envoyer vers VLAN/VLSM
        if self.vlan_vlsm_page is not None:
            if hasattr(self.vlan_vlsm_page, "set_report_data"):
                self.vlan_vlsm_page.set_report_data(report)
            elif hasattr(self.vlan_vlsm_page, "set_report"):
                self.vlan_vlsm_page.set_report(report)

        # 2) Envoyer vers ACLPage
        if self.acl_page is not None:
            if hasattr(self.acl_page, "set_report"):
                self.acl_page.set_report(report)
            elif hasattr(self.acl_page, "set_report_data"):
                self.acl_page.set_report_data(report)

        # 3) Envoyer vers AI Page
        if self.ai_page is not None:
            if hasattr(self.ai_page, "load_discovery_report"):
                self.ai_page.load_discovery_report(report)
            elif hasattr(self.ai_page, "set_report"):
                self.ai_page.set_report(report)

    def load_saved_sites(self):
        permissions = self.user_data.get("permissions", [])

        if "architecture_list" not in permissions:
            self.report_status.setText("Accès restreint selon vos permissions")
            return

        if not hasattr(self.api, "get_saved_sites"):
            self.report_status.setText("ApiClient: get_saved_sites manquant")
            return

        result = self.api.get_saved_sites()

        self.site_selector.blockSignals(True)
        self.site_selector.clear()
        self.site_selector.addItem("Sélectionner un site sauvegardé", None)

        if not result.get("success"):
            self.site_selector.blockSignals(False)
            return

        sites = result.get("sites", [])

        for site in sites:
            site_id = site.get("id")
            site_name = site.get("site_name", "SITE")
            created_at = site.get("created_at", "-")
            self.site_selector.addItem(f"{site_name} | {created_at}", site_id)

        self.site_selector.blockSignals(False)

    def load_selected_site(self):
        permissions = self.user_data.get("permissions", [])

        if "architecture_list" not in permissions:
            return

        report_id = self.site_selector.currentData()

        if not report_id:
            return

        result = self.api.get_architecture_by_id(report_id)

        if not result.get("success"):
            QMessageBox.warning(
                self,
                "Erreur",
                result.get("message", "Impossible de charger l’architecture.")
            )
            return

        report = result.get("report", {})

        self.current_report = report
        self.discovery_report = report

        self.draw_graph({"report": report})
        self.report_status.setText("Architecture sauvegardée chargée")

        self.send_report_to_connected_pages(report)

    def delete_selected_site(self):
        permissions = self.user_data.get("permissions", [])

        if "architecture_delete" not in permissions:
            QMessageBox.information(
                self,
                "Accès restreint",
                "Seul l'administrateur peut supprimer une architecture."
            )
            return

        report_id = self.site_selector.currentData()

        if not report_id:
            QMessageBox.warning(self, "Erreur", "Aucun site sélectionné.")
            return

        confirm = QMessageBox.question(
            self,
            "Confirmation",
            "Voulez-vous vraiment supprimer cette architecture sauvegardée ?"
        )

        if confirm != QMessageBox.Yes:
            return

        result = self.api.delete_architecture(report_id)

        if not result.get("success"):
            QMessageBox.warning(
                self,
                "Erreur",
                result.get("message", "Suppression impossible.")
            )
            return

        QMessageBox.information(self, "Succès", "Architecture supprimée.")
        self.current_report = {}
        self.show_start_message()
        self.load_saved_sites()

    def open_discovery_dialog(self):
        permissions = self.user_data.get("permissions", [])
        role = self.user_data.get("role", "").lower()

        if role == "analyst" or "discover_site" not in permissions:
            QMessageBox.information(
                self,
                "Accès restreint",
                "Vous n'avez pas la permission de lancer une découverte réseau."
            )
            return

        dialog = QDialog(self)
        dialog.setWindowTitle("Nouvelle découverte réseau")
        dialog.resize(460, 420)

        layout = QVBoxLayout(dialog)
        title = QLabel("Nouvelle découverte réseau")
        title.setStyleSheet("font-size: 18px; font-weight: bold; color: #38bdf8;")
        layout.addWidget(title)

        form = QFormLayout()

        input_site = QLineEdit()
        input_site.setPlaceholderText("Ex: Siège-Headquarter")

        input_hostname = QLineEdit()
        input_hostname.setPlaceholderText("Ex: CORE-SW")

        input_ip = QLineEdit()
        input_ip.setPlaceholderText("Ex: 192.168.1.1")

        input_username = QLineEdit()
        input_username.setPlaceholderText("Ex: admin")

        input_password = QLineEdit()
        input_password.setPlaceholderText("Mot de passe SSH")
        input_password.setEchoMode(QLineEdit.Password)

        input_secret = QLineEdit()
        input_secret.setPlaceholderText("Secret enable")
        input_secret.setEchoMode(QLineEdit.Password)

        input_model = QLineEdit()
        input_model.setPlaceholderText("Ex: Cisco 2960")

        form.addRow("Site :", input_site)
        form.addRow("Hostname :", input_hostname)
        form.addRow("IP :", input_ip)
        form.addRow("Username :", input_username)
        form.addRow("Password :", input_password)
        form.addRow("Secret :", input_secret)
        form.addRow("Model :", input_model)

        layout.addLayout(form)

        btn_launch = QPushButton("Lancer la découverte")
        layout.addWidget(btn_launch)

        def launch():
            payload = {
                "site_name": input_site.text().strip(),
                "seed_device": {
                    "hostname": input_hostname.text().strip() or "UNKNOWN",
                    "ip": input_ip.text().strip(),
                    "username": input_username.text().strip(),
                    "password": input_password.text().strip(),
                    "secret": input_secret.text().strip(),
                    "model": input_model.text().strip()
                }
            }

            if not payload["site_name"] or not payload["seed_device"]["ip"] or not payload["seed_device"]["username"] or not payload["seed_device"]["password"]:
                self.show_scene_message("Site, IP, username et password sont obligatoires", "#ef4444")
                return

            dialog.accept()
            self.run_discovery(payload)

        btn_launch.clicked.connect(launch)
        dialog.exec()

    def build_payload_from_current_report(self):
        """
        Reconstruit automatiquement le payload de découverte à partir
        du rapport actuellement chargé.

        Objectif :
        - Si l'utilisateur a chargé une architecture sauvegardée,
          le bouton Actualiser peut relancer une vraie découverte
          sans ressaisir IP / username / password.
        """
        report = self.current_report or self.discovery_report or {}

        site = report.get("site", {})
        site_name = site.get("site_name", "SITE")

        core_device = site.get("core_device", {}) or {}

        # Fallback : prendre le premier équipement de la topologie
        if not core_device:
            devices = report.get("topology", {}).get("devices", [])
            if devices:
                core_device = devices[0]

        ip = core_device.get("ip")
        username = core_device.get("username")
        password = core_device.get("password")
        secret = core_device.get("secret") or password

        if not ip or not username or not password:
            return None

        return {
            "site_name": site_name,
            "seed_device": {
                "hostname": core_device.get("hostname", "UNKNOWN"),
                "ip": ip,
                "username": username,
                "password": password,
                "secret": secret,
                "model": core_device.get("model", "")
            }
        }

    def refresh_graph(self):
        """
        Bouton Actualiser.

        Nouvelle logique :
        - Si un payload de découverte existe, relancer une vraie découverte.
        - Sinon, reconstruire le payload depuis le rapport chargé.
        - Si impossible, recharger seulement le rapport sauvegardé.
        """
        permissions = self.user_data.get("permissions", [])

        if "architecture_list" not in permissions:
            QMessageBox.information(
                self,
                "Accès restreint",
                "Vous n'avez pas la permission de consulter les architectures."
            )
            return

        # 1) Priorité : relancer une vraie découverte réseau
        payload = self.last_discovery_payload or self.build_payload_from_current_report()

        if payload:
            self.report_status.setText("Actualisation : nouvelle découverte en cours...")
            self.show_scene_message("Actualisation de l’architecture en cours...", "#38bdf8")
            self.run_discovery(payload)
            return

        # 2) Fallback : recharger le rapport sauvegardé sélectionné
        report_id = self.site_selector.currentData()

        if report_id:
            result = self.api.get_architecture_by_id(report_id)

            if not result.get("success"):
                QMessageBox.warning(
                    self,
                    "Erreur",
                    result.get("message", "Impossible d’actualiser l’architecture.")
                )
                return

            report = result.get("report", {})

            self.current_report = report
            self.discovery_report = report

            self.draw_graph({"report": report})
            self.report_status.setText("Architecture rechargée depuis la base")
            self.send_report_to_connected_pages(report)
            return

        # 3) Dernier fallback : recharger seulement la liste
        self.load_saved_sites()

        if self.current_report:
            self.draw_graph({"report": self.current_report})
            self.send_report_to_connected_pages(self.current_report)
            self.report_status.setText("Graphe actualisé depuis les données locales")
        else:
            self.show_scene_message("Aucun site chargé à actualiser", "#facc15")
            self.report_status.setText("Aucun site chargé")

    def on_ws_status_changed(self, status):
        self.websocket_status = status
        self.ws_status_text.setText(status)

        if status == "Connecté":
            self.ws_status_dot.setStyleSheet("color: #22c55e; font-size: 16px;")
        else:
            self.ws_status_dot.setStyleSheet("color: #ef4444; font-size: 16px;")

    def on_notification_received(self, data):
        self.notifications.append(data)
        self.unread_notifications += 1
        self.update_notification_badge()

        hostname = data.get("hostname")

        if hostname and hostname in self.node_map:
            self.node_map[hostname].mark_alert()

    def update_notification_badge(self):
        if self.unread_notifications > 0:
            self.notification_badge.setText(str(self.unread_notifications))
            self.notification_badge.show()
        else:
            self.notification_badge.hide()

    def show_notifications_popup(self):
        dialog = QDialog(self)
        dialog.setWindowTitle("Notifications")
        dialog.resize(420, 420)

        dialog_layout = QVBoxLayout(dialog)
        title = QLabel("🔔 Notifications")
        title.setStyleSheet("font-size: 18px; font-weight: bold; color: #38bdf8;")
        dialog_layout.addWidget(title)

        status = QLabel(f"WebSocket : {self.websocket_status}")
        dialog_layout.addWidget(status)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)

        container = QWidget()
        container_layout = QVBoxLayout(container)

        if not self.notifications:
            container_layout.addWidget(QLabel("Aucune notification"))
        else:
            for notif in reversed(self.notifications):
                notif_type = notif.get("type", "INFO").upper()
                message = notif.get("message", "Notification")
                hostname = notif.get("hostname", "-")
                item = QLabel(f"{notif_type} | {hostname}\n{message}")
                item.setWordWrap(True)
                container_layout.addWidget(item)

        container_layout.addStretch()
        scroll.setWidget(container)
        dialog_layout.addWidget(scroll)

        self.unread_notifications = 0
        self.update_notification_badge()
        dialog.exec()

    def run_discovery(self, payload):
        """
        Lance la découverte réseau dans un QThread pour éviter
        de bloquer l'interface PySide6 pendant les appels API/SSH/NAPALM.
        """
        permissions = self.user_data.get("permissions", [])
        role = self.user_data.get("role", "").lower()

        if role == "analyst" or "discover_site" not in permissions:
            QMessageBox.information(
                self,
                "Accès restreint",
                "Vous n'avez pas la permission de lancer une découverte réseau."
            )
            return

        if self.discovery_worker is not None and self.discovery_worker.isRunning():
            QMessageBox.information(
                self,
                "Découverte en cours",
                "Une découverte réseau est déjà en cours. Veuillez attendre la fin du traitement."
            )
            return

        self.last_discovery_payload = payload

        self.btn_discover.setEnabled(False)
        self.btn_refresh.setEnabled(False)

        self.report_status.setText("Découverte réseau en cours...")
        self.show_scene_message("Découverte réseau en cours...\nVeuillez patienter.", "#38bdf8")

        self.discovery_worker = DiscoveryWorker(self.api, payload)
        self.discovery_worker.finished_signal.connect(self.on_discovery_finished)
        self.discovery_worker.error_signal.connect(self.on_discovery_error)
        self.discovery_worker.finished.connect(self.on_discovery_thread_finished)
        self.discovery_worker.start()

    def on_discovery_finished(self, result):
        try:
            if not result.get("success"):
                error = result.get("error", "Erreur inconnue")
                self.show_scene_message(f"Erreur API : {error}", "#ef4444")
                self.report_status.setText("Erreur découverte")
                return

            data = result.get("data", {})
            report = data.get("report", data) if isinstance(data, dict) else {}

            self.current_report = report
            self.discovery_report = report

            self.draw_graph({"report": report})

            if "architecture_list" in self.user_data.get("permissions", []):
                self.load_saved_sites()

            self.send_report_to_connected_pages(report)

            if self.vlan_vlsm_page is not None or self.acl_page is not None or self.ai_page is not None:
                self.report_status.setText("Rapport chargé et envoyé vers les modules connectés")
            else:
                self.report_status.setText("Rapport chargé - aucune page connectée")

        except Exception as e:
            self.show_scene_message(f"Erreur traitement résultat : {e}", "#ef4444")
            self.report_status.setText("Erreur traitement résultat")

    def on_discovery_error(self, error):
        self.show_scene_message(f"Erreur connexion backend : {error}", "#ef4444")
        self.report_status.setText("Erreur connexion backend")

    def on_discovery_thread_finished(self):
        self.btn_discover.setEnabled(True)
        self.btn_refresh.setEnabled(True)
        self.discovery_worker = None

    def clear_scene_safely(self):
        """
        Nettoie la scène en arrêtant d'abord les timers des NodeItem.

        Sans cette méthode, un ancien NodeItem supprimé par scene.clear()
        peut continuer à recevoir le signal de son QTimer.
        """
        for item in self.scene.items():
            if isinstance(item, NodeItem):
                item.stop_timer()

        self.scene.clear()

    def show_start_message(self):
        self.clear_scene_safely()
        text = QGraphicsTextItem("Clique sur 'Nouvelle découverte' pour commencer")
        text.setDefaultTextColor(QColor("#38bdf8"))
        text.setPos(260, 260)
        self.scene.addItem(text)

    def show_scene_message(self, message, color="#38bdf8"):
        self.clear_scene_safely()
        text = QGraphicsTextItem(message)
        text.setDefaultTextColor(QColor(color))
        text.setPos(260, 260)
        self.scene.addItem(text)

    def get_node_position(self, device, index_by_role):
        role = normalize_device_role(device)
        device["role"] = role

        layout_map = {
            "SITE_CORE": 120,
            "CORE": 120,
            "CORE_SWITCH": 120,
            "DISTRIBUTION": 290,
            "DISTRIBUTION_SWITCH": 290,
            "EDGE_ROUTER": 120,
            "ROUTER": 120,
            "FIREWALL": 290,
            "FIREWALL_CORE": 290,
            "ACCESS": 460,
            "ACCESS_SWITCH": 460,
            "SERVER": 610,
            "UNKNOWN": 610
        }

        y = layout_map.get(role, 610)
        index = index_by_role.get(role, 0)
        x = 180 + (index * 220)
        index_by_role[role] = index + 1

        return x, y

    def draw_graph(self, data):
        self.clear_scene_safely()
        self.node_map = {}

        report = data.get("report", {})
        self.current_report = report

        topology = report.get("topology", {})
        devices = topology.get("devices", [])
        devices = [dict(device, role=normalize_device_role(device)) for device in devices]
        links = topology.get("links", [])

        site = report.get("site", {})
        site_name = site.get("site_name", "-")

        self.subtitle_label.setText(f"Topologie du site : {site_name}")
        self.site_label.setText(f"Site : {site_name}")

        if not devices:
            self.show_scene_message("Aucun équipement découvert", "#facc15")
            return

        index_by_role = {}

        for device in devices:
            hostname = device.get("hostname", "device")
            x, y = self.get_node_position(device, index_by_role)

            node = NodeItem(x, y, device, self.show_device_info)
            self.scene.addItem(node)
            self.node_map[hostname] = node

            role_text = QGraphicsTextItem(device.get("role", "UNKNOWN"))
            role_text.setDefaultTextColor(QColor("#cbd5e1"))
            role_text.setPos(x - 45, y + 50)
            self.scene.addItem(role_text)

        for link in links:
            src = link.get("source")
            dst = link.get("target")

            if src in self.node_map and dst in self.node_map:
                self.scene.addItem(LinkItem(self.node_map[src], self.node_map[dst]))

        if not links:
            text = QGraphicsTextItem("Aucun lien détecté")
            text.setDefaultTextColor(QColor("#facc15"))
            text.setPos(260, 370)
            self.scene.addItem(text)

        rect = self.scene.itemsBoundingRect().adjusted(-120, -120, 120, 120)
        self.scene.setSceneRect(rect)
        self.view.fitInView(rect, Qt.KeepAspectRatio)

        self.fill_device_list(devices)
        self.update_report_panel(report)

        if devices:
            self.show_device_info(devices[0])

    def clear_layout(self, layout):
        while layout.count():
            item = layout.takeAt(0)
            widget = item.widget()

            if widget:
                widget.deleteLater()

    def fill_device_list(self, devices):
        self.clear_layout(self.device_list_layout)

        for device in devices:
            hostname = device.get("hostname", "-")
            ip = device.get("ip", "-")
            role = normalize_device_role(device)
            device["role"] = role
            reachable = device.get("reachable", False)

            status_dot = "🟢" if reachable else "🔴"
            btn = QPushButton(f"{status_dot}  {hostname}\n{ip}    {role}")
            btn.clicked.connect(lambda _, d=device: self.show_device_info(d))
            self.device_list_layout.addWidget(btn)

        self.device_list_layout.addStretch()

    def filter_device_list(self):
        query = self.search_input.text().lower()
        devices = self.current_report.get("topology", {}).get("devices", [])

        if not query:
            self.fill_device_list(devices)
            return

        filtered = [
            d for d in devices
            if query in str(d.get("hostname", "")).lower()
            or query in str(d.get("ip", "")).lower()
            or query in str(d.get("role", "")).lower()
        ]

        self.fill_device_list(filtered)

    def fill_interfaces_table(self, interfaces):
        self.interfaces_table.setRowCount(0)

        if not isinstance(interfaces, dict):
            return

        for row, (name, data) in enumerate(interfaces.items()):
            self.interfaces_table.insertRow(row)

            is_up = data.get("is_up", data.get("status", "").lower() == "up")
            vlan = data.get("access_vlan", data.get("vlan", "-"))
            speed = data.get("speed", data.get("debit", "-"))

            self.interfaces_table.setItem(row, 0, QTableWidgetItem(str(name)))

            status_item = QTableWidgetItem("Up" if is_up else "Down")
            status_item.setForeground(QColor("#22c55e") if is_up else QColor("#ef4444"))
            self.interfaces_table.setItem(row, 1, status_item)

            self.interfaces_table.setItem(row, 2, QTableWidgetItem(str(vlan)))
            self.interfaces_table.setItem(row, 3, QTableWidgetItem(str(speed)))

    def fill_neighbors_table(self, neighbors):
        self.neighbors_table.setRowCount(0)

        if not isinstance(neighbors, list):
            return

        for row, n in enumerate(neighbors):
            self.neighbors_table.insertRow(row)
            self.neighbors_table.setItem(row, 0, QTableWidgetItem(str(n.get("hostname", n.get("neighbor", "-")))))
            self.neighbors_table.setItem(row, 1, QTableWidgetItem(str(n.get("local_interface", "-"))))
            self.neighbors_table.setItem(row, 2, QTableWidgetItem(str(n.get("remote_interface", "-"))))

    def fill_vlan_table(self, vlans):
        self.vlan_table.setRowCount(0)

        if not isinstance(vlans, list):
            return

        for row, vlan in enumerate(vlans):
            self.vlan_table.insertRow(row)
            self.vlan_table.setItem(row, 0, QTableWidgetItem(str(vlan.get("id", vlan.get("vlan_id", "-")))))
            self.vlan_table.setItem(row, 1, QTableWidgetItem(str(vlan.get("name", vlan.get("vlan_name", "-")))))

    def show_device_info(self, device):
        status = "Joignable" if device.get("reachable", False) else "Non joignable"

        inventory_devices = self.current_report.get("inventory", {}).get("devices", [])
        inv = next(
            (d for d in inventory_devices if d.get("hostname") == device.get("hostname")),
            {}
        )

        vlans = inv.get("vlans", device.get("vlans", []))
        acls = inv.get("existing_acls", device.get("existing_acls", []))
        interfaces = inv.get("interfaces", {})
        neighbors = inv.get("neighbors", [])
        trunks = inv.get("trunks", [])
        svis = inv.get("svis", [])

        vlan_count = len(vlans) if isinstance(vlans, list) else 0
        acl_count = len(acls) if isinstance(acls, list) else 0
        interface_count = len(interfaces) if isinstance(interfaces, dict) else 0

        self.info_hostname.setText(f"Hostname : {device.get('hostname', '-')}")
        self.info_ip.setText(f"IP : {device.get('ip', '-')}")
        self.info_role.setText(f"Rôle : {normalize_device_role(device)}")
        self.info_model.setText(f"Modèle : {device.get('model', '-')}")
        self.info_status.setText(f"État : {status}")
        self.info_vlans.setText(f"VLANs : {vlan_count}")
        self.info_acls.setText(f"ACLs : {acl_count}")

        self.fill_interfaces_table(interfaces)
        self.fill_neighbors_table(neighbors)
        self.fill_vlan_table(vlans)

        self.extra_info.setText(
            f"Routing : {inv.get('routing', False)}\n"
            f"Interfaces : {interface_count}\n"
            f"Trunks : {len(trunks) if isinstance(trunks, list) else 0}\n"
            f"SVIs : {len(svis) if isinstance(svis, list) else 0}\n"
            f"ACLs : {acl_count}"
        )

    def update_report_panel(self, report):
        summary = report.get("summary", {})
        network_context = report.get("network_context", {})
        ai_context = report.get("ai_context", {})

        vlans = network_context.get("vlans", [])
        subnets = network_context.get("subnets", [])
        acl_points = network_context.get("acl_points", [])

        self.report_status.setText("Rapport chargé")

        vlan_preview = ", ".join([
            f"VLAN {v.get('vlan_id')}:{v.get('vlan_name')}"
            for v in vlans[:4]
        ]) or "Aucun VLAN détecté"

        subnet_preview = ", ".join([
            f"{s.get('subnet')} → {s.get('zone_name')}"
            for s in subnets[:3]
        ]) or "Aucun subnet détecté"

        acl_preview = ", ".join([
            f"{a.get('device')} ({a.get('type')})"
            for a in acl_points[:3]
        ]) or "Aucun point ACL"

        health = ai_context.get("topology_health_inputs", {})

        self.report_text.setText(
            f"Résumé : "
            f"{summary.get('device_count', 0)} équipements | "
            f"{summary.get('switch_count', 0)} switches | "
            f"{summary.get('subnet_count', 0)} subnets | "
            f"{summary.get('zone_count', 0)} zones | "
            f"{summary.get('acl_candidate_count', 0)} points ACL\n\n"
            f"VLANs : {vlan_preview}\n"
            f"Subnets/VLSM : {subnet_preview}\n"
            f"ACL points : {acl_preview}\n"
            f"IA : links={health.get('link_count', 0)}, "
            f"routing_devices={health.get('routing_device_count', 0)}, "
            f"firewall_present={health.get('firewall_present', False)}"
        )