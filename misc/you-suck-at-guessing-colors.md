# You suck at guessing colors. LLMs don't.

<!-- Alt titles:
  - Color me surprised: LLMs beat you at your favorite color game
  - I lost a color game to a 20B parameter language model
  - The telephone game, but for colors
-->

> TODO: hook. One or two sentences about playing dialed.gg/color with friends and
> being reliably terrible. The screenshot where the game called your 5.55 "the
> score equivalent of elevator music" belongs here.

## The game

- dialed.gg/color: see a color for a few seconds, recreate it from memory with
  hue / saturation / brightness sliders, scored 0-10 across 5 rounds.
- TODO: your personal stats, your friends' scores, the group chat trash talk.
- The nagging question: is this hard because color memory is hard, or because
  *translating color into anything else* is hard?

## The idea: a telephone game for machines

- Two agents. A **describer** sees a hex code and must describe the color in
  plain English -- no hex codes, no RGB, no numbers allowed (a validator
  rejects and retries any leak). A **guesser** that has never seen the hex
  reconstructs the color from the description alone.
- Round trip quality is measured with a perceptual color distance, so the eval
  scores itself: no human labels anywhere.
- Built with Pydantic AI (structured outputs, output validators with automatic
  retry), SQLite for trials, a tiny Streamlit app for playing with it, and a
  word-budget knob on the describer (the compression parameter).
- TODO: link the repo. Maybe include the comparison-square screenshot from the
  app (source color top-left triangle, guess bottom-right).

## Reverse-engineering the game's scoring formula

<!-- This is the detective story section. Beats to hit: -->

- Wanted the eval scored in the game's own currency, so I fed pairs of colors
  and game scores to Claude and asked it to reverse-engineer the metric.
- The blind search: 100+ candidate metrics (CIEDE2000, CAM16, OKLab, redmean,
  HSB cones...) x transform families. Best fits kept converging on
  `10 / (1 + (deltaE2000 / k) ^ p)` but *never exactly* -- an irreducible
  ~0.05 error floor no formula could cross.
- The twist: the actual formula (dug out of the site's minified JS) is
  CIEDE2000 squashed through `10 / (1 + (dE / 25.25) ^ 1.55)`, plus a
  hand-tuned hue bonus/penalty gated by saturation... plus a deliberate
  **hash-seeded jitter of +/-0.04** so scores feel organic. The noise floor
  was engineered in. No curve fitter could ever have closed the gap.
- Verified: reimplementation matches the game's JS on every test pair.
- The eval now uses this exact formula (minus jitter) as its primary metric.
- TODO: your telling of watching the search almost-converge, and the reveal.

## Results

### Small models are already better than you

- gpt-oss-20b (a 20B open model on Groq's free tier), given only **5 words**
  per description, averages **7.81 / 10** over 216 trials.
- TODO: human baseline! Collect your + friends' dialed.gg scores for the
  comparison table. The title's claim needs this data. (n >= 3 humans x 5
  rounds would do.)
- Caveat to be honest about: the game tests color *memory* under time
  pressure; the eval tests color *communication*. Related skills, not the
  same game. TODO: decide how hard to lean on the comparison.

### The word budget barely matters

| budget (words) | gpt-oss-20b | Sonnet 5 | Sonnet actually used |
|---:|---:|---:|---:|
| 5  | 7.81 | 8.48 | 4.4 words |
| 15 | 8.11 | 8.56 | 11.9 words |
| 30 | TODO | 8.62 | 24.2 words |

- n = 216 trials per cell (72 colors x 3 replicates), SE ~ 0.07.
- Sonnet 5 packs nearly everything into ~4 words; 6x more budget buys +0.14.
- Color identity apparently lives in the first few words ("muted lavender,
  pink undertones"); everything after is garnish.

### Where the model gap lives: describing vs guessing

| describer -> guesser | budget 5 | budget 15 |
|---|---:|---:|
| gpt-oss -> gpt-oss | 7.81 | 8.11 |
| gpt-oss -> Sonnet 5 | 8.20 | 8.43 |
| Sonnet 5 -> Sonnet 5 | 8.48 | 8.56 |

- Crossover trick: the same stored descriptions, guessed by both models --
  paired statistics, very tight error bars.
- ~60-70% of the gap is **guessing skill** (words -> hex), and that deficit is
  stable. The describing deficit shrinks as the budget grows: given room, the
  small model says enough; it just can't *read* as precisely.
- TODO: fourth cell (Sonnet descriptions -> gpt-oss guesser) pending free-tier
  quota.

### Some colors are just hard

- Hardest (mean over 9 trials, Sonnet): `#40552b` dark olive (5.21!),
  `#d4d42b` chartreuse, `#aa5580` mauve -- the regions where English color
  vocabulary is genuinely poor.
- Easiest: cyans and deep blues (`#2bd4d4`: 9.75). "Bright cyan" is
  unambiguous.
- Replicate variance says difficulty is a stable property of the color, not
  sampling luck (within-color std ~0.5 vs between-color ~0.9).
- Both models fail on the *same* colors. TODO: maybe a difficulty-map figure
  (72 swatches colored by mean score).

## What's next

- A live site where you play the same describe-and-guess game against the
  AI -- same descriptions, same scoring -- and see where you land. TODO: link
  when it exists; every visitor round doubles as human baseline data.
- Full describer x guesser matrix across more models (the harness makes any
  OpenAI-compatible endpoint or Anthropic model a one-flag swap).
- TODO: your wishlist.

---

<!-- Facts checked against the experiment DBs, 2026-09-06. Pending: gpt-oss
budget-30 tier (ETA Sept 8), fourth matrix cell, human baseline. -->
