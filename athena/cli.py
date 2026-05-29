"""
CLI - Command-line interface for Athena
"""
import argparse
import sys
from pathlib import Path

from .agent import Agent


def main():
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(
        description="Athena - Lightweight Local AI Agent",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  athena                          # Start interactive chat
  athena -m llama3.2:3b           # Use specific model
  athena --memory-search "query"  # Search memories
  athena --memory-save "content"  # Save to memory
  athena --memory-list            # List recent memories
        """
    )
    
    parser.add_argument(
        "-m", "--model",
        default="llama3.2:3b",
        help="Ollama model to use (default: llama3.2:3b)"
    )
    
    parser.add_argument(
        "--ollama-url",
        default="http://localhost:11434",
        help="Ollama API URL (default: http://localhost:11434)"
    )
    
    parser.add_argument(
        "--memory-path",
        default="~/.athena/memory.db",
        help="Path to memory database (default: ~/.athena/memory.db)"
    )
    
    parser.add_argument(
        "--memory-search",
        metavar="QUERY",
        help="Search memories and exit"
    )
    
    parser.add_argument(
        "--memory-save",
        metavar="CONTENT",
        help="Save content to memory and exit"
    )
    
    parser.add_argument(
        "--memory-category",
        default="general",
        help="Category for memory operations (default: general)"
    )
    
    parser.add_argument(
        "--memory-list",
        action="store_true",
        help="List recent memories and exit"
    )
    
    parser.add_argument(
        "--memory-count",
        action="store_true",
        help="Count total memories and exit"
    )
    
    parser.add_argument(
        "--version",
        action="version",
        version=f"%(prog)s 0.1.0"
    )
    
    args = parser.parse_args()
    
    # Memory operations (non-interactive)
    if args.memory_search:
        agent = Agent(model=args.model, memory_path=args.memory_path)
        results = agent.memory.search(args.memory_search, category=args.memory_category)
        if results:
            print(f"Found {len(results)} results:")
            for r in results:
                print(f"  [{r['category']}] {r['content'][:100]}...")
        else:
            print("No memories found.")
        return
    
    if args.memory_save:
        agent = Agent(model=args.model, memory_path=args.memory_path)
        memory_id = agent.memory.save(args.memory_save, category=args.memory_category)
        print(f"Saved to memory (id: {memory_id})")
        return
    
    if args.memory_list:
        agent = Agent(model=args.model, memory_path=args.memory_path)
        memories = agent.memory.get_recent(limit=20, category=args.memory_category)
        if memories:
            print(f"Recent memories ({len(memories)}):")
            for m in memories:
                print(f"  [{m['category']}] {m['content'][:80]}...")
        else:
            print("No memories yet.")
        return
    
    if args.memory_count:
        agent = Agent(model=args.model, memory_path=args.memory_path)
        count = agent.memory.count(args.memory_category)
        print(f"Total memories: {count}")
        return
    
    # Interactive chat mode
    print(f"Athena v0.1.0 - Lightweight Local AI Agent")
    print(f"Model: {args.model}")
    print(f"Memory: {args.memory_path}")
    print(f"Type 'quit' or 'exit' to stop.\n")
    
    agent = Agent(
        model=args.model,
        ollama_url=args.ollama_url,
        memory_path=args.memory_path,
    )
    
    while True:
        try:
            user_input = input("You: ").strip()
            
            if not user_input:
                continue
            
            if user_input.lower() in ("quit", "exit", "q"):
                print("Goodbye!")
                break
            
            if user_input.lower() == "clear":
                agent.conversation_history.clear()
                print("Conversation cleared.")
                continue
            
            if user_input.lower() == "memory":
                count = agent.memory.count()
                print(f"Memory entries: {count}")
                continue
            
            response = agent.chat(user_input)
            print(f"\nAthena: {response}\n")
            
        except KeyboardInterrupt:
            print("\nGoodbye!")
            break
        except EOFError:
            print("\nGoodbye!")
            break


if __name__ == "__main__":
    main()
