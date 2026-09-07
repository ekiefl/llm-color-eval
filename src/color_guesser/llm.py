import os

from openai import AsyncOpenAI, OpenAI
from pydantic_ai.models import AbstractModel
from pydantic_ai.models.anthropic import AnthropicModel
from pydantic_ai.models.openai import OpenAIChatModel
from pydantic_ai.providers.ollama import OllamaProvider
from pydantic_ai.providers.openai import OpenAIProvider

OLLAMA_BASE_URL = "http://localhost:11434/v1"
GROQ_BASE_URL = "https://api.groq.com/openai/v1"
MAX_RETRIES = 8


def ollama_model(name: str) -> OpenAIChatModel:
    """Create a model served by a local Ollama instance.

    Args:
        name: Name of a model already pulled into Ollama.

    Returns:
        A model that talks to Ollama's OpenAI-compatible endpoint.
    """
    return OpenAIChatModel(name, provider=OllamaProvider(base_url=OLLAMA_BASE_URL))


def openai_compatible_model(name: str, base_url: str, api_key_env: str) -> OpenAIChatModel:
    """Create a model served by any OpenAI-compatible endpoint.

    Covers hosted free tiers such as Groq, Google AI Studio, OpenRouter, and
    Cerebras, which all expose OpenAI-compatible APIs.

    Args:
        name: Model name as the endpoint knows it.
        base_url: Base URL of the endpoint.
        api_key_env: Name of the environment variable holding the API key.

    Returns:
        A model that talks to the endpoint.
    """
    client = AsyncOpenAI(
        base_url=base_url, api_key=os.environ[api_key_env], max_retries=MAX_RETRIES
    )
    return OpenAIChatModel(name, provider=OpenAIProvider(openai_client=client))


def resolve_model(name: str, base_url: str, api_key_env: str) -> AbstractModel:
    """Create a model from endpoint settings.

    Names prefixed with ``anthropic:`` go to the Anthropic API using the
    ``ANTHROPIC_API_KEY`` environment variable; other names go to the
    OpenAI-compatible endpoint at ``base_url``, or to local Ollama when
    ``base_url`` is empty.

    Args:
        name: Model name, optionally prefixed with a provider.
        base_url: Base URL of an OpenAI-compatible endpoint, or empty for local Ollama.
        api_key_env: Name of the environment variable holding the endpoint's API key.

    Returns:
        The model.
    """
    if name.startswith("anthropic:"):
        return AnthropicModel(name.removeprefix("anthropic:"))
    if base_url:
        return openai_compatible_model(name, base_url, api_key_env)
    return ollama_model(name)


def list_model_names(base_url: str, api_key_env: str) -> list[str]:
    """List the model names served by an OpenAI-compatible endpoint.

    Args:
        base_url: Base URL of the endpoint.
        api_key_env: Name of the environment variable holding the API key.

    Returns:
        Model names in sorted order.
    """
    client = OpenAI(base_url=base_url, api_key=os.environ[api_key_env])
    return sorted(model.id for model in client.models.list())
