import re

from pydantic_ai import Agent, ModelRetry, TextOutput
from pydantic_ai.models import AbstractModel

from color_guesser.models import Guess

INSTRUCTIONS = (
    "You will be given a natural language description of a color. Guess the"
    " color being described and reply with its hex code, like #3fa76e."
)

HASHED_HEX = re.compile(r"#[0-9a-fA-F]{6}\b")
BARE_HEX = re.compile(r"\b[0-9a-fA-F]{6}\b")


def extract_guess(text: str) -> Guess:
    """Pull the guessed hex code out of a model's free-form reply.

    The last hex code in the text is taken as the final answer, preferring
    codes written with a leading hash so prose that happens to contain six
    hex-alphabet letters does not shadow an explicit code.

    Args:
        text: The model's reply.

    Returns:
        The guess.

    Raises:
        ModelRetry: If the text contains no hex code.
    """
    hashed = HASHED_HEX.findall(text)
    if hashed:
        return Guess(hex_code=hashed[-1])
    bare = BARE_HEX.findall(text)
    if bare:
        return Guess(hex_code=f"#{bare[-1]}")
    raise ModelRetry("Reply with a six digit hex color code, like #3fa76e.")


def build_guesser(model: AbstractModel) -> Agent[None, Guess]:
    """Build the agent that turns a description back into a hex code.

    The guess is extracted from plain text rather than tool-called or parsed
    as JSON, so the guesser works on any text model and every model guesses
    through the same mechanism.

    Args:
        model: The model the agent runs on.

    Returns:
        An agent that maps a description to a hex code guess.
    """
    return Agent(model, instructions=INSTRUCTIONS, output_type=TextOutput(extract_guess), retries=3)
