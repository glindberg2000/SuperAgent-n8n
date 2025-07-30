#!/bin/bash

# SuperAgent Discord Bot Setup Script

set -e

echo "🤖 Setting up Discord Bot for SuperAgent n8n"
echo "==========================================="

# 1. Create virtual environment
echo "1. Creating Python virtual environment..."
python3 -m venv discord-bot-venv

# 2. Activate venv and install dependencies
echo "2. Installing dependencies..."
source discord-bot-venv/bin/activate
pip install --upgrade pip
pip install -r requirements-discord.txt

# 3. Check environment variables
echo "3. Checking environment variables..."
if [ -f .env ]; then
    if grep -q "DISCORD_TOKEN_GROK4" .env; then
        echo "✅ Discord token found in .env"
    else
        echo "❌ DISCORD_TOKEN_GROK4 not found in .env"
        exit 1
    fi
else
    echo "❌ .env file not found"
    exit 1
fi

# 4. Check n8n is running
echo "4. Checking n8n status..."
if curl -f http://localhost:5678/healthz > /dev/null 2>&1; then
    echo "✅ n8n is running"
else
    echo "❌ n8n is not running. Please start it first with:"
    echo "   docker-compose -f docker/docker-compose.yml --env-file .env up -d"
    exit 1
fi

# 5. Display instructions
echo ""
echo "✅ Setup complete!"
echo ""
echo "📋 Next steps:"
echo "1. Make sure the 'Discord Grok4 Bot - Final' workflow is imported and ACTIVATED in n8n"
echo "2. Run the Discord bot:"
echo "   source discord-bot-venv/bin/activate"
echo "   python discord_forwarder.py"
echo ""
echo "3. Test in Discord:"
echo "   - Send a message mentioning @Grok4Agent"
echo "   - Or send a message with 'grok' in it"
echo ""
echo "📊 Monitor:"
echo "   - n8n interface: http://localhost:5678"
echo "   - n8n logs: docker-compose -f docker/docker-compose.yml logs -f n8n"
echo "   - Bot logs: Will appear in terminal"