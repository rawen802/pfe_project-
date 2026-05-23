from PySide6.QtCore import Qt, QPropertyAnimation, QEasingCurve, QParallelAnimationGroup, Property, Signal
from PySide6.QtGui import QColor, QPainter, QPen, QBrush
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QLabel, QPushButton, QHBoxLayout,
    QFrame, QGraphicsOpacityEffect, QGraphicsDropShadowEffect, QSizePolicy
)


class AnimatedButton(QPushButton):
    def __init__(self, text: str, parent=None):
        super().__init__(text, parent)
        self.setCursor(Qt.PointingHandCursor)

        shadow = QGraphicsDropShadowEffect(self)
        shadow.setBlurRadius(12)
        shadow.setOffset(0, 4)
        shadow.setColor(QColor(0, 0, 0, 80))
        self.setGraphicsEffect(shadow)

    def enterEvent(self, event):
        effect = self.graphicsEffect()
        if isinstance(effect, QGraphicsDropShadowEffect):
            effect.setBlurRadius(24)
            effect.setOffset(0, 8)
        super().enterEvent(event)

    def leaveEvent(self, event):
        effect = self.graphicsEffect()
        if isinstance(effect, QGraphicsDropShadowEffect):
            effect.setBlurRadius(12)
            effect.setOffset(0, 4)
        super().leaveEvent(event)


class PulseIcon(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMinimumSize(180, 180)
        self.setMaximumSize(220, 220)
        self._scale = 1.0

        self.pulse_anim = QPropertyAnimation(self, b"pulse_scale", self)
        self.pulse_anim.setDuration(1600)
        self.pulse_anim.setLoopCount(-1)
        self.pulse_anim.setStartValue(1.0)
        self.pulse_anim.setKeyValueAt(0.5, 1.08)
        self.pulse_anim.setEndValue(1.0)
        self.pulse_anim.setEasingCurve(QEasingCurve.InOutSine)

    def start(self):
        self.pulse_anim.start()

    @Property(float)
    def pulse_scale(self):
        return self._scale

    @pulse_scale.setter
    def pulse_scale(self, value):
        self._scale = value
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)

        w = self.width()
        h = self.height()
        cx = w / 2
        cy = h / 2
        radius = 62 * self._scale

        painter.setPen(Qt.NoPen)
        painter.setBrush(QBrush(QColor(59, 179, 255, 35)))
        painter.drawEllipse(
            int(cx - radius - 20),
            int(cy - radius - 20),
            int((radius + 20) * 2),
            int((radius + 20) * 2),
        )

        painter.setBrush(QBrush(QColor("#12385d")))
        painter.setPen(QPen(QColor("#3bb3ff"), 4))
        painter.drawEllipse(int(cx - radius), int(cy - radius), int(radius * 2), int(radius * 2))

        painter.setPen(QPen(QColor("#7fd3ff"), 4))
        node_r = 8

        top = (cx, cy - 26)
        left = (cx - 28, cy + 10)
        right = (cx + 28, cy + 10)
        bottom = (cx, cy + 34)

        painter.drawLine(int(top[0]), int(top[1]), int(left[0]), int(left[1]))
        painter.drawLine(int(top[0]), int(top[1]), int(right[0]), int(right[1]))
        painter.drawLine(int(left[0]), int(left[1]), int(bottom[0]), int(bottom[1]))
        painter.drawLine(int(right[0]), int(right[1]), int(bottom[0]), int(bottom[1]))

        painter.setBrush(QBrush(QColor("#3bb3ff")))
        painter.setPen(Qt.NoPen)

        for x, y in [top, left, right, bottom]:
            painter.drawEllipse(int(x - node_r), int(y - node_r), node_r * 2, node_r * 2)


