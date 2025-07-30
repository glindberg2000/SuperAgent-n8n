#!/usr/bin/env python3
"""
Test Discord MCP Tools
======================

Test Discord MCP server functionality to see what server info,
channels, messages, and users we can retrieve.
"""

import os
import asyncio
import logging
import sys
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Add src to path
sys.path.append(str(Path(__file__).parent / "src"))

from mcp_servers.discord import DiscordMCPServer

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class DiscordMCPTester:
    """Test Discord MCP server functionality"""
    
    def __init__(self):
        self.server = None
        self.test_results = {}
    
    async def run_tests(self):
        """Run Discord MCP tests"""
        logger.info("🔍 Testing Discord MCP Tools...")
        
        # Check for Discord token
        discord_token = os.getenv('DISCORD_TOKEN_GROK4') or os.getenv('DISCORD_TOKEN')
        if not discord_token:
            logger.error("❌ No Discord token found. Set DISCORD_TOKEN_GROK4 or DISCORD_TOKEN")
            return
        
        server_id = os.getenv('DEFAULT_SERVER_ID')
        if not server_id:
            logger.warning("⚠️ No DEFAULT_SERVER_ID set, will use first available server")
        
        try:
            # Create Discord MCP server instance
            self.server = DiscordMCPServer(
                discord_token=discord_token,
                server_id=server_id,
                port=8099  # Use test port
            )
            
            # Start Discord bot (but not WebSocket server for testing)
            logger.info("🤖 Starting Discord bot...")
            
            async def run_bot():
                await self.server.bot.start(discord_token)
            
            # Start bot and wait for ready
            bot_task = asyncio.create_task(run_bot())
            
            # Give bot time to connect
            await asyncio.sleep(3)
            
            if self.server.bot.is_ready():
                logger.info("✅ Discord bot is ready!")
                
                # Run tests
                await self.test_bot_info()
                await self.test_guilds_and_channels()
                await self.test_channel_operations()
                await self.test_user_operations()
            else:
                logger.warning("⚠️ Bot not ready, waiting longer...")
                await asyncio.sleep(5)
                if self.server.bot.is_ready():
                    logger.info("✅ Discord bot is ready!")
                    await self.test_bot_info()
                    await self.test_guilds_and_channels()
                    await self.test_channel_operations()
                    await self.test_user_operations()
                else:
                    logger.error("❌ Bot failed to become ready")
            
            # Cleanup
            if not self.server.bot.is_closed():
                await self.server.bot.close()
            
            # Cancel bot task
            if not bot_task.done():
                bot_task.cancel()
                try:
                    await bot_task
                except asyncio.CancelledError:
                    pass
            
        except Exception as e:
            logger.error(f"❌ Test failed: {e}")
            if self.server and self.server.bot:
                await self.server.bot.close()
    
    async def test_bot_info(self):
        """Test basic bot information"""
        try:
            bot = self.server.bot
            logger.info(f"🤖 Bot User: {bot.user}")
            logger.info(f"🤖 Bot ID: {bot.user.id}")
            logger.info(f"🤖 Bot Discriminator: {bot.user.discriminator}")
            logger.info(f"🤖 Bot Guilds Count: {len(bot.guilds)}")
            
            self.test_results["bot_info"] = {
                "user": str(bot.user),
                "id": str(bot.user.id),
                "guild_count": len(bot.guilds)
            }
            
        except Exception as e:
            logger.error(f"❌ Bot info test failed: {e}")
    
    async def test_guilds_and_channels(self):
        """Test guild and channel listing"""
        try:
            bot = self.server.bot
            
            for guild in bot.guilds:
                logger.info(f"🏠 Guild: {guild.name} (ID: {guild.id})")
                logger.info(f"   Members: {guild.member_count}")
                
                # Test list_channels functionality
                result = await self.server.list_channels(str(guild.id))
                if result.get("success"):
                    channels = result.get("channels", [])
                    logger.info(f"   📋 Channels found: {len(channels)}")
                    
                    # Show first few channels
                    for channel in channels[:5]:
                        logger.info(f"      #{channel['name']} ({channel['type']}) - ID: {channel['id']}")
                    
                    if len(channels) > 5:
                        logger.info(f"      ... and {len(channels) - 5} more channels")
                    
                    self.test_results["channels"] = {
                        "guild": guild.name,
                        "total_channels": len(channels),
                        "sample_channels": channels[:3]
                    }
                else:
                    logger.error(f"   ❌ Failed to list channels: {result.get('error')}")
                
                break  # Test first guild only
                
        except Exception as e:
            logger.error(f"❌ Guilds and channels test failed: {e}")
    
    async def test_channel_operations(self):
        """Test channel-specific operations"""
        try:
            bot = self.server.bot
            
            # Find a text channel to test
            test_channel = None
            for guild in bot.guilds:
                for channel in guild.text_channels:
                    if channel.permissions_for(guild.me).read_message_history:
                        test_channel = channel
                        break
                if test_channel:
                    break
            
            if not test_channel:
                logger.warning("⚠️ No accessible text channel found for testing")
                return
            
            logger.info(f"📝 Testing channel operations in #{test_channel.name}")
            
            # Test get_channel_history
            history_result = await self.server.get_channel_history(
                str(test_channel.id), 
                limit=5
            )
            
            if history_result.get("success"):
                messages = history_result.get("messages", [])
                logger.info(f"   📜 Retrieved {len(messages)} recent messages")
                
                for msg in messages:
                    author = msg.get("author", {})
                    content = msg.get("content", "")[:50]  # First 50 chars
                    logger.info(f"      {author.get('username', 'Unknown')}: {content}...")
                
                self.test_results["channel_history"] = {
                    "channel": test_channel.name,
                    "messages_retrieved": len(messages),
                    "sample_message": messages[0] if messages else None
                }
            else:
                logger.error(f"   ❌ Failed to get channel history: {history_result.get('error')}")
            
            # Test get_channel_members
            members_result = await self.server.get_channel_members(str(test_channel.id))
            
            if members_result.get("success"):
                members = members_result.get("members", [])
                logger.info(f"   👥 Channel has {len(members)} accessible members")
                
                # Show first few members
                for member in members[:3]:
                    status = member.get("status", "unknown")
                    logger.info(f"      {member.get('display_name', 'Unknown')} ({status})")
                
                self.test_results["channel_members"] = {
                    "channel": test_channel.name,
                    "member_count": len(members),
                    "sample_members": members[:3]
                }
            else:
                logger.error(f"   ❌ Failed to get channel members: {members_result.get('error')}")
                
        except Exception as e:
            logger.error(f"❌ Channel operations test failed: {e}")
    
    async def test_user_operations(self):
        """Test user-specific operations"""
        try:
            bot = self.server.bot
            
            # Test get_online_users
            online_result = await self.server.get_online_users()
            
            if online_result.get("success"):
                online_users = online_result.get("online_users", [])
                logger.info(f"👥 Found {len(online_users)} online users")
                
                # Show first few online users
                for user in online_users[:5]:
                    activity = user.get("activity")
                    activity_str = f" (Playing: {activity})" if activity else ""
                    logger.info(f"   🟢 {user.get('display_name', 'Unknown')} - {user.get('status', 'unknown')}{activity_str}")
                
                self.test_results["online_users"] = {
                    "total_online": len(online_users),
                    "sample_users": online_users[:3]
                }
            else:
                logger.error(f"❌ Failed to get online users: {online_result.get('error')}")
            
            # Test get_user_info for bot itself
            if bot.user:
                user_info_result = await self.server.get_user_info(str(bot.user.id))
                
                if user_info_result.get("success"):
                    user_info = user_info_result.get("user", {})
                    mutual_guilds = user_info.get("mutual_guilds", [])
                    logger.info(f"🤖 Bot is in {len(mutual_guilds)} mutual guilds")
                    
                    self.test_results["user_info"] = {
                        "bot_user": user_info.get("username"),
                        "mutual_guilds": len(mutual_guilds)
                    }
                else:
                    logger.error(f"❌ Failed to get user info: {user_info_result.get('error')}")
                    
        except Exception as e:
            logger.error(f"❌ User operations test failed: {e}")
    
    def print_summary(self):
        """Print test summary"""
        logger.info("\n" + "="*60)
        logger.info("🔍 DISCORD MCP TEST SUMMARY")
        logger.info("="*60)
        
        for test_name, results in self.test_results.items():
            logger.info(f"✅ {test_name.upper()}:")
            if isinstance(results, dict):
                for key, value in results.items():
                    logger.info(f"   {key}: {value}")
            else:
                logger.info(f"   {results}")
            logger.info("")
        
        logger.info("="*60)
        logger.info("🎯 READY FOR GROK TESTING!")
        logger.info("You can now ask Grok via Discord what he sees.")
        logger.info("="*60)


async def main():
    """Run Discord MCP tests"""
    tester = DiscordMCPTester()
    await tester.run_tests()
    tester.print_summary()


if __name__ == "__main__":
    asyncio.run(main())