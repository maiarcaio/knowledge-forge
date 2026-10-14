from knowledge_forge.urls import canonicalize_url


def test_canonicalize_youtube_watch_url_removes_tracking_parameters() -> None:
    result = canonicalize_url(
        "https://www.youtube.com/watch?v=abc123XYZ09&utm_source=saved&feature=share"
    )

    assert result.platform == "youtube"
    assert result.canonical_url == "https://www.youtube.com/watch?v=abc123XYZ09"
    assert result.external_id == "abc123XYZ09"
