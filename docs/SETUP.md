# Setup Guide

**Complete deployment instructions for SuperAgent n8n Discord bot.**

## Prerequisites

- **Python 3.8+** with pip
- **Docker & Docker Compose** 
- **Discord Bot Token** - [Create one here](https://discord.com/developers/applications)
- **Grok4 API Key** - [Get from x.ai](https://x.ai)

## Environment Setup

### 1. Clone Repository
```bash
git clone https://github.com/your-username/SuperAgent-n8n.git
cd SuperAgent-n8n
```

### 2. Python Environment
```bash
# Create virtual environment
python -m venv .venv
source .venv/bin/activate  # Linux/Mac
# .venv\Scripts\activate     # Windows

# Install dependencies
pip install -r requirements-api.txt
```

### 3. Environment Configuration
```bash
cp .env.example .env
```

Edit `.env` with your credentials:
```bash
# Discord Configuration
DISCORD_TOKEN_GROK4=your_discord_bot_token_here
DEFAULT_SERVER_ID=your_discord_server_id

# AI API Keys
XAI_API_KEY=your_grok4_api_key_here

# Database Configuration (use defaults)
POSTGRES_USER=superagent
POSTGRES_PASSWORD=superagent-db-2025
POSTGRES_DB=superagent
POSTGRES_HOST=postgres
POSTGRES_PORT=5436
```

## Infrastructure Deployment

### 1. Start Docker Stack
```bash
docker-compose -f docker/docker-compose.yml up -d
```

This starts:
- n8n workflow server (port 5678)
- PostgreSQL database (port 5436)
- Redis cache (port 6379)

### 2. Verify Services
```bash
docker ps
# Should show: superagent-n8n, postgres, redis containers

curl http://localhost:5678
# Should return n8n interface
```

## n8n Configuration

### 1. Access n8n Interface
Open http://localhost:5678 in your browser

### 2. First-time Setup
- Create admin account
- Skip onboarding tutorials

### 3. Configure PostgreSQL Credentials
1. Go to **Settings** → **Credentials**
2. Add new **PostgreSQL** credential
3. Name: `SuperAgent PostgreSQL`
4. Host: `postgres`
5. Database: `superagent`
6. User: `superagent`
7. Password: `superagent-db-2025`
8. Port: `5432`

### 4. Import Workflow
1. Click **Import from file**
2. Select `workflows/discord-grok4-python-api.json`
3. Click **Import**

### 5. Activate Workflow
1. Open the imported workflow
2. Toggle switch to **Active**
3. Verify webhook URL shows as active

## Service Deployment

### 1. Start API Server
```bash
# Terminal 1
source .venv/bin/activate
python discord_api_server.py
```

Expected output:
```
Starting Discord API Server...
✅ Grok4 API configured
✅ Discord token configured
Database: localhost:5436/superagent
* Running on http://127.0.0.1:5001
```

### 2. Start Discord Bot
```bash
# Terminal 2
source .venv/bin/activate
python discord_forwarder.py
```

Expected output:
```
Logged in as YourBot#1234 (ID: 123456789)
Forwarding messages to: http://localhost:5678/webhook/grok4-python-api
```

## Testing

### 1. Basic Test
In Discord channel where bot has access:
```
@YourBot hello there!
```

### 2. Memory Test
```
@YourBot my name is John
@YourBot what's my name?
```

Bot should remember "John" from the previous message.

### 3. Database Verification
```bash
python check_database.py
```

Should show users and message history.

## Monitoring

### Health Checks
```bash
# API Server
curl http://localhost:5001/health

# n8n
curl http://localhost:5678

# Database
python check_database.py
```

### Logs
- **API Server**: Terminal 1 output
- **Discord Bot**: Terminal 2 output  
- **n8n**: `docker logs superagent-n8n`
- **Database**: `docker logs superagent-n8n-postgres-1`

## Troubleshooting

### Bot Not Responding
1. Check Discord bot logs for connection errors
2. Verify n8n workflow is active
3. Test API server: `curl http://localhost:5001/health`
4. Check database connection: `python check_database.py`

### n8n Connection Issues
1. Ensure Docker containers are running: `docker ps`
2. Check n8n logs: `docker logs superagent-n8n`
3. Verify port 5678 is accessible

### Database Issues
1. Check PostgreSQL container: `docker ps | grep postgres`
2. Verify database schema: `python check_database.py`
3. Check connection in n8n credentials

### Memory Not Working
1. Verify PostgreSQL credentials in n8n
2. Check database for stored messages: `python check_database.py`
3. Look for database errors in API server logs

## Production Deployment

### Process Management
```bash
# Install PM2
npm install -g pm2

# Start services
pm2 start discord_api_server.py --interpreter python3 --name discord-api
pm2 start discord_forwarder.py --interpreter python3 --name discord-bot

# Save configuration
pm2 save
pm2 startup
```

### WSGI Server
```bash
# Install Gunicorn
pip install gunicorn

# Run API server with Gunicorn
gunicorn -w 4 -b 0.0.0.0:5001 discord_api_server:app
```

### SSL/HTTPS
Configure reverse proxy (nginx/Apache) for external webhook access.

### Monitoring
Set up logging, metrics, and health check monitoring for production use.

## Next Steps

Once the basic system is working:
1. **File Upload Support** - Handle Discord attachments
2. **RAG Integration** - Add document retrieval
3. **Multi-Agent Routing** - Add Claude, Gemini
4. **Web Dashboard** - Management interface
5. **Analytics** - Usage metrics and insights

Your SuperAgent n8n Discord bot is now ready for operation! 🚀