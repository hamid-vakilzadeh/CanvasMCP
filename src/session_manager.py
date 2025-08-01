"""Session management for stateful MCP server with automatic cleanup."""

import asyncio
import time
from dataclasses import dataclass, field
from typing import Dict, Optional, Tuple
import threading
import logging

logger = logging.getLogger(__name__)


@dataclass
class SessionData:
    """Session data containing user credentials and metadata."""
    
    base_url: str
    access_token: str
    api_key: str
    created_at: float = field(default_factory=time.time)
    last_accessed: float = field(default_factory=time.time)
    
    def update_access_time(self) -> None:
        """Update the last accessed timestamp."""
        self.last_accessed = time.time()
    
    def is_expired(self, timeout_minutes: int = 15) -> bool:
        """Check if session has expired based on idle timeout."""
        idle_time = time.time() - self.last_accessed
        return idle_time > (timeout_minutes * 60)


class SessionManager:
    """Manages user sessions with automatic cleanup of expired sessions."""
    
    def __init__(self, cleanup_interval_minutes: int = 5, session_timeout_minutes: int = 15):
        """
        Initialize the session manager.
        
        Args:
            cleanup_interval_minutes: How often to run cleanup (default: 5 minutes)
            session_timeout_minutes: Session idle timeout (default: 15 minutes)
        """
        self._sessions: Dict[str, SessionData] = {}
        self._lock = threading.RLock()
        self.cleanup_interval = cleanup_interval_minutes * 60  # Convert to seconds
        self.session_timeout = session_timeout_minutes
        self._cleanup_task: Optional[asyncio.Task] = None
        self._running = False
        
    def start_cleanup_task(self) -> None:
        """Start the automatic cleanup task."""
        if not self._running:
            self._running = True
            self._cleanup_task = asyncio.create_task(self._cleanup_loop())
            logger.info(f"Session cleanup task started (interval: {self.cleanup_interval}s, timeout: {self.session_timeout}m)")
    
    def stop_cleanup_task(self) -> None:
        """Stop the automatic cleanup task."""
        self._running = False
        if self._cleanup_task and not self._cleanup_task.done():
            self._cleanup_task.cancel()
            logger.info("Session cleanup task stopped")
    
    async def _cleanup_loop(self) -> None:
        """Background task that periodically cleans up expired sessions."""
        while self._running:
            try:
                await asyncio.sleep(self.cleanup_interval)
                self.cleanup_expired_sessions()
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in session cleanup task: {e}")
    
    def cleanup_expired_sessions(self) -> int:
        """Remove expired sessions and return count of removed sessions."""
        with self._lock:
            expired_sessions = [
                session_id for session_id, session_data in self._sessions.items()
                if session_data.is_expired(self.session_timeout)
            ]
            
            for session_id in expired_sessions:
                del self._sessions[session_id]
                logger.debug(f"Cleaned up expired session: {session_id}")
            
            if expired_sessions:
                print(f"🧹 [SESSION] Cleaned up {len(expired_sessions)} expired sessions")
                logger.info(f"Cleaned up {len(expired_sessions)} expired sessions")
            
            return len(expired_sessions)
    
    def create_session(self, session_id: str, base_url: str, access_token: str, api_key: str) -> None:
        """
        Create or update a session with user credentials.
        
        Args:
            session_id: Unique session identifier
            base_url: Canvas base URL
            access_token: Decrypted Canvas access token
            api_key: Original API key for reference
        """
        with self._lock:
            session_data = SessionData(
                base_url=base_url,
                access_token=access_token,
                api_key=api_key
            )
            self._sessions[session_id] = session_data
            logger.debug(f"Created session: {session_id}")
    
    def get_session(self, session_id: str) -> Optional[Tuple[str, str]]:
        """
        Get session credentials if session exists and is not expired.
        
        Args:
            session_id: Session identifier
            
        Returns:
            Tuple of (base_url, access_token) if valid, None otherwise
        """
        with self._lock:
            session_data = self._sessions.get(session_id)
            
            if not session_data:
                logger.debug(f"Session not found: {session_id}")
                return None
            
            if session_data.is_expired(self.session_timeout):
                logger.debug(f"Session expired: {session_id}")
                del self._sessions[session_id]
                return None
            
            # Update access time and return credentials
            session_data.update_access_time()
            logger.debug(f"Session accessed: {session_id}")
            return (session_data.base_url, session_data.access_token)
    
    def remove_session(self, session_id: str) -> bool:
        """
        Remove a specific session.
        
        Args:
            session_id: Session identifier
            
        Returns:
            True if session was removed, False if not found
        """
        with self._lock:
            if session_id in self._sessions:
                del self._sessions[session_id]
                logger.debug(f"Removed session: {session_id}")
                return True
            return False
    
    def get_session_count(self) -> int:
        """Get the current number of active sessions."""
        with self._lock:
            return len(self._sessions)
    
    def get_session_info(self, session_id: str) -> Optional[Dict]:
        """
        Get session information for debugging/monitoring.
        
        Args:
            session_id: Session identifier
            
        Returns:
            Dict with session info or None if not found
        """
        with self._lock:
            session_data = self._sessions.get(session_id)
            if not session_data:
                return None
            
            return {
                "session_id": session_id,
                "created_at": session_data.created_at,
                "last_accessed": session_data.last_accessed,
                "idle_time_seconds": time.time() - session_data.last_accessed,
                "is_expired": session_data.is_expired(self.session_timeout),
                "base_url": session_data.base_url,
                "api_key": session_data.api_key[:10] + "..." if session_data.api_key else None,
            }


# Global session manager instance
session_manager = SessionManager()

# Thread-local storage for current request context
import threading
_context_local = threading.local()


def set_current_session_credentials(base_url: str, access_token: str, session_id: str) -> None:
    """Set the current request's session credentials in thread-local storage."""
    _context_local.base_url = base_url
    _context_local.access_token = access_token  
    _context_local.session_id = session_id


def get_current_session_credentials() -> tuple[str, str] | None:
    """Get the current request's session credentials from thread-local storage."""
    try:
        return (_context_local.base_url, _context_local.access_token)
    except AttributeError:
        return None


def get_current_session_id() -> str | None:
    """Get the current request's session ID from thread-local storage."""
    try:
        return _context_local.session_id
    except AttributeError:
        return None