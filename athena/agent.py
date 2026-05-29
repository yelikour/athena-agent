"""
Core Agent - The brain of Athena
Handles conversation, tool calling, and reasoning loop.
"""
import json
import sqlite3
from datetime import datetime
from typing import Optional, Dict, Any, List
from pathlib import Path

from .memory import Memory
from .tools import ToolRegistry


class Agent:
    """
    A minimal AI agent with:
    - Local LLM inference (via Ollama)
    - Persistent memory (SQLite)
    - Tool calling (MCP-compatible)
    """
    
    def __init__(
        self,
        model: str = "llama3.2:3b",
        ollama_url: str = "http://localhost:11434",
        memory_path: str = "~/.athena/memory.db",
        system_prompt: Optional[str] = None,
    ):
        self.model = model
        self.ollama_url = ollama_url.rstrip("/")
        self.memory = Memory(memory_path)
        self.tools = ToolRegistry()
        self.conversation_history: List[Dict[str, str]] = []
        
        self.system_prompt = system_prompt or """You are Athena, a helpful AI assistant.
You have access to tools that can help with various tasks.
Always think step by step. Use tools when needed.
Be concise and helpful."""
        
        # Register built-in tools
        self._register_builtin_tools()
    
    def _register_builtin_tools(self):
        """Register built-in tools."""
        @self.tools.register("memory_search")
        def memory_search(query: str, limit: int = 5) -> str:
            """Search your memory for relevant information."""
            results = self.memory.search(query, limit)
            if not results:
                return "No relevant memories found."
            return "\n".join([f"- {r['content']}" for r in results])
        
        @self.tools.register("memory_save")
        def memory_save(content: str, category: str = "general") -> str:
            """Save information to your memory."""
            self.memory.save(content, category)
            return f"Saved to memory (category: {category})"
        
        @self.tools.register("run_command")
        def run_command(command: str) -> str:
            """Run a shell command and return the output."""
            import subprocess
            try:
                result = subprocess.run(
                    command, shell=True, capture_output=True, text=True, timeout=30
                )
                output = result.stdout or result.stderr
                return output[:2000] if output else "Command executed (no output)"
            except subprocess.TimeoutExpired:
                return "Command timed out after 30 seconds"
            except Exception as e:
                return f"Error: {str(e)}"
        
        @self.tools.register("get_time")
        def get_time() -> str:
            """Get the current date and time."""
            return datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    def chat(self, user_input: str) -> str:
        """
        Main chat loop with tool calling.
        
        1. Add user message to history
        2. Build prompt with system + history
        3. Call LLM
        4. Check if tool call needed
        5. Execute tool and loop
        6. Return final response
        """
        # Add user message
        self.conversation_history.append({
            "role": "user",
            "content": user_input
        })
        
        # Build messages for LLM
        messages = [
            {"role": "system", "content": self.system_prompt}
        ]
        
        # Add tool descriptions
        if self.tools.tools:
            tool_desc = "\n\nAvailable tools:\n"
            for name, func in self.tools.tools.items():
                tool_desc += f"- {name}: {func.__doc__ or 'No description'}\n"
            tool_desc += "\nTo use a tool, respond with: [TOOL: tool_name(arg1='value1', arg2='value2')]"
            messages[0]["content"] += tool_desc
        
        messages.extend(self.conversation_history)
        
        # Call LLM
        response = self._call_llm(messages)
        
        # Check for tool calls
        if "[TOOL:" in response:
            response = self._handle_tool_calls(response)
        
        # Add to history
        self.conversation_history.append({
            "role": "assistant",
            "content": response
        })
        
        # Save to memory
        self.memory.save(
            f"User: {user_input}\nAssistant: {response}",
            category="conversations"
        )
        
        return response
    
    def _call_llm(self, messages: List[Dict[str, str]]) -> str:
        """Call Ollama API."""
        import httpx
        
        try:
            with httpx.Client(timeout=60.0) as client:
                response = client.post(
                    f"{self.ollama_url}/api/chat",
                    json={
                        "model": self.model,
                        "messages": messages,
                        "stream": False,
                    }
                )
                response.raise_for_status()
                return response.json()["message"]["content"]
        except httpx.ConnectError:
            return "Error: Cannot connect to Ollama. Is it running? (ollama serve)"
        except Exception as e:
            return f"Error calling LLM: {str(e)}"
    
    def _handle_tool_calls(self, response: str) -> str:
        """Parse and execute tool calls from LLM response."""
        import re
        
        # Extract tool calls: [TOOL: name(args)]
        pattern = r'\[TOOL:\s*(\w+)\((.*?)\)\]'
        matches = re.findall(pattern, response)
        
        results = []
        for tool_name, args_str in matches:
            if tool_name in self.tools.tools:
                # Parse arguments
                kwargs = {}
                if args_str:
                    # Simple parsing: key='value' or key="value"
                    for match in re.finditer(r"(\w+)=(?:'([^']*)'|\"([^\"]*)\")", args_str):
                        key = match.group(1)
                        value = match.group(2) or match.group(3)
                        kwargs[key] = value
                
                # Execute tool
                try:
                    result = self.tools.execute(tool_name, **kwargs)
                    results.append(f"[{tool_name}] {result}")
                except Exception as e:
                    results.append(f"[{tool_name}] Error: {str(e)}")
        
        # Append results and get final response
        if results:
            tool_results = "\n".join(results)
            messages = [
                {"role": "system", "content": self.system_prompt},
                {"role": "user", "content": f"Tool results:\n{tool_results}\n\nPlease summarize these results for the user."}
            ]
            return self._call_llm(messages)
        
        return response
    
    def save_context(self, key: str, value: str):
        """Save a key-value pair to persistent memory."""
        self.memory.save(f"{key}: {value}", category="context")
    
    def get_context(self, key: str) -> Optional[str]:
        """Retrieve a value from persistent memory."""
        results = self.memory.search(key, limit=1)
        return results[0]["content"] if results else None
