import asyncio
import sqlite3

from pydantic_ai import Agent
from pydantic_ai.models.openai import OpenAIChatModelSettings
from pydantic_ai.settings import ModelSettings

from color_guesser.db import insert_description, insert_guess
from color_guesser.metrics import delta_e, dialed_score
from color_guesser.models import Guess, TrialResult


def _settings(seed: int, effort: str) -> ModelSettings:
    """Build model settings for a batch's calls.

    Args:
        seed: Sampling seed.
        effort: Reasoning effort; empty leaves the endpoint's default in place.

    Returns:
        The settings.
    """
    if effort:
        return OpenAIChatModelSettings(seed=seed, openai_reasoning_effort=effort)
    return ModelSettings(seed=seed)


async def run_trial(
    describer: Agent[None, str],
    guesser: Agent[None, Guess],
    hex_code: str,
    seed: int,
    effort: str,
) -> TrialResult:
    """Run one color through the describe-then-guess loop.

    Args:
        describer: The describing agent.
        guesser: The guessing agent.
        hex_code: The color to test.
        seed: Sampling seed passed to both model calls, so replicates of the
            same color can be varied yet reproduced.
        effort: Reasoning effort for both model calls; empty leaves the
            endpoint's default in place.

    Returns:
        The trial outcome.
    """
    settings = _settings(seed, effort)
    description = (await describer.run(hex_code, model_settings=settings)).output
    guess = (await guesser.run(description, model_settings=settings)).output
    return TrialResult(
        hex_code=hex_code,
        description=description,
        guessed_hex_code=guess.hex_code,
        score=dialed_score(hex_code, guess.hex_code),
        delta_e=delta_e(hex_code, guess.hex_code),
    )


async def run_batch(
    conn: sqlite3.Connection,
    describer: Agent[None, str],
    guesser: Agent[None, Guess],
    describer_name: str,
    guesser_name: str,
    hex_codes: list[str],
    max_words: int,
    seed: int,
    effort: str,
    concurrency: int,
    pace: float,
) -> list[TrialResult]:
    """Run many colors through the loop concurrently, recording every trial.

    Each completed trial is written to the database as it finishes, so a run
    that dies partway through keeps its finished trials.

    Args:
        conn: Open results database connection.
        describer: The describing agent.
        guesser: The guessing agent.
        describer_name: Name of the describing model, recorded with each description.
        guesser_name: Name of the guessing model, recorded with each guess.
        hex_codes: The colors to test.
        max_words: Word budget the describer was built with, recorded with each description.
        seed: Sampling seed for every trial in the batch.
        effort: Reasoning effort for every model call; empty leaves the endpoint's default.
        concurrency: Maximum number of colors in flight at once.
        pace: Seconds between trial starts, throttling the batch below
            per-minute rate limits; zero starts trials as fast as concurrency allows.

    Returns:
        One result per color, in dataset order.
    """
    semaphore = asyncio.Semaphore(concurrency)

    async def bounded(index: int, hex_code: str) -> TrialResult:
        await asyncio.sleep(index * pace)
        async with semaphore:
            result = await run_trial(describer, guesser, hex_code, seed, effort)
        description_id = insert_description(
            conn, hex_code, describer_name, max_words, result.description
        )
        insert_guess(
            conn,
            description_id,
            guesser_name,
            result.guessed_hex_code,
            result.score,
            result.delta_e,
        )
        return result

    return list(
        await asyncio.gather(*(bounded(i, hex_code) for i, hex_code in enumerate(hex_codes)))
    )


async def guess_batch(
    conn: sqlite3.Connection,
    guesser: Agent[None, Guess],
    guesser_name: str,
    descriptions: list[tuple[int, str, str]],
    seed: int,
    effort: str,
    concurrency: int,
    pace: float,
) -> list[TrialResult]:
    """Run a guesser over stored descriptions, recording every guess.

    This is the crossover path: descriptions written by one model can be
    guessed by another without re-describing.

    Args:
        conn: Open results database connection.
        guesser: The guessing agent.
        guesser_name: Name of the guessing model, recorded with each guess.
        descriptions: Rows of description id, source hex code, and description text.
        seed: Sampling seed for every call.
        effort: Reasoning effort for every call; empty leaves the endpoint's default.
        concurrency: Maximum number of guesses in flight at once.
        pace: Seconds between call starts, for staying below per-minute rate limits.

    Returns:
        One result per description, in input order.
    """
    semaphore = asyncio.Semaphore(concurrency)
    settings = _settings(seed, effort)

    async def bounded(index: int, description_id: int, hex_code: str, text: str) -> TrialResult:
        await asyncio.sleep(index * pace)
        async with semaphore:
            guess = (await guesser.run(text, model_settings=settings)).output
        result = TrialResult(
            hex_code=hex_code,
            description=text,
            guessed_hex_code=guess.hex_code,
            score=dialed_score(hex_code, guess.hex_code),
            delta_e=delta_e(hex_code, guess.hex_code),
        )
        insert_guess(
            conn, description_id, guesser_name, result.guessed_hex_code, result.score, result.delta_e
        )
        return result

    return list(
        await asyncio.gather(*(bounded(i, *row) for i, row in enumerate(descriptions)))
    )
