"""PeerClaw channel plugin for nanobot.

Implements the BaseChannel interface to bridge PeerClaw P2P messaging
with nanobot's AI agent loop. Communication with the PeerClaw Go agent
uses a local WebSocket bridge.

Architecture:
    PeerClaw Agent (Go)              nanobot
    agent/platform/bridge/           this plugin
            │                            │
            ├── ws://localhost:19100 ────►│ (bridge server)
            │                            │
            ├── chat.send ──────────────►│──► MessageBus.inbound
            │◄── chat.event ────────────│◄── AgentLoop response
            ├── chat.inject ────────────►│──► notification display
            │                            │
"""

from __future__ import annotations

import asyncio
import json
import logging
from typing import Any

import websockets
import websockets.server
from nanobot.bus.events import OutboundMessage
from nanobot.channels.base import BaseChannel

logger = logging.getLogger(__name__)

# Bridge protocol frame types.
TYPE_CHAT_SEND = "chat.send"
TYPE_CHAT_INJECT = "chat.inject"
TYPE_CHAT_EVENT = "chat.event"


class PeerClawChannel(BaseChannel):
    """PeerClaw P2P messaging channel for nanobot."""

    name = "peerclaw"
    display_name = "PeerClaw"

    def __init__(self, config: dict[str, Any], bus: Any) -> None:
        super().__init__(config, bus)
        self._host = config.get("bridge_host", "localhost")
        self._port = config.get("bridge_port", 19100)
        self._server: websockets.server.WebSocketServer | None = None
        self._clients: set[websockets.WebSocketServerProtocol] = set()

    @classmethod
    def default_config(cls) -> dict[str, Any]:
        return {
            "enabled": False,
            "bridge_host": "localhost",
            "bridge_port": 19100,
            "allowFrom": [],
        }

    async def start(self) -> None:
        """Start the bridge WebSocket server and listen for PeerClaw agent connections."""
        self._server = await websockets.serve(
            self._handle_connection,
            self._host,
            self._port,
        )
        self.set_running(True)
        logger.info(f"PeerClaw bridge listening on ws://{self._host}:{self._port}")

        # Block until stopped.
        try:
            await asyncio.Future()
        except asyncio.CancelledError:
            pass

    async def stop(self) -> None:
        """Stop the bridge server."""
        if self._server:
            self._server.close()
            await self._server.wait_closed()
        self.set_running(False)
        logger.info("PeerClaw bridge stopped")

    async def send(self, msg: OutboundMessage) -> None:
        """Send an AI response back to the PeerClaw agent via bridge."""
        frame = {
            "type": TYPE_CHAT_EVENT,
            "data": {
                "sessionKey": f"peerclaw:dm:{msg.chat_id}",
                "state": "final",
                "message": msg.content,
            },
        }
        data = json.dumps(frame)

        # Broadcast to all connected PeerClaw agents.
        disconnected = set()
        for ws in self._clients:
            try:
                await ws.send(data)
            except websockets.ConnectionClosed:
                disconnected.add(ws)
        self._clients -= disconnected

    async def _handle_connection(
        self,
        websocket: websockets.WebSocketServerProtocol,
        path: str = "/",
    ) -> None:
        """Handle a PeerClaw agent WebSocket connection."""
        self._clients.add(websocket)
        logger.info(f"PeerClaw agent connected from {websocket.remote_address}")

        try:
            async for raw in websocket:
                await self._handle_frame(raw)
        except websockets.ConnectionClosed:
            pass
        finally:
            self._clients.discard(websocket)
            logger.info(f"PeerClaw agent disconnected from {websocket.remote_address}")

    async def _handle_frame(self, raw: str | bytes) -> None:
        """Parse and dispatch a bridge protocol frame."""
        try:
            frame = json.loads(raw)
        except json.JSONDecodeError:
            logger.warning("Invalid bridge frame: not valid JSON")
            return

        frame_type = frame.get("type", "")
        data = frame.get("data", {})

        if frame_type == TYPE_CHAT_SEND:
            session_key = data.get("sessionKey", "")
            message = data.get("message", "")
            sender_id = _extract_peer_id(session_key)

            await self._handle_message(
                sender_id=sender_id,
                chat_id=sender_id,
                content=message,
                session_key_override=session_key,
            )

        elif frame_type == TYPE_CHAT_INJECT:
            message = data.get("message", "")
            label = data.get("label", "notification")
            logger.info(f"PeerClaw notification [{label}]: {message}")

            # Inject as a system message.
            await self._handle_message(
                sender_id="peerclaw-system",
                chat_id="peerclaw-notifications",
                content=message,
                session_key_override="peerclaw:notifications",
            )

        elif frame_type == "ping":
            # Respond with pong to all connected clients.
            for ws in self._clients:
                try:
                    await ws.send(json.dumps({"type": "pong"}))
                except websockets.ConnectionClosed:
                    pass

        else:
            logger.debug(f"Unknown bridge frame type: {frame_type}")


def _extract_peer_id(session_key: str) -> str:
    """Extract peer agent ID from session key like 'peerclaw:dm:<id>'."""
    prefix = "peerclaw:dm:"
    if session_key.startswith(prefix):
        return session_key[len(prefix):]
    return session_key
