import colorsys
import math

from coloraide import Color


def delta_e(hex_a: str, hex_b: str) -> float:
    """Compute the CIEDE2000 perceptual distance between two colors.

    A distance below one is imperceptible to humans, around ten reads as a
    clearly different shade, and unrelated colors typically score above forty.

    Args:
        hex_a: First color as a ``#rrggbb`` hex code.
        hex_b: Second color as a ``#rrggbb`` hex code.

    Returns:
        The CIEDE2000 distance.
    """
    return Color(hex_a).delta_e(hex_b, method="2000")


def _hex_to_rgb(hex_code: str) -> tuple[float, float, float]:
    """Parse a hex code into RGB channels on the unit interval.

    Args:
        hex_code: The color as a ``#rrggbb`` hex code.

    Returns:
        The red, green, and blue channels in [0, 1].
    """
    r, g, b = (int(hex_code[i : i + 2], 16) / 255 for i in (1, 3, 5))
    return r, g, b


def _linearize(channel: float) -> float:
    """Convert one sRGB channel to linear light.

    Args:
        channel: The gamma-encoded channel in [0, 1].

    Returns:
        The linear-light channel.
    """
    if channel <= 0.04045:
        return channel / 12.92
    return ((channel + 0.055) / 1.055) ** 2.4


def _rgb_to_lab(r: float, g: float, b: float) -> tuple[float, float, float]:
    """Convert sRGB channels to CIELAB under the D65 white point.

    Args:
        r: Red channel in [0, 1].
        g: Green channel in [0, 1].
        b: Blue channel in [0, 1].

    Returns:
        The L*, a*, and b* components.
    """
    rl, gl, bl = _linearize(r), _linearize(g), _linearize(b)
    x = (0.4124564 * rl + 0.3575761 * gl + 0.1804375 * bl) / 0.95047
    y = 0.2126729 * rl + 0.7151522 * gl + 0.0721750 * bl
    z = (0.0193339 * rl + 0.1191920 * gl + 0.9503041 * bl) / 1.08883

    def f(t: float) -> float:
        if t > 0.008856:
            return t ** (1 / 3)
        return 7.787 * t + 16 / 116

    return 116 * f(y) - 16, 500 * (f(x) - f(y)), 200 * (f(y) - f(z))


def _cie2000(lab_a: tuple[float, float, float], lab_b: tuple[float, float, float]) -> float:
    """Compute CIEDE2000 between two Lab colors.

    Args:
        lab_a: First color as L*, a*, b* components.
        lab_b: Second color as L*, a*, b* components.

    Returns:
        The CIEDE2000 distance.
    """
    l1, a1, b1 = lab_a
    l2, a2, b2 = lab_b
    l_bar = (l1 + l2) / 2
    c_bar = (math.hypot(a1, b1) + math.hypot(a2, b2)) / 2
    g = 0.5 * (1 - math.sqrt(c_bar**7 / (c_bar**7 + 25**7)))
    ap1, ap2 = a1 * (1 + g), a2 * (1 + g)
    cp1, cp2 = math.hypot(ap1, b1), math.hypot(ap2, b2)
    cp_bar = (cp1 + cp2) / 2
    dcp = cp2 - cp1
    hp1 = math.degrees(math.atan2(b1, ap1)) % 360
    hp2 = math.degrees(math.atan2(b2, ap2)) % 360
    if abs(hp1 - hp2) <= 180:
        dhp = hp2 - hp1
        hp_bar = (hp1 + hp2) / 2
    else:
        dhp = hp2 - hp1 + 360 if hp2 <= hp1 else hp2 - hp1 - 360
        hp_bar = (hp1 + hp2 + 360) / 2 if hp1 + hp2 < 360 else (hp1 + hp2 - 360) / 2
    dhp_term = 2 * math.sqrt(cp1 * cp2) * math.sin(math.radians(dhp) / 2)
    t = (
        1
        - 0.17 * math.cos(math.radians(hp_bar - 30))
        + 0.24 * math.cos(math.radians(2 * hp_bar))
        + 0.32 * math.cos(math.radians(3 * hp_bar + 6))
        - 0.20 * math.cos(math.radians(4 * hp_bar - 63))
    )
    sl = 1 + 0.015 * (l_bar - 50) ** 2 / math.sqrt(20 + (l_bar - 50) ** 2)
    sc = 1 + 0.045 * cp_bar
    sh = 1 + 0.015 * cp_bar * t
    rt = (
        -2
        * math.sqrt(cp_bar**7 / (cp_bar**7 + 25**7))
        * math.sin(math.radians(60 * math.exp(-(((hp_bar - 275) / 25) ** 2))))
    )
    return math.sqrt(
        ((l2 - l1) / sl) ** 2
        + (dcp / sc) ** 2
        + (dhp_term / sh) ** 2
        + (dcp / sc) * rt * (dhp_term / sh)
    )


def dialed_score(hex_a: str, hex_b: str) -> float:
    """Score the similarity of two colors with dialed.gg's color game formula.

    The CIEDE2000 distance between the colors is squashed onto a zero-to-ten
    scale via ``10 / (1 + (dE / 25.25) ** 1.55)``, then adjusted with a
    saturation-gated bonus for close hues and penalty for distant hues. The
    game's deterministic score jitter is omitted. Ten means identical, and
    scores fall toward zero as the colors diverge.

    Args:
        hex_a: First color as a ``#rrggbb`` hex code.
        hex_b: Second color as a ``#rrggbb`` hex code.

    Returns:
        The similarity score in [0, 10], rounded to two decimals.
    """
    rgb_a = _hex_to_rgb(hex_a)
    rgb_b = _hex_to_rgb(hex_b)
    distance = _cie2000(_rgb_to_lab(*rgb_a), _rgb_to_lab(*rgb_b))
    base = 10 / (1 + (distance / 25.25) ** 1.55)
    hue_a, sat_a = colorsys.rgb_to_hsv(*rgb_a)[:2]
    hue_b, sat_b = colorsys.rgb_to_hsv(*rgb_b)[:2]
    dh = 360 * min(abs(hue_a - hue_b), 1 - abs(hue_a - hue_b))
    mean_sat = 100 * (sat_a + sat_b) / 2
    adjusted = (
        base
        + (10 - base) * max(0.0, 1 - (dh / 25) ** 1.5) * min(1.0, mean_sat / 30) * 0.25
        - base * max(0.0, (dh - 30) / 150) * min(1.0, mean_sat / 40) * 0.15
    )
    return max(0.0, min(10.0, round(adjusted, 2)))
