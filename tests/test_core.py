"""
Tests for Athena core modules
"""
import pytest
import tempfile
from pathlib import Path

from athena.memory import Memory, MemoryError
from athena.tools import ToolRegistry, Tool, ToolError
from athena.agent import Agent, LLMConnectionError
from athena.sessions import SessionManager, Session
from athena.cron import CronScheduler, CronJob, JobStatus, CronParser
from athena.web import WebSearcher, URLFetcher


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
        assert not self.memory.delete(99999)
    
    def test_count(self):
        """Test counting memories."""
        assert self.memory.count() == 0
        
        self.memory.save("One")
        self.memory.save("Two")
        assert self.memory.count() == 2
        assert self.memory.count(category="general") == 2
    
    def test_get_categories(self):
        """Test getting categories."""
        self.memory.save("Tech", category="tech")
        self.memory.save("Personal", category="personal")
        
        categories = self.memory.get_categories()
        assert "personal" in categories
        assert "tech" in categories
    
    def test_clear(self):
        """Test clearing memories."""
        self.memory.save("One")
        self.memory.save("Two")
        assert self.memory.count() == 2
        
        self.memory.clear()
        assert self.memory.count() == 0
    
    def test_empty_search(self):
        """Test empty search query."""
        results = self.memory.search("")
        assert results == []
    
    def test_empty_content_error(self):
        """Test saving empty content raises error."""
        with pytest.raises(ValueError):
            self.memory.save("")
        with pytest.raises(ValueError):
            self.memory.save("   ")


class TestTool:
    """Test Tool class."""
    
    def test_basic_tool(self):
        """Test basic tool creation."""
        def greet(name: str) -> str:
            """Greet someone."""
            return f"Hello, {name}!"
        
        tool = Tool(greet, "greet")
        assert tool.name == "greet"
        assert tool.description == "Greet someone."
        assert "name" in tool.parameters
    
    def test_tool_execution(self):
        """Test tool execution."""
        def add(a: int, b: int) -> int:
            """Add two numbers."""
            return a + b
        
        tool = Tool(add, "add")
        result = tool.execute(a=5, b=3)
        assert result == 8
    
    def test_tool_missing_param(self):
        """Test tool with missing required parameter."""
        def greet(name: str) -> str:
            """Greet someone."""
            return f"Hello, {name}!"
        
        tool = Tool(greet, "greet")
        with pytest.raises(ToolError):
            tool.execute()


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
    
    def test_remove_tool(self):
        """Test removing a tool."""
        @self.registry.register("temp")
        def temp() -> str:
            return "temp"
        
        assert self.registry.remove("temp")
        assert "temp" not in self.registry.tools
        assert not self.registry.remove("nonexistent")
    
    def test_clear_tools(self):
        """Test clearing all tools."""
        @self.registry.register("tool1")
        def tool1(): pass
        
        @self.registry.register("tool2")
        def tool2(): pass
        
        self.registry.clear()
        assert len(self.registry.tools) == 0
    
    def test_execute_unknown_tool(self):
        """Test executing unknown tool."""
        with pytest.raises(ToolError):
            self.registry.execute("nonexistent")


class TestAgent:
    """Test Agent class."""
    
    def setup_method(self):
        """Setup agent with temp memory."""
        self.tmp_dir = tempfile.mkdtemp()
        self.db_path = Path(self.tmp_dir) / "test_memory.db"
    
    def test_agent_init(self):
        """Test agent initialization."""
        agent = Agent(
            memory_path=str(self.db_path),
            skip_provider_init=True
        )
        assert agent.memory is not None
        assert agent.tools is not None
    
    def test_builtin_tools_registered(self):
        """Test that built-in tools are registered."""
        agent = Agent(memory_path=str(self.db_path), skip_provider_init=True)
        tool_names = list(agent.tools.tools.keys())
        assert "memory_search" in tool_names
        assert "memory_save" in tool_names
        assert "get_time" in tool_names
        assert "run_command" in tool_names
    
    def test_parse_tool_args(self):
        """Test tool argument parsing."""
        args = Agent._parse_tool_args("name='hello', count=5")
        assert args["name"] == "hello"
        assert args["count"] == 5
        
        args = Agent._parse_tool_args('name="world"')
        assert args["name"] == "world"
        
        args = Agent._parse_tool_args("")
        assert args == {}
    
    def test_format_size(self):
        """Test file size formatting."""
        assert Agent._format_size(500) == "500.0B"
        assert Agent._format_size(1500) == "1.5KB"
        assert Agent._format_size(1_500_000) == "1.4MB"
        assert Agent._format_size(1_500_000_000) == "1.4GB"


class TestSessions:
    """Test Session Manager."""
    
    def setup_method(self):
        """Setup test database."""
        self.tmp_dir = tempfile.mkdtemp()
        self.db_path = Path(self.tmp_dir) / "test_sessions.db"
        self.manager = SessionManager(str(self.db_path))
    
    def test_create_session(self):
        """Test creating a session."""
        session = self.manager.create_session("Test Session")
        assert session.id.startswith("session_")
        assert session.title == "Test Session"
    
    def test_get_session(self):
        """Test getting a session."""
        session = self.manager.create_session("Test")
        retrieved = self.manager.get_session(session.id)
        assert retrieved is not None
        assert retrieved.title == "Test"
    
    def test_list_sessions(self):
        """Test listing sessions."""
        self.manager.create_session("Session 1")
        self.manager.create_session("Session 2")
        
        sessions = self.manager.list_sessions()
        assert len(sessions) == 2
    
    def test_add_message(self):
        """Test adding messages."""
        session = self.manager.create_session("Test")
        
        self.manager.add_message(session.id, "user", "Hello")
        self.manager.add_message(session.id, "assistant", "Hi there!")
        
        messages = self.manager.get_messages(session.id)
        assert len(messages) == 2
        assert messages[0].role == "user"
        assert messages[1].role == "assistant"
    
    def test_delete_session(self):
        """Test deleting a session."""
        session = self.manager.create_session("To Delete")
        assert self.manager.delete_session(session.id)
        assert self.manager.get_session(session.id) is None
    
    def test_export_import(self):
        """Test export and import."""
        session = self.manager.create_session("Export Test")
        self.manager.add_message(session.id, "user", "Test message")
        
        exported = self.manager.export_session(session.id)
        assert exported is not None
        
        imported = self.manager.import_session(exported)
        assert imported is not None
        assert imported.title == "Export Test"


class TestCron:
    """Test Cron Scheduler."""
    
    def setup_method(self):
        """Setup test scheduler."""
        self.tmp_dir = tempfile.mkdtemp()
        self.storage_path = Path(self.tmp_dir) / "test_cron.json"
        self.scheduler = CronScheduler(str(self.storage_path))
    
    def test_add_job(self):
        """Test adding a job."""
        job = self.scheduler.add_job("test", "echo hello", schedule="every 1h")
        assert job.name == "test"
        assert job.schedule == "every 1h"
    
    def test_list_jobs(self):
        """Test listing jobs."""
        self.scheduler.add_job("job1", "echo 1")
        self.scheduler.add_job("job2", "echo 2")
        
        jobs = self.scheduler.list_jobs()
        assert len(jobs) == 2
    
    def test_pause_resume(self):
        """Test pausing and resuming jobs."""
        job = self.scheduler.add_job("test", "echo hello")
        
        assert self.scheduler.pause_job(job.id)
        paused = self.scheduler.get_job(job.id)
        assert not paused.enabled
        
        assert self.scheduler.resume_job(job.id)
        resumed = self.scheduler.get_job(job.id)
        assert resumed.enabled
    
    def test_remove_job(self):
        """Test removing a job."""
        job = self.scheduler.add_job("test", "echo hello")
        assert self.scheduler.remove_job(job.id)
        assert self.scheduler.get_job(job.id) is None
    
    def test_parse_interval(self):
        """Test interval parsing."""
        assert CronParser.parse_interval("30m") == 1800
        assert CronParser.parse_interval("2h") == 7200
        assert CronParser.parse_interval("1d") == 86400
        assert CronParser.parse_interval("every 5m") == 300
    
    def test_parse_cron(self):
        """Test cron expression parsing."""
        result = CronParser.parse_cron("0 * * * *")
        assert result is not None
        assert result["minute"] == "0"
        assert result["hour"] == "*"
    
    def test_persistence(self):
        """Test job persistence."""
        self.scheduler.add_job("persistent", "echo test")
        
        scheduler2 = CronScheduler(str(self.storage_path))
        jobs = scheduler2.list_jobs()
        assert len(jobs) == 1
        assert jobs[0].name == "persistent"


class TestWeb:
    """Test Web tools."""
    
    def test_searcher_init(self):
        """Test searcher initialization."""
        searcher = WebSearcher()
        assert searcher.timeout == 10
    
    def test_fetcher_init(self):
        """Test fetcher initialization."""
        fetcher = URLFetcher()
        assert fetcher.timeout == 15
