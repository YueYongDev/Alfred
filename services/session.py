"""Database session utilities for service functions."""

from contextlib import contextmanager
from typing import Iterator

from sqlalchemy.orm import Session

from db.database import SessionLocal


@contextmanager
def session_scope() -> Iterator[Session]:
    """Provide a transactional scope around a series of operations."""
    session: Session = SessionLocal()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()
