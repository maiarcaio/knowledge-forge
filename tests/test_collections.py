from knowledge_forge.library import Library


def test_library_creates_a_collection_and_assigns_a_source(tmp_path) -> None:
    library = Library(tmp_path)
    source = library.create_source("https://youtu.be/abc123XYZ09")

    collection = library.create_collection("AI engineering", "Things to build and study")
    library.add_source_to_collection(source.id, collection.id)

    assert library.list_collection_sources(collection.id) == [source]
