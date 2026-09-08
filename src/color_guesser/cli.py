import asyncio
import json
import random
import statistics
from pathlib import Path

import typer
from dotenv import load_dotenv

from color_guesser.db import connect
from color_guesser.describer import build_describer
from color_guesser.guesser import build_guesser
from color_guesser.llm import GROQ_BASE_URL, resolve_model
from color_guesser.metrics import delta_e, dialed_score
from color_guesser.models import ColorSample
from color_guesser.runner import guess_batch
from color_guesser.runner import run_batch as run_batch_async
from color_guesser.sampler import sample_halton, sample_stratified, sample_uniform

load_dotenv()

app = typer.Typer(no_args_is_help=True)


def write_dataset(hex_codes: list[str], output: Path) -> None:
    """Write hex codes to a JSONL dataset file.

    Args:
        hex_codes: The colors to write.
        output: Path of the JSONL file to write.
    """
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open("w") as f:
        for hex_code in hex_codes:
            f.write(ColorSample(hex_code=hex_code).model_dump_json() + "\n")
    typer.echo(f"Wrote {len(hex_codes)} colors to {output}")


def read_dataset(dataset: Path) -> list[str]:
    """Read hex codes from a JSONL dataset file.

    Args:
        dataset: Path of a JSONL file written by the generate commands.

    Returns:
        The hex codes in file order.
    """
    return [
        ColorSample.model_validate_json(line).hex_code
        for line in dataset.read_text().splitlines()
    ]


@app.command()
def generate_uniform(
    n: int = 100, seed: int = 0, output: Path = Path("data/uniform.jsonl")
) -> None:
    """Generate a dataset of hex codes sampled uniformly from RGB space.

    Args:
        n: Number of colors to sample.
        seed: Seed for the random number generator.
        output: Path of the JSONL file to write.
    """
    write_dataset(sample_uniform(n, seed), output)


@app.command()
def generate_stratified(
    hue_steps: int = 12,
    lightness_steps: int = 4,
    saturation_steps: int = 3,
    output: Path = Path("data/stratified.jsonl"),
) -> None:
    """Generate a dataset of hex codes on an evenly spaced HLS grid.

    Args:
        hue_steps: Number of evenly spaced hues.
        lightness_steps: Number of evenly spaced lightness levels.
        saturation_steps: Number of evenly spaced saturation levels.
        output: Path of the JSONL file to write.
    """
    write_dataset(sample_stratified(hue_steps, lightness_steps, saturation_steps), output)


@app.command()
def generate_halton(n: int = 1000, output: Path = Path("data/halton.jsonl")) -> None:
    """Generate a dataset evenly spread across the HSB slider space.

    The sample is prefix-stable: regenerating with a larger n keeps the
    first colors identical, so existing trials on them stay valid.

    Args:
        n: Number of colors to sample.
        output: Path of the JSONL file to write.
    """
    write_dataset(sample_halton(n), output)


@app.command()
def run_replicates(
    dataset: Path,
    replicates: int = 3,
    describer: str = "anthropic:claude-sonnet-5",
    guesser: str = "anthropic:claude-sonnet-5",
    max_words: int = 5,
    seed: int = 0,
    effort: str = "",
    base_url: str = GROQ_BASE_URL,
    api_key_env: str = "GROQ_KEY",
    db_path: Path = Path("data/results.db"),
    concurrency: int = 3,
    pace: float = 2.5,
) -> None:
    """Top up every dataset color to a target replicate count.

    Existing trials per color for this describer and word budget are counted
    and only the missing replicates run, so the command is idempotent:
    re-running after a crash, or after growing the dataset, does only the
    remaining work.

    Args:
        dataset: JSONL dataset of colors, as written by the generate commands.
        replicates: Target number of trials per color.
        describer: Model that writes the descriptions.
        guesser: Model that guesses colors from the descriptions.
        max_words: Word budget for descriptions.
        seed: Sampling seed for every call.
        effort: Reasoning effort for every call; empty leaves the endpoint's default.
        base_url: Base URL of an OpenAI-compatible endpoint; empty means local Ollama.
        api_key_env: Name of the environment variable holding the endpoint's API key.
        db_path: Path of the SQLite database trials are recorded in.
        concurrency: Maximum number of colors in flight at once.
        pace: Seconds between trial starts, for staying below per-minute rate limits.
    """
    hex_codes = list(dict.fromkeys(read_dataset(dataset)))
    conn = connect(db_path)
    existing = dict(
        conn.execute(
            "SELECT hex_code, count(*) FROM descriptions"
            " WHERE describer = ? AND max_words = ? GROUP BY hex_code",
            (describer, max_words),
        ).fetchall()
    )
    work = []
    for hex_code in hex_codes:
        work.extend([hex_code] * max(0, replicates - existing.get(hex_code, 0)))
    typer.echo(f"colors: {len(hex_codes)}, trials to run: {len(work)}")
    if not work:
        conn.close()
        return
    describer_agent = build_describer(resolve_model(describer, base_url, api_key_env), max_words)
    guesser_agent = build_guesser(resolve_model(guesser, base_url, api_key_env))
    results = asyncio.run(
        run_batch_async(
            conn,
            describer_agent,
            guesser_agent,
            describer,
            guesser,
            work,
            max_words,
            seed,
            effort,
            concurrency,
            pace,
        )
    )
    conn.close()
    echo_summary(results)


