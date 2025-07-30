#!/usr/bin/env python3
"""
Filesystem MCP Server
=====================

Provides file system operations through MCP (Model Context Protocol).
Enables secure file reading, writing, and analysis capabilities.
"""

import os
import json
import asyncio
import logging
from typing import Dict, List, Optional, Any
from pathlib import Path
import websockets
import argparse
import aiofiles
import hashlib
import mimetypes
from datetime import datetime

logger = logging.getLogger(__name__)

class FilesystemMCPServer:
    """MCP server providing filesystem operations"""
    
    def __init__(self, allowed_dirs: List[str], max_file_size: str = "25MB", 
                 allowed_extensions: str = None, port: int = 8002):
        self.allowed_dirs = [Path(d).resolve() for d in allowed_dirs]
        self.max_file_size = self._parse_size(max_file_size)
        self.allowed_extensions = set(allowed_extensions.split(',')) if allowed_extensions else {
            '.py', '.js', '.ts', '.md', '.txt', '.json', '.yaml', '.yml', 
            '.sql', '.sh', '.html', '.css', '.cpp', '.c', '.h', '.go', 
            '.rs', '.java', '.php', '.rb', '.swift', '.kt', '.scala',
            '.dockerfile', '.gitignore', '.env', '.toml', '.ini', '.cfg'
        }
        self.port = port
        self.websocket_server = None
        self.connected_clients = set()
        
        # Ensure allowed directories exist
        for dir_path in self.allowed_dirs:
            dir_path.mkdir(parents=True, exist_ok=True)
    
    def _parse_size(self, size_str: str) -> int:
        """Parse size string like '25MB' to bytes"""
        size_str = size_str.upper()
        if size_str.endswith('KB'):
            return int(size_str[:-2]) * 1024
        elif size_str.endswith('MB'):
            return int(size_str[:-2]) * 1024 * 1024
        elif size_str.endswith('GB'):
            return int(size_str[:-2]) * 1024 * 1024 * 1024
        else:
            return int(size_str)
    
    async def start(self):
        """Start the filesystem MCP server"""
        try:
            self.websocket_server = await websockets.serve(
                self.handle_client,
                "localhost",
                self.port,
                subprotocols=["mcp"]
            )
            logger.info(f"Filesystem MCP server listening on ws://localhost:{self.port}/mcp")
            await self.websocket_server.wait_closed()
            
        except Exception as e:
            logger.error(f"Failed to start filesystem MCP server: {e}")
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
                    "name": "filesystem-mcp-server",
                    "version": "1.0.0"
                }
            }
        }
    
    async def handle_tools_list(self, request_id: str) -> Dict[str, Any]:
        """Return list of available filesystem tools"""
        tools = [
            {
                "name": "read_file",
                "description": "Read content from a file",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "file_path": {"type": "string", "description": "Path to the file"},
                        "encoding": {"type": "string", "description": "Text encoding", "default": "utf-8"}
                    },
                    "required": ["file_path"]
                }
            },
            {
                "name": "write_file",
                "description": "Write content to a file",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "file_path": {"type": "string", "description": "Path to write file"},
                        "content": {"type": "string", "description": "Content to write"},
                        "encoding": {"type": "string", "description": "Text encoding", "default": "utf-8"},
                        "overwrite": {"type": "boolean", "description": "Allow overwriting", "default": False}
                    },
                    "required": ["file_path", "content"]
                }
            },
            {
                "name": "list_files",
                "description": "List files in a directory",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "directory": {"type": "string", "description": "Directory path", "default": "."},
                        "pattern": {"type": "string", "description": "File pattern", "default": "*"},
                        "recursive": {"type": "boolean", "description": "Search subdirectories", "default": False}
                    },
                    "required": []
                }
            },
            {
                "name": "analyze_codebase",
                "description": "Analyze a codebase for structure and metrics",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "directory": {"type": "string", "description": "Root directory to analyze"},
                        "languages": {"type": "array", "items": {"type": "string"}, "description": "Languages to focus on"}
                    },
                    "required": ["directory"]
                }
            },
            {
                "name": "get_file_info",
                "description": "Get metadata information about a file",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "file_path": {"type": "string", "description": "Path to the file"}
                    },
                    "required": ["file_path"]
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
            
            if tool_name == "read_file":
                result = await self.read_file(**arguments)
            elif tool_name == "write_file":
                result = await self.write_file(**arguments)
            elif tool_name == "list_files":
                result = await self.list_files(**arguments)
            elif tool_name == "analyze_codebase":
                result = await self.analyze_codebase(**arguments)
            elif tool_name == "get_file_info":
                result = await self.get_file_info(**arguments)
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
    
    def _is_safe_path(self, path: Path) -> bool:
        """Check if a file path is safe to access"""
        try:
            abs_path = path.resolve()
            return any(
                str(abs_path).startswith(str(allowed_dir))
                for allowed_dir in self.allowed_dirs
            )
        except Exception:
            return False
    
    # Filesystem tool implementations
    async def read_file(self, file_path: str, encoding: str = 'utf-8') -> Dict[str, Any]:
        """Read content from a file"""
        try:
            file_path = Path(file_path)
            
            if not self._is_safe_path(file_path):
                return {"error": "Access denied: File path not allowed"}
            
            if not file_path.exists():
                return {"error": f"File not found: {file_path}"}
            
            if not file_path.is_file():
                return {"error": f"Path is not a file: {file_path}"}
            
            # Check file size
            file_size = file_path.stat().st_size
            if file_size > self.max_file_size:
                return {"error": f"File too large: {file_size} bytes (max: {self.max_file_size})"}
            
            # Check file extension
            if file_path.suffix.lower() not in self.allowed_extensions:
                return {"error": f"File type not allowed: {file_path.suffix}"}
            
            # Read file content
            async with aiofiles.open(file_path, 'r', encoding=encoding) as f:
                content = await f.read()
            
            # Get file metadata
            stat = file_path.stat()
            
            return {
                "success": True,
                "file_path": str(file_path),
                "file_name": file_path.name,
                "file_size": file_size,
                "file_extension": file_path.suffix,
                "mime_type": mimetypes.guess_type(str(file_path))[0] or 'text/plain',
                "created_time": datetime.fromtimestamp(stat.st_ctime).isoformat(),
                "modified_time": datetime.fromtimestamp(stat.st_mtime).isoformat(),
                "content": content,
                "line_count": content.count('\n') + 1,
                "char_count": len(content),
                "encoding": encoding
            }
            
        except UnicodeDecodeError:
            return {"error": f"Failed to decode file with encoding {encoding}"}
        except Exception as e:
            return {"error": str(e)}
    
    async def write_file(self, file_path: str, content: str, encoding: str = 'utf-8', overwrite: bool = False) -> Dict[str, Any]:
        """Write content to a file"""
        try:
            file_path = Path(file_path)
            
            if not self._is_safe_path(file_path):
                return {"error": "Access denied: File path not allowed"}
            
            # Check if file exists and overwrite policy
            if file_path.exists() and not overwrite:
                return {"error": "File already exists. Use overwrite=True to replace it."}
            
            # Check file extension
            if file_path.suffix.lower() not in self.allowed_extensions:
                return {"error": f"File type not allowed: {file_path.suffix}"}
            
            # Check content size
            content_size = len(content.encode(encoding))
            if content_size > self.max_file_size:
                return {"error": f"Content too large: {content_size} bytes (max: {self.max_file_size})"}
            
            # Create parent directories if needed
            file_path.parent.mkdir(parents=True, exist_ok=True)
            
            # Write file
            async with aiofiles.open(file_path, 'w', encoding=encoding) as f:
                await f.write(content)
            
            # Generate file hash for verification
            file_hash = hashlib.md5(content.encode(encoding)).hexdigest()
            
            return {
                "success": True,
                "file_path": str(file_path),
                "file_name": file_path.name,
                "bytes_written": content_size,
                "line_count": content.count('\n') + 1,
                "char_count": len(content),
                "file_hash": file_hash,
                "created_time": datetime.now().isoformat(),
                "overwritten": file_path.exists()
            }
            
        except Exception as e:
            return {"error": str(e)}
    
    async def list_files(self, directory: str = ".", pattern: str = "*", recursive: bool = False) -> Dict[str, Any]:
        """List files in a directory"""
        try:
            dir_path = Path(directory)
            
            if not self._is_safe_path(dir_path):
                return {"error": "Access denied: Directory path not allowed"}
            
            if not dir_path.exists():
                return {"error": f"Directory not found: {dir_path}"}
            
            if not dir_path.is_dir():
                return {"error": f"Path is not a directory: {dir_path}"}
            
            files = []
            search_pattern = "**/" + pattern if recursive else pattern
            
            for file_path in dir_path.glob(search_pattern):
                if file_path.is_file():
                    stat = file_path.stat()
                    files.append({
                        "name": file_path.name,
                        "path": str(file_path.relative_to(dir_path)),
                        "full_path": str(file_path),
                        "size": stat.st_size,
                        "extension": file_path.suffix,
                        "mime_type": mimetypes.guess_type(str(file_path))[0] or 'unknown',
                        "modified_time": datetime.fromtimestamp(stat.st_mtime).isoformat(),
                        "is_allowed": file_path.suffix.lower() in self.allowed_extensions
                    })
            
            # Sort by name
            files.sort(key=lambda x: x['name'])
            
            return {
                "success": True,
                "directory": str(dir_path),
                "pattern": pattern,
                "recursive": recursive,
                "file_count": len(files),
                "files": files
            }
            
        except Exception as e:
            return {"error": str(e)}
    
    async def analyze_codebase(self, directory: str, languages: List[str] = None) -> Dict[str, Any]:
        """Analyze a codebase for structure and metrics"""
        try:
            dir_path = Path(directory)
            
            if not self._is_safe_path(dir_path):
                return {"error": "Access denied: Directory path not allowed"}
            
            if not dir_path.exists() or not dir_path.is_dir():
                return {"error": f"Directory not found: {dir_path}"}
            
            analysis = {
                "success": True,
                "directory": str(dir_path),
                "analyzed_at": datetime.now().isoformat(),
                "languages": {},
                "file_types": {},
                "total_files": 0,
                "total_lines": 0,
                "total_size": 0,
                "largest_files": [],
                "recent_files": []
            }
            
            # Language extensions mapping
            lang_extensions = {
                'python': ['.py'],
                'javascript': ['.js', '.jsx'],
                'typescript': ['.ts', '.tsx'],
                'java': ['.java'],
                'cpp': ['.cpp', '.cc', '.cxx'],
                'c': ['.c'],
                'go': ['.go'],
                'rust': ['.rs'],
                'php': ['.php'],
                'ruby': ['.rb'],
                'swift': ['.swift'],
                'kotlin': ['.kt'],
                'scala': ['.scala']
            }
            
            files_analyzed = []
            
            # Recursively analyze files
            for file_path in dir_path.rglob("*"):
                if not file_path.is_file():
                    continue
                
                # Skip hidden files and common ignore patterns
                if any(part.startswith('.') for part in file_path.parts):
                    continue
                
                if any(ignore in str(file_path) for ignore in ['node_modules', '__pycache__', '.git']):
                    continue
                
                try:
                    stat = file_path.stat()
                    ext = file_path.suffix.lower()
                    
                    # Count file types
                    analysis['file_types'][ext] = analysis['file_types'].get(ext, 0) + 1
                    analysis['total_files'] += 1
                    analysis['total_size'] += stat.st_size
                    
                    # Analyze code files
                    if ext in self.allowed_extensions:
                        try:
                            async with aiofiles.open(file_path, 'r', encoding='utf-8') as f:
                                content = await f.read()
                            
                            lines = content.count('\n') + 1
                            analysis['total_lines'] += lines
                            
                            # Determine language
                            language = None
                            for lang, extensions in lang_extensions.items():
                                if ext in extensions:
                                    language = lang
                                    break
                            
                            if language and (not languages or language in languages):
                                if language not in analysis['languages']:
                                    analysis['languages'][language] = {
                                        'files': 0,
                                        'lines': 0,
                                        'size': 0
                                    }
                                
                                analysis['languages'][language]['files'] += 1
                                analysis['languages'][language]['lines'] += lines
                                analysis['languages'][language]['size'] += stat.st_size
                            
                            files_analyzed.append({
                                'path': str(file_path.relative_to(dir_path)),
                                'size': stat.st_size,
                                'lines': lines,
                                'language': language,
                                'modified': stat.st_mtime
                            })
                            
                        except (UnicodeDecodeError, PermissionError):
                            continue
                
                except (OSError, PermissionError):
                    continue
            
            # Find largest files
            analysis['largest_files'] = sorted(
                files_analyzed,
                key=lambda x: x['size'],
                reverse=True
            )[:10]
            
            # Find most recently modified files
            analysis['recent_files'] = sorted(
                files_analyzed,
                key=lambda x: x['modified'],
                reverse=True
            )[:10]
            
            # Clean up timestamps in recent files
            for file_info in analysis['recent_files']:
                file_info['modified'] = datetime.fromtimestamp(file_info['modified']).isoformat()
            
            return analysis
            
        except Exception as e:
            return {"error": str(e)}
    
    async def get_file_info(self, file_path: str) -> Dict[str, Any]:
        """Get metadata information about a file"""
        try:
            file_path = Path(file_path)
            
            if not self._is_safe_path(file_path):
                return {"error": "Access denied: File path not allowed"}
            
            if not file_path.exists():
                return {"error": f"File not found: {file_path}"}
            
            stat = file_path.stat()
            
            return {
                "success": True,
                "file_path": str(file_path),
                "file_name": file_path.name,
                "file_size": stat.st_size,
                "file_extension": file_path.suffix,
                "mime_type": mimetypes.guess_type(str(file_path))[0] or 'unknown',
                "created_time": datetime.fromtimestamp(stat.st_ctime).isoformat(),
                "modified_time": datetime.fromtimestamp(stat.st_mtime).isoformat(),
                "is_file": file_path.is_file(),
                "is_directory": file_path.is_dir(),
                "is_allowed": file_path.suffix.lower() in self.allowed_extensions,
                "permissions": {
                    "readable": os.access(file_path, os.R_OK),
                    "writable": os.access(file_path, os.W_OK),
                    "executable": os.access(file_path, os.X_OK)
                }
            }
            
        except Exception as e:
            return {"error": str(e)}


async def main():
    """Main entry point for the filesystem MCP server"""
    parser = argparse.ArgumentParser(description="Filesystem MCP Server")
    parser.add_argument("--allowed-dirs", nargs='+', required=True, help="Allowed directories")
    parser.add_argument("--max-file-size", default="25MB", help="Maximum file size")
    parser.add_argument("--allowed-extensions", help="Comma-separated list of allowed extensions")
    parser.add_argument("--port", type=int, default=8002, help="WebSocket port")
    
    args = parser.parse_args()
    
    # Configure logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # Create and start server
    server = FilesystemMCPServer(
        allowed_dirs=args.allowed_dirs,
        max_file_size=args.max_file_size,
        allowed_extensions=args.allowed_extensions,
        port=args.port
    )
    
    try:
        await server.start()
    except KeyboardInterrupt:
        logger.info("Shutting down filesystem MCP server...")
    except Exception as e:
        logger.error(f"Filesystem MCP server error: {e}")
        raise


if __name__ == "__main__":
    asyncio.run(main())