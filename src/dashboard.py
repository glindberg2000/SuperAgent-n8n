#!/usr/bin/env python3
"""
BotForge Dashboard
==================

Web interface for managing Discord bots, viewing configurations, and monitoring status.
"""

import os
import json
import yaml
import docker
import requests
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

def get_system_health():
    """Get comprehensive system health information"""
    health = {
        'database': {'status': 'unknown', 'details': {}},
        'redis': {'status': 'unknown', 'details': {}},
        'api_server': {'status': 'unknown', 'details': {}},
        'docker_containers': {'status': 'unknown', 'details': {}},
        'discord_bots': {'status': 'unknown', 'details': {}},
        'mcp_tools': {'status': 'unknown', 'details': {}},
        'memory_system': {'status': 'unknown', 'details': {}}
    }

    # Check PostgreSQL Database
    try:
        with get_db_connection() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                # Test connection and get stats
                cur.execute("SELECT version()")
                version = cur.fetchone()['version']

                cur.execute("SELECT COUNT(*) as total FROM discord_messages")
                message_count = cur.fetchone()['total']

                cur.execute("SELECT COUNT(DISTINCT user_id) as users FROM discord_messages WHERE user_id IS NOT NULL")
                user_count = cur.fetchone()['users']

                cur.execute("SELECT COUNT(DISTINCT bot_name) as bots FROM discord_messages WHERE bot_name IS NOT NULL")
                bot_count = cur.fetchone()['bots']

                # Check if vector extension exists
                cur.execute("SELECT EXISTS(SELECT 1 FROM pg_extension WHERE extname = 'vector')")
                has_vector = cur.fetchone()['exists']

                health['database'] = {
                    'status': 'healthy',
                    'details': {
                        'version': version.split(' ')[1],
                        'total_messages': message_count,
                        'unique_users': user_count,
                        'active_bots': bot_count,
                        'vector_enabled': has_vector,
                        'connection_pool': 'active'
                    }
                }
    except Exception as e:
        health['database'] = {
            'status': 'error',
            'details': {'error': str(e)}
        }

    # Check Docker containers
    try:
        client = docker.from_env()
        containers = client.containers.list(all=True)

        container_status = {}
        for container in containers:
            if 'superagent' in container.name or 'botforge' in container.name:
                # Safely extract creation time
                created_time = 'Unknown'
                try:
                    created_raw = container.attrs.get('Created', '')
                    if created_raw:
                        created_time = created_raw[:19]  # Just the date/time part
                except:
                    pass

                container_status[container.name] = {
                    'status': container.status,
                    'image': container.image.tags[0] if container.image.tags else 'unknown',
                    'created': created_time,
                    'ports': str(container.ports) if container.ports else 'None'
                }

        health['docker_containers'] = {
            'status': 'healthy' if container_status else 'warning',
            'details': container_status
        }
    except Exception as e:
        health['docker_containers'] = {
            'status': 'error',
            'details': {'error': str(e)}
        }

    # Check API Server
    try:
        response = requests.get('http://localhost:5001/health', timeout=5)
        if response.status_code == 200:
            health['api_server'] = {
                'status': 'healthy',
                'details': {
                    'response_time': f"{response.elapsed.total_seconds():.3f}s",
                    'endpoint': 'http://localhost:5001'
                }
            }
        else:
            health['api_server'] = {
                'status': 'warning',
                'details': {'status_code': response.status_code}
            }
    except Exception as e:
        health['api_server'] = {
            'status': 'error',
            'details': {'error': str(e)}
        }

    # Check MCP Tools availability
    try:
        # Check if discord bot has MCP tools loaded
        bot_configs = load_bot_configs()
        mcp_tools_status = {}

        for bot_id, config in bot_configs.get('bots', {}).items():
            if config.get('enabled', False):
                # Simulate MCP tool check - in reality would check the bot's tool registry
                mcp_tools_status[bot_id] = {
                    'tools_loaded': ['list_channels', 'get_channel_history', 'get_server_info', 'get_online_users', 'search_messages'],
                    'tool_count': 5,
                    'last_check': datetime.utcnow().isoformat()
                }

        health['mcp_tools'] = {
            'status': 'healthy' if mcp_tools_status else 'warning',
            'details': mcp_tools_status
        }
    except Exception as e:
        health['mcp_tools'] = {
            'status': 'error',
            'details': {'error': str(e)}
        }

    # Check Memory System
    try:
        with get_db_connection() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                # Check recent conversation activity
                cur.execute("""
                    SELECT
                        COUNT(*) as total_conversations,
                        COUNT(DISTINCT channel_id) as unique_channels,
                        MAX(timestamp) as last_activity
                    FROM discord_messages
                    WHERE timestamp > NOW() - INTERVAL '24 hours'
                """)
                memory_stats = cur.fetchone()

                # Check table sizes
                cur.execute("""
                    SELECT
                        schemaname,
                        tablename,
                        attname,
                        n_distinct,
                        most_common_vals
                    FROM pg_stats
                    WHERE tablename = 'discord_messages'
                    AND attname IN ('bot_name', 'channel_id')
                    LIMIT 5
                """)
                table_stats = cur.fetchall()

                health['memory_system'] = {
                    'status': 'healthy',
                    'details': {
                        'conversations_24h': memory_stats['total_conversations'],
                        'active_channels': memory_stats['unique_channels'],
                        'last_activity': memory_stats['last_activity'].isoformat() if memory_stats['last_activity'] else None,
                        'table_stats': [dict(row) for row in table_stats]
                    }
                }
    except Exception as e:
        health['memory_system'] = {
            'status': 'error',
            'details': {'error': str(e)}
        }

    return health

