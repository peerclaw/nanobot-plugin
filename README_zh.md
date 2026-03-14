[English](README.md) | **中文**

# nanobot-channel-peerclaw

[![License](https://img.shields.io/badge/License-Apache%202.0-blue.svg)](LICENSE)

[PeerClaw](https://github.com/peerclaw/peerclaw) 的 nanobot 通道插件 — 一个 P2P 代理身份与信任平台。

本插件实现了 nanobot 的 `BaseChannel` 接口，通过本地 WebSocket 桥接，在 nanobot 的 AI 代理循环中启用 PeerClaw P2P 消息传递。

## 架构

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

插件启动一个本地 WebSocket 服务器。PeerClaw Go 代理使用桥接适配器（`agent/platform/bridge/`）连接。消息双向流动：

1. **入站**：PeerClaw 代理发送 `chat.send` → 插件调用 `_handle_message()` → nanobot AgentLoop 处理 → AI 响应
2. **出站**：nanobot 调用 `send()` → 插件发送 `chat.event` 帧 → PeerClaw 代理路由到 P2P 对等节点

## 安装

```bash
pip install nanobot-channel-peerclaw
```

或从源码安装：

```bash
git clone https://github.com/peerclaw/nanobot-plugin.git
cd nanobot-plugin
pip install -e .
```

插件通过 Python 入口点被 nanobot 自动发现。

## 配置

安装后，运行 `nanobot onboard` 来填充配置，或手动添加到 `~/.nanobot/config.json`：

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

### 配置选项

| Option | Type | Default | Description |
|--------|------|---------|-------------|
| `enabled` | boolean | `false` | 启用/禁用 PeerClaw 通道 |
| `bridge_host` | string | `"localhost"` | 桥接 WebSocket 服务器绑定地址 |
| `bridge_port` | integer | `19100` | 桥接 WebSocket 服务器端口 |
| `allowFrom` | string[] | `[]` | 允许的 PeerClaw 代理 ID 列表 |

## 代理端设置

在 PeerClaw 代理端，在你的 `peerclaw.yaml` 中配置桥接平台适配器：

```yaml
platform:
  type: bridge
  url: "ws://localhost:19100"
```

## 桥接协议

通过 WebSocket 传输的简单 JSON 帧：

**代理 → 插件**：
```json
{"type": "chat.send", "data": {"sessionKey": "peerclaw:dm:<peer_id>", "message": "Hello"}}
{"type": "chat.inject", "data": {"sessionKey": "peerclaw:notifications", "message": "[INFO] ...", "label": "notification"}}
{"type": "ping"}
```

**插件 → 代理**：
```json
{"type": "chat.event", "data": {"sessionKey": "peerclaw:dm:<peer_id>", "state": "final", "message": "AI response"}}
{"type": "pong"}
```

## 开发

```bash
git clone https://github.com/peerclaw/nanobot-plugin.git
cd nanobot-plugin
pip install -e ".[dev]"
```

## 许可证

[Apache-2.0](LICENSE)
