#!/usr/bin/env python3
"""
Discord Tools for BotForge
==========================

Provides Discord interaction capabilities that can be called by LLMs as tools.
These functions give bots the ability to interact with Discord like real users.
"""

import logging
import discord
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Union
import json
import re

logger = logging.getLogger(__name__)

class DiscordTools:
    """Discord interaction tools for LLM function calling"""
    
    def __init__(self, bot_instance: discord.Client):
        self.bot = bot_instance
    
    async def get_channel_history(self, channel_id: str, limit: int = 50, before_message_id: Optional[str] = None) -> Dict[str, Any]:
        """
        Get message history from a Discord channel
        
        Args:
            channel_id: Discord channel ID
            limit: Number of messages to retrieve (max 100)
            before_message_id: Get messages before this message ID
            
        Returns:
            Dict with messages list and metadata
        """
        try:
            channel = self.bot.get_channel(int(channel_id))
            if not channel:
                return {"error": f"Channel {channel_id} not found or not accessible"}
            
            # Limit safety check
            limit = min(limit, 100)
            
            before = None
            if before_message_id:
                try:
                    before = discord.Object(id=int(before_message_id))
                except ValueError:
                    return {"error": "Invalid before_message_id format"}
            
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
                    "attachments": [
                        {
                            "filename": att.filename,
                            "size": att.size,
                            "url": att.url,
                            "content_type": att.content_type
                        } for att in message.attachments
                    ],
                    "embeds": len(message.embeds),
                    "reactions": [
                        {
                            "emoji": str(reaction.emoji),
                            "count": reaction.count
                        } for reaction in message.reactions
                    ],
                    "reply_to": str(message.reference.message_id) if message.reference else None
                })
            
            return {
                "success": True,
                "channel_name": channel.name,
                "channel_type": str(channel.type),
                "message_count": len(messages),
                "messages": messages
            }
            
        except Exception as e:
            logger.error(f"Error getting channel history: {e}")
            return {"error": str(e)}
    
    async def get_channel_members(self, channel_id: str) -> Dict[str, Any]:
        """
        Get members who have access to a specific channel
        
        Args:
            channel_id: Discord channel ID
            
        Returns:
            Dict with member list and metadata
        """
        try:
            channel = self.bot.get_channel(int(channel_id))
            if not channel:
                return {"error": f"Channel {channel_id} not found or not accessible"}
            
            if not hasattr(channel, 'guild'):
                return {"error": "Channel is not a guild channel"}
            
            # Get members who can view this channel
            members = []
            for member in channel.guild.members:
                permissions = channel.permissions_for(member)
                if permissions.view_channel:
                    members.append({
                        "id": str(member.id),
                        "username": member.name,
                        "display_name": member.display_name,
                        "discriminator": member.discriminator,
                        "bot": member.bot,
                        "status": str(member.status),
                        "activity": str(member.activity) if member.activity else None,
                        "roles": [role.name for role in member.roles if role.name != "@everyone"],
                        "joined_at": member.joined_at.isoformat() if member.joined_at else None,
                        "permissions": {
                            "can_send_messages": permissions.send_messages,
                            "can_manage_messages": permissions.manage_messages,
                            "can_read_history": permissions.read_message_history
                        }
                    })
            
            return {
                "success": True,
                "channel_name": channel.name,
                "guild_name": channel.guild.name,
                "member_count": len(members),
                "members": members
            }
            
        except Exception as e:
            logger.error(f"Error getting channel members: {e}")
            return {"error": str(e)}
    
    async def get_online_users(self, guild_id: Optional[str] = None) -> Dict[str, Any]:
        """
        Get currently online users in a guild
        
        Args:
            guild_id: Discord guild ID (optional, uses first guild if not provided)
            
        Returns:
            Dict with online users list
        """
        try:
            guild = None
            if guild_id:
                guild = self.bot.get_guild(int(guild_id))
            else:
                # Use first available guild
                guild = self.bot.guilds[0] if self.bot.guilds else None
            
            if not guild:
                return {"error": "Guild not found or bot not in any guild"}
            
            online_users = []
            for member in guild.members:
                if member.status != discord.Status.offline:
                    online_users.append({
                        "id": str(member.id),
                        "username": member.name,
                        "display_name": member.display_name,
                        "status": str(member.status),
                        "activity": {
                            "name": member.activity.name if member.activity else None,
                            "type": str(member.activity.type) if member.activity else None
                        },
                        "bot": member.bot
                    })
            
            return {
                "success": True,
                "guild_name": guild.name,
                "online_count": len(online_users),
                "total_members": guild.member_count,
                "online_users": online_users
            }
            
        except Exception as e:
            logger.error(f"Error getting online users: {e}")
            return {"error": str(e)}
    
    async def mention_user(self, user_id: str, message: str, channel_id: str) -> Dict[str, Any]:
        """
        Mention a user in a specific channel
        
        Args:
            user_id: Discord user ID to mention
            message: Message content
            channel_id: Channel to send the message in
            
        Returns:
            Dict with success status and message info
        """
        try:
            channel = self.bot.get_channel(int(channel_id))
            if not channel:
                return {"error": f"Channel {channel_id} not found or not accessible"}
            
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
            logger.error(f"Error mentioning user: {e}")
            return {"error": str(e)}
    
    async def search_messages(self, query: str, channel_id: Optional[str] = None, limit: int = 25) -> Dict[str, Any]:
        """
        Search for messages containing specific text
        
        Args:
            query: Text to search for
            channel_id: Specific channel to search in (optional)
            limit: Number of results to return
            
        Returns:
            Dict with search results
        """
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
            
            if not channels_to_search:
                return {"error": "No accessible channels to search"}
            
            results = []
            query_lower = query.lower()
            
            for channel in channels_to_search[:5]:  # Limit channel search for performance
                try:
                    async for message in channel.history(limit=200):  # Search recent messages
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
                                "timestamp": message.created_at.isoformat(),
                                "url": f"https://discord.com/channels/{message.guild.id}/{message.channel.id}/{message.id}"
                            })
                            
                            if len(results) >= limit:
                                break
                    
                    if len(results) >= limit:
                        break
                        
                except discord.Forbidden:
                    continue  # Skip channels we can't access
            
            return {
                "success": True,
                "query": query,
                "result_count": len(results),
                "results": results
            }
            
        except Exception as e:
            logger.error(f"Error searching messages: {e}")
            return {"error": str(e)}
    
    async def get_user_info(self, user_id: str) -> Dict[str, Any]:
        """
        Get detailed information about a user
        
        Args:
            user_id: Discord user ID
            
        Returns:
            Dict with user information
        """
        try:
            user = self.bot.get_user(int(user_id))
            if not user:
                return {"error": f"User {user_id} not found"}
            
            user_info = {
                "id": str(user.id),
                "username": user.name,
                "discriminator": user.discriminator,
                "display_name": user.display_name,
                "bot": user.bot,
                "created_at": user.created_at.isoformat(),
                "avatar_url": str(user.avatar) if user.avatar else None
            }
            
            # Add guild-specific info if user is in mutual guilds
            mutual_guilds = []
            for guild in self.bot.guilds:
                member = guild.get_member(user.id)
                if member:
                    mutual_guilds.append({
                        "guild_id": str(guild.id),
                        "guild_name": guild.name,
                        "nickname": member.nick,
                        "status": str(member.status),
                        "roles": [role.name for role in member.roles if role.name != "@everyone"],
                        "joined_at": member.joined_at.isoformat() if member.joined_at else None
                    })
            
            user_info["mutual_guilds"] = mutual_guilds
            
            return {
                "success": True,
                "user": user_info
            }
            
        except Exception as e:
            logger.error(f"Error getting user info: {e}")
            return {"error": str(e)}
    
    async def list_channels(self, guild_id: Optional[str] = None, channel_type: Optional[str] = None) -> Dict[str, Any]:
        """
        List channels in a guild
        
        Args:
            guild_id: Discord guild ID (optional)
            channel_type: Filter by channel type ('text', 'voice', 'category')
            
        Returns:
            Dict with channels list
        """
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
                    "category": channel.category.name if channel.category else None,
                    "permissions": {
                        "can_view": channel.permissions_for(guild.me).view_channel,
                        "can_send": getattr(channel.permissions_for(guild.me), 'send_messages', False),
                        "can_read_history": getattr(channel.permissions_for(guild.me), 'read_message_history', False)
                    }
                })
            
            # Sort by position
            channels.sort(key=lambda x: x['position'])
            
            return {
                "success": True,
                "guild_name": guild.name,
                "guild_id": str(guild.id),
                "channel_count": len(channels),
                "channels": channels
            }
            
        except Exception as e:
            logger.error(f"Error listing channels: {e}")
            return {"error": str(e)}


