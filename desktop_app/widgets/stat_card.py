from PySide6.QtWidgets import QFrame, QVBoxLayout, QLabel


class StatCard(QFrame):
    def __init__(self, title: str, value: str, subtitle: str = ""):
        super().__init__()
        self.setObjectName("statCard")

        layout = QVBoxLayout(self)
        layout.setContentsMargins(18, 18, 18, 18)
        layout.setSpacing(6)

        self.title = QLabel(title)
        self.title.setObjectName("statTitle")

        self.value = QLabel(value)
        self.value.setObjectName("statValue")

        self.subtitle = QLabel(subtitle)
        self.subtitle.setObjectName("statSubtitle")

        layout.addWidget(self.title)
        layout.addWidget(self.value)
        layout.addWidget(self.subtitle)