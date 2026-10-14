from knowledge_forge.library import DuplicateSourceError, Library


def test_library_persists_source_and_rejects_a_tracking_url_duplicate(tmp_path) -> None:
    library = Library(tmp_path)
    created = library.create_source(
        "https://www.youtube.com/watch?v=abc123XYZ09",
        title="A long interview",
    )

    assert created.status == "queued"
    assert created.platform == "youtube"
    assert library.get_source(created.id).title == "A long interview"

    try:
        library.create_source("https://youtu.be/abc123XYZ09?feature=shared")
    except DuplicateSourceError as error:
        assert error.source_id == created.id
    else:
        raise AssertionError("Expected a duplicate source error")
