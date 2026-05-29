"""
Memory - Persistent storage for Athena
Uses SQLite with FTS5 for full-text search.
"""
import sqlite3
from datetime import datetime
from typing import List, Dict, Optional
from pathlib import Path
import logging

logger = logging.getLogger(__name__)


class MemoryError(Exception):
    """Base exception for Memory errors."""
    pass


class Memory:
    """
    SQLite-based memory with full-text search.
    
    Features:
    - Persistent across sessions
    - Full-text search via FTS5
    - Category-based organization
    - Automatic timestamps
    - Thread-safe operations
    
    Example:
        >>> memory = Memory("~/.athena/memory.db")
        >>> memory.save("Python is great", category="tech")
        >>> results = memory.search("Python")
    """
    
    def __init__(self, db_path: str = "~/.athena/memory.db"):
        """
        Initialize Memory.
        
        Args:
            db_path: Path to SQLite database file
        """
        self.db_path = Path(db_path).expanduser()
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_db()
    
    def _init_db(self):
        """Initialize database schema."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                # Enable WAL mode for better concurrency
                conn.execute("PRAGMA journal_mode=WAL")
                
                conn.execute("""
                    CREATE TABLE IF NOT EXISTS memories (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        content TEXT NOT NULL,
                        category TEXT DEFAULT 'general',
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                """)
                
                # FTS5 index for full-text search
                conn.execute("""
                    CREATE VIRTUAL TABLE IF NOT EXISTS memories_fts USING fts5(
                        content,
                        category,
                        content='memories',
                        content_rowid='id'
                    )
                """)
                
                # Triggers to keep FTS in sync
                conn.execute("""
                    CREATE TRIGGER IF NOT EXISTS memories_ai AFTER INSERT ON memories BEGIN
                        INSERT INTO memories_fts(rowid, content, category)
                        VALUES (new.id, new.content, new.category);
                    END
                """)
                
                conn.execute("""
                    CREATE TRIGGER IF NOT EXISTS memories_ad AFTER DELETE ON memories BEGIN
                        INSERT INTO memories_fts(memories_fts, rowid, content, category)
                        VALUES ('delete', old.id, old.content, old.category);
                    END
                """)
                
                conn.execute("""
                    CREATE TRIGGER IF NOT EXISTS memories_au AFTER UPDATE ON memories BEGIN
                        INSERT INTO memories_fts(memories_fts, rowid, content, category)
                        VALUES ('delete', old.id, old.content, old.category);
                        INSERT INTO memories_fts(rowid, content, category)
                        VALUES (new.id, new.content, new.category);
                    END
                """)
                
                # Create indexes for better performance
                conn.execute(
                    "CREATE INDEX IF NOT EXISTS idx_memories_category ON memories(category)"
                )
                conn.execute(
                    "CREATE INDEX IF NOT EXISTS idx_memories_created ON memories(created_at)"
                )
                
                logger.debug(f"Memory database initialized at {self.db_path}")
        except sqlite3.Error as e:
            raise MemoryError(f"Failed to initialize database: {e}")
    
    def save(self, content: str, category: str = "general") -> int:
        """
        Save a memory entry.
        
        Args:
            content: Text content to save
            category: Category for organization
            
        Returns:
            ID of the saved memory
            
        Raises:
            MemoryError: If save fails
        """
        if not content or not content.strip():
            raise ValueError("Content cannot be empty")
        
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.execute(
                    "INSERT INTO memories (content, category) VALUES (?, ?)",
                    (content.strip(), category)
                )
                memory_id = cursor.lastrowid
                logger.debug(f"Saved memory {memory_id} in category '{category}'")
                return memory_id
        except sqlite3.Error as e:
            raise MemoryError(f"Failed to save memory: {e}")
    
    def search(self, query: str, limit: int = 5, category: Optional[str] = None) -> List[Dict]:
        """
        Search memories using full-text search.
        
        Args:
            query: Search query
            limit: Maximum results to return
            category: Filter by category
            
        Returns:
            List of matching memories
            
        Raises:
            MemoryError: If search fails
        """
        if not query or not query.strip():
            return []
        
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.row_factory = sqlite3.Row
                
                # Clean query for FTS5
                clean_query = query.strip()
                # Add quotes for exact phrase matching if multiple words
                if " " in clean_query:
                    clean_query = f'"{clean_query}"'
                
                if category:
                    cursor = conn.execute(
                        """SELECT m.id, m.content, m.category, m.created_at
                           FROM memories m
                           JOIN memories_fts f ON m.id = f.rowid
                           WHERE memories_fts MATCH ? AND m.category = ?
                           ORDER BY rank
                           LIMIT ?""",
                        (clean_query, category, limit)
                    )
                else:
                    cursor = conn.execute(
                        """SELECT m.id, m.content, m.category, m.created_at
                           FROM memories m
                           JOIN memories_fts f ON m.id = f.rowid
                           WHERE memories_fts MATCH ?
                           ORDER BY rank
                           LIMIT ?""",
                        (clean_query, limit)
                    )
                
                results = [dict(row) for row in cursor.fetchall()]
                logger.debug(f"Search for '{query}' returned {len(results)} results")
                return results
        except sqlite3.Error as e:
            logger.error(f"Search failed: {e}")
            return []
    
    def get_recent(self, limit: int = 10, category: Optional[str] = None) -> List[Dict]:
        """
        Get recent memories.
        
        Args:
            limit: Maximum results
            category: Filter by category
            
        Returns:
            List of recent memories
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.row_factory = sqlite3.Row
                
                if category:
                    cursor = conn.execute(
                        """SELECT id, content, category, created_at
                           FROM memories
                           WHERE category = ?
                           ORDER BY created_at DESC
                           LIMIT ?""",
                        (category, limit)
                    )
                else:
                    cursor = conn.execute(
                        """SELECT id, content, category, created_at
                           FROM memories
                           ORDER BY created_at DESC
                           LIMIT ?""",
                        (limit,)
                    )
                
                return [dict(row) for row in cursor.fetchall()]
        except sqlite3.Error as e:
            logger.error(f"Failed to get recent memories: {e}")
            return []
    
    def delete(self, memory_id: int) -> bool:
        """
        Delete a memory entry.
        
        Args:
            memory_id: ID of memory to delete
            
        Returns:
            True if deleted, False if not found
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.execute(
                    "DELETE FROM memories WHERE id = ?",
                    (memory_id,)
                )
                deleted = cursor.rowcount > 0
                if deleted:
                    logger.debug(f"Deleted memory {memory_id}")
                return deleted
        except sqlite3.Error as e:
            logger.error(f"Failed to delete memory: {e}")
            return False
    
    def clear(self, category: Optional[str] = None):
        """
        Clear memories (optionally by category).
        
        Args:
            category: If provided, only clear this category
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                if category:
                    conn.execute(
                        "DELETE FROM memories WHERE category = ?",
                        (category,)
                    )
                    logger.info(f"Cleared memories in category '{category}'")
                else:
                    conn.execute("DELETE FROM memories")
                    logger.info("Cleared all memories")
        except sqlite3.Error as e:
            raise MemoryError(f"Failed to clear memories: {e}")
    
    def count(self, category: Optional[str] = None) -> int:
        """
        Count total memories.
        
        Args:
            category: Count only this category
            
        Returns:
            Number of memories
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                if category:
                    cursor = conn.execute(
                        "SELECT COUNT(*) FROM memories WHERE category = ?",
                        (category,)
                    )
                else:
                    cursor = conn.execute("SELECT COUNT(*) FROM memories")
                return cursor.fetchone()[0]
        except sqlite3.Error as e:
            logger.error(f"Failed to count memories: {e}")
            return 0
    
    def get_categories(self) -> List[str]:
        """Get list of all categories."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.execute(
                    "SELECT DISTINCT category FROM memories ORDER BY category"
                )
                return [row[0] for row in cursor.fetchall()]
        except sqlite3.Error as e:
            logger.error(f"Failed to get categories: {e}")
            return []
