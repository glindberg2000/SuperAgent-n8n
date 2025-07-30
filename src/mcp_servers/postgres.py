#!/usr/bin/env python3
"""
PostgreSQL MCP Server
====================

Provides PostgreSQL database operations and vector search through MCP (Model Context Protocol).
Includes vector similarity search using pgvector extension.
"""

import os
import json
import asyncio
import logging
from typing import Dict, List, Optional, Any
import asyncpg
import websockets
import argparse
from datetime import datetime
import hashlib

logger = logging.getLogger(__name__)

class PostgreSQLMCPServer:
    """MCP server providing PostgreSQL operations"""
    
    def __init__(self, connection_string: str = None, port: int = 8003):
        self.connection_string = connection_string or self._build_connection_string()
        self.port = port
        self.pool = None
        self.websocket_server = None
        self.connected_clients = set()
    
    def _build_connection_string(self) -> str:
        """Build PostgreSQL connection string from environment variables"""
        host = os.getenv('POSTGRES_HOST', 'localhost')
        port = os.getenv('POSTGRES_PORT', '5436')
        database = os.getenv('POSTGRES_DB', 'botforge')
        username = os.getenv('POSTGRES_USER', 'botforge')
        password = os.getenv('POSTGRES_PASSWORD', 'botforge-db-2025')
        
        return f"postgresql://{username}:{password}@{host}:{port}/{database}"
    
    async def start(self):
        """Start the PostgreSQL MCP server"""
        try:
            # Initialize database connection pool
            self.pool = await asyncpg.create_pool(self.connection_string)
            logger.info("✅ PostgreSQL connection pool initialized")
            
            # Start WebSocket server
            self.websocket_server = await websockets.serve(
                self.handle_client,
                "localhost",
                self.port,
                subprotocols=["mcp"]
            )
            logger.info(f"PostgreSQL MCP server listening on ws://localhost:{self.port}/mcp")
            await self.websocket_server.wait_closed()
            
        except Exception as e:
            logger.error(f"Failed to start PostgreSQL MCP server: {e}")
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
                    "name": "postgres-mcp-server",
                    "version": "1.0.0"
                }
            }
        }
    
    async def handle_tools_list(self, request_id: str) -> Dict[str, Any]:
        """Return list of available PostgreSQL tools"""
        tools = [
            {
                "name": "execute_query",
                "description": "Execute a SQL query (SELECT only for safety)",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "query": {"type": "string", "description": "SQL query to execute"},
                        "parameters": {"type": "array", "description": "Query parameters", "default": []}
                    },
                    "required": ["query"]
                }
            },
            {
                "name": "search_documents",
                "description": "Search for documents using vector similarity",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "query": {"type": "string", "description": "Search query"},
                        "collection_name": {"type": "string", "description": "Collection to search", "default": "documents"},
                        "limit": {"type": "integer", "description": "Max results", "default": 10},
                        "similarity_threshold": {"type": "number", "description": "Similarity threshold", "default": 0.7}
                    },
                    "required": ["query"]
                }
            },
            {
                "name": "add_document_embedding",
                "description": "Add a document with embedding to the vector store",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "content": {"type": "string", "description": "Document content"},
                        "embedding": {"type": "array", "items": {"type": "number"}, "description": "Vector embedding"},
                        "metadata": {"type": "object", "description": "Document metadata"},
                        "collection_name": {"type": "string", "description": "Collection name", "default": "documents"}
                    },
                    "required": ["content", "embedding"]
                }
            },
            {
                "name": "search_conversations",
                "description": "Search conversation history using vector similarity",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "query": {"type": "string", "description": "Search query"},
                        "embedding": {"type": "array", "items": {"type": "number"}, "description": "Query embedding"},
                        "limit": {"type": "integer", "description": "Max results", "default": 10},
                        "similarity_threshold": {"type": "number", "description": "Similarity threshold", "default": 0.7}
                    },
                    "required": ["embedding"]
                }
            },
            {
                "name": "search_code",
                "description": "Search code using vector similarity",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "query": {"type": "string", "description": "Search query"},
                        "embedding": {"type": "array", "items": {"type": "number"}, "description": "Query embedding"},
                        "repository": {"type": "string", "description": "Repository filter"},
                        "language": {"type": "string", "description": "Language filter"},
                        "limit": {"type": "integer", "description": "Max results", "default": 10},
                        "similarity_threshold": {"type": "number", "description": "Similarity threshold", "default": 0.7}
                    },
                    "required": ["embedding"]
                }
            },
            {
                "name": "get_conversation_history",
                "description": "Get conversation history for a user or channel",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "user_id": {"type": "string", "description": "Discord user ID"},
                        "channel_id": {"type": "string", "description": "Discord channel ID"},
                        "limit": {"type": "integer", "description": "Max messages", "default": 50}
                    },
                    "required": []
                }
            },
            {
                "name": "save_conversation",
                "description": "Save a conversation to the database",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "channel_id": {"type": "string", "description": "Discord channel ID"},
                        "user_id": {"type": "string", "description": "Discord user ID"},
                        "messages": {"type": "array", "description": "Message list"},
                        "agent_type": {"type": "string", "description": "Agent type"}
                    },
                    "required": ["channel_id", "messages"]
                }
            },
            {
                "name": "get_database_stats",
                "description": "Get statistics about the database",
                "inputSchema": {
                    "type": "object",
                    "properties": {},
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
            
            if tool_name == "execute_query":
                result = await self.execute_query(**arguments)
            elif tool_name == "search_documents":
                result = await self.search_documents(**arguments)
            elif tool_name == "add_document_embedding":
                result = await self.add_document_embedding(**arguments)
            elif tool_name == "search_conversations":
                result = await self.search_conversations(**arguments)
            elif tool_name == "search_code":
                result = await self.search_code(**arguments)
            elif tool_name == "get_conversation_history":
                result = await self.get_conversation_history(**arguments)
            elif tool_name == "save_conversation":
                result = await self.save_conversation(**arguments)
            elif tool_name == "get_database_stats":
                result = await self.get_database_stats(**arguments)
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
    
    # PostgreSQL tool implementations
    async def execute_query(self, query: str, parameters: List[Any] = None) -> Dict[str, Any]:
        """Execute a SQL query (SELECT only for safety)"""
        try:
            # Safety check - only allow SELECT queries
            query_upper = query.strip().upper()
            if not query_upper.startswith('SELECT'):
                return {"error": "Only SELECT queries are allowed for safety"}
            
            async with self.pool.acquire() as conn:
                if parameters:
                    rows = await conn.fetch(query, *parameters)
                else:
                    rows = await conn.fetch(query)
                
                # Convert to list of dictionaries
                results = [dict(row) for row in rows]
                
                return {
                    "success": True,
                    "query": query,
                    "row_count": len(results),
                    "results": results
                }
                
        except Exception as e:
            return {"error": str(e)}
    
    async def search_documents(self, query: str, collection_name: str = "documents", 
                             limit: int = 10, similarity_threshold: float = 0.7) -> Dict[str, Any]:
        """Search for documents using vector similarity"""
        try:
            # This would require the query to be embedded first
            # For now, return a placeholder
            return {
                "error": "Document search requires embedding generation. Use the vector storage client directly."
            }
        except Exception as e:
            return {"error": str(e)}
    
    async def add_document_embedding(self, content: str, embedding: List[float], 
                                   metadata: Dict[str, Any] = None, 
                                   collection_name: str = "documents") -> Dict[str, Any]:
        """Add a document with embedding to the vector store"""
        try:
            doc_id = hashlib.md5(content.encode()).hexdigest()
            
            async with self.pool.acquire() as conn:
                await conn.execute("""
                    INSERT INTO document_embeddings 
                    (document_id, chunk_index, content, embedding, metadata, collection_name)
                    VALUES ($1, $2, $3, $4, $5, $6)
                    ON CONFLICT (document_id, chunk_index) DO UPDATE SET
                    content = EXCLUDED.content,
                    embedding = EXCLUDED.embedding,
                    metadata = EXCLUDED.metadata,
                    updated_at = NOW()
                """, doc_id, 0, content, embedding, json.dumps(metadata or {}), collection_name)
            
            return {
                "success": True,
                "document_id": doc_id,
                "collection": collection_name,
                "content_length": len(content)
            }
            
        except Exception as e:
            return {"error": str(e)}
    
    async def search_conversations(self, embedding: List[float], query: str = "",
                                 limit: int = 10, similarity_threshold: float = 0.7) -> Dict[str, Any]:
        """Search conversation history using vector similarity"""
        try:
            async with self.pool.acquire() as conn:
                results = await conn.fetch("""
                    SELECT * FROM search_similar_conversations($1, $2, $3)
                """, embedding, similarity_threshold, limit)
                
                conversations = []
                for row in results:
                    conversations.append({
                        "conversation_id": str(row['conversation_id']),
                        "summary": row['summary'],
                        "similarity": float(row['similarity']),
                        "participant_count": row['participant_count'],
                        "message_count": row['message_count']
                    })
                
                return {
                    "success": True,
                    "query": query,
                    "result_count": len(conversations),
                    "conversations": conversations
                }
                
        except Exception as e:
            return {"error": str(e)}
    
    async def search_code(self, embedding: List[float], query: str = "",
                         repository: str = None, language: str = None,
                         limit: int = 10, similarity_threshold: float = 0.7) -> Dict[str, Any]:
        """Search code using vector similarity"""
        try:
            async with self.pool.acquire() as conn:
                results = await conn.fetch("""
                    SELECT * FROM search_similar_code($1, $2, $3, $4, $5)
                """, embedding, repository, language, similarity_threshold, limit)
                
                code_results = []
                for row in results:
                    code_results.append({
                        "id": str(row['id']),
                        "repository": row['repository_name'],
                        "file_path": row['file_path'],
                        "content": row['content'],
                        "similarity": float(row['similarity']),
                        "language": row['language'],
                        "metadata": json.loads(row['metadata']) if row['metadata'] else {}
                    })
                
                return {
                    "success": True,
                    "query": query,
                    "result_count": len(code_results),
                    "results": code_results
                }
                
        except Exception as e:
            return {"error": str(e)}
    
    async def get_conversation_history(self, user_id: str = None, channel_id: str = None, 
                                     limit: int = 50) -> Dict[str, Any]:
        """Get conversation history for a user or channel"""
        try:
            async with self.pool.acquire() as conn:
                if user_id and channel_id:
                    query = """
                        SELECT m.*, c.discord_channel_id, u.username, u.display_name
                        FROM messages m
                        JOIN conversations c ON m.conversation_id = c.id
                        JOIN discord_users u ON m.user_id = u.id
                        WHERE c.user_id = $1 AND c.discord_channel_id = $2
                        ORDER BY m.created_at DESC
                        LIMIT $3
                    """
                    rows = await conn.fetch(query, int(user_id), int(channel_id), limit)
                elif user_id:
                    query = """
                        SELECT m.*, c.discord_channel_id, u.username, u.display_name
                        FROM messages m
                        JOIN conversations c ON m.conversation_id = c.id
                        JOIN discord_users u ON m.user_id = u.id
                        WHERE c.user_id = $1
                        ORDER BY m.created_at DESC
                        LIMIT $2
                    """
                    rows = await conn.fetch(query, int(user_id), limit)
                elif channel_id:
                    query = """
                        SELECT m.*, c.discord_channel_id, u.username, u.display_name
                        FROM messages m
                        JOIN conversations c ON m.conversation_id = c.id
                        JOIN discord_users u ON m.user_id = u.id
                        WHERE c.discord_channel_id = $1
                        ORDER BY m.created_at DESC
                        LIMIT $2
                    """
                    rows = await conn.fetch(query, int(channel_id), limit)
                else:
                    return {"error": "Either user_id or channel_id must be provided"}
                
                messages = []
                for row in rows:
                    messages.append({
                        "id": str(row['id']),
                        "content": row['content'],
                        "user_id": str(row['user_id']),
                        "username": row['username'],
                        "display_name": row['display_name'],
                        "message_type": row['message_type'],
                        "agent_name": row['agent_name'],
                        "created_at": row['created_at'].isoformat(),
                        "metadata": json.loads(row['metadata']) if row['metadata'] else {}
                    })
                
                return {
                    "success": True,
                    "message_count": len(messages),
                    "messages": messages
                }
                
        except Exception as e:
            return {"error": str(e)}
    
    async def save_conversation(self, channel_id: str, messages: List[Dict[str, Any]], 
                              user_id: str = None, agent_type: str = None) -> Dict[str, Any]:
        """Save a conversation to the database"""
        try:
            async with self.pool.acquire() as conn:
                async with conn.transaction():
                    # Create or get conversation
                    conversation_id = await conn.fetchval("""
                        INSERT INTO conversations (discord_channel_id, user_id, agent_type)
                        VALUES ($1, $2, $3)
                        ON CONFLICT (discord_channel_id, user_id) DO UPDATE SET
                        updated_at = NOW()
                        RETURNING id
                    """, int(channel_id), int(user_id) if user_id else None, agent_type)
                    
                    # Save messages
                    saved_messages = 0
                    for msg in messages:
                        await conn.execute("""
                            INSERT INTO messages (conversation_id, user_id, content, message_type, agent_name, metadata)
                            VALUES ($1, $2, $3, $4, $5, $6)
                        """, conversation_id, int(msg.get('user_id', 0)), msg.get('content', ''),
                        msg.get('type', 'user'), msg.get('agent_name'), json.dumps(msg.get('metadata', {})))
                        saved_messages += 1
                    
                    return {
                        "success": True,
                        "conversation_id": str(conversation_id),
                        "messages_saved": saved_messages
                    }
                    
        except Exception as e:
            return {"error": str(e)}
    
    async def get_database_stats(self) -> Dict[str, Any]:
        """Get statistics about the database"""
        try:
            async with self.pool.acquire() as conn:
                stats = {}
                
                # Get table row counts
                tables = ['discord_users', 'conversations', 'messages', 'entities', 
                         'document_embeddings', 'conversation_embeddings', 'code_embeddings']
                
                for table in tables:
                    count = await conn.fetchval(f"SELECT COUNT(*) FROM {table}")
                    stats[f"{table}_count"] = count
                
                # Get embedding collection stats
                doc_collections = await conn.fetch("""
                    SELECT collection_name, COUNT(*) as count 
                    FROM document_embeddings 
                    GROUP BY collection_name
                """)
                stats['document_collections'] = {row['collection_name']: row['count'] for row in doc_collections}
                
                # Get code repository stats
                code_repos = await conn.fetch("""
                    SELECT repository_name, COUNT(*) as count 
                    FROM code_embeddings 
                    GROUP BY repository_name
                """)
                stats['code_repositories'] = {row['repository_name']: row['count'] for row in code_repos}
                
                return {
                    "success": True,
                    "timestamp": datetime.now().isoformat(),
                    "statistics": stats
                }
                
        except Exception as e:
            return {"error": str(e)}


async def main():
    """Main entry point for the PostgreSQL MCP server"""
    parser = argparse.ArgumentParser(description="PostgreSQL MCP Server")
    parser.add_argument("--connection-string", help="PostgreSQL connection string")
    parser.add_argument("--port", type=int, default=8003, help="WebSocket port")
    
    args = parser.parse_args()
    
    # Configure logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # Create and start server
    server = PostgreSQLMCPServer(
        connection_string=args.connection_string,
        port=args.port
    )
    
    try:
        await server.start()
    except KeyboardInterrupt:
        logger.info("Shutting down PostgreSQL MCP server...")
        if server.pool:
            await server.pool.close()
    except Exception as e:
        logger.error(f"PostgreSQL MCP server error: {e}")
        raise


if __name__ == "__main__":
    asyncio.run(main())