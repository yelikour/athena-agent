"""
Core Agent - The brain of Athena
Handles conversation, tool calling, and reasoning loop.
"""
import json
import re
import sqlite3
from datetime import datetime
from typing import Optional, Dict, Any, List, Union
from pathlib import Path
import logging

from .memory import Memory
from .tools import ToolRegistry

logger = logging.getLogger(__name__)


class AgentError(Exception):
    """Base exception for Agent errors."""
    pass


class LLMConnectionError(AgentError):
    """Error connecting to LLM."""
    pass


class ToolExecutionError(AgentError):
    """Error executing a tool."""
    pass


class Agent:
    """
    A minimal AI agent with:
    - Local LLM inference (via Ollama)
    - Persistent memory (SQLite)
    - Tool calling (MCP-compatible)
    
    Example:
        >>> agent = Agent(model="llama3.2:3b")
        >>> response = agent.chat("What's the weather like?")
        >>> print(response)
    """
    
    def __init__(
        self,
        model: str = "llama3.2:3b",
        ollama_url: str = "http://localhost:11434",
        memory_path: str = "~/.athena/memory.db",
        system_prompt: Optional[str] = None,
        max_tool_rounds: int = 5,
    ):
        """
        Initialize the Agent.
        
        Args:
            model: Ollama model name
            ollama_url: Ollama API endpoint
            memory_path: Path to SQLite memory database
            system_prompt: Custom system prompt
            max_tool_rounds: Maximum tool call rounds per query
        """
        self.model = model
        self.ollama_url = ollama_url.rstrip("/")
        self.memory = Memory(memory_path)
        self.tools = ToolRegistry()
        self.conversation_history: List[Dict[str, str]] = []
        self.max_tool_rounds = max_tool_rounds
        
        self.system_prompt = system_prompt or self._default_system_prompt()
        
        # Register built-in tools
        self._register_builtin_tools()
    
    def _default_system_prompt(self) -> str:
        """Generate default system prompt."""
        return """You are Athena, a helpful AI assistant created to be useful, harmless, and honest.

## Core Capabilities
- Answer questions and have conversations
- Use tools to perform actions when needed
- Remember important information across sessions

## Tool Usage
When you need to use a tool, respond with exactly this format:
[TOOL: tool_name(param1='value1', param2='value2')]

You can call multiple tools by listing them on separate lines.
After receiving tool results, summarize them for the user.

## Guidelines
- Be concise and helpful
- Think step by step for complex tasks
- Admit when you don't know something
- Always be honest and transparent"""
    
    def _register_builtin_tools(self):
        """Register built-in tools."""
        @self.tools.register("memory_search")
        def memory_search(query: str, limit: int = 5) -> str:
            """Search your memory for relevant information."""
            results = self.memory.search(query, limit)
            if not results:
                return "No relevant memories found."
            return "\n".join([f"- [{r['category']}] {r['content'][:200]}" for r in results])
        
        @self.tools.register("memory_save")
        def memory_save(content: str, category: str = "general") -> str:
            """Save information to your memory for future reference."""
            memory_id = self.memory.save(content, category)
            return f"Saved to memory (id: {memory_id}, category: {category})"
        
        @self.tools.register("memory_recent")
        def memory_recent(limit: int = 5) -> str:
            """Get your most recent memories."""
            results = self.memory.get_recent(limit)
            if not results:
                return "No memories yet."
            return "\n".join([f"- [{r['category']}] {r['content'][:100]}" for r in results])
        
        @self.tools.register("run_command")
        def run_command(command: str) -> str:
            """Run a shell command and return the output. Use with caution."""
            import subprocess
            try:
                result = subprocess.run(
                    command, shell=True, capture_output=True, text=True, timeout=30
                )
                output = result.stdout or result.stderr
                if result.returncode != 0:
                    return f"Command failed (exit {result.returncode}):\n{output[:1500]}"
                return output[:2000] if output else "Command executed successfully (no output)"
            except subprocess.TimeoutExpired:
                return "Error: Command timed out after 30 seconds"
            except Exception as e:
                return f"Error executing command: {str(e)}"
        
        @self.tools.register("get_time")
        def get_time() -> str:
            """Get the current date and time."""
            return datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        @self.tools.register("read_file")
        def read_file(path: str) -> str:
            """Read the contents of a file."""
            try:
                file_path = Path(path).expanduser()
                if not file_path.exists():
                    return f"Error: File not found: {path}"
                if file_path.stat().st_size > 1_000_000:  # 1MB limit
                    return "Error: File too large (>1MB)"
                return file_path.read_text(encoding="utf-8")[:5000]
            except Exception as e:
                return f"Error reading file: {str(e)}"
        
        @self.tools.register("list_files")
        def list_files(path: str = ".") -> str:
            """List files in a directory."""
            try:
                dir_path = Path(path).expanduser()
                if not dir_path.exists():
                    return f"Error: Directory not found: {path}"
                if not dir_path.is_dir():
                    return f"Error: Not a directory: {path}"
                items = []
                for item in sorted(dir_path.iterdir()):
                    prefix = "📁" if item.is_dir() else "📄"
                    size = item.stat().st_size if item.is_file() else 0
                    items.append(f"{prefix} {item.name} ({self._format_size(size)})")
                return "\n".join(items[:50])  # Limit to 50 items
            except Exception as e:
                return f"Error listing files: {str(e)}"
    
    @staticmethod
    def _format_size(size_bytes: int) -> str:
        """Format file size in human readable format."""
        for unit in ['B', 'KB', 'MB', 'GB']:
            if size_bytes < 1024:
                return f"{size_bytes:.1f}{unit}"
            size_bytes /= 1024
        return f"{size_bytes:.1f}TB"
    
    def chat(self, user_input: str) -> str:
        """
        Main chat loop with tool calling.
        
        Args:
            user_input: User's message
            
        Returns:
            Assistant's response
            
        Raises:
            LLMConnectionError: If cannot connect to Ollama
        """
        # Add user message
        self.conversation_history.append({
            "role": "user",
            "content": user_input
        })
        
        # Tool calling loop
        for round_num in range(self.max_tool_rounds):
            # Build messages for LLM
            messages = self._build_messages()
            
            # Call LLM
            try:
                response = self._call_llm(messages)
            except LLMConnectionError:
                raise
            except Exception as e:
                logger.error(f"LLM call failed: {e}")
                response = f"I encountered an error: {str(e)}"
            
            # Check for tool calls
            if "[TOOL:" not in response:
                break
            
            # Handle tool calls
            response = self._handle_tool_calls(response, user_input)
        
        # Add to history
        self.conversation_history.append({
            "role": "assistant",
            "content": response
        })
        
        # Trim history if too long (keep last 20 exchanges)
        if len(self.conversation_history) > 40:
            self.conversation_history = self.conversation_history[-40:]
        
        return response
    
    def _build_messages(self) -> List[Dict[str, str]]:
        """Build message list for LLM."""
        messages = [
            {"role": "system", "content": self.system_prompt}
        ]
        
        # Add tool descriptions
        if self.tools.tools:
            tool_desc = "\n\n## Available Tools\n"
            for name, func in self.tools.tools.items():
                tool_desc += f"- {name}: {func.__doc__ or 'No description'}\n"
            tool_desc += "\nTo use a tool, respond with: [TOOL: tool_name(param='value')]"
            messages[0]["content"] += tool_desc
        
        messages.extend(self.conversation_history)
        return messages
    
    def _call_llm(self, messages: List[Dict[str, str]]) -> str:
        """Call Ollama API."""
        import httpx
        
        try:
            with httpx.Client(timeout=120.0) as client:
                response = client.post(
                    f"{self.ollama_url}/api/chat",
                    json={
                        "model": self.model,
                        "messages": messages,
                        "stream": False,
                        "options": {
                            "temperature": 0.7,
                            "num_predict": 2048,
                        }
                    }
                )
                response.raise_for_status()
                return response.json()["message"]["content"]
        except httpx.ConnectError:
            raise LLMConnectionError(
                "Cannot connect to Ollama. Is it running?\n"
                "Start it with: ollama serve"
            )
        except httpx.HTTPStatusError as e:
            raise LLMConnectionError(f"Ollama API error: {e.response.status_code}")
        except Exception as e:
            raise LLMConnectionError(f"Unexpected error: {str(e)}")
    
    def _handle_tool_calls(self, response: str, original_query: str) -> str:
        """Parse and execute tool calls from LLM response."""
        # Extract tool calls: [TOOL: name(args)]
        pattern = r'\[TOOL:\s*(\w+)\((.*?)\)\]'
        matches = re.findall(pattern, response)
        
        if not matches:
            return response
        
        results = []
        for tool_name, args_str in matches:
            if tool_name not in self.tools.tools:
                results.append(f"[{tool_name}] Error: Unknown tool")
                continue
            
            # Parse arguments
            kwargs = self._parse_tool_args(args_str)
            
            # Execute tool
            try:
                result = self.tools.execute(tool_name, **kwargs)
                results.append(f"[{tool_name}] {result}")
                logger.info(f"Tool {tool_name} executed successfully")
            except Exception as e:
                error_msg = f"[{tool_name}] Error: {str(e)}"
                results.append(error_msg)
                logger.error(error_msg)
        
        # Append results and get summary
        if results:
            tool_results = "\n".join(results)
            summary_messages = [
                {"role": "system", "content": self.system_prompt},
                {"role": "user", "content": (
                    f"Original query: {original_query}\n\n"
                    f"Tool execution results:\n{tool_results}\n\n"
                    f"Please provide a helpful summary for the user based on these results."
                )}
            ]
            try:
                return self._call_llm(summary_messages)
            except Exception as e:
                return f"Tools executed:\n{tool_results}\n\n(Summary generation failed: {e})"
        
        return response
    
    @staticmethod
    def _parse_tool_args(args_str: str) -> Dict[str, Any]:
        """Parse tool arguments from string."""
        kwargs = {}
        if not args_str:
            return kwargs
        
        # Match key='value' or key="value" or key=value
        for match in re.finditer(r"(\w+)=(?:'([^']*)'|\"([^\"]*)\"|(\S+))", args_str):
            key = match.group(1)
            value = match.group(2) or match.group(3) or match.group(4)
            # Try to convert numeric values
            try:
                value = int(value)
            except ValueError:
                try:
                    value = float(value)
                except ValueError:
                    pass
            kwargs[key] = value
        
        return kwargs
    
    def reset(self):
        """Reset conversation history."""
        self.conversation_history.clear()
    
    def save_context(self, key: str, value: str, category: str = "context"):
        """Save a key-value pair to persistent memory."""
        self.memory.save(f"{key}: {value}", category=category)
    
    def get_context(self, key: str, category: str = "context") -> Optional[str]:
        """Retrieve a value from persistent memory."""
        results = self.memory.search(key, limit=1, category=category)
        if results:
            # Extract value after colon
            content = results[0]["content"]
            if ": " in content:
                return content.split(": ", 1)[1]
        return None
