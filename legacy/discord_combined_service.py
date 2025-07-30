#!/usr/bin/env python3
"""
SuperAgent n8n - Combined Discord Bot + API Server
Single service that handles Discord events AND API processing
"""

import asyncio
import discord
import aiohttp
import json
import os
import threading
import time
from datetime import datetime
from dotenv import load_dotenv
from flask import Flask, request, jsonify
import psycopg2
import psycopg2.extras
import requests

# Load environment variables
load_dotenv()

# Configuration
DISCORD_TOKEN = os.getenv('DISCORD_TOKEN_GROK4')
XAI_API_KEY = os.getenv('XAI_API_KEY')
N8N_WEBHOOK_URL = os.getenv('N8N_WEBHOOK_URL', 'http://n8n:5678/webhook/grok4-python-api')

# Database configuration (Docker internal networking)
POSTGRES_HOST = os.getenv('POSTGRES_HOST', 'postgres')
POSTGRES_PORT = os.getenv('POSTGRES_PORT', '5432')
POSTGRES_DB = os.getenv('POSTGRES_DB', 'superagent')
POSTGRES_USER = os.getenv('POSTGRES_USER', 'superagent')
POSTGRES_PASSWORD = os.getenv('POSTGRES_PASSWORD', 'superagent-db-2025')

# Flask app for API endpoints
app = Flask(__name__)

# Discord client
intents = discord.Intents.default()
intents.message_content = True
intents.messages = True

