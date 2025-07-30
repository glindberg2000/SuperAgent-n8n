#!/usr/bin/env python3
"""
Discord MCP Server
==================

Provides Discord interaction capabilities through MCP (Model Context Protocol).
Enables bots to interact with Discord channels, users, and messages.
"""

import os
import json
import asyncio
import logging
from typing import Dict, List, Optional, Any
import discord
from discord.ext import commands
import websockets
import argparse
from datetime import datetime

logger = logging.getLogger(__name__)

class DiscordMCPServer:
    """MCP server providing Discord interaction tools"""
    
    def __init__(self, discord_token: str, server_id: str = None, port: int = 8001):
        self.discord_token = discord_token
        self.server_id = server_id
        self.port = port
        self.bot = None
        self.websocket_server = None
        self.connected_clients = set()
        
        # Initialize Discord bot
        intents = discord.Intents.default()
        intents.message_content = True
        intents.members = True
        self.bot = commands.Bot(command_prefix='!', intents=intents)
        
        # Register bot events
        self.setup_bot_events()
    
    def setup_bot_events(self):
        """Setup Discord bot event handlers"""
        
        @self.bot.event
        async def on_ready():
            logger.info(f"Discord bot logged in as {self.bot.user}")
    
    async def start(self):
        """Start the Discord MCP server"""
        try:
            # Start Discord bot
            bot_task = asyncio.create_task(self.bot.start(self.discord_token))
            
            # Wait for bot to be ready
            await self.bot.wait_until_ready()
            logger.info("Discord bot is ready")
            
            # Start WebSocket server
            ws_task = asyncio.create_task(self.start_websocket_server())
            
            # Run both tasks
            await asyncio.gather(bot_task, ws_task)
            
        except Exception as e:
            logger.error(f"Failed to start Discord MCP server: {e}")
            raise
    
    async def start_websocket_server(self):
        """Start the WebSocket server for MCP communication"""
        try:
            self.websocket_server = await websockets.serve(
                self.handle_client, 
                "localhost", 
                self.port,
                subprotocols=["mcp"]
            )
            logger.info(f"Discord MCP server listening on ws://localhost:{self.port}/mcp")
            await self.websocket_server.wait_closed()
            
        except Exception as e:
            logger.error(f"WebSocket server error: {e}")
            raise
    
    async def handle_client(self, websocket, path):
        """Handle incoming MCP client connections"""
        try:
            self.connected_clients.add(websocket)
            logger.info(f"MCP client connected from {websocket.remote_address}")
            
            async for message in websocket:
                try:
                    request = json.loads(message)
                    response = await self.handle_mcp_request(request)
                    await websocket.send(json.dumps(response))
                except json.JSONDecodeError:
                    error_response = {
                        "jsonrpc": "2.0",
                        "id": None,
                        "error": {"code": -32700, "message": "Parse error"}
                    }
                    await websocket.send(json.dumps(error_response))
                    
        except websockets.exceptions.ConnectionClosed:
            logger.info("MCP client disconnected")
        except Exception as e:
            logger.error(f"Error handling MCP client: {e}")
        finally:
            self.connected_clients.discard(websocket)
    
    async def handle_mcp_request(self, request: Dict[str, Any]) -> Dict[str, Any]:
        """Handle MCP requests"""
        try:
            method = request.get("method")
            params = request.get("params", {})
            request_id = request.get("id")
            
            if method == "initialize":
                return await self.handle_initialize(request_id, params)
            elif method == "tools/list":
                return await self.handle_tools_list(request_id)
            elif method == "tools/call":
                return await self.handle_tool_call(request_id, params)
            else:
                return {
                    "jsonrpc": "2.0",
                    "id": request_id,
                    "error": {"code": -32601, "message": f"Method not found: {method}"}
                }
                
        except Exception as e:
            logger.error(f"Error handling MCP request: {e}")
            return {
                "jsonrpc": "2.0",
                "id": request.get("id"),
                "error": {"code": -32603, "message": f"Internal error: {str(e)}"}
            }
    
    async def handle_initialize(self, request_id: str, params: Dict[str, Any]) -> Dict[str, Any]:
        """Handle MCP initialization"""
        return {
            "jsonrpc": "2.0",
            "id": request_id,
            "result": {
                "protocolVersion": "2024-11-05",
                "capabilities": {
                    "tools": {}
                },
                "serverInfo": {
                    "name": "discord-mcp-server",
                    "version": "1.0.0"
                }
            }
        }
    
    async def handle_tools_list(self, request_id: str) -> Dict[str, Any]:
        """Return list of available Discord tools"""
        tools = [
            {
                "name": "get_channel_history",
                "description": "Get message history from a Discord channel",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "channel_id": {"type": "string", "description": "Discord channel ID"},
                        "limit": {"type": "integer", "description": "Number of messages", "default": 50},
                        "before_message_id": {"type": "string", "description": "Get messages before this ID"}
                    },
                    "required": ["channel_id"]
                }
            },
            {
                "name": "send_message",
                "description": "Send a message to a Discord channel",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "channel_id": {"type": "string", "description": "Discord channel ID"},
                        "content": {"type": "string", "description": "Message content"},
                        "embed": {"type": "object", "description": "Optional embed object"}
                    },
                    "required": ["channel_id", "content"]
                }
            },
            {
                "name": "get_channel_members",
                "description": "Get members who have access to a channel",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "channel_id": {"type": "string", "description": "Discord channel ID"}
                    },
                    "required": ["channel_id"]
                }
            },
            {
                "name": "get_online_users",
                "description": "Get currently online users in the server",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "guild_id": {"type": "string", "description": "Discord server ID (optional)"}
                    },
                    "required": []
                }
            },
            {
                "name": "mention_user",
                "description": "Mention a user in a channel",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "user_id": {"type": "string", "description": "Discord user ID"},
                        "message": {"type": "string", "description": "Message content"},
                        "channel_id": {"type": "string", "description": "Channel ID"}
                    },
                    "required": ["user_id", "message", "channel_id"]
                }
            },
            {
                "name": "search_messages",
                "description": "Search for messages containing specific text",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "query": {"type": "string", "description": "Search query"},
                        "channel_id": {"type": "string", "description": "Channel to search (optional)"},
                        "limit": {"type": "integer", "description": "Max results", "default": 25}
                    },
                    "required": ["query"]
                }
            },
            {
                "name": "get_user_info",
                "description": "Get detailed information about a user",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "user_id": {"type": "string", "description": "Discord user ID"}
                    },
                    "required": ["user_id"]
                }
            },
            {
                "name": "list_channels",
                "description": "List channels in the server",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "guild_id": {"type": "string", "description": "Server ID (optional)"},
                        "channel_type": {"type": "string", "description": "Filter by type", "enum": ["text", "voice", "category"]}
                    },
                    "required": []
                }
            }
        ]
        
        return {
            "jsonrpc": "2.0",
            "id": request_id,
            "result": {"tools": tools}
        }
    
    async def handle_tool_call(self, request_id: str, params: Dict[str, Any]) -> Dict[str, Any]:
        """Handle tool calls"""
        try:
            tool_name = params.get("name")
            arguments = params.get("arguments", {})
            
            if tool_name == "get_channel_history":
                result = await self.get_channel_history(**arguments)
            elif tool_name == "send_message":
                result = await self.send_message(**arguments)
            elif tool_name == "get_channel_members":
                result = await self.get_channel_members(**arguments)
            elif tool_name == "get_online_users":
                result = await self.get_online_users(**arguments)
            elif tool_name == "mention_user":
                result = await self.mention_user(**arguments)
            elif tool_name == "search_messages":
                result = await self.search_messages(**arguments)
            elif tool_name == "get_user_info":
                result = await self.get_user_info(**arguments)
            elif tool_name == "list_channels":
                result = await self.list_channels(**arguments)
            else:
                return {
                    "jsonrpc": "2.0",
                    "id": request_id,
                    "error": {"code": -32601, "message": f"Unknown tool: {tool_name}"}
                }
            
            return {
                "jsonrpc": "2.0",
                "id": request_id,
                "result": result
            }
            
        except Exception as e:
            logger.error(f"Error calling tool {params.get('name')}: {e}")
            return {
                "jsonrpc": "2.0",
                "id": request_id,
                "error": {"code": -32603, "message": str(e)}
            }
    
    # Discord tool implementations
    async def get_channel_history(self, channel_id: str, limit: int = 50, before_message_id: str = None) -> Dict[str, Any]:
        """Get message history from a Discord channel"""
        try:
            channel = self.bot.get_channel(int(channel_id))
            if not channel:
                return {"error": f"Channel {channel_id} not found"}
            
            limit = min(limit, 100)
            before = discord.Object(id=int(before_message_id)) if before_message_id else None
            
            messages = []
            async for message in channel.history(limit=limit, before=before):
                messages.append({
                    "id": str(message.id),
                    "author": {
                        "id": str(message.author.id),
                        "username": message.author.name,
                        "display_name": message.author.display_name,
                        "bot": message.author.bot
                    },
                    "content": message.content,
                    "timestamp": message.created_at.isoformat(),
                    "edited_timestamp": message.edited_at.isoformat() if message.edited_at else None,
                    "attachments": [{"filename": att.filename, "url": att.url} for att in message.attachments],
                    "embeds": len(message.embeds),
                    "reactions": [{"emoji": str(r.emoji), "count": r.count} for r in message.reactions]
                })
            
            return {
                "success": True,
                "channel_name": channel.name,
                "message_count": len(messages),
                "messages": messages
            }
            
        except Exception as e:
            return {"error": str(e)}
    
    async def send_message(self, channel_id: str, content: str, embed: Dict[str, Any] = None) -> Dict[str, Any]:
        """Send a message to a Discord channel"""
        try:
            channel = self.bot.get_channel(int(channel_id))
            if not channel:
                return {"error": f"Channel {channel_id} not found"}
            
            discord_embed = None
            if embed:
                discord_embed = discord.Embed.from_dict(embed)
            
            message = await channel.send(content=content, embed=discord_embed)
            
            return {
                "success": True,
                "message_id": str(message.id),
                "channel_name": channel.name,
                "content": content
            }
            
        except Exception as e:
            return {"error": str(e)}
    
    async def get_channel_members(self, channel_id: str) -> Dict[str, Any]:
        """Get members who have access to a channel"""
        try:
            channel = self.bot.get_channel(int(channel_id))
            if not channel or not hasattr(channel, 'guild'):
                return {"error": f"Channel {channel_id} not found or not a guild channel"}
            
            members = []
            for member in channel.guild.members:
                permissions = channel.permissions_for(member)
                if permissions.view_channel:
                    members.append({
                        "id": str(member.id),
                        "username": member.name,
                        "display_name": member.display_name,
                        "bot": member.bot,
                        "status": str(member.status),
                        "roles": [role.name for role in member.roles if role.name != "@everyone"]
                    })
            
            return {
                "success": True,
                "channel_name": channel.name,
                "member_count": len(members),
                "members": members
            }
            
        except Exception as e:
            return {"error": str(e)}
    
    async def get_online_users(self, guild_id: str = None) -> Dict[str, Any]:
        """Get currently online users"""
        try:
            guild = None
            if guild_id:
                guild = self.bot.get_guild(int(guild_id))
            else:
                guild = self.bot.guilds[0] if self.bot.guilds else None
            
            if not guild:
                return {"error": "Guild not found"}
            
            online_users = []
            for member in guild.members:
                if member.status != discord.Status.offline:
                    online_users.append({
                        "id": str(member.id),
                        "username": member.name,
                        "display_name": member.display_name,
                        "status": str(member.status),
                        "activity": member.activity.name if member.activity else None,
                        "bot": member.bot
                    })
            
            return {
                "success": True,
                "guild_name": guild.name,
                "online_count": len(online_users),
                "online_users": online_users
            }
            
        except Exception as e:
            return {"error": str(e)}
    
    async def mention_user(self, user_id: str, message: str, channel_id: str) -> Dict[str, Any]:
        """Mention a user in a channel"""
        try:
            channel = self.bot.get_channel(int(channel_id))
            if not channel:
                return {"error": f"Channel {channel_id} not found"}
            
            user = self.bot.get_user(int(user_id))
            if not user:
                return {"error": f"User {user_id} not found"}
            
            mention_text = f"<@{user_id}> {message}"
            sent_message = await channel.send(mention_text)
            
            return {
                "success": True,
                "message_id": str(sent_message.id),
                "channel_name": channel.name,
                "mentioned_user": user.display_name,
                "content": mention_text
            }
            
        except Exception as e:
            return {"error": str(e)}
    
    async def search_messages(self, query: str, channel_id: str = None, limit: int = 25) -> Dict[str, Any]:
        """Search for messages containing specific text"""
        try:
            channels_to_search = []
            
            if channel_id:
                channel = self.bot.get_channel(int(channel_id))
                if channel:
                    channels_to_search = [channel]
            else:
                # Search in all accessible text channels
                for guild in self.bot.guilds:
                    for channel in guild.text_channels:
                        if channel.permissions_for(guild.me).read_message_history:
                            channels_to_search.append(channel)
            
            results = []
            query_lower = query.lower()
            
            for channel in channels_to_search[:5]:  # Limit for performance
                try:
                    async for message in channel.history(limit=200):
                        if query_lower in message.content.lower():
                            results.append({
                                "message_id": str(message.id),
                                "channel_id": str(message.channel.id),
                                "channel_name": message.channel.name,
                                "author": {
                                    "id": str(message.author.id),
                                    "username": message.author.name,
                                    "display_name": message.author.display_name
                                },
                                "content": message.content,
                                "timestamp": message.created_at.isoformat()
                            })
                            
                            if len(results) >= limit:
                                break
                    
                    if len(results) >= limit:
                        break
                        
                except discord.Forbidden:
                    continue
            
            return {
                "success": True,
                "query": query,
                "result_count": len(results),
                "results": results
            }
            
        except Exception as e:
            return {"error": str(e)}
    
    async def get_user_info(self, user_id: str) -> Dict[str, Any]:
        """Get detailed information about a user"""
        try:
            user = self.bot.get_user(int(user_id))
            if not user:
                return {"error": f"User {user_id} not found"}
            
            user_info = {
                "id": str(user.id),
                "username": user.name,
                "display_name": user.display_name,
                "bot": user.bot,
                "created_at": user.created_at.isoformat(),
                "avatar_url": str(user.avatar) if user.avatar else None
            }
            
            # Add guild-specific info
            mutual_guilds = []
            for guild in self.bot.guilds:
                member = guild.get_member(user.id)
                if member:
                    mutual_guilds.append({
                        "guild_id": str(guild.id),
                        "guild_name": guild.name,
                        "nickname": member.nick,
                        "status": str(member.status),
                        "roles": [role.name for role in member.roles if role.name != "@everyone"]
                    })
            
            user_info["mutual_guilds"] = mutual_guilds
            
            return {"success": True, "user": user_info}
            
        except Exception as e:
            return {"error": str(e)}
    
    async def list_channels(self, guild_id: str = None, channel_type: str = None) -> Dict[str, Any]:
        """List channels in a guild"""
        try:
            guild = None
            if guild_id:
                guild = self.bot.get_guild(int(guild_id))
            else:
                guild = self.bot.guilds[0] if self.bot.guilds else None
            
            if not guild:
                return {"error": "Guild not found"}
            
            channels = []
            for channel in guild.channels:
                # Filter by type if specified
                if channel_type:
                    if channel_type == 'text' and not isinstance(channel, discord.TextChannel):
                        continue
                    elif channel_type == 'voice' and not isinstance(channel, discord.VoiceChannel):
                        continue
                    elif channel_type == 'category' and not isinstance(channel, discord.CategoryChannel):
                        continue
                
                channels.append({
                    "id": str(channel.id),
                    "name": channel.name,
                    "type": str(channel.type),
                    "position": channel.position,
                    "category": channel.category.name if channel.category else None
                })
            
            channels.sort(key=lambda x: x['position'])
            
            return {
                "success": True,
                "guild_name": guild.name,
                "guild_id": str(guild.id),
                "channel_count": len(channels),
                "channels": channels
            }
            
        except Exception as e:
            return {"error": str(e)}


async def main():
    """Main entry point for the Discord MCP server"""
    parser = argparse.ArgumentParser(description="Discord MCP Server")
    parser.add_argument("--token", required=True, help="Discord bot token")
    parser.add_argument("--server-id", help="Discord server ID")
    parser.add_argument("--port", type=int, default=8001, help="WebSocket port")
    
    args = parser.parse_args()
    
    # Configure logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # Create and start server
    server = DiscordMCPServer(
        discord_token=args.token,
        server_id=args.server_id,
        port=args.port
    )
    
    try:
        await server.start()
    except KeyboardInterrupt:
        logger.info("Shutting down Discord MCP server...")
    except Exception as e:
        logger.error(f"Discord MCP server error: {e}")
        raise


if __name__ == "__main__":
    asyncio.run(main())