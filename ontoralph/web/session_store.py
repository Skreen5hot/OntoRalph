"""Session token management for OntoRalph Web API.

This module provides secure session token generation and validation.
Tokens are used to authenticate SSE connections without exposing API keys.
"""

import secrets
import threading
from dataclasses import dataclass
from datetime import datetime, timedelta


@dataclass
class Session:
    """A session containing provider and API key information."""

    token: str
    provider: str
    api_key: str
    expires_at: datetime
    created_at: datetime


class SessionStore:
    """Thread-safe in-memory session token store.

    Sessions expire after 30 minutes of inactivity and are automatically
    extended when used.
    """

    DEFAULT_TTL_MINUTES = 30
    TOKEN_PREFIX = "ort_"
    TOKEN_BYTES = 32

    def __init__(self, ttl_minutes: int = DEFAULT_TTL_MINUTES) -> None:
        """Initialize the session store.

        Args:
            ttl_minutes: Token TTL in minutes (default: 30)
        """
        self._sessions: dict[str, Session] = {}
        self._lock = threading.RLock()
        self._ttl = timedelta(minutes=ttl_minutes)

    def create_session(self, provider: str, api_key: str) -> Session:
        """Create a new session token.

        Args:
            provider: LLM provider name ('claude', 'openai', 'mock')
            api_key: API key for the provider

        Returns:
            Session object with token and expiration
        """
        # Generate cryptographically random token
        random_bytes = secrets.token_urlsafe(self.TOKEN_BYTES)
        token = f"{self.TOKEN_PREFIX}{random_bytes}"

        now = datetime.now()
        session = Session(
            token=token,
            provider=provider,
            api_key=api_key,
            expires_at=now + self._ttl,
            created_at=now,
        )

        with self._lock:
            # Clean up expired sessions periodically
            self._cleanup_expired()
            self._sessions[token] = session

        return session

    def validate_session(self, token: str) -> Session | None:
        """Validate a session token and extend its TTL.

        Args:
            token: The session token to validate

        Returns:
            Session if valid, None if invalid or expired
        """
        with self._lock:
            session = self._sessions.get(token)
            if session is None:
                return None

            # Check if expired
            if datetime.now() > session.expires_at:
                del self._sessions[token]
                return None

            # Extend TTL on successful validation
            session.expires_at = datetime.now() + self._ttl
            return session

    def get_session(self, token: str) -> Session | None:
        """Get session without extending TTL.

        Args:
            token: The session token

        Returns:
            Session if valid, None if invalid or expired
        """
        with self._lock:
            session = self._sessions.get(token)
            if session is None:
                return None

            if datetime.now() > session.expires_at:
                del self._sessions[token]
                return None

            return session

    def invalidate_session(self, token: str) -> bool:
        """Invalidate a session token.

        Args:
            token: The session token to invalidate

        Returns:
            True if session was invalidated, False if not found
        """
        with self._lock:
            if token in self._sessions:
                del self._sessions[token]
                return True
            return False

    def _cleanup_expired(self) -> int:
        """Remove all expired sessions.

        Returns:
            Number of sessions removed
        """
        now = datetime.now()
        expired = [
            token
            for token, session in self._sessions.items()
            if now > session.expires_at
        ]
        for token in expired:
            del self._sessions[token]
        return len(expired)

    def clear_all(self) -> int:
        """Clear all sessions (e.g., on server shutdown).

        Returns:
            Number of sessions cleared
        """
        with self._lock:
            count = len(self._sessions)
            self._sessions.clear()
            return count

    @property
    def session_count(self) -> int:
        """Number of active sessions."""
        with self._lock:
            self._cleanup_expired()
            return len(self._sessions)


# Global session store instance
_session_store: SessionStore | None = None


def get_session_store() -> SessionStore:
    """Get the global session store instance.

    Returns:
        The singleton SessionStore instance
    """
    global _session_store
    if _session_store is None:
        _session_store = SessionStore()
    return _session_store


def reset_session_store() -> None:
    """Reset the global session store (for testing)."""
    global _session_store
    if _session_store is not None:
        _session_store.clear_all()
    _session_store = None