class SuperAgentBot:
    def __init__(self):
        self.discord_client = discord.Client(intents=intents)
        self.setup_discord_events()
        
    def setup_discord_events(self):
        @self.discord_client.event
        async def on_ready():
            print(f'🤖 Discord Bot logged in as {self.discord_client.user} (ID: {self.discord_client.user.id})')
            print(f'📡 Connected to {len(self.discord_client.guilds)} Discord servers')
            
        @self.discord_client.event
        async def on_message(message):
            await self.handle_discord_message(message)
    
    async def handle_discord_message(self, message):
        """Handle Discord messages and process with AI"""
        try:
            # Don't respond to own messages
            if message.author.id == self.discord_client.user.id:
                return
            
            # Check if bot should respond
            bot_mentioned = any(mention.id == self.discord_client.user.id for mention in message.mentions)
            contains_grok = 'grok' in message.content.lower()
            role_mentioned = bool(message.role_mentions) or '<@&' in message.content
            
            if not (bot_mentioned or contains_grok or role_mentioned):
                return
            
            print(f"📨 Processing message from {message.author}: {message.content[:50]}...")
            
            # Process message directly (no n8n needed!)
            response = await self.process_message_with_ai(message)
            
            if response:
                # Send response to Discord
                if message.reference:  # Reply to a message
                    await message.reply(response)
                else:
                    await message.channel.send(response)
                    
                print(f"✅ Sent response to {message.author}")
                
        except Exception as e:
            print(f"❌ Error handling Discord message: {e}")
            try:
                await message.channel.send("I'm experiencing a technical issue. Please try again! 🔧")
            except:
                pass
    
    async def process_message_with_ai(self, message):
        """Process message with full AI pipeline"""
        try:
            # Extract data
            user_id = str(message.author.id)
            username = message.author.name
            channel_id = str(message.channel.id)
            content = message.content
            message_id = str(message.id)
            reply_to_id = str(message.reference.message_id) if message.reference else None
            
            # Clean content
            import re
            clean_content = re.sub(r'<@!?\d+>', '', content)
            clean_content = re.sub(r'<@&\d+>', '', clean_content).strip()
            
            # Database operations
            self.ensure_user_exists(user_id, username)
            
            # Get conversation history BEFORE storing current message
            history = self.get_conversation_history(user_id, channel_id, limit=15)
            
            # Store current message
            metadata = {
                'channelId': channel_id,
                'replyToId': reply_to_id,
                'originalContent': content
            }
            self.store_user_message(message_id, user_id, clean_content, metadata)
            
            # Build conversation context
            conversation_messages = [{
                'role': 'system',
                'content': f'You are Grok4Agent, a helpful Discord bot powered by Grok-4. You have memory of previous conversations with {username} in this channel. Be conversational, insightful, and engaging. Reference previous context when relevant.'
            }]
            
            # Add history (reverse chronological order)
            for msg in reversed(history):
                role = 'user' if msg['message_type'] == 'user' else 'assistant'
                conversation_messages.append({
                    'role': role,
                    'content': msg['content']
                })
            
            # Add current message
            conversation_messages.append({
                'role': 'user',
                'content': clean_content
            })
            
            # Limit context
            if len(conversation_messages) > 25:
                conversation_messages = [conversation_messages[0]] + conversation_messages[-24:]
            
            print(f"🧠 Built context with {len(conversation_messages)} messages")
            
            # Call Grok4 API
            try:
                grok_response = self.call_grok4(conversation_messages)
                bot_content = grok_response['choices'][0]['message']['content']
            except requests.exceptions.ReadTimeout:
                bot_content = "I'm experiencing a brief connection delay. Could you repeat that? I'm here and ready to help! 🤖"
            except Exception as e:
                print(f"Grok4 API error: {e}")
                bot_content = "I'm having a technical moment. Please try again in a few seconds! 🔧"
            
            # Store bot response
            response_metadata = {
                'channelId': channel_id,
                'model': 'grok-4-latest',
                'isReply': reply_to_id is not None
            }
            self.store_bot_response(user_id, bot_content, response_metadata)
            
            return bot_content
            
        except Exception as e:
            print(f"❌ Error processing message with AI: {e}")
            return "I encountered an error processing your message. Please try again! 🔧"

    def get_db_connection(self):
        """Get database connection"""
        return psycopg2.connect(
            host=POSTGRES_HOST,
            port=POSTGRES_PORT,
            database=POSTGRES_DB,
            user=POSTGRES_USER,
            password=POSTGRES_PASSWORD
        )
    
    def ensure_user_exists(self, user_id, username):
        """Ensure user exists in database"""
        with self.get_db_connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute("""
                    INSERT INTO discord_users (id, username, display_name) 
                    VALUES (%s, %s, %s) 
                    ON CONFLICT (id) DO UPDATE SET 
                        username = EXCLUDED.username,
                        updated_at = NOW()
                """, (int(user_id), username, username))
                conn.commit()
    
    def store_user_message(self, message_id, user_id, content, metadata):
        """Store user message"""
        with self.get_db_connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute("""
                    INSERT INTO messages (discord_message_id, user_id, content, metadata, message_type)
                    VALUES (%s, %s, %s, %s, 'user')
                    ON CONFLICT (discord_message_id) DO NOTHING
                """, (int(message_id), int(user_id), content, json.dumps(metadata)))
                conn.commit()
    
    def get_conversation_history(self, user_id, channel_id, limit=15):
        """Get conversation history"""
        with self.get_db_connection() as conn:
            with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cursor:
                cursor.execute("""
                    SELECT content, message_type, created_at, agent_name
                    FROM messages 
                    WHERE user_id = %s 
                      AND (metadata->>'channelId')::TEXT = %s
                    ORDER BY created_at DESC 
                    LIMIT %s
                """, (int(user_id), str(channel_id), limit))
                return cursor.fetchall()
    
    def store_bot_response(self, user_id, content, metadata):
        """Store bot response"""
        with self.get_db_connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute("""
                    INSERT INTO messages (user_id, content, metadata, message_type, agent_name)
                    VALUES (%s, %s, %s, 'assistant', 'Grok4Agent')
                """, (int(user_id), content, json.dumps(metadata)))
                conn.commit()
    
    def call_grok4(self, messages):
        """Call Grok4 API"""
        headers = {
            'Authorization': f'Bearer {XAI_API_KEY}',
            'Content-Type': 'application/json'
        }
        
        payload = {
            'model': 'grok-4-latest',
            'messages': messages,
            'max_tokens': 1500,
            'temperature': 0.7
        }
        
        response = requests.post(
            'https://api.x.ai/v1/chat/completions',
            headers=headers,
            json=payload,
            timeout=30
        )
        
        if response.status_code == 200:
            return response.json()
        else:
            raise Exception(f"Grok4 API error: {response.status_code} - {response.text}")

    async def start_discord_bot(self):
        """Start Discord bot"""
        await self.discord_client.start(DISCORD_TOKEN)

