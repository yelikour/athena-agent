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
  athena                          # Start interactive chat
  athena -m llama3.2:3b           # Use specific model
  athena --memory-search "query"  # Search memories
  athena --memory-save "content"  # Save to memory
  athena --memory-list            # List recent memories
  athena --list-tools             # List available tools
  athena --health                 # System health check
  athena --cron list              # List scheduled jobs
        """
    )
    
    # Model options
    model_group = parser.add_argument_group("Model")
    model_group.add_argument(
        "-m", "--model",
        default="llama3.2:3b",
        help="Ollama model to use (default: llama3.2:3b)"
    )
    model_group.add_argument(
        "--ollama-url",
        default="http://localhost:11434",
        help="Ollama API URL (default: http://localhost:11434)"
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
        "--memory-category",
        default="general",
        help="Category for memory operations (default: general)"
    )
    memory_group.add_argument(
        "--memory-list",
        action="store_true",
        help="List recent memories and exit"
    )
    memory_group.add_argument(
        "--memory-count",
        action="store_true",
        help="Count total memories and exit"
    )
    memory_group.add_argument(
        "--memory-clear",
        action="store_true",
        help="Clear all memories and exit"
    )
    
    # Session options
    session_group = parser.add_argument_group("Sessions")
    session_group.add_argument(
        "--sessions",
        action="store_true",
        help="List recent sessions and exit"
    )
    session_group.add_argument(
        "--session-new",
        metavar="TITLE",
        help="Create a new session and exit"
    )
    session_group.add_argument(
        "--session-continue",
        metavar="ID",
        help="Continue a previous session"
    )
    
    # Tool options
    tool_group = parser.add_argument_group("Tools")
    tool_group.add_argument(
        "--list-tools",
        action="store_true",
        help="List available tools and exit"
    )
    
    # Cron options
    cron_group = parser.add_argument_group("Cron Jobs")
    cron_group.add_argument(
        "--cron",
        choices=["list", "status"],
        help="Cron operations"
    )
    
    # System options
    system_group = parser.add_argument_group("System")
    system_group.add_argument(
        "--health",
        action="store_true",
        help="Run system health check and exit"
    )
    system_group.add_argument(
        "--providers",
        action="store_true",
        help="List available LLM providers"
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
    
    # Initialize agent
    agent = Agent(
        model=args.model,
        ollama_url=args.ollama_url,
        memory_path=args.memory_path,
    )
    
    # Handle commands
    if args.memory_search:
        _handle_memory_search(agent, args.memory_search, args.memory_category)
        return
    
    if args.memory_save:
        _handle_memory_save(agent, args.memory_save, args.memory_category)
        return
    
    if args.memory_list:
        _handle_memory_list(agent, args.memory_category)
        return
    
    if args.memory_count:
        _handle_memory_count(agent, args.memory_category)
        return
    
    if args.memory_clear:
        _handle_memory_clear(agent, args.memory_category)
        return
    
    if args.list_tools:
        _handle_list_tools(agent)
        return
    
    if args.sessions:
        _handle_sessions(agent)
        return
    
    if args.session_new:
        _handle_session_new(agent, args.session_new)
        return
    
    if args.cron:
        _handle_cron(args.cron)
        return
    
    if args.health:
        _handle_health()
        return
    
    if args.providers:
        _handle_providers()
        return
    
    # Interactive chat mode
    _run_interactive_chat(agent, args.session_continue)


def _handle_memory_search(agent: Agent, query: str, category: str):
    """Handle memory search command."""
    results = agent.memory.search(query, category=category)
    if results:
        print(f"🔍 Found {len(results)} results for '{query}':\n")
        for r in results:
            print(f"  [{r['category']}] {r['content'][:100]}")
            print(f"    └─ {r['created_at']}")
    else:
        print(f"No memories found for '{query}'.")


def _handle_memory_save(agent: Agent, content: str, category: str):
    """Handle memory save command."""
    memory_id = agent.memory.save(content, category=category)
    print(f"✅ Saved to memory (id: {memory_id}, category: {category})")


def _handle_memory_list(agent: Agent, category: str):
    """Handle memory list command."""
    memories = agent.memory.get_recent(limit=20, category=category)
    if memories:
        print(f"📝 Recent memories ({len(memories)}):\n")
        for m in memories:
            print(f"  [{m['category']}] {m['content'][:80]}")
            print(f"    └─ {m['created_at']}")
    else:
        print("No memories yet.")


def _handle_memory_count(agent: Agent, category: str):
    """Handle memory count command."""
    count = agent.memory.count(category)
    cats = agent.memory.get_categories()
    print(f"📊 Total memories: {count}")
    if cats:
        print(f"   Categories: {', '.join(cats)}")


def _handle_memory_clear(agent: Agent, category: str):
    """Handle memory clear command."""
    confirm = input(f"Clear {'all' if not category else category} memories? [y/N]: ")
    if confirm.lower() == "y":
        agent.memory.clear(category)
        print("✅ Memories cleared.")
    else:
        print("Cancelled.")


def _handle_list_tools(agent: Agent):
    """Handle list tools command."""
    tools = agent.tools.list_tools()
    if tools:
        print(f"🔧 Available tools ({len(tools)}):\n")
        for name, info in tools.items():
            print(f"  {name}: {info['description'][:60]}")
            if info['parameters']:
                params = ", ".join(info['parameters'].keys())
                print(f"    └─ Parameters: {params}")
    else:
        print("No tools registered.")


def _handle_sessions(agent: Agent):
    """Handle sessions list command."""
    from .sessions import SessionManager
    manager = SessionManager()
    sessions = manager.list_sessions(limit=10)
    
    if sessions:
        print(f"📋 Recent sessions ({len(sessions)}):\n")
        for s in sessions:
            print(f"  {s.id[:20]}...")
            print(f"    Title: {s.title}")
            print(f"    Messages: {s.message_count}")
            print(f"    Updated: {s.updated_at[:19]}")
    else:
        print("No sessions yet.")


def _handle_session_new(agent: Agent, title: str):
    """Handle session new command."""
    from .sessions import SessionManager
    manager = SessionManager()
    session = manager.create_session(title)
    print(f"✅ Created session: {session.id}")
    print(f"   Use 'athena --session-continue {session.id}' to continue")


def _handle_cron(action: str):
    """Handle cron commands."""
    from .cron import CronScheduler
    scheduler = CronScheduler()
    
    if action == "list":
        jobs = scheduler.list_jobs()
        if jobs:
            print(f"⏰ Scheduled jobs ({len(jobs)}):\n")
            for job in jobs:
                status = "✓" if job.enabled else "✗"
                print(f"  {status} {job.name}")
                print(f"    Schedule: {job.schedule}")
                print(f"    Last run: {job.last_run or 'Never'}")
        else:
            print("No scheduled jobs.")
    
    elif action == "status":
        print("Cron scheduler status: Ready")


def _handle_health():
    """Handle health check command."""
    from .monitor import SystemMonitor
    monitor = SystemMonitor()
    health = monitor.health_check()
    
    print("🏥 System Health Check\n")
    print(f"  Score: {health['health_score']}/100 ({health['health_status']})")
    print(f"  OS: {health['system']['os']} {health['system']['os_version'][:30]}")
    print(f"  CPU: {health['cpu_percent']}%")
    print(f"  Memory: {health['memory']['percent']}%")
    print(f"  Disk: {health['disk']['percent']}%")
    
    if health['gpu']:
        print(f"  GPU: {health['gpu']['name']}")
        print(f"  GPU Temp: {health['gpu']['temperature_c']}°C")
    
    print(f"\n  Network:")
    print(f"    Internet: {'✓' if health['network']['internet'] else '✗'}")
    print(f"    Ollama: {'✓' if health['network']['ollama'] else '✗'}")


def _handle_providers():
    """Handle providers list command."""
    from .providers import create_default_registry
    registry = create_default_registry()
    
    providers = registry.list_providers()
    if providers:
        print(f"🤖 LLM Providers ({len(providers)}):\n")
        for name, available in providers.items():
            status = "✓ Available" if available else "✗ Not configured"
            print(f"  {name}: {status}")
    else:
        print("No providers registered.")


def _run_interactive_chat(agent: Agent, session_id: Optional[str] = None):
    """Run interactive chat mode."""
    from .sessions import SessionManager
    manager = SessionManager()
    
    # Create or continue session
    if session_id:
        session = manager.get_session(session_id)
        if not session:
            print(f"❌ Session not found: {session_id}")
            return
        print(f"📋 Continuing session: {session.title}")
        
        # Load history
        messages = manager.get_messages(session_id)
        for msg in messages:
            agent.conversation_history.append({
                "role": msg.role,
                "content": msg.content,
            })
    else:
        session = manager.create_session("Chat", model=agent.model)
    
    print("\n🏛️ Athena v0.2.0 - Lightweight Local AI Agent")
    print(f"   Model: {agent.model}")
    print(f"   Session: {session.id[:20]}...")
    print(f"   Memory: {agent.memory.db_path}")
    print(f"   Tools: {len(agent.tools.tools)} available")
    print("\n   Commands: 'quit' to exit, 'clear' to reset, 'memory' for info\n")
    
    try:
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
                
                if user_input.lower() == "memory":
                    count = agent.memory.count()
                    print(f"📊 Memory entries: {count}\n")
                    continue
                
                if user_input.lower() == "tools":
                    _handle_list_tools(agent)
                    print()
                    continue
                
                if user_input.lower() == "health":
                    _handle_health()
                    print()
                    continue
                
                # Save user message
                manager.add_message(session.id, "user", user_input)
                
                # Get response
                response = agent.chat(user_input)
                
                # Save assistant response
                manager.add_message(session.id, "assistant", response)
                
                print(f"\nAthena: {response}\n")
                
            except LLMConnectionError as e:
                print(f"\n❌ Connection Error: {e}\n")
                break
            except KeyboardInterrupt:
                print("\n\n👋 Goodbye!")
                break
            except EOFError:
                print("\n\n👋 Goodbye!")
                break
    
    except Exception as e:
        print(f"\n❌ Unexpected error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
