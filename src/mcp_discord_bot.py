#!/usr/bin/env python3
"""
MCP-Enabled Discord Bot for BotForge
=====================================

Discord bot that uses MCP (Model Context Protocol) for tool access,
providing standardized interactions with Discord, file systems, databases,
and other services through MCP servers.
"""

import os
import asyncio
import logging
import json
import yaml
from datetime import datetime
from typing import Dict, List, Optional, Any
from pathlib import Path

import discord
from discord.ext import commands

# MCP client
from mcp_client import get_mcp_client, call_mcp_tool

# LLM providers
from llm_providers import LLMProviders

# Vector storage with PostgreSQL
from vector_storage_postgres import PostgreSQLVectorStorage

logger = logging.getLogger(__name__)

class MCPDiscordBot:
    """Discord bot with MCP tool integration"""
    
    def __init__(self, config_path: str = "./config/bots.yaml"):
        self.config_path = config_path
        self.config = None
        self.bots = {}
        self.mcp_client = None
        self.vector_storage = None
        self.llm_providers = None
        
        # Load configuration
        self.load_config()
        
        # Initialize components
        self.llm_providers = LLMProviders()
    
    def load_config(self):
        """Load bot configuration from YAML file"""
        try:
            config_file = Path(self.config_path)
            if not config_file.exists():
                raise FileNotFoundError(f"Configuration file not found: {self.config_path}")
            
            with open(config_file, 'r') as f:
                self.config = yaml.safe_load(f)
            
            logger.info(f"✅ Configuration loaded from {self.config_path}")
            
        except Exception as e:
            logger.error(f"❌ Failed to load configuration: {e}")
            raise
    
    async def initialize(self):
        """Initialize all components"""
        try:
            # Initialize MCP client
            self.mcp_client = await get_mcp_client()
            logger.info("✅ MCP client initialized")
            
            # Initialize vector storage
            self.vector_storage = PostgreSQLVectorStorage()
            await self.vector_storage.initialize()
            logger.info("✅ Vector storage initialized")
            
            logger.info("✅ All components initialized successfully")
            
        except Exception as e:
            logger.error(f"❌ Failed to initialize components: {e}")
            raise
    
    async def create_bot(self, bot_name: str, bot_config: Dict[str, Any]) -> commands.Bot:
        """Create a Discord bot instance with MCP integration"""
        try:
            # Discord bot setup
            intents = discord.Intents.default()
            intents.message_content = True
            intents.members = True
            
            bot = commands.Bot(
                command_prefix=self.config.get('global', {}).get('discord', {}).get('command_prefix', '!'),
                intents=intents
            )
            
            # Store bot configuration
            bot.bot_config = bot_config
            bot.mcp_client = self.mcp_client
            bot.vector_storage = self.vector_storage
            bot.llm_providers = self.llm_providers
            
            # Setup event handlers
            self.setup_bot_events(bot, bot_name, bot_config)
            
            return bot
            
        except Exception as e:
            logger.error(f"Failed to create bot {bot_name}: {e}")
            raise
    
    def setup_bot_events(self, bot: commands.Bot, bot_name: str, bot_config: Dict[str, Any]):
        """Setup Discord bot event handlers"""
        
        @bot.event
        async def on_ready():
            logger.info(f"✅ {bot_name} ({bot.user}) is ready!")
            
            # Set bot status
            activity = discord.Activity(
                type=discord.ActivityType.listening,
                name=f"for {', '.join(bot_config.get('trigger_words', []))}"
            )
            await bot.change_presence(activity=activity)
        
        @bot.event
        async def on_message(message):
            """Handle incoming messages"""
            try:
                # Skip if message is from a bot
                if message.author.bot:
                    return
                
                # Check if bot should respond
                if not await self.should_respond(message, bot_config):
                    return
                
                # Process the message
                await self.process_message(bot, message, bot_name, bot_config)
                
            except Exception as e:
                logger.error(f"Error handling message in {bot_name}: {e}")
                await message.channel.send(f"❌ An error occurred: {str(e)[:100]}...")
        
        @bot.event
        async def on_error(event, *args, **kwargs):
            logger.error(f"Discord error in {bot_name} during {event}: {args}")
    
    async def should_respond(self, message: discord.Message, bot_config: Dict[str, Any]) -> bool:
        """Determine if the bot should respond to a message"""
        try:
            content = message.content.lower()
            trigger_words = bot_config.get('trigger_words', [])
            
            # Check for trigger words
            if any(trigger.lower() in content for trigger in trigger_words):
                return True
            
            # Check for direct mentions
            if message.mentions and any(mention.bot for mention in message.mentions):
                return True
            
            # Check for replies to bot messages
            if message.reference and message.reference.message_id:
                try:
                    referenced_message = await message.channel.fetch_message(message.reference.message_id)
                    if referenced_message.author.bot:
                        return True
                except:
                    pass
            
            return False
            
        except Exception as e:
            logger.error(f"Error checking if should respond: {e}")
            return False
    
    async def process_message(self, bot: commands.Bot, message: discord.Message, 
                            bot_name: str, bot_config: Dict[str, Any]):
        """Process a message and generate a response"""
        try:
            # Show typing indicator
            async with message.channel.typing():
                # Get conversation context
                context = await self.get_conversation_context(message, bot_config)
                
                # Get available MCP tools
                available_tools = self.mcp_client.get_tools_schema() if self.mcp_client else []
                
                # Prepare messages for LLM
                messages = [
                    {
                        "role": "system",
                        "content": self.build_system_prompt(bot_config, available_tools)
                    }
                ]
                
                # Add conversation context
                messages.extend(context)
                
                # Add current message
                messages.append({
                    "role": "user",
                    "content": f"{message.author.display_name}: {message.content}"
                })
                
                # Generate response using LLM
                response = await self.generate_response(
                    messages, bot_config, available_tools
                )
                
                # Send response
                if response:
                    # Split long responses
                    if len(response) > 2000:
                        chunks = [response[i:i+2000] for i in range(0, len(response), 2000)]
                        for chunk in chunks:
                            await message.channel.send(chunk)
                    else:
                        await message.channel.send(response)
                    
                    # Save conversation
                    await self.save_conversation(message, response, bot_name)
                
        except Exception as e:
            logger.error(f"Error processing message: {e}")
            await message.channel.send(f"❌ Sorry, I encountered an error: {str(e)[:100]}...")
    
    def build_system_prompt(self, bot_config: Dict[str, Any], available_tools: List[Dict[str, Any]]) -> str:
        """Build the system prompt for the LLM"""
        personality = bot_config.get('personality', 'You are a helpful AI assistant.')
        
        tools_description = ""
        if available_tools:
            tools_list = [f"- {tool['name']}: {tool['description']}" for tool in available_tools]
            tools_description = f"""

**Available Tools:**
You have access to the following tools through MCP (Model Context Protocol):
{chr(10).join(tools_list)}

Use these tools when appropriate to help users. Call tools by using the function calling capability of the LLM.
"""
        
        return f"""{personality}{tools_description}

**Context:**
- You are {bot_config.get('name', 'Assistant')} in a Discord server
- Current time: {datetime.now().isoformat()}
- You can interact with Discord, read/write files, search databases, and more through available tools
- Be helpful, concise, and engaging in your responses
- If you need to use tools, explain what you're doing briefly"""
    
    async def get_conversation_context(self, message: discord.Message, 
                                     bot_config: Dict[str, Any]) -> List[Dict[str, str]]:
        """Get recent conversation context"""
        try:
            max_context = bot_config.get('max_context_messages', 15)
            context = []
            
            # Get recent messages from the channel
            async for msg in message.channel.history(limit=max_context, before=message):
                # Skip very old messages or messages from other bots
                if msg.author.bot and msg.author != message.guild.me:
                    continue
                
                role = "assistant" if msg.author.bot else "user"
                content = f"{msg.author.display_name}: {msg.content}" if not msg.author.bot else msg.content
                
                context.insert(0, {
                    "role": role,
                    "content": content
                })
            
            return context
            
        except Exception as e:
            logger.error(f"Error getting conversation context: {e}")
            return []
    
    async def generate_response(self, messages: List[Dict[str, str]], 
                              bot_config: Dict[str, Any],
                              available_tools: List[Dict[str, Any]]) -> str:
        """Generate response using LLM with tool calling"""
        try:
            llm_provider = bot_config.get('llm_provider', 'xai')
            llm_model = bot_config.get('llm_model', 'grok-4-latest')
            api_key_env = bot_config.get('api_key_env', 'XAI_API_KEY')
            
            # Get LLM response with tool calling
            response = await self.llm_providers.chat_completion(
                provider=llm_provider,
                model=llm_model,
                messages=messages,
                api_key=os.getenv(api_key_env),
                tools=available_tools,
                tool_choice="auto"
            )
            
            # Handle tool calls
            if response.get('tool_calls'):
                return await self.handle_tool_calls(response, messages, bot_config)
            
            return response.get('content', 'Sorry, I could not generate a response.')
            
        except Exception as e:
            logger.error(f"Error generating response: {e}")
            return f"❌ Error generating response: {str(e)[:100]}..."
    
    async def handle_tool_calls(self, response: Dict[str, Any], 
                              messages: List[Dict[str, str]], 
                              bot_config: Dict[str, Any]) -> str:
        """Handle LLM tool calls through MCP"""
        try:
            tool_calls = response.get('tool_calls', [])
            tool_results = []
            
            for tool_call in tool_calls:
                tool_name = tool_call.get('name')
                tool_args = tool_call.get('arguments', {})
                
                logger.info(f"Calling MCP tool: {tool_name} with args: {tool_args}")
                
                # Call the MCP tool
                result = await call_mcp_tool(tool_name, tool_args)
                tool_results.append({
                    "tool": tool_name,
                    "result": result
                })
            
            # Add tool results to conversation and get final response
            messages.append({
                "role": "assistant",
                "content": response.get('content', ''),
                "tool_calls": tool_calls
            })
            
            for tool_result in tool_results:
                messages.append({
                    "role": "tool",
                    "name": tool_result["tool"],
                    "content": json.dumps(tool_result["result"])
                })
            
            # Get final response from LLM
            final_response = await self.llm_providers.chat_completion(
                provider=bot_config.get('llm_provider', 'xai'),
                model=bot_config.get('llm_model', 'grok-4-latest'),
                messages=messages,
                api_key=os.getenv(bot_config.get('api_key_env', 'XAI_API_KEY'))
            )
            
            return final_response.get('content', 'Tool execution completed.')
            
        except Exception as e:
            logger.error(f"Error handling tool calls: {e}")
            return f"❌ Error executing tools: {str(e)[:100]}..."
    
    async def save_conversation(self, message: discord.Message, response: str, bot_name: str):
        """Save conversation to database via MCP"""
        try:
            if not self.mcp_client:
                return
            
            conversation_data = {
                "channel_id": str(message.channel.id),
                "user_id": str(message.author.id),
                "messages": [
                    {
                        "user_id": str(message.author.id),
                        "content": message.content,
                        "type": "user",
                        "metadata": {"username": message.author.display_name}
                    },
                    {
                        "user_id": "0",  # Bot user
                        "content": response,
                        "type": "assistant",
                        "agent_name": bot_name,
                        "metadata": {"bot_name": bot_name}
                    }
                ],
                "agent_type": bot_name
            }
            
            await call_mcp_tool("save_conversation", conversation_data)
            
        except Exception as e:
            logger.error(f"Error saving conversation: {e}")
    
    async def start_bot(self, bot_name: str, bot_config: Dict[str, Any]):
        """Start a single bot"""
        try:
            if not bot_config.get('enabled', True):
                logger.info(f"Bot {bot_name} is disabled, skipping...")
                return
            
            # Get Discord token
            discord_token_env = bot_config.get('discord_token_env')
            discord_token = os.getenv(discord_token_env)
            
            if not discord_token:
                logger.error(f"Discord token not found for {bot_name} (env: {discord_token_env})")
                return
            
            # Create bot instance
            bot = await self.create_bot(bot_name, bot_config)
            
            # Store bot reference
            self.bots[bot_name] = bot
            
            # Start bot
            logger.info(f"Starting {bot_name}...")
            await bot.start(discord_token)
            
        except Exception as e:
            logger.error(f"Error starting bot {bot_name}: {e}")
    
    async def start_all_bots(self):
        """Start all enabled bots"""
        try:
            # Initialize components first
            await self.initialize()
            
            # Get bot configurations
            bots_config = self.config.get('bots', {})
            
            if not bots_config:
                logger.error("No bots configured")
                return
            
            # Create tasks for all bots
            bot_tasks = []
            for bot_name, bot_config in bots_config.items():
                if bot_config.get('enabled', True):
                    task = asyncio.create_task(self.start_bot(bot_name, bot_config))
                    bot_tasks.append(task)
                    logger.info(f"Created task for {bot_name}")
            
            if not bot_tasks:
                logger.error("No enabled bots found")
                return
            
            # Run all bots concurrently
            logger.info(f"Starting {len(bot_tasks)} bots...")
            await asyncio.gather(*bot_tasks, return_exceptions=True)
            
        except Exception as e:
            logger.error(f"Error starting bots: {e}")
            raise
    
    async def shutdown(self):
        """Shutdown all bots and cleanup"""
        logger.info("Shutting down MCP Discord Bot system...")
        
        # Close all bot connections
        for bot_name, bot in self.bots.items():
            try:
                await bot.close()
                logger.info(f"Bot {bot_name} closed")
            except Exception as e:
                logger.error(f"Error closing bot {bot_name}: {e}")
        
        # Cleanup MCP client
        if self.mcp_client:
            await self.mcp_client.shutdown()
        
        # Cleanup vector storage
        if self.vector_storage:
            await self.vector_storage.close()
        
        logger.info("Shutdown complete")


async def main():
    """Main entry point"""
    # Configure logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler('/app/logs/mcp_discord_bot.log'),
            logging.StreamHandler()
        ]
    )
    logger.info("Starting MCP Discord Bot system...")
    
    # Create and start bot system
    bot_system = MCPDiscordBot()
    
    try:
        await bot_system.start_all_bots()
    except KeyboardInterrupt:
        logger.info("Received shutdown signal...")
    except Exception as e:
        logger.error(f"Fatal error: {e}")
    finally:
        await bot_system.shutdown()


if __name__ == "__main__":
    asyncio.run(main())