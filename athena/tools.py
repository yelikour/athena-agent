"""
Tools - MCP-compatible tool registry for Athena
Allows registering and calling tools dynamically.
"""
from typing import Callable, Dict, Any, Optional
import inspect


class Tool:
    """Wrapper for a tool function with metadata."""
    
    def __init__(self, func: Callable, name: Optional[str] = None):
        self.func = func
        self.name = name or func.__name__
        self.description = func.__doc__ or "No description"
        self.parameters = self._extract_parameters()
    
    def _extract_parameters(self) -> Dict[str, str]:
        """Extract parameter info from function signature."""
        sig = inspect.signature(self.func)
        params = {}
        for name, param in sig.parameters.items():
            if param.annotation != inspect.Parameter.empty:
                params[name] = str(param.annotation)
            else:
                params[name] = "str"
        return params
    
    def execute(self, **kwargs) -> Any:
        """Execute the tool with given arguments."""
        return self.func(**kwargs)


class ToolRegistry:
    """
    Registry for tools that the agent can use.
    
    MCP-compatible: Tools are registered with name, description, and parameters.
    """
    
    def __init__(self):
        self.tools: Dict[str, Tool] = {}
    
    def register(self, name: Optional[str] = None):
        """Decorator to register a tool."""
        def decorator(func: Callable):
            tool = Tool(func, name)
            self.tools[tool.name] = tool
            return func
        return decorator
    
    def add(self, func: Callable, name: Optional[str] = None):
        """Register a tool function directly."""
        tool = Tool(func, name)
        self.tools[tool.name] = tool
    
    def execute(self, tool_name: str, **kwargs) -> Any:
        """Execute a registered tool."""
        if tool_name not in self.tools:
            raise ValueError(f"Tool '{tool_name}' not registered")
        return self.tools[tool_name].execute(**kwargs)
    
    def list_tools(self) -> Dict[str, Dict]:
        """List all registered tools with their metadata."""
        return {
            name: {
                "description": tool.description,
                "parameters": tool.parameters,
            }
            for name, tool in self.tools.items()
        }
    
    def to_mcp_schema(self) -> list:
        """Export tools as MCP-compatible schema."""
        schemas = []
        for name, tool in self.tools.items():
            schema = {
                "name": name,
                "description": tool.description,
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        param: {"type": "string"}
                        for param in tool.parameters
                    },
                    "required": list(tool.parameters.keys()),
                }
            }
            schemas.append(schema)
        return schemas


class MCPToolAdapter:
    """
    Adapter to use MCP servers as tools.
    
    Connects to an MCP server via stdio or HTTP and registers
    all available tools.
    """
    
    def __init__(self, registry: ToolRegistry):
        self.registry = registry
    
    def connect_stdio(self, command: str, args: list = None):
        """Connect to an MCP server via stdio."""
        # TODO: Implement MCP stdio protocol
        raise NotImplementedError("MCP stdio connection coming in v0.2")
    
    def connect_http(self, url: str):
        """Connect to an MCP server via HTTP/SSE."""
        # TODO: Implement MCP HTTP protocol
        raise NotImplementedError("MCP HTTP connection coming in v0.2")
