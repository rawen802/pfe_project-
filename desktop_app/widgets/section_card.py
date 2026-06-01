from PySide6.QtWidgets import QFrame, QVBoxLayout, QLabel


class SectionCard(QFrame):
    def __init__(self, title: str):
        super().__init__()
        self.setObjectName("sectionCard")

        self.layout_main = QVBoxLayout(self)
        self.layout_main.setContentsMargins(18, 18, 18, 18)
        self.layout_main.setSpacing(14)

        self.title = QLabel(title)
        self.title.setObjectName("sectionTitle")

        self.layout_main.addWidget(self.title)

    def add_widget(self, widget):
        self.layout_main.addWidget(widget)

    def add_layout(self, layout):
        self.layout_main.addLayout(layout)