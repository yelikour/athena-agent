"""
Example: Basic usage of Athena Agent
"""
from athena import Agent


def main():
    """Demonstrate basic Athena usage."""
    
    # Create agent
    agent = Agent(
        model="llama3.2:3b",
        memory_path="~/.athena/example_memory.db"
    )
    
    print("🏛️ Athena Example\n")
    
    # Example 1: Simple chat
    print("=== Example 1: Simple Chat ===")
    response = agent.chat("What's 2 + 2?")
    print(f"Response: {response}\n")
    
    # Example 2: Save and search memory
    print("=== Example 2: Memory Operations ===")
    agent.memory.save("Python is my favorite programming language", category="preferences")
    agent.memory.save("I'm working on a machine learning project", category="projects")
    
    results = agent.memory.search("programming")
    print(f"Search results: {results}\n")
    
    # Example 3: Custom tool
    print("=== Example 3: Custom Tool ===")
    
    @agent.tools.register("calculate")
    def calculate(expression: str) -> str:
        """Evaluate a math expression safely."""
        try:
            # Simple eval for demo (use ast.literal_eval in production)
            result = eval(expression)
            return str(result)
        except Exception as e:
            return f"Error: {e}"
    
    response = agent.chat("Calculate 15 * 23 + 7")
    print(f"Response: {response}\n")
    
    # Example 4: List tools
    print("=== Example 4: Available Tools ===")
    tools = agent.tools.list_tools()
    for name, info in tools.items():
        print(f"  - {name}: {info['description'][:50]}...")
    
    print("\n✅ Example complete!")


if __name__ == "__main__":
    main()
