# SuperAgent n8n - Technical Architecture

## 🏗️ High-Level Architecture

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│    Discord      │    │      n8n        │    │   Data Layer    │
│                 │    │   Workflows     │    │                 │
│ ┌─────────────┐ │    │ ┌─────────────┐ │    │ ┌─────────────┐ │
│ │ Bot Messages│ │◄──►│ │ Message     │ │◄──►│ │ PostgreSQL  │ │
│ │ Mentions    │ │    │ │ Handler     │ │    │ │ (Memory)    │ │
│ │ Reactions   │ │    │ │             │ │    │ │             │ │
│ └─────────────┘ │    │ └─────────────┘ │    │ └─────────────┘ │
│                 │    │                 │    │                 │
│ ┌─────────────┐ │    │ ┌─────────────┐ │    │ ┌─────────────┐ │
│ │ Webhooks    │ │◄──►│ │ Agent       │ │◄──►│ │ Redis       │ │
│ │ Events      │ │    │ │ Router      │ │    │ │ (Cache)     │ │
│ └─────────────┘ │    │ └─────────────┘ │    │ └─────────────┘ │
└─────────────────┘    └─────────────────┘    └─────────────────┘
                                │
                                ▼
                       ┌─────────────────┐
                       │   LLM APIs      │
                       │                 │
                       │ ┌─────────────┐ │
                       │ │ Grok4       │ │
                       │ │ Claude      │ │
                       │ │ Gemini      │ │
                       │ └─────────────┘ │
                       └─────────────────┘
```

## 🔄 Workflow Design Patterns

### 1. Message Processing Flow

```
Discord Mention
│
├── Webhook Trigger (n8n)
│   │
│   ├── Message Parser
│   │   ├── Extract user info
│   │   ├── Parse message content  
│   │   └── Identify intent
│   │
│   ├── Context Retrieval (PostgreSQL)
│   │   ├── Get user history
│   │   ├── Load conversation context
│   │   └── Fetch relevant entities
│   │
│   ├── Agent Router
│   │   ├── Analyze request type
│   │   ├── Select appropriate LLM
│   │   └── Route to agent workflow
│   │
│   ├── LLM Processing
│   │   ├── Build context prompt
│   │   ├── Call LLM API
│   │   ├── Process tool requests
│   │   └── Generate response
│   │
│   ├── Memory Update (PostgreSQL)
│   │   ├── Store user message
│   │   ├── Store agent response
│   │   └── Update entity tracking
│   │
│   └── Discord Response
│       ├── Format message
│       ├── Send to Discord API
│       └── Log completion
│
└── Success/Error Handling
```

### 2. Tool Calling Loop

```
LLM Requests Tool
│
├── Tool Call Parser
│   ├── Validate tool name
│   ├── Check parameters
│   └── Verify permissions
│
├── Tool Execution
│   ├── Discord API Call
│   ├── Error Handling
│   └── Result Processing
│
├── Result Formatting
│   ├── Structure data
│   ├── Add context
│   └── Prepare for LLM
│
└── LLM Continuation
    ├── Send results to LLM
    ├── Process follow-up
    └── Generate final response