class WelcomePage(QWidget):
    login_clicked = Signal()
    create_account_clicked = Signal()

    def __init__(self):
        super().__init__()
        self.setWindowTitle("NetAutoAI")
        self.resize(1200, 700)

        self._animations = []
        self.setup_ui()
        self.apply_styles()
        self.start_animations()

    def setup_ui(self):
        root_layout = QVBoxLayout(self)
        root_layout.setContentsMargins(36, 36, 36, 36)
        root_layout.setSpacing(20)

        self.hero = QFrame()
        self.hero.setObjectName("hero")

        hero_shadow = QGraphicsDropShadowEffect(self)
        hero_shadow.setBlurRadius(34)
        hero_shadow.setOffset(0, 10)
        hero_shadow.setColor(QColor(0, 0, 0, 110))
        self.hero.setGraphicsEffect(hero_shadow)

        hero_layout = QHBoxLayout(self.hero)
        hero_layout.setContentsMargins(36, 36, 36, 36)
        hero_layout.setSpacing(24)

        left_container = QFrame()
        left_container.setObjectName("leftContainer")

        left_layout = QVBoxLayout(left_container)
        left_layout.setSpacing(12)
        left_layout.setContentsMargins(0, 0, 0, 0)

        self.badge = QLabel("AI-Powered Network Automation")
        self.badge.setObjectName("badge")

        self.title = QLabel(
            "Automatisez votre réseau\navec intelligence et sécurité"
        )
        self.title.setObjectName("title")
        self.title.setWordWrap(True)
        self.title.setMaximumWidth(680)

        buttons_layout = QHBoxLayout()
        buttons_layout.setSpacing(14)

        self.btn_login = AnimatedButton("Se connecter")
        self.btn_login.setObjectName("primary")

        self.btn_create_account = AnimatedButton("Créer un compte")
        self.btn_create_account.setObjectName("secondary")

        self.btn_login.clicked.connect(self.login_clicked.emit)
        self.btn_create_account.clicked.connect(self.create_account_clicked.emit)

        buttons_layout.addWidget(self.btn_login)
        buttons_layout.addWidget(self.btn_create_account)
        buttons_layout.addStretch()

        stats_layout = QHBoxLayout()
        stats_layout.setSpacing(14)

        self.card1 = self.create_stat_card(
            "Authentification",
            "Connexion sécurisée avec JWT"
        )

        self.card2 = self.create_stat_card(
            "Gestion des rôles",
            "Admin, engineer, viewer"
        )

        self.card3 = self.create_stat_card(
            "Accès contrôlé",
            "Dashboard selon permissions"
        )

        stats_layout.addWidget(self.card1)
        stats_layout.addWidget(self.card2)
        stats_layout.addWidget(self.card3)

        left_layout.addWidget(self.badge)
        left_layout.addSpacing(8)
        left_layout.addWidget(self.title)
        left_layout.addStretch(1)
        left_layout.addLayout(buttons_layout)
        left_layout.addSpacing(20)
        left_layout.addLayout(stats_layout)
        left_layout.addStretch()

        right_container = QFrame()
        right_container.setObjectName("rightContainer")

        right_layout = QVBoxLayout(right_container)
        right_layout.setContentsMargins(0, 0, 0, 0)
        right_layout.setSpacing(14)

        self.visual_card = QFrame()
        self.visual_card.setObjectName("visualCard")

        visual_shadow = QGraphicsDropShadowEffect(self)
        visual_shadow.setBlurRadius(26)
        visual_shadow.setOffset(0, 8)
        visual_shadow.setColor(QColor(0, 0, 0, 90))
        self.visual_card.setGraphicsEffect(visual_shadow)

        visual_layout = QVBoxLayout(self.visual_card)
        visual_layout.setContentsMargins(24, 24, 24, 24)
        visual_layout.setSpacing(16)

        self.live_label = QLabel("● Système actif")
        self.live_label.setObjectName("liveLabel")
        self.live_label.setAlignment(Qt.AlignRight)

        self.visual_icon = PulseIcon()

        self.visual_title = QLabel(
            "Accédez à votre espace\nNetAutoAI sécurisé"
        )
        self.visual_title.setObjectName("visualTitle")
        self.visual_title.setAlignment(Qt.AlignCenter)
        self.visual_title.setWordWrap(True)

        visual_stats = QHBoxLayout()
        visual_stats.setSpacing(12)

        self.mini1 = self.create_mini_box("JWT", "Sécurité")
        self.mini2 = self.create_mini_box("RBAC", "Rôles")
        self.mini3 = self.create_mini_box("IA", "Validation")

        visual_stats.addWidget(self.mini1)
        visual_stats.addWidget(self.mini2)
        visual_stats.addWidget(self.mini3)

        visual_layout.addWidget(self.live_label)
        visual_layout.addStretch()
        visual_layout.addWidget(self.visual_icon, alignment=Qt.AlignCenter)
        visual_layout.addWidget(self.visual_title)
        visual_layout.addStretch()
        visual_layout.addLayout(visual_stats)

        right_layout.addWidget(self.visual_card)

        hero_layout.addWidget(left_container, 3)
        hero_layout.addWidget(right_container, 2)

        root_layout.addWidget(self.hero)

        for widget in [self.badge, self.title]:
            self.add_opacity_effect(widget)

    def create_stat_card(self, title_text: str, desc_text: str) -> QFrame:
        card = QFrame()
        card.setObjectName("statCard")

        shadow = QGraphicsDropShadowEffect(self)
        shadow.setBlurRadius(18)
        shadow.setOffset(0, 6)
        shadow.setColor(QColor(0, 0, 0, 70))
        card.setGraphicsEffect(shadow)

        layout = QVBoxLayout(card)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(8)

        title = QLabel(title_text)
        title.setObjectName("statTitle")

        desc = QLabel(desc_text)
        desc.setObjectName("statDesc")
        desc.setWordWrap(True)

        layout.addWidget(title)
        layout.addWidget(desc)

        return card

    def create_mini_box(self, value: str, label: str) -> QFrame:
        box = QFrame()
        box.setObjectName("miniBox")

        layout = QVBoxLayout(box)
        layout.setContentsMargins(14, 14, 14, 14)
        layout.setSpacing(4)

        value_label = QLabel(value)
        value_label.setObjectName("miniValue")
        value_label.setAlignment(Qt.AlignCenter)

        text_label = QLabel(label)
        text_label.setObjectName("miniText")
        text_label.setAlignment(Qt.AlignCenter)

        layout.addWidget(value_label)
        layout.addWidget(text_label)

        return box

    def add_opacity_effect(self, widget):
        effect = QGraphicsOpacityEffect(widget)
        effect.setOpacity(0.0)
        widget.setGraphicsEffect(effect)
        widget.opacity_effect = effect

    def fade_in_widget(self, widget, duration=300):
        anim = QPropertyAnimation(widget.opacity_effect, b"opacity", self)
        anim.setDuration(duration)
        anim.setStartValue(0.0)
        anim.setEndValue(1.0)
        anim.setEasingCurve(QEasingCurve.OutCubic)

        self._animations.append(anim)
        return anim

    def start_animations(self):
        group = QParallelAnimationGroup(self)

        for widget in [self.badge, self.title]:
            group.addAnimation(self.fade_in_widget(widget, 260))

        group.start()
        self._animations.append(group)

    def showEvent(self, event):
        super().showEvent(event)
        self.visual_icon.start()

    def apply_styles(self):
        self.setStyleSheet("""
            QWidget {
                background-color: #07111f;
                color: #ffffff;
                font-family: Arial, sans-serif;
            }

            QLabel {
                background: transparent;
            }

            #hero {
                background: qlineargradient(
                    x1: 0, y1: 0, x2: 1, y2: 1,
                    stop: 0 #0f1b33,
                    stop: 0.5 #10264a,
                    stop: 1 #0a3558
                );
                border: 1px solid rgba(255, 255, 255, 0.08);
                border-radius: 26px;
            }

            #leftContainer,
            #rightContainer {
                background: transparent;
            }

            #badge {
                background-color: rgba(59, 179, 255, 0.16);
                color: #9adaff;
                border: 1px solid rgba(59, 179, 255, 0.30);
                border-radius: 14px;
                padding: 8px 14px;
                font-size: 13px;
                font-weight: 600;
                max-width: 260px;
            }

            #title {
                font-size: 42px;
                font-weight: 800;
                color: #ffffff;
            }

            QPushButton {
                min-height: 48px;
                padding: 12px 18px;
                border-radius: 12px;
                font-size: 14px;
                font-weight: 700;
            }

            #primary {
                background-color: #3bb3ff;
                color: #08111f;
                border: none;
            }

            #primary:hover {
                background-color: #69c8ff;
            }

            #secondary {
                background-color: transparent;
                color: #3bb3ff;
                border: 1px solid #3bb3ff;
            }

            #secondary:hover {
                background-color: rgba(59, 179, 255, 0.10);
            }

            #statCard {
                background-color: rgba(255, 255, 255, 0.06);
                border: 1px solid rgba(255, 255, 255, 0.08);
                border-radius: 18px;
            }

            #statTitle {
                color: #56c2ff;
                font-size: 17px;
                font-weight: 700;
            }

            #statDesc {
                color: #c7d6ea;
                font-size: 13px;
                line-height: 1.5;
            }

            #visualCard {
                background: rgba(8, 19, 38, 0.72);
                border: 1px solid rgba(255, 255, 255, 0.08);
                border-radius: 22px;
            }

            #liveLabel {
                color: #74f39d;
                font-size: 13px;
                font-weight: 700;
            }

            #visualTitle {
                color: #f3f7fd;
                font-size: 20px;
                font-weight: 700;
            }

            #miniBox {
                background-color: rgba(255, 255, 255, 0.05);
                border: 1px solid rgba(255, 255, 255, 0.07);
                border-radius: 16px;
            }

            #miniValue {
                color: #3bb3ff;
                font-size: 22px;
                font-weight: 800;
            }

            #miniText {
                color: #c9d6e8;
                font-size: 12px;
            }
        """)