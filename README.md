# SuperAgent n8n - AI Discord Bot with Memory

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![Docker](https://img.shields.io/badge/docker-%230db7ed.svg?style=flat&logo=docker&logoColor=white)](https://www.docker.com/)
[![Grok4](https://img.shields.io/badge/Grok4-AI-red.svg)](https://x.ai/)

A **production-ready Discord bot** with **zero-friction setup** - get an AI-powered Discord bot with full memory running in under 2 minutes!

## 🎯 **Features**

- 🤖 **Grok4 AI Integration** - Latest Grok-4 model with live data access
- 🧠 **Full Memory System** - Remembers conversation history per user/channel  
- 🔗 **Discord Threading** - Proper reply chains and message references
- 📊 **PostgreSQL Storage** - Persistent conversation and user data
- 🐳 **One-Command Deploy** - Complete setup with single script
- ⚡ **Real-time Processing** - Sub-second response times
- 🛡️ **Error Handling** - Graceful fallbacks for API timeouts
- 📊 **Built-in Monitoring** - Health checks and statistics endpoints

## 🏗️ **Architecture**

```
Discord Message → Combined Python Service → PostgreSQL + Grok4 → Discord Response
```

**Why This Design:**
- **Simple**: Single containerized service, no complex orchestration
- **Reliable**: Direct API calls, no middleware dependencies
- **Fast**: Minimal latency with direct processing
- **Maintainable**: Everything in one place, easy to debug

## 🚀 **Zero-Friction Setup**

```bash
# 1. Clone repository
git clone https://github.com/glindberg2000/SuperAgent-n8n.git
cd SuperAgent-n8n

# 2. One-command setup (creates .env, starts everything)
./start.sh
```

**That's it!** The script will:
- ✅ Check dependencies (Docker, Docker Compose)
- ✅ Create `.env` file with template (you add your keys)
- ✅ Start PostgreSQL database with auto-initialization
- ✅ Build and start Discord bot service
- ✅ Wait for services to be healthy
- ✅ Show you monitoring URLs and test instructions

## 🔑 **Required API Keys**

You need just **two things**:

1. **Discord Bot Token** - Get from [Discord Developer Portal](https://discord.com/developers/applications)
2. **Grok4 API Key** - Get from [x.ai](https://x.ai)

The setup script creates a `.env` file template - just fill in your keys and run `./start.sh` again!

## 📁 **Repository Structure**

```
SuperAgent-n8n/
├── discord_combined_service.py    # Main Discord bot + API server
├── start.sh                       # One-command setup script
├── docker-compose.simple.yml      # Docker configuration
├── requirements-api.txt           # Python dependencies
├── docker/                        # Docker build files
│   ├── Dockerfile.discord-bot     # Container definition
│   └── init.sql                   # Database schema
├── tests/                         # Test configurations
├── docs/                          # Comprehensive documentation
└── workflows/                     # Optional n8n workflows (advanced)
```

## 📊 **Monitoring & Health Checks**

Once running, monitor your bot with built-in endpoints:

```bash
# Check if everything is healthy
curl http://localhost:5001/health

# View bot statistics
curl http://localhost:5001/stats

# Watch real-time logs  
docker-compose -f docker-compose.simple.yml logs -f discord-bot
```

## 🎛️ **Advanced Setup (Optional)**

Want visual workflow management? Add n8n:

```bash
# Start with advanced features
./start.sh --advanced
```

This adds:
- 🔄 **n8n Visual Editor**: `http://localhost:5678` (admin / superagent-n8n-2025)
- 📝 **Workflow Management**: Import from `workflows/` directory
- 🔧 **Custom Logic**: Visual programming for complex responses

## 💡 **Features in Detail**

- **🧠 Smart Memory**: Remembers context across conversations per user/channel
- **⚡ Fast Responses**: Direct processing, <2 second response times
- **🛡️ Error Recovery**: Graceful fallbacks for API timeouts and errors
- **📊 Statistics**: Track usage, response times, and user engagement
- **🔍 Debug Mode**: Comprehensive logging for troubleshooting
- **🐳 Zero Config**: Everything configured with sensible defaults

## 🚀 **Success Metrics**

- **Setup Time**: <2 minutes from clone to running bot
- **Response Rate**: >99% of mentions get responses  
- **Response Time**: <2 seconds average
- **Memory Accuracy**: Contextual responses using conversation history
- **Uptime**: >99.9% with Docker restart policies

## 🔗 **Resources**

- 📚 [Complete Documentation](docs/)
- 🎮 [Discord Developer Portal](https://discord.com/developers/applications)
- 🤖 [Grok4 API Documentation](https://x.ai)
- 🐳 [Docker Installation](https://docs.docker.com/get-docker/)

---

**Built for Simplicity**: This system replaces complex MCP/n8n orchestration with a single, reliable service that "just works".