#!/usr/bin/env python3
"""
BotForge Discord Bot with MCP Integration
=========================================

This version includes MCP tools for Discord interaction and PostgreSQL memory.
"""

import os
import asyncio
import logging
import aiohttp
import discord
from discord.ext import commands
import yaml
import json
import psycopg2
from psycopg2.extras import RealDictCursor
from typing import Dict, Any, Optional, List
from datetime import datetime
import sys

# Add src to path for imports
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('./logs/discord_bot.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class MCPDiscordBot(commands.Bot):
    """Discord bot with MCP tool integration and memory"""
    
    def __init__(self, bot_config: Dict[str, Any], api_server_url: str):
        self.bot_config = bot_config
        self.api_server_url = api_server_url
        self.bot_name = bot_config['name']
        self.db_config = {
            'host': os.getenv('POSTGRES_HOST', 'localhost'),
            'port': int(os.getenv('POSTGRES_PORT', 5436)),
            'database': os.getenv('POSTGRES_DB', 'superagent'),
            'user': os.getenv('POSTGRES_USER', 'superagent'),
            'password': os.getenv('POSTGRES_PASSWORD', 'superagent-db-2025')
        }
        
        # Configure intents
        intents = discord.Intents.default()
        intents.message_content = True
        intents.guilds = True
        intents.guild_messages = True
        intents.dm_messages = True
        intents.members = True
        
        super().__init__(
            command_prefix=commands.when_mentioned_or('!'),
            intents=intents,
            description=f"{self.bot_name} - AI Assistant with MCP Tools"
        )
        
        # Discord tools available
        self.discord_tools = {
            "list_channels": self.tool_list_channels,
            "get_channel_history": self.tool_get_channel_history,
            "get_server_info": self.tool_get_server_info,
            "get_online_users": self.tool_get_online_users,
            "search_messages": self.tool_search_messages
        }
    
    def get_db_connection(self):
        """Get PostgreSQL database connection"""
        return psycopg2.connect(**self.db_config)
    
    async def store_message(self, message, is_bot=False):
        """Store message in PostgreSQL for memory"""
        try:
            with self.get_db_connection() as conn:
                with conn.cursor() as cur:
                    cur.execute("""
                        INSERT INTO discord_messages 
                        (bot_name, channel_id, guild_id, user_id, username, message_content, message_id, timestamp)
                        VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                    """, (
                        self.bot_name if is_bot else None,
                        str(message.channel.id),
                        str(message.guild.id) if message.guild else None,
                        str(message.author.id) if hasattr(message.author, 'id') else None,
                        message.author.display_name if hasattr(message.author, 'display_name') else str(message.author),
                        message.content,
                        str(message.id) if hasattr(message, 'id') else None,
                        message.created_at if hasattr(message, 'created_at') else datetime.now()
                    ))
                    conn.commit()
        except Exception as e:
            logger.error(f"Failed to store message: {e}")
    
    async def get_conversation_history(self, channel_id: str, limit: int = 30) -> List[Dict]:
        """Get conversation history from PostgreSQL"""
        try:
            with self.get_db_connection() as conn:
                with conn.cursor(cursor_factory=RealDictCursor) as cur:
                    cur.execute("""
                        SELECT message_content, username, timestamp, bot_name
                        FROM discord_messages 
                        WHERE channel_id = %s 
                        ORDER BY timestamp DESC 
                        LIMIT %s
                    """, (channel_id, limit))
                    
                    messages = cur.fetchall()
                    # Convert to format expected by AI
                    formatted_messages = []
                    for msg in reversed(messages):  # Reverse to get chronological order
                        if msg['bot_name']:
                            role = "assistant"
                        else:
                            role = "user"
                        formatted_messages.append({
                            "role": role,
                            "content": f"{msg['username']}: {msg['message_content']}"
                        })
                    return formatted_messages
        except Exception as e:
            logger.error(f"Failed to get history: {e}")
            return []
    
    # Discord MCP Tools
    async def tool_list_channels(self, guild_id: Optional[str] = None) -> Dict:
        """List all channels in the server"""
        try:
            guild = None
            if guild_id:
                guild = self.get_guild(int(guild_id))
            else:
                guild = self.guilds[0] if self.guilds else None
            
            if not guild:
                return {"error": "Server not found"}
            
            channels = []
            for channel in guild.channels:
                channels.append({
                    "id": str(channel.id),
                    "name": channel.name,
                    "type": str(channel.type),
                    "category": channel.category.name if channel.category else None
                })
            
            return {
                "success": True,
                "channels": channels,
                "count": len(channels)
            }
        except Exception as e:
            return {"error": str(e)}
    
    async def tool_get_channel_history(self, channel_id: str, limit: int = 10) -> Dict:
        """Get recent messages from a channel"""
        try:
            channel = self.get_channel(int(channel_id))
            if not channel:
                return {"error": "Channel not found"}
            
            messages = []
            async for message in channel.history(limit=limit):
                messages.append({
                    "id": str(message.id),
                    "author": message.author.display_name,
                    "content": message.content,
                    "timestamp": message.created_at.isoformat()
                })
            
            return {
                "success": True,
                "messages": messages,
                "channel": channel.name
            }
        except Exception as e:
            return {"error": str(e)}
    
    async def tool_get_server_info(self, guild_id: Optional[str] = None) -> Dict:
        """Get information about the Discord server"""
        try:
            guild = None
            if guild_id:
                guild = self.get_guild(int(guild_id))
            else:
                guild = self.guilds[0] if self.guilds else None
            
            if not guild:
                return {"error": "Server not found"}
            
            return {
                "success": True,
                "server": {
                    "name": guild.name,
                    "id": str(guild.id),
                    "member_count": guild.member_count,
                    "channel_count": len(guild.channels),
                    "created_at": guild.created_at.isoformat(),
                    "owner": guild.owner.display_name if guild.owner else "Unknown"
                }
            }
        except Exception as e:
            return {"error": str(e)}
    
    async def tool_get_online_users(self, guild_id: Optional[str] = None) -> Dict:
        """Get list of online users"""
        try:
            guild = None
            if guild_id:
                guild = self.get_guild(int(guild_id))
            else:
                guild = self.guilds[0] if self.guilds else None
            
            if not guild:
                return {"error": "Server not found"}
            
            online_users = []
            for member in guild.members:
                if member.status != discord.Status.offline:
                    online_users.append({
                        "id": str(member.id),
                        "username": member.display_name,
                        "status": str(member.status),
                        "activity": str(member.activity) if member.activity else None
                    })
            
            return {
                "success": True,
                "online_users": online_users,
                "count": len(online_users)
            }
        except Exception as e:
            return {"error": str(e)}
    
    def format_tool_results_fallback(self, tool_results: List[Dict], original_question: str) -> str:
        """Format tool results into a natural response when API fails"""
        response = f"Here's what I found regarding your question:\n\n"
        
        for tool_result in tool_results:
            tool_name = tool_result['tool_name']
            result = tool_result['result']
            
            if tool_name == 'get_server_info' and result.get('success'):
                server = result['server']
                response += f"📊 **Server Information:**\n"
                response += f"• Server: **{server['name']}**\n"
                response += f"• Members: {server['member_count']}\n"
                response += f"• Channels: {server['channel_count']}\n"
                response += f"• Owner: {server['owner']}\n\n"
                
            elif tool_name == 'list_channels' and result.get('success'):
                channels = result['channels']
                response += f"📋 **Available Channels ({result['count']}):**\n"
                for channel in channels[:10]:  # Show first 10
                    response += f"• #{channel['name']} ({channel['type']})\n"
                if len(channels) > 10:
                    response += f"• ... and {len(channels) - 10} more channels\n"
                response += "\n"
                
            elif tool_name == 'get_channel_history' and result.get('success'):
                messages = result['messages']
                response += f"💬 **Recent Messages in #{result['channel']} ({len(messages)} messages):**\n"
                for msg in messages[:5]:  # Show first 5
                    response += f"• {msg['author']}: {msg['content'][:100]}{'...' if len(msg['content']) > 100 else ''}\n"
                response += "\n"
                
            elif tool_name == 'get_online_users' and result.get('success'):
                users = result['online_users']
                response += f"👥 **Online Users ({result['count']}):**\n"
                for user in users[:10]:  # Show first 10
                    status_emoji = "🟢" if user['status'] == 'online' else "🟡" if user['status'] == 'idle' else "🔴"
                    response += f"• {status_emoji} {user['username']}\n"
                response += "\n"
                
            elif tool_name == 'search_messages' and result.get('success'):
                search_results = result['results']
                response += f"🔍 **Search Results for '{result['query']}' ({result['count']} found):**\n"
                for msg in search_results[:5]:  # Show first 5
                    response += f"• **#{msg['channel']}** - {msg['author']}: {msg['content'][:150]}{'...' if len(msg['content']) > 150 else ''}\n"
                response += "\n"
        
        if not any(tr['result'].get('success') for tr in tool_results):
            response = "I encountered some issues retrieving the information you requested. Please try again later."
            
        return response
    
    async def tool_search_messages(self, query: str, channel_id: Optional[str] = None, limit: int = 20) -> Dict:
        """Search for messages containing specific text"""
        try:
            results = []
            channels_to_search = []
            
            if channel_id:
                channel = self.get_channel(int(channel_id))
                if channel:
                    channels_to_search = [channel]
            else:
                # Search all text channels
                for guild in self.guilds:
                    channels_to_search.extend(guild.text_channels)
            
            for channel in channels_to_search[:5]:  # Limit to 5 channels for performance
                try:
                    async for message in channel.history(limit=100):
                        if query.lower() in message.content.lower():
                            results.append({
                                "channel": channel.name,
                                "author": message.author.display_name,
                                "content": message.content,
                                "timestamp": message.created_at.isoformat()
                            })
                            if len(results) >= limit:
                                break
                except:
                    continue  # Skip channels we can't access
                
                if len(results) >= limit:
                    break
            
            return {
                "success": True,
                "results": results,
                "count": len(results),
                "query": query
            }
        except Exception as e:
            return {"error": str(e)}
    
    async def process_with_tools(self, message):
        """Process message with MCP tool support"""
        # Store the incoming message
        await self.store_message(message)
        
        # Get conversation history from database
        history = await self.get_conversation_history(str(message.channel.id))
        
        # Get current server context
        server_info = await self.tool_get_server_info()
        channels_info = await self.tool_list_channels()
        
        # Build enhanced context for AI
        context = f"""
You are {self.bot_name} with access to Discord tools and conversation memory.

**Current Context:**
- Server: {server_info['server']['name'] if server_info.get('success') else 'Unknown'}
- Channel: #{message.channel.name}
- User: {message.author.display_name}

**Available Discord Tools:**
1. list_channels() - List all channels in the server
2. get_channel_history(channel_id, limit) - Get recent messages from a channel
3. get_server_info() - Get server information
4. get_online_users() - Get list of online users
5. search_messages(query, channel_id) - Search for messages

**Recent Conversation History:**
{len(history)} previous messages in this conversation.

When users ask about channels, server info, or browsing, use the appropriate tool and provide specific information.
"""
        
        # Prepare the message for AI with context
        enhanced_message = {
            "role": "user",
            "content": message.content,
            "context": context,
            "tools_available": list(self.discord_tools.keys())
        }
        
        # Send to API server with enhanced context
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
            "timestamp": message.created_at.isoformat(),
            "conversation_history": history,
            "enhanced_context": context,
            "tools_available": list(self.discord_tools.keys())
        }
        
        # Get AI response
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
                    
                    # Check if AI requested tool usage
                    if 'tool_calls' in result:
                        # Execute all tool calls and collect results
                        tool_results = []
                        for tool_call in result['tool_calls']:
                            tool_name = tool_call.get('tool')
                            tool_args = tool_call.get('arguments', {})
                            
                            # Parse arguments if they're a JSON string
                            if isinstance(tool_args, str):
                                try:
                                    tool_args = json.loads(tool_args)
                                except json.JSONDecodeError:
                                    logger.error(f"Failed to parse tool arguments: {tool_args}")
                                    tool_args = {}
                            
                            if tool_name in self.discord_tools:
                                logger.info(f"🔧 Calling tool {tool_name} with args: {tool_args}")
                                tool_result = await self.discord_tools[tool_name](**tool_args)
                                tool_results.append({
                                    'tool_name': tool_name,
                                    'result': tool_result
                                })
                        
                        # If tools were called, send results back to LLM for final response
                        if tool_results:
                            follow_up_data = webhook_data.copy()
                            follow_up_data.update({
                                'message_content': f"Based on the tool results, please provide a natural response to the user's question: {message.content}",
                                'tool_results': tool_results,
                                'follow_up_request': True
                            })
                            
                            # Get final LLM response with tool results
                            async with session.post(
                                f"{self.api_server_url}/process_discord_message",
                                json=follow_up_data,
                                headers={'Content-Type': 'application/json'}
                            ) as follow_up_response:
                                if follow_up_response.status == 200:
                                    follow_up_result = await follow_up_response.json()
                                    ai_response = follow_up_result.get('response', ai_response)
                                else:
                                    # Fallback: Format tool results manually if API fails
                                    logger.warning(f"Follow-up API failed, formatting results manually")
                                    formatted_results = self.format_tool_results_fallback(tool_results, message.content)
                                    ai_response = formatted_results
                    
                    # Clean up response and check for empty content
                    if not ai_response or not ai_response.strip():
                        ai_response = "I encountered an issue processing your request. Please try again."
                    
                    # Remove any self-mentions to avoid confusion
                    ai_response = ai_response.replace(f"<@{self.user.id}>", "").replace(f"@{self.user.name}", "")
                    
                    # Send response with better chunking
                    if len(ai_response) > 1900:
                        # Split on natural breaks (sentences, paragraphs)
                        chunks = []
                        current_chunk = ""
                        
                        for paragraph in ai_response.split("\n\n"):
                            if len(current_chunk + paragraph) > 1800:
                                if current_chunk:
                                    chunks.append(current_chunk.strip())
                                    current_chunk = ""
                            current_chunk += paragraph + "\n\n"
                        
                        if current_chunk.strip():
                            chunks.append(current_chunk.strip())
                        
                        for i, chunk in enumerate(chunks):
                            if i > 0:
                                chunk = f"*...continued*\n\n{chunk}"
                            if chunk.strip():  # Only send non-empty chunks
                                sent_msg = await message.channel.send(chunk)
                                # Store bot response
                                sent_msg.content = chunk
                                sent_msg.author = self.user
                                await self.store_message(sent_msg, is_bot=True)
                    else:
                        sent_msg = await message.channel.send(ai_response)
                        # Store bot response
                        sent_msg.content = ai_response
                        sent_msg.author = self.user
                        await self.store_message(sent_msg, is_bot=True)
                    
                    logger.info(f"✅ {self.bot_name} responded with tools")
                else:
                    error_text = await response.text()
                    logger.error(f"❌ API server error {response.status}: {error_text}")
                    await message.channel.send("Sorry, I'm having trouble processing your request right now.")
    
    async def setup_hook(self):
        """Called when the bot is starting up"""
        logger.info(f"🤖 {self.bot_name} with MCP tools is starting up...")
        await self.tree.sync()
        logger.info(f"✅ {self.bot_name} commands synced")
    
    async def on_ready(self):
        """Called when bot is ready"""
        logger.info(f"🚀 {self.bot_name} with MCP tools is ready!")
        logger.info(f"Bot user: {self.user}")
        logger.info(f"Bot ID: {self.user.id}")
        logger.info(f"Guilds: {len(self.guilds)}")
        logger.info(f"Discord Tools Available: {len(self.discord_tools)}")
        
        # Set status
        activity = discord.Activity(
            type=discord.ActivityType.listening,
            name="commands | MCP tools enabled"
        )
        await self.change_presence(activity=activity, status=discord.Status.online)
    
    async def on_message(self, message):
        """Handle incoming messages"""
        # Ignore messages from bots
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
            async with message.channel.typing():
                await self.process_with_tools(message)
        
        # Process commands
        await self.process_commands(message)

def load_bot_config(bot_id: str) -> Optional[Dict[str, Any]]:
    """Load bot configuration from YAML file"""
    try:
        with open('./config/bots.yaml', 'r') as f:
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
    api_server_url = os.getenv('API_SERVER_URL', 'http://localhost:5001')
    
    if not discord_token:
        logger.error("❌ DISCORD_TOKEN not provided")
        return
    
    # Load bot configuration
    bot_config = load_bot_config(bot_name.lower())
    if not bot_config:
        logger.error(f"❌ No configuration found for bot: {bot_name}")
        return
    
    if not bot_config.get('enabled', False):
        logger.info(f"🚫 Bot {bot_name} is disabled in configuration")
        return
    
    # Create and run bot with MCP tools
    bot = MCPDiscordBot(bot_config, api_server_url)
    
    try:
        await bot.start(discord_token)
    except Exception as e:
        logger.error(f"💥 Bot failed to start: {e}")
        raise

if __name__ == "__main__":
    asyncio.run(main())