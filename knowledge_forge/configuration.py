from collections.abc import Mapping

from knowledge_forge.chat import Answerer, EvidenceOnlyAnswerer, OpenAICompatibleAnswerer


def answerer_from_environment(environment: Mapping[str, str]) -> Answerer:
    api_key = environment.get("KNOWLEDGE_FORGE_API_KEY")
    if not api_key:
        return EvidenceOnlyAnswerer()
    return OpenAICompatibleAnswerer(
        api_key=api_key,
        model=environment.get("KNOWLEDGE_FORGE_MODEL", "gpt-4.1-mini"),
        base_url=environment.get("KNOWLEDGE_FORGE_BASE_URL", "https://api.openai.com/v1"),
    )