@app.command()
def roundtrip(
    hex_code: str,
    model: str = "openai/gpt-oss-20b",
    max_words: int = 30,
    base_url: str = GROQ_BASE_URL,
    api_key_env: str = "GROQ_KEY",
) -> None:
    """Run a single color through the describe-then-guess loop.

    Args:
        hex_code: The color to test, as a ``#rrggbb`` hex code.
        model: Model name, as the endpoint knows it.
        max_words: Word budget for the description.
        base_url: Base URL of an OpenAI-compatible endpoint; empty means local Ollama.
        api_key_env: Name of the environment variable holding the endpoint's API key.
    """
    sample = ColorSample(hex_code=hex_code)
    llm = resolve_model(model, base_url, api_key_env)
    describer = build_describer(llm, max_words)
    guesser = build_guesser(llm)
    description = describer.run_sync(sample.hex_code).output
    guess = guesser.run_sync(description).output
    typer.echo(f"color:       {sample.hex_code}")
    typer.echo(f"description: {description}")
    typer.echo(f"guess:       {guess.hex_code}")
    typer.echo(f"score:       {dialed_score(sample.hex_code, guess.hex_code):.2f} / 10")
    typer.echo(f"delta E:     {delta_e(sample.hex_code, guess.hex_code):.2f}")


@app.command()
def run_batch(
    dataset: Path,
    describer: str = "openai/gpt-oss-20b",
    guesser: str = "openai/gpt-oss-20b",
    max_words: int = 30,
    seed: int = 0,
    effort: str = "",
    base_url: str = GROQ_BASE_URL,
    api_key_env: str = "GROQ_KEY",
    db_path: Path = Path("data/results.db"),
    concurrency: int = 4,
    pace: float = 0.0,
) -> None:
    """Run every color in a dataset through the loop and record the trials.

    Args:
        dataset: JSONL dataset of colors, as written by the generate commands.
        describer: Model that writes the descriptions.
        guesser: Model that guesses colors from the descriptions.
        max_words: Word budget for descriptions.
        seed: Sampling seed, so replicate batches can differ yet be reproduced.
        effort: Reasoning effort for every model call; empty leaves the endpoint's default.
        base_url: Base URL of an OpenAI-compatible endpoint; empty means local Ollama.
        api_key_env: Name of the environment variable holding the endpoint's API key.
        db_path: Path of the SQLite database trials are recorded in.
        concurrency: Maximum number of colors in flight at once.
        pace: Seconds between trial starts, for staying below per-minute rate limits.
    """
    hex_codes = read_dataset(dataset)
    describer_agent = build_describer(resolve_model(describer, base_url, api_key_env), max_words)
    guesser_agent = build_guesser(resolve_model(guesser, base_url, api_key_env))
    conn = connect(db_path)
    results = asyncio.run(
        run_batch_async(
            conn,
            describer_agent,
            guesser_agent,
            describer,
            guesser,
            hex_codes,
            max_words,
            seed,
            effort,
            concurrency,
            pace,
        )
    )
    conn.close()
    echo_summary(results)


