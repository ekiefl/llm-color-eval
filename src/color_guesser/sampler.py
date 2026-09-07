import colorsys
import random


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
