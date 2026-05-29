"""
Sessions - Session management for Athena
Persistent conversation history and session control.
"""
import json
import sqlite3
import logging
from datetime import datetime
from typing import List, Dict, Optional
from pathlib import Path
from dataclasses import dataclass, asdict

logger = logging.getLogger(__name__)


@dataclass
class Message:
    """A chat message."""
    role: str  # user, assistant, system
    content: str
    timestamp: Optional[str] = None
    
    def to_dict(self) -> Dict:
        return {
            "role": self.role,
            "content": self.content,
            "timestamp": self.timestamp or datetime.now().isoformat(),
        }


@dataclass
class Session:
    """A chat session."""
    id: str
    title: str
    created_at: str
    updated_at: str
    message_count: int = 0
    model: str = ""
    
    def to_dict(self) -> Dict:
        return asdict(self)


class SessionManager:
    """
    Manage chat sessions with persistent storage.
    
    Features:
    - Multiple sessions
    - Session history
    - Session search
    - Auto-titling
    
    Example:
        >>> manager = SessionManager()
        >>> session = manager.create_session("Research Notes")
        >>> manager.add_message(session.id, "user", "Hello")
        >>> messages = manager.get_messages(session.id)
    """
    
    def __init__(self, db_path: str = "~/.athena/sessions.db"):
        """Initialize session manager."""
        self.db_path = Path(db_path).expanduser()
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_db()
    
    def _init_db(self):
        """Initialize database schema."""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("PRAGMA journal_mode=WAL")
            
            conn.execute("""
                CREATE TABLE IF NOT EXISTS sessions (
                    id TEXT PRIMARY KEY,
                    title TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    message_count INTEGER DEFAULT 0,
                    model TEXT DEFAULT ''
                )
            """)
            
            conn.execute("""
                CREATE TABLE IF NOT EXISTS messages (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    session_id TEXT NOT NULL,
                    role TEXT NOT NULL,
                    content TEXT NOT NULL,
                    timestamp TEXT NOT NULL,
                    FOREIGN KEY (session_id) REFERENCES sessions(id)
                )
            """)
            
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_messages_session 
                ON messages(session_id)
            """)
    
    def create_session(self, title: str = "New Chat", model: str = "") -> Session:
        """Create a new session."""
        session_id = f"session_{int(datetime.now().timestamp() * 1000)}"
        now = datetime.now().isoformat()
        
        session = Session(
            id=session_id,
            title=title,
            created_at=now,
            updated_at=now,
            model=model,
        )
        
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                """INSERT INTO sessions (id, title, created_at, updated_at, model)
                   VALUES (?, ?, ?, ?, ?)""",
                (session.id, session.title, session.created_at, 
                 session.updated_at, session.model)
            )
        
        logger.info(f"Created session: {session_id}")
        return session
    
    def get_session(self, session_id: str) -> Optional[Session]:
        """Get a session by ID."""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.execute(
                "SELECT * FROM sessions WHERE id = ?",
                (session_id,)
            )
            row = cursor.fetchone()
            
            if row:
                return Session(**dict(row))
        return None
    
    def list_sessions(self, limit: int = 20) -> List[Session]:
        """List recent sessions."""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.execute(
                """SELECT * FROM sessions 
                   ORDER BY updated_at DESC 
                   LIMIT ?""",
                (limit,)
            )
            return [Session(**dict(row)) for row in cursor.fetchall()]
    
    def delete_session(self, session_id: str) -> bool:
        """Delete a session and its messages."""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("DELETE FROM messages WHERE session_id = ?", (session_id,))
            cursor = conn.execute("DELETE FROM sessions WHERE id = ?", (session_id,))
            return cursor.rowcount > 0
    
    def add_message(self, session_id: str, role: str, content: str) -> int:
        """Add a message to a session."""
        timestamp = datetime.now().isoformat()
        
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute(
                """INSERT INTO messages (session_id, role, content, timestamp)
                   VALUES (?, ?, ?, ?)""",
                (session_id, role, content, timestamp)
            )
            
            # Update session
            conn.execute(
                """UPDATE sessions 
                   SET updated_at = ?, message_count = message_count + 1
                   WHERE id = ?""",
                (timestamp, session_id)
            )
            
            return cursor.lastrowid
    
    def get_messages(self, session_id: str, limit: int = 50) -> List[Message]:
        """Get messages from a session."""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.execute(
                """SELECT role, content, timestamp 
                   FROM messages 
                   WHERE session_id = ?
                   ORDER BY timestamp DESC
                   LIMIT ?""",
                (session_id, limit)
            )
            messages = [Message(**dict(row)) for row in cursor.fetchall()]
            messages.reverse()  # Oldest first
            return messages
    
    def search_sessions(self, query: str) -> List[Session]:
        """Search sessions by title."""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.execute(
                """SELECT * FROM sessions 
                   WHERE title LIKE ?
                   ORDER BY updated_at DESC""",
                (f"%{query}%",)
            )
            return [Session(**dict(row)) for row in cursor.fetchall()]
    
    def update_title(self, session_id: str, title: str) -> bool:
        """Update session title."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute(
                "UPDATE sessions SET title = ? WHERE id = ?",
                (title, session_id)
            )
            return cursor.rowcount > 0
    
    def export_session(self, session_id: str) -> Optional[Dict]:
        """Export session as JSON."""
        session = self.get_session(session_id)
        if not session:
            return None
        
        messages = self.get_messages(session_id, limit=1000)
        
        return {
            "session": session.to_dict(),
            "messages": [m.to_dict() for m in messages],
        }
    
    def import_session(self, data: Dict) -> Optional[Session]:
        """Import session from JSON."""
        session_data = data.get("session", {})
        messages_data = data.get("messages", [])
        
        session = self.create_session(
            title=session_data.get("title", "Imported"),
            model=session_data.get("model", ""),
        )
        
        for msg in messages_data:
            self.add_message(
                session.id,
                msg.get("role", "user"),
                msg.get("content", "")
            )
        
        return session
