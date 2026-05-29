"""
CLI - Command-line interface for Athena
"""
import argparse
import sys
import logging
from pathlib import Path
from typing import Optional

from .agent import Agent, LLMConnectionError


def setup_logging(verbose: bool = False):
    """Setup logging configuration."""
    level = logging.DEBUG if verbose else logging.WARNING
    logging.basicConfig(
        level=level,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%H:%M:%S",
    )


def main():
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(
        prog="athena",
        description="🏛️ Athena - Lightweight Local AI Agent",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  athena                          # Start chat (auto-detect best provider)
  athena -p deepseek              # Use DeepSeek
  athena -p glm -m glm-4-flash    # Use GLM with specific model
  athena --memory-search "query"  # Search memories
  athena --health                 # System health check
        """
    )
    
    # Provider options
    provider_group = parser.add_argument_group("Provider")
    provider_group.add_argument(
        "-p", "--provider",
        help="LLM provider (auto-detect if not specified)"
    )
    provider_group.add_argument(
        "-m", "--model",
        help="Model name override"
    )
    provider_group.add_argument(
        "--providers",
        action="store_true",
        help="List available providers and exit"
    )
    
    # Memory options
    memory_group = parser.add_argument_group("Memory")
    memory_group.add_argument(
        "--memory-path",
        default="~/.athena/memory.db",
        help="Path to memory database (default: ~/.athena/memory.db)"
    )
    memory_group.add_argument(
        "--memory-search",
        metavar="QUERY",
        help="Search memories and exit"
    )
    memory_group.add_argument(
        "--memory-save",
        metavar="CONTENT",
        help="Save content to memory and exit"
    )
    memory_group.add_argument(
        "--memory-list",
        action="store_true",
        help="List recent memories and exit"
    )
    
    # System options
    system_group = parser.add_argument_group("System")
    system_group.add_argument(
        "--health",
        action="store_true",
        help="Run system health check and exit"
    )
    system_group.add_argument(
        "--list-tools",
        action="store_true",
        help="List available tools and exit"
    )
    
    # General options
    parser.add_argument(
        "-v", "--verbose",
        action="store_true",
        help="Enable verbose logging"
    )
    parser.add_argument(
        "--version",
        action="version",
        version="%(prog)s 0.2.0"
    )
    
    args = parser.parse_args()
    setup_logging(args.verbose)
    
    # Handle commands that don't need agent
    if args.providers:
        _handle_providers()
        return
    
    if args.health:
        _handle_health()
        return
    
    # Initialize agent
    try:
        agent = Agent(
            provider=args.provider,
            model=args.model,
            memory_path=args.memory_path,
        )
    except Exception as e:
        print(f"❌ Failed to initialize Athena: {e}")
        sys.exit(1)
    
    # Handle commands that need agent
    if args.memory_search:
        _handle_memory_search(agent, args.memory_search)
        return
    
    if args.memory_save:
        _handle_memory_save(agent, args.memory_save)
        return
    
    if args.memory_list:
        _handle_memory_list(agent)
        return
    
    if args.list_tools:
        _handle_list_tools(agent)
        return
    
    # Interactive chat mode
    _run_interactive_chat(agent)


def _handle_providers():
    """Handle providers list command."""
    from .providers import create_default_registry
    registry = create_default_registry()
    
    providers = registry.list_providers()
    if providers:
        print(f"🤖 Available Providers ({len(providers)}):\n")
        for name, available in providers.items():
            status = "✓" if available else "✗"
            print(f"  {status} {name}")
        
        best = registry.get_best()
        if best:
            print(f"\n  Best available: {best.name} ({best.config.model})")
    else:
        print("No providers found. Set up an API key or start Ollama.")


def _handle_health():
    """Handle health check command."""
    try:
        from .monitor import SystemMonitor
        monitor = SystemMonitor()
        health = monitor.health_check()
        
        print("🏥 System Health\n")
        print(f"  Score: {health['health_score']}/100 ({health['health_status']})")
        print(f"  CPU: {health['cpu_percent']}%")
        print(f"  Memory: {health['memory']['percent']}%")
        print(f"  Disk: {health['disk']['percent']}%")
        
        if health['gpu']:
            print(f"  GPU: {health['gpu']['name']} ({health['gpu']['temperature_c']}°C)")
        
        print(f"\n  Network:")
        print(f"    Internet: {'✓' if health['network']['internet'] else '✗'}")
        print(f"    Ollama: {'✓' if health['network']['ollama'] else '✗'}")
    except ImportError:
        print("Monitor module not available. Install with: pip install psutil")


def _handle_memory_search(agent: Agent, query: str):
    """Handle memory search command."""
    results = agent.memory.search(query)
    if results:
        print(f"🔍 Found {len(results)} results:\n")
        for r in results:
            print(f"  [{r['category']}] {r['content'][:100]}")
    else:
        print(f"No memories found for '{query}'.")


def _handle_memory_save(agent: Agent, content: str):
    """Handle memory save command."""
    memory_id = agent.memory.save(content)
    print(f"✅ Saved (id: {memory_id})")


def _handle_memory_list(agent: Agent):
    """Handle memory list command."""
    memories = agent.memory.get_recent(limit=20)
    if memories:
        print(f"📝 Recent memories ({len(memories)}):\n")
        for m in memories:
            print(f"  [{m['category']}] {m['content'][:80]}")
    else:
        print("No memories yet.")


def _handle_list_tools(agent: Agent):
    """Handle list tools command."""
    tools = agent.tools.list_tools()
    if tools:
        print(f"🔧 Tools ({len(tools)}):\n")
        for name, info in tools.items():
            print(f"  {name}: {info['description'][:60]}")


def _run_interactive_chat(agent: Agent):
    """Run interactive chat mode."""
    print(f"🏛️ Athena v0.2.0")
    print(f"   Provider: {agent.provider_name}")
    print(f"   Model: {agent.model}")
    print(f"   Memory: {agent.memory.db_path}")
    print(f"   Tools: {len(agent.tools.tools)} available")
    print(f"\n   Commands: 'quit' to exit, 'clear' to reset, 'tools' to list tools\n")
    
    while True:
        try:
            user_input = input("You: ").strip()
            
            if not user_input:
                continue
            
            if user_input.lower() in ("quit", "exit", "q"):
                print("\n👋 Goodbye!")
                break
            
            if user_input.lower() == "clear":
                agent.reset()
                print("🔄 Conversation cleared.\n")
                continue
            
            if user_input.lower() == "tools":
                _handle_list_tools(agent)
                print()
                continue
            
            if user_input.lower() == "health":
                _handle_health()
                print()
                continue
            
            if user_input.lower() == "memory":
                count = agent.memory.count()
                print(f"📊 Memory: {count} entries\n")
                continue
            
            # Get response
            response = agent.chat(user_input)
            print(f"\nAthena: {response}\n")
            
        except KeyboardInterrupt:
            print("\n\n👋 Goodbye!")
            break
        except EOFError:
            print("\n\n👋 Goodbye!")
            break
        except LLMConnectionError as e:
            print(f"\n❌ {e}\n")
            break
        except Exception as e:
            print(f"\n❌ Error: {e}\n")


if __name__ == "__main__":
    main()