# Flask API endpoints
bot_instance = SuperAgentBot()

@app.route('/health', methods=['GET'])
def health_check():
    """Health check endpoint"""
    try:
        # Test database connection
        with bot_instance.get_db_connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute('SELECT 1')
        
        # Check Discord connection
        discord_status = "connected" if bot_instance.discord_client.is_ready() else "disconnected"
        
        return jsonify({
            'status': 'healthy',
            'database': 'connected',
            'discord': discord_status,
            'timestamp': datetime.now().isoformat()
        })
    except Exception as e:
        return jsonify({
            'status': 'unhealthy',
            'error': str(e)
        }), 500

@app.route('/stats', methods=['GET'])
def get_stats():
    """Get bot statistics"""
    try:
        with bot_instance.get_db_connection() as conn:
            with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cursor:
                # Get user count
                cursor.execute("SELECT COUNT(*) as user_count FROM discord_users")
                user_count = cursor.fetchone()['user_count']
                
                # Get message count
                cursor.execute("SELECT COUNT(*) as message_count FROM messages")
                message_count = cursor.fetchone()['message_count']
                
                # Get recent activity
                cursor.execute("""
                    SELECT COUNT(*) as recent_messages 
                    FROM messages 
                    WHERE created_at > NOW() - INTERVAL '24 hours'
                """)
                recent_messages = cursor.fetchone()['recent_messages']
        
        return jsonify({
            'users': user_count,
            'total_messages': message_count,
            'messages_24h': recent_messages,
            'discord_servers': len(bot_instance.discord_client.guilds) if bot_instance.discord_client.is_ready() else 0,
            'timestamp': datetime.now().isoformat()
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

def run_flask_app():
    """Run Flask app in separate thread"""
    app.run(host='0.0.0.0', port=5001, debug=False)

def run_discord_bot():
    """Run Discord bot"""
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    loop.run_until_complete(bot_instance.start_discord_bot())

def main():
    """Main entry point"""
    print("🚀 Starting SuperAgent n8n Combined Service")
    print(f"✅ Discord token configured: {'✅' if DISCORD_TOKEN else '❌'}")
    print(f"✅ Grok4 API configured: {'✅' if XAI_API_KEY else '❌'}")
    print(f"✅ Database: {POSTGRES_HOST}:{POSTGRES_PORT}/{POSTGRES_DB}")
    
    # Wait for database to be ready
    print("⏳ Waiting for database connection...")
    for i in range(30):
        try:
            with bot_instance.get_db_connection() as conn:
                with conn.cursor() as cursor:
                    cursor.execute('SELECT 1')
            print("✅ Database connected!")
            break
        except:
            time.sleep(2)
    else:
        print("❌ Database connection failed after 60 seconds")
        return
    
    # Start Flask API in background thread
    flask_thread = threading.Thread(target=run_flask_app, daemon=True)
    flask_thread.start()
    print("✅ API server started on port 5001")
    
    # Start Discord bot (main thread)
    print("✅ Starting Discord bot...")
    try:
        run_discord_bot()
    except KeyboardInterrupt:
        print("🛑 Shutting down SuperAgent...")

if __name__ == '__main__':
    main()