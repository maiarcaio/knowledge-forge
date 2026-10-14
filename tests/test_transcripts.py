import json

from knowledge_forge.library import Library, TranscriptChunkInput


def test_library_preserves_raw_transcript_indexes_chunks_and_exports_markdown(tmp_path) -> None:
    library = Library(tmp_path)
    source = library.create_source("https://youtu.be/abc123XYZ09", title="Evidence interview")
    raw = {"language": "en", "events": [{"tStartMs": 73000, "segs": [{"utf8": "pricing"}]}]}

    library.store_transcript(
        source.id,
        raw=raw,
        chunks=[
            TranscriptChunkInput(start_seconds=73, end_seconds=79, text="Our pricing started at $49."),
            TranscriptChunkInput(start_seconds=80, end_seconds=86, text="We changed the onboarding flow."),
        ],
    )

    assert json.loads((tmp_path / "sources" / source.id / "raw-transcript.json").read_text()) == raw
    assert library.get_source(source.id).status == "ready"
    assert [chunk.text for chunk in library.search("pricing")] == ["Our pricing started at $49."]
    markdown = library.export_markdown(source.id)
    assert "[01:13](https://www.youtube.com/watch?v=abc123XYZ09&t=73s) Our pricing started at $49." in markdown
