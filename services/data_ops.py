"""Shared ingestion and summarization services exposed to agent tools."""

from __future__ import annotations

import time
from typing import Dict, Optional

from collectors.blogs_collector import import_blogs_from_directory, summarize_blogs as summarize_db_blogs
from collectors.notes_collector import import_notes_from_directory, summarize_notes as summarize_db_notes
from collectors.photos_collector import import_photo_from_photoprism, summarize_photos as summarize_db_photos
from client.photoprism_client import Client as PhotoprismClient
from server import config

from .session import session_scope


def ingest_notes(directory: Optional[str] = None) -> Dict:
    """Import markdown notes into the database."""
    target_dir = str(directory or config.NOTES_DIR)
    started = time.time()
    with session_scope() as session:
        import_notes_from_directory(target_dir, session)
    duration = time.time() - started
    return {
        "task": "ingest_notes",
        "directory": target_dir,
        "elapsed_seconds": round(duration, 2),
    }


def ingest_blogs(directory: Optional[str] = None) -> Dict:
    target_dir = str(directory or config.BLOGS_DIR)
    started = time.time()
    with session_scope() as session:
        import_blogs_from_directory(target_dir, session)
    duration = time.time() - started
    return {
        "task": "ingest_blogs",
        "directory": target_dir,
        "elapsed_seconds": round(duration, 2),
    }


def ingest_photoprism_photos() -> Dict:
    client = _build_photoprism_client()
    started = time.time()
    with session_scope() as session:
        import_photo_from_photoprism(client, session)
    duration = time.time() - started
    return {
        "task": "ingest_photoprism_photos",
        "photoprism_domain": config.PHOTO_PRISM_DOMAIN,
        "elapsed_seconds": round(duration, 2),
    }


def summarize_notes() -> Dict:
    started = time.time()
    with session_scope() as session:
        summarize_db_notes(session)
    duration = time.time() - started
    return {
        "task": "summarize_notes",
        "elapsed_seconds": round(duration, 2),
    }


def summarize_blogs() -> Dict:
    started = time.time()
    with session_scope() as session:
        summarize_db_blogs(session)
    duration = time.time() - started
    return {
        "task": "summarize_blogs",
        "elapsed_seconds": round(duration, 2),
    }


def summarize_photoprism_photos() -> Dict:
    client = _build_photoprism_client()
    started = time.time()
    with session_scope() as session:
        summarize_db_photos(client, session)
    duration = time.time() - started
    return {
        "task": "summarize_photoprism_photos",
        "photoprism_domain": config.PHOTO_PRISM_DOMAIN,
        "elapsed_seconds": round(duration, 2),
    }


def _build_photoprism_client() -> PhotoprismClient:
    if not config.PHOTO_PRISM_USERNAME or not config.PHOTO_PRISM_PASSWORD:
        raise RuntimeError("Photoprism credentials are not configured via environment variables.")
    return PhotoprismClient(
        username=config.PHOTO_PRISM_USERNAME,
        password=config.PHOTO_PRISM_PASSWORD,
        domain=config.PHOTO_PRISM_DOMAIN,
    )
