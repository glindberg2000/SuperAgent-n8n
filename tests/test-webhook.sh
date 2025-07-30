#!/bin/bash

# Test n8n Discord webhook

echo "Testing n8n Discord webhook..."

# Test URL (use while in editor, before activation)
echo "1. Testing with test URL..."
curl -X POST http://localhost:5678/webhook-test/discord-test \
  -H "Content-Type: application/json" \
  -d '{
    "content": "Hello from test!",
    "author": {
      "id": "123456789",
      "username": "TestUser",
      "bot": false
    },
    "channel_id": "987654321",
    "id": "msg123"
  }'

echo -e "\n\n2. Testing with production URL (after activation)..."
curl -X POST http://localhost:5678/webhook/discord-test \
  -H "Content-Type: application/json" \
  -d '{
    "content": "Hello from production!",
    "author": {
      "id": "123456789",
      "username": "TestUser",
      "bot": false
    },
    "channel_id": "987654321",
    "id": "msg456"
  }'