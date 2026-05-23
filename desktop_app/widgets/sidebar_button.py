from PySide6.QtCore import Qt
from PySide6.QtWidgets import QPushButton


class SidebarButton(QPushButton):
    def __init__(self, text: str):
        super().__init__(text)
        self.setCursor(Qt.PointingHandCursor)
        self.setCheckable(True)
        self.setObjectName("sidebarButton")