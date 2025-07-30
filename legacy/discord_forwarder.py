#!/usr/bin/env python3
"""
Discord to n8n Forwarder
Forwards Discord messages to n8n webhook for processing
"""

import discord
import aiohttp
import asyncio
import os
import json
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Configuration
DISCORD_TOKEN = os.getenv('DISCORD_TOKEN_GROK4')
N8N_WEBHOOK_URL = "http://localhost:5678/webhook/grok4-python-api"  # Simple n8n → Python API architecture
BOT_ID = "1396750004588253205"  # Grok4 bot ID

# Discord intents
intents = discord.Intents.default()
intents.message_content = True
intents.messages = True

class DiscordForwarder(discord.Client):
    def __init__(self):
        super().__init__(intents=intents)
        
    async def on_ready(self):
        print(f'Logged in as {self.user} (ID: {self.user.id})')
        print(f'Forwarding messages to: {N8N_WEBHOOK_URL}')
        print('------')
    
    async def on_message(self, message):
        # Debug: log all messages
        print(f"[DEBUG] Saw message from {message.author} in #{message.channel}: {message.content[:50]}...")
        
        # Don't forward our own messages
        if message.author.id == self.user.id:
            print(f"[DEBUG] Ignoring own message")
            return
        
        # Check if bot is mentioned or message contains "grok"
        bot_mentioned = any(mention.id == self.user.id for mention in message.mentions)
        contains_grok = 'grok' in message.content.lower()
        
        # Also check for role mentions or direct bot mentions in content
        bot_id_in_content = str(self.user.id) in message.content
        
        # Check for role mentions (common pattern: <@&ROLE_ID>)
        role_mentioned = bool(message.role_mentions) or '<@&' in message.content
        
        print(f"[DEBUG] Bot mentioned: {bot_mentioned}, Contains grok: {contains_grok}, Bot ID in content: {bot_id_in_content}, Role mentioned: {role_mentioned}")
        
        if not (bot_mentioned or contains_grok or bot_id_in_content or role_mentioned):
            print(f"[DEBUG] Message doesn't match criteria - ignoring")
            return
        
        # Prepare webhook data
        webhook_data = {
            "id": str(message.id),
            "content": message.content,
            "channel_id": str(message.channel.id),
            "guild_id": str(message.guild.id) if message.guild else None,
            "reply_to_message_id": str(message.reference.message_id) if message.reference else None,
            "author": {
                "id": str(message.author.id),
                "username": message.author.name,
                "bot": message.author.bot
            },
            "mentions": [
                {
                    "id": str(mention.id),
                    "username": mention.name
                }
                for mention in message.mentions
            ]
        }
        
        print(f"Forwarding message from {message.author}: {message.content[:50]}...")
        print(f"Debug - Message data: {json.dumps(webhook_data, indent=2)}")
        
        # Forward to n8n
        async with aiohttp.ClientSession() as session:
            try:
                async with session.post(N8N_WEBHOOK_URL, json=webhook_data) as response:
                    if response.status == 200:
                        print(f"✅ Message forwarded successfully")
                    else:
                        print(f"❌ Failed to forward: {response.status}")
                        text = await response.text()
                        print(f"Response: {text}")
            except Exception as e:
                print(f"❌ Error forwarding message: {e}")

# Run the bot
if __name__ == "__main__":
    client = DiscordForwarder()
    client.run(DISCORD_TOKEN)