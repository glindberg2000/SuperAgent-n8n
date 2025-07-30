#!/usr/bin/env python3
"""
Discord Bot API Server
Handles database operations and AI processing for n8n Discord bot
"""

from flask import Flask, request, jsonify
import psycopg2
import psycopg2.extras
import requests
import json
import os
from datetime import datetime
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

app = Flask(__name__)

# Configuration
XAI_API_KEY = os.getenv('XAI_API_KEY')
DISCORD_TOKEN = os.getenv('DISCORD_TOKEN_GROK4')
PORT = int(os.getenv('PORT', '5001'))
# Handle Docker vs local development
POSTGRES_HOST = os.getenv('POSTGRES_HOST', 'localhost')
if POSTGRES_HOST == 'postgres':  # Docker container name
    POSTGRES_HOST = 'localhost'
POSTGRES_PORT = os.getenv('POSTGRES_PORT', '5432')
POSTGRES_DB = os.getenv('POSTGRES_DB', 'superagent')
POSTGRES_USER = os.getenv('POSTGRES_USER', 'superagent')
POSTGRES_PASSWORD = os.getenv('POSTGRES_PASSWORD', 'superagent_password')

def get_db_connection():
    """Get PostgreSQL database connection"""
    return psycopg2.connect(
        host=POSTGRES_HOST,
        port=POSTGRES_PORT,
        database=POSTGRES_DB,
        user=POSTGRES_USER,
        password=POSTGRES_PASSWORD
    )

def ensure_user_exists(user_id, username):
    """Ensure Discord user exists in database"""
    with get_db_connection() as conn:
        with conn.cursor() as cursor:
            cursor.execute("""
                INSERT INTO discord_users (id, username, display_name) 
                VALUES (%s, %s, %s) 
                ON CONFLICT (id) DO UPDATE SET 
                    username = EXCLUDED.username,
                    updated_at = NOW()
            """, (int(user_id), username, username))
            conn.commit()

def store_user_message(message_id, user_id, content, metadata):
    """Store user message in database"""
    with get_db_connection() as conn:
        with conn.cursor() as cursor:
            cursor.execute("""
                INSERT INTO messages (discord_message_id, user_id, content, metadata, message_type)
                VALUES (%s, %s, %s, %s, 'user')
                ON CONFLICT (discord_message_id) DO NOTHING
            """, (int(message_id), int(user_id), content, json.dumps(metadata)))
            conn.commit()

def get_conversation_history(user_id, channel_id, limit=15):
    """Get recent conversation history for user in channel"""
    with get_db_connection() as conn:
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

def store_bot_response(user_id, content, metadata):
    """Store bot response in database"""
    with get_db_connection() as conn:
        with conn.cursor() as cursor:
            cursor.execute("""
                INSERT INTO messages (user_id, content, metadata, message_type, agent_name)
                VALUES (%s, %s, %s, 'assistant', 'Grok4Agent')
            """, (int(user_id), content, json.dumps(metadata)))
            conn.commit()

def call_grok4(messages):
    """Call Grok4 API with conversation messages"""
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

def send_discord_message(channel_id, content, reply_to_message_id=None):
    """Send message to Discord channel"""
    headers = {
        'Authorization': f'Bot {DISCORD_TOKEN}',
        'Content-Type': 'application/json'
    }
    
    payload = {
        'content': content
    }
    
    # Add reply reference if provided
    if reply_to_message_id:
        payload['message_reference'] = {
            'message_id': str(reply_to_message_id)
        }
    
    url = f'https://discord.com/api/v10/channels/{channel_id}/messages'
    response = requests.post(url, headers=headers, json=payload, timeout=10)
    
    if response.status_code in [200, 201]:
        return response.json()
    else:
        raise Exception(f"Discord API error: {response.status_code} - {response.text}")

