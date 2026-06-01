# app/websocket/manager.py

import json

active_connections = {}


async def connect(user_id: int, websocket):
    await websocket.accept()
    active_connections[user_id] = websocket
    print(f"WebSocket connecté user_id={user_id}")


def disconnect(user_id: int):
    active_connections.pop(user_id, None)
    print(f"WebSocket déconnecté user_id={user_id}")


async def send_notification(user_id: int, message: str, type: str = "INFO", hostname: str = None):
    if user_id in active_connections:
        await active_connections[user_id].send_text(
            json.dumps({
                "message": message,
                "type": type,
                "hostname": hostname
            })
        )