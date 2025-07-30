#!/usr/bin/env python3
"""
BotForge Dashboard
==================

Web interface for managing Discord bots, viewing configurations, and monitoring status.
"""

import os
import json
import yaml
from datetime import datetime
from flask import Flask, render_template, request, jsonify, redirect, url_for
import psycopg2
from psycopg2.extras import RealDictCursor

app = Flask(__name__, template_folder='./templates', static_folder='./static')

# Database configuration
DB_CONFIG = {
    'host': os.getenv('POSTGRES_HOST', 'postgres'),
    'port': int(os.getenv('POSTGRES_PORT', 5432)),
    'database': os.getenv('POSTGRES_DB', 'botforge'),
    'user': os.getenv('POSTGRES_USER', 'botforge'),
    'password': os.getenv('POSTGRES_PASSWORD', 'botforge-db-2025')
}

def get_db_connection():
    """Get database connection"""
    return psycopg2.connect(**DB_CONFIG)

def load_bot_configs():
    """Load bot configurations from YAML"""
    try:
        with open('./config/bots.yaml', 'r') as f:
            return yaml.safe_load(f)
    except Exception as e:
        print(f"Error loading bot config: {e}")
        return {'bots': {}}

def save_bot_configs(config):
    """Save bot configurations to YAML"""
    try:
        # Ensure config directory exists
        import os
        os.makedirs('./config', exist_ok=True)
        
        with open('./config/bots.yaml', 'w') as f:
            yaml.dump(config, f, default_flow_style=False, indent=2)
        print(f"✅ Successfully saved bot configuration")
        return True
    except Exception as e:
        print(f"❌ Error saving bot config: {e}")
        import traceback
        traceback.print_exc()
        return False

def update_env_variable(var_name, var_value):
    """Update environment variable in .env file"""
    try:
        env_file_path = './.env'
        
        # Read current .env file
        env_lines = []
        if os.path.exists(env_file_path):
            with open(env_file_path, 'r') as f:
                env_lines = f.readlines()
        
        # Find and update the variable
        updated = False
        for i, line in enumerate(env_lines):
            if line.strip() and not line.strip().startswith('#'):
                if '=' in line:
                    current_var = line.split('=')[0].strip()
                    if current_var == var_name:
                        env_lines[i] = f"{var_name}={var_value}\n"
                        updated = True
                        break
        
        # If variable wasn't found, add it
        if not updated:
            env_lines.append(f"{var_name}={var_value}\n")
        
        # Write back to .env file
        with open(env_file_path, 'w') as f:
            f.writelines(env_lines)
        
        # Update current environment
        os.environ[var_name] = var_value
        
        print(f"✅ Successfully updated environment variable: {var_name}")
        return True
    except Exception as e:
        print(f"❌ Error updating environment variable {var_name}: {e}")
        import traceback
        traceback.print_exc()
        return False

@app.route('/')
def dashboard():
    """Main dashboard page"""
    bot_configs = load_bot_configs()
    
    # Get bot statistics from database
    stats = {}
    try:
        with get_db_connection() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                # Get message counts by bot
                cur.execute("""
                    SELECT bot_name, COUNT(*) as message_count,
                           MAX(timestamp) as last_message
                    FROM discord_messages 
                    WHERE bot_name IS NOT NULL
                    GROUP BY bot_name
                """)
                for row in cur.fetchall():
                    stats[row['bot_name']] = {
                        'message_count': row['message_count'],
                        'last_message': row['last_message']
                    }
    except Exception as e:
        print(f"Database error: {e}")
    
    return render_template('dashboard.html', 
                         bots=bot_configs['bots'], 
                         stats=stats)

@app.route('/bot/<bot_id>')
def bot_detail(bot_id):
    """Bot configuration detail page"""
    bot_configs = load_bot_configs()
    bot_config = bot_configs['bots'].get(bot_id)
    
    if not bot_config:
        return "Bot not found", 404
    
    # Get environment variable values
    env_values = {}
    if bot_config.get('discord_token_env'):
        token_value = os.getenv(bot_config['discord_token_env'])
        if token_value:
            # Show first 10 and last 10 characters with *** in between for security
            env_values[bot_config['discord_token_env']] = f"{token_value[:10]}***{token_value[-10:]}" if len(token_value) > 20 else token_value
        else:
            env_values[bot_config['discord_token_env']] = "Not set"
    
    if bot_config.get('api_key_env'):
        api_key_value = os.getenv(bot_config['api_key_env'])
        if api_key_value:
            # Show first 8 characters for API keys
            env_values[bot_config['api_key_env']] = f"{api_key_value[:8]}***" if len(api_key_value) > 8 else api_key_value
        else:
            env_values[bot_config['api_key_env']] = "Not set"
    
    # Get recent messages for this bot
    recent_messages = []
    try:
        with get_db_connection() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute("""
                    SELECT username, message_content, timestamp, channel_id
                    FROM discord_messages 
                    WHERE bot_name = %s
                    ORDER BY timestamp DESC 
                    LIMIT 50
                """, (bot_config['name'],))
                recent_messages = cur.fetchall()
    except Exception as e:
        print(f"Database error: {e}")
    
    return render_template('bot_detail.html', 
                         bot_id=bot_id,
                         bot_config=bot_config, 
                         env_values=env_values,
                         recent_messages=recent_messages)

