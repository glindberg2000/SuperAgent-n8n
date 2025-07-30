#!/usr/bin/env python3
"""
BotForge Discord Bot - Multi-Bot Support
=========================================

This is the main Discord bot that connects to Discord and forwards messages
to the API server for processing by different AI models.
"""

import os
import asyncio
import logging
import aiohttp
import discord
from discord.ext import commands
import yaml
import json
from typing import Dict, Any, Optional

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('/app/logs/discord_bot.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class BotForgeBot(commands.Bot):
    """Enhanced Discord bot with multi-bot configuration support"""
    
    def __init__(self, bot_config: Dict[str, Any], api_server_url: str):
        self.bot_config = bot_config
        self.api_server_url = api_server_url
        self.bot_name = bot_config['name']
        
        # Configure intents
        intents = discord.Intents.default()
        intents.message_content = True
        intents.guilds = True
        intents.guild_messages = True
        intents.dm_messages = True
        
        super().__init__(
            command_prefix=commands.when_mentioned_or('!'),
            intents=intents,
            description=f"{self.bot_name} - AI Assistant"
        )
    
    async def setup_hook(self):
        """Called when the bot is starting up"""
        logger.info(f"🤖 {self.bot_name} is starting up...")
        await self.tree.sync()
        logger.info(f"✅ {self.bot_name} commands synced")
    
    async def on_ready(self):
        """Called when bot is ready"""
        logger.info(f"🚀 {self.bot_name} is ready!")
        logger.info(f"Bot user: {self.user}")
        logger.info(f"Bot ID: {self.user.id}")
        logger.info(f"Guilds: {len(self.guilds)}")
        
        # Set status
        activity = discord.Activity(
            type=discord.ActivityType.listening,
            name="@mentions and trigger words"
        )
        await self.change_presence(activity=activity, status=discord.Status.online)
    
    async def on_message(self, message):
        """Handle incoming messages"""
        # Ignore messages from bots (including ourselves)
        if message.author.bot:
            return
        
        # Check if bot was mentioned or trigger words used
        should_respond = False
        
        # Check for mentions
        if self.user in message.mentions:
            should_respond = True
            logger.info(f"📩 {self.bot_name} mentioned by {message.author}")
        
        # Check for trigger words
        if not should_respond:
            trigger_words = self.bot_config.get('trigger_words', [])
            message_lower = message.content.lower()
            
            for trigger in trigger_words:
                if trigger.lower() in message_lower:
                    should_respond = True
                    logger.info(f"🎯 Trigger word '{trigger}' detected by {self.bot_name}")
                    break
        
        if should_respond:
            await self.process_message(message)
        
        # Process commands
        await self.process_commands(message)
    
    async def process_message(self, message):
        """Process and respond to a message"""
        try:
            # Show typing indicator
            async with message.channel.typing():
                # Prepare webhook data
                webhook_data = {
                    "bot_name": self.bot_name,
                    "bot_config": self.bot_config,
                    "channel_id": str(message.channel.id),
                    "channel_name": getattr(message.channel, 'name', 'DM'),
                    "guild_id": str(message.guild.id) if message.guild else None,
                    "guild_name": message.guild.name if message.guild else None,
                    "user_id": str(message.author.id),
                    "username": message.author.display_name,
                    "message_content": message.content,
                    "message_id": str(message.id),
                    "timestamp": message.created_at.isoformat()
                }
                
                # Add response delay if configured
                response_delay = self.bot_config.get('response_delay', 0)
                if response_delay > 0:
                    await asyncio.sleep(response_delay)
                
                # Send to API server
                timeout = aiohttp.ClientTimeout(total=30)
                async with aiohttp.ClientSession(timeout=timeout) as session:
                    async with session.post(
                        f"{self.api_server_url}/process_discord_message",
                        json=webhook_data,
                        headers={'Content-Type': 'application/json'}
                    ) as response:
                        
                        if response.status == 200:
                            result = await response.json()
                            ai_response = result.get('response', 'Sorry, I encountered an error.')
                            
                            # Split long messages if needed
                            if len(ai_response) > 2000:
                                chunks = [ai_response[i:i+1900] for i in range(0, len(ai_response), 1900)]
                                for i, chunk in enumerate(chunks):
                                    if i > 0:
                                        chunk = f"(continued...)\n{chunk}"
                                    await message.channel.send(chunk)
                            else:
                                await message.channel.send(ai_response)
                            
                            logger.info(f"✅ {self.bot_name} responded successfully")
                        else:
                            error_text = await response.text()
                            logger.error(f"❌ API server error {response.status}: {error_text}")
                            await message.channel.send("Sorry, I'm having trouble processing your request right now.")
        
        except asyncio.TimeoutError:
            logger.error(f"⏰ Timeout waiting for API server response")
            await message.channel.send("Sorry, that took too long to process. Please try again.")
        except Exception as e:
            logger.error(f"💥 Error processing message: {e}")
            await message.channel.send("Sorry, I encountered an unexpected error.")

def load_bot_config(bot_id: str) -> Optional[Dict[str, Any]]:
    """Load bot configuration from YAML file"""
    try:
        with open('/app/config/bots.yaml', 'r') as f:
            config = yaml.safe_load(f)
            return config['bots'].get(bot_id)
    except Exception as e:
        logger.error(f"Failed to load bot config: {e}")
        return None

async def main():
    """Main bot runner"""
    # Get configuration from environment
    discord_token = os.getenv('DISCORD_TOKEN')
    bot_name = os.getenv('BOT_NAME', 'unknown')
    api_server_url = os.getenv('API_SERVER_URL', 'http://api-server:5001')
    
    if not discord_token:
        logger.error("❌ DISCORD_TOKEN not provided")
        return
    
    # Load bot configuration
    bot_config = load_bot_config(bot_name.lower())
    if not bot_config:
        logger.error(f"❌ No configuration found for bot: {bot_name}")
        # List available configs for debugging
        try:
            with open('/app/config/bots.yaml', 'r') as f:
                config = yaml.safe_load(f)
                logger.error(f"Available bot configs: {list(config.get('bots', {}).keys())}")
        except Exception as e:
            logger.error(f"Failed to read config file: {e}")
        return
    
    if not bot_config.get('enabled', False):
        logger.info(f"🚫 Bot {bot_name} is disabled in configuration")
        return
    
    # Create and run bot
    bot = BotForgeBot(bot_config, api_server_url)
    
    try:
        await bot.start(discord_token)
    except Exception as e:
        logger.error(f"💥 Bot failed to start: {e}")
        raise

if __name__ == "__main__":
    asyncio.run(main())