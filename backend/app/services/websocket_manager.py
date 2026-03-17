"""
WebSocket connection manager for real-time progress broadcasting.
"""
import json
from fastapi import WebSocket
from typing import Dict, Set


class ConnectionManager:
    def __init__(self):
        self.active_connections: Dict[str, Set[WebSocket]] = {}

    async def connect(self, channel: str, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.setdefault(channel, set()).add(websocket)

    def disconnect(self, channel: str, websocket: WebSocket):
        conns = self.active_connections.get(channel, set())
        conns.discard(websocket)
        if not conns:
            self.active_connections.pop(channel, None)

    async def broadcast(self, channel: str, data: dict):
        for ws in list(self.active_connections.get(channel, [])):
            try:
                await ws.send_text(json.dumps(data))
            except Exception:
                self.active_connections.get(channel, set()).discard(ws)


ws_manager = ConnectionManager()
