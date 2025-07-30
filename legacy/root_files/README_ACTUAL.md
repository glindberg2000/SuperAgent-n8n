# SuperAgent Discord Bot - Actual Working System

## 🤖 What This Is

A containerized Discord bot that uses Grok4 AI with persistent memory. The bot responds to mentions and remembers conversation history per user/channel.

## 🏗️ Architecture

```
Discord → Discord Bot Container → API Server Container → PostgreSQL + Grok4 → Discord
```

### Active Containers:
- **discord-bot**: Listens to Discord, forwards messages
- **api-server**: Processes with AI, manages database
- **postgres**: Stores conversation history
- **redis**: Ready for future caching

## 🚀 Quick Start

1. **Clone and configure:**
```bash
git clone <repo>
cd SuperAgent-n8n
cp .env.example .env
# Edit .env with your keys:
# - DISCORD_TOKEN_GROK4
# - XAI_API_KEY
```

2. **Start everything:**
```bash
docker-compose -f docker-compose.separate.yml up -d
```

3. **Check it's working:**
```bash
# Check health
curl http://localhost:5001/health

# View logs
docker-compose -f docker-compose.separate.yml logs -f
```

4. **Test in Discord:**
- Mention your bot: `@Grok4 hello!`
- Or use keywords: `hey grok, what's up?`

## 📁 Important Files

### Configuration:
- `.env` - Your API keys and tokens
- `docker-compose.separate.yml` - Container orchestration

### Code:
- `discord_forwarder.py` - Discord bot that listens and forwards
- `discord_api_server.py` - API server with AI and database

### Docker:
- `docker/Dockerfile.discord-bot-separate` - Discord bot container
- `docker/Dockerfile.api-server` - API server container

## 🔧 Common Tasks

### View Logs:
```bash
docker-compose -f docker-compose.separate.yml logs discord-bot
docker-compose -f docker-compose.separate.yml logs api-server
```

### Restart Services:
```bash
docker-compose -f docker-compose.separate.yml restart
```

### Backup Database:
```bash
docker exec superagent-n8n-postgres-1 pg_dump -U superagent superagent > backup.sql
```

### Stop Everything:
```bash
docker-compose -f docker-compose.separate.yml down
```

## ⚠️ Important Notes

- **n8n is NOT used** - All the n8n files and workflows are legacy
- **Port 5436** - PostgreSQL (not default 5432)
- **Port 5001** - API server health check
- **No visual interface** - Direct code-based approach

## 🎯 Environment Variables Used

Required:
- `DISCORD_TOKEN_GROK4` - Discord bot token
- `XAI_API_KEY` - Grok4 API key

Optional:
- `POSTGRES_*` - Database settings (defaults provided)

## 🚫 Ignore These Files

All these are legacy/unused:
- `workflows/` directory
- `docker-compose.yml` 
- `docker-compose.simple.yml`
- Any n8n-related configs
- `discord_combined_service.py`