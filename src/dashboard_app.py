#!/usr/bin/env python3
"""
BotForge Dashboard Application
=============================

Flask web application for managing and monitoring BotForge bots.
Provides real-time status, configuration management, and statistics.
"""

import os
import logging
import json
import yaml
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional

import requests
from flask import Flask, render_template, jsonify, request, redirect, url_for, flash
import psycopg2
from psycopg2.extras import RealDictCursor

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('/app/logs/dashboard.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

app = Flask(__name__)
app.secret_key = os.getenv('DASHBOARD_SECRET', 'dev-secret-change-in-production')

# Configuration
API_SERVER_URL = os.getenv('API_SERVER_URL', 'http://api-server:5001')
DB_CONFIG = {
    'host': os.getenv('POSTGRES_HOST', 'postgres'),
    'port': int(os.getenv('POSTGRES_PORT', 5432)),
    'database': os.getenv('POSTGRES_DB', 'botforge'),
    'user': os.getenv('POSTGRES_USER', 'botforge'),
    'password': os.getenv('POSTGRES_PASSWORD', 'botforge-db-2025')
}

class DashboardManager:
    """Manages dashboard data and operations"""
    
    def __init__(self):
        self.api_url = API_SERVER_URL
        self.db_config = DB_CONFIG
    
    def get_db_connection(self):
        """Get database connection"""
        return psycopg2.connect(**self.db_config)
    
    def load_bot_configs(self) -> Dict[str, Any]:
        """Load bot configurations from YAML"""
        try:
            with open('/app/config/bots.yaml', 'r') as f:
                return yaml.safe_load(f)
        except Exception as e:
            logger.error(f"Failed to load bot config: {e}")
            return {'bots': {}, 'global': {}}
    
    def save_bot_configs(self, config_data: Dict[str, Any]) -> bool:
        """Save bot configurations to YAML"""
        try:
            with open('/app/config/bots.yaml', 'w') as f:
                yaml.dump(config_data, f, default_flow_style=False, indent=2)
            return True
        except Exception as e:
            logger.error(f"Failed to save bot config: {e}")
            return False
    
    def get_api_stats(self) -> Dict[str, Any]:
        """Get statistics from API server"""
        try:
            response = requests.get(f"{self.api_url}/stats", timeout=5)
            if response.status_code == 200:
                return response.json()
            else:
                return {'error': f'API returned {response.status_code}'}
        except Exception as e:
            logger.error(f"Failed to get API stats: {e}")
            return {'error': str(e)}
    
    def get_api_health(self) -> Dict[str, Any]:
        """Get health status from API server"""
        try:
            response = requests.get(f"{self.api_url}/health", timeout=5)
            if response.status_code == 200:
                return response.json()
            else:
                return {'status': 'unhealthy', 'error': f'API returned {response.status_code}'}
        except Exception as e:
            logger.error(f"Failed to get API health: {e}")
            return {'status': 'unhealthy', 'error': str(e)}
    
    def get_bot_statistics(self) -> List[Dict[str, Any]]:
        """Get per-bot statistics from database"""
        try:
            with self.get_db_connection() as conn:
                with conn.cursor(cursor_factory=RealDictCursor) as cur:
                    # Get message counts per bot for today
                    cur.execute("""
                        SELECT 
                            bot_name,
                            COUNT(*) as messages_today,
                            COUNT(DISTINCT user_id) as unique_users_today,
                            MAX(timestamp) as last_message_time
                        FROM discord_messages 
                        WHERE timestamp > %s AND bot_name != 'unknown'
                        GROUP BY bot_name
                    """, (datetime.utcnow() - timedelta(days=1),))
                    
                    bot_stats = []
                    for row in cur.fetchall():
                        bot_stats.append(dict(row))
                    
                    return bot_stats
        except Exception as e:
            logger.error(f"Failed to get bot statistics: {e}")
            return []
    
    def get_recent_messages(self, limit: int = 50) -> List[Dict[str, Any]]:
        """Get recent messages across all bots"""
        try:
            with self.get_db_connection() as conn:
                with conn.cursor(cursor_factory=RealDictCursor) as cur:
                    cur.execute("""
                        SELECT 
                            bot_name,
                            channel_id,
                            username,
                            message_content,
                            timestamp,
                            CASE WHEN user_id = 'bot' THEN true ELSE false END as is_bot_message
                        FROM discord_messages 
                        ORDER BY timestamp DESC 
                        LIMIT %s
                    """, (limit,))
                    
                    messages = []
                    for row in cur.fetchall():
                        msg = dict(row)
                        msg['timestamp'] = msg['timestamp'].isoformat() if msg['timestamp'] else None
                        messages.append(msg)
                    
                    return messages
        except Exception as e:
            logger.error(f"Failed to get recent messages: {e}")
            return []

# Initialize dashboard manager
dashboard = DashboardManager()

@app.route('/')
def index():
    """Main dashboard page"""
    try:
        # Get bot configurations
        bot_configs = dashboard.load_bot_configs()
        
        # Get API health and stats
        health = dashboard.get_api_health()
        stats = dashboard.get_api_stats()
        
        # Get bot-specific statistics
        bot_stats = dashboard.get_bot_statistics()
        
        # Create bot status data
        bot_status_data = {}
        for bot_id, bot_config in bot_configs.get('bots', {}).items():
            # Find matching stats
            bot_stat = next((s for s in bot_stats if s['bot_name'].lower() == bot_config['name'].lower()), {})
            
            bot_status_data[bot_id] = {
                'config': bot_config,
                'stats': bot_stat,
                'status': 'online' if bot_config.get('enabled', False) else 'offline'
            }
        
        return render_template('dashboard.html',
                             bot_status_data=bot_status_data,
                             system_health=health,
                             system_stats=stats,
                             page_title="BotForge Dashboard")
    
    except Exception as e:
        logger.error(f"Dashboard error: {e}")
        return render_template('error.html', error=str(e)), 500

@app.route('/api/stats')
def api_stats():
    """API endpoint for dashboard statistics"""
    try:
        stats = dashboard.get_api_stats()
        health = dashboard.get_api_health()
        bot_stats = dashboard.get_bot_statistics()
        
        return jsonify({
            'system': stats,
            'health': health,
            'bots': bot_stats,
            'timestamp': datetime.utcnow().isoformat()
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/config')
def config_page():
    """Bot configuration management page"""
    try:
        bot_configs = dashboard.load_bot_configs()
        return render_template('config.html',
                             bot_configs=bot_configs,
                             page_title="Bot Configuration")
    except Exception as e:
        logger.error(f"Config page error: {e}")
        return render_template('error.html', error=str(e)), 500

@app.route('/config/save', methods=['POST'])
def save_config():
    """Save bot configuration changes"""
    try:
        # Get form data
        config_data = request.get_json()
        
        if not config_data:
            flash('No configuration data received', 'error')
            return redirect(url_for('config_page'))
        
        # Save configuration
        if dashboard.save_bot_configs(config_data):
            flash('Configuration saved successfully!', 'success')
        else:
            flash('Failed to save configuration', 'error')
        
        return jsonify({'success': True})
    
    except Exception as e:
        logger.error(f"Config save error: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/logs')
def logs_page():
    """Recent messages and logs page"""
    try:
        recent_messages = dashboard.get_recent_messages(100)
        bot_configs = dashboard.load_bot_configs()
        return render_template('logs.html',
                             recent_messages=recent_messages,
                             bot_configs=bot_configs,
                             page_title="Recent Messages")
    except Exception as e:
        logger.error(f"Logs page error: {e}")
        return render_template('error.html', error=str(e)), 500

@app.route('/health')
def health_check():
    """Dashboard health check"""
    try:
        # Test database connection
        with dashboard.get_db_connection() as conn:
            with conn.cursor() as cur:
                cur.execute('SELECT 1')
        
        # Test API connection
        api_health = dashboard.get_api_health()
        
        return jsonify({
            'status': 'healthy',
            'timestamp': datetime.utcnow().isoformat(),
            'database': 'connected',
            'api_server': api_health.get('status', 'unknown')
        })
    except Exception as e:
        return jsonify({
            'status': 'unhealthy',
            'error': str(e),
            'timestamp': datetime.utcnow().isoformat()
        }), 500

if __name__ == '__main__':
    logger.info("🚀 Starting BotForge Dashboard...")
    app.run(host='0.0.0.0', port=3000, debug=False)