import re

from pydantic_ai import Agent, ModelRetry
from pydantic_ai.models import AbstractModel

INSTRUCTIONS_TEMPLATE = (
    "You will be given a color as a hex code. Describe the color in natural"
    " language so that someone who cannot see it can reproduce it as closely as"
    " possible. Use at most {max_words} words. Never reveal the hex code, RGB"
    " or HSL values, or any other numeric encoding of the color. Do not use"
    " digit characters anywhere; spell any quantity out in words."
)

ENCODING_LEAK = re.compile(r"[0-9#%]")


def word_count(text: str) -> int:
    """Count whitespace-delimited words.

    Args:
        text: The text to count words in.

    Returns:
        The number of words.
    """
    return len(text.split())


def build_describer(model: AbstractModel, max_words: int) -> Agent[None, str]:
    """Build the agent that turns a hex code into a natural language description.

    The agent's output is validated to contain no digits, hash signs, or
    percent signs, so a description cannot smuggle the hex code or any other
    numeric encoding to the guesser. The output must also fit within the word
    budget, which makes the budget a scannable parameter of the eval.

    Args:
        model: The model the agent runs on.
        max_words: Maximum number of whitespace-delimited words in the description.

    Returns:
        An agent that maps a hex code prompt to a description.
    """
    agent = Agent(
        model, instructions=INSTRUCTIONS_TEMPLATE.format(max_words=max_words), retries=6
    )

    @agent.output_validator
    def validate(output: str) -> str:
        if ENCODING_LEAK.search(output):
            raise ModelRetry(
                "The description must not contain digits, '#', or '%'."
                " Describe the color in words only."
            )
        if word_count(output) > max_words:
            raise ModelRetry(
                f"The description has {word_count(output)} words but the limit"
                f" is {max_words}. Shorten it."
            )
        return output

    return agent
