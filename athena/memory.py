"""
Memory - Persistent storage for Athena
Uses SQLite with FTS5 for full-text search.
"""
import sqlite3
from datetime import datetime
from typing import List, Dict, Optional
from pathlib import Path


class Memory:
    """
    SQLite-based memory with full-text search.
    
    Features:
    - Persistent across sessions
    - Full-text search via FTS5
    - Category-based organization
    - Automatic timestamps
    """
    
    def __init__(self, db_path: str = "~/.athena/memory.db"):
        self.db_path = Path(db_path).expanduser()
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_db()
    
    def _init_db(self):
        """Initialize database schema."""
        with sqlite3.connect(self.db_path) as conn:
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
    
    def save(self, content: str, category: str = "general") -> int:
        """Save a memory entry."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute(
                "INSERT INTO memories (content, category) VALUES (?, ?)",
                (content, category)
            )
            return cursor.lastrowid
    
    def search(self, query: str, limit: int = 5, category: Optional[str] = None) -> List[Dict]:
        """Search memories using full-text search."""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            
            if category:
                cursor = conn.execute(
                    """SELECT m.id, m.content, m.category, m.created_at
                       FROM memories m
                       JOIN memories_fts f ON m.id = f.rowid
                       WHERE memories_fts MATCH ? AND m.category = ?
                       ORDER BY rank
                       LIMIT ?""",
                    (query, category, limit)
                )
            else:
                cursor = conn.execute(
                    """SELECT m.id, m.content, m.category, m.created_at
                       FROM memories m
                       JOIN memories_fts f ON m.id = f.rowid
                       WHERE memories_fts MATCH ?
                       ORDER BY rank
                       LIMIT ?""",
                    (query, limit)
                )
            
            return [dict(row) for row in cursor.fetchall()]
    
    def get_recent(self, limit: int = 10, category: Optional[str] = None) -> List[Dict]:
        """Get recent memories."""
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
    
    def delete(self, memory_id: int) -> bool:
        """Delete a memory entry."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute(
                "DELETE FROM memories WHERE id = ?",
                (memory_id,)
            )
            return cursor.rowcount > 0
    
    def clear(self, category: Optional[str] = None):
        """Clear memories (optionally by category)."""
        with sqlite3.connect(self.db_path) as conn:
            if category:
                conn.execute(
                    "DELETE FROM memories WHERE category = ?",
                    (category,)
                )
            else:
                conn.execute("DELETE FROM memories")
    
    def count(self, category: Optional[str] = None) -> int:
        """Count total memories."""
        with sqlite3.connect(self.db_path) as conn:
            if category:
                cursor = conn.execute(
                    "SELECT COUNT(*) FROM memories WHERE category = ?",
                    (category,)
                )
            else:
                cursor = conn.execute("SELECT COUNT(*) FROM memories")
            return cursor.fetchone()[0]
