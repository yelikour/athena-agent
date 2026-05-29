"""
Tests for Athena core modules
"""
import pytest
import tempfile
from pathlib import Path

from athena.memory import Memory
from athena.tools import ToolRegistry


class TestMemory:
    """Test Memory module."""
    
    def setup_method(self):
        """Setup test database."""
        self.tmp_dir = tempfile.mkdtemp()
        self.db_path = Path(self.tmp_dir) / "test_memory.db"
        self.memory = Memory(str(self.db_path))
    
    def test_save_and_search(self):
        """Test saving and searching memories."""
        self.memory.save("Python is a programming language", category="tech")
        self.memory.save("Machine learning uses neural networks", category="tech")
        self.memory.save("The weather is sunny today", category="general")
        
        results = self.memory.search("programming")
        assert len(results) == 1
        assert "Python" in results[0]["content"]
    
    def test_category_filter(self):
        """Test category-based filtering."""
        self.memory.save("Tech info", category="tech")
        self.memory.save("Personal info", category="personal")
        
        results = self.memory.search("info", category="tech")
        assert len(results) == 1
        assert results[0]["category"] == "tech"
    
    def test_recent_memories(self):
        """Test getting recent memories."""
        for i in range(5):
            self.memory.save(f"Memory {i}")
        
        recent = self.memory.get_recent(limit=3)
        assert len(recent) == 3
    
    def test_delete_memory(self):
        """Test deleting memories."""
        memory_id = self.memory.save("To be deleted")
        assert self.memory.delete(memory_id)
        
        recent = self.memory.get_recent()
        assert len(recent) == 0
    
    def test_count(self):
        """Test counting memories."""
        assert self.memory.count() == 0
        
        self.memory.save("One")
        self.memory.save("Two")
        assert self.memory.count() == 2


class TestToolRegistry:
    """Test Tool Registry."""
    
    def setup_method(self):
        """Setup registry."""
        self.registry = ToolRegistry()
    
    def test_register_tool(self):
        """Test registering a tool via decorator."""
        @self.registry.register("greet")
        def greet(name: str) -> str:
            """Greet someone."""
            return f"Hello, {name}!"
        
        assert "greet" in self.registry.tools
        result = self.registry.execute("greet", name="World")
        assert result == "Hello, World!"
    
    def test_list_tools(self):
        """Test listing tools."""
        @self.registry.register("test_tool")
        def test_tool() -> str:
            """A test tool."""
            return "test"
        
        tools = self.registry.list_tools()
        assert "test_tool" in tools
        assert tools["test_tool"]["description"] == "A test tool."
    
    def test_mcp_schema(self):
        """Test MCP schema export."""
        @self.registry.register("search")
        def search(query: str) -> str:
            """Search for something."""
            return f"Results for {query}"
        
        schema = self.registry.to_mcp_schema()
        assert len(schema) == 1
        assert schema[0]["name"] == "search"
        assert "query" in schema[0]["inputSchema"]["properties"]