def get_discord_tools_schema() -> List[Dict[str, Any]]:
    """
    Get the function schema for Discord tools that can be used by LLMs
    
    Returns:
        List of function schemas for OpenAI/Anthropic function calling
    """
    return [
        {
            "name": "get_channel_history",
            "description": "Get message history from a Discord channel. Useful for reviewing past conversations, understanding context, or analyzing team discussions.",
            "parameters": {
                "type": "object",
                "properties": {
                    "channel_id": {
                        "type": "string",
                        "description": "Discord channel ID to get history from"
                    },
                    "limit": {
                        "type": "integer",
                        "description": "Number of messages to retrieve (max 100)",
                        "default": 50
                    },
                    "before_message_id": {
                        "type": "string",
                        "description": "Get messages before this message ID (optional)"
                    }
                },
                "required": ["channel_id"]
            }
        },
        {
            "name": "get_channel_members",
            "description": "Get list of members who have access to a specific channel. Useful for understanding team composition and permissions.",
            "parameters": {
                "type": "object",
                "properties": {
                    "channel_id": {
                        "type": "string",
                        "description": "Discord channel ID to get members from"
                    }
                },
                "required": ["channel_id"]
            }
        },
        {
            "name": "get_online_users",
            "description": "Get currently online users in the server. Useful for knowing who's available for immediate collaboration.",
            "parameters": {
                "type": "object",
                "properties": {
                    "guild_id": {
                        "type": "string",
                        "description": "Discord server/guild ID (optional)"
                    }
                },
                "required": []
            }
        },
        {
            "name": "mention_user",
            "description": "Mention a specific user in a channel. Use this to get someone's attention or involve them in a discussion.",
            "parameters": {
                "type": "object",
                "properties": {
                    "user_id": {
                        "type": "string",
                        "description": "Discord user ID to mention"
                    },
                    "message": {
                        "type": "string",
                        "description": "Message content to send with the mention"
                    },
                    "channel_id": {
                        "type": "string",
                        "description": "Channel ID to send the message in"
                    }
                },
                "required": ["user_id", "message", "channel_id"]
            }
        },
        {
            "name": "search_messages",
            "description": "Search for messages containing specific text across channels. Useful for finding past discussions, decisions, or references.",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "Text to search for in messages"
                    },
                    "channel_id": {
                        "type": "string",
                        "description": "Specific channel to search in (optional)"
                    },
                    "limit": {
                        "type": "integer",
                        "description": "Number of results to return",
                        "default": 25
                    }
                },
                "required": ["query"]
            }
        },
        {
            "name": "get_user_info",
            "description": "Get detailed information about a specific user, including roles and status.",
            "parameters": {
                "type": "object",
                "properties": {
                    "user_id": {
                        "type": "string",
                        "description": "Discord user ID to get information about"
                    }
                },
                "required": ["user_id"]
            }
        },
        {
            "name": "list_channels",
            "description": "List all channels in the server. Useful for navigation and understanding server structure.",
            "parameters": {
                "type": "object",
                "properties": {
                    "guild_id": {
                        "type": "string",
                        "description": "Discord server/guild ID (optional)"
                    },
                    "channel_type": {
                        "type": "string",
                        "description": "Filter by channel type: 'text', 'voice', or 'category'",
                        "enum": ["text", "voice", "category"]
                    }
                },
                "required": []
            }
        }
    ]