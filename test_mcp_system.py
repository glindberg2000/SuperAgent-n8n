#!/usr/bin/env python3
"""
MCP System Test Suite
====================

Test the MCP implementation to ensure it works before switching over.
Tests basic functionality, server connections, and tool calls.
"""

import os
import asyncio
import logging
import json
from pathlib import Path
import tempfile

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class MCPSystemTester:
    """Test suite for MCP system components"""
    
    def __init__(self):
        self.test_results = {}
        self.temp_dir = None
    
    async def run_all_tests(self):
        """Run all MCP system tests"""
        logger.info("🧪 Starting MCP System Tests...")
        
        tests = [
            ("Basic Imports", self.test_imports),
            ("MCP Configuration", self.test_mcp_config),
            ("Vector Storage", self.test_vector_storage),
            ("Filesystem Server", self.test_filesystem_server),
            ("MCP Client", self.test_mcp_client),
            ("Bot Configuration", self.test_bot_config)
        ]
        
        for test_name, test_func in tests:
            try:
                logger.info(f"🔍 Running test: {test_name}")
                await test_func()
                self.test_results[test_name] = "✅ PASS"
                logger.info(f"✅ {test_name}: PASSED")
            except Exception as e:
                self.test_results[test_name] = f"❌ FAIL: {str(e)}"
                logger.error(f"❌ {test_name}: FAILED - {e}")
        
        # Print summary
        self.print_test_summary()
    
    async def test_imports(self):
        """Test that all MCP modules can be imported"""
        try:
            # Test basic imports
            import sys
            sys.path.append('/Users/greg/repos/SuperAgent-n8n/src')
            
            # Try importing our MCP modules
            from mcp_client import MCPClient, MCPServer
            logger.info("✓ MCP client imports successful")
            
            from vector_storage_postgres import PostgreSQLVectorStorage
            logger.info("✓ PostgreSQL vector storage imports successful")
            
            # Try importing MCP servers (they might fail due to missing deps)
            try:
                from mcp_servers.filesystem import FilesystemMCPServer
                logger.info("✓ Filesystem MCP server imports successful")
            except ImportError as e:
                logger.warning(f"⚠️ Filesystem server import issue: {e}")
            
            try:
                from mcp_servers.postgres import PostgreSQLMCPServer
                logger.info("✓ PostgreSQL MCP server imports successful")
            except ImportError as e:
                logger.warning(f"⚠️ PostgreSQL server import issue: {e}")
            
        except Exception as e:
            raise Exception(f"Import failed: {e}")
    
    async def test_mcp_config(self):
        """Test MCP configuration loading"""
        mcp_config_path = Path("/Users/greg/repos/SuperAgent-n8n/mcp.json")
        
        if not mcp_config_path.exists():
            raise Exception(f"MCP config file not found: {mcp_config_path}")
        
        with open(mcp_config_path) as f:
            config = json.load(f)
        
        # Check required sections
        if "mcpServers" not in config:
            raise Exception("Missing 'mcpServers' section in mcp.json")
        
        servers = config["mcpServers"]
        expected_servers = ["discord", "filesystem", "postgres"]
        
        for server in expected_servers:
            if server not in servers:
                raise Exception(f"Missing server config: {server}")
            
            server_config = servers[server]
            if "command" not in server_config:
                raise Exception(f"Missing 'command' in {server} config")
        
        logger.info(f"✓ MCP config valid with {len(servers)} servers")
    
    async def test_vector_storage(self):
        """Test PostgreSQL vector storage connection"""
        # Create a mock connection string for testing
        test_conn_string = "postgresql://test:test@localhost:5436/test"
        
        try:
            from vector_storage_postgres import PostgreSQLVectorStorage
            
            # Create instance (won't actually connect without real DB)
            storage = PostgreSQLVectorStorage(connection_string=test_conn_string)
            
            # Test configuration
            assert storage.embedding_model == "text-embedding-3-small"
            assert storage.chunk_size == 1000
            assert storage.chunk_overlap == 200
            
            logger.info("✓ Vector storage configuration valid")
            
            # Test text splitter
            test_text = "This is a test document. " * 100
            chunks = storage.text_splitter.split_text(test_text)
            assert len(chunks) > 1
            logger.info(f"✓ Text splitter working, created {len(chunks)} chunks")
            
        except Exception as e:
            raise Exception(f"Vector storage test failed: {e}")
    
    async def test_filesystem_server(self):
        """Test filesystem MCP server basic functionality"""
        # Create temporary directory for testing
        with tempfile.TemporaryDirectory() as temp_dir:
            self.temp_dir = temp_dir
            
            try:
                from mcp_servers.filesystem import FilesystemMCPServer
                
                # Create server instance
                server = FilesystemMCPServer(
                    allowed_dirs=[temp_dir],
                    max_file_size="1MB",
                    port=8099  # Use different port for testing
                )
                
                # Test path safety
                test_path = Path(temp_dir) / "test.txt"
                assert server._is_safe_path(test_path)
                
                # Test unsafe path
                unsafe_path = Path("/etc/passwd")
                assert not server._is_safe_path(unsafe_path)
                
                logger.info("✓ Filesystem server path safety checks working")
                
                # Test file operations (without actually starting server)
                test_content = "Hello, MCP World!"
                
                # Create test file
                with open(test_path, 'w') as f:
                    f.write(test_content)
                
                # Test read operation
                result = await server.read_file(str(test_path))
                assert result.get("success") == True
                assert result.get("content") == test_content
                
                logger.info("✓ Filesystem server file operations working")
                
            except Exception as e:
                raise Exception(f"Filesystem server test failed: {e}")
    
    async def test_mcp_client(self):
        """Test MCP client initialization and configuration"""
        try:
            from mcp_client import MCPClient
            
            # Test client creation
            client = MCPClient(config_path="/Users/greg/repos/SuperAgent-n8n/mcp.json")
            
            # Check configuration loading
            assert client.config_path == "/Users/greg/repos/SuperAgent-n8n/mcp.json"
            assert client.servers == {}
            assert client.all_tools == {}
            assert not client.is_initialized
            
            logger.info("✓ MCP client initialization successful")
            
            # Test tool schema generation (without actual servers)
            schemas = client.get_tools_schema()
            assert isinstance(schemas, list)
            
            logger.info("✓ MCP client tool schema generation working")
            
        except Exception as e:
            raise Exception(f"MCP client test failed: {e}")
    
    async def test_bot_config(self):
        """Test bot configuration loading"""
        config_path = Path("/Users/greg/repos/SuperAgent-n8n/config/bots.yaml")
        
        if not config_path.exists():
            raise Exception(f"Bot config not found: {config_path}")
        
        import yaml
        with open(config_path) as f:
            config = yaml.safe_load(f)
        
        # Check required sections
        if "bots" not in config:
            raise Exception("Missing 'bots' section in config")
        
        if "global" not in config:
            raise Exception("Missing 'global' section in config")
        
        bots = config["bots"]
        expected_bots = ["system_architect", "code_reviewer"]
        
        for bot_name in expected_bots:
            if bot_name not in bots:
                raise Exception(f"Missing bot config: {bot_name}")
            
            bot_config = bots[bot_name]
            required_fields = ["name", "llm_provider", "llm_model", "personality"]
            
            for field in required_fields:
                if field not in bot_config:
                    raise Exception(f"Missing field '{field}' in {bot_name} config")
        
        logger.info(f"✓ Bot configuration valid with {len(bots)} bots")
    
    def print_test_summary(self):
        """Print test results summary"""
        logger.info("\n" + "="*60)
        logger.info("🧪 MCP SYSTEM TEST RESULTS")
        logger.info("="*60)
        
        passed = 0
        failed = 0
        
        for test_name, result in self.test_results.items():
            logger.info(f"{result} {test_name}")
            if result.startswith("✅"):
                passed += 1
            else:
                failed += 1
        
        logger.info("="*60)
        logger.info(f"SUMMARY: {passed} passed, {failed} failed")
        
        if failed == 0:
            logger.info("🎉 ALL TESTS PASSED! MCP system is ready for basic testing.")
        else:
            logger.warning("⚠️ Some tests failed. Review issues before deployment.")
        
        logger.info("="*60)


async def main():
    """Run MCP system tests"""
    tester = MCPSystemTester()
    await tester.run_all_tests()


if __name__ == "__main__":
    asyncio.run(main())