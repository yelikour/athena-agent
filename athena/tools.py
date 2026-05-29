"""
Tools - MCP-compatible tool registry for Athena
Allows registering and calling tools dynamically.
"""
from typing import Callable, Dict, Any, Optional, List
import inspect
import logging

logger = logging.getLogger(__name__)


class ToolError(Exception):
    """Base exception for Tool errors."""
    pass


class Tool:
    """
    Wrapper for a tool function with metadata.
    
    Attributes:
        func: The wrapped function
        name: Tool name
        description: Tool description from docstring
        parameters: Parameter information
    """
    
    def __init__(self, func: Callable, name: Optional[str] = None):
        """
        Initialize Tool.
        
        Args:
            func: Function to wrap
            name: Optional custom name (defaults to function name)
        """
        self.func = func
        self.name = name or func.__name__
        self.description = func.__doc__ or "No description"
        self.parameters = self._extract_parameters()
    
    def _extract_parameters(self) -> Dict[str, Dict[str, str]]:
        """Extract parameter info from function signature."""
        sig = inspect.signature(self.func)
        params = {}
        
        for name, param in sig.parameters.items():
            param_info = {
                "type": "string",
                "required": True,
            }
            
            # Extract type annotation
            if param.annotation != inspect.Parameter.empty:
                type_name = getattr(param.annotation, '__name__', str(param.annotation))
                param_info["type"] = type_name
            
            # Check for default value
            if param.default != inspect.Parameter.empty:
                param_info["required"] = False
                param_info["default"] = param.default
            
            params[name] = param_info
        
        return params
    
    def execute(self, **kwargs) -> Any:
        """
        Execute the tool with given arguments.
        
        Args:
            **kwargs: Tool arguments
            
        Returns:
            Tool execution result
            
        Raises:
            ToolError: If execution fails
        """
        try:
            # Validate required parameters
            for name, param_info in self.parameters.items():
                if param_info["required"] and name not in kwargs:
                    if "default" not in param_info:
                        raise ToolError(f"Missing required parameter: {name}")
            
            return self.func(**kwargs)
        except TypeError as e:
            raise ToolError(f"Invalid arguments for {self.name}: {e}")
        except Exception as e:
            raise ToolError(f"Tool execution failed: {e}")


class ToolRegistry:
    """
    Registry for tools that the agent can use.
    
    MCP-compatible: Tools are registered with name, description, and parameters.
    
    Example:
        >>> registry = ToolRegistry()
        >>> @registry.register("greet")
        ... def greet(name: str) -> str:
        ...     return f"Hello, {name}!"
        >>> result = registry.execute("greet", name="World")
    """
    
    def __init__(self):
        self.tools: Dict[str, Tool] = {}
    
    def register(self, name: Optional[str] = None):
        """
        Decorator to register a tool.
        
        Args:
            name: Optional custom name
            
        Returns:
            Decorator function
            
        Example:
            >>> @registry.register("my_tool")
            ... def my_tool(arg: str) -> str:
            ...     return result
        """
        def decorator(func: Callable):
            tool = Tool(func, name)
            self.tools[tool.name] = tool
            logger.debug(f"Registered tool: {tool.name}")
            return func
        return decorator
    
    def add(self, func: Callable, name: Optional[str] = None):
        """
        Register a tool function directly.
        
        Args:
            func: Function to register
            name: Optional custom name
        """
        tool = Tool(func, name)
        self.tools[tool.name] = tool
        logger.debug(f"Added tool: {tool.name}")
    
    def execute(self, tool_name: str, **kwargs) -> Any:
        """
        Execute a registered tool.
        
        Args:
            tool_name: Name of tool to execute
            **kwargs: Tool arguments
            
        Returns:
            Tool execution result
            
        Raises:
            ToolError: If tool not found or execution fails
        """
        if tool_name not in self.tools:
            available = ", ".join(self.tools.keys())
            raise ToolError(
                f"Tool '{tool_name}' not registered. "
                f"Available tools: {available}"
            )
        return self.tools[tool_name].execute(**kwargs)
    
    def get(self, name: str) -> Optional[Tool]:
        """Get a tool by name."""
        return self.tools.get(name)
    
    def list_tools(self) -> Dict[str, Dict]:
        """
        List all registered tools with their metadata.
        
        Returns:
            Dictionary of tool info
        """
        return {
            name: {
                "description": tool.description,
                "parameters": tool.parameters,
            }
            for name, tool in self.tools.items()
        }
    
    def to_mcp_schema(self) -> List[Dict]:
        """
        Export tools as MCP-compatible schema.
        
        Returns:
            List of MCP tool schemas
        """
        schemas = []
        for name, tool in self.tools.items():
            # Convert parameters to MCP format
            properties = {}
            required = []
            
            for param_name, param_info in tool.parameters.items():
                properties[param_name] = {
                    "type": param_info["type"],
                    "description": f"Parameter: {param_name}",
                }
                if param_info["required"]:
                    required.append(param_name)
                elif "default" in param_info:
                    properties[param_name]["default"] = param_info["default"]
            
            schema = {
                "name": name,
                "description": tool.description,
                "inputSchema": {
                    "type": "object",
                    "properties": properties,
                    "required": required,
                }
            }
            schemas.append(schema)
        
        return schemas
    
    def remove(self, name: str) -> bool:
        """
        Remove a tool from registry.
        
        Args:
            name: Name of tool to remove
            
        Returns:
            True if removed, False if not found
        """
        if name in self.tools:
            del self.tools[name]
            logger.debug(f"Removed tool: {name}")
            return True
        return False
    
    def clear(self):
        """Remove all tools."""
        self.tools.clear()
        logger.debug("Cleared all tools")


class MCPToolAdapter:
    """
    Adapter to use MCP servers as tools.
    
    Connects to an MCP server via stdio or HTTP and registers
    all available tools.
    
    Example:
        >>> adapter = MCPToolAdapter(registry)
        >>> adapter.connect_stdio("uvx", ["mcp-server-filesystem"])
    """
    
    def __init__(self, registry: ToolRegistry):
        self.registry = registry
        self.connections: Dict[str, Any] = {}
    
    def connect_stdio(self, command: str, args: List[str] = None):
        """
        Connect to an MCP server via stdio.
        
        Args:
            command: Command to run
            args: Command arguments
            
        Raises:
            NotImplementedError: Not yet implemented
        """
        # TODO: Implement MCP stdio protocol
        raise NotImplementedError(
            "MCP stdio connection coming in v0.2. "
            "Track progress at: https://github.com/yelikour/athena-agent/issues/1"
        )
    
    def connect_http(self, url: str):
        """
        Connect to an MCP server via HTTP/SSE.
        
        Args:
            url: Server URL
            
        Raises:
            NotImplementedError: Not yet implemented
        """
        # TODO: Implement MCP HTTP protocol
        raise NotImplementedError(
            "MCP HTTP connection coming in v0.2. "
            "Track progress at: https://github.com/yelikour/athena-agent/issues/2"
        )
    
    def disconnect_all(self):
        """Disconnect from all MCP servers."""
        for name, conn in self.connections.items():
            try:
                # TODO: Proper cleanup
                pass
            except Exception as e:
                logger.error(f"Error disconnecting from {name}: {e}")
        self.connections.clear()
