import colorsys
import random


def _halton(index: int, base: int) -> float:
    """Compute one coordinate of the Halton low-discrepancy sequence.

    Args:
        index: One-based index into the sequence.
        base: Prime base of the coordinate.

    Returns:
        A value in [0, 1).
    """
    result = 0.0
    fraction = 1.0
    while index > 0:
        fraction /= base
        result += fraction * (index % base)
        index //= base
    return result


def sample_halton(n: int) -> list[str]:
    """Sample hex codes evenly spread across the HSB slider space.

    Points come from the Halton sequence (bases two, three, and five) over
    hue, saturation, and brightness, so the sample is even where uniform RGB
    sampling clumps into muddy midtones. Saturation spans 30 to 90 and
    brightness 40 to 90, mirroring the color range dialed.gg draws its own
    targets from. The sequence is deterministic and prefix-stable: the first
    n colors of a larger sample are always identical, so a dataset can be
    grown without invalidating work already done on the earlier colors.

    Args:
        n: Number of colors to sample.

    Returns:
        Hex codes in ``#rrggbb`` form.
    """
    colors = []
    for i in range(1, n + 1):
        h = _halton(i, 2) * 360
        s = 30 + _halton(i, 3) * 60
        b = 40 + _halton(i, 5) * 50
        r, g, bl = colorsys.hsv_to_rgb(h / 360, s / 100, b / 100)
        colors.append(f"#{round(r * 255):02x}{round(g * 255):02x}{round(bl * 255):02x}")
    return colors


def sample_uniform(n: int, seed: int) -> list[str]:
    """Sample hex codes uniformly at random from RGB space.

    Args:
        n: Number of colors to sample.
        seed: Seed for the random number generator.

    Returns:
        Hex codes in ``#rrggbb`` form.
    """
    rng = random.Random(seed)
    return [f"#{rng.randrange(1 << 24):06x}" for _ in range(n)]


def sample_stratified(hue_steps: int, lightness_steps: int, saturation_steps: int) -> list[str]:
    """Sample hex codes on an evenly spaced grid in HLS space.

    Uniform RGB sampling over-represents murky midtones; a grid over hue,
    lightness, and saturation spreads samples across perceptually distinct
    regions. Lightness and saturation extremes are excluded so the grid never
    collapses to black, white, or duplicate grays.

    Args:
        hue_steps: Number of evenly spaced hues.
        lightness_steps: Number of evenly spaced lightness levels.
        saturation_steps: Number of evenly spaced saturation levels.

    Returns:
        Hex codes in ``#rrggbb`` form.
    """
    colors = []
    for h in range(hue_steps):
        for li in range(lightness_steps):
            for s in range(saturation_steps):
                hue = h / hue_steps
                lightness = (li + 1) / (lightness_steps + 1)
                saturation = (s + 1) / (saturation_steps + 1)
                r, g, b = colorsys.hls_to_rgb(hue, lightness, saturation)
                colors.append(f"#{round(r * 255):02x}{round(g * 255):02x}{round(b * 255):02x}")
    return colors
