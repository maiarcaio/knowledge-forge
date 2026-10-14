import os
from pathlib import Path

from fastapi import FastAPI, HTTPException, status
from fastapi.responses import FileResponse, Response
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from knowledge_forge.chat import Answerer, ChatService
from knowledge_forge.configuration import answerer_from_environment
from knowledge_forge.ingestion.youtube import YouTubeIngestor
from knowledge_forge.library import DuplicateSourceError, Library, Source


class CreateSourceRequest(BaseModel):
    url: str = Field(min_length=1)
    title: str | None = None


class CreateCollectionRequest(BaseModel):
    name: str = Field(min_length=1)
    description: str | None = None


class ChatRequest(BaseModel):
    question: str = Field(min_length=1)


def _source_payload(source: Source) -> dict[str, str | None]:
    payload: dict[str, str | None] = {
        "id": source.id,
        "canonical_url": source.canonical_url,
        "platform": source.platform,
        "external_id": source.external_id,
        "title": source.title,
        "status": source.status,
        "created_at": source.created_at,
        "next_step": None,
    }
    if source.platform == "instagram":
        payload["next_step"] = "manual_or_permitted_ingestion_required"
    return payload


def _timestamp(seconds: float) -> str:
    minutes, remainder = divmod(int(seconds), 60)
    hours, minutes = divmod(minutes, 60)
    return f"{hours:02d}:{minutes:02d}:{remainder:02d}" if hours else f"{minutes:02d}:{remainder:02d}"


def _citation_url(url: str, seconds: float) -> str:
    separator = "&" if "?" in url else "?"
    return f"{url}{separator}t={int(seconds)}s"


def create_app(
    data_root: Path,
    youtube_ingestor: YouTubeIngestor | None = None,
    answerer: Answerer | None = None,
) -> FastAPI:
    app = FastAPI(title="Knowledge Forge", version="0.1.0")
    static_dir = Path(__file__).parent / "static"
    app.mount("/static", StaticFiles(directory=static_dir), name="static")
    app.state.library = Library(data_root)
    app.state.youtube_ingestor = youtube_ingestor or YouTubeIngestor()
    app.state.chat_service = ChatService(
        app.state.library,
        answerer or answerer_from_environment(os.environ),
    )

    @app.get("/", include_in_schema=False)
    def dashboard() -> FileResponse:
        return FileResponse(static_dir / "index.html")

    @app.post("/api/sources", status_code=status.HTTP_201_CREATED)
    def create_source(request: CreateSourceRequest) -> dict[str, str | None]:
        try:
            source = app.state.library.create_source(request.url, request.title)
        except DuplicateSourceError as error:
            raise HTTPException(status_code=409, detail={"source_id": error.source_id}) from error
        return _source_payload(source)

    @app.get("/api/sources/{source_id}")
    def get_source(source_id: str) -> dict[str, str | None]:
        source = app.state.library.get_source(source_id)
        if not source:
            raise HTTPException(status_code=404, detail="Source not found")
        return _source_payload(source)

    @app.get("/api/sources/{source_id}/export.md")
    def export_source(source_id: str) -> Response:
        try:
            markdown = app.state.library.export_markdown(source_id)
        except KeyError as error:
            raise HTTPException(status_code=404, detail="Source not found") from error
        return Response(content=markdown, media_type="text/markdown")

    @app.post("/api/sources/{source_id}/ingest")
    def ingest_source(source_id: str) -> dict[str, str | None]:
        source = app.state.library.get_source(source_id)
        if not source:
            raise HTTPException(status_code=404, detail="Source not found")
        if source.platform == "youtube":
            app.state.youtube_ingestor.ingest(app.state.library, source_id)
        elif source.platform == "instagram":
            return {
                **_source_payload(source),
                "next_step": "manual_or_permitted_ingestion_required",
            }
        processed = app.state.library.get_source(source_id)
        return _source_payload(processed) if processed else _source_payload(source)

    @app.get("/api/search")
    def search(q: str) -> dict[str, list[dict[str, str | float | None]]]:
        chunks = app.state.library.search(q)
        results: list[dict[str, str | float | None]] = []
        for chunk in chunks:
            source = app.state.library.get_source(chunk.source_id)
            if not source:
                continue
            results.append(
                {
                    "chunk_id": chunk.id,
                    "source_id": source.id,
                    "source_title": source.title,
                    "source_url": _citation_url(source.canonical_url, chunk.start_seconds),
                    "timestamp": _timestamp(chunk.start_seconds),
                    "start_seconds": chunk.start_seconds,
                    "end_seconds": chunk.end_seconds,
                    "text": chunk.text,
                }
            )
        return {"results": results}

    @app.post("/api/collections", status_code=status.HTTP_201_CREATED)
    def create_collection(request: CreateCollectionRequest) -> dict[str, str | None]:
        collection = app.state.library.create_collection(request.name, request.description)
        return {
            "id": collection.id,
            "name": collection.name,
            "description": collection.description,
            "created_at": collection.created_at,
        }

    @app.post("/api/chat")
    def chat(request: ChatRequest) -> dict[str, object]:
        result = app.state.chat_service.answer(request.question)
        return {
            "answer": result.answer,
            "citations": [
                {
                    "source_id": citation.source_id,
                    "source_title": citation.source_title,
                    "url": citation.url,
                    "timestamp": citation.timestamp,
                    "text": citation.text,
                }
                for citation in result.citations
            ],
        }

    return app


app = create_app(Path("data"))
