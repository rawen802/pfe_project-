import os

from PySide6.QtCore import Qt, QSize
from PySide6.QtGui import QIcon, QPixmap
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QFrame, QGridLayout, QSizePolicy, QScrollArea
)


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


def image_path(file_name: str) -> str:

    possible_paths = [
        os.path.join(PROJECT_ROOT, "assets", file_name),
        os.path.join(PROJECT_ROOT, "desktop_app,", "assets", file_name),
        os.path.abspath(os.path.join(CURRENT_DIR, "..", "assets", file_name)),
        
        os.path.abspath(os.path.join(CURRENT_DIR, "assets", file_name)),
        
    ]

    for path in possible_paths:
        if os.path.exists(path):
            return path

    return possible_paths[0]


ICON_SIZE = QSize(22, 22)


class HomePage(QWidget):
    def __init__(self, user_data=None, parent_stack=None, main_window=None):
        super().__init__()

        self.user_data = user_data or {}
        self.parent_stack = parent_stack
        self.main_window = main_window

        self.setup_ui()
        self.apply_style()

    def setup_ui(self):
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(0)

        scroll = QScrollArea()
        scroll.setObjectName("homeScroll")
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        outer.addWidget(scroll)

        container = QWidget()
        container.setObjectName("homeContainer")
        scroll.setWidget(container)

        root = QVBoxLayout(container)
        root.setContentsMargins(26, 18, 26, 18)
        root.setSpacing(18)

        hero = QFrame()
        hero.setObjectName("heroCard")
        hero.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)

        hero_layout = QHBoxLayout(hero)
        hero_layout.setContentsMargins(32, 24, 32, 24)
        hero_layout.setSpacing(24)

        left = QVBoxLayout()
        left.setSpacing(12)

        badge = QLabel("PLATEFORME INTELLIGENTE")
        badge.setObjectName("badge")

        title = QLabel(
            "Automatisez et sécurisez\n"
            "votre infrastructure réseau\n"
            "avec l’intelligence artificielle"
        )
        title.setObjectName("heroTitle")
        title.setWordWrap(True)

        subtitle = QLabel(
            "NetAutoAI combine découverte réseau, analyse IA, planification intelligente "
            "et déploiement automatisé pour construire des réseaux plus sécurisés, "
            "plus fiables et plus performants."
        )
        subtitle.setObjectName("heroSubtitle")
        subtitle.setWordWrap(True)

        left.addWidget(badge, 0, Qt.AlignLeft)
        left.addWidget(title)
        left.addWidget(subtitle)
        left.addSpacing(30)
        left.addStretch()

        # Zone visuelle droite simplifiée sans image externe
        right = QFrame()
        right.setObjectName("networkVisual")
        right.setMinimumWidth(420)
        right.setMaximumHeight(260)

        visual_layout = QVBoxLayout(right)
        visual_layout.setContentsMargins(18, 14, 18, 14)
        visual_layout.setSpacing(10)

        status = QLabel("• Système actif\nBackend : Online")
        status.setObjectName("statusBadge")
        status.setAlignment(Qt.AlignRight)

        visual_layout.addWidget(status, 0, Qt.AlignRight)

        topology_box = QFrame()
        topology_box.setObjectName("topologyBox")

        topology_layout = QGridLayout(topology_box)
        topology_layout.setContentsMargins(24, 18, 24, 18)
        topology_layout.setHorizontalSpacing(20)
        topology_layout.setVerticalSpacing(14)

        topology_layout.addWidget(
            self.visual_node("FW", "verified.png", "sideNode"), 0, 0
        )
        topology_layout.addWidget(
            self.visual_node("CORE", "centre_de_control.png", "coreNode"), 0, 1
        )
        topology_layout.addWidget(
            self.visual_node("SRV", "network.png", "sideNode"), 0, 2
        )
        topology_layout.addWidget(
            self.visual_node("SW DIST", "network.png", "smallNode"), 1, 0
        )
        topology_layout.addWidget(
            self.visual_node("SW ACCESS", "network.png", "smallNode"), 1, 2
        )

        visual_layout.addWidget(topology_box)
        visual_layout.addStretch()

        hero_layout.addLayout(left, 5)
        hero_layout.addWidget(right, 4)

        root.addWidget(hero)

        root.addSpacing(22)

        modules = QGridLayout()
        modules.setSpacing(18)

        modules.addWidget(
            self.feature_card(
                title="Découverte intelligente",
                description="Détection automatique des équipements, liens, VLANs et architecture réseau.",
                icon="network.png",
                accent="blue"
            ),
            0, 0
        )

        modules.addWidget(
            self.feature_card(
                title="AI Security Engine",
                description="Analyse intelligente des ACL, détection des risques et recommandations IA.",
                icon="brain.png",
                accent="purple"
            ),
            0, 1
        )

        modules.addWidget(
            self.feature_card(
                title="VLAN / VLSM Automation",
                description="Génération automatique des VLANs, plans IP et segmentation réseau.",
                icon="bar-chart.png",
                accent="cyan"
            ),
            0, 2
        )

        modules.addWidget(
            self.feature_card(
                title="Déploiement automatisé",
                description="Déploiement sécurisé des configurations Cisco via Ansible et templates.",
                icon="shuttle.png",
                accent="green"
            ),
            0, 3
        )

        root.addLayout(modules)

        workflow = QFrame()
        workflow.setObjectName("workflowCard")
        workflow.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)

        workflow_layout = QVBoxLayout(workflow)
        workflow_layout.setContentsMargins(24, 16, 24, 16)
        workflow_layout.setSpacing(12)

        workflow_title = QLabel("Notre workflow intelligent")
        workflow_title.setObjectName("sectionTitle")
        workflow_layout.addWidget(workflow_title)

        steps = QHBoxLayout()
        steps.setSpacing(8)

        steps.addWidget(self.workflow_step("1. Découverte", "Analyse automatique\nde votre réseau", "search.png"))
        steps.addWidget(self.workflow_line())
        steps.addWidget(self.workflow_step("2. Analyse IA", "Détection des risques\net optimisation", "brain.png"))
        steps.addWidget(self.workflow_line())
        steps.addWidget(self.workflow_step("3. Planification", "Génération VLAN/VLSM\net segmentation", "bar-chart.png"))
        steps.addWidget(self.workflow_line())
        steps.addWidget(self.workflow_step("4. Sécurisation", "Validation ACL et renforcement\nde la sécurité", "verified.png"))
        steps.addWidget(self.workflow_line())
        steps.addWidget(self.workflow_step("5. Déploiement", "Déploiement automatisé\net supervision", "shuttle.png"))

        workflow_layout.addLayout(steps)

        root.addWidget(workflow)

        footer = QLabel("NetAutoAI © 2026 • AI-Powered Network Automation Platform")
        footer.setObjectName("footer")
        footer.setAlignment(Qt.AlignCenter)

        root.addWidget(footer)

    def icon_label(self, icon_file, size=34):
        label = QLabel()
        label.setAlignment(Qt.AlignCenter)

        pixmap = QPixmap(icon_path(icon_file))
        if not pixmap.isNull():
            label.setPixmap(
                pixmap.scaled(size, size, Qt.KeepAspectRatio, Qt.SmoothTransformation)
            )

        return label

    def visual_node(self, text, icon_file, object_name):
        frame = QFrame()
        frame.setObjectName(object_name)

        layout = QVBoxLayout(frame)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(6)

        layout.addWidget(self.icon_label(icon_file, 30), 0, Qt.AlignCenter)

        label = QLabel(text)
        label.setObjectName("nodeLabel")
        label.setAlignment(Qt.AlignCenter)

        layout.addWidget(label)
        return frame

    def feature_card(self, title, description, icon, accent="blue"):
        frame = QFrame()
        frame.setObjectName(f"featureCard_{accent}")

    # hauteur augmentée
        frame.setMinimumHeight(240)
        frame.setMaximumHeight(260)

        frame.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)

        layout = QVBoxLayout(frame)

    # espacements améliorés
        layout.setContentsMargins(20, 18, 20, 18)
        layout.setSpacing(14)

        icon_box = QFrame()
        icon_box.setObjectName(f"featureIcon_{accent}")
        icon_box.setFixedSize(58, 58)

        icon_layout = QVBoxLayout(icon_box)
        icon_layout.setContentsMargins(0, 0, 0, 0)

        icon_layout.addWidget(
            self.icon_label(icon, 28),
            0,
            Qt.AlignCenter
        )

        title_label = QLabel(title)
        title_label.setObjectName("featureTitle")

    # correction texte coupé
        title_label.setWordWrap(True)
        title_label.setAlignment(Qt.AlignCenter)

        desc_label = QLabel(description)
        desc_label.setObjectName("featureDesc")

    # correction description
        desc_label.setWordWrap(True)
        desc_label.setAlignment(Qt.AlignCenter)

        layout.addWidget(icon_box, 0, Qt.AlignCenter)
        layout.addWidget(title_label)
        layout.addWidget(desc_label)

        layout.addStretch()

        return frame
    def workflow_step(self, title, desc, icon):
        frame = QFrame()
        frame.setObjectName("workflowStep")

        layout = QVBoxLayout(frame)
        layout.setContentsMargins(8, 4, 8, 4)
        layout.setSpacing(8)

        circle = QFrame()
        circle.setObjectName("workflowCircle")
        circle.setFixedSize(54, 54)

        circle_layout = QVBoxLayout(circle)
        circle_layout.setContentsMargins(0, 0, 0, 0)
        circle_layout.addWidget(self.icon_label(icon, 24), 0, Qt.AlignCenter)

        title_label = QLabel(title)
        title_label.setObjectName("workflowTitle")
        title_label.setAlignment(Qt.AlignCenter)

        desc_label = QLabel(desc)
        desc_label.setObjectName("workflowDesc")
        desc_label.setAlignment(Qt.AlignCenter)

        layout.addWidget(circle, 0, Qt.AlignCenter)
        layout.addWidget(title_label)
        layout.addWidget(desc_label)

        return frame

    def workflow_line(self):
        line = QFrame()
        line.setObjectName("workflowLine")
        line.setFixedHeight(2)
        line.setMinimumWidth(45)
        return line

    def apply_style(self):
        self.setStyleSheet("""
            QWidget {
                background-color: #071426;
                color: white;
                font-family: Segoe UI;
            }

            QScrollArea#homeScroll {
                background-color: #071426;
                border: none;
            }

            QWidget#homeContainer {
                background-color: #071426;
            }

            QLabel {
                background: transparent;
            }

            QFrame#heroCard {
                min-height: 360px;
                max-height: 400px;
                background: qlineargradient(
                    x1:0, y1:0, x2:1, y2:1,
                    stop:0 #0B1F3A,
                    stop:0.55 #0E2B4D,
                    stop:1 #071426
                );
                border: 1px solid #1E4F80;
                border-radius: 24px;
            }

            QLabel#badge {
                background-color: rgba(34, 199, 255, 0.12);
                color: #69D7FF;
                border: 1px solid #2A5D91;
                border-radius: 12px;
                padding: 7px 16px;
                font-size: 11px;
                font-weight: 900;
                letter-spacing: 1px;
            }

            QLabel#heroTitle {
                font-size: 27px;
                font-weight: 900;
                color: white;
                line-height: 1.15;
            }

            QLabel#heroSubtitle {
                font-size: 14px;
                color: #B9CBE7;
                line-height: 1.5;
            }



            QFrame#networkVisual {
                background-color: rgba(8, 19, 33, 0.65);
                border: 1px solid #1E4F80;
                border-radius: 22px;
            }

            QLabel#statusBadge {
                color: #64F29A;
                font-size: 13px;
                font-weight: 800;
            }

            QFrame#topologyBox {
                min-height: 135px;
                max-height: 160px;
                background-color: #081525;
                border: 1px solid #123B63;
                border-radius: 20px;
            }

            QFrame#coreNode {
                background-color: #123B63;
                border: 2px solid #3BB3FF;
                border-radius: 18px;
                min-width: 88px;
                min-height: 58px;
            }

            QFrame#sideNode {
                background-color: #10233F;
                border: 1px solid #2A5D91;
                border-radius: 16px;
                min-width: 74px;
                min-height: 54px;
            }

            QFrame#smallNode {
                background-color: #123052;
                border: 1px solid #22C7FF;
                border-radius: 16px;
                min-width: 88px;
                min-height: 48px;
            }

            QLabel#nodeLabel {
                color: #DCEBFF;
                font-size: 12px;
                font-weight: 900;
            }

            QFrame#featureCard_blue,
            QFrame#featureCard_purple,
            QFrame#featureCard_cyan,
            QFrame#featureCard_green {
                background-color: #10233F;
                border: 1px solid #1E4F80;
                border-radius: 18px;
            }

            QFrame#featureCard_blue:hover,
            QFrame#featureCard_purple:hover,
            QFrame#featureCard_cyan:hover,
            QFrame#featureCard_green:hover {
                border: 1px solid #3BB3FF;
                background-color: #123052;
            }

            QFrame#featureIcon_blue,
            QFrame#featureIcon_cyan {
                background-color: rgba(34, 199, 255, 0.18);
                border: 1px solid #22C7FF;
                border-radius: 32px;
            }

            QFrame#featureIcon_purple {
                background-color: rgba(124, 58, 237, 0.25);
                border: 1px solid #8B5CF6;
                border-radius: 32px;
            }

            QFrame#featureIcon_green {
                background-color: rgba(34, 197, 94, 0.22);
                border: 1px solid #22C55E;
                border-radius: 32px;
            }

            QLabel#featureTitle {
                color: white;
                font-size: 17px;
                font-weight: 900;
                padding-top: 4px
            }

            QLabel#featureDesc {
                color: #B9CBE7;
                font-size: 13px;
                line-height: 1.5;
                padding-left: 6px;
                padding-right: 6px;
            }

            QFrame#workflowCard {
                min-height: 185px;
                max-height: 220px;
                background-color: #10233F;
                border: 1px solid #1E4F80;
                border-radius: 18px;
            }

            QFrame#workflowStep {
                background-color: #123052;
                border: 1px solid #1E4F80;
                border-radius: 16px;
                min-width: 135px;
                max-width: 170px;
                min-height: 112px;
            }

            QLabel#sectionTitle {
                color: white;
                font-size: 18px;
                font-weight: 900;
            }

            QFrame#workflowCircle {
                background-color: #123B63;
                border: 1px solid #22C7FF;
                border-radius: 29px;
            }

            QFrame#workflowLine {
                background-color: #2A5D91;
                margin-top: 29px;
            }

            QLabel#workflowTitle {
                color: white;
                font-size: 13px;
                font-weight: 900;
            }

            QLabel#workflowDesc {
                color: #B9CBE7;
                font-size: 12px;
            }

            QLabel#footer {
                color: #7890B0;
                font-size: 12px;
            }
        """)
