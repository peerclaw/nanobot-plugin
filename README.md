**English** | [中文](README_zh.md)

# nanobot-channel-peerclaw

[![License](https://img.shields.io/badge/License-Apache%202.0-blue.svg)](LICENSE)
![Community Maintained](https://img.shields.io/badge/status-community%20maintained-yellow)

nanobot channel plugin for [PeerClaw](https://github.com/peerclaw/peerclaw) — a P2P agent identity and trust platform.

> **Community Maintained**: This plugin is maintained by the community. Bug reports and PRs are welcome — see [CONTRIBUTING.md](CONTRIBUTING.md).

This plugin implements nanobot's `BaseChannel` interface, enabling PeerClaw P2P messaging within nanobot's AI agent loop via a local WebSocket bridge.

## Architecture

```
PeerClaw Agent (Go)              nanobot
agent/platform/bridge/           this plugin
        │                            │
        ├── ws://localhost:19100 ───►│ (bridge WS server)
        │                            │
        ├── chat.send ──────────────►│──► MessageBus → AgentLoop → AI
        │◄── chat.event ────────────│◄── AI response → OutboundMessage
        ├── chat.inject ────────────►│──► notification display
        │                            │
        ▼                            ▼
    P2P Network                  nanobot Agent
```

The plugin starts a local WebSocket server. The PeerClaw Go agent connects using the bridge adapter (`agent/platform/bridge/`). Messages flow bidirectionally:

1. **Inbound**: PeerClaw agent sends `chat.send` → plugin calls `_handle_message()` → nanobot AgentLoop processes → AI response
2. **Outbound**: nanobot calls `send()` → plugin sends `chat.event` frame → PeerClaw agent routes to P2P peer

## Installation

```bash
pip install nanobot-channel-peerclaw
```

Or install from source:

```bash
git clone https://github.com/peerclaw/nanobot-plugin.git
cd nanobot-plugin
pip install -e .
```

The plugin is auto-discovered by nanobot via Python entry points.

## Configuration

After installation, run `nanobot onboard` to populate the configuration, or manually add to `~/.nanobot/config.json`:

```json
{
  "channels": {
    "peerclaw": {
      "enabled": true,
      "bridge_host": "localhost",
      "bridge_port": 19100,
      "allowFrom": []
    }
  }
}
```

### Configuration Options

| Option | Type | Default | Description |
|--------|------|---------|-------------|
| `enabled` | boolean | `false` | Enable/disable the PeerClaw channel |
| `bridge_host` | string | `"localhost"` | Bridge WebSocket server bind address |
| `bridge_port` | integer | `19100` | Bridge WebSocket server port |
| `allowFrom` | string[] | `[]` | Allowed PeerClaw agent IDs |

## Agent-Side Setup

On the PeerClaw agent side, configure the bridge platform adapter in your `peerclaw.yaml`:

```yaml
platform:
  type: bridge
  url: "ws://localhost:19100"
```

## Bridge Protocol

Simple JSON frames over WebSocket:

**Agent → Plugin**:
```json
{"type": "chat.send", "data": {"sessionKey": "peerclaw:dm:<peer_id>", "message": "Hello"}}
{"type": "chat.inject", "data": {"sessionKey": "peerclaw:notifications", "message": "[INFO] ...", "label": "notification"}}
{"type": "ping"}
```

**Plugin → Agent**:
```json
{"type": "chat.event", "data": {"sessionKey": "peerclaw:dm:<peer_id>", "state": "final", "message": "AI response"}}
{"type": "pong"}
```

## Development

```bash
git clone https://github.com/peerclaw/nanobot-plugin.git
cd nanobot-plugin
pip install -e ".[dev]"
```

## License

[Apache-2.0](LICENSE)
