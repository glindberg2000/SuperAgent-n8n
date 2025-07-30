#!/usr/bin/env python3
"""
File Operations for BotForge
============================

Provides file read/write capabilities and code analysis tools for LLMs.
Enables bots to work with documents, code files, and attachments.
"""

import os
import logging
import json
import yaml
from pathlib import Path
from typing import Dict, List, Optional, Any, Union
import mimetypes
import base64
import hashlib
from datetime import datetime
import asyncio
import aiofiles
import magic  # For file type detection

logger = logging.getLogger(__name__)

class FileOperations:
    """File operations and code analysis tools for LLM function calling"""
    
    def __init__(self, upload_directory: str = "/app/uploads", max_file_size_mb: int = 25):
        self.upload_dir = Path(upload_directory)
        self.max_file_size = max_file_size_mb * 1024 * 1024  # Convert to bytes
        self.allowed_extensions = {
            '.py', '.js', '.ts', '.md', '.txt', '.json', '.yaml', '.yml', 
            '.sql', '.sh', '.html', '.css', '.cpp', '.c', '.h', '.go', 
            '.rs', '.java', '.php', '.rb', '.swift', '.kt', '.scala',
            '.dockerfile', '.gitignore', '.env', '.toml', '.ini', '.cfg'
        }
        
        # Create upload directory if it doesn't exist
        self.upload_dir.mkdir(parents=True, exist_ok=True)
        
        # Initialize file type detector
        try:
            self.mime_detector = magic.Magic(mime=True)
        except:
            self.mime_detector = None
            logger.warning("python-magic not available, using basic mime detection")
    
    async def read_file(self, file_path: str, encoding: str = 'utf-8') -> Dict[str, Any]:
        """
        Read content from a file
        
        Args:
            file_path: Path to the file to read
            encoding: Text encoding (default: utf-8)
            
        Returns:
            Dict with file content and metadata
        """
        try:
            file_path = Path(file_path)
            
            # Security check - ensure file is within allowed areas
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
            file_info = {
                "success": True,
                "file_path": str(file_path),
                "file_name": file_path.name,
                "file_size": file_size,
                "file_extension": file_path.suffix,
                "mime_type": self._get_mime_type(file_path),
                "created_time": datetime.fromtimestamp(stat.st_ctime).isoformat(),
                "modified_time": datetime.fromtimestamp(stat.st_mtime).isoformat(),
                "content": content,
                "line_count": content.count('\n') + 1,
                "char_count": len(content),
                "encoding": encoding
            }
            
            # Add code analysis if it's a code file
            if self._is_code_file(file_path):
                file_info["code_analysis"] = await self._analyze_code(content, file_path.suffix)
            
            return file_info
            
        except UnicodeDecodeError:
            # Try binary read for non-text files
            try:
                async with aiofiles.open(file_path, 'rb') as f:
                    binary_content = await f.read()
                
                return {
                    "success": True,
                    "file_path": str(file_path),
                    "file_name": file_path.name,
                    "file_size": len(binary_content),
                    "mime_type": self._get_mime_type(file_path),
                    "content_type": "binary",
                    "content_base64": base64.b64encode(binary_content).decode('utf-8'),
                    "error": "File contains binary data, provided as base64"
                }
            except Exception as e:
                return {"error": f"Failed to read binary file: {e}"}
        
        except Exception as e:
            logger.error(f"Error reading file {file_path}: {e}")
            return {"error": str(e)}
    
    async def write_file(self, file_path: str, content: str, encoding: str = 'utf-8', overwrite: bool = False) -> Dict[str, Any]:
        """
        Write content to a file
        
        Args:
            file_path: Path where to write the file
            content: Content to write
            encoding: Text encoding (default: utf-8)
            overwrite: Whether to overwrite existing files
            
        Returns:
            Dict with operation result
        """
        try:
            file_path = Path(file_path)
            
            # Security check
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
            logger.error(f"Error writing file {file_path}: {e}")
            return {"error": str(e)}
    
    async def list_files(self, directory: str = ".", pattern: str = "*", recursive: bool = False) -> Dict[str, Any]:
        """
        List files in a directory
        
        Args:
            directory: Directory to list files from
            pattern: File pattern to match (e.g., "*.py")
            recursive: Whether to search subdirectories
            
        Returns:
            Dict with file listing
        """
        try:
            dir_path = Path(directory)
            
            # Security check
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
                        "mime_type": self._get_mime_type(file_path),
                        "modified_time": datetime.fromtimestamp(stat.st_mtime).isoformat(),
                        "is_code_file": self._is_code_file(file_path),
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
            logger.error(f"Error listing files in {directory}: {e}")
            return {"error": str(e)}
    
    async def analyze_codebase(self, directory: str, languages: Optional[List[str]] = None) -> Dict[str, Any]:
        """
        Analyze a codebase for structure, metrics, and insights
        
        Args:
            directory: Root directory of the codebase
            languages: List of programming languages to focus on
            
        Returns:
            Dict with codebase analysis
        """
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
                
                if any(ignore in str(file_path) for ignore in ['node_modules', '__pycache__', '.git', 'venv', 'env']):
                    continue
                
                try:
                    stat = file_path.stat()
                    ext = file_path.suffix.lower()
                    
                    # Count file types
                    analysis['file_types'][ext] = analysis['file_types'].get(ext, 0) + 1
                    analysis['total_files'] += 1
                    analysis['total_size'] += stat.st_size
                    
                    # Analyze code files
                    if ext in self.allowed_extensions and self._is_code_file(file_path):
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
                            continue  # Skip binary or inaccessible files
                
                except (OSError, PermissionError):
                    continue  # Skip files we can't access
            
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
            logger.error(f"Error analyzing codebase {directory}: {e}")
            return {"error": str(e)}
    
    def _is_safe_path(self, path: Path) -> bool:
        """Check if a file path is safe to access (security check)"""
        try:
            # Convert to absolute path
            abs_path = path.resolve()
            
            # Define allowed base directories
            allowed_bases = [
                Path("/app/uploads").resolve(),
                Path("/app/data").resolve(),
                Path("/tmp").resolve(),
                Path.cwd()  # Current working directory
            ]
            
            # Check if path is under any allowed base directory
            for base in allowed_bases:
                try:
                    abs_path.relative_to(base)
                    return True
                except ValueError:
                    continue
            
            return False
            
        except Exception:
            return False
    
    def _get_mime_type(self, file_path: Path) -> str:
        """Get MIME type of a file"""
        if self.mime_detector:
            try:
                return self.mime_detector.from_file(str(file_path))
            except:
                pass
        
        # Fallback to mimetypes module
        mime_type, _ = mimetypes.guess_type(str(file_path))
        return mime_type or 'application/octet-stream'
    
    def _is_code_file(self, file_path: Path) -> bool:
        """Check if a file is a code file based on extension"""
        code_extensions = {
            '.py', '.js', '.ts', '.jsx', '.tsx', '.java', '.cpp', '.c', '.h',
            '.go', '.rs', '.php', '.rb', '.swift', '.kt', '.scala', '.sql',
            '.sh', '.bash', '.yaml', '.yml', '.json', '.html', '.css'
        }
        return file_path.suffix.lower() in code_extensions
    
    async def _analyze_code(self, content: str, extension: str) -> Dict[str, Any]:
        """Basic code analysis"""
        lines = content.split('\n')
        
        analysis = {
            "total_lines": len(lines),
            "non_empty_lines": len([line for line in lines if line.strip()]),
            "comment_lines": 0,
            "function_count": 0,
            "class_count": 0,
            "import_count": 0
        }
        
        # Language-specific analysis
        if extension == '.py':
            for line in lines:
                stripped = line.strip()
                if stripped.startswith('#'):
                    analysis["comment_lines"] += 1
                elif stripped.startswith('def '):
                    analysis["function_count"] += 1
                elif stripped.startswith('class '):
                    analysis["class_count"] += 1
                elif stripped.startswith(('import ', 'from ')):
                    analysis["import_count"] += 1
        
        elif extension in ['.js', '.ts']:
            for line in lines:
                stripped = line.strip()
                if stripped.startswith('//') or stripped.startswith('/*'):
                    analysis["comment_lines"] += 1
                elif 'function ' in stripped or '=>' in stripped:
                    analysis["function_count"] += 1
                elif stripped.startswith('class '):
                    analysis["class_count"] += 1
                elif stripped.startswith(('import ', 'require(')):
                    analysis["import_count"] += 1
        
        return analysis


