from fastapi.testclient import TestClient

from knowledge_forge.app import create_app
from knowledge_forge.ingestion.youtube import Caption, YouTubeIngestor
from knowledge_forge.library import TranscriptChunkInput


def test_source_api_creates_a_youtube_source_and_reports_duplicates(tmp_path) -> None:
    client = TestClient(create_app(tmp_path))

    created = client.post(
        "/api/sources",
        json={"url": "https://www.youtube.com/watch?v=abc123XYZ09&utm_source=save", "title": "Interview"},
    )

    assert created.status_code == 201
    assert created.json()["platform"] == "youtube"
    assert created.json()["status"] == "queued"

    duplicate = client.post("/api/sources", json={"url": "https://youtu.be/abc123XYZ09"})
    assert duplicate.status_code == 409
    assert duplicate.json()["detail"]["source_id"] == created.json()["id"]


def test_source_api_accepts_instagram_link_without_claiming_a_transcript(tmp_path) -> None:
    client = TestClient(create_app(tmp_path))

    response = client.post("/api/sources", json={"url": "https://www.instagram.com/reel/C0FFEE/"})

    assert response.status_code == 201
    assert response.json()["platform"] == "instagram"
    assert response.json()["status"] == "queued"
    assert response.json()["next_step"] == "manual_or_permitted_ingestion_required"


def test_search_and_collection_endpoints_return_evidence_with_timestamps(tmp_path) -> None:
    app = create_app(tmp_path)
    client = TestClient(app)
    created = client.post("/api/sources", json={"url": "https://youtu.be/abc123XYZ09"}).json()
    app.state.library.store_transcript(
        created["id"],
        raw={"origin": "fixture"},
        chunks=[
            TranscriptChunkInput(start_seconds=73, end_seconds=78, text="Pricing started at $49."),
        ],
    )

    search = client.get("/api/search", params={"q": "pricing"})
    collection = client.post("/api/collections", json={"name": "AI engineering"})

    assert search.status_code == 200
    assert search.json()["results"][0]["timestamp"] == "01:13"
    assert search.json()["results"][0]["source_url"].endswith("&t=73s")
    assert collection.status_code == 201
    assert collection.json()["name"] == "AI engineering"


class FakeCaptionClient:
    def fetch(self, video_id: str) -> list[Caption]:
        return [Caption(start_seconds=73, duration_seconds=5, text="Pricing started at $49.")]


def test_ingest_endpoint_processes_youtube_source_with_the_configured_adapter(tmp_path) -> None:
    app = create_app(tmp_path, youtube_ingestor=YouTubeIngestor(FakeCaptionClient()))
    client = TestClient(app)
    source = client.post("/api/sources", json={"url": "https://youtu.be/abc123XYZ09"}).json()

    response = client.post(f"/api/sources/{source['id']}/ingest")

    assert response.status_code == 200
    assert response.json()["status"] == "ready"
