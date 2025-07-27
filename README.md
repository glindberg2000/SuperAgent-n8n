# SuperAgent n8n - Multi-Agent Discord AI Chatbot

A reliable, production-ready Discord chatbot system using n8n workflows with multi-LLM support and memory.

## 🎯 Project Goals

Build a Discord bot system that provides:
- **Multi-Agent Support**: Grok4, Claude, and Gemini personalities
- **Intelligent Memory**: Conversation context and entity tracking  
- **Tool Calling**: Discord API integration for server info, message reading, etc.
- **Production Ready**: 99%+ uptime, sub-2s response time
- **Team Friendly**: Visual workflow management via n8n interface

## 🏗️ Architecture

**n8n-First Design** - Workflows handle all complexity:
```
Discord Message → n8n Webhook → Agent Router → LLM Processing → Memory Store → Discord Response
```

**Core Components:**
- **n8n Workflows**: Visual automation for Discord + LLM integration
- **PostgreSQL**: Conversation memory and context storage
- **Redis**: Fast caching and session management
- **Docker**: Containerized deployment

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