# Vertex AI

<p align="center">
  <img src="ui/public/favicon.svg" alt="Vertex AI" width="80" />
</p>

<p align="center">
  <strong>Next-generation AI operating system. Run your own AI — on your terms.</strong>
</p>

<p align="center">
  <a href="https://github.com/niroopn2005-art/vertex-ai/actions/workflows/ci.yml">
    <img src="https://img.shields.io/github/actions/workflow/status/niroopn2005-art/vertex-ai/ci.yml?branch=main&style=for-the-badge&label=Build" alt="Build Status" />
  </a>
  <a href="LICENSE">
    <img src="https://img.shields.io/badge/License-MIT-blue.svg?style=for-the-badge" alt="MIT License" />
  </a>
</p>

---

**Vertex AI** is a self-hosted, local-first AI gateway you run on your own machine. It connects any large language model to the messaging channels you already use — WhatsApp, Telegram, Slack, Discord, iMessage, and more — while giving you full control over your data, your models, and your privacy.

No cloud lock-in. No subscriptions required. Your AI, running at home.

---

## Features

- **Multi-channel inbox** — Connect WhatsApp, Telegram, Slack, Discord, Google Chat, Signal, iMessage, IRC, Microsoft Teams, Matrix, Feishu, LINE, Mattermost, Nostr, and more from a single gateway.
- **Model-agnostic** — Works with Anthropic (Claude), OpenAI (GPT), Google (Gemini), Ollama (local), and any OpenAI-compatible provider. Swap models without changing anything else.
- **Local-first gateway** — Single control plane for sessions, channels, tools, and events. Your data never leaves your machine unless you choose otherwise.
- **Premium Control UI** — Electric blue glassmorphism interface. Real-time session management, agent overview, usage stats, and full configuration — all in the browser.
- **Voice support** — Wake words, push-to-talk, and continuous voice mode on macOS/iOS/Android via ElevenLabs or system TTS.
- **Multi-agent routing** — Route different channels and accounts to isolated agents with separate workspaces and session histories.
- **MCP support** — Full Model Context Protocol integration for connecting external tools and data sources.
- **Built-in automation** — Cron jobs, webhook triggers, Gmail Pub/Sub, and session-to-session messaging.
- **Skills system** — Extend your agent with markdown-based skills. Mount custom tool collections per agent or globally.
- **Live Canvas** — Agent-driven visual workspace with A2UI for rendering rich interactive content.
- **Security-first** — DM pairing, sandboxed sessions, token-based auth, and full operator controls out of the box.

---

## Installation

**Requirements:** Node.js 24 (recommended) or Node.js 22.19+

### Via npm (recommended)

```bash
npm install -g vertex-ai@latest
# or
pnpm add -g vertex-ai@latest
```

### From source

```bash
git clone https://github.com/niroopn2005-art/vertex-ai.git
cd vertex-ai

pnpm install
pnpm build
pnpm ui:build
```

---

## Quick Start

### 1. Run onboarding (first time)

```bash
vertex-ai onboard --install-daemon
```

This guides you through gateway setup, model configuration, workspace initialization, and channel connections. Installs a background daemon (launchd on macOS, systemd on Linux) so the gateway stays running.

### 2. Check gateway status

```bash
vertex-ai gateway status
```

### 3. Open the Control UI

Navigate to `http://localhost:18789` in your browser. Paste your gateway token when prompted.

### 4. Run in foreground (debug mode)

```bash
vertex-ai gateway stop
vertex-ai gateway --port 18789 --verbose
```

### 5. Send a message or invoke the agent

```bash
# Talk to the AI agent directly
vertex-ai agent --message "Summarize my tasks for today" --thinking high

# Send a message to a connected channel
vertex-ai message send --target +1234567890 --message "Hello from Vertex AI"
```

---

## Configuration

The main config file lives at `~/.vertex-ai/vertex-ai.json`.

### Minimal configuration

```json5
{
  "agents": {
    "defaults": {
      "model": "<provider>/<model-id>",
      "workspace": "~/.vertex-ai/workspace"
    }
  },
  "models": {
    "providers": {
      "anthropic": {
        "apiKey": "sk-ant-..."
      }
    }
  },
  "gateway": {
    "mode": "local",
    "auth": {
      "mode": "token",
      "token": "<your-gateway-token>"
    }
  },
  "ui": {
    "assistant": {
      "name": "Vertex",
      "avatar": "⬡"
    }
  }
}
```

### Supported model providers

| Provider | Example model ID |
|---|---|
| Anthropic | `anthropic/claude-opus-4-7` |
| OpenAI | `openai/gpt-4o` |
| Google Gemini | `google/gemini-2.0-flash` |
| Ollama (local) | `ollama/llama3` |
| Any OpenAI-compatible | `openai-compat/your-model` |

### Key configuration paths

| Key | Description |
|---|---|
| `agents.defaults.model` | Default model for all agents |
| `agents.defaults.workspace` | Agent workspace directory |
| `gateway.auth.token` | Gateway authentication token |
| `models.providers.*` | API keys per provider |
| `ui.assistant.name` | Display name shown in the Control UI |
| `ui.assistant.avatar` | Avatar emoji or image URL |

