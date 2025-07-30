# SuperAgent n8n - AI Discord Bot with Memory

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.8+](https://img.shields.io/badge/python-3.8+-blue.svg)](https://www.python.org/downloads/)
[![Docker](https://img.shields.io/badge/docker-%230db7ed.svg?style=flat&logo=docker&logoColor=white)](https://www.docker.com/)
[![n8n](https://img.shields.io/badge/n8n-workflow-orange.svg)](https://n8n.io/)

A **production-ready Discord bot** that combines n8n workflow automation with Python API services for reliable, memory-enabled AI conversations using **Grok4**.

## 🎯 **Features**

- 🤖 **Grok4 AI Integration** - Advanced conversational AI with live data access
- 🧠 **Full Memory System** - Remembers conversation history per user/channel  
- 🔗 **Discord Threading** - Proper reply chains and message references
- 📊 **PostgreSQL Storage** - Persistent conversation and user data
- 🐳 **Docker Deployment** - Containerized infrastructure with n8n
- ⚡ **Real-time Processing** - Sub-second response times
- 🛡️ **Error Handling** - Graceful fallbacks for API timeouts
- 🔍 **Database Tools** - Built-in utilities for monitoring and debugging

## 🏗️ **Architecture**

```
Discord Message → Python Bot → n8n Webhook → Python API Server → PostgreSQL + Grok4 + Discord Response
```

**Why This Architecture:**
- **Reliable**: n8n handles orchestration, Python handles business logic
- **Scalable**: Easy to add more LLMs, channels, and features
- **Maintainable**: Clear separation of concerns between components
- **Debuggable**: Detailed logging and monitoring at every step

## 🚀 Quick Start

```bash
# 1. Clone and setup
git clone <repo-url>
cd SuperAgent-n8n
cp .env.example .env

# 2. Configure environment
# Edit .env with your API keys

# 3. Start with Docker
docker-compose up -d

# 4. Access n8n interface
open http://localhost:5678

# 5. Import workflows
# Import workflows/*.json files via n8n interface
```

## 📁 Repository Structure

```
SuperAgent-n8n/
├── workflows/              # n8n workflow definitions
│   ├── discord-bot-base.json
│   ├── memory-postgres.json
│   └── agents/
├── docker/                 # Docker configuration
│   ├── docker-compose.yml
│   └── n8n/
├── config/                 # Agent configurations
│   ├── agent-personas.json
│   └── llm-prompts.json
├── docs/                   # Documentation
│   ├── SPECS.md           # Detailed specifications
│   ├── SETUP.md           # Setup guide
│   └── ARCHITECTURE.md    # Technical architecture
└── scripts/               # Utility scripts
    ├── setup.sh
    └── deploy.sh
```

## 🤖 Supported Agents

- **Grok4Agent**: Research, analysis, live search capabilities
- **ClaudeAgent**: Code analysis, writing, complex reasoning  
- **GeminiAgent**: Creative tasks, multimodal analysis

## 🔧 Key Features

- ✅ **Visual Workflow Design**: No-code Discord bot creation
- ✅ **Multi-LLM Support**: Best LLM for each task type
- ✅ **Persistent Memory**: PostgreSQL-backed conversation history
- ✅ **Tool Integration**: Discord API, web search, file handling
- ✅ **Scalable Architecture**: Handles enterprise workloads
- ✅ **Easy Monitoring**: Visual workflow execution logs

## 📊 Success Metrics

- **Response Rate**: >99% of mentions get responses
- **Response Time**: <2 seconds average
- **Uptime**: >99.9% availability
- **Accuracy**: Contextually appropriate responses
- **Scalability**: Handle 1000+ concurrent users

## 🔗 Links

- [n8n Documentation](https://docs.n8n.io/)
- [Discord Developer Portal](https://discord.com/developers/docs)
- [Project Specifications](docs/SPECS.md)

---

**Previous Attempt**: This replaces the complex MCP-based approach with a proven, reliable n8n workflow system.