@app.route('/api/bot/<bot_id>/toggle', methods=['POST'])
def toggle_bot(bot_id):
    """Toggle bot enabled/disabled status"""
    bot_configs = load_bot_configs()
    
    if bot_id not in bot_configs['bots']:
        return jsonify({'error': 'Bot not found'}), 404
    
    # Toggle enabled status
    current_status = bot_configs['bots'][bot_id].get('enabled', False)
    bot_configs['bots'][bot_id]['enabled'] = not current_status
    
    if save_bot_configs(bot_configs):
        return jsonify({
            'success': True, 
            'enabled': bot_configs['bots'][bot_id]['enabled']
        })
    else:
        return jsonify({'error': 'Failed to save configuration'}), 500

@app.route('/api/bot/<bot_id>/update', methods=['POST'])
def update_bot(bot_id):
    """Update bot configuration"""
    bot_configs = load_bot_configs()
    
    if bot_id not in bot_configs['bots']:
        return jsonify({'error': 'Bot not found'}), 404
    
    data = request.json
    
    # Handle environment variable updates first
    env_updates = {}
    if 'discord_token' in data and data['discord_token']:
        token_env = bot_configs['bots'][bot_id].get('discord_token_env')
        if token_env:
            env_updates[token_env] = data['discord_token']
    
    if 'api_key' in data and data['api_key']:
        api_key_env = bot_configs['bots'][bot_id].get('api_key_env')
        if api_key_env:
            env_updates[api_key_env] = data['api_key']
    
    # Update environment variables
    for env_var, env_value in env_updates.items():
        if not update_env_variable(env_var, env_value):
            return jsonify({'error': f'Failed to update environment variable: {env_var}'}), 500
    
    # Update allowed bot config fields
    allowed_fields = [
        'name', 'personality', 'llm_provider', 'llm_model', 
        'max_context_messages', 'max_turns_per_thread', 
        'response_delay', 'trigger_words', 'enabled',
        'discord_token_env', 'api_key_env'
    ]
    
    for field in allowed_fields:
        if field in data:
            bot_configs['bots'][bot_id][field] = data[field]
    
    if save_bot_configs(bot_configs):
        return jsonify({'success': True})
    else:
        return jsonify({'error': 'Failed to save configuration'}), 500

@app.route('/api/system/status')
def system_status():
    """Get system status and statistics"""
    try:
        with get_db_connection() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                # Get total message count
                cur.execute("SELECT COUNT(*) as total_messages FROM discord_messages")
                total_messages = cur.fetchone()['total_messages']
                
                # Get unique users
                cur.execute("SELECT COUNT(DISTINCT user_id) as unique_users FROM discord_messages WHERE user_id IS NOT NULL")
                unique_users = cur.fetchone()['unique_users']
                
                # Get active bots
                cur.execute("SELECT COUNT(DISTINCT bot_name) as active_bots FROM discord_messages WHERE bot_name IS NOT NULL")
                active_bots = cur.fetchone()['active_bots']
        
        return jsonify({
            'database_connected': True,
            'total_messages': total_messages,
            'unique_users': unique_users,
            'active_bots': active_bots,
            'timestamp': datetime.utcnow().isoformat()
        })
    except Exception as e:
        return jsonify({
            'database_connected': False,
            'error': str(e),
            'timestamp': datetime.utcnow().isoformat()
        }), 500

@app.route('/logs')
def view_logs():
    """View system logs"""
    log_files = []
    logs_dir = './logs'
    
    if os.path.exists(logs_dir):
        for filename in os.listdir(logs_dir):
            if filename.endswith('.log'):
                filepath = os.path.join(logs_dir, filename)
                log_files.append({
                    'name': filename,
                    'size': os.path.getsize(filepath),
                    'modified': datetime.fromtimestamp(os.path.getmtime(filepath))
                })
    
    return render_template('logs.html', log_files=log_files)

@app.route('/api/logs/<filename>')
def get_log_content(filename):
    """Get log file content"""
    if not filename.endswith('.log'):
        return jsonify({'error': 'Invalid file type'}), 400
    
    filepath = os.path.join('./logs', filename)
    
    if not os.path.exists(filepath):
        return jsonify({'error': 'Log file not found'}), 404
    
    try:
        with open(filepath, 'r') as f:
            # Get last 500 lines
            lines = f.readlines()
            content = ''.join(lines[-500:])
        
        return jsonify({'content': content})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/health')
def health():
    """Health check endpoint for dashboard"""
    return jsonify({'status': 'healthy'})

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=3000, debug=True)