### Environment variables

| Variable | Description |
|---|---|
| `VERTEX_AI_CONFIG` | Override config file path |
| `VERTEX_AI_PORT` | Override gateway port (default: 18789) |
| `VERTEX_AI_LOG_LEVEL` | Log verbosity: `error`, `warn`, `info`, `debug` |

---

## Architecture

Vertex AI is structured around a central **Gateway** — a Node.js process that acts as the single control plane for all AI activity.

```
┌─────────────────────────────────────────────────┐
│                  Vertex AI Gateway               │
│                                                 │
│  ┌──────────┐  ┌───────────┐  ┌─────────────┐  │
│  │ Channels │  │  Agents   │  │   Control   │  │
│  │ (inbox)  │  │ (workers) │  │     UI      │  │
│  └────┬─────┘  └─────┬─────┘  └──────┬──────┘  │
│       │              │               │          │
│  ┌────▼──────────────▼───────────────▼──────┐   │
│  │            WebSocket Bus (RPC)            │   │
│  └────────────────────┬──────────────────────┘  │
│                       │                         │
│  ┌────────────────────▼──────────────────────┐  │
│  │         Model Router / Failover           │  │
│  └────────────────────┬──────────────────────┘  │
└───────────────────────┼─────────────────────────┘
                        │
          ┌─────────────▼────────────┐
          │     LLM Providers        │
          │  Anthropic / OpenAI /    │
          │  Google / Ollama / etc.  │
          └──────────────────────────┘
```

- **Channels** receive inbound messages from connected platforms and route them to the appropriate agent.
- **Agents** are isolated workers with their own workspace, skill set, and session history.
- **The Control UI** is a web app served by the gateway on `localhost:18789` for configuration and real-time monitoring.
- **The Model Router** selects and fails over between configured LLM providers transparently.

---

## Project Structure

```
vertex-ai/
├── src/                    # Core gateway source (TypeScript)
│   ├── gateway/            # HTTP server, WebSocket bus, auth
│   ├── agents/             # Agent runtime, session management
│   ├── channels/           # Messaging platform integrations
│   └── models/             # LLM provider adapters + failover
├── ui/                     # Control UI (Web Components, Lit, Vite)
│   ├── src/styles/         # CSS design system (Electric Blue theme)
│   ├── src/ui/             # UI components and views
│   └── public/             # Static assets, favicon, manifest
├── packages/               # Shared internal packages
│   └── gateway-protocol/   # WebSocket RPC protocol definitions
├── extensions/             # Built-in plugin extensions
├── skills/                 # Bundled agent skill definitions
├── scripts/                # Build and dev tooling
├── dist/                   # Compiled gateway output
├── dist-runtime/           # Runtime-only build output
└── vertex-ai.json          # Local config (at ~/.vertex-ai/)
```

---

## Security

Vertex AI connects to real messaging surfaces. Treat all inbound messages as **untrusted input** by default.

### Default DM policy

All channels default to `dmPolicy: "pairing"` — unknown senders get a pairing code and their message is not processed until you approve them:

```bash
vertex-ai pairing approve <channel> <code>
```

### Sandboxing

For non-main sessions (e.g. group chats), enable sandbox mode to isolate agent tool access:

```json5
{
  "agents": {
    "defaults": {
      "sandbox": { "mode": "non-main" }
    }
  }
}
```

### Run a security audit

```bash
vertex-ai doctor
```

This surfaces any risky or misconfigured settings.

---

## Roadmap

- [ ] **Web UI v2** — Drag-and-drop agent builder and visual workflow editor
- [ ] **Plugin marketplace** — Installable skill packs from a central registry
- [ ] **Mobile app** — Native iOS/Android companion app with full agent control
- [ ] **Team mode** — Multi-user gateway with role-based access control
- [ ] **Memory layer** — Long-term vector memory across sessions with semantic search
- [ ] **Custom model hosting** — First-class support for self-hosted models via vLLM/Ollama
- [ ] **Observability dashboard** — Token usage, latency, cost tracking, and model analytics
- [ ] **Agent-to-agent protocols** — Structured communication between multiple deployed agents

---

## Development

Use `pnpm` for source checkouts. The repo is a pnpm workspace.

```bash
# Clone and install
git clone https://github.com/niroopn2005-art/vertex-ai.git
cd vertex-ai
pnpm install

# First-time setup (writes local config and workspace)
pnpm vertex-ai setup

# Build the Control UI
pnpm ui:build

# Start the dev loop (auto-reloads on source changes)
pnpm gateway:watch
```

### Useful dev commands

| Command | Description |
|---|---|
| `pnpm gateway:watch` | Start gateway with auto-reload |
| `pnpm ui:build` | Build the Control UI bundle |
| `pnpm ui:dev` | Run Control UI in dev mode (hot reload) |
| `pnpm build` | Full production build |
| `pnpm test` | Run all tests |
| `pnpm vertex-ai doctor` | Check config and surface issues |

---

## License

MIT License — see [LICENSE](LICENSE) for details.

---

<p align="center">
  Built with ⚡ — Electric Blue, Deep Space Black, and a lot of ambition.
</p>
