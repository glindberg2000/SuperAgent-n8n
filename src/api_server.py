#!/usr/bin/env python3
"""
BotForge API Server
==================

Central API server that handles Discord messages and routes them to appropriate
AI models based on bot configuration.
"""

import os
import logging
import asyncio
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, List
import json
import yaml

from flask import Flask, request, jsonify
import psycopg2
from psycopg2.extras import RealDictCursor
import redis

# AI Provider imports
import openai
from anthropic import Anthropic
import requests
import discord
from discord.ext import commands

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('./logs/api_server.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

app = Flask(__name__)

# Global configurations
DB_CONFIG = {
    'host': os.getenv('POSTGRES_HOST', 'postgres'),
    'port': int(os.getenv('POSTGRES_PORT', 5432)),
    'database': os.getenv('POSTGRES_DB', 'botforge'),
    'user': os.getenv('POSTGRES_USER', 'botforge'),
    'password': os.getenv('POSTGRES_PASSWORD', 'botforge-db-2025')
}

REDIS_CONFIG = {
    'host': os.getenv('REDIS_HOST', 'redis'),
    'port': int(os.getenv('REDIS_PORT', 6379)),
    'db': 0
}

class AIProviderManager:
    """Manages different AI providers"""
    
    def __init__(self):
        self.providers = {}
        self._setup_providers()
    
    def _setup_providers(self):
        """Initialize AI providers"""
        # OpenAI/GPT
        openai_key = os.getenv('OPENAI_API_KEY')
        if openai_key:
            openai.api_key = openai_key
            self.providers['openai'] = self._call_openai
            logger.info("✅ OpenAI provider initialized")
        
        # Anthropic/Claude
        anthropic_key = os.getenv('ANTHROPIC_API_KEY')
        if anthropic_key:
            try:
                self.providers['anthropic'] = Anthropic(api_key=anthropic_key)
                logger.info("✅ Anthropic provider initialized")
            except Exception as e:
                logger.warning(f"⚠️ Failed to initialize Anthropic provider: {e}")
        
        # X.AI/Grok
        xai_key = os.getenv('XAI_API_KEY')
        if xai_key:
            self.providers['xai'] = self._call_xai
            logger.info("✅ X.AI provider initialized")
    
    async def get_response(self, provider: str, model: str, messages: List[Dict], personality: str, tools: List[Dict] = None) -> str:
        """Get response from specified AI provider"""
        try:
            if provider == 'openai':
                return await self._call_openai(model, messages, personality)
            elif provider == 'anthropic':
                return await self._call_anthropic(model, messages, personality)
            elif provider == 'xai':
                return await self._call_xai(model, messages, personality, tools)
            else:
                return f"❌ Unknown AI provider: {provider}"
        except Exception as e:
            logger.error(f"AI Provider error ({provider}): {e}")
            return f"Sorry, I'm having trouble connecting to {provider} right now."
    
    async def _call_openai(self, model: str, messages: List[Dict], personality: str) -> str:
        """Call OpenAI API"""
        try:
            # Add personality as system message
            full_messages = [{"role": "system", "content": personality}] + messages
            
            response = await openai.ChatCompletion.acreate(
                model=model,
                messages=full_messages,
                max_tokens=1500,
                temperature=0.7
            )
            return response.choices[0].message.content.strip()
        except Exception as e:
            logger.error(f"OpenAI API error: {e}")
            raise
    
    async def _call_anthropic(self, model: str, messages: List[Dict], personality: str) -> str:
        """Call Anthropic API"""
        try:
            # Convert messages format and add personality
            claude_messages = []
            for msg in messages:
                if msg['role'] == 'user':
                    claude_messages.append({"role": "user", "content": msg['content']})
                elif msg['role'] == 'assistant':
                    claude_messages.append({"role": "assistant", "content": msg['content']})
            
            response = self.providers['anthropic'].messages.create(
                model=model,
                max_tokens=1500,
                system=personality,
                messages=claude_messages
            )
            return response.content[0].text
        except Exception as e:
            logger.error(f"Anthropic API error: {e}")
            raise
    
    async def _call_xai(self, model: str, messages: List[Dict], personality: str, tools: List[Dict] = None) -> str:
        """Call X.AI/Grok API with optional function calling"""
        try:
            # Add personality as system message
            full_messages = [{"role": "system", "content": personality}] + messages
            
            # Build request payload
            payload = {
                "messages": full_messages,
                "model": model,
                "stream": False,
                "temperature": 0.7,
                "max_tokens": 1500
            }
            
            # Add tools if provided
            if tools:
                payload["tools"] = tools
                payload["tool_choice"] = "auto"
                logger.info(f"🔧 XAI payload includes {len(tools)} tools with tool_choice=auto")
            
            response = requests.post(
                "https://api.x.ai/v1/chat/completions",
                headers={
                    "Authorization": f"Bearer {os.getenv('XAI_API_KEY')}",
                    "Content-Type": "application/json"
                },
                json=payload,
                timeout=30
            )
            
            if response.status_code == 200:
                result = response.json()
                message = result['choices'][0]['message']
                
                # Check if there are tool calls
                if message.get('tool_calls'):
                    logger.info(f"🔧 XAI returned {len(message['tool_calls'])} tool calls")
                    return {
                        "content": message.get('content', ''),
                        "tool_calls": message['tool_calls']
                    }
                else:
                    logger.info("🔧 XAI returned text response, no tool calls")
                    return message.get('content', '').strip()
            else:
                logger.error(f"X.AI API error: {response.status_code} - {response.text}")
                raise Exception(f"X.AI API returned {response.status_code}")
        except Exception as e:
            logger.error(f"X.AI API error: {e}")
            raise

class DatabaseManager:
    """Manages PostgreSQL database operations"""
    
    def __init__(self):
        self.db_config = DB_CONFIG
    
    def get_connection(self):
        """Get database connection"""
        return psycopg2.connect(**self.db_config)
    
    def store_message(self, webhook_data: Dict[str, Any]) -> None:
        """Store message in database"""
        try:
            with self.get_connection() as conn:
                with conn.cursor() as cur:
                    cur.execute("""
                        INSERT INTO discord_messages 
                        (bot_name, channel_id, guild_id, user_id, username, message_content, message_id, timestamp)
                        VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                    """, (
                        webhook_data['bot_name'],
                        webhook_data['channel_id'],
                        webhook_data.get('guild_id'),
                        webhook_data['user_id'],
                        webhook_data['username'],
                        webhook_data['message_content'],
                        webhook_data['message_id'],
                        webhook_data['timestamp']
                    ))
                    conn.commit()
        except Exception as e:
            logger.error(f"Database storage error: {e}")
    
    def get_conversation_history(self, bot_name: str, channel_id: str, user_id: str, limit: int = 10) -> List[Dict[str, Any]]:
        """Get recent conversation history"""
        try:
            with self.get_connection() as conn:
                with conn.cursor(cursor_factory=RealDictCursor) as cur:
                    cur.execute("""
                        SELECT message_content, username, timestamp, bot_name
                        FROM discord_messages 
                        WHERE channel_id = %s 
                        AND (user_id = %s OR bot_name = %s)
                        ORDER BY timestamp DESC 
                        LIMIT %s
                    """, (channel_id, user_id, bot_name, limit))
                    
                    messages = []
                    for row in reversed(cur.fetchall()):  # Reverse to get chronological order
                        if row['bot_name'] == bot_name:
                            role = 'assistant'
                            content = row['message_content']
                        else:
                            role = 'user'
                            content = row['message_content']
                        
                        messages.append({
                            'role': role,
                            'content': content
                        })
                    
                    return messages
        except Exception as e:
            logger.error(f"Database history error: {e}")
            return []

def load_bot_configs() -> Dict[str, Any]:
    """Load bot configurations from YAML"""
    try:
        with open('./config/bots.yaml', 'r') as f:
            return yaml.safe_load(f)
    except Exception as e:
        logger.error(f"Failed to load bot config: {e}")
        return {'bots': {}}

class DiscordToolsManager:
    """Provides Discord interaction capabilities for AI agents"""
    
    def __init__(self):
        self.bot = None
        self.discord_token = os.getenv('DISCORD_TOKEN_GROK4')
        if self.discord_token:
            self.setup_bot()
    
    def setup_bot(self):
        """Initialize Discord bot for tools"""
        intents = discord.Intents.default()
        intents.message_content = True
        intents.members = True
        intents.guilds = True
        
        self.bot = commands.Bot(command_prefix='!tools_', intents=intents)
        
        @self.bot.event
        async def on_ready():
            logger.info(f"🔧 Discord Tools bot ready: {self.bot.user}")
    
    async def get_server_info(self, guild_id: str = None):
        """Get Discord server information"""
        if not self.bot or not self.bot.is_ready():
            return {"error": "Discord tools not available"}
        
        try:
            if guild_id:
                guild = self.bot.get_guild(int(guild_id))
            else:
                guild = self.bot.guilds[0] if self.bot.guilds else None
            
            if not guild:
                return {"error": "Server not found"}
            
            return {
                "success": True,
                "server": {
                    "name": guild.name,
                    "id": str(guild.id),
                    "member_count": guild.member_count,
                    "channel_count": len(guild.channels),
                    "created_at": guild.created_at.isoformat()
                }
            }
        except Exception as e:
            logger.error(f"Error getting server info: {e}")
            return {"error": str(e)}
    
    async def list_channels(self, guild_id: str = None):
        """List channels in Discord server"""
        if not self.bot or not self.bot.is_ready():
            return {"error": "Discord tools not available"}
        
        try:
            if guild_id:
                guild = self.bot.get_guild(int(guild_id))
            else:
                guild = self.bot.guilds[0] if self.bot.guilds else None
            
            if not guild:
                return {"error": "Server not found"}
            
            channels = []
            for channel in guild.channels:
                channels.append({
                    "id": str(channel.id),
                    "name": channel.name,
                    "type": str(channel.type),
                    "category": channel.category.name if channel.category else None,
                    "position": channel.position
                })
            
            return {
                "success": True,
                "channels": channels,
                "count": len(channels)
            }
        except Exception as e:
            logger.error(f"Error listing channels: {e}")
            return {"error": str(e)}
    
    async def get_channel_info(self, channel_id: str):
        """Get information about a specific channel"""
        if not self.bot or not self.bot.is_ready():
            return {"error": "Discord tools not available"}
        
        try:
            channel = self.bot.get_channel(int(channel_id))
            if not channel:
                return {"error": "Channel not found"}
            
            info = {
                "id": str(channel.id),
                "name": channel.name,
                "type": str(channel.type),
                "guild": channel.guild.name,
                "category": channel.category.name if channel.category else None,
                "position": channel.position,
                "created_at": channel.created_at.isoformat()
            }
            
            if hasattr(channel, 'topic') and channel.topic:
                info["topic"] = channel.topic
            
            return {
                "success": True,
                "channel": info
            }
        except Exception as e:
            logger.error(f"Error getting channel info: {e}")
            return {"error": str(e)}

# Initialize managers
ai_manager = AIProviderManager()
db_manager = DatabaseManager()
discord_tools = DiscordToolsManager()

# Start Discord tools bot if available
async def start_discord_tools():
    """Start Discord tools bot in the background"""
    if discord_tools.discord_token and discord_tools.bot:
        try:
            # Start the bot in the background
            import threading
            def run_bot():
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                loop.run_until_complete(discord_tools.bot.start(discord_tools.discord_token))
            
            bot_thread = threading.Thread(target=run_bot, daemon=True)
            bot_thread.start()
            logger.info("🚀 Discord tools bot starting in background...")
        except Exception as e:
            logger.error(f"Failed to start Discord tools bot: {e}")

# Start Discord tools on import
try:
    asyncio.run(start_discord_tools())
except Exception as e:
    logger.warning(f"Discord tools initialization warning: {e}")

async def enhance_personality_with_tools(personality: str, webhook_data: Dict) -> str:
    """Enhance AI personality with available Discord tools information"""
    
    # Check if Discord tools are available
    tools_available = discord_tools.discord_token is not None
    
    if not tools_available:
        return personality
    
    # Get current server information
    try:
        server_info = await discord_tools.get_server_info()
        channels_info = await discord_tools.list_channels()
        
        if server_info.get('success') and channels_info.get('success'):
            server_data = server_info['server']
            channels_data = channels_info['channels'][:10]  # First 10 channels
            
            tools_context = f"""

🔧 **DISCORD TOOLS AVAILABLE** - You have access to live Discord server information:

**Current Server**: {server_data['name']} (ID: {server_data['id']})
- Members: {server_data['member_count']}
- Channels: {server_data['channel_count']} total

**Available Channels** (showing first 10):
"""
            for ch in channels_data:
                tools_context += f"- #{ch['name']} ({ch['type']}) - ID: {ch['id']}\n"
            
            tools_context += f"""
**Your Discord Capabilities**:
- ✅ View server information (name, member count, channels)
- ✅ List all channels and their types
- ✅ Get detailed channel information
- ✅ Access current server context: "{server_data['name']}"

When users ask about "this server", "current channels", or "browse channels", you can provide specific information about the {server_data['name']} Discord server you're currently connected to.
"""
            
            return personality + tools_context
    except Exception as e:
        logger.error(f"Error enhancing personality with tools: {e}")
    
    return personality

@app.route('/health', methods=['GET'])
def health_check():
    """Health check endpoint"""
    try:
        # Test database connection
        with db_manager.get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute('SELECT 1')
        
        return jsonify({
            'status': 'healthy',
            'timestamp': datetime.utcnow().isoformat(),
            'services': {
                'database': 'connected',
                'ai_providers': list(ai_manager.providers.keys())
            }
        })
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        return jsonify({
            'status': 'unhealthy',
            'error': str(e)
        }), 500

@app.route('/stats', methods=['GET'])
def get_stats():
    """Get system statistics"""
    try:
        with db_manager.get_connection() as conn:
            with conn.cursor() as cur:
                # Get message counts
                cur.execute("SELECT COUNT(*) FROM discord_messages WHERE timestamp > %s", 
                           (datetime.utcnow() - timedelta(days=1),))
                messages_today = cur.fetchone()[0]
                
                cur.execute("SELECT COUNT(DISTINCT user_id) FROM discord_messages WHERE timestamp > %s", 
                           (datetime.utcnow() - timedelta(days=1),))
                active_users = cur.fetchone()[0]
                
                cur.execute("SELECT COUNT(*) FROM discord_messages")
                total_messages = cur.fetchone()[0]
                
                cur.execute("SELECT COUNT(DISTINCT user_id) FROM discord_messages")
                total_users = cur.fetchone()[0]
        
        return jsonify({
            'messages_today': messages_today,
            'active_users_today': active_users,
            'total_messages': total_messages,
            'total_users': total_users,
            'ai_providers': list(ai_manager.providers.keys()),
            'timestamp': datetime.utcnow().isoformat()
        })
    except Exception as e:
        logger.error(f"Stats error: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/process_discord_message', methods=['POST'])
def process_discord_message():
    """Main endpoint for processing Discord messages"""
    try:
        webhook_data = request.json
        
        if not webhook_data:
            return jsonify({'error': 'No data provided'}), 400
        
        logger.info(f"Processing message from {webhook_data.get('username')} via {webhook_data.get('bot_name')}")
        
        # Store message in database
        db_manager.store_message(webhook_data)
        
        # Get bot configuration
        bot_configs = load_bot_configs()
        bot_display_name = webhook_data['bot_name']
        
        # Find bot config by matching display name
        bot_config = None
        bot_key = None
        for key, config in bot_configs['bots'].items():
            if config.get('name', '').lower() == bot_display_name.lower():
                bot_config = config
                bot_key = key
                break
        
        if not bot_config:
            return jsonify({'error': f'Bot configuration not found: {bot_display_name}'}), 404
        
        # Get conversation history (use provided history if available from MCP bot)
        if 'conversation_history' in webhook_data:
            history = webhook_data['conversation_history']
            logger.info(f"Using MCP bot conversation history: {len(history)} messages")
        else:
            max_context = bot_config.get('max_context_messages', 10)
            history = db_manager.get_conversation_history(
                webhook_data['bot_name'],
                webhook_data['channel_id'],
                webhook_data['user_id'],
                max_context
            )
        
        # Handle tool results from follow-up requests
        if webhook_data.get('follow_up_request') and 'tool_results' in webhook_data:
            # This is a follow-up request with tool results
            tool_results = webhook_data['tool_results']
            logger.info(f"🔧 Processing follow-up request with {len(tool_results)} tool results")
            tool_context = "Tool execution results:\n"
            for tool_result in tool_results:
                tool_context += f"- {tool_result['tool_name']}: {json.dumps(tool_result['result'], indent=2)}\n"
            
            current_message = {
                'role': 'user', 
                'content': f"{tool_context}\n\nUser's original question: {webhook_data.get('original_message', webhook_data['message_content'])}\n\nPlease provide a natural, helpful response based on the tool results above."
            }
        else:
            # Regular message
            current_message = {
                'role': 'user',
                'content': webhook_data['message_content']
            }
        
        # Prepare messages for AI
        messages = history + [current_message]
        
        # Get AI response (run async function in sync context)
        import asyncio
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            # Enhance personality with Discord tools information
            base_personality = bot_config.get('personality', 'You are a helpful AI assistant.')
            enhanced_personality = loop.run_until_complete(
                enhance_personality_with_tools(base_personality, webhook_data)
            )
            
            # Define Discord tools for function calling if MCP tools are available
            # Don't provide tools for follow-up requests (we already have tool results)
            tools = None
            if 'tools_available' in webhook_data and not webhook_data.get('follow_up_request'):
                logger.info(f"🔧 Tools available from MCP bot: {webhook_data['tools_available']}")
                tools = [
                    {
                        "type": "function",
                        "function": {
                            "name": "list_channels",
                            "description": "List all channels available in the Discord server",
                            "parameters": {
                                "type": "object",
                                "properties": {
                                    "guild_id": {
                                        "type": "string",
                                        "description": "The Discord server/guild ID (optional)"
                                    }
                                }
                            }
                        }
                    },
                    {
                        "type": "function", 
                        "function": {
                            "name": "get_server_info",
                            "description": "Get information about the current Discord server",
                            "parameters": {
                                "type": "object",
                                "properties": {
                                    "guild_id": {
                                        "type": "string",
                                        "description": "The Discord server/guild ID (optional)"
                                    }
                                }
                            }
                        }
                    },
                    {
                        "type": "function",
                        "function": {
                            "name": "get_channel_history", 
                            "description": "Get recent messages from a specific Discord channel",
                            "parameters": {
                                "type": "object",
                                "properties": {
                                    "channel_id": {
                                        "type": "string",
                                        "description": "The Discord channel ID to get messages from"
                                    },
                                    "limit": {
                                        "type": "integer",
                                        "description": "Number of messages to retrieve (default 10)"
                                    }
                                },
                                "required": ["channel_id"]
                            }
                        }
                    },
                    {
                        "type": "function",
                        "function": {
                            "name": "get_online_users",
                            "description": "Get list of currently online users in the Discord server",
                            "parameters": {
                                "type": "object",
                                "properties": {
                                    "guild_id": {
                                        "type": "string", 
                                        "description": "The Discord server/guild ID (optional)"
                                    }
                                }
                            }
                        }
                    },
                    {
                        "type": "function",
                        "function": {
                            "name": "search_messages",
                            "description": "Search for messages containing specific text",
                            "parameters": {
                                "type": "object",
                                "properties": {
                                    "query": {
                                        "type": "string",
                                        "description": "The text to search for in messages"
                                    },
                                    "channel_id": {
                                        "type": "string",
                                        "description": "Limit search to specific channel (optional)"
                                    },
                                    "limit": {
                                        "type": "integer",
                                        "description": "Maximum number of results (default 20)"
                                    }
                                },
                                "required": ["query"]
                            }
                        }
                    }
                ]
                logger.info(f"🔧 Sending {len(tools)} tools to XAI API")
            else:
                logger.info("❌ No tools_available in webhook_data - tools will be None")
            
            ai_response = loop.run_until_complete(ai_manager.get_response(
                provider=bot_config['llm_provider'],
                model=bot_config['llm_model'],
                messages=messages,
                personality=enhanced_personality,
                tools=tools
            ))
        finally:
            loop.close()
        
        # Handle function calls if present
        if isinstance(ai_response, dict) and 'tool_calls' in ai_response:
            # Extract tool calls for the Discord bot to handle
            logger.info(f"🔧 AI requested tool calls: {len(ai_response['tool_calls'])}")
            return jsonify({
                'success': True,
                'response': ai_response.get('content', 'Let me check that for you...'),
                'tool_calls': [
                    {
                        'tool': call['function']['name'],
                        'arguments': call['function'].get('arguments', {})
                    }
                    for call in ai_response['tool_calls']
                ],
                'bot_name': webhook_data['bot_name']
            })
        else:
            # Store AI response for regular text responses
            response_content = ai_response if isinstance(ai_response, str) else str(ai_response)
            response_data = webhook_data.copy()
            response_data.update({
                'message_content': response_content,
                'username': webhook_data['bot_name'],
                'user_id': None,  # Bot responses don't need user_id
                'timestamp': datetime.utcnow().isoformat()
            })
            db_manager.store_message(response_data)
        
            logger.info(f"✅ Generated response for {webhook_data.get('username')}")
        
            return jsonify({
                'success': True,
                'response': response_content,
                'bot_name': webhook_data['bot_name']
            })
        
    except Exception as e:
        logger.error(f"💥 Error processing message: {e}")
        return jsonify({
            'success': False,
            'error': str(e),
            'response': 'Sorry, I encountered an error processing your message.'
        }), 500

if __name__ == '__main__':
    logger.info("🚀 Starting BotForge API Server...")
    app.run(host='0.0.0.0', port=5001, debug=False)