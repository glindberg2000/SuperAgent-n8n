#!/usr/bin/env python3
"""
MCP (Model Context Protocol) Client for BotForge
===============================================

Provides standardized tool access through MCP servers, allowing bots to use
Discord tools, file operations, database access, and other capabilities
through a unified interface.
"""

import os
import json
import asyncio
import subprocess
import logging
from typing import Dict, List, Optional, Any, Union
from pathlib import Path
import aiohttp
import websockets
from datetime import datetime
import uuid

logger = logging.getLogger(__name__)

class MCPServer:
    """Represents a single MCP server connection"""
    
    def __init__(self, name: str, config: Dict[str, Any]):
        self.name = name
        self.config = config
        self.process = None
        self.websocket = None
        self.tools = {}
        self.is_connected = False
        self.last_ping = None
    
    async def start(self) -> bool:
        """Start the MCP server process"""
        try:
            command = self.config.get("command", "python")
            args = self.config.get("args", [])
            env = os.environ.copy()
            env.update(self.config.get("env", {}))
            
            # Replace environment variable placeholders
            for key, value in env.items():
                if isinstance(value, str) and value.startswith("${") and value.endswith("}"):
                    env_var = value[2:-1]
                    env[key] = os.getenv(env_var, "")
            
            # Start the MCP server process
            self.process = await asyncio.create_subprocess_exec(
                command, *args,
                env=env,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            
            # Wait a moment for the server to start
            await asyncio.sleep(2)
            
            # Check if process is still running
            if self.process.returncode is not None:
                stdout, stderr = await self.process.communicate()
                logger.error(f"MCP server {self.name} failed to start: {stderr.decode()}")
                return False
            
            logger.info(f"✅ MCP server {self.name} started successfully")
            return True
            
        except Exception as e:
            logger.error(f"❌ Failed to start MCP server {self.name}: {e}")
            return False
    
    async def connect(self, port: int = None) -> bool:
        """Connect to the MCP server via WebSocket"""
        try:
            # If no port specified, try to discover it
            if port is None:
                port = 8000 + hash(self.name) % 1000  # Generate consistent port
            
            ws_url = f"ws://localhost:{port}/mcp"
            self.websocket = await websockets.connect(ws_url)
            
            # Send initialization message
            init_message = {
                "jsonrpc": "2.0",
                "id": str(uuid.uuid4()),
                "method": "initialize",
                "params": {
                    "protocolVersion": "2024-11-05",
                    "capabilities": {
                        "tools": {}
                    },
                    "clientInfo": {
                        "name": "BotForge",
                        "version": "1.0.0"
                    }
                }
            }
            
            await self.websocket.send(json.dumps(init_message))
            response = await self.websocket.recv()
            init_response = json.loads(response)
            
            if "error" in init_response:
                logger.error(f"MCP server {self.name} initialization failed: {init_response['error']}")
                return False
            
            # Discover available tools
            await self._discover_tools()
            
            self.is_connected = True
            self.last_ping = datetime.now()
            logger.info(f"✅ Connected to MCP server {self.name} with {len(self.tools)} tools")
            return True
            
        except Exception as e:
            logger.error(f"❌ Failed to connect to MCP server {self.name}: {e}")
            return False
    
    async def _discover_tools(self):
        """Discover available tools from the MCP server"""
        try:
            tools_message = {
                "jsonrpc": "2.0",
                "id": str(uuid.uuid4()),
                "method": "tools/list"
            }
            
            await self.websocket.send(json.dumps(tools_message))
            response = await self.websocket.recv()
            tools_response = json.loads(response)
            
            if "result" in tools_response and "tools" in tools_response["result"]:
                for tool in tools_response["result"]["tools"]:
                    self.tools[tool["name"]] = {
                        "name": tool["name"],
                        "description": tool.get("description", ""),
                        "parameters": tool.get("inputSchema", {}),
                        "server": self.name
                    }
                    
            logger.info(f"Discovered {len(self.tools)} tools from {self.name}: {list(self.tools.keys())}")
            
        except Exception as e:
            logger.error(f"Failed to discover tools from {self.name}: {e}")
    
    async def call_tool(self, tool_name: str, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """Call a tool on this MCP server"""
        try:
            if not self.is_connected or not self.websocket:
                return {"error": f"Not connected to MCP server {self.name}"}
            
            if tool_name not in self.tools:
                return {"error": f"Tool {tool_name} not found on server {self.name}"}
            
            # Prepare tool call message
            call_message = {
                "jsonrpc": "2.0",
                "id": str(uuid.uuid4()),
                "method": "tools/call",
                "params": {
                    "name": tool_name,
                    "arguments": parameters
                }
            }
            
            await self.websocket.send(json.dumps(call_message))
            response = await self.websocket.recv()
            call_response = json.loads(response)
            
            if "error" in call_response:
                return {"error": call_response["error"]}
            
            return call_response.get("result", {})
            
        except Exception as e:
            logger.error(f"Error calling tool {tool_name} on {self.name}: {e}")
            return {"error": str(e)}
    
    async def stop(self):
        """Stop the MCP server"""
        self.is_connected = False
        
        if self.websocket:
            await self.websocket.close()
            
        if self.process:
            self.process.terminate()
            try:
                await asyncio.wait_for(self.process.wait(), timeout=5.0)
            except asyncio.TimeoutError:
                self.process.kill()
                await self.process.wait()
        
        logger.info(f"MCP server {self.name} stopped")


class MCPClient:
    """MCP client that manages multiple server connections and provides unified tool access"""
    
    def __init__(self, config_path: str = "mcp.json"):
        self.config_path = config_path
        self.servers: Dict[str, MCPServer] = {}
        self.all_tools: Dict[str, Dict[str, Any]] = {}
        self.is_initialized = False
    
    async def initialize(self) -> bool:
        """Initialize the MCP client and start all servers"""
        try:
            # Load MCP configuration
            config_file = Path(self.config_path)
            if not config_file.exists():
                logger.error(f"MCP configuration file not found: {self.config_path}")
                return False
            
            with open(config_file, 'r') as f:
                config = json.load(f)
            
            # Start all MCP servers
            mcp_servers = config.get("mcpServers", {})
            start_tasks = []
            
            for server_name, server_config in mcp_servers.items():
                server = MCPServer(server_name, server_config)
                self.servers[server_name] = server
                start_tasks.append(server.start())
            
            # Wait for all servers to start
            start_results = await asyncio.gather(*start_tasks, return_exceptions=True)
            
            # Connect to all servers
            connect_tasks = []
            for i, (server_name, result) in enumerate(zip(mcp_servers.keys(), start_results)):
                if isinstance(result, bool) and result:
                    connect_tasks.append(self.servers[server_name].connect())
                else:
                    logger.warning(f"Server {server_name} failed to start, skipping connection")
            
            if connect_tasks:
                connect_results = await asyncio.gather(*connect_tasks, return_exceptions=True)
                
                # Collect all available tools
                for server in self.servers.values():
                    if server.is_connected:
                        self.all_tools.update(server.tools)
            
            self.is_initialized = True
            logger.info(f"✅ MCP client initialized with {len(self.all_tools)} total tools from {len([s for s in self.servers.values() if s.is_connected])} servers")
            return True
            
        except Exception as e:
            logger.error(f"❌ Failed to initialize MCP client: {e}")
            return False
    
    def get_available_tools(self) -> List[Dict[str, Any]]:
        """Get list of all available tools across all servers"""
        return list(self.all_tools.values())
    
    def get_tools_schema(self) -> List[Dict[str, Any]]:
        """Get OpenAI/Anthropic compatible function schemas for all tools"""
        schemas = []
        
        for tool_name, tool_info in self.all_tools.items():
            schema = {
                "name": tool_name,
                "description": tool_info.get("description", f"Tool from {tool_info.get('server', 'unknown')} server"),
                "parameters": tool_info.get("parameters", {
                    "type": "object",
                    "properties": {},
                    "required": []
                })
            }
            schemas.append(schema)
        
        return schemas
    
    async def call_tool(self, tool_name: str, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """Call a tool by name across all servers"""
        try:
            if not self.is_initialized:
                return {"error": "MCP client not initialized"}
            
            if tool_name not in self.all_tools:
                return {"error": f"Tool {tool_name} not found. Available tools: {list(self.all_tools.keys())}"}
            
            tool_info = self.all_tools[tool_name]
            server_name = tool_info.get("server")
            
            if server_name not in self.servers:
                return {"error": f"Server {server_name} not found"}
            
            server = self.servers[server_name]
            if not server.is_connected:
                return {"error": f"Server {server_name} not connected"}
            
            # Call the tool on the appropriate server
            result = await server.call_tool(tool_name, parameters)
            
            # Add metadata about the tool call
            if "error" not in result:
                result["_mcp_metadata"] = {
                    "server": server_name,
                    "tool": tool_name,
                    "called_at": datetime.now().isoformat()
                }
            
            return result
            
        except Exception as e:
            logger.error(f"Error calling tool {tool_name}: {e}")
            return {"error": str(e)}
    
    async def health_check(self) -> Dict[str, Any]:
        """Check the health of all MCP servers"""
        health_status = {
            "overall_status": "healthy",
            "servers": {},
            "total_tools": len(self.all_tools),
            "connected_servers": 0,
            "failed_servers": 0
        }
        
        for server_name, server in self.servers.items():
            if server.is_connected:
                health_status["servers"][server_name] = {
                    "status": "connected",
                    "tools_count": len(server.tools),
                    "last_ping": server.last_ping.isoformat() if server.last_ping else None
                }
                health_status["connected_servers"] += 1
            else:
                health_status["servers"][server_name] = {
                    "status": "disconnected",
                    "tools_count": 0,
                    "last_ping": None
                }
                health_status["failed_servers"] += 1
        
        if health_status["failed_servers"] > 0:
            health_status["overall_status"] = "degraded" if health_status["connected_servers"] > 0 else "failed"
        
        return health_status
    
    async def shutdown(self):
        """Shutdown all MCP servers"""
        logger.info("Shutting down MCP client...")
        
        stop_tasks = []
        for server in self.servers.values():
            stop_tasks.append(server.stop())
        
        if stop_tasks:
            await asyncio.gather(*stop_tasks, return_exceptions=True)
        
        self.servers.clear()
        self.all_tools.clear()
        self.is_initialized = False
        logger.info("MCP client shutdown complete")


# Global MCP client instance
mcp_client = MCPClient()

async def get_mcp_client() -> MCPClient:
    """Get the global MCP client instance, initializing if necessary"""
    if not mcp_client.is_initialized:
        await mcp_client.initialize()
    return mcp_client

def get_mcp_tools_schema() -> List[Dict[str, Any]]:
    """Get MCP tools schema for LLM function calling (sync version)"""
    if mcp_client.is_initialized:
        return mcp_client.get_tools_schema()
    return []

async def call_mcp_tool(tool_name: str, parameters: Dict[str, Any]) -> Dict[str, Any]:
    """Call an MCP tool (async version)"""
    client = await get_mcp_client()
    return await client.call_tool(tool_name, parameters)