from __future__ import annotations

import json
import re
import sqlite3
import uuid
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from threading import RLock

from knowledge_forge.urls import canonicalize_url


@dataclass(frozen=True)
class Source:
    id: str
    canonical_url: str
    platform: str
    external_id: str | None
    title: str | None
    status: str
    created_at: str


@dataclass(frozen=True)
class TranscriptChunkInput:
    start_seconds: float
    end_seconds: float
    text: str


@dataclass(frozen=True)
class TranscriptChunk:
    id: str
    source_id: str
    position: int
    start_seconds: float
    end_seconds: float
    text: str


@dataclass(frozen=True)
class Collection:
    id: str
    name: str
    description: str | None
    created_at: str


class DuplicateSourceError(Exception):
    def __init__(self, source_id: str) -> None:
        self.source_id = source_id
        super().__init__(f"Source already exists: {source_id}")


class Library:
    def __init__(self, root: Path) -> None:
        self.root = Path(root)
        self.root.mkdir(parents=True, exist_ok=True)
        self._lock = RLock()
        self._connection = sqlite3.connect(self.root / "knowledge-forge.sqlite3", check_same_thread=False)
        self._connection.row_factory = sqlite3.Row
        self._initialize_schema()

    def _initialize_schema(self) -> None:
        with self._lock:
            self._connection.executescript(
                """
            CREATE TABLE IF NOT EXISTS sources (
                id TEXT PRIMARY KEY,
                canonical_url TEXT NOT NULL UNIQUE,
                platform TEXT NOT NULL,
                external_id TEXT,
                title TEXT,
                status TEXT NOT NULL,
                created_at TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS transcript_chunks (
                id TEXT PRIMARY KEY,
                source_id TEXT NOT NULL REFERENCES sources(id),
                position INTEGER NOT NULL,
                start_seconds REAL NOT NULL,
                end_seconds REAL NOT NULL,
                text TEXT NOT NULL,
                UNIQUE(source_id, position)
            );
            CREATE VIRTUAL TABLE IF NOT EXISTS transcript_search
            USING fts5(chunk_id UNINDEXED, source_id UNINDEXED, text);
            CREATE TABLE IF NOT EXISTS collections (
                id TEXT PRIMARY KEY,
                name TEXT NOT NULL UNIQUE,
                description TEXT,
                created_at TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS collection_sources (
                collection_id TEXT NOT NULL REFERENCES collections(id),
                source_id TEXT NOT NULL REFERENCES sources(id),
                PRIMARY KEY (collection_id, source_id)
            );
                """
            )
            self._connection.commit()

    def create_source(self, url: str, title: str | None = None) -> Source:
        canonical = canonicalize_url(url)
        with self._lock:
            existing = self._connection.execute(
                "SELECT id FROM sources WHERE canonical_url = ?", (canonical.canonical_url,)
            ).fetchone()
            if existing:
                raise DuplicateSourceError(existing["id"])

            source = Source(
                id=str(uuid.uuid4()),
                canonical_url=canonical.canonical_url,
                platform=canonical.platform,
                external_id=canonical.external_id,
                title=title,
                status="queued",
                created_at=datetime.now(UTC).isoformat(),
            )
            self._connection.execute(
                """
            INSERT INTO sources (id, canonical_url, platform, external_id, title, status, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
                (
                    source.id,
                    source.canonical_url,
                    source.platform,
                    source.external_id,
                    source.title,
                    source.status,
                    source.created_at,
                ),
            )
            self._connection.commit()
        return source

    def get_source(self, source_id: str) -> Source | None:
        with self._lock:
            row = self._connection.execute("SELECT * FROM sources WHERE id = ?", (source_id,)).fetchone()
        return self._source_from_row(row) if row else None

    def store_transcript(
        self, source_id: str, raw: dict[str, object], chunks: list[TranscriptChunkInput]
    ) -> None:
        if not self.get_source(source_id):
            raise KeyError(f"Unknown source: {source_id}")
        source_dir = self.root / "sources" / source_id
        source_dir.mkdir(parents=True, exist_ok=True)
        (source_dir / "raw-transcript.json").write_text(json.dumps(raw, indent=2), encoding="utf-8")

        with self._lock:
            self._connection.execute("DELETE FROM transcript_search WHERE source_id = ?", (source_id,))
            self._connection.execute("DELETE FROM transcript_chunks WHERE source_id = ?", (source_id,))
            for position, chunk in enumerate(chunks):
                chunk_id = str(uuid.uuid4())
                self._connection.execute(
                """
                INSERT INTO transcript_chunks
                (id, source_id, position, start_seconds, end_seconds, text)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                    (
                        chunk_id,
                        source_id,
                        position,
                        chunk.start_seconds,
                        chunk.end_seconds,
                        chunk.text,
                    ),
                )
                self._connection.execute(
                    "INSERT INTO transcript_search (chunk_id, source_id, text) VALUES (?, ?, ?)",
                    (chunk_id, source_id, chunk.text),
                )
            self._connection.execute("UPDATE sources SET status = 'ready' WHERE id = ?", (source_id,))
            self._connection.commit()

    def set_status(self, source_id: str, status: str) -> None:
        with self._lock:
            cursor = self._connection.execute("UPDATE sources SET status = ? WHERE id = ?", (status, source_id))
            self._connection.commit()
        if cursor.rowcount == 0:
            raise KeyError(f"Unknown source: {source_id}")

    def search(self, query: str) -> list[TranscriptChunk]:
        terms = re.findall(r"[\w$]+", query.lower())
        if not terms:
            return []
        fts_query = " OR ".join(terms)
        with self._lock:
            rows = self._connection.execute(
                """
            SELECT chunks.* FROM transcript_search AS search
            JOIN transcript_chunks AS chunks ON chunks.id = search.chunk_id
            WHERE transcript_search MATCH ?
            ORDER BY rank
                """,
                (fts_query,),
            ).fetchall()
        return [self._chunk_from_row(row) for row in rows]

    def export_markdown(self, source_id: str) -> str:
        source = self.get_source(source_id)
        if not source:
            raise KeyError(f"Unknown source: {source_id}")
        with self._lock:
            rows = self._connection.execute(
                "SELECT * FROM transcript_chunks WHERE source_id = ? ORDER BY position", (source_id,)
            ).fetchall()
        heading = source.title or source.canonical_url
        lines = [f"# {heading}", "", f"Source: {source.canonical_url}", "", "## Transcript", ""]
        for row in rows:
            chunk = self._chunk_from_row(row)
            seconds = int(chunk.start_seconds)
            lines.append(f"[{self._format_timestamp(seconds)}]({source.canonical_url}&t={seconds}s) {chunk.text}")
        return "\n".join(lines) + "\n"

    def create_collection(self, name: str, description: str | None = None) -> Collection:
        collection = Collection(
            id=str(uuid.uuid4()),
            name=name.strip(),
            description=description,
            created_at=datetime.now(UTC).isoformat(),
        )
        with self._lock:
            self._connection.execute(
                "INSERT INTO collections (id, name, description, created_at) VALUES (?, ?, ?, ?)",
                (collection.id, collection.name, collection.description, collection.created_at),
            )
            self._connection.commit()
        return collection

    def add_source_to_collection(self, source_id: str, collection_id: str) -> None:
        if not self.get_source(source_id):
            raise KeyError(f"Unknown source: {source_id}")
        with self._lock:
            self._connection.execute(
                "INSERT OR IGNORE INTO collection_sources (collection_id, source_id) VALUES (?, ?)",
                (collection_id, source_id),
            )
            self._connection.commit()

    def list_collection_sources(self, collection_id: str) -> list[Source]:
        with self._lock:
            rows = self._connection.execute(
                """
                SELECT sources.* FROM sources
                JOIN collection_sources ON collection_sources.source_id = sources.id
                WHERE collection_sources.collection_id = ?
                ORDER BY sources.created_at
                """,
                (collection_id,),
            ).fetchall()
        return [self._source_from_row(row) for row in rows]

    @staticmethod
    def _source_from_row(row: sqlite3.Row) -> Source:
        return Source(
            id=row["id"],
            canonical_url=row["canonical_url"],
            platform=row["platform"],
            external_id=row["external_id"],
            title=row["title"],
            status=row["status"],
            created_at=row["created_at"],
        )

    @staticmethod
    def _chunk_from_row(row: sqlite3.Row) -> TranscriptChunk:
        return TranscriptChunk(
            id=row["id"],
            source_id=row["source_id"],
            position=row["position"],
            start_seconds=row["start_seconds"],
            end_seconds=row["end_seconds"],
            text=row["text"],
        )

    @staticmethod
    def _format_timestamp(total_seconds: int) -> str:
        minutes, seconds = divmod(total_seconds, 60)
        hours, minutes = divmod(minutes, 60)
        return f"{hours:02d}:{minutes:02d}:{seconds:02d}" if hours else f"{minutes:02d}:{seconds:02d}"
