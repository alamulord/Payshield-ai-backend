# app/services/realtime_service.py — WebSocket manager for real-time alerts
"""
Realtime Service: Manages WebSocket connections for broadcasting
live alerts and transaction feed updates to connected frontend clients.
O(c) per broadcast where c = number of connected clients
"""
import json
import asyncio
from typing import Dict, Set
from fastapi import WebSocket
from datetime import datetime, timezone


class ConnectionManager:
    """Manages WebSocket connections. Thread-safe via asyncio."""

    def __init__(self):
        self.active_connections: Dict[str, WebSocket] = {}
        self._lock = asyncio.Lock()

    async def connect(self, websocket: WebSocket, client_id: str):
        """Accept and register a WebSocket connection. O(1)"""
        await websocket.accept()
        async with self._lock:
            self.active_connections[client_id] = websocket
        print(f"[WS] Client {client_id} connected. Total: {len(self.active_connections)}")

    async def disconnect(self, client_id: str):
        """Remove a WebSocket connection. O(1)"""
        async with self._lock:
            self.active_connections.pop(client_id, None)
        print(f"[WS] Client {client_id} disconnected. Total: {len(self.active_connections)}")

    async def send_personal(self, message: dict, client_id: str):
        """Send message to a specific client. O(1)"""
        ws = self.active_connections.get(client_id)
        if ws:
            try:
                await ws.send_json(message)
            except Exception:
                await self.disconnect(client_id)

    async def broadcast(self, message: dict):
        """Broadcast message to all connected clients. O(c)"""
        disconnected = []
        async with self._lock:
            for client_id, ws in self.active_connections.items():
                try:
                    await ws.send_json(message)
                except Exception:
                    disconnected.append(client_id)

        # Clean up disconnected clients
        for client_id in disconnected:
            await self.disconnect(client_id)

    async def broadcast_alert(self, alert_data: dict):
        """Broadcast a new alert to all clients. O(c)"""
        await self.broadcast({
            "type": "new_alert",
            "data": alert_data,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        })

    async def broadcast_transaction(self, tx_data: dict):
        """Broadcast a new transaction to all clients. O(c)"""
        await self.broadcast({
            "type": "new_transaction",
            "data": tx_data,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        })

    async def broadcast_activity(self, activity_data: dict):
        """Broadcast activity feed update. O(c)"""
        await self.broadcast({
            "type": "activity_update",
            "data": activity_data,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        })

    @property
    def client_count(self) -> int:
        return len(self.active_connections)


# Singleton instance
ws_manager = ConnectionManager()
