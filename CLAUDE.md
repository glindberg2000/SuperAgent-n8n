# SuperAgent n8n - Multi-Agent Discord System

## Project Overview
SuperAgent n8n is a reliable, production-ready Discord bot system using n8n workflows with multi-LLM support and memory. This project replaces the failed MCP-based approach with proven enterprise technology.

## Current Status - n8n Implementation
- ✅ Complete n8n workflow architecture designed
- ✅ PostgreSQL + Redis + Docker stack configured
- ✅ Multi-agent support (Grok4, Claude, Gemini) specified
- ✅ Production-ready deployment configuration
- ✅ Comprehensive documentation and setup guides
- ✅ Automated setup scripts created
- 🚀 **Ready for implementation** - Working bot expected in 1-5 days

## Architecture

### **Core Production Stack** ✅
```
SuperAgent-n8n/
├── workflows/                    # n8n workflow definitions
│   ├── discord-bot-base.json    # Main Discord message handler
│   ├── memory-postgres.json     # Memory management workflow
│   └── agents/                  # Agent-specific workflows
│       ├── agent-grok4.json
│       ├── agent-claude.json
│       └── agent-gemini.json
├── docker/                      # Docker configuration
│   ├── docker-compose.yml      # Full stack deployment
│   └── init.sql                 # Database initialization
├── config/                      # Agent configurations
│   └── agent-personas.json     # Multi-agent personalities
├── scripts/                     # Automation scripts
│   └── setup.sh               # One-click setup
└── .env.example                # Environment template
```

### **Documentation & Guides** 📚
```
├── CLAUDE.md                    # This project documentation (updated for n8n)
├── docs/
│   ├── SPECS.md                # Detailed technical specifications
│   ├── ARCHITECTURE.md         # n8n workflow architecture
│   └── SETUP.md               # Comprehensive setup guide
├── MIGRATION_FROM_MCP.md       # Why we pivoted from MCP
└── README.md                   # Project overview
```

### **Data Layer** 📁
```
├── PostgreSQL                  # Primary data store
│   ├── discord_users          # User management
│   ├── conversations          # Conversation threads
│   ├── messages               # Message history
│   ├── entities               # Entity tracking for memory
│   └── workflow_executions    # n8n execution logs
├── Redis                      # Caching layer
│   ├── user_sessions          # Active user sessions
│   ├── conversation_cache     # Recent conversation cache
│   └── rate_limiting          # API rate limit tracking
└── n8n Data                   # Workflow persistence
    ├── workflow_definitions   # Visual workflow storage
    └── execution_history      # Workflow execution logs
```

## Quick Start

### 1. Environment Setup
```bash
# Clone the new repository
git clone git@github.com:glindberg2000/SuperAgent-n8n.git
cd SuperAgent-n8n

# Copy environment template
cp .env.example .env

# Edit .env with your API keys and Discord tokens
# At minimum, set:
# - DISCORD_TOKEN_GROK4
# - XAI_API_KEY  
# - DEFAULT_SERVER_ID
# - Other LLM API keys as needed
```

### 2. Automated Setup
```bash
# One-click setup (recommended)
./scripts/setup.sh

# Or manual Docker setup
docker-compose -f docker/docker-compose.yml up -d
```

### 3. n8n Configuration
```bash
# Access n8n interface
open http://localhost:5678

# Import workflows from workflows/ directory
# Configure Discord webhooks
# Test agent workflows
```

### 4. Test the System
```bash
# Send test message in Discord
@Grok4Agent hello!

# Monitor n8n execution logs
# Check database for stored conversations
```

## n8n Workflow Configuration
The system uses n8n workflows instead of complex Python code for reliability and maintainability.

### Core Workflows
1. **Discord Bot Base**: Main message handling and routing
2. **Memory Management**: PostgreSQL conversation storage and retrieval
3. **Agent Workflows**: LLM-specific processing (Grok4, Claude, Gemini)
4. **Tool Execution**: Discord API integration and tool calling

## Features

