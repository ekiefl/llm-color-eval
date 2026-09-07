from pydantic import BaseModel, Field, field_validator

HEX_PATTERN = r"^#[0-9a-fA-F]{6}$"


class ColorSample(BaseModel):
    """A color in the evaluation dataset, identified by its hex code."""

    hex_code: str = Field(pattern=HEX_PATTERN)

    @field_validator("hex_code")
    @classmethod
    def lowercase(cls, value: str) -> str:
        """Normalize the hex code to lowercase.

        Args:
            value: The validated hex code.

        Returns:
            The hex code in lowercase.
        """
        return value.lower()


class Guess(BaseModel):
    """The guesser's reconstruction of a color it has never seen."""

    hex_code: str = Field(pattern=HEX_PATTERN)

    @field_validator("hex_code")
    @classmethod
    def lowercase(cls, value: str) -> str:
        """Normalize the hex code to lowercase.

        Args:
            value: The validated hex code.

        Returns:
            The hex code in lowercase.
        """
        return value.lower()


class TrialResult(BaseModel):
    """The outcome of one color's trip through the describe-then-guess loop."""

    hex_code: str
    description: str
    guessed_hex_code: str
    score: float
    delta_e: float
