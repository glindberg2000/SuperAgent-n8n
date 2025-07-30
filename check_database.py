#!/usr/bin/env python3
"""
Quick script to check database contents and verify memory is working
"""

import psycopg2
import psycopg2.extras
import json
from dotenv import load_dotenv
import os

load_dotenv()

# Database configuration
POSTGRES_HOST = os.getenv('POSTGRES_HOST', 'localhost')
if POSTGRES_HOST == 'postgres':
    POSTGRES_HOST = 'localhost'
POSTGRES_PORT = os.getenv('POSTGRES_PORT', '5432')
POSTGRES_DB = os.getenv('POSTGRES_DB', 'superagent')
POSTGRES_USER = os.getenv('POSTGRES_USER', 'superagent')
POSTGRES_PASSWORD = os.getenv('POSTGRES_PASSWORD', 'superagent_password')

def check_database():
    """Check database contents"""
    try:
        conn = psycopg2.connect(
            host=POSTGRES_HOST,
            port=POSTGRES_PORT,
            database=POSTGRES_DB,
            user=POSTGRES_USER,
            password=POSTGRES_PASSWORD
        )
        
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cursor:
            print("=== DISCORD USERS ===")
            cursor.execute("SELECT * FROM discord_users ORDER BY id")
            users = cursor.fetchall()
            for user in users:
                print(f"ID: {user['id']}, Username: {user['username']}")
            
            print(f"\n=== RECENT MESSAGES (Last 10) ===")
            cursor.execute("""
                SELECT m.discord_message_id, m.user_id, u.username, m.content, 
                       m.message_type, m.agent_name, m.created_at,
                       (m.metadata->>'channelId') as channel_id
                FROM messages m 
                LEFT JOIN discord_users u ON m.user_id = u.id 
                ORDER BY m.created_at DESC 
                LIMIT 10
            """)
            messages = cursor.fetchall()
            
            for msg in messages:
                msg_type = msg['message_type']
                agent = f" ({msg['agent_name']})" if msg['agent_name'] else ""
                content = msg['content'][:60] + '...' if len(msg['content']) > 60 else msg['content']
                print(f"{msg['created_at']} [{msg_type}]{agent} {msg['username']}: {content}")
            
            print(f"\n=== CONVERSATION STATS ===")
            cursor.execute("""
                SELECT 
                    u.username,
                    (metadata->>'channelId') as channel_id,
                    COUNT(*) as message_count,
                    MAX(created_at) as last_message
                FROM messages m
                JOIN discord_users u ON m.user_id = u.id
                GROUP BY u.username, (metadata->>'channelId')
                ORDER BY last_message DESC
            """)
            stats = cursor.fetchall()
            
            for stat in stats:
                print(f"User: {stat['username']}, Channel: {stat['channel_id']}, Messages: {stat['message_count']}, Last: {stat['last_message']}")
        
        conn.close()
        print("\n✅ Database check complete!")
        
    except Exception as e:
        print(f"❌ Database error: {e}")

if __name__ == '__main__':
    check_database()