#!/usr/bin/env python3
"""
PostgreSQL Vector Storage and RAG for BotForge
==============================================

Provides vector storage, document embedding, and retrieval-augmented generation
capabilities using PostgreSQL with pgvector extension for intelligent document 
search and context retrieval.
"""

import os
import logging
import json
import hashlib
import asyncio
from datetime import datetime
from typing import Dict, List, Optional, Any, Union, Tuple
from pathlib import Path
import psycopg2
from psycopg2.extras import RealDictCursor
import asyncpg
import numpy as np

# Vector embeddings
import openai
from sentence_transformers import SentenceTransformer

# Document processing
import tiktoken
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain.document_loaders import TextLoader, DirectoryLoader
from langchain.schema import Document

logger = logging.getLogger(__name__)

class PostgreSQLVectorStorage:
    """PostgreSQL-based vector storage and RAG capabilities for document search"""
    
    def __init__(self, 
                 connection_string: str = None,
                 embedding_model: str = "text-embedding-3-small",
                 chunk_size: int = 1000,
                 chunk_overlap: int = 200):
        
        self.connection_string = connection_string or self._build_connection_string()
        self.embedding_model = embedding_model
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
        
        # Initialize embeddings
        self.openai_embeddings = None
        self.sentence_transformer = None
        self._init_embeddings()
        
        # Initialize text splitter
        self.text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap,
            length_function=len,
            separators=["\n\n", "\n", " ", ""]
        )
        
        # Connection pool
        self.pool = None
    
    def _build_connection_string(self) -> str:
        """Build PostgreSQL connection string from environment variables"""
        host = os.getenv('POSTGRES_HOST', 'localhost')
        port = os.getenv('POSTGRES_PORT', '5436')
        database = os.getenv('POSTGRES_DB', 'botforge')
        username = os.getenv('POSTGRES_USER', 'botforge')
        password = os.getenv('POSTGRES_PASSWORD', 'botforge-db-2025')
        
        return f"postgresql://{username}:{password}@{host}:{port}/{database}"
    
    async def initialize(self):
        """Initialize the connection pool"""
        try:
            self.pool = await asyncpg.create_pool(self.connection_string)
            logger.info("✅ PostgreSQL connection pool initialized")
        except Exception as e:
            logger.error(f"❌ Failed to initialize PostgreSQL connection pool: {e}")
            raise
    
    async def close(self):
        """Close the connection pool"""
        if self.pool:
            await self.pool.close()
            logger.info("PostgreSQL connection pool closed")
    
    def _init_embeddings(self):
        """Initialize embedding models"""
        try:
            # Try OpenAI embeddings first
            if os.getenv('OPENAI_API_KEY'):
                openai.api_key = os.getenv('OPENAI_API_KEY')
                self.openai_embeddings = True
                logger.info("✅ OpenAI embeddings initialized")
            else:
                logger.warning("⚠️ OpenAI API key not found")
        except Exception as e:
            logger.warning(f"⚠️ Failed to initialize OpenAI embeddings: {e}")
        
        try:
            # Fallback to sentence transformers
            self.sentence_transformer = SentenceTransformer('all-MiniLM-L6-v2')
            logger.info("✅ SentenceTransformer initialized as fallback")
        except Exception as e:
            logger.error(f"❌ Failed to initialize SentenceTransformer: {e}")
    
    async def embed_text(self, text: str) -> List[float]:
        """Generate embeddings for text"""
        try:
            if self.openai_embeddings:
                response = await openai.Embedding.acreate(
                    model=self.embedding_model,
                    input=text
                )
                return response['data'][0]['embedding']
            elif self.sentence_transformer:
                # Run in thread pool to avoid blocking
                loop = asyncio.get_event_loop()
                embeddings = await loop.run_in_executor(
                    None, 
                    self.sentence_transformer.encode, 
                    text
                )
                return embeddings.tolist()
            else:
                raise Exception("No embedding model available")
        
        except Exception as e:
            logger.error(f"Error generating embeddings: {e}")
            raise
    
    async def add_document(self, 
                          content: str, 
                          metadata: Dict[str, Any], 
                          collection_name: str = "documents") -> Dict[str, Any]:
        """
        Add a document to the vector store
        
        Args:
            content: Document content
            metadata: Document metadata (title, source, type, etc.)
            collection_name: Collection to add to
            
        Returns:
            Dict with operation result
        """
        try:
            if not self.pool:
                await self.initialize()
            
            # Split document into chunks
            documents = self.text_splitter.split_text(content)
            
            # Generate unique document ID
            doc_id = hashlib.md5(content.encode()).hexdigest()
            
            async with self.pool.acquire() as conn:
                # Insert chunks with embeddings
                inserted_chunks = 0
                for i, chunk in enumerate(documents):
                    if not chunk.strip():
                        continue
                    
                    # Generate embeddings
                    embeddings = await self.embed_text(chunk)
                    
                    # Prepare metadata for this chunk
                    chunk_metadata = metadata.copy()
                    chunk_metadata.update({
                        "chunk_index": i,
                        "chunk_count": len(documents),
                        "doc_id": doc_id,
                        "added_at": datetime.now().isoformat(),
                        "content_length": len(chunk)
                    })
                    
                    # Insert into database
                    await conn.execute("""
                        INSERT INTO document_embeddings 
                        (document_id, chunk_index, content, embedding, metadata, collection_name)
                        VALUES ($1, $2, $3, $4, $5, $6)
                        ON CONFLICT (document_id, chunk_index) DO UPDATE SET
                        content = EXCLUDED.content,
                        embedding = EXCLUDED.embedding,
                        metadata = EXCLUDED.metadata,
                        updated_at = NOW()
                    """, doc_id, i, chunk, embeddings, json.dumps(chunk_metadata), collection_name)
                    
                    inserted_chunks += 1
            
            return {
                "success": True,
                "doc_id": doc_id,
                "chunks_added": inserted_chunks,
                "collection": collection_name,
                "metadata": metadata
            }
            
        except Exception as e:
            logger.error(f"Error adding document: {e}")
            return {"error": str(e)}
    
    async def search_documents(self, 
                              query: str, 
                              collection_name: str = "documents",
                              limit: int = 10,
                              similarity_threshold: float = 0.7,
                              metadata_filter: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Search for relevant documents
        
        Args:
            query: Search query
            collection_name: Collection to search in
            limit: Maximum number of results
            similarity_threshold: Minimum similarity score
            metadata_filter: Optional metadata filters
            
        Returns:
            Dict with search results
        """
        try:
            if not self.pool:
                await self.initialize()
            
            # Generate query embedding
            query_embedding = await self.embed_text(query)
            
            async with self.pool.acquire() as conn:
                # Use the PostgreSQL function for similarity search
                results = await conn.fetch("""
                    SELECT * FROM search_similar_documents($1, $2, $3, $4)
                """, query_embedding, collection_name, similarity_threshold, limit)
                
                # Process results
                search_results = []
                for row in results:
                    metadata = json.loads(row['metadata']) if row['metadata'] else {}
                    
                    # Apply metadata filter if specified
                    if metadata_filter:
                        if not all(metadata.get(key) == value for key, value in metadata_filter.items()):
                            continue
                    
                    search_results.append({
                        "content": row['content'],
                        "metadata": metadata,
                        "similarity_score": round(float(row['similarity']), 4),
                        "document_id": row['document_id'],
                        "collection": row['collection_name']
                    })
            
            return {
                "success": True,
                "query": query,
                "collection": collection_name,
                "results_count": len(search_results),
                "results": search_results,
                "similarity_threshold": similarity_threshold
            }
            
        except Exception as e:
            logger.error(f"Error searching documents: {e}")
            return {"error": str(e)}
    
    async def add_conversation_memory(self, 
                                    conversation_id: str, 
                                    messages: List[Dict[str, str]], 
                                    summary: Optional[str] = None) -> Dict[str, Any]:
        """
        Add conversation to long-term memory for future retrieval
        
        Args:
            conversation_id: Unique conversation identifier
            messages: List of message objects with role and content
            summary: Optional conversation summary
            
        Returns:
            Dict with operation result
        """
        try:
            if not self.pool:
                await self.initialize()
            
            # Create conversation summary
            if not summary:
                conversation_text = ""
                for msg in messages:
                    role = msg.get('role', 'unknown')
                    content = msg.get('content', '')
                    conversation_text += f"{role}: {content}\n\n"
                summary = conversation_text[:500] + "..." if len(conversation_text) > 500 else conversation_text
            
            # Generate embedding for the summary
            embedding = await self.embed_text(summary)
            
            async with self.pool.acquire() as conn:
                # Insert conversation embedding
                await conn.execute("""
                    INSERT INTO conversation_embeddings 
                    (conversation_id, summary, embedding, participant_count, message_count)
                    VALUES ($1, $2, $3, $4, $5)
                    ON CONFLICT (conversation_id) DO UPDATE SET
                    summary = EXCLUDED.summary,
                    embedding = EXCLUDED.embedding,
                    participant_count = EXCLUDED.participant_count,
                    message_count = EXCLUDED.message_count
                """, conversation_id, summary, embedding, 
                len(set(msg.get('role', 'unknown') for msg in messages)), len(messages))
            
            return {
                "success": True,
                "conversation_id": conversation_id,
                "summary": summary,
                "message_count": len(messages)
            }
            
        except Exception as e:
            logger.error(f"Error adding conversation memory: {e}")
            return {"error": str(e)}
    
    async def retrieve_relevant_context(self, 
                                       query: str, 
                                       max_tokens: int = 2000,
                                       collections: Optional[List[str]] = None) -> Dict[str, Any]:
        """
        Retrieve relevant context for RAG (Retrieval-Augmented Generation)
        
        Args:
            query: User query or context to search for
            max_tokens: Maximum tokens in the returned context
            collections: Collections to search in (default: documents)
            
        Returns:
            Dict with relevant context and metadata
        """
        try:
            if collections is None:
                collections = ["documents", "code", "conversations", "team_knowledge"]
            
            all_results = []
            
            # Search across specified collections
            for collection_name in collections:
                search_result = await self.search_documents(
                    query=query,
                    collection_name=collection_name,
                    limit=5
                )
                
                if search_result.get("success") and search_result.get("results"):
                    for result in search_result["results"]:
                        result["collection"] = collection_name
                        all_results.append(result)
            
            # Sort by similarity score
            all_results.sort(key=lambda x: x["similarity_score"], reverse=True)
            
            # Build context within token limit
            context_parts = []
            token_count = 0
            
            # Use tiktoken to count tokens
            try:
                encoding = tiktoken.get_encoding("cl100k_base")
            except:
                # Fallback to simple character counting
                encoding = None
            
            for result in all_results:
                content = result["content"]
                metadata = result["metadata"]
                
                # Estimate tokens
                if encoding:
                    content_tokens = len(encoding.encode(content))
                else:
                    content_tokens = len(content) // 4  # Rough estimate
                
                if token_count + content_tokens > max_tokens:
                    break
                
                # Add to context
                source_info = ""
                if metadata.get("title"):
                    source_info = f"From: {metadata['title']}"
                elif metadata.get("file_name"):
                    source_info = f"From: {metadata['file_name']}"
                elif metadata.get("type"):
                    source_info = f"From: {metadata['type']}"
                
                context_part = f"{source_info}\n{content}\n---\n"
                context_parts.append(context_part)
                token_count += content_tokens
            
            context = "\n".join(context_parts)
            
            return {
                "success": True,
                "query": query,
                "context": context,
                "token_count": token_count,
                "source_count": len(context_parts),
                "collections_searched": collections,
                "sources": [
                    {
                        "content_preview": result["content"][:100] + "...",
                        "similarity": result["similarity_score"],
                        "collection": result["collection"],
                        "metadata": result["metadata"]
                    } for result in all_results[:len(context_parts)]
                ]
            }
            
        except Exception as e:
            logger.error(f"Error retrieving context: {e}")
            return {"error": str(e)}
    
    async def add_code_repository(self, repo_path: str, repo_name: str) -> Dict[str, Any]:
        """
        Index a code repository for search
        
        Args:
            repo_path: Path to the repository
            repo_name: Name identifier for the repository
            
        Returns:
            Dict with indexing results
        """
        try:
            if not self.pool:
                await self.initialize()
            
            repo_path = Path(repo_path)
            if not repo_path.exists():
                return {"error": f"Repository path not found: {repo_path}"}
            
            indexed_files = 0
            skipped_files = 0
            
            # Supported code file extensions
            code_extensions = {
                '.py', '.js', '.ts', '.jsx', '.tsx', '.java', '.cpp', '.c', '.h',
                '.go', '.rs', '.php', '.rb', '.swift', '.kt', '.scala', '.sql',
                '.yaml', '.yml', '.json', '.md', '.txt', '.sh', '.dockerfile'
            }
            
            async with self.pool.acquire() as conn:
                for file_path in repo_path.rglob("*"):
                    if not file_path.is_file():
                        continue
                    
                    # Skip hidden files and common ignore patterns
                    if any(part.startswith('.') for part in file_path.parts):
                        continue
                    
                    if any(ignore in str(file_path) for ignore in [
                        'node_modules', '__pycache__', '.git', 'venv', 'env', 
                        'build', 'dist', 'target', '.idea', '.vscode'
                    ]):
                        continue
                    
                    if file_path.suffix.lower() not in code_extensions:
                        skipped_files += 1
                        continue
                    
                    try:
                        # Read file content
                        with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                            content = f.read()
                        
                        # Skip very large files
                        if len(content) > 100000:  # 100KB limit
                            skipped_files += 1
                            continue
                        
                        # Split into chunks
                        chunks = self.text_splitter.split_text(content)
                        
                        for i, chunk in enumerate(chunks):
                            if not chunk.strip():
                                continue
                            
                            # Generate embeddings
                            embeddings = await self.embed_text(chunk)
                            
                            # Prepare metadata
                            metadata = {
                                "type": "code_file",
                                "repository": repo_name,
                                "file_path": str(file_path.relative_to(repo_path)),
                                "file_name": file_path.name,
                                "file_extension": file_path.suffix,
                                "language": self._detect_language(file_path.suffix),
                                "file_size": len(content),
                                "line_count": content.count('\n') + 1
                            }
                            
                            # Insert into database
                            await conn.execute("""
                                INSERT INTO code_embeddings 
                                (repository_name, file_path, chunk_index, content, embedding, language, file_size, line_count, metadata)
                                VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9)
                                ON CONFLICT (repository_name, file_path, chunk_index) DO UPDATE SET
                                content = EXCLUDED.content,
                                embedding = EXCLUDED.embedding,
                                language = EXCLUDED.language,
                                file_size = EXCLUDED.file_size,
                                line_count = EXCLUDED.line_count,
                                metadata = EXCLUDED.metadata
                            """, repo_name, str(file_path.relative_to(repo_path)), i, chunk, 
                            embeddings, metadata["language"], metadata["file_size"], 
                            metadata["line_count"], json.dumps(metadata))
                        
                        indexed_files += 1
                        
                    except Exception as e:
                        skipped_files += 1
                        logger.warning(f"Error indexing {file_path}: {e}")
            
            return {
                "success": True,
                "repository": repo_name,
                "repository_path": str(repo_path),
                "indexed_files": indexed_files,
                "skipped_files": skipped_files,
                "total_processed": indexed_files + skipped_files
            }
            
        except Exception as e:
            logger.error(f"Error indexing repository: {e}")
            return {"error": str(e)}
    
    def _detect_language(self, extension: str) -> str:
        """Detect programming language from file extension"""
        lang_map = {
            '.py': 'python',
            '.js': 'javascript',
            '.ts': 'typescript',
            '.jsx': 'javascript',
            '.tsx': 'typescript',
            '.java': 'java',
            '.cpp': 'cpp',
            '.c': 'c',
            '.h': 'c',
            '.go': 'go',
            '.rs': 'rust',
            '.php': 'php',
            '.rb': 'ruby',
            '.swift': 'swift',
            '.kt': 'kotlin',
            '.scala': 'scala',
            '.sql': 'sql',
            '.sh': 'bash',
            '.yaml': 'yaml',
            '.yml': 'yaml',
            '.json': 'json',
            '.md': 'markdown',
            '.txt': 'text'
        }
        return lang_map.get(extension.lower(), 'unknown')
    
    async def get_collection_stats(self) -> Dict[str, Any]:
        """Get statistics about all collections"""
        try:
            if not self.pool:
                await self.initialize()
            
            async with self.pool.acquire() as conn:
                # Get document embedding stats
                doc_stats = await conn.fetch("""
                    SELECT collection_name, COUNT(*) as count 
                    FROM document_embeddings 
                    GROUP BY collection_name
                """)
                
                # Get conversation stats
                conv_count = await conn.fetchval("SELECT COUNT(*) FROM conversation_embeddings")
                
                # Get code stats
                code_stats = await conn.fetch("""
                    SELECT repository_name, COUNT(*) as count 
                    FROM code_embeddings 
                    GROUP BY repository_name
                """)
                
                collections = {}
                for row in doc_stats:
                    collections[row['collection_name']] = {"document_count": row['count']}
                
                collections["conversations"] = {"document_count": conv_count or 0}
                
                for row in code_stats:
                    collections[f"code_{row['repository_name']}"] = {"document_count": row['count']}
                
                total_docs = sum(c["document_count"] for c in collections.values())
                
                return {
                    "success": True,
                    "collections": collections,
                    "total_documents": total_docs
                }
            
        except Exception as e:
            logger.error(f"Error getting collection stats: {e}")
            return {"error": str(e)}


def get_rag_tools_schema() -> List[Dict[str, Any]]:
    """
    Get the function schema for RAG tools that can be used by LLMs
    
    Returns:
        List of function schemas for OpenAI/Anthropic function calling
    """
    return [
        {
            "name": "search_documents",
            "description": "Search for relevant documents, code, or past conversations using semantic similarity. Perfect for finding information, code examples, or related discussions.",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "Search query - describe what you're looking for"
                    },
                    "collection_name": {
                        "type": "string",
                        "description": "Collection to search: 'documents', 'code', 'conversations', or 'team_knowledge'",
                        "enum": ["documents", "code", "conversations", "team_knowledge"],
                        "default": "documents"
                    },
                    "limit": {
                        "type": "integer",
                        "description": "Maximum number of results to return",
                        "default": 10
                    }
                },
                "required": ["query"]
            }
        },
        {
            "name": "retrieve_relevant_context",
            "description": "Retrieve comprehensive context for a query by searching across multiple document collections. Use this when you need background information for a detailed response.",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "Query or topic to retrieve context for"
                    },
                    "max_tokens": {
                        "type": "integer",
                        "description": "Maximum tokens in returned context",
                        "default": 2000
                    },
                    "collections": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Collections to search in (optional)"
                    }
                },
                "required": ["query"]
            }
        },
        {
            "name": "add_document",
            "description": "Add a document to the knowledge base for future retrieval. Use this to store important information, documentation, or team knowledge.",
            "parameters": {
                "type": "object",
                "properties": {
                    "content": {
                        "type": "string",
                        "description": "Document content to store"
                    },
                    "metadata": {
                        "type": "object",
                        "description": "Document metadata (title, source, type, tags, etc.)"
                    },
                    "collection_name": {
                        "type": "string",
                        "description": "Collection to add to",
                        "enum": ["documents", "code", "conversations", "team_knowledge"],
                        "default": "documents"
                    }
                },
                "required": ["content", "metadata"]
            }
        },
        {
            "name": "add_code_repository",
            "description": "Index an entire code repository for search. Use this to make a codebase searchable for architecture reviews and code analysis.",
            "parameters": {
                "type": "object",
                "properties": {
                    "repo_path": {
                        "type": "string",
                        "description": "Path to the code repository"
                    },
                    "repo_name": {
                        "type": "string",
                        "description": "Name identifier for the repository"
                    }
                },
                "required": ["repo_path", "repo_name"]
            }
        }
    ]