def echo_summary(results: list) -> None:
    """Print score and delta E summary statistics for a batch of trials.

    Args:
        results: The batch's trial results.
    """
    scores = [result.score for result in results]
    deltas = [result.delta_e for result in results]
    worst = min(results, key=lambda result: result.score)
    typer.echo(f"trials:         {len(results)}")
    typer.echo(f"mean score:     {statistics.mean(scores):.2f} / 10")
    typer.echo(f"median score:   {statistics.median(scores):.2f} / 10")
    typer.echo(f"mean delta E:   {statistics.mean(deltas):.2f}")
    typer.echo(f"median delta E: {statistics.median(deltas):.2f}")
    typer.echo(
        f"worst:          {worst.hex_code} -> {worst.guessed_hex_code}"
        f" ({worst.score:.2f}, delta E {worst.delta_e:.2f})"
    )


@app.command()
def export_widget(
    db_path: Path = Path("data/halton_sonnet.db"),
    n: int = 150,
    output: Path = Path("docs/trials.json"),
) -> None:
    """Export a balanced sample of trials for the web widget.

    Each exported trial is one described-and-guessed color. The sample is
    spread evenly across the difficulty range, with each color appearing at
    most once, and written as JSON for the GitHub Pages game.

    Args:
        db_path: Path of the SQLite database holding descriptions and guesses.
        n: Number of trials to export.
        output: Path of the JSON file to write.
    """
    conn = connect(db_path)
    rows = conn.execute(
        "SELECT d.id, d.hex_code, d.text, d.max_words, d.describer FROM descriptions d"
        " WHERE EXISTS (SELECT 1 FROM guesses g WHERE g.description_id = d.id) ORDER BY d.id"
    ).fetchall()
    trials = []
    for description_id, hex_code, text, max_words, describer in rows:
        guesses = {
            guesser: {"hex": guess_hex, "score": score}
            for guesser, guess_hex, score in conn.execute(
                "SELECT guesser, hex_code, score FROM guesses WHERE description_id = ?",
                (description_id,),
            )
        }
        trials.append(
            {
                "hex": hex_code,
                "description": text,
                "budget": max_words,
                "describer": describer,
                "guesses": guesses,
            }
        )
    conn.close()
    seen = set()
    unique = []
    for trial in trials:
        if trial["hex"] not in seen:
            seen.add(trial["hex"])
            unique.append(trial)
    sampled = random.Random(0).sample(unique, min(n, len(unique)))
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(sampled, indent=1))
    typer.echo(f"Wrote {len(sampled)} trials to {output}")


@app.command()
def guess_existing(
    db_path: Path,
    guesser: str = "anthropic:claude-sonnet-5",
    seed: int = 0,
    effort: str = "",
    base_url: str = GROQ_BASE_URL,
    api_key_env: str = "GROQ_KEY",
    concurrency: int = 3,
    pace: float = 2.0,
) -> None:
    """Run a guesser over descriptions already stored in a results database.

    Descriptions that already have a guess from this guesser are skipped, so
    the command is safe to re-run as new descriptions accumulate.

    Args:
        db_path: Path of the SQLite database holding the descriptions.
        guesser: Model that guesses colors from the stored descriptions.
        seed: Sampling seed for every call.
        effort: Reasoning effort for every call; empty leaves the endpoint's default.
        base_url: Base URL of an OpenAI-compatible endpoint; empty means local Ollama.
        api_key_env: Name of the environment variable holding the endpoint's API key.
        concurrency: Maximum number of guesses in flight at once.
        pace: Seconds between call starts, for staying below per-minute rate limits.
    """
    conn = connect(db_path)
    rows = conn.execute(
        "SELECT d.id, d.hex_code, d.text FROM descriptions d"
        " WHERE NOT EXISTS ("
        "   SELECT 1 FROM guesses g WHERE g.description_id = d.id AND g.guesser = ?"
        " ) ORDER BY d.id",
        (guesser,),
    ).fetchall()
    typer.echo(f"descriptions to guess: {len(rows)}")
    guesser_agent = build_guesser(resolve_model(guesser, base_url, api_key_env))
    results = asyncio.run(
        guess_batch(conn, guesser_agent, guesser, rows, seed, effort, concurrency, pace)
    )
    conn.close()
    echo_summary(results)
