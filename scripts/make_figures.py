import colorsys
import html
import sqlite3
import statistics
import textwrap
from pathlib import Path

import typer

app = typer.Typer(no_args_is_help=True)

INK = "#0b0b0b"
INK_2 = "#52514e"
GRID = "#e8e8e6"
EDGE = "#d5d4d0"
SONNET = "#2a78d6"
GPTOSS = "#eb6834"
FONT = "system-ui, -apple-system, sans-serif"


def svg_text(x: float, y: float, s: str, size: int, fill: str, anchor: str, weight: str) -> str:
    """Render one SVG text element.

    Args:
        x: X coordinate.
        y: Y coordinate.
        s: The text.
        size: Font size in pixels.
        fill: Text color.
        anchor: SVG text-anchor value.
        weight: SVG font-weight value.

    Returns:
        The SVG fragment.
    """
    return (
        f'<text x="{x}" y="{y}" font-family="{FONT}" font-size="{size}" fill="{fill}"'
        f' text-anchor="{anchor}" font-weight="{weight}">{s}</text>'
    )


def budget_stats(db_path: Path, guesser: str) -> dict[int, tuple[float, float]]:
    """Compute mean score and standard error per completed budget tier.

    Args:
        db_path: Path of the results database.
        guesser: Name of the guesser whose scores are aggregated.

    Returns:
        Mapping of word budget to mean score and standard error.
    """
    conn = sqlite3.connect(db_path)
    rows = conn.execute(
        "SELECT d.max_words, g.score FROM guesses g"
        " JOIN descriptions d ON g.description_id = d.id WHERE g.guesser = ?"
        " ORDER BY g.id",
        (guesser,),
    ).fetchall()
    conn.close()
    by_budget: dict[int, list[float]] = {}
    for budget, score in rows:
        by_budget.setdefault(budget, []).append(score)
    stats = {}
    for budget, scores in by_budget.items():
        complete = scores[: len(scores) // 72 * 72]
        if complete:
            stats[budget] = (
                statistics.mean(complete),
                statistics.stdev(complete) / len(complete) ** 0.5,
            )
    return stats


def color_difficulty(db_path: Path) -> list[tuple[str, float]]:
    """Rank colors by how well they survive the describe-then-guess loop.

    Args:
        db_path: Path of the results database.

    Returns:
        Hex codes with mean scores, easiest first.
    """
    conn = sqlite3.connect(db_path)
    rows = conn.execute(
        "SELECT d.hex_code, avg(g.score) FROM guesses g"
        " JOIN descriptions d ON g.description_id = d.id GROUP BY d.hex_code"
    ).fetchall()
    conn.close()
    return sorted(rows, key=lambda row: -row[1])


def pipeline_svg() -> str:
    """Draw the describe-then-guess pipeline diagram in a two-row layout.

    Returns:
        The SVG document.
    """
    parts = [
        '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 640 460" font-family="sans-serif">',
        '<rect width="640" height="460" fill="#ffffff"/>',
        '<defs><marker id="arr" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7"'
        ' markerHeight="7" orient="auto-start-reverse">'
        f'<path d="M 0 0 L 10 5 L 0 10 z" fill="{INK_2}"/></marker></defs>',
    ]
    parts.append('<rect x="24" y="62" width="88" height="88" rx="14" fill="#3fa76e"/>')
    parts.append(svg_text(68, 174, "#3fa76e", 17, INK_2, "middle", "400"))
    parts.append(svg_text(68, 46, "the color", 17, INK_2, "middle", "400"))
    parts.append(f'<line x1="120" y1="106" x2="158" y2="106" stroke="{INK_2}" stroke-width="2.5" marker-end="url(#arr)"/>')
    parts.append(f'<rect x="162" y="70" width="152" height="72" rx="12" fill="#ffffff" stroke="{EDGE}" stroke-width="1.5"/>')
    parts.append(svg_text(238, 100, "describer", 21, INK, "middle", "600"))
    parts.append(svg_text(238, 126, "(LLM)", 16, INK_2, "middle", "400"))
    parts.append(f'<line x1="322" y1="106" x2="360" y2="106" stroke="{INK_2}" stroke-width="2.5" marker-end="url(#arr)"/>')
    parts.append(f'<rect x="364" y="48" width="252" height="120" rx="12" fill="#ffffff" stroke="{EDGE}" stroke-width="1.5"/>')
    parts.append(svg_text(490, 84, "“medium-toned, fresh", 17, INK, "middle", "400"))
    parts.append(svg_text(490, 108, "grass-green with a slight", 17, INK, "middle", "400"))
    parts.append(svg_text(490, 132, "blue undertone…”", 17, INK, "middle", "400"))
    parts.append(svg_text(490, 158, "no hex, no RGB, no numbers", 14, INK_2, "middle", "400"))
    parts.append(f'<line x1="24" y1="230" x2="616" y2="230" stroke="{INK_2}" stroke-width="1.5" stroke-dasharray="6 6"/>')
    parts.append(svg_text(24, 216, "sees the color", 15, INK_2, "start", "400"))
    parts.append(svg_text(24, 254, "never sees the color", 15, INK_2, "start", "400"))
    parts.append(
        f'<path d="M 490 172 L 490 336 L 476 336" fill="none" stroke="{INK_2}"'
        ' stroke-width="2.5" marker-end="url(#arr)"/>'
    )
    parts.append(f'<rect x="320" y="300" width="152" height="72" rx="12" fill="#ffffff" stroke="{EDGE}" stroke-width="1.5"/>')
    parts.append(svg_text(396, 330, "guesser", 21, INK, "middle", "600"))
    parts.append(svg_text(396, 356, "(LLM)", 16, INK_2, "middle", "400"))
    parts.append(f'<line x1="316" y1="336" x2="278" y2="336" stroke="{INK_2}" stroke-width="2.5" marker-end="url(#arr)"/>')
    parts.append('<rect x="182" y="292" width="88" height="88" rx="14" fill="#4a9e6a"/>')
    parts.append(svg_text(226, 404, "#4a9e6a", 17, INK_2, "middle", "400"))
    parts.append(svg_text(226, 276, "the guess", 17, INK_2, "middle", "400"))
    parts.append("</svg>")
    return "".join(parts)

def example_rows(db_path: Path, hex_code: str) -> list[tuple[int, float, str]]:
    """Fetch one representative description of a color per word budget.

    The median-scoring replicate is chosen for each budget.

    Args:
        db_path: Path of the results database.
        hex_code: The example color.

    Returns:
        Budget, score, and description text per budget, smallest budget first.
    """
    conn = sqlite3.connect(db_path)
    budgets = [
        r[0]
        for r in conn.execute(
            "SELECT DISTINCT max_words FROM descriptions WHERE hex_code = ? ORDER BY max_words",
            (hex_code,),
        )
    ]
    rows = []
    for budget in budgets:
        trials = conn.execute(
            "SELECT g.score, d.text FROM guesses g JOIN descriptions d ON g.description_id = d.id"
            " WHERE d.hex_code = ? AND d.max_words = ? ORDER BY g.score",
            (hex_code, budget),
        ).fetchall()
        score, text = trials[len(trials) // 2]
        rows.append((budget, score, text))
    conn.close()
    return rows


def budget_curve_svg(
    series: dict[str, tuple[str, dict[int, tuple[float, float]]]],
    examples: list[tuple[int, float, str]],
    example_hex: str,
) -> str:
    """Draw the score versus budget chart with example prose per budget below.

    Args:
        series: Mapping of series label to its color and per-budget stats.
        examples: Budget, score, and description text rows for the example color.
        example_hex: The example color the prose describes.

    Returns:
        The SVG document.
    """
    width, height = 720, 420
    left, right, top, bottom = 70, 130, 30, 60
    y_min, y_max = 7.0, 9.0
    budgets = sorted({b for _, stats in series.values() for b in stats})
    x_min, x_max = 0, budgets[-1] + 5

    def sx(v: float) -> float:
        return left + (v - x_min) / (x_max - x_min) * (width - left - right)

    def sy(v: float) -> float:
        return top + (y_max - v) / (y_max - y_min) * (height - top - bottom)

    section = []
    cursor = height + 34
    section.append(f'<rect x="{left}" y="{cursor - 19}" width="24" height="24" rx="6" fill="{example_hex}"/>')
    section.append(svg_text(left + 34, cursor, f"one color at every budget — {example_hex}", 15, INK, "start", "600"))
    cursor += 30
    for budget, score, text in examples:
        section.append(svg_text(left, cursor, f"{budget} words · scored {score:.1f}", 12, INK_2, "start", "600"))
        cursor += 19
        for line in textwrap.wrap(text, width=92):
            section.append(svg_text(left, cursor, html.escape(line), 13, INK, "start", "400"))
            cursor += 17
        cursor += 15
    total_height = cursor + 6

    parts = [
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {width} {total_height}" font-family="sans-serif">',
        f'<rect width="{width}" height="{total_height}" fill="#ffffff"/>',
    ]
    parts.extend(section)
    for tick in (7.0, 7.5, 8.0, 8.5, 9.0):
        y = sy(tick)
        parts.append(f'<line x1="{left}" y1="{y}" x2="{width - right}" y2="{y}" stroke="{GRID}" stroke-width="1"/>')
        parts.append(svg_text(left - 10, y + 4, f"{tick:.1f}", 12, INK_2, "end", "400"))
    for budget in budgets:
        x = sx(budget)
        parts.append(svg_text(x, height - bottom + 22, str(budget), 12, INK_2, "middle", "400"))
    parts.append(svg_text(left + (width - left - right) / 2, height - 14, "word budget", 13, INK_2, "middle", "400"))
    parts.append(f'<text x="18" y="{top + (height - top - bottom) / 2}" font-family="{FONT}" font-size="13"'
                 f' fill="{INK_2}" text-anchor="middle" transform="rotate(-90 18 {top + (height - top - bottom) / 2})">mean score (0–10)</text>')
    legend_x = left
    for label, (color, stats) in series.items():
        parts.append(f'<circle cx="{legend_x}" cy="16" r="5" fill="{color}"/>')
        parts.append(svg_text(legend_x + 11, 20, label, 13, INK, "start", "400"))
        legend_x += 11 + 8 * len(label) + 30
        points = sorted(stats.items())
        path = " ".join(f"{'M' if i == 0 else 'L'} {sx(b)} {sy(m)}" for i, (b, (m, _)) in enumerate(points))
        parts.append(f'<path d="{path}" fill="none" stroke="{color}" stroke-width="2"/>')
        for budget, (mean, se) in points:
            x, y0, y1 = sx(budget), sy(mean - se), sy(mean + se)
            parts.append(f'<line x1="{x}" y1="{y0}" x2="{x}" y2="{y1}" stroke="{color}" stroke-width="1.5"/>')
            parts.append(f'<line x1="{x - 4}" y1="{y0}" x2="{x + 4}" y2="{y0}" stroke="{color}" stroke-width="1.5"/>')
            parts.append(f'<line x1="{x - 4}" y1="{y1}" x2="{x + 4}" y2="{y1}" stroke="{color}" stroke-width="1.5"/>')
            parts.append(f'<circle cx="{x}" cy="{sy(mean)}" r="4.5" fill="{color}" stroke="#ffffff" stroke-width="2"/>')
        end_budget, (end_mean, _) = points[-1]
        parts.append(svg_text(sx(end_budget) + 14, sy(end_mean) + 4, label, 13, INK, "start", "600"))
    parts.append(svg_text(width - 10, 20, "error bars ±1 SE", 11, INK_2, "end", "400"))
    parts.append("</svg>")
    return "".join(parts)


def difficulty_grid_svg(ranked: list[tuple[str, float]]) -> str:
    """Draw the color difficulty grid, easiest to hardest.

    Args:
        ranked: Hex codes with mean scores, easiest first.

    Returns:
        The SVG document.
    """
    cols, cell, gap = 12, 54, 6
    rows = (len(ranked) + cols - 1) // cols
    width = cols * (cell + gap) - gap + 40
    height = rows * (cell + gap) - gap + 92
    parts = [
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {width} {height}" font-family="sans-serif">',
        f'<rect width="{width}" height="{height}" fill="#ffffff"/>',
        svg_text(20, 26, "easiest →", 13, INK, "start", "600"),
        svg_text(width - 20, height - 44, "→ hardest", 13, INK, "end", "600"),
    ]
    labeled = {0, len(ranked) - 3, len(ranked) - 2, len(ranked) - 1}
    for i, (hex_code, score) in enumerate(ranked):
        r, c = divmod(i, cols)
        x, y = 20 + c * (cell + gap), 40 + r * (cell + gap)
        parts.append(f'<rect x="{x}" y="{y}" width="{cell}" height="{cell}" rx="8" fill="{hex_code}"/>')
        if i in labeled:
            rgb = [int(hex_code[j : j + 2], 16) for j in (1, 3, 5)]
            luma = (0.299 * rgb[0] + 0.587 * rgb[1] + 0.114 * rgb[2]) / 255
            ink = "#000000" if luma > 0.45 else "#ffffff"
            parts.append(svg_text(x + cell / 2, y + cell / 2 + 5, f"{score:.1f}", 14, ink, "middle", "600"))
    parts.append(
        svg_text(20, height - 18, "72 colors ranked by mean round-trip score over 9 trials (Sonnet 5 describing and guessing)", 12, INK_2, "start", "400")
    )
    parts.append("</svg>")
    return "".join(parts)


def hue_scatter_svg(db_path: Path) -> str:
    """Draw per-color mean score against hue with a circular rolling mean.

    Every color is plotted as a dot in its own color, so the x axis doubles
    as the color wheel; a dark trend line shows the rolling mean over a
    thirty-degree hue window with wrap-around.

    Args:
        db_path: Path of the results database with per-color trials.

    Returns:
        The SVG document.
    """
    conn = sqlite3.connect(db_path)
    rows = conn.execute(
        "SELECT d.hex_code, avg(g.score) FROM guesses g"
        " JOIN descriptions d ON g.description_id = d.id GROUP BY d.hex_code"
    ).fetchall()
    conn.close()
    points = []
    for hex_code, mean in rows:
        r, g, b = (int(hex_code[i : i + 2], 16) / 255 for i in (1, 3, 5))
        hue = colorsys.rgb_to_hsv(r, g, b)[0] * 360
        points.append((hue, mean, hex_code))

    width, height = 720, 420
    left, right, top, bottom = 60, 20, 30, 60
    y_min, y_max = 2.0, 10.0

    def sx(hue: float) -> float:
        return left + hue / 360 * (width - left - right)

    def sy(v: float) -> float:
        return top + (y_max - v) / (y_max - y_min) * (height - top - bottom)

    parts = [
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {width} {height}" font-family="sans-serif">',
        f'<rect width="{width}" height="{height}" fill="#ffffff"/>',
    ]
    for tick in (2, 4, 6, 8, 10):
        y = sy(tick)
        parts.append(f'<line x1="{left}" y1="{y}" x2="{width - right}" y2="{y}" stroke="{GRID}"/>')
        parts.append(svg_text(left - 10, y + 4, str(tick), 12, INK_2, "end", "400"))
    for tick in range(0, 361, 60):
        parts.append(svg_text(sx(tick), height - bottom + 22, f"{tick}°", 12, INK_2, "middle", "400"))
    parts.append(svg_text(left + (width - left - right) / 2, height - 14, "hue", 13, INK_2, "middle", "400"))
    parts.append(
        f'<text x="18" y="{top + (height - top - bottom) / 2}" font-family="{FONT}" font-size="13"'
        f' fill="{INK_2}" text-anchor="middle"'
        f' transform="rotate(-90 18 {top + (height - top - bottom) / 2})">mean score (0–10)</text>'
    )
    for hue, mean, hex_code in points:
        parts.append(f'<circle cx="{sx(hue):.1f}" cy="{sy(mean):.1f}" r="3" fill="{hex_code}" fill-opacity="0.75"/>')
    trend = []
    for h in range(0, 361, 3):
        window = [m for hue, m, _ in points if min(abs(hue - h), 360 - abs(hue - h)) <= 15]
        trend.append((h, statistics.mean(window)))
    path = " ".join(f"{'M' if i == 0 else 'L'} {sx(h):.1f} {sy(m):.1f}" for i, (h, m) in enumerate(trend))
    parts.append(f'<path d="{path}" fill="none" stroke="{INK}" stroke-width="2.5"/>')
    valley = min(trend, key=lambda t: t[1])
    parts.append(svg_text(sx(valley[0]), sy(valley[1]) + 30, "the green valley", 13, INK, "middle", "600"))
    parts.append(
        svg_text(
            width - right,
            18,
            f"{len(points):,} colors × 3 trials · Sonnet 5, five-word budget · line: ±15° rolling mean",
            11,
            INK_2,
            "end",
            "400",
        )
    )
    parts.append("</svg>")
    return "".join(parts)


def sv_marginals_svg(db_path: Path) -> str:
    """Draw per-color mean score against saturation and brightness, side by side.

    Both panels use the same style as the hue figure: each color plotted as a
    dot in its own color with a dark rolling-mean trend line.

    Args:
        db_path: Path of the results database with per-color trials.

    Returns:
        The SVG document.
    """
    conn = sqlite3.connect(db_path)
    rows = conn.execute(
        "SELECT d.hex_code, avg(g.score) FROM guesses g"
        " JOIN descriptions d ON g.description_id = d.id GROUP BY d.hex_code"
    ).fetchall()
    conn.close()
    pts = []
    for hex_code, mean in rows:
        r, g, b = (int(hex_code[i : i + 2], 16) / 255 for i in (1, 3, 5))
        _, s, v = colorsys.rgb_to_hsv(r, g, b)
        pts.append((s * 100, v * 100, mean, hex_code))

    width, height = 720, 380
    top, bottom = 34, 58
    y_min, y_max = 2.0, 10.0
    panels = [
        ("saturation", 0, 30, 90, 60, 350),
        ("brightness", 1, 40, 90, 415, 705),
    ]

    def sy(v: float) -> float:
        return top + (y_max - v) / (y_max - y_min) * (height - top - bottom)

    parts = [
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {width} {height}" font-family="sans-serif">',
        f'<rect width="{width}" height="{height}" fill="#ffffff"/>',
    ]
    for tick in (2, 4, 6, 8, 10):
        y = sy(tick)
        parts.append(svg_text(50, y + 4, str(tick), 12, INK_2, "end", "400"))
        for _, _, _, _, px0, px1 in panels:
            parts.append(f'<line x1="{px0}" y1="{y}" x2="{px1}" y2="{y}" stroke="{GRID}"/>')
    parts.append(
        f'<text x="16" y="{top + (height - top - bottom) / 2}" font-family="{FONT}" font-size="13"'
        f' fill="{INK_2}" text-anchor="middle"'
        f' transform="rotate(-90 16 {top + (height - top - bottom) / 2})">mean score (0–10)</text>'
    )
    for name, idx, lo, hi, px0, px1 in panels:
        def px(v: float) -> float:
            return px0 + (v - lo) / (hi - lo) * (px1 - px0)

        parts.append(svg_text((px0 + px1) / 2, height - 14, name, 13, INK_2, "middle", "400"))
        for tick in range(lo, hi + 1, 20):
            parts.append(svg_text(px(tick), height - bottom + 20, str(tick), 12, INK_2, "middle", "400"))
        for p in pts:
            parts.append(
                f'<circle cx="{px(p[idx]):.1f}" cy="{sy(p[2]):.1f}" r="3" fill="{p[3]}" fill-opacity="0.75"/>'
            )
        trend = []
        for center in range(lo, hi + 1, 2):
            window = [p[2] for p in pts if abs(p[idx] - center) <= 5]
            trend.append((center, statistics.mean(window)))
        path = " ".join(
            f"{'M' if i == 0 else 'L'} {px(c):.1f} {sy(m):.1f}" for i, (c, m) in enumerate(trend)
        )
        parts.append(f'<path d="{path}" fill="none" stroke="{INK}" stroke-width="2.5"/>')
    parts.append(
        svg_text(
            705,
            18,
            f"{len(pts):,} colors × 3 trials · Sonnet 5, five-word budget · lines: ±5 rolling mean",
            11,
            INK_2,
            "end",
            "400",
        )
    )
    parts.append("</svg>")
    return "".join(parts)


def _heat_cells(db_path: Path) -> tuple[list[list[float]], float, float, int]:
    """Compute smoothed mean scores over the hue-by-brightness plane.

    Args:
        db_path: Path of the results database with per-color trials.

    Returns:
        Rows of cell values (brightness rows from dark to bright, hue columns),
        the minimum and maximum cell value, and the number of colors.
    """
    conn = sqlite3.connect(db_path)
    rows = conn.execute(
        "SELECT d.hex_code, avg(g.score) FROM guesses g"
        " JOIN descriptions d ON g.description_id = d.id GROUP BY d.hex_code"
    ).fetchall()
    conn.close()
    pts = []
    for hex_code, mean in rows:
        r, g, b = (int(hex_code[i : i + 2], 16) / 255 for i in (1, 3, 5))
        h, _, v = colorsys.rgb_to_hsv(r, g, b)
        pts.append((h * 360, v * 100, mean))
    cells = []
    values = []
    for j in range(10):
        v_center = 40 + (j + 0.5) * 5
        row = []
        for i in range(24):
            h_center = (i + 0.5) * 15
            window = [
                m
                for h, v, m in pts
                if min(abs(h - h_center), 360 - abs(h - h_center)) <= 10 and abs(v - v_center) <= 5
            ]
            value = statistics.mean(window)
            row.append(value)
            values.append(value)
        cells.append(row)
    return cells, min(values), max(values), len(pts)


def _ramp(value: float, lo: float, hi: float) -> str:
    """Map a score onto the sequential blue ramp, darker meaning lower.

    Args:
        value: The score to map.
        lo: Score mapped to the dark end.
        hi: Score mapped to the light end.

    Returns:
        An ``rgb(...)`` color string.
    """
    t = (value - lo) / (hi - lo)
    dark, light = (16, 60, 104), (232, 242, 252)
    rgb = [round(d + (l - d) * t) for d, l in zip(dark, light)]
    return f"rgb({rgb[0]},{rgb[1]},{rgb[2]})"


def hue_brightness_heatmap_svg(db_path: Path) -> str:
    """Draw mean score over the hue-by-brightness plane as a heatmap.

    Cells are smoothed with overlapping windows of ten degrees of hue and
    five brightness units; darker cells mark lower scores, so difficulty
    reads as dark terrain.

    Args:
        db_path: Path of the results database with per-color trials.

    Returns:
        The SVG document.
    """
    cells, lo, hi, n_colors = _heat_cells(db_path)
    hue_bins, v_bins = 24, 10

    def ramp(value: float) -> str:
        return _ramp(value, lo, hi)

    width, height = 720, 420
    left, top = 60, 30
    cell_w, cell_h = 26, 30
    parts = [
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {width} {height}" font-family="sans-serif">',
        f'<rect width="{width}" height="{height}" fill="#ffffff"/>',
    ]
    for j, row in enumerate(cells):
        y = top + (v_bins - 1 - j) * cell_h
        for i, value in enumerate(row):
            parts.append(
                f'<rect x="{left + i * cell_w}" y="{y}" width="{cell_w - 1}" height="{cell_h - 1}"'
                f' rx="3" fill="{ramp(value)}"/>'
            )
    for tick in range(0, 361, 60):
        parts.append(svg_text(left + tick / 15 * cell_w, top + v_bins * cell_h + 18, f"{tick}°", 12, INK_2, "middle", "400"))
    parts.append(svg_text(left + hue_bins * cell_w / 2, top + v_bins * cell_h + 40, "hue", 13, INK_2, "middle", "400"))
    for v_tick in (40, 60, 80, 90):
        y = top + (90 - v_tick) / 5 * cell_h
        parts.append(svg_text(left - 8, y + 4, str(v_tick), 12, INK_2, "end", "400"))
    parts.append(
        f'<text x="18" y="{top + v_bins * cell_h / 2}" font-family="{FONT}" font-size="13" fill="{INK_2}"'
        f' text-anchor="middle" transform="rotate(-90 18 {top + v_bins * cell_h / 2})">brightness</text>'
    )
    bar_x, bar_y, bar_w = left, height - 34, 200
    for k in range(40):
        parts.append(
            f'<rect x="{bar_x + k * bar_w / 40}" y="{bar_y}" width="{bar_w / 40 + 0.5}" height="10"'
            f' fill="{ramp(lo + (hi - lo) * k / 39)}"/>'
        )
    parts.append(svg_text(bar_x - 8, bar_y + 9, f"{lo:.1f}", 11, INK_2, "end", "400"))
    parts.append(svg_text(bar_x + bar_w + 8, bar_y + 9, f"{hi:.1f}", 11, INK_2, "start", "400"))
    parts.append(svg_text(bar_x + bar_w / 2, bar_y - 6, "mean score", 11, INK_2, "middle", "400"))
    parts.append(
        svg_text(
            width - 20,
            bar_y + 9,
            f"{n_colors:,} colors × 3 trials · Sonnet 5, five-word budget",
            11,
            INK_2,
            "end",
            "400",
        )
    )
    parts.append("</svg>")
    return "".join(parts)


def difficulty_wheel_svg(db_path: Path) -> str:
    """Draw mean score on a color wheel: hue as angle, brightness as radius.

    The dark core is low brightness and the rim is high brightness; cell shade
    follows the same sequential ramp as the flat heatmap, and a thin rainbow
    ring around the outside anchors the hue orientation.

    Args:
        db_path: Path of the results database with per-color trials.

    Returns:
        The SVG document.
    """
    import math

    cells, lo, hi, n_colors = _heat_cells(db_path)
    width, height = 720, 530
    cx, cy = 360, 225
    r0, r1 = 52, 178

    def point(hue: float, radius: float) -> tuple[float, float]:
        theta = math.radians(hue - 90)
        return cx + radius * math.cos(theta), cy + radius * math.sin(theta)

    def sector(h0: float, h1: float, ra: float, rb: float, fill: str) -> str:
        x0, y0 = point(h0, ra)
        x1, y1 = point(h0, rb)
        x2, y2 = point(h1, rb)
        x3, y3 = point(h1, ra)
        return (
            f'<path d="M {x0:.1f} {y0:.1f} L {x1:.1f} {y1:.1f}'
            f' A {rb:.1f} {rb:.1f} 0 0 1 {x2:.1f} {y2:.1f}'
            f' L {x3:.1f} {y3:.1f}'
            f' A {ra:.1f} {ra:.1f} 0 0 0 {x0:.1f} {y0:.1f} Z"'
            f' fill="{fill}" stroke="#ffffff" stroke-width="1"/>'
        )

    parts = [
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {width} {height}" font-family="sans-serif">',
        f'<rect width="{width}" height="{height}" fill="#ffffff"/>',
    ]
    ring_w = (r1 - r0) / 10
    for j, row in enumerate(cells):
        ra = r0 + j * ring_w
        rb = ra + ring_w
        for i, value in enumerate(row):
            parts.append(sector(i * 15, (i + 1) * 15, ra, rb, _ramp(value, lo, hi)))
    for i in range(72):
        h = i * 5
        rgb = colorsys.hsv_to_rgb((h + 2.5) / 360, 0.85, 0.95)
        fill = f"rgb({round(rgb[0] * 255)},{round(rgb[1] * 255)},{round(rgb[2] * 255)})"
        parts.append(sector(h, h + 5, r1 + 5, r1 + 15, fill))
    for hue in (0, 90, 180, 270):
        x, y = point(hue, r1 + 30)
        parts.append(svg_text(x, y + 4, f"{hue}°", 12, INK_2, "middle", "400"))
    parts.append(svg_text(cx, cy - 4, "dark", 11, INK_2, "middle", "400"))
    parts.append(svg_text(cx, cy + 12, "core", 11, INK_2, "middle", "400"))
    parts.append(svg_text(cx, cy + r1 + 56, "brightness grows outward, forty at the core to ninety at the rim", 12, INK_2, "middle", "400"))
    bar_x, bar_y, bar_w = 40, height - 25, 180
    for k in range(40):
        parts.append(
            f'<rect x="{bar_x + k * bar_w / 40}" y="{bar_y}" width="{bar_w / 40 + 0.5}" height="10"'
            f' fill="{_ramp(lo + (hi - lo) * k / 39, lo, hi)}"/>'
        )
    parts.append(svg_text(bar_x - 8, bar_y + 9, f"{lo:.1f}", 11, INK_2, "end", "400"))
    parts.append(svg_text(bar_x + bar_w + 8, bar_y + 9, f"{hi:.1f}", 11, INK_2, "start", "400"))
    parts.append(svg_text(bar_x + bar_w / 2, bar_y - 6, "mean score", 11, INK_2, "middle", "400"))
    parts.append(
        svg_text(
            width - 20,
            bar_y + 9,
            f"{n_colors:,} colors × 3 trials · Sonnet 5, five-word budget",
            11,
            INK_2,
            "end",
            "400",
        )
    )
    parts.append("</svg>")
    return "".join(parts)


def hue_combined_svg(db_path: Path) -> str:
    """Draw the hue scatter and the difficulty wheel side by side.

    Both panels share one rolling mean over hue: the left panel shows it as a
    line over the scatter, and the right panel wraps the same curve around
    the wheel as a ring outside the cells, averaging score across brightness.

    Args:
        db_path: Path of the results database with per-color trials.

    Returns:
        The SVG document.
    """
    import math

    conn = sqlite3.connect(db_path)
    rows = conn.execute(
        "SELECT d.hex_code, avg(g.score) FROM guesses g"
        " JOIN descriptions d ON g.description_id = d.id GROUP BY d.hex_code"
    ).fetchall()
    conn.close()
    points = []
    for hex_code, mean in rows:
        r, g, b = (int(hex_code[i : i + 2], 16) / 255 for i in (1, 3, 5))
        hue = colorsys.rgb_to_hsv(r, g, b)[0] * 360
        points.append((hue, mean, hex_code))
    trend = []
    for h in range(0, 361, 3):
        window = [m for hue, m, _ in points if min(abs(hue - h), 360 - abs(hue - h)) <= 15]
        trend.append((h, statistics.mean(window)))
    cells, lo, hi, n_colors = _heat_cells(db_path)

    width, height = 1240, 620
    parts = [
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {width} {height}" font-family="sans-serif">',
        f'<rect width="{width}" height="{height}" fill="#ffffff"/>',
    ]

    left, right_edge, top, bottom = 95, 640, 45, 125
    y_min, y_max = 2.0, 10.0

    def sx(hue: float) -> float:
        return left + hue / 360 * (right_edge - left)

    def sy(v: float) -> float:
        return top + (y_max - v) / (y_max - y_min) * (height - top - bottom)

    for tick in (2, 4, 6, 8, 10):
        y = sy(tick)
        parts.append(f'<line x1="{left}" y1="{y}" x2="{right_edge}" y2="{y}" stroke="{GRID}"/>')
        parts.append(svg_text(left - 10, y + 4, str(tick), 28, INK_2, "end", "400"))
    for tick in range(0, 361, 60):
        parts.append(svg_text(sx(tick), height - bottom + 36, f"{tick}°", 28, INK_2, "middle", "400"))
    parts.append(svg_text((left + right_edge) / 2, height - bottom + 74, "hue", 31, INK_2, "middle", "400"))
    parts.append(
        f'<text x="32" y="{top + (height - top - bottom) / 2}" font-family="{FONT}" font-size="31"'
        f' fill="{INK_2}" text-anchor="middle"'
        f' transform="rotate(-90 32 {top + (height - top - bottom) / 2})">mean score (0–10)</text>'
    )
    for hue, mean, hex_code in points:
        parts.append(f'<circle cx="{sx(hue):.1f}" cy="{sy(mean):.1f}" r="5.5" fill="{hex_code}" fill-opacity="0.75"/>')
    path = " ".join(f"{'M' if i == 0 else 'L'} {sx(h):.1f} {sy(m):.1f}" for i, (h, m) in enumerate(trend))
    parts.append(f'<path d="{path}" fill="none" stroke="{INK}" stroke-width="4.5"/>')

    cx, cy = 950, 285
    r0, r1 = 46, 150
    band0, band1 = r1 + 26, r1 + 72
    t_lo = min(m for _, m in trend) - 0.08
    t_hi = max(m for _, m in trend) + 0.08

    def point_at(hue: float, radius: float) -> tuple[float, float]:
        theta = math.radians(hue - 90)
        return cx + radius * math.cos(theta), cy + radius * math.sin(theta)

    def sector(h0: float, h1: float, ra: float, rb: float, fill: str) -> str:
        x0, y0 = point_at(h0, ra)
        x1, y1 = point_at(h0, rb)
        x2, y2 = point_at(h1, rb)
        x3, y3 = point_at(h1, ra)
        return (
            f'<path d="M {x0:.1f} {y0:.1f} L {x1:.1f} {y1:.1f}'
            f' A {rb:.1f} {rb:.1f} 0 0 1 {x2:.1f} {y2:.1f}'
            f' L {x3:.1f} {y3:.1f}'
            f' A {ra:.1f} {ra:.1f} 0 0 0 {x0:.1f} {y0:.1f} Z"'
            f' fill="{fill}" stroke="#ffffff" stroke-width="1"/>'
        )

    ring_w = (r1 - r0) / 10
    for j, row in enumerate(cells):
        for i, value in enumerate(row):
            parts.append(sector(i * 15, (i + 1) * 15, r0 + j * ring_w, r0 + (j + 1) * ring_w, _ramp(value, lo, hi)))
    for i in range(72):
        h = i * 5
        rgb = colorsys.hsv_to_rgb((h + 2.5) / 360, 0.85, 0.95)
        fill = f"rgb({round(rgb[0] * 255)},{round(rgb[1] * 255)},{round(rgb[2] * 255)})"
        parts.append(sector(h, h + 5, r1 + 5, r1 + 14, fill))

    def band_r(value: float) -> float:
        return band0 + (value - t_lo) / (t_hi - t_lo) * (band1 - band0)

    for ref, angle in ((8.0, 302), (8.5, 334)):
        parts.append(f'<circle cx="{cx}" cy="{cy}" r="{band_r(ref):.1f}" fill="none" stroke="{GRID}" stroke-width="1"/>')
        rx, ry = point_at(angle, band_r(ref))
        parts.append(svg_text(rx, ry - 3, f"{ref:.1f}", 23, INK_2, "middle", "400"))
    ring_path = " ".join(
        f"{'M' if i == 0 else 'L'} {point_at(h, band_r(m))[0]:.1f} {point_at(h, band_r(m))[1]:.1f}"
        for i, (h, m) in enumerate(trend)
    )
    parts.append(f'<path d="{ring_path} Z" fill="none" stroke="{INK}" stroke-width="4.5"/>')
    for hue in (0, 90, 180, 270):
        x, y = point_at(hue, band1 + 30)
        parts.append(svg_text(x, y + 4, f"{hue}°", 28, INK_2, "middle", "400"))
    bar_x, bar_y, bar_w = cx - 105, height - 38, 210
    for k in range(40):
        parts.append(
            f'<rect x="{bar_x + k * bar_w / 40}" y="{bar_y}" width="{bar_w / 40 + 0.5}" height="15"'
            f' fill="{_ramp(lo + (hi - lo) * k / 39, lo, hi)}"/>'
        )
    parts.append(svg_text(bar_x - 8, bar_y + 9, f"{lo:.1f}", 25, INK_2, "end", "400"))
    parts.append(svg_text(bar_x + bar_w + 8, bar_y + 9, f"{hi:.1f}", 25, INK_2, "start", "400"))
    parts.append(svg_text(bar_x + bar_w / 2, bar_y - 14, "cell mean score", 25, INK_2, "middle", "400"))
    parts.append("</svg>")
    return "".join(parts)


def budget_widget_html(
    series: dict[str, tuple[str, dict[int, tuple[float, float]]]],
    examples: list[tuple[int, float, str]],
    example_hex: str,
) -> str:
    """Build the interactive budget figure as a self-contained HTML page.

    The chart is the same score-versus-budget plot as the static SVG; hovering
    or tapping a budget column shows that budget's example description in a
    fixed panel below, so the prose never stretches the page.

    Args:
        series: Mapping of series label to its color and per-budget stats.
        examples: Budget, score, and description text rows for the example color.
        example_hex: Color whose descriptions fill the prose panel.

    Returns:
        The HTML document.
    """
    import json

    budgets = sorted({b for _, stats in series.values() for b in stats})
    data = {
        "budgets": budgets,
        "series": [
            {"label": label, "color": color, "stats": {str(b): stats[b] for b in stats}}
            for label, (color, stats) in series.items()
        ],
        "prose": {str(b): {"score": s, "text": t} for b, s, t in examples},
        "hex": example_hex,
    }
    width, height = 720, 360
    left, right, top, bottom = 60, 20, 26, 44
    x_min, x_max = 0, budgets[-1] + 12
    y_min, y_max = 7.0, 9.2

    def sx(v: float) -> float:
        return left + (v - x_min) / (x_max - x_min) * (width - left - right)

    def sy(v: float) -> float:
        return top + (y_max - v) / (y_max - y_min) * (height - top - bottom)

    svg = [f'<svg viewBox="0 0 {width} {height}">']
    for tick in (7.0, 7.5, 8.0, 8.5, 9.0):
        y = sy(tick)
        svg.append(f'<line x1="{left}" y1="{y}" x2="{width - right}" y2="{y}" stroke="{GRID}"/>')
        svg.append(f'<text x="{left - 8}" y="{y + 4}" text-anchor="end" class="tick">{tick:.1f}</text>')
    for label_info in data["series"]:
        color = label_info["color"]
        pts = sorted((int(b), v) for b, v in label_info["stats"].items())
        path = " ".join(f"{'M' if i == 0 else 'L'} {sx(b)} {sy(v[0])}" for i, (b, v) in enumerate(pts))
        svg.append(f'<path d="{path}" fill="none" stroke="{color}" stroke-width="2"/>')
        for b, (mean, se) in pts:
            x = sx(b)
            svg.append(f'<line x1="{x}" y1="{sy(mean - se)}" x2="{x}" y2="{sy(mean + se)}" stroke="{color}" stroke-width="1.5"/>')
            svg.append(f'<circle cx="{x}" cy="{sy(mean)}" r="4" fill="{color}" stroke="#fff" stroke-width="2"/>')
    for b in budgets:
        x = sx(b)
        svg.append(f'<text x="{x}" y="{height - bottom + 20}" text-anchor="middle" class="tick">{b}</text>')
        svg.append(
            f'<rect class="hit" data-budget="{b}" x="{x - 12}" y="{top}" width="24"'
            f' height="{height - top - bottom}" fill="transparent"/>'
        )
    svg.append(f'<rect id="cursor" x="0" y="{top}" width="24" height="{height - top - bottom}" fill="#0b0b0b" opacity="0" rx="6"/>')
    svg.append(f'<text x="{left}" y="16" class="tick">error bars ±1 SE</text>')
    svg.append(f'<text x="{left + (width - left - right) / 2}" y="{height - 4}" text-anchor="middle" class="tick">word budget</text>')
    svg.append(f'<text x="14" y="{top + (height - top - bottom) / 2}" text-anchor="middle" class="tick"'
               f' transform="rotate(-90 14 {top + (height - top - bottom) / 2})">mean score (0–10)</text>')
    svg.append("</svg>")

    legend = "".join(
        f'<span class="key"><span class="dot" style="background:{s["color"]}"></span>{s["label"]}</span>'
        for s in data["series"]
    )
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Word budget vs score</title>
<style>
  * {{ box-sizing: border-box; margin: 0; }}
  body {{ background: #fff; color: #0b0b0b; font: 15px/1.5 system-ui, -apple-system, sans-serif; padding: 10px; }}
  #wrap {{ max-width: 720px; margin: 0 auto; display: flex; flex-direction: column; min-height: 545px; }}
  .tick {{ font-size: 16px; fill: {INK_2}; font-family: system-ui, sans-serif; }}
  svg {{ width: 100%; height: auto; display: block; }}
  .hit {{ cursor: pointer; }}
  #legend {{ display: flex; gap: 18px; font-size: 13px; color: {INK_2}; padding: 0 0 4px 60px; }}
  .key {{ display: flex; align-items: center; gap: 6px; }}
  .dot {{ width: 10px; height: 10px; border-radius: 50%; display: inline-block; }}
  #panel {{ border: 1px solid {EDGE}; border-radius: 10px; padding: 12px 16px; margin-top: 6px; flex: 1; min-height: 150px; overflow-y: auto; }}
  #panel-head {{ display: flex; align-items: center; gap: 10px; margin-bottom: 8px; font-size: 13px; color: {INK_2}; }}
  #panel-head .chip {{ width: 20px; height: 20px; border-radius: 5px; background: {example_hex}; }}
  #panel-head b {{ color: {INK}; }}
  #prose {{ font-size: 14px; }}
  #hint {{ font-size: 12px; color: {INK_2}; margin-top: 6px; }}
</style>
</head>
<body>
<div id="wrap">
  <div id="legend">{legend}</div>
  {"".join(svg)}
  <div id="panel">
    <div id="panel-head"><span class="chip"></span><span id="panel-label"></span></div>
    <div id="prose"></div>
  </div>
  <div id="hint">Hover or tap a budget on the chart to read how the describer spent it on {example_hex}.</div>
</div>
<script>
const DATA = {json.dumps(data)};
const cursor = document.getElementById("cursor");
const panelLabel = document.getElementById("panel-label");
const prose = document.getElementById("prose");

function activate(budget) {{
  const hit = document.querySelector(`.hit[data-budget="${{budget}}"]`);
  cursor.setAttribute("x", parseFloat(hit.getAttribute("x")));
  cursor.setAttribute("opacity", "0.06");
  const p = DATA.prose[budget];
  const stats = DATA.series
    .filter(s => s.stats[budget])
    .map(s => `${{s.label}} ${{s.stats[budget][0].toFixed(2)}}`)
    .join(" · ");
  panelLabel.innerHTML = `<b>${{budget}}-word budget</b> · ${{stats}}` +
    (p ? ` · this description scored ${{p.score.toFixed(1)}}` : "");
  prose.textContent = p ? p.text : "No example description at this budget.";
}}
for (const hit of document.querySelectorAll(".hit")) {{
  const b = hit.dataset.budget;
  hit.addEventListener("pointerenter", () => activate(b));
  hit.addEventListener("click", () => activate(b));
}}
activate(String(DATA.budgets[Math.floor(DATA.budgets.length / 2)]));
</script>
</body>
</html>
"""


@app.command()
def make(
    out_dir: Path,
    sonnet_db: Path = Path("data/scan72_sonnet.db"),
    gptoss_db: Path = Path("data/scan72.db"),
    halton_db: Path = Path("data/halton_sonnet.db"),
    example_hex: str = "#95eabf",
) -> None:
    """Generate the blog figures from the experiment databases.

    Args:
        out_dir: Directory the SVG files are written to.
        sonnet_db: Results database of the Sonnet 5 scan.
        gptoss_db: Results database of the gpt-oss-20b scan.
        halton_db: Results database of the large evenly-spread color experiment.
        example_hex: Color whose per-budget descriptions appear under the budget curve.
    """
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "pipeline.svg").write_text(pipeline_svg())
    series = {
        "Sonnet 5": (SONNET, budget_stats(sonnet_db, "anthropic:claude-sonnet-5")),
        "gpt-oss-20b": (GPTOSS, budget_stats(gptoss_db, "openai/gpt-oss-20b")),
    }
    examples = example_rows(sonnet_db, example_hex)
    (out_dir / "budget_curve.svg").write_text(budget_curve_svg(series, examples, example_hex))
    widget = Path("docs/budget.html")
    widget.write_text(budget_widget_html(series, examples, example_hex))
    typer.echo(f"wrote {widget}")
    (out_dir / "difficulty_grid.svg").write_text(difficulty_grid_svg(color_difficulty(sonnet_db)))
    (out_dir / "hue_difficulty.svg").write_text(hue_scatter_svg(halton_db))
    (out_dir / "sv_marginals.svg").write_text(sv_marginals_svg(halton_db))
    (out_dir / "hue_brightness_heatmap.svg").write_text(hue_brightness_heatmap_svg(halton_db))
    (out_dir / "difficulty_wheel.svg").write_text(difficulty_wheel_svg(halton_db))
    (out_dir / "hue_combined.svg").write_text(hue_combined_svg(halton_db))
    for name in (
        "pipeline.svg",
        "budget_curve.svg",
        "difficulty_grid.svg",
        "hue_difficulty.svg",
        "sv_marginals.svg",
        "hue_brightness_heatmap.svg",
        "difficulty_wheel.svg",
        "hue_combined.svg",
    ):
        typer.echo(f"wrote {out_dir / name}")


if __name__ == "__main__":
    app()
