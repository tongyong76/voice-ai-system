import json
import asyncio
from fastapi import WebSocket, WebSocketDisconnect
from typing import Dict, Set
from ..core.redis import get_redis


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
            for connection in self.active_connections[channel]:
                try:
                    await connection.send_json(message)
                except:
                    pass


manager = ConnectionManager()


async def websocket_endpoint(websocket: WebSocket, channel: str = "default"):
    await manager.connect(websocket, channel)
    try:
        while True:
            data = await websocket.receive_text()
            # Handle incoming messages if needed
    except WebSocketDisconnect:
        manager.disconnect(websocket, channel)


async def redis_subscriber():
    """Subscribe to Redis channels and broadcast to WebSocket clients"""
    r = await get_redis()
    pubsub = r.pubsub()
    await pubsub.subscribe("audio:inference_result", "alert:trigger")

    async for message in pubsub.listen():
        if message["type"] == "message":
            data = json.loads(message["data"])
            channel = data.get("channel", "default")
            await manager.broadcast(channel, data)
