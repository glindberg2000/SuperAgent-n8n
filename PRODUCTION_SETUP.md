# SuperAgent n8n - Production Setup Guide

## 🎉 **System Status: FULLY OPERATIONAL**

This guide will get you from zero to a working Discord bot with AI memory in **under 10 minutes**.

## **Architecture Overview**

```
Discord → Python Bot → n8n → Python API → PostgreSQL + Grok4 → Discord Response
```

**Why this architecture works:**
- **Discord Bot**: Handles Discord events, forwards to n8n
- **n8n**: Simple workflow orchestration (just 1 HTTP call)
- **Python API**: All business logic, database, AI processing
- **PostgreSQL**: Conversation memory and user data
- **Clean separation**: Each component does what it's best at

## **Prerequisites**

- **Python 3.8+** with pip
- **Docker & Docker Compose** (for n8n stack)
- **Discord Bot Token** (from Discord Developer Portal)
- **Grok4 API Key** (from x.ai)

## **Step 1: Environment Setup**

```bash
# Clone repository
git clone <repo-url>
cd SuperAgent-n8n

# Create Python virtual environment
python -m venv .venv
source .venv/bin/activate  # Linux/Mac
# .venv\Scripts\activate     # Windows

# Install Python dependencies
pip install discord.py aiohttp python-dotenv
pip install -r requirements-api.txt
```

## **Step 2: Configuration**

Create `.env` file with your credentials:

```bash
# Discord Configuration
DISCORD_TOKEN_GROK4=your_discord_bot_token_here
DEFAULT_SERVER_ID=your_discord_server_id

# AI API Keys
XAI_API_KEY=your_grok4_api_key_here

# Database Configuration (use these defaults)
POSTGRES_USER=superagent
POSTGRES_PASSWORD=superagent-db-2025
POSTGRES_DB=superagent
POSTGRES_HOST=postgres
POSTGRES_PORT=5436
```

## **Step 3: Start Infrastructure**

```bash
# Start n8n + PostgreSQL + Redis stack
docker-compose -f docker/docker-compose.yml up -d

# Verify services are running
docker ps
# Should show: superagent-n8n (n8n), postgres, redis containers
```

## **Step 4: Configure n8n Workflow**

1. **Open n8n**: http://localhost:5678
2. **Create account/login**
3. **Import workflow**: Upload `workflows/discord-grok4-python-api.json`
4. **Configure credentials**:
   - Add PostgreSQL credential: `postgres-main` with your database details
5. **Activate workflow**: Toggle the workflow to "Active"

## **Step 5: Start Python Services**

**Terminal 1 - API Server:**
```bash
source .venv/bin/activate
python discord_api_server.py
# Should see: ✅ Grok4 API configured, ✅ Discord token configured
```

**Terminal 2 - Discord Bot:**
```bash
source .venv/bin/activate
python discord_forwarder.py
# Should see: Logged in as YourBot#1234
```

## **Step 6: Test the Bot**

In Discord:
1. **Direct mention**: `@YourBot hello there!`
2. **Role mention**: `@role_name are you working?`
3. **Contains "grok"**: `hey grok, what's up?`

**Expected behavior:**
- Bot responds with AI-generated content
- Remembers previous conversation context
- Stores all messages in PostgreSQL database

## **Verification & Monitoring**

### Check Database Contents
```bash
python check_database.py
```

### View Logs
```bash
# API Server logs (in Terminal 1)
# Shows: message processing, database operations, Grok4 calls

# Discord Bot logs (in Terminal 2) 
# Shows: Discord events, message forwarding

# n8n logs
docker logs superagent-n8n
```

### Health Checks
```bash
# Test API server
curl http://localhost:5001/health

# Test n8n
curl http://localhost:5678

# Test database connection
python check_database.py
```

## **Production Deployment**

### **For Production Use:**

1. **Use production WSGI server** instead of Flask dev server:
```bash
pip install gunicorn
gunicorn -w 4 -b 0.0.0.0:5001 discord_api_server:app
```

2. **Use process manager** for reliability:
```bash
# Install PM2
npm install -g pm2

# Start services with PM2
pm2 start discord_api_server.py --interpreter python3 --name discord-api
pm2 start discord_forwarder.py --interpreter python3 --name discord-bot
pm2 save
pm2 startup
```

3. **Configure reverse proxy** (nginx/Apache) for external access

4. **Set up SSL/HTTPS** for webhook endpoints

5. **Configure monitoring** (logs, metrics, alerts)

## **System Features**

### ✅ **What Works**
- **Full conversation memory** - Bot remembers previous messages per user/channel
- **Multiple trigger types** - Direct mentions, role mentions, keyword detection
- **Discord reply threading** - Proper reply chains
- **Database persistence** - PostgreSQL with full conversation history
- **Error handling** - Graceful fallbacks for API timeouts
- **Docker deployment** - Containerized infrastructure
- **Development tools** - Database inspection, health checks

### 🔄 **Architecture Benefits**
- **Reliable**: n8n handles orchestration, Python handles complexity
- **Scalable**: Easy to add more LLMs, channels, features  
- **Maintainable**: Clear separation of concerns
- **Debuggable**: Detailed logging at every step
- **Extensible**: Ready for RAG, file uploads, multi-agent routing

## **Troubleshooting**

### **Bot not responding?**
1. Check Discord bot is logged in: `discord_forwarder.py` logs
2. Verify n8n workflow is active: http://localhost:5678
3. Test API server: `curl http://localhost:5001/health`
4. Check database: `python check_database.py`

### **Memory not working?**
1. Verify PostgreSQL is running: `docker ps`
2. Check database schema: `python check_database.py`
3. Look for database errors in API server logs

### **Grok4 timeouts?**
- Normal occasional issue, system has automatic fallbacks
- Check API key is valid: `XAI_API_KEY` in `.env`

### **Docker networking issues?**
- n8n workflow should use `host.docker.internal:5001`
- Python API server runs on host, not in Docker

## **Next Steps**

The system is now ready for enhancements:
- 📁 **File upload/download** support
- 🧠 **RAG (Retrieval Augmented Generation)** integration
- 🤖 **Multi-agent routing** (Claude, Gemini)
- 🌐 **Web dashboard** for monitoring
- 📊 **Analytics and metrics**
- 🔍 **Vector search** for semantic memory

**Your Discord bot is fully operational with AI memory! ** 🎉

## **Support**

- **Database inspection**: `python check_database.py`
- **Health monitoring**: `curl http://localhost:5001/health`
- **Logs**: Check both Python terminals and `docker logs superagent-n8n`
- **n8n interface**: http://localhost:5678 for workflow debugging