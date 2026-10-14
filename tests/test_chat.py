from fastapi.testclient import TestClient

from knowledge_forge.app import create_app
from knowledge_forge.chat import OpenAICompatibleAnswerer
from knowledge_forge.library import TranscriptChunkInput


class FakeAnswerer:
    def answer(self, question: str, evidence: list[str]) -> str:
        assert question == "What was the pricing?"
        assert evidence == ["[01:13] Pricing started at $49."]
        return "The initial price was $49."


def test_chat_returns_an_answer_with_timestamped_evidence(tmp_path) -> None:
    app = create_app(tmp_path, answerer=FakeAnswerer())
    client = TestClient(app)
    source = client.post("/api/sources", json={"url": "https://youtu.be/abc123XYZ09"}).json()
    app.state.library.store_transcript(
        source["id"],
        raw={"origin": "fixture"},
        chunks=[TranscriptChunkInput(start_seconds=73, end_seconds=78, text="Pricing started at $49.")],
    )

    response = client.post("/api/chat", json={"question": "What was the pricing?"})

    assert response.status_code == 200
    assert response.json()["answer"] == "The initial price was $49."
    assert response.json()["citations"][0]["timestamp"] == "01:13"
    assert response.json()["citations"][0]["url"].endswith("&t=73s")


class FakeResponse:
    def raise_for_status(self) -> None:
        return None

    def json(self) -> dict[str, object]:
        return {"choices": [{"message": {"content": "The initial price was $49."}}]}


class FakeHttpClient:
    def __init__(self) -> None:
        self.request: dict[str, object] | None = None

    def post(self, url: str, **kwargs: object) -> FakeResponse:
        self.request = {"url": url, **kwargs}
        return FakeResponse()


def test_openai_compatible_answerer_sends_only_retrieved_evidence() -> None:
    client = FakeHttpClient()
    answerer = OpenAICompatibleAnswerer(api_key="test-key", model="gpt-test", client=client)

    result = answerer.answer("What was the pricing?", ["[01:13] Pricing started at $49."])

    assert result == "The initial price was $49."
    assert client.request is not None
    assert client.request["url"] == "https://api.openai.com/v1/chat/completions"
    assert client.request["json"]["messages"][1]["content"].endswith("[01:13] Pricing started at $49.")
