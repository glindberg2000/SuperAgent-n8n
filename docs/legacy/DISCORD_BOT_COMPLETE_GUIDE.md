# Complete Discord Bot Setup Guide

## Architecture Overview

```
┌─────────────────┐     ┌──────────────────┐     ┌─────────────────┐
│  Discord Server │     │  Python Bot      │     │  n8n Workflow   │
│                 │     │  (Forwarder)     │     │  (localhost)    │
└────────┬────────┘     └────────┬─────────┘     └────────┬────────┘
         │                       │                          │
         │ WebSocket            │ HTTP POST                │
         │ (Discord Gateway)    │ localhost:5678          │
         │                      │                          │
    [Message Event]────────────►│                          │
         │                      │                          │
         │                      ├─────────────────────────►│
         │                      │  Forward Message         │
         │                      │                          │
         │                      │                          ├─► Grok4 API
         │                      │                          │
         │                      │                          │◄─ Response
         │                      │                          │
         │◄─────────────────────┼──────────────────────────┤
      [Send Response]           │  Discord API Call        │
                               │                          │
```

## Why This Architecture?

1. **No Public URL/Ngrok Needed**: 
   - Python bot connects TO Discord (outbound websocket)
   - Python bot sends TO n8n locally (localhost HTTP)
   - n8n sends TO Discord API (outbound HTTPS)
   - All connections are outbound - no incoming firewall rules needed!

2. **Security Benefits**:
   - n8n webhook stays on localhost (not exposed to internet)
   - Discord token only in Python bot
   - API keys only in n8n environment

## Complete Setup Steps

### 1. Ensure n8n Stack is Running
```bash
# Check status
docker-compose -f docker/docker-compose.yml --env-file .env ps

# If not running, start it
docker-compose -f docker/docker-compose.yml --env-file .env up -d
```

### 2. Import and Activate n8n Workflow
1. Open n8n: http://localhost:5678
2. Login: admin / superagent-n8n-2025
3. Import workflow: `workflows/discord-grok4-final.json`
4. **IMPORTANT**: Click the toggle to ACTIVATE the workflow
5. Note the webhook URL: `http://localhost:5678/webhook/discord-grok4-final`

### 3. Run the Discord Bot
```bash
# Activate virtual environment
source discord-bot-venv/bin/activate

# Run the bot
python discord_forwarder.py
```

You should see:
```
Logged in as Grok4Agent (ID: 1396750004588253205)
Forwarding messages to: http://localhost:5678/webhook/discord-grok4-final
------
```

### 4. Test in Discord
Send a message in any channel the bot can see:
- "@Grok4Agent hello!"
- "Hey grok, what's up?"
- Any message mentioning the bot or containing "grok"

### 5. Monitor the Flow

**Terminal 1 - Bot Logs:**
```
Forwarding message from Greg: @Grok4Agent hello!...
✅ Message forwarded successfully
```

**Terminal 2 - n8n Logs:**
```bash
docker-compose -f docker/docker-compose.yml logs -f n8n
```

**n8n Interface:**
- Go to Executions tab
- See each message flow through the workflow
- Check for any errors

## Troubleshooting

### Bot not responding?
1. Check bot is running (terminal shows "Logged in as...")
2. Check n8n workflow is ACTIVATED (toggle is on)
3. Check webhook URL matches in `discord_forwarder.py`
4. Check bot has permissions in Discord channel

### n8n workflow failing?
1. Check Grok4 API credentials are set
2. Check Discord token environment variable is loaded
3. Look at execution details in n8n interface

### Discord API errors?
- The bot needs these permissions:
  - Read Messages
  - Send Messages
  - Read Message History

## Production Deployment

For production, you would:

1. **Use a Process Manager**:
   ```bash
   # Install PM2
   npm install -g pm2
   
   # Run bot with PM2
   pm2 start discord_forwarder.py --interpreter python3
   ```

2. **Deploy n8n to Cloud**:
   - Deploy Docker stack to cloud server
   - Use proper domain with HTTPS
   - Update webhook URL in Python bot

3. **Add Error Handling**:
   - Retry logic for failed webhooks
   - Reconnection handling
   - Logging to files

## Success Indicators

✅ Python bot shows "Logged in as..."
✅ n8n workflow shows "Active" status
✅ Bot forwards messages (terminal shows "✅ Message forwarded")
✅ n8n Executions show successful runs
✅ Discord receives responses from Grok4

## Architecture Benefits

1. **Simplicity**: No complex networking setup
2. **Security**: Everything runs locally, only outbound connections
3. **Reliability**: n8n handles retries and error recovery
4. **Visibility**: Visual workflow shows exactly what happens
5. **Flexibility**: Easy to add new features in n8n

This approach successfully replaces the complex MCP architecture with a simple, reliable message forwarding system!