```

## 📊 Data Architecture

### PostgreSQL Schema

```sql
-- Users and Discord entities
CREATE TABLE discord_users (
    id BIGINT PRIMARY KEY,
    username VARCHAR(255),
    display_name VARCHAR(255),
    avatar_url TEXT,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

-- Conversations (threads of related messages)
CREATE TABLE conversations (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    discord_channel_id BIGINT NOT NULL,
    discord_thread_id BIGINT,
    user_id BIGINT REFERENCES discord_users(id),
    agent_type VARCHAR(50),
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

-- Individual messages
CREATE TABLE messages (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    conversation_id UUID REFERENCES conversations(id),
    discord_message_id BIGINT,
    user_id BIGINT REFERENCES discord_users(id),
    content TEXT NOT NULL,
    message_type VARCHAR(20) DEFAULT 'user', -- 'user', 'assistant', 'system'
    agent_name VARCHAR(50),
    metadata JSONB,
    created_at TIMESTAMP DEFAULT NOW()
);

-- Entity tracking for memory
CREATE TABLE entities (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id BIGINT REFERENCES discord_users(id),
    entity_type VARCHAR(50), -- 'preference', 'fact', 'context'
    entity_key VARCHAR(255),
    entity_value TEXT,
    confidence FLOAT DEFAULT 1.0,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

-- Workflow execution logs
CREATE TABLE workflow_executions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    workflow_name VARCHAR(255),
    execution_id VARCHAR(255),
    status VARCHAR(50),
    input_data JSONB,
    output_data JSONB,
    error_message TEXT,
    duration_ms INTEGER,
    created_at TIMESTAMP DEFAULT NOW()
);
```

### Redis Cache Structure

```
# User session cache (TTL: 1 hour)
user_session:{user_id} = {
    "last_active": timestamp,
    "preferred_agent": "grok4|claude|gemini",
    "conversation_id": "uuid",
    "context_summary": "text"
}

# Recent conversation cache (TTL: 6 hours)  
conversation:{conversation_id} = {
    "messages": [...recent_messages],
    "entities": {...relevant_entities},
    "agent_context": "accumulated_context"
}

# Rate limiting (TTL: varies)
rate_limit:{user_id}:{timeframe} = request_count

# Tool call cache (TTL: 5 minutes)
tool_result:{hash} = cached_result
```

## 🔌 n8n Workflow Specifications

### Core Workflow Files

#### 1. `discord-bot-base.json`
- **Purpose**: Main Discord message handling workflow
- **Triggers**: Discord webhook events
- **Nodes**: 
  - Webhook (Discord events)
  - Message Parser (JavaScript)
  - Context Retrieval (PostgreSQL)
  - Agent Router (Switch)
  - Response Formatter (JavaScript)
  - Discord Reply (HTTP Request)

#### 2. `memory-postgres.json`
- **Purpose**: Memory management and context retrieval
- **Triggers**: Called by other workflows
- **Nodes**:
  - Context Query (PostgreSQL)
  - Entity Extraction (JavaScript)
  - Memory Update (PostgreSQL)
  - Cache Update (Redis)

#### 3. `agent-grok4.json`
- **Purpose**: Grok4-specific processing workflow
- **Triggers**: Routed from main workflow
- **Nodes**:
  - Prompt Builder (JavaScript)
  - Grok4 API Call (HTTP Request)
  - Tool Call Parser (JavaScript)
  - Tool Executor (Switch → HTTP Request)
  - Response Generator (JavaScript)

#### 4. `agent-claude.json`
- **Purpose**: Claude-specific processing workflow
- **Similar structure to Grok4 with Claude API specifics**

#### 5. `agent-gemini.json`
- **Purpose**: Gemini-specific processing workflow
- **Similar structure with Gemini API specifics**

### Workflow Design Principles

1. **Modular Design**: Each workflow has single responsibility
2. **Error Handling**: Every node has error branches
3. **Monitoring**: Built-in execution logging
4. **Configuration**: Environment-driven settings
5. **Scalability**: Designed for parallel execution

## 🔧 Configuration Management

### Environment-Based Configuration

```javascript
// n8n workflow configuration
const config = {
  discord: {
    tokens: {
      grok4: process.env.DISCORD_TOKEN_GROK4,
      claude: process.env.DISCORD_TOKEN_CLAUDE,
      gemini: process.env.DISCORD_TOKEN_GEMINI
    },
    defaultServerId: process.env.DEFAULT_SERVER_ID,
    webhookUrl: process.env.N8N_WEBHOOK_URL
  },
  
  llm: {
    grok4: {
      apiKey: process.env.XAI_API_KEY,
      baseUrl: "https://api.x.ai/v1",
      model: "grok-4-latest",
      maxTokens: 4000
    },
    claude: {
      apiKey: process.env.ANTHROPIC_API_KEY,
      model: "claude-3-sonnet-20240229",
      maxTokens: 4000
    },
    gemini: {
      apiKey: process.env.GOOGLE_AI_API_KEY,
      model: "gemini-2.0-flash",
      maxTokens: 4000
    }
  },
  
  memory: {
    postgres: {
      host: process.env.POSTGRES_HOST,
      database: process.env.POSTGRES_DB,
      user: process.env.POSTGRES_USER,
      password: process.env.POSTGRES_PASSWORD
    },
    redis: {
      host: process.env.REDIS_HOST,
      port: process.env.REDIS_PORT
    },
    contextWindow: 10, // messages
    cacheTimeout: 3600 // seconds
  }
}
```

## 🚀 Deployment Architecture

### Docker Composition

```yaml
version: '3.8'
services:
  n8n:
    image: n8nio/n8n:latest
    ports:
      - "5678:5678"
    environment:
      - N8N_BASIC_AUTH_ACTIVE=true
      - N8N_BASIC_AUTH_USER=admin
      - N8N_BASIC_AUTH_PASSWORD=${N8N_PASSWORD}
      - N8N_ENCRYPTION_KEY=${N8N_ENCRYPTION_KEY}
    volumes:
      - n8n_data:/home/node/.n8n
      - ./workflows:/home/node/.n8n/workflows
    depends_on:
      - postgres
      - redis

  postgres:
    image: postgres:15
    environment:
      - POSTGRES_DB=${POSTGRES_DB}
      - POSTGRES_USER=${POSTGRES_USER}
      - POSTGRES_PASSWORD=${POSTGRES_PASSWORD}
    volumes:
      - postgres_data:/var/lib/postgresql/data
      - ./init.sql:/docker-entrypoint-initdb.d/init.sql

  redis:
    image: redis:7-alpine
    ports:
      - "6379:6379"
    volumes:
      - redis_data:/data

volumes:
  n8n_data:
  postgres_data:
  redis_data:
```

### Scaling Considerations

1. **Horizontal Scaling**: Multiple n8n instances with load balancer
2. **Database Scaling**: PostgreSQL read replicas for memory queries
3. **Cache Scaling**: Redis Cluster for high-throughput caching
4. **Monitoring**: Prometheus metrics with Grafana dashboards

---

This architecture provides a solid foundation for reliable, scalable Discord bot operations using proven technologies.