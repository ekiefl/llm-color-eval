# color-guesser

An evaluation harness for a two-agent color communication game:

1. A **describer** agent is given a hex code and must describe the color in
   natural language, without leaking hex codes, RGB values, or any other
   numeric encoding.
2. A **guesser** agent, which never sees the hex code, must reconstruct the
   color from the description alone.

The round trip is scored with two metrics, no human labels needed:

- **Score (primary)**: the 0-10 similarity formula reverse-engineered from
  the [dialed.gg color game](https://dialed.gg/color) — CIEDE2000 squashed
  through `10 / (1 + (dE / 25.25) ** 1.55)`, plus a saturation-gated bonus
  for close hues and penalty for distant hues. The game's deterministic
  score jitter is omitted. Ten is a perfect match.
- **Delta E (secondary)**: the raw CIEDE2000 perceptual distance.

## Layout

- `sampler.py` — draws hex codes from RGB or HLS space to build datasets
- `describer.py` — the hex-to-description agent, with an output validator that rejects encoding leaks
- `guesser.py` — the description-to-hex agent, with structured output
- `metrics.py` — the dialed.gg similarity score (primary) and CIEDE2000 (secondary)
- `models.py` — Pydantic records shared across modules
- `llm.py` — model factories for local Ollama and any OpenAI-compatible endpoint
- `db.py` — SQLite storage: `descriptions` (color, describer, word budget, text) and `guesses` (guesser, guessed hex, delta E), one description to many guesses
- `runner.py` — concurrent batch runner that records every trial as it completes
- `cli.py` — the `color-guesser` command line interface
- `app.py` — Streamlit app for single trials with a visual comparison

An API key is read from `.env` (e.g. `GROQ_KEY=...`), which is loaded
automatically by the CLI and the app.

## Usage

Generate datasets:

```sh
uv run color-guesser generate-uniform --n 100 --output data/uniform.jsonl
uv run color-guesser generate-stratified --hue-steps 12 --output data/stratified.jsonl
```

Run a single color through the describe-then-guess loop (defaults to Groq's
`openai/gpt-oss-20b` with the key in `GROQ_KEY`):

```sh
uv run color-guesser roundtrip "#3fa76e"
```

Run a whole dataset and record every trial in SQLite:

```sh
uv run color-guesser run-batch data/stratified.jsonl \
    --describer openai/gpt-oss-20b \
    --guesser qwen/qwen3.8-27b \
    --max-words 30 \
    --db-path data/results.db
```

Launch the visual app:

```sh
uv run streamlit run src/color_guesser/app.py
```

## Web widget

`docs/` holds a self-contained browser game: read a real AI-written color
description, dial in your guess with HSB sliders, and see how you score
against the models that guessed from the same words. No backend and no API
calls; the AI answers are precomputed trials exported from the results
database:

```sh
uv run color-guesser export-widget --db-path data/scan72.db --n 90
```

Serve it locally with `python3 -m http.server --directory docs`, or enable
GitHub Pages (Settings, Pages, deploy from branch, `/docs` folder) and embed
it anywhere with:

```html
<iframe src="https://ekiefl.github.io/llm-color-eval/" width="100%" height="680"
        style="border:none"></iframe>
```

To use a different OpenAI-compatible endpoint, pass `--base-url` and
`--api-key-env`; an empty `--base-url` targets local Ollama instead.
