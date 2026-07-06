import json
import asyncio
from fastapi import WebSocket, WebSocketDisconnect, Query
from typing import Dict, Set


class ConnectionManager:
    def __init__(self):
        self.active_connections: Dict[str, Set[WebSocket]] = {}

    async def connect(self, websocket: WebSocket, channel: str):
        await websocket.accept()
        if channel not in self.active_connections:
            self.active_connections[channel] = set()
        self.active_connections[channel].add(websocket)

    def disconnect(self, websocket: WebSocket, channel: str):
        if channel in self.active_connections:
            self.active_connections[channel].discard(websocket)

    async def broadcast(self, channel: str, message: dict):
        if channel in self.active_connections:
            dead = []
            for connection in self.active_connections[channel]:
                try:
                    await connection.send_json(message)
                except Exception:
                    dead.append(connection)
            for conn in dead:
                self.active_connections[channel].discard(conn)

    @property
    def connection_count(self) -> int:
        return sum(len(conns) for conns in self.active_connections.values())


manager = ConnectionManager()


async def websocket_endpoint(websocket: WebSocket, channel: str = Query(default="realtime")):
    await manager.connect(websocket, channel)
    try:
        while True:
            data = await websocket.receive_text()
            # Handle incoming messages (e.g., ping/pong, subscribe)
            try:
                msg = json.loads(data)
                if msg.get("type") == "ping":
                    await websocket.send_json({"type": "pong"})
            except json.JSONDecodeError:
                pass
    except WebSocketDisconnect:
        manager.disconnect(websocket, channel)
