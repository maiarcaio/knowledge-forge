from knowledge_forge.ingestion.youtube import Caption, CaptionsUnavailableError, YouTubeIngestor
from knowledge_forge.library import Library


class FakeCaptionClient:
    def fetch(self, video_id: str) -> list[Caption]:
        assert video_id == "abc123XYZ09"
        return [
            Caption(start_seconds=73, duration_seconds=4, text="Pricing started at $49."),
            Caption(start_seconds=77, duration_seconds=4, text="Then we changed onboarding."),
        ]


def test_youtube_ingestor_preserves_caption_evidence_and_marks_source_ready(tmp_path) -> None:
    library = Library(tmp_path)
    source = library.create_source("https://youtu.be/abc123XYZ09")

    YouTubeIngestor(FakeCaptionClient()).ingest(library, source.id)

    assert library.get_source(source.id).status == "ready"
    assert [chunk.text for chunk in library.search("onboarding")] == ["Then we changed onboarding."]


class UnavailableCaptionClient:
    def fetch(self, video_id: str) -> list[Caption]:
        raise CaptionsUnavailableError("No public captions")


def test_youtube_ingestor_marks_missing_captions_without_creating_a_fake_transcript(tmp_path) -> None:
    library = Library(tmp_path)
    source = library.create_source("https://youtu.be/abc123XYZ09")

    YouTubeIngestor(UnavailableCaptionClient()).ingest(library, source.id)

    assert library.get_source(source.id).status == "captions_unavailable"
    assert library.search("pricing") == []