### 🧠 Memory & Context Management
- PostgreSQL-based conversation history with thread awareness
- Redis caching for fast context retrieval
- Cross-conversation entity tracking and memory
- Configurable context windows per agent

### 🤖 Multi-LLM Support
- **Grok4**: Research, analysis, detailed explanations with live search
- **Claude**: Code analysis, writing, complex reasoning
- **Gemini**: Creative tasks, multimodal analysis, collaboration
- Intelligent agent routing based on message content

### 🛡️ Production Ready
- n8n enterprise workflow platform (99.9% uptime)
- Docker containerized deployment
- Built-in monitoring and error handling
- Visual workflow management and debugging

### 📊 Monitoring & Logging
- n8n visual execution logs
- PostgreSQL conversation analytics
- Redis performance metrics
- Health checks for all services

## Configuration

### Agent Configuration (`config/agent-personas.json`)
```json
{
  "agents": {
    "grok4_agent": {
      "name": "Grok4Agent",
      "llm_type": "grok4",
      "model": "grok-4-latest",
      "personality": "helpful, analytical, and engaging",
      "capabilities": ["research", "analysis", "live search"]
    }
  }
}
```

### n8n Workflow Configuration
- Visual workflow design via n8n interface
- Discord webhook integration
- PostgreSQL and Redis connections
- LLM API integrations

## Roadmap

### Phase 1: Foundation (Day 1) ✅
- [x] Repository setup and documentation
- [x] Docker stack configuration
- [x] Database schema design
- [ ] Basic Discord webhook workflow

### Phase 2: Core Functionality (Days 2-3)
- [ ] Agent routing workflows
- [ ] LLM integration workflows  
- [ ] Memory management workflows
- [ ] Discord tool calling

### Phase 3: Advanced Features (Day 4)
- [ ] Multi-agent coordination
- [ ] Advanced memory features
- [ ] Performance optimization
- [ ] Error handling refinement

### Phase 4: Production (Day 5)
- [ ] Security hardening
- [ ] Monitoring setup
- [ ] Deployment automation
- [ ] Documentation completion

## Environment Variables Needed
```bash
# Discord
DISCORD_TOKEN_GROK4=bot_token
DISCORD_TOKEN_CLAUDE=bot_token
DISCORD_TOKEN_GEMINI=bot_token
DEFAULT_SERVER_ID=discord_server_id

# LLM APIs
XAI_API_KEY=grok_api_key
ANTHROPIC_API_KEY=claude_api_key
GOOGLE_AI_API_KEY=gemini_api_key

# Infrastructure
POSTGRES_PASSWORD=secure_password
REDIS_PASSWORD=secure_password
N8N_BASIC_AUTH_PASSWORD=admin_password
```

## Migration from MCP

This repository represents a **complete architectural pivot** from the previous MCP-based approach:

### Why We Migrated
- **0% Success Rate**: 6 failed MCP implementations
- **Infrastructure Issues**: Complex async/sync conflicts
- **Data Format Problems**: MCP server inconsistencies
- **Over-Engineering**: Unnecessary complexity

### n8n Benefits
- **Proven Platform**: 750K+ active bots, enterprise-scale
- **Visual Development**: No-code workflow creation
- **Built-in Reliability**: 99.9% uptime, error handling
- **Fast Implementation**: Days instead of weeks

See `MIGRATION_FROM_MCP.md` for detailed analysis.

## Notes
- Uses n8n workflows for all Discord and LLM interactions
- PostgreSQL provides reliable data persistence
- Redis enables high-performance caching
- Docker ensures consistent deployment across environments
- Visual workflow management replaces complex Python debugging

## 🎉 Success Metrics
- **Working Discord Bot**: 1-5 days (vs. weeks of MCP debugging)
- **Response Rate**: >99% (vs. 0% with MCP)
- **Response Time**: <2 seconds average
- **Uptime**: >99.9% reliability
- **Maintainability**: Visual workflows vs. complex Python code

**This n8n approach will deliver a production-ready Discord bot system with proven reliability and enterprise-grade scalability.**