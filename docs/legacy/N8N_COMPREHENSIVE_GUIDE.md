# n8n Comprehensive Guide for SuperAgent Discord Bot

## Table of Contents
1. [What is n8n?](#what-is-n8n)
2. [Core Concepts](#core-concepts)
3. [Building Workflows Programmatically](#building-workflows-programmatically)
4. [Integrating with Discord, PostgreSQL, Redis, and LLMs](#integrations)
5. [Developing Without the UI](#developing-without-ui)
6. [Best Practices for Discord Bots](#best-practices)
7. [n8n vs Traditional Coding](#comparison)
8. [SuperAgent-n8n Implementation Guide](#implementation-guide)

## What is n8n?

n8n (pronounced "n-eight-n") is a **workflow automation platform** that allows you to connect different services and build complex automation flows. Think of it as a visual programming environment where you create "workflows" by connecting "nodes" that represent different operations or services.

### Key Characteristics:
- **Open-source and self-hostable**: You control your data and infrastructure
- **Node-based architecture**: Each operation is a node that processes data
- **JSON-based workflows**: Everything can be defined as code
- **Extensible**: Create custom nodes for any API or service
- **Real-time execution**: Workflows run immediately or on triggers
- **Built-in error handling**: Retry logic, error branches, and notifications

### Why n8n for Discord Bots?

Traditional Discord bot development requires:
- Managing event loops and websocket connections
- Handling rate limits and reconnections
- Building complex state management
- Orchestrating multiple services

n8n simplifies this by:
- Providing pre-built Discord nodes with connection management
- Offering visual flow control and error handling
- Enabling easy integration with databases and APIs
- Supporting parallel and sequential execution patterns

## Core Concepts

### 1. Nodes
A **node** is the fundamental building block in n8n. Each node:
- Performs a specific task (send message, query database, call API)
- Has inputs and outputs
- Can transform data
- Has configurable parameters

Example node types:
- **Trigger Nodes**: Start workflows (Discord message received, webhook, schedule)
- **Action Nodes**: Perform operations (send Discord message, query database)
- **Logic Nodes**: Control flow (IF conditions, loops, merge data)

### 2. Workflows
A **workflow** is a collection of connected nodes that:
- Defines the automation logic
- Specifies execution order
- Handles data flow between nodes
- Can be triggered manually or automatically

### 3. Connections
**Connections** link nodes together and define:
- Data flow direction
- Execution sequence
- Conditional paths
- Error handling routes

### 4. Triggers
**Triggers** are special nodes that start workflows:
- **Webhook triggers**: HTTP endpoints
- **Schedule triggers**: Cron-based execution
- **App-specific triggers**: Discord events, database changes
- **Manual triggers**: On-demand execution

### 5. Expressions
n8n uses a powerful **expression language** for dynamic values:
```javascript
// Access previous node data
{{ $node["Discord"].json.content }}

// Use JavaScript
{{ new Date().toISOString() }}

// Transform data
{{ $json.message.toLowerCase() }}
```

## Building Workflows Programmatically

n8n workflows are JSON objects that define nodes and connections. Here's the structure:

### Basic Workflow Structure
```json
{
  "name": "Discord Bot Workflow",
  "nodes": [
    {
      "parameters": {},
      "id": "unique-id",
      "name": "Node Name",
      "type": "n8n-nodes-base.discord",
      "typeVersion": 1,
      "position": [250, 300]
    }
  ],
  "connections": {
    "Node Name": {
      "main": [
        [
          {
            "node": "Next Node",
            "type": "main",
            "index": 0
          }
        ]
      ]
    }
  }
}
```

### Example: Discord Message Handler
```json
{
  "name": "Discord Message Handler",
  "nodes": [
    {
      "parameters": {
        "event": "messageCreate",
        "guildId": "={{ $env.DISCORD_GUILD_ID }}"
      },
      "id": "discord-trigger",
      "name": "Discord Trigger",
      "type": "n8n-nodes-base.discordTrigger",
      "typeVersion": 1,
      "position": [250, 300]
    },
    {
      "parameters": {
        "conditions": {
          "string": [
            {
              "value1": "={{ $json.content }}",
              "operation": "startsWith",
              "value2": "!ask"
            }
          ]
        }
      },
      "id": "check-command",
      "name": "Check Command",
      "type": "n8n-nodes-base.if",
      "typeVersion": 1,
      "position": [450, 300]
    },
    {
      "parameters": {
        "model": "gpt-4",
        "messages": {
          "values": [
            {
              "role": "user",
              "content": "={{ $node['Discord Trigger'].json.content.replace('!ask ', '') }}"
            }
          ]
        }
      },
      "id": "openai-node",
      "name": "OpenAI",
      "type": "@n8n/n8n-nodes-langchain.openAi",
      "typeVersion": 1,
      "position": [650, 200]
    },
    {
      "parameters": {
        "resource": "message",
        "operation": "send",
        "guildId": "={{ $node['Discord Trigger'].json.guildId }}",
        "channelId": "={{ $node['Discord Trigger'].json.channelId }}",
        "content": "={{ $json.choices[0].message.content }}"
      },
      "id": "send-response",
      "name": "Send Response",
      "type": "n8n-nodes-base.discord",
      "typeVersion": 1,
      "position": [850, 200]
    }
  ],
  "connections": {
    "Discord Trigger": {
      "main": [[{"node": "Check Command", "type": "main", "index": 0}]]
    },
    "Check Command": {
      "main": [
        [{"node": "OpenAI", "type": "main", "index": 0}],
        []
      ]
    },
    "OpenAI": {
      "main": [[{"node": "Send Response", "type": "main", "index": 0}]]
    }
  }
}
```

## Integrations

### Discord Integration

n8n provides comprehensive Discord nodes:

#### Discord Trigger Node
```json
{
  "parameters": {
    "event": "messageCreate",
    "guildId": "123456789",
    "authentication": "oAuth2"
  },
  "credentials": {
    "discordOAuth2Api": {
      "id": "1",
      "name": "Discord Bot"
    }
  },
  "type": "n8n-nodes-base.discordTrigger"
}
```

Events available:
- `messageCreate`: New messages
- `messageUpdate`: Edited messages
- `messageDelete`: Deleted messages
- `guildMemberAdd`: New members
- `reactionAdd`: Reactions added

#### Discord Action Node
```json
{
  "parameters": {
    "resource": "message",
    "operation": "send",
    "guildId": "={{ $json.guildId }}",
    "channelId": "={{ $json.channelId }}",
    "content": "Response text",
    "embeds": {
      "values": [
        {
          "title": "Embed Title",
          "description": "Rich content",
          "color": 5814783
        }
      ]
    }
  },
  "type": "n8n-nodes-base.discord"
}
```

### PostgreSQL Integration

```json
{
  "parameters": {
    "operation": "executeQuery",
    "query": "INSERT INTO messages (user_id, content, timestamp) VALUES ($1, $2, $3)",
    "additionalFields": {
      "queryParams": "={{ [$json.userId, $json.content, new Date().toISOString()] }}"
    }
  },
  "credentials": {
    "postgres": {
      "id": "2",
      "name": "SuperAgent DB"
    }
  },
  "type": "n8n-nodes-base.postgres"
}
```

Operations:
- `executeQuery`: Run custom SQL
- `insert`: Insert records
- `update`: Update records
- `delete`: Delete records
- `select`: Query records

### Redis Integration

```json
{
  "parameters": {
    "operation": "set",
    "key": "user:{{ $json.userId }}:context",
    "value": "={{ JSON.stringify($json) }}",
    "expire": true,
    "ttl": 3600
  },
  "credentials": {
    "redis": {
      "id": "3",
      "name": "SuperAgent Cache"
    }
  },
  "type": "n8n-nodes-base.redis"
}
```

### LLM Integration

#### OpenAI/GPT
```json
{
  "parameters": {
    "model": "gpt-4",
    "messages": {
      "values": [
        {
          "role": "system",
          "content": "You are a helpful Discord assistant."
        },
        {
          "role": "user",
          "content": "={{ $json.messageContent }}"
        }
      ]
    },
    "options": {
      "temperature": 0.7,
      "maxTokens": 500
    }
  },
  "type": "@n8n/n8n-nodes-langchain.openAi"
}
```

#### Claude Integration
```json
{
  "parameters": {
    "model": "claude-3-opus-20240229",
    "prompt": "={{ $json.prompt }}",
    "maxTokensToSample": 1000
  },
  "credentials": {
    "anthropicApi": {
      "id": "4",
      "name": "Claude API"
    }
  },
  "type": "@n8n/n8n-nodes-langchain.anthropic"
}
```

## Developing Without the UI

### 1. Workflow as Code Structure
Create workflow JSON files in your project:
```
SuperAgent-n8n/
├── workflows/
│   ├── discord-message-handler.json
│   ├── context-manager.json
│   └── agent-orchestrator.json
├── nodes/
│   └── custom-nodes/
├── credentials/
│   └── credentials.encrypted.json
└── docker-compose.yml
```

### 2. Using n8n CLI
```bash
# Import workflow
n8n import:workflow --input=./workflows/discord-message-handler.json

# Export workflow
n8n export:workflow --id=1 --output=./workflows/

# Execute workflow
n8n execute --file=./workflows/discord-message-handler.json
```

### 3. Programmatic Workflow Management
```javascript
// workflow-manager.js
const axios = require('axios');

class WorkflowManager {
  constructor(n8nUrl, apiKey) {
    this.api = axios.create({
      baseURL: `${n8nUrl}/api/v1`,
      headers: { 'X-N8N-API-KEY': apiKey }
    });
  }

  async createWorkflow(workflowData) {
    const response = await this.api.post('/workflows', workflowData);
    return response.data;
  }

  async updateWorkflow(id, workflowData) {
    const response = await this.api.patch(`/workflows/${id}`, workflowData);
    return response.data;
  }

  async activateWorkflow(id) {
    const response = await this.api.patch(`/workflows/${id}`, { active: true });
    return response.data;
  }
}
```

### 4. Environment-based Configuration
```json
{
  "nodes": [
    {
      "parameters": {
        "guildId": "={{ $env.DISCORD_GUILD_ID }}",
        "model": "={{ $env.LLM_MODEL }}",
        "temperature": "={{ $env.LLM_TEMPERATURE }}"
      }
    }
  ]
}
```

### 5. Version Control Best Practices
```yaml
# .gitignore
credentials/
*.decrypted.json
.env

# workflow-config.yml
workflows:
  - name: discord-handler
    file: workflows/discord-message-handler.json
    active: true
    env:
      - DISCORD_GUILD_ID
      - LLM_MODEL
```

## Best Practices for Discord Bots

### 1. Message Handling Pattern
```json
{
  "name": "Discord Message Handler Pattern",
  "nodes": [
    {
      "name": "Discord Trigger",
      "type": "n8n-nodes-base.discordTrigger",
      "parameters": {
        "event": "messageCreate"
      }
    },
    {
      "name": "Filter Bot Messages",
      "type": "n8n-nodes-base.if",
      "parameters": {
        "conditions": {
          "boolean": [
            {
              "value1": "={{ $json.author.bot }}",
              "operation": "equal",
              "value2": false
            }
          ]
        }
      }
    },
    {
      "name": "Rate Limit Check",
      "type": "n8n-nodes-base.redis",
      "parameters": {
        "operation": "get",
        "key": "ratelimit:{{ $json.author.id }}"
      }
    },
    {
      "name": "Process Command",
      "type": "n8n-nodes-base.function",
      "parameters": {
        "functionCode": "const content = $input.item.json.content;\nconst command = content.split(' ')[0];\nconst args = content.split(' ').slice(1);\n\nreturn {\n  command,\n  args,\n  original: $input.item.json\n};"
      }
    }
  ]
}
```

### 2. Context Management
```json
{
  "name": "Context Manager",
  "nodes": [
    {
      "name": "Get User Context",
      "type": "n8n-nodes-base.postgres",
      "parameters": {
        "operation": "executeQuery",
        "query": "SELECT * FROM user_context WHERE user_id = $1 ORDER BY timestamp DESC LIMIT 10",
        "additionalFields": {
          "queryParams": "={{ [$json.userId] }}"
        }
      }
    },
    {
      "name": "Cache Context",
      "type": "n8n-nodes-base.redis",
      "parameters": {
        "operation": "set",
        "key": "context:{{ $json.userId }}",
        "value": "={{ JSON.stringify($json) }}",
        "expire": true,
        "ttl": 3600
      }
    }
  ]
}
```

### 3. Error Handling
```json
{
  "name": "Error Handler",
  "nodes": [
    {
      "name": "Try Block",
      "type": "n8n-nodes-base.errorTrigger"
    },
    {
      "name": "Log Error",
      "type": "n8n-nodes-base.postgres",
      "parameters": {
        "operation": "insert",
        "table": "error_logs",
        "columns": "workflow_id,error_message,stack_trace,timestamp",
        "values": "={{ [$workflow.id, $json.error.message, $json.error.stack, new Date().toISOString()] }}"
      }
    },
    {
      "name": "Notify Admin",
      "type": "n8n-nodes-base.discord",
      "parameters": {
        "resource": "message",
        "operation": "send",
        "channelId": "{{ $env.ADMIN_CHANNEL_ID }}",
        "content": "Error in workflow: {{ $json.error.message }}"
      }
    }
  ]
}
```

### 4. Multi-Agent Orchestration
```json
{
  "name": "Agent Orchestrator",
  "nodes": [
    {
      "name": "Route to Agent",
      "type": "n8n-nodes-base.switch",
      "parameters": {
        "dataPropertyName": "command",
        "values": {
          "string": [
            {
              "name": "research",
              "value": "!research"
            },
            {
              "name": "code",
              "value": "!code"
            },
            {
              "name": "general",
              "value": "!ask"
            }
          ]
        }
      }
    },
    {
      "name": "Research Agent",
      "type": "n8n-nodes-base.httpRequest",
      "parameters": {
        "url": "http://grok-agent:3000/process",
        "method": "POST",
        "body": "={{ $json }}"
      }
    },
    {
      "name": "Code Agent",
      "type": "@n8n/n8n-nodes-langchain.anthropic",
      "parameters": {
        "model": "claude-3-opus-20240229",
        "prompt": "You are a code assistant. {{ $json.query }}"
      }
    }
  ]
}
```

## n8n vs Traditional Coding

### Traditional Approach
```python
# Traditional Discord bot
import discord
import asyncio
from sqlalchemy import create_engine
import redis
import openai

class DiscordBot(discord.Client):
    def __init__(self):
        super().__init__()
        self.db = create_engine('postgresql://...')
        self.redis = redis.Redis()
        self.openai = openai.Client()
        
    async def on_message(self, message):
        if message.author.bot:
            return
            
        # Rate limiting
        if self.redis.get(f"rate:{message.author.id}"):
            return
            
        # Get context
        with self.db.connect() as conn:
            context = conn.execute("SELECT * FROM context WHERE user_id = ?", message.author.id)
            
        # Process with LLM
        response = await self.openai.chat.completions.create(
            model="gpt-4",
            messages=[{"role": "user", "content": message.content}]
        )
        
        # Send response
        await message.channel.send(response.choices[0].message.content)
        
        # Update context
        with self.db.connect() as conn:
            conn.execute("INSERT INTO context VALUES (?, ?, ?)", 
                        message.author.id, message.content, response.choices[0].message.content)

# Requires:
# - Connection management
# - Error handling
# - Rate limiting logic
# - Database transactions
# - Async coordination
```

### n8n Approach
```json
{
  "nodes": [
    {
      "name": "Discord Trigger",
      "type": "n8n-nodes-base.discordTrigger"
    },
    {
      "name": "Rate Limit",
      "type": "n8n-nodes-base.redis"
    },
    {
      "name": "Get Context",
      "type": "n8n-nodes-base.postgres"
    },
    {
      "name": "Process LLM",
      "type": "@n8n/n8n-nodes-langchain.openAi"
    },
    {
      "name": "Send Response",
      "type": "n8n-nodes-base.discord"
    },
    {
      "name": "Update Context",
      "type": "n8n-nodes-base.postgres"
    }
  ]
}
```

### Key Differences

| Aspect | Traditional | n8n |
|--------|-------------|-----|
| **Connection Management** | Manual websocket handling | Built-in resilient connections |
| **Error Handling** | Try-catch blocks everywhere | Visual error branches |
| **Rate Limiting** | Custom implementation | Configurable node settings |
| **Monitoring** | Custom logging | Built-in execution history |
| **Scaling** | Complex async management | Parallel execution nodes |
| **Testing** | Mock everything | Test individual nodes |
| **Deployment** | Multiple services | Single n8n instance |

## SuperAgent-n8n Implementation Guide

### Phase 1: Basic Setup

#### 1. Project Structure
```
SuperAgent-n8n/
├── docker-compose.yml
├── .env
├── workflows/
│   ├── main-discord-handler.json
│   ├── agent-grok4.json
│   ├── agent-claude.json
│   └── agent-gemini.json
├── config/
│   ├── agents.json
│   └── prompts.json
├── data/
│   └── postgres-init.sql
└── docs/
    └── N8N_COMPREHENSIVE_GUIDE.md
```

#### 2. Docker Compose Configuration
```yaml
version: '3.8'

services:
  n8n:
    image: n8nio/n8n
    restart: always
    ports:
      - "5678:5678"
    environment:
      - N8N_BASIC_AUTH_ACTIVE=true
      - N8N_BASIC_AUTH_USER=${N8N_USER}
      - N8N_BASIC_AUTH_PASSWORD=${N8N_PASSWORD}
      - N8N_HOST=${N8N_HOST}
      - N8N_PORT=5678
      - N8N_PROTOCOL=http
      - NODE_ENV=production
      - WEBHOOK_URL=${N8N_WEBHOOK_URL}
      - GENERIC_TIMEZONE=${TIMEZONE}
    volumes:
      - n8n_data:/home/node/.n8n
      - ./workflows:/workflows
      - ./config:/config

  postgres:
    image: postgres:15
    restart: always
    environment:
      POSTGRES_USER: ${POSTGRES_USER}
      POSTGRES_PASSWORD: ${POSTGRES_PASSWORD}
      POSTGRES_DB: superagent
    volumes:
      - postgres_data:/var/lib/postgresql/data
      - ./data/postgres-init.sql:/docker-entrypoint-initdb.d/init.sql

  redis:
    image: redis:7-alpine
    restart: always
    command: redis-server --appendonly yes
    volumes:
      - redis_data:/data

volumes:
  n8n_data:
  postgres_data:
  redis_data:
```

#### 3. Database Schema
```sql
-- data/postgres-init.sql
CREATE TABLE messages (
    id SERIAL PRIMARY KEY,
    guild_id VARCHAR(255) NOT NULL,
    channel_id VARCHAR(255) NOT NULL,
    user_id VARCHAR(255) NOT NULL,
    content TEXT NOT NULL,
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE user_context (
    id SERIAL PRIMARY KEY,
    user_id VARCHAR(255) NOT NULL,
    interaction_type VARCHAR(50),
    input TEXT,
    output TEXT,
    agent_name VARCHAR(50),
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE agent_memory (
    id SERIAL PRIMARY KEY,
    agent_name VARCHAR(50) NOT NULL,
    key VARCHAR(255) NOT NULL,
    value JSONB,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(agent_name, key)
);

CREATE INDEX idx_user_context_user_id ON user_context(user_id);
CREATE INDEX idx_messages_timestamp ON messages(timestamp);
```

### Phase 2: Core Workflows

#### Main Discord Handler
```json
{
  "name": "Main Discord Handler",
  "nodes": [
    {
      "parameters": {
        "event": "messageCreate",
        "guildId": "={{ $env.DISCORD_GUILD_ID }}"
      },
      "name": "Discord Message",
      "type": "n8n-nodes-base.discordTrigger",
      "position": [250, 300]
    },
    {
      "parameters": {
        "conditions": {
          "boolean": [
            {
              "value1": "={{ $json.author.bot }}",
              "operation": "equal",
              "value2": false
            }
          ]
        }
      },
      "name": "Filter Bots",
      "type": "n8n-nodes-base.if",
      "position": [450, 300]
    },
    {
      "parameters": {
        "jsCode": "const content = $input.item.json.content;\nconst mentions = $input.item.json.mentions;\n\n// Check if bot is mentioned or command is used\nconst botMentioned = mentions.some(m => m.id === $env.BOT_USER_ID);\nconst hasCommand = content.match(/^!(ask|research|code|help)/i);\n\nif (!botMentioned && !hasCommand) {\n  return null;\n}\n\n// Extract command and query\nlet command = 'general';\nlet query = content;\n\nif (hasCommand) {\n  const match = content.match(/^!(\\w+)\\s*(.*)/);\n  command = match[1].toLowerCase();\n  query = match[2];\n} else {\n  query = content.replace(/<@!?\\d+>/g, '').trim();\n}\n\nreturn {\n  command,\n  query,\n  user: $input.item.json.author,\n  channel: $input.item.json.channelId,\n  guild: $input.item.json.guildId,\n  originalMessage: $input.item.json\n};"
      },
      "name": "Parse Command",
      "type": "n8n-nodes-base.code",
      "position": [650, 300]
    },
    {
      "parameters": {
        "operation": "insert",
        "table": "messages",
        "columns": "guild_id,channel_id,user_id,content",
        "values": "={{ [$json.guild, $json.channel, $json.user.id, $json.originalMessage.content] }}"
      },
      "name": "Log Message",
      "type": "n8n-nodes-base.postgres",
      "position": [850, 400]
    },
    {
      "parameters": {
        "dataPropertyName": "command",
        "values": {
          "string": [
            {"name": "research", "value": "research"},
            {"name": "code", "value": "code"},
            {"name": "general", "value": "ask"},
            {"name": "help", "value": "help"}
          ]
        }
      },
      "name": "Route Command",
      "type": "n8n-nodes-base.switch",
      "position": [850, 300]
    }
  ]
}
```

#### Agent Workflow Template
```json
{
  "name": "Grok4 Research Agent",
  "nodes": [
    {
      "parameters": {
        "operation": "executeQuery",
        "query": "SELECT * FROM user_context WHERE user_id = $1 ORDER BY timestamp DESC LIMIT 10",
        "additionalFields": {
          "queryParams": "={{ [$json.user.id] }}"
        }
      },
      "name": "Get Context",
      "type": "n8n-nodes-base.postgres",
      "position": [250, 300]
    },
    {
      "parameters": {
        "jsCode": "const context = $input.item.json;\nconst systemPrompt = `You are Grok4, a research-focused AI assistant. You provide detailed, analytical responses with current information.`;\n\nconst messages = [\n  { role: 'system', content: systemPrompt }\n];\n\n// Add context from previous interactions\nif (context.length > 0) {\n  context.forEach(ctx => {\n    messages.push({ role: 'user', content: ctx.input });\n    messages.push({ role: 'assistant', content: ctx.output });\n  });\n}\n\n// Add current query\nmessages.push({ role: 'user', content: $node['Main Discord Handler'].json.query });\n\nreturn { messages };"
      },
      "name": "Build Prompt",
      "type": "n8n-nodes-base.code",
      "position": [450, 300]
    },
    {
      "parameters": {
        "url": "https://api.x.ai/v1/chat/completions",
        "authentication": "genericCredentialType",
        "genericAuthType": "httpHeaderAuth",
        "sendHeaders": true,
        "headerParameters": {
          "parameters": [
            {
              "name": "Authorization",
              "value": "Bearer {{ $env.XAI_API_KEY }}"
            }
          ]
        },
        "sendBody": true,
        "bodyParameters": {
          "parameters": [
            {
              "name": "model",
              "value": "grok-beta"
            },
            {
              "name": "messages",
              "value": "={{ $json.messages }}"
            },
            {
              "name": "temperature",
              "value": "0.7"
            }
          ]
        }
      },
      "name": "Call Grok API",
      "type": "n8n-nodes-base.httpRequest",
      "position": [650, 300]
    },
    {
      "parameters": {
        "resource": "message",
        "operation": "send",
        "guildId": "={{ $node['Main Discord Handler'].json.guild }}",
        "channelId": "={{ $node['Main Discord Handler'].json.channel }}",
        "content": "={{ $json.choices[0].message.content }}"
      },
      "name": "Send Response",
      "type": "n8n-nodes-base.discord",
      "position": [850, 300]
    },
    {
      "parameters": {
        "operation": "insert",
        "table": "user_context",
        "columns": "user_id,interaction_type,input,output,agent_name",
        "values": "={{ [$node['Main Discord Handler'].json.user.id, 'research', $node['Main Discord Handler'].json.query, $json.choices[0].message.content, 'grok4'] }}"
      },
      "name": "Save Context",
      "type": "n8n-nodes-base.postgres",
      "position": [850, 400]
    }
  ]
}
```

### Phase 3: Advanced Features

#### 1. Memory Management Workflow
```json
{
  "name": "Memory Management",
  "nodes": [
    {
      "parameters": {
        "operation": "get",
        "key": "memory:{{ $json.userId }}:{{ $json.topic }}"
      },
      "name": "Check Cache",
      "type": "n8n-nodes-base.redis"
    },
    {
      "parameters": {
        "conditions": {
          "boolean": [
            {
              "value1": "={{ $json.exists }}",
              "operation": "equal",
              "value2": false
            }
          ]
        }
      },
      "name": "Cache Miss?",
      "type": "n8n-nodes-base.if"
    },
    {
      "parameters": {
        "operation": "executeQuery",
        "query": "SELECT value FROM agent_memory WHERE agent_name = $1 AND key = $2",
        "additionalFields": {
          "queryParams": "={{ [$json.agent, $json.key] }}"
        }
      },
      "name": "Load from DB",
      "type": "n8n-nodes-base.postgres"
    },
    {
      "parameters": {
        "operation": "set",
        "key": "memory:{{ $json.userId }}:{{ $json.topic }}",
        "value": "={{ $json.value }}",
        "expire": true,
        "ttl": 3600
      },
      "name": "Update Cache",
      "type": "n8n-nodes-base.redis"
    }
  ]
}
```

#### 2. Multi-Agent Coordination
```json
{
  "name": "Multi-Agent Coordinator",
  "nodes": [
    {
      "parameters": {
        "jsCode": "// Analyze query to determine best agent\nconst query = $json.query.toLowerCase();\nlet agents = [];\n\nif (query.includes('research') || query.includes('analyze') || query.includes('explain')) {\n  agents.push('grok4');\n}\n\nif (query.includes('code') || query.includes('debug') || query.includes('implement')) {\n  agents.push('claude');\n}\n\nif (query.includes('creative') || query.includes('brainstorm') || query.includes('design')) {\n  agents.push('gemini');\n}\n\n// Default to general agent\nif (agents.length === 0) {\n  agents.push('grok4');\n}\n\nreturn { selectedAgents: agents, query: $json };"
      },
      "name": "Agent Selection",
      "type": "n8n-nodes-base.code"
    },
    {
      "parameters": {
        "batchSize": 1
      },
      "name": "Split by Agent",
      "type": "n8n-nodes-base.splitInBatches"
    },
    {
      "parameters": {
        "mode": "combine",
        "combinationMode": "multiplex"
      },
      "name": "Combine Results",
      "type": "n8n-nodes-base.merge"
    }
  ]
}
```

### Phase 4: Deployment and Monitoring

#### 1. Automated Workflow Deployment
```javascript
// deploy-workflows.js
const fs = require('fs');
const path = require('path');
const axios = require('axios');

async function deployWorkflows() {
  const workflowDir = './workflows';
  const files = fs.readdirSync(workflowDir);
  
  for (const file of files) {
    if (file.endsWith('.json')) {
      const workflow = JSON.parse(
        fs.readFileSync(path.join(workflowDir, file), 'utf8')
      );
      
      // Add environment-specific settings
      workflow.settings = {
        errorWorkflow: "error-handler",
        timezone: process.env.TIMEZONE,
        saveExecutionProgress: true,
        saveManualExecutions: true
      };
      
      // Deploy to n8n
      await axios.post(
        `${process.env.N8N_URL}/api/v1/workflows`,
        workflow,
        {
          headers: {
            'X-N8N-API-KEY': process.env.N8N_API_KEY
          }
        }
      );
      
      console.log(`Deployed: ${workflow.name}`);
    }
  }
}

deployWorkflows();
```

#### 2. Monitoring Dashboard Workflow
```json
{
  "name": "System Monitor",
  "nodes": [
    {
      "parameters": {
        "rule": {
          "interval": [
            {
              "field": "minutes",
              "minutesInterval": 5
            }
          ]
        }
      },
      "name": "Every 5 Minutes",
      "type": "n8n-nodes-base.scheduleTrigger"
    },
    {
      "parameters": {
        "operation": "executeQuery",
        "query": "SELECT COUNT(*) as message_count, COUNT(DISTINCT user_id) as unique_users FROM messages WHERE timestamp > NOW() - INTERVAL '5 minutes'"
      },
      "name": "Get Metrics",
      "type": "n8n-nodes-base.postgres"
    },
    {
      "parameters": {
        "content": "**System Status Update**\nMessages: {{ $json.message_count }}\nActive Users: {{ $json.unique_users }}\nTimestamp: {{ new Date().toISOString() }}"
      },
      "name": "Format Report",
      "type": "n8n-nodes-base.discord"
    }
  ]
}
```

### Phase 5: Testing and Validation

#### Test Workflow Template
```json
{
  "name": "Test Suite",
  "nodes": [
    {
      "parameters": {
        "jsCode": "// Test data\nreturn [\n  { test: 'command_parsing', input: '!research AI trends', expected: 'research' },\n  { test: 'mention_handling', input: '<@BOT_ID> what is n8n?', expected: 'general' },\n  { test: 'context_retrieval', input: 'continue our discussion', expected: 'context_loaded' }\n];"
      },
      "name": "Test Cases",
      "type": "n8n-nodes-base.code"
    },
    {
      "parameters": {
        "conditions": {
          "string": [
            {
              "value1": "={{ $json.result }}",
              "operation": "equal",
              "value2": "={{ $json.expected }}"
            }
          ]
        }
      },
      "name": "Validate Result",
      "type": "n8n-nodes-base.if"
    }
  ]
}
```

## Conclusion

n8n provides a powerful, visual approach to building Discord bots that:
- Simplifies complex integrations
- Provides built-in error handling and monitoring
- Enables rapid development and iteration
- Scales naturally with workflow parallelization
- Maintains code as configuration (JSON workflows)

For SuperAgent-n8n, this means:
1. **Faster Development**: Visual workflow design speeds up implementation
2. **Better Reliability**: Built-in connection management and error handling
3. **Easier Maintenance**: Visual debugging and execution history
4. **Flexible Architecture**: Easy to add new agents and capabilities
5. **Production Ready**: Built-in monitoring, logging, and scalability

The transition from MCP to n8n represents a shift from low-level protocol management to high-level workflow orchestration, allowing you to focus on bot logic rather than infrastructure concerns.