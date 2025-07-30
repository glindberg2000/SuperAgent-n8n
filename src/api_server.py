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

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('/app/logs/api_server.log'),
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
    
    async def get_response(self, provider: str, model: str, messages: List[Dict], personality: str) -> str:
        """Get response from specified AI provider"""
        try:
            if provider == 'openai':
                return await self._call_openai(model, messages, personality)
            elif provider == 'anthropic':
                return await self._call_anthropic(model, messages, personality)
            elif provider == 'xai':
                return await self._call_xai(model, messages, personality)
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
    
    async def _call_xai(self, model: str, messages: List[Dict], personality: str) -> str:
        """Call X.AI/Grok API"""
        try:
            # Add personality as system message
            full_messages = [{"role": "system", "content": personality}] + messages
            
            response = requests.post(
                "https://api.x.ai/v1/chat/completions",
                headers={
                    "Authorization": f"Bearer {os.getenv('XAI_API_KEY')}",
                    "Content-Type": "application/json"
                },
                json={
                    "messages": full_messages,
                    "model": model,
                    "stream": False,
                    "temperature": 0.7,
                    "max_tokens": 1500
                },
                timeout=30
            )
            
            if response.status_code == 200:
                result = response.json()
                return result['choices'][0]['message']['content'].strip()
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
        with open('/app/config/bots.yaml', 'r') as f:
            return yaml.safe_load(f)
    except Exception as e:
        logger.error(f"Failed to load bot config: {e}")
        return {'bots': {}}

# Initialize managers
ai_manager = AIProviderManager()
db_manager = DatabaseManager()

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
        
        # Get conversation history
        max_context = bot_config.get('max_context_messages', 10)
        history = db_manager.get_conversation_history(
            webhook_data['bot_name'],
            webhook_data['channel_id'],
            webhook_data['user_id'],
            max_context
        )
        
        # Add current message to history
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
            ai_response = loop.run_until_complete(ai_manager.get_response(
                provider=bot_config['llm_provider'],
                model=bot_config['llm_model'],
                messages=messages,
                personality=bot_config.get('personality', 'You are a helpful AI assistant.')
            ))
        finally:
            loop.close()
        
        # Store AI response
        response_data = webhook_data.copy()
        response_data.update({
            'message_content': ai_response,
            'username': webhook_data['bot_name'],
            'user_id': 'bot',
            'timestamp': datetime.utcnow().isoformat()
        })
        db_manager.store_message(response_data)
        
        logger.info(f"✅ Generated response for {webhook_data.get('username')}")
        
        return jsonify({
            'success': True,
            'response': ai_response,
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