@app.route('/process_discord_message', methods=['POST'])
def process_discord_message():
    """Main endpoint to process Discord messages with memory and AI response"""
    try:
        request_data = request.get_json()
        
        # n8n sends Discord data in the 'body' field
        if 'body' in request_data and 'id' in request_data['body']:
            data = request_data['body']
        else:
            data = request_data
        
        print(f"Received data: {json.dumps(data, indent=2)}")
        
        # Extract message data
        message_id = data.get('id')
        content = data.get('content', '')
        channel_id = data.get('channel_id')
        reply_to_id = data.get('reply_to_message_id')
        author = data.get('author', {})
        user_id = author.get('id')
        username = author.get('username')
        
        # Validate required fields
        if not message_id or not user_id or not username:
            raise ValueError(f"Missing required fields: message_id={message_id}, user_id={user_id}, username={username}")
        
        # Ensure IDs are strings for int conversion
        message_id = str(message_id)
        user_id = str(user_id)
        channel_id = str(channel_id)
        
        # Clean content (remove mentions)
        import re
        clean_content = re.sub(r'<@!?\d+>', '', content)
        clean_content = re.sub(r'<@&\d+>', '', clean_content).strip()
        
        print(f"Processing message from {username}: {clean_content[:50]}...")
        
        # Step 1: Ensure user exists
        ensure_user_exists(user_id, username)
        
        # Step 2: Get conversation history BEFORE storing current message
        # This prevents the current message from appearing in the context
        history = get_conversation_history(user_id, channel_id, limit=15)
        
        # Step 3: Store user message AFTER getting history
        message_metadata = {
            'channelId': channel_id,
            'replyToId': reply_to_id,
            'originalContent': content
        }
        store_user_message(message_id, user_id, clean_content, message_metadata)
        
        # Step 4: Build conversation context
        conversation_messages = []
        
        # Add system prompt
        is_reply = reply_to_id is not None
        reply_context = ' You are replying to a previous message in this conversation thread.' if is_reply else ''
        
        conversation_messages.append({
            'role': 'system',
            'content': f'You are Grok4Agent, a helpful Discord bot powered by Grok-4. You have memory of previous conversations with {username} in this channel.{reply_context} Be conversational, insightful, and engaging. Reference previous context when relevant.'
        })
        
        # Add conversation history (reverse chronological order)
        for msg in reversed(history):
            role = 'user' if msg['message_type'] == 'user' else 'assistant'
            conversation_messages.append({
                'role': role,
                'content': msg['content']
            })
        
        # Add current message (check for duplicates first)
        current_message_content = clean_content
        if not conversation_messages or conversation_messages[-1]['content'] != current_message_content:
            conversation_messages.append({
                'role': 'user',
                'content': current_message_content
            })
        
        # Limit context to prevent token overflow
        if len(conversation_messages) > 25:
            # Keep system message and last 24 messages
            conversation_messages = [conversation_messages[0]] + conversation_messages[-24:]
        
        print(f"Built context with {len(conversation_messages)} messages")
        
        # Show conversation history for debugging
        print("Conversation context being sent to Grok4:")
        for i, msg in enumerate(conversation_messages[-3:]):  # Show last 3 messages
            role = msg['role']
            content = msg['content'][:100] + '...' if len(msg['content']) > 100 else msg['content']
            print(f"  {i}: [{role}] {content}")
        
        # Step 5: Call Grok4 API
        try:
            grok_response = call_grok4(conversation_messages)
            bot_content = grok_response['choices'][0]['message']['content']
        except requests.exceptions.ReadTimeout:
            print("Grok4 API timeout - using fallback response")
            bot_content = "I'm experiencing a brief connection delay. Could you repeat that? I'm here and ready to help! 🤖"
        except Exception as e:
            print(f"Grok4 API error: {e}")
            bot_content = "I'm having a technical moment. Please try again in a few seconds! 🔧"
        
        print(f"Grok4 response: {bot_content[:100]}...")
        
        # Step 6: Store bot response
        response_metadata = {
            'channelId': channel_id,
            'model': 'grok-4-latest',
            'isReply': is_reply,
            'conversationLength': len(conversation_messages)
        }
        store_bot_response(user_id, bot_content, response_metadata)
        
        # Step 7: Send to Discord
        discord_response = send_discord_message(channel_id, bot_content, reply_to_id)
        
        return jsonify({
            'success': True,
            'bot_message_id': discord_response.get('id'),
            'conversation_length': len(conversation_messages),
            'is_reply': is_reply,
            'processed_at': datetime.now().isoformat()
        })
        
    except Exception as e:
        print(f"Error processing message: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/health', methods=['GET'])
def health_check():
    """Health check endpoint"""
    try:
        # Test database connection
        with get_db_connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute('SELECT 1')
        
        return jsonify({
            'status': 'healthy',
            'database': 'connected',
            'timestamp': datetime.now().isoformat()
        })
    except Exception as e:
        return jsonify({
            'status': 'unhealthy',
            'error': str(e)
        }), 500

if __name__ == '__main__':
    print("Starting Discord API Server...")
    print(f"Grok4 API configured: {'✅' if XAI_API_KEY else '❌'}")
    print(f"Discord token configured: {'✅' if DISCORD_TOKEN else '❌'}")
    print(f"Database: {POSTGRES_HOST}:{POSTGRES_PORT}/{POSTGRES_DB}")
    print(f"Server will start on port: {PORT}")
    
    app.run(host='0.0.0.0', port=PORT, debug=True)