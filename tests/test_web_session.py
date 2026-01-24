"""Tests for session store."""

import time
from datetime import datetime, timedelta

from ontoralph.web.session_store import (
    Session,
    SessionStore,
    get_session_store,
    reset_session_store,
)


class TestSessionStore:
    """Tests for SessionStore class."""

    def setup_method(self) -> None:
        """Reset session store before each test."""
        reset_session_store()

    def test_create_session(self) -> None:
        """Test creating a session."""
        store = SessionStore()
        session = store.create_session("claude", "sk-ant-test123")

        assert session.token.startswith("ort_")
        assert len(session.token) > 40  # Token should be substantial
        assert session.provider == "claude"
        assert session.api_key == "sk-ant-test123"
        assert session.expires_at > datetime.now()

    def test_session_token_uniqueness(self) -> None:
        """Test that each session gets a unique token."""
        store = SessionStore()
        tokens = set()

        for _ in range(100):
            session = store.create_session("mock", "key")
            assert session.token not in tokens
            tokens.add(session.token)

    def test_validate_session_success(self) -> None:
        """Test validating a valid session."""
        store = SessionStore()
        session = store.create_session("claude", "sk-ant-test123")

        validated = store.validate_session(session.token)
        assert validated is not None
        assert validated.provider == "claude"
        assert validated.api_key == "sk-ant-test123"

    def test_validate_session_invalid_token(self) -> None:
        """Test validating an invalid token returns None."""
        store = SessionStore()
        validated = store.validate_session("ort_invalid_token")
        assert validated is None

    def test_validate_session_extends_ttl(self) -> None:
        """Test that validation extends the TTL."""
        store = SessionStore(ttl_minutes=1)
        session = store.create_session("claude", "key")

        original_expires = session.expires_at

        # Small delay
        time.sleep(0.1)

        # Validate should extend TTL
        validated = store.validate_session(session.token)
        assert validated is not None
        assert validated.expires_at > original_expires

    def test_validate_session_expired(self) -> None:
        """Test that expired sessions are rejected."""
        store = SessionStore(ttl_minutes=0)  # Immediate expiration

        session = store.create_session("claude", "key")

        # Wait a tiny bit for expiration
        time.sleep(0.01)

        validated = store.validate_session(session.token)
        assert validated is None

    def test_get_session_no_extend(self) -> None:
        """Test get_session doesn't extend TTL."""
        store = SessionStore(ttl_minutes=1)
        session = store.create_session("claude", "key")

        original_expires = session.expires_at

        # Small delay
        time.sleep(0.1)

        # get_session should NOT extend TTL
        retrieved = store.get_session(session.token)
        assert retrieved is not None
        assert retrieved.expires_at == original_expires

    def test_invalidate_session(self) -> None:
        """Test invalidating a session."""
        store = SessionStore()
        session = store.create_session("claude", "key")

        # Session is valid
        assert store.validate_session(session.token) is not None

        # Invalidate
        result = store.invalidate_session(session.token)
        assert result is True

        # Session is no longer valid
        assert store.validate_session(session.token) is None

    def test_invalidate_nonexistent_session(self) -> None:
        """Test invalidating a nonexistent session returns False."""
        store = SessionStore()
        result = store.invalidate_session("ort_nonexistent")
        assert result is False

    def test_session_count(self) -> None:
        """Test session count property."""
        store = SessionStore()
        assert store.session_count == 0

        store.create_session("claude", "key1")
        assert store.session_count == 1

        store.create_session("openai", "key2")
        assert store.session_count == 2

    def test_clear_all(self) -> None:
        """Test clearing all sessions."""
        store = SessionStore()

        for i in range(5):
            store.create_session("mock", f"key{i}")

        assert store.session_count == 5

        cleared = store.clear_all()
        assert cleared == 5
        assert store.session_count == 0

    def test_cleanup_expired(self) -> None:
        """Test that expired sessions are cleaned up."""
        store = SessionStore(ttl_minutes=0)  # Immediate expiration

        # Create some sessions
        for i in range(5):
            store.create_session("mock", f"key{i}")

        # Wait for expiration
        time.sleep(0.01)

        # Access session_count triggers cleanup
        assert store.session_count == 0


class TestGlobalSessionStore:
    """Tests for global session store functions."""

    def setup_method(self) -> None:
        """Reset session store before each test."""
        reset_session_store()

    def test_get_session_store_singleton(self) -> None:
        """Test that get_session_store returns the same instance."""
        store1 = get_session_store()
        store2 = get_session_store()
        assert store1 is store2

    def test_reset_session_store(self) -> None:
        """Test that reset clears the store."""
        store = get_session_store()
        store.create_session("claude", "key")
        assert store.session_count == 1

        reset_session_store()

        # New store should be empty
        new_store = get_session_store()
        assert new_store.session_count == 0
        assert new_store is not store


class TestSessionDataclass:
    """Tests for Session dataclass."""

    def test_session_fields(self) -> None:
        """Test Session dataclass fields."""
        now = datetime.now()
        expires = now + timedelta(minutes=30)

        session = Session(
            token="ort_test123",
            provider="claude",
            api_key="sk-ant-abc",
            expires_at=expires,
            created_at=now,
        )

        assert session.token == "ort_test123"
        assert session.provider == "claude"
        assert session.api_key == "sk-ant-abc"
        assert session.expires_at == expires
        assert session.created_at == now
