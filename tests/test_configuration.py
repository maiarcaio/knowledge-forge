from knowledge_forge.chat import EvidenceOnlyAnswerer, OpenAICompatibleAnswerer
from knowledge_forge.configuration import answerer_from_environment


def test_configuration_uses_openai_compatible_provider_only_when_a_key_is_present() -> None:
    configured = answerer_from_environment({"KNOWLEDGE_FORGE_API_KEY": "secret", "KNOWLEDGE_FORGE_MODEL": "gpt-test"})
    unconfigured = answerer_from_environment({})

    assert isinstance(configured, OpenAICompatibleAnswerer)
    assert isinstance(unconfigured, EvidenceOnlyAnswerer)
