# SuperAgent n8n - Setup Guide

## 🚀 Quick Start (5 Minutes)

### Prerequisites
- Docker and Docker Compose
- Discord bot tokens
- LLM API keys (Grok4, Claude, Gemini)

### 1. Clone and Configure
```bash
git clone <repo-url>
cd SuperAgent-n8n
cp .env.example .env
```

### 2. Edit Environment Variables
```bash
# Edit .env file with your credentials
nano .env

# Required variables:
DISCORD_TOKEN_GROK4=your_bot_token
XAI_API_KEY=your_grok_api_key
ANTHROPIC_API_KEY=your_claude_api_key
GOOGLE_AI_API_KEY=your_gemini_api_key
DEFAULT_SERVER_ID=your_discord_server_id
```

### 3. Start Services
```bash
# Start all services
docker-compose -f docker/docker-compose.yml up -d

# Check status
docker-compose -f docker/docker-compose.yml ps
```

### 4. Access n8n Interface
- Open: http://localhost:5678
- Login: admin / (your N8N_BASIC_AUTH_PASSWORD)

### 5. Import Workflows
1. Go to n8n interface
2. Click "Import from file"
3. Import `workflows/*.json` files
4. Configure webhook URLs in Discord

## 📋 Detailed Setup

### Discord Bot Setup

#### 1. Create Discord Applications
1. Go to [Discord Developer Portal](https://discord.com/developers/applications)
2. Create 3 applications: Grok4Agent, ClaudeAgent, GeminiAgent
3. For each application:
   - Go to "Bot" section
   - Create bot
   - Copy bot token
   - Enable "Message Content Intent"
   - Enable "Server Members Intent"

#### 2. Bot Permissions
Required permissions for each bot:
- Send Messages
- Read Message History
- Use Slash Commands
- Add Reactions
- Manage Messages (optional)
- Read Messages/View Channels

Invite URL template:
```
https://discord.com/api/oauth2/authorize?client_id=YOUR_BOT_ID&permissions=274877975552&scope=bot
```

### n8n Workflow Configuration

#### 1. Import Base Workflows
Import these workflows in order:
1. `workflows/discord-bot-base.json` - Main message handler
2. `workflows/memory-postgres.json` - Memory management
3. `workflows/agents/agent-grok4.json` - Grok4 processing
4. `workflows/agents/agent-claude.json` - Claude processing
5. `workflows/agents/agent-gemini.json` - Gemini processing

#### 2. Configure Webhooks
1. In n8n, activate the "Discord Bot Base" workflow
2. Copy the webhook URL (will be like: `http://localhost:5678/webhook/discord`)
3. Configure Discord webhook for your server:
   - Server Settings → Integrations → Webhooks
   - Create webhook for #general channel
   - Set webhook URL to your n8n webhook

#### 3. Test Workflows
1. Send test message: `@Grok4Agent hello`
2. Check n8n execution logs
3. Verify bot response in Discord

### Database Setup

#### PostgreSQL Configuration
The database is automatically initialized via Docker with:
- User management tables
- Conversation tracking
- Message history
- Entity extraction
- Workflow logs

#### Redis Configuration
Redis is used for:
- Session caching
- Rate limiting
- Temporary storage
- Workflow coordination

### LLM API Configuration

#### Grok4 (X.AI)
```bash
XAI_API_KEY=your_xai_api_key
# Base URL: https://api.x.ai/v1
# Model: grok-4-latest
```

#### Claude (Anthropic)
```bash
ANTHROPIC_API_KEY=your_anthropic_key
# Model: claude-3-sonnet-20240229
```

#### Gemini (Google)
```bash
GOOGLE_AI_API_KEY=your_google_ai_key
# Model: gemini-2.0-flash
```

## 🔧 Advanced Configuration

### Environment Variables Reference

#### Discord Configuration
```bash
DISCORD_TOKEN_GROK4=          # Grok4 bot token
DISCORD_TOKEN_CLAUDE=         # Claude bot token
DISCORD_TOKEN_GEMINI=         # Gemini bot token
DEFAULT_SERVER_ID=            # Discord server ID
GENERAL_CHANNEL_ID=           # General channel ID
```

#### Database Configuration
```bash
POSTGRES_HOST=localhost       # PostgreSQL host
POSTGRES_PORT=5432           # PostgreSQL port
POSTGRES_DB=superagent_n8n   # Database name
POSTGRES_USER=superagent     # Database user
POSTGRES_PASSWORD=           # Database password

REDIS_HOST=localhost         # Redis host
REDIS_PORT=6379             # Redis port
REDIS_PASSWORD=             # Redis password
```

#### n8n Configuration
```bash
N8N_HOST=localhost          # n8n host
N8N_PORT=5678              # n8n port
N8N_BASIC_AUTH_USER=admin  # n8n admin user
N8N_BASIC_AUTH_PASSWORD=   # n8n admin password
N8N_ENCRYPTION_KEY=        # 32-character encryption key
```

### Monitoring & Logging

#### Health Checks
- n8n: http://localhost:5678/healthz
- Health service: http://localhost:8080
- PostgreSQL: `docker exec superagent-postgres pg_isready`
- Redis: `docker exec superagent-redis redis-cli ping`

#### Logs
```bash
# View all logs
docker-compose -f docker/docker-compose.yml logs -f

# View specific service logs
docker-compose -f docker/docker-compose.yml logs -f n8n
docker-compose -f docker/docker-compose.yml logs -f postgres
docker-compose -f docker/docker-compose.yml logs -f redis
```

#### Metrics
- Workflow executions: Check n8n interface
- Database queries: PostgreSQL logs
- Cache performance: Redis INFO command

## 🐛 Troubleshooting

### Common Issues

#### Bot Not Responding
1. Check Discord webhook configuration
2. Verify bot tokens in .env
3. Check n8n workflow execution logs
4. Ensure bot has correct permissions

#### Database Connection Errors
1. Verify PostgreSQL is running: `docker ps`
2. Check connection settings in .env
3. Test connection: `docker exec superagent-postgres pg_isready`

#### n8n Workflow Errors
1. Check workflow logs in n8n interface
2. Verify API keys are configured
3. Test individual nodes in workflows
4. Check network connectivity to APIs

#### Memory Issues
1. Check PostgreSQL logs for errors
2. Verify Redis connectivity
3. Monitor memory usage: `docker stats`

### Performance Tuning

#### Database Optimization
```sql
-- Create additional indexes for performance
CREATE INDEX CONCURRENTLY idx_messages_recent 
ON messages(created_at DESC) WHERE created_at > NOW() - INTERVAL '7 days';

-- Analyze query performance
EXPLAIN ANALYZE SELECT * FROM messages WHERE conversation_id = 'uuid';
```

#### Redis Optimization
```bash
# Monitor Redis performance
redis-cli --latency-history
redis-cli INFO memory
```

#### n8n Optimization
- Increase `EXECUTIONS_TIMEOUT` for long-running workflows
- Adjust `N8N_PAYLOAD_SIZE_MAX` for large responses
- Monitor execution queue length

## 🔒 Security Checklist

- [ ] Change default n8n admin password
- [ ] Use strong PostgreSQL password
- [ ] Configure Redis password
- [ ] Limit Discord bot permissions
- [ ] Enable rate limiting
- [ ] Regular security updates
- [ ] Monitor access logs
- [ ] Backup encryption keys

## 🚀 Production Deployment

### Docker Swarm / Kubernetes
- Use orchestration for high availability
- Implement service discovery
- Configure load balancing
- Set up monitoring and alerting

### Backup Strategy
```bash
# Database backup
docker exec superagent-postgres pg_dump -U superagent superagent_n8n > backup.sql

# n8n workflows backup
docker cp superagent-n8n:/home/node/.n8n ./n8n-backup
```

### Scaling
- Horizontal scaling: Multiple n8n instances
- Database scaling: Read replicas
- Cache scaling: Redis cluster
- Load balancing: nginx/traefik

---

**Need Help?** Check the troubleshooting section or create an issue in the repository.