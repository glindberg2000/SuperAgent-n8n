# API Reference

**Python API server endpoints and data structures for SuperAgent n8n Discord bot.**

## Base URL
```
http://localhost:5001
```

## Endpoints

### Health Check

**GET** `/health`

Returns server health status and database connectivity.

**Response**:
```json
{
  "status": "healthy",
  "database": "connected", 
  "timestamp": "2025-07-29T17:00:00.000000"
}
```

**Error Response**:
```json
{
  "status": "unhealthy",
  "error": "could not connect to database"
}
```

### Process Discord Message

**POST** `/process_discord_message`

Main endpoint for processing Discord messages with AI and memory.

**Request Body**:
```json
{
  "body": {
    "id": "1399905493182451743",
    "content": "<@1396750004588253205> hello there!",
    "channel_id": "1398000953512296549", 
    "guild_id": "1395578178973597799",
    "reply_to_message_id": null,
    "author": {
      "id": "392808447734972419",
      "username": ".cryptoplato",
      "bot": false
    },
    "mentions": [
      {
        "id": "1396750004588253205",
        "username": "Grok4"
      }
    ]
  }
}
```

**Response**:
```json
{
  "success": true,
  "bot_message_id": "1399905756789123456",
  "conversation_length": 5,
  "is_reply": false,
  "processed_at": "2025-07-29T17:00:00.000000"
}
```

**Error Response**:
```json
{
  "success": false,
  "error": "Missing required fields: user_id"
}
```

## Data Structures

### Discord Message Object
```json
{
  "id": "string",           // Discord message ID
  "content": "string",      // Message content with mentions
  "channel_id": "string",   // Discord channel ID
  "guild_id": "string",     // Discord server ID
  "reply_to_message_id": "string|null", // ID of message being replied to
  "author": {
    "id": "string",         // Discord user ID
    "username": "string",   // Discord username
    "bot": "boolean"        // Whether author is a bot
  },
  "mentions": [
    {
      "id": "string",       // Mentioned user ID
      "username": "string"  // Mentioned username
    }
  ]
}
```

### Processing Response Object
```json
{
  "success": "boolean",            // Whether processing succeeded
  "bot_message_id": "string",      // Discord ID of bot's response message
  "conversation_length": "number", // Number of messages in conversation context
  "is_reply": "boolean",          // Whether this was a reply to another message
  "processed_at": "string",       // ISO timestamp of processing
  "error": "string"               // Error message if success=false
}
```

## Internal Functions

### Database Operations

#### `ensure_user_exists(user_id, username)`
Creates or updates user record in `discord_users` table.

**Parameters**:
- `user_id` (str): Discord user ID
- `username` (str): Discord username

**Returns**: None

#### `store_user_message(message_id, user_id, content, metadata)`
Stores user message in `messages` table.

**Parameters**:
- `message_id` (str): Discord message ID
- `user_id` (str): Discord user ID  
- `content` (str): Cleaned message content
- `metadata` (dict): Channel ID, reply info, original content

**Returns**: None

#### `get_conversation_history(user_id, channel_id, limit=15)`
Retrieves recent conversation history for context building.

**Parameters**:
- `user_id` (str): Discord user ID
- `channel_id` (str): Discord channel ID
- `limit` (int): Maximum messages to retrieve

**Returns**: List of message dictionaries

#### `store_bot_response(user_id, content, metadata)`
Stores bot response in `messages` table for future context.

**Parameters**:
- `user_id` (str): Discord user ID
- `content` (str): Bot response content
- `metadata` (dict): Channel ID, model info, conversation length

**Returns**: None

### AI Integration

#### `call_grok4(messages)`
Makes API call to Grok4 with conversation context.

**Parameters**:
- `messages` (list): Conversation messages in OpenAI format

**Returns**: Grok4 API response object

**Example**:
```python
messages = [
  {
    "role": "system",
    "content": "You are Grok4Agent, a helpful Discord bot..."
  },
  {
    "role": "user", 
    "content": "Hello there!"
  }
]
response = call_grok4(messages)
```

### Discord Integration

#### `send_discord_message(channel_id, content, reply_to_message_id=None)`
Sends message to Discord channel via API.

**Parameters**:
- `channel_id` (str): Discord channel ID
- `content` (str): Message content to send
- `reply_to_message_id` (str, optional): ID of message to reply to

**Returns**: Discord API response object

## Error Handling

### Common Error Types

**ValidationError**: Missing required fields
```json
{
  "success": false,
  "error": "Missing required fields: message_id=None, user_id=None"
}
```

**DatabaseError**: Database connection or query issues
```json
{
  "success": false,
  "error": "could not translate host name \"postgres\" to address"
}
``` 

**APITimeoutError**: Grok4 API timeout (automatically handled)
- Returns fallback response: "I'm experiencing a brief connection delay..."
- Does not return error to client

**DiscordAPIError**: Discord API issues
```json
{
  "success": false,
  "error": "Discord API error: 403 - Missing Permissions"
}
```

### Fallback Behavior

1. **Grok4 Timeout**: Returns friendly fallback message
2. **Database Error**: Returns error but doesn't crash
3. **Discord API Error**: Logs error, returns failure response
4. **Invalid Data**: Validates and returns descriptive error

## Rate Limits

### External APIs
- **Grok4 API**: Subject to x.ai rate limits
- **Discord API**: 50 requests per second per bot

### Internal Limits
- **No artificial rate limiting**: Relies on external API limits
- **Database**: No query limits (PostgreSQL scales well)
- **Memory**: Conversation history limited to prevent token overflow

## Authentication

### API Security
- **No authentication required**: Internal service
- **Network isolation**: Not exposed externally
- **Environment variables**: All secrets via environment

### External Service Authentication
- **Discord**: Bot token in Authorization header
- **Grok4**: API key in Authorization header
- **Database**: Username/password authentication

## Development

### Testing Endpoints

**Health Check**:
```bash
curl http://localhost:5001/health
```

**Process Message** (with test data):
```bash
curl -X POST http://localhost:5001/process_discord_message \
  -H "Content-Type: application/json" \
  -d @test_message.json
```

### Debugging

**Enable Debug Mode**:
```python
app.run(host='0.0.0.0', port=5001, debug=True)
```

**Check Logs**:
- Console output shows all processing steps
- Database operations logged with queries
- API calls logged with response times

### Environment Variables

Required:
```bash
XAI_API_KEY=your_grok4_api_key
DISCORD_TOKEN_GROK4=your_discord_bot_token
POSTGRES_HOST=localhost
POSTGRES_PORT=5436
POSTGRES_DB=superagent
POSTGRES_USER=superagent
POSTGRES_PASSWORD=superagent-db-2025
```

Optional:
```bash
PORT=5001                    # API server port
LOG_LEVEL=INFO              # Logging level
DEBUG=False                 # Debug mode
```

This API provides the core functionality for Discord message processing with AI and memory capabilities. 🚀