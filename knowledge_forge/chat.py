from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

import httpx

from knowledge_forge.library import Library


class Answerer(Protocol):
    def answer(self, question: str, evidence: list[str]) -> str: ...


class EvidenceOnlyAnswerer:
    def answer(self, question: str, evidence: list[str]) -> str:
        if not evidence:
            return "No matching evidence was found in your local library."
        return "AI provider not configured. Review the matching evidence below or configure a provider."


class OpenAICompatibleAnswerer:
    """Small adapter for OpenAI-compatible chat-completions endpoints."""

    def __init__(
        self,
        api_key: str,
        model: str,
        base_url: str = "https://api.openai.com/v1",
        client: object | None = None,
    ) -> None:
        self._api_key = api_key
        self._model = model
        self._base_url = base_url.rstrip("/")
        self._client = client or httpx.Client()

    def answer(self, question: str, evidence: list[str]) -> str:
        context = "\n\n".join(evidence) or "No evidence was retrieved."
        response = self._client.post(
            f"{self._base_url}/chat/completions",
            headers={"Authorization": f"Bearer {self._api_key}"},
            timeout=45,
            json={
                "model": self._model,
                "temperature": 0.2,
                "messages": [
                    {
                        "role": "system",
                        "content": "Answer only from the supplied evidence. State when evidence is missing.",
                    },
                    {"role": "user", "content": f"Question: {question}\n\nEvidence:\n{context}"},
                ],
            },
        )
        response.raise_for_status()
        content = response.json()["choices"][0]["message"]["content"]
        return str(content)


@dataclass(frozen=True)
class Citation:
    source_id: str
    source_title: str | None
    url: str
    timestamp: str
    text: str


@dataclass(frozen=True)
class ChatResult:
    answer: str
    citations: list[Citation]


class ChatService:
    def __init__(self, library: Library, answerer: Answerer) -> None:
        self._library = library
        self._answerer = answerer

    def answer(self, question: str) -> ChatResult:
        chunks = self._library.search(question)[:6]
        citations: list[Citation] = []
        evidence: list[str] = []
        for chunk in chunks:
            source = self._library.get_source(chunk.source_id)
            if not source:
                continue
            seconds = int(chunk.start_seconds)
            minutes, remainder = divmod(seconds, 60)
            hours, minutes = divmod(minutes, 60)
            timestamp = f"{hours:02d}:{minutes:02d}:{remainder:02d}" if hours else f"{minutes:02d}:{remainder:02d}"
            separator = "&" if "?" in source.canonical_url else "?"
            url = f"{source.canonical_url}{separator}t={seconds}s"
            citations.append(
                Citation(
                    source_id=source.id,
                    source_title=source.title,
                    url=url,
                    timestamp=timestamp,
                    text=chunk.text,
                )
            )
            evidence.append(f"[{timestamp}] {chunk.text}")
        return ChatResult(answer=self._answerer.answer(question, evidence), citations=citations)
