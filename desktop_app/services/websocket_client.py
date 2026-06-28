from PySide6.QtCore import QObject, Signal, QUrl
from PySide6.QtWebSockets import QWebSocket


class NotificationWebSocketClient(QObject):
    message_received = Signal(dict)
    status_changed = Signal(str)

    def __init__(self, user_id: int, parent=None):
        super().__init__(parent)
        self.user_id = user_id
        self.socket = QWebSocket()

        self.socket.connected.connect(self.on_connected)
        self.socket.disconnected.connect(self.on_disconnected)
        self.socket.textMessageReceived.connect(self.on_text_message)

    def connect_to_server(self):
        url = QUrl(f"ws://127.0.0.1:8000/ws/notifications/{self.user_id}")
        self.socket.open(url)

    def on_connected(self):
        self.status_changed.emit("Connecté")

    def on_disconnected(self):
        self.status_changed.emit("Déconnecté")

    def on_text_message(self, message: str):
        try:
            import json
            data = json.loads(message)
        except Exception:
            data = {"type": "INFO", "message": message}

        self.message_received.emit(data)