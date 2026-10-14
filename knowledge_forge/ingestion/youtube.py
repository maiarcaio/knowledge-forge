from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Protocol

from youtube_transcript_api import YouTubeTranscriptApi
from youtube_transcript_api._errors import CouldNotRetrieveTranscript

from knowledge_forge.library import Library, TranscriptChunkInput


@dataclass(frozen=True)
class Caption:
    start_seconds: float
    duration_seconds: float
    text: str


class CaptionsUnavailableError(Exception):
    """Raised when a public video does not expose usable captions."""


class CaptionClient(Protocol):
    def fetch(self, video_id: str) -> list[Caption]: ...


class YouTubeCaptionClient:
    def fetch(self, video_id: str) -> list[Caption]:
        try:
            transcript = YouTubeTranscriptApi().fetch(video_id)
        except CouldNotRetrieveTranscript as error:
            raise CaptionsUnavailableError(str(error)) from error
        return [
            Caption(
                start_seconds=snippet.start,
                duration_seconds=snippet.duration,
                text=snippet.text,
            )
            for snippet in transcript
        ]


class YouTubeIngestor:
    def __init__(self, caption_client: CaptionClient | None = None) -> None:
        self._caption_client = caption_client or YouTubeCaptionClient()

    def ingest(self, library: Library, source_id: str) -> None:
        source = library.get_source(source_id)
        if not source:
            raise KeyError(f"Unknown source: {source_id}")
        if source.platform != "youtube" or not source.external_id:
            raise ValueError("YouTube ingestion requires a YouTube source with a video ID")

        try:
            captions = self._caption_client.fetch(source.external_id)
        except CaptionsUnavailableError:
            library.set_status(source_id, "captions_unavailable")
            return
        raw = {"provider": "youtube_captions", "video_id": source.external_id, "captions": [asdict(item) for item in captions]}
        chunks = [
            TranscriptChunkInput(
                start_seconds=caption.start_seconds,
                end_seconds=caption.start_seconds + caption.duration_seconds,
                text=caption.text,
            )
            for caption in captions
            if caption.text.strip()
        ]
        library.store_transcript(source_id, raw=raw, chunks=chunks)