def get_file_tools_schema() -> List[Dict[str, Any]]:
    """
    Get the function schema for file operations that can be used by LLMs
    
    Returns:
        List of function schemas for OpenAI/Anthropic function calling
    """
    return [
        {
            "name": "read_file",
            "description": "Read content from a file. Use this to examine code, configuration files, documentation, or any text-based files.",
            "parameters": {
                "type": "object",
                "properties": {
                    "file_path": {
                        "type": "string",
                        "description": "Path to the file to read"
                    },
                    "encoding": {
                        "type": "string",
                        "description": "Text encoding (default: utf-8)",
                        "default": "utf-8"
                    }
                },
                "required": ["file_path"]
            }
        },
        {
            "name": "write_file",
            "description": "Write content to a file. Use this to create new files, update existing code, or save generated content.",
            "parameters": {
                "type": "object",
                "properties": {
                    "file_path": {
                        "type": "string",
                        "description": "Path where to write the file"
                    },
                    "content": {
                        "type": "string",
                        "description": "Content to write to the file"
                    },
                    "encoding": {
                        "type": "string",
                        "description": "Text encoding (default: utf-8)",
                        "default": "utf-8"
                    },
                    "overwrite": {
                        "type": "boolean",
                        "description": "Whether to overwrite existing files",
                        "default": false
                    }
                },
                "required": ["file_path", "content"]
            }
        },
        {
            "name": "list_files",
            "description": "List files in a directory. Use this to explore project structure, find specific files, or understand codebase organization.",
            "parameters": {
                "type": "object",
                "properties": {
                    "directory": {
                        "type": "string",
                        "description": "Directory to list files from",
                        "default": "."
                    },
                    "pattern": {
                        "type": "string",
                        "description": "File pattern to match (e.g., '*.py', '*.js')",
                        "default": "*"
                    },
                    "recursive": {
                        "type": "boolean",
                        "description": "Whether to search subdirectories",
                        "default": false
                    }
                },
                "required": []
            }
        },
        {
            "name": "analyze_codebase",
            "description": "Analyze a codebase for structure, metrics, and insights. Use this for architecture reviews, code audits, or understanding project composition.",
            "parameters": {
                "type": "object",
                "properties": {
                    "directory": {
                        "type": "string",
                        "description": "Root directory of the codebase to analyze"
                    },
                    "languages": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "List of programming languages to focus on (optional)"
                    }
                },
                "required": ["directory"]
            }
        }
    ]