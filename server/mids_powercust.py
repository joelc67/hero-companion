"""
mids_powercust.py - Produce a Homecoming .powerCust file (power color/glow
customization) from a build + a color scheme.

Format (verified from real Homecoming/powercust/*.powerCust files): CRLF text,
an outer { ... } wrapping one block per power:

    PowerCustomization
    {
    \tPowerName <dotted internal power name>
    \tPower 0
    \tColor1  r,  g,  b,  a
    \tColor2  r,  g,  b,  a
    }

Color1 = primary tint, Color2 = secondary / inner-glow tint (alpha always 255).
The numeric `Power` field in game-written files is a runtime handle; the loader
is expected to match by PowerName, so we write 0 (flagged for an in-game test).
"""

CRLF = "\r\n"

BRIGHTNESS = {            # multiplier applied to each RGB channel
    "dark": 0.5,
    "default": 1.0,
    "bright": 1.5,
}


def _clamp(v):
    return max(0, min(255, int(round(v))))


def apply_brightness(rgb, mode):
    m = BRIGHTNESS.get(mode, 1.0)
    return [_clamp(c * m) for c in rgb[:3]]


def _color_line(label, rgb):
    r, g, b = (rgb + [0, 0, 0])[:3]
    a = rgb[3] if len(rgb) > 3 else 255
    return f"\t{label}  {_clamp(r)},  {_clamp(g)},  {_clamp(b)},  {_clamp(a)}"


def _block(full_name, c1, c2):
    return CRLF.join([
        "PowerCustomization",
        "{",
        f"\tPowerName {full_name}",
        "\tPower 0",
        _color_line("Color1", c1),
        _color_line("Color2", c2),
        "}",
    ])


def build_powercust(blocks):
    """blocks: [{full_name, c1:[r,g,b(,a)], c2:[r,g,b(,a)]}] -> file text.
    Matches the game's framing: leading blank line, outer '{', blocks separated
    by two blank lines, trailing outer '}'."""
    body = (CRLF + CRLF).join(_block(b["full_name"], b["c1"], b["c2"])
                             for b in blocks)
    return (CRLF + "{" + CRLF + body + CRLF + CRLF + "}" + CRLF + CRLF)


def scheme_blocks(powers, default_scheme, by_powerset=None):
    """Expand per-powerset color schemes into one block per power.
    powers: [{full_name, powerset_full_name}]
    default_scheme / by_powerset values: {c1:[r,g,b], c2:[r,g,b], brightness}.
    Returns the block list for build_powercust."""
    by_powerset = by_powerset or {}
    out = []
    for p in powers:
        full = p.get("full_name")
        if not full:
            continue
        sc = by_powerset.get(p.get("powerset_full_name")) or default_scheme
        if not sc:
            continue
        bright = sc.get("brightness", "default")
        c1 = apply_brightness(sc.get("c1") or [255, 255, 255], bright) + [255]
        c2 = apply_brightness(sc.get("c2") or [255, 255, 255], bright) + [255]
        out.append({"full_name": full, "c1": c1, "c2": c2})
    return out
