# BotForge - Multi-Bot AI Discord Platform

> **Note**: This project was previously called "SuperAgent-n8n". The n8n dependency has been removed in favor of a streamlined containerized architecture.

## 🤖 What is BotForge?

BotForge is a containerized platform for running multiple AI-powered Discord bots with persistent memory. Each bot can use different LLMs (Grok4, Claude, GPT-4) and maintains conversation history per user and channel.

## ✨ Features

- 🤖 **Multiple Bot Support** - Run different bots with different LLMs simultaneously
- 🧠 **Persistent Memory** - Each bot remembers conversation history
- 🐳 **Fully Containerized** - Easy deployment with Docker
- 🔧 **Configurable** - YAML-based bot configuration
- 📊 **Monitoring** - Health checks and statistics endpoints
- 🚀 **Scalable** - Add new bots without code changes

## 🏗️ Architecture

```
Discord → Discord Bot Container → API Server → PostgreSQL + LLM APIs → Discord
                                       ↓
                                 Web Dashboard (Port 3000)
```

## 🚀 Quick Start

### 1. Prerequisites
- Docker and Docker Compose
- Discord bot token(s)
- API key(s) for your chosen LLM(s)

### 2. Setup

```bash
# Clone the repository
git clone https://github.com/yourusername/botforge.git
cd botforge

# Copy and configure environment
cp .env.example .env
# Edit .env with your tokens and API keys

# Start all services
docker-compose up -d

# Check health
curl http://localhost:5001/health

# Access dashboard
open http://localhost:3000
```

### 3. Test Your Bot

In Discord:
- Mention your bot: `@Grok4 hello!`
- Use trigger words: `hey grok, what's the weather?`

## 📁 Project Structure

```
botforge/
├── docker-compose.yml      # Main orchestration file
├── .env                    # Your configuration (create from .env.example)
├── config/
│   └── bots.yaml          # Bot personalities and settings
├── src/
│   ├── discord_bot.py     # Discord connection handler
│   └── api_server.py      # API server with LLM integration
├── docker/
│   ├── Dockerfile.bot     # Discord bot container
│   ├── Dockerfile.api     # API server container
│   └── init.sql          # Database schema
├── dashboard/             # Web dashboard UI
└── logs/                  # Application logs
```

## 🔧 Configuration

### Bot Configuration (config/bots.yaml)

```yaml
bots:
  grok4:
    name: "Grok4 Assistant"
    enabled: true
    llm_provider: "xai"
    llm_model: "grok-4-latest"
    personality: "You are Grok4, a helpful AI assistant..."
    trigger_words: ["grok", "hey grok"]
```

### Environment Variables

Only configure what you need:
- `DISCORD_TOKEN_*` - Bot tokens
- `XAI_API_KEY` - For Grok4
- `ANTHROPIC_API_KEY` - For Claude
- `OPENAI_API_KEY` - For GPT

## 📊 Monitoring

### Health Check
```bash
curl http://localhost:5001/health
```

### Statistics
```bash
curl http://localhost:5001/stats
```

### Logs
```bash
# All services
docker-compose logs -f

# Specific bot
docker-compose logs -f discord-bot-grok4
```

## 🛠️ Common Operations

### Add a New Bot

1. Add Discord token to `.env`
2. Add bot configuration to `config/bots.yaml`
3. Restart services: `docker-compose restart`

### Backup Database

```bash
# Get the actual container name first
docker ps --format "table {{.Names}}" | grep postgres

# Then backup (container name may vary based on your setup)
docker exec [postgres-container-name] pg_dump -U botforge botforge > backup.sql
```

### Update Bot Personality

1. Edit `config/bots.yaml`
2. Restart the bot: `docker-compose restart discord-bot-grok4`

## 🚧 Roadmap

- [x] Web Dashboard for bot management
- [x] Real-time metrics and monitoring
- [ ] Plugin system for custom commands
- [ ] Multi-server configuration UI
- [ ] Conversation analytics
- [ ] Export conversation history

## 🤝 Contributing

Contributions are welcome! Please read our contributing guidelines before submitting PRs.

## 📝 License

MIT License - see LICENSE file for details

## ⚠️ Migration from SuperAgent-n8n

If you're migrating from the old n8n-based system:
1. Your database is compatible - just update the connection settings
2. Workflows are no longer needed - the system is code-based now
3. Check `legacy/` folder for old configurations

---

**Built with ❤️ for the Discord community**