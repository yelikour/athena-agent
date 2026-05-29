"""
Athena - Lightweight Local AI Agent

A minimal, privacy-first AI agent framework with multi-provider support.

Example:
    >>> from athena import Agent
    >>> agent = Agent()  # Auto-detect best provider
    >>> response = agent.chat("Hello!")
    >>> print(response)
"""
__version__ = "0.2.0"
__author__ = "夜理"

# Core
from .agent import Agent, AgentError, LLMConnectionError, ToolExecutionError
from .memory import Memory, MemoryError
from .tools import ToolRegistry, Tool, ToolError, MCPToolAdapter

# Sessions
from .sessions import SessionManager, Session, Message

# Cron
from .cron import CronScheduler, CronJob, JobStatus

# Providers
from .providers import (
    Provider, ProviderConfig, ProviderRegistry,
    OpenAICompatibleProvider, OllamaProvider,
    create_default_registry,
)

# Web
from .web import WebSearcher, URLFetcher, SearchResult

# Monitor
from .monitor import SystemMonitor, SystemInfo, register_monitor_tools

__all__ = [
    # Core
    "Agent",
    "AgentError",
    "LLMConnectionError",
    "ToolExecutionError",
    "Memory",
    "MemoryError",
    "ToolRegistry",
    "Tool",
    "ToolError",
    "MCPToolAdapter",
    
    # Sessions
    "SessionManager",
    "Session",
    "Message",
    
    # Cron
    "CronScheduler",
    "CronJob",
    "JobStatus",
    
    # Providers
    "Provider",
    "ProviderConfig",
    "ProviderRegistry",
    "OpenAICompatibleProvider",
    "OllamaProvider",
    "create_default_registry",
    
    # Web
    "WebSearcher",
    "URLFetcher",
    "SearchResult",
    
    # Monitor
    "SystemMonitor",
    "SystemInfo",
    "register_monitor_tools",
]