def get_discord_bot_metrics():
    """Get Discord bot specific metrics"""
    try:
        with get_db_connection() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                # Bot activity metrics
                cur.execute("""
                    SELECT
                        bot_name,
                        COUNT(*) as total_responses,
                        COUNT(DISTINCT user_id) as unique_users_served,
                        COUNT(DISTINCT channel_id) as channels_active,
                        AVG(LENGTH(message_content)) as avg_response_length,
                        MAX(timestamp) as last_response
                    FROM discord_messages
                    WHERE bot_name IS NOT NULL
                    AND timestamp > NOW() - INTERVAL '7 days'
                    GROUP BY bot_name
                """)
                bot_metrics = cur.fetchall()

                # Response time analysis (if we had timing data)
                cur.execute("""
                    SELECT
                        DATE_TRUNC('hour', timestamp) as hour,
                        COUNT(*) as message_count
                    FROM discord_messages
                    WHERE timestamp > NOW() - INTERVAL '24 hours'
                    GROUP BY DATE_TRUNC('hour', timestamp)
                    ORDER BY hour DESC
                    LIMIT 24
                """)
                hourly_activity = cur.fetchall()

                return {
                    'bot_metrics': [dict(row) for row in bot_metrics],
                    'hourly_activity': [dict(row) for row in hourly_activity]
                }
    except Exception as e:
        return {'error': str(e)}

@app.route('/')
def dashboard():
    """Main dashboard page with comprehensive system monitoring"""
    bot_configs = load_bot_configs()

    # Get comprehensive system health
    system_health = get_system_health()
    bot_metrics = get_discord_bot_metrics()

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
                         stats=stats,
                         system_health=system_health,
                         bot_metrics=bot_metrics)

@app.route('/system')
def system_dashboard():
    """Comprehensive system monitoring dashboard"""
    # Get comprehensive system health
    system_health = get_system_health()
    bot_metrics = get_discord_bot_metrics()

    return render_template('system_dashboard.html',
                         system_health=system_health,
                         bot_metrics=bot_metrics)

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

@app.route('/api/system/health')
def api_system_health():
    """Get comprehensive system health status"""
    return jsonify(get_system_health())

@app.route('/api/system/metrics')
def api_system_metrics():
    """Get system performance metrics"""
    return jsonify(get_discord_bot_metrics())

@app.route('/api/system/containers')
def api_docker_containers():
    """Get Docker container status"""
    try:
        client = docker.from_env()
        containers = client.containers.list(all=True)

        container_info = []
        for container in containers:
            if 'superagent' in container.name or 'botforge' in container.name:
                container_info.append({
                    'name': container.name,
                    'status': container.status,
                    'image': container.image.tags[0] if container.image.tags else 'unknown',
                    'created': container.attrs['Created'],
                    'ports': container.ports,
                    'labels': container.labels
                })

        return jsonify({'containers': container_info})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/mcp/tools/<bot_id>')
def api_mcp_tools(bot_id):
    """Get MCP tools status for specific bot"""
    # This would normally query the actual bot for its tool registry
    # For now, return mock data based on our known tools
    tools = {
        'available_tools': [
            {'name': 'list_channels', 'description': 'List Discord channels', 'status': 'active'},
            {'name': 'get_channel_history', 'description': 'Get channel message history', 'status': 'active'},
            {'name': 'get_server_info', 'description': 'Get Discord server information', 'status': 'active'},
            {'name': 'get_online_users', 'description': 'Get online users list', 'status': 'active'},
            {'name': 'search_messages', 'description': 'Search through messages', 'status': 'active'}
        ],
        'tool_count': 5,
        'last_updated': datetime.utcnow().isoformat()
    }
    return jsonify(tools)

@app.route('/health')
def health():
    """Health check endpoint for dashboard"""
    return jsonify({'status': 'healthy'})

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=3000, debug=True)
