"""Artistic style definitions and aesthetic presets for PhotoCraft Painter.

Provides overarching art styles (realistic, dreamlike, abstract, sketchy, cartoon, painterly)
that govern prompt engineering, color palettes, brushstroke dynamics, and detail generation.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class StylePreset:
    """Configuration for an overarching artistic style."""

    id: str
    name: str
    description: str
    ai_guidance: str
    wobble: float
    outline_hardness: float
    outline_size_scale: float
    wash_hardness: float
    wash_opacity: float
    color_mood: str

    def adjust_color(self, hex_col: str | None, factor: float = 1.0) -> str | None:
        """Adjust color according to the style's palette characteristics."""
        if not hex_col or not hex_col.startswith("#"):
            return hex_col
        try:
            h = hex_col.lstrip("#")
            if len(h) == 3:
                h = "".join(c * 2 for c in h)
            r = int(h[0:2], 16)
            g = int(h[2:4], 16)
            b = int(h[4:6], 16)

            if self.id == "sketchy":
                # Desaturate towards graphite / charcoal / sepia tones
                gray = int(0.299 * r + 0.587 * g + 0.114 * b)
                # Keep a subtle warm sepia undertone
                r = int(gray * 0.95 * factor)
                g = int(gray * 0.90 * factor)
                b = int(gray * 0.85 * factor)
            elif self.id == "dreamlike":
                # Shift towards luminous pastel / ethereal glow (boost magenta/cyan/gold)
                r = int(min(255, r * 1.08 + 15) * factor)
                g = int(min(255, g * 0.98 + 10) * factor)
                b = int(min(255, b * 1.15 + 20) * factor)
            elif self.id == "cartoon":
                # High contrast, saturated vivid cel colors
                r = int(min(255, r * 1.12 if r > 128 else r * 0.88) * factor)
                g = int(min(255, g * 1.12 if g > 128 else g * 0.88) * factor)
                b = int(min(255, b * 1.12 if b > 128 else b * 0.88) * factor)
            elif self.id == "abstract":
                # Bold pop contrast with slight chromatic vibrancy
                r = int(min(255, (r + 30 if r > g else r * 0.8)) * factor)
                g = int(min(255, (g + 30 if g > b else g * 0.8)) * factor)
                b = int(min(255, (b + 30 if b > r else b * 0.8)) * factor)
            else:
                # Realistic & Painterly: standard luminance scaling
                r = int(r * factor)
                g = int(g * factor)
                b = int(b * factor)

            return f"#{max(0, min(255, r)):02x}{max(0, min(255, g)):02x}{max(0, min(255, b)):02x}"
        except Exception:
            return hex_col


STYLE_PRESETS: dict[str, StylePreset] = {
    "realistic": StylePreset(
        id="realistic",
        name="Realistic",
        description="Natural lighting, volumetric chiaroscuro shading, smooth blending, true-to-life values",
        ai_guidance=(
            "ARTISTIC STYLE: REALISTIC / NATURALISTIC\n"
            "- Render the subject with authentic physical presence, accurate anatomical proportions, and three-dimensional volume.\n"
            "- Use chiaroscuro lighting: defined key light direction, soft core shadows, ambient bounce light, and subtle ambient occlusion.\n"
            "- Employ smooth value gradations, soft feathered transitions, naturalistic color temperatures, and fine specular glints.\n"
            "- Keep contours natural and integrated into the lighting rather than heavy artificial outlines."
        ),
        wobble=0.25,
        outline_hardness=0.85,
        outline_size_scale=0.9,
        wash_hardness=0.6,
        wash_opacity=0.9,
        color_mood="Naturalistic values, warm key light, cool ambient fill, volumetric chiaroscuro",
    ),
    "dreamlike": StylePreset(
        id="dreamlike",
        name="Dreamlike",
        description="Ethereal surrealism, glowing translucent washes, pastel & nebula tones, soft luminous halos",
        ai_guidance=(
            "ARTISTIC STYLE: DREAMLIKE / ETHEREAL SURREALISM\n"
            "- Infuse the scene with a surreal, luminous atmosphere, soft magical radiance, and dreamlike floating energy.\n"
            "- Use luminous ethereal palettes: glowing pastels, rich amethyst, iridescent turquoise, magenta, and celestial gold.\n"
            "- Apply soft, billowing, translucent brush washes with gentle atmospheric blending (hardness 0.3-0.5, opacity 0.6-0.8).\n"
            "- Include glowing edge rim-lights, floating particle starlight arcs, and shimmering specular aura glints."
        ),
        wobble=0.45,
        outline_hardness=0.45,
        outline_size_scale=0.8,
        wash_hardness=0.38,
        wash_opacity=0.75,
        color_mood="Ethereal pastels, iridescent cyan/violet/gold, luminous floating glow",
    ),
    "abstract": StylePreset(
        id="abstract",
        name="Abstract",
        description="Bold geometric & organic deconstructed planes, dynamic expressive angles, vibrant color contrast",
        ai_guidance=(
            "ARTISTIC STYLE: ABSTRACT / EXPRESSIONIST\n"
            "- Deconstruct the subject into expressive geometric planes, sweeping diagonal vectors, and bold color harmonies.\n"
            "- Use energetic, non-traditional color palettes with vibrant complementary clashes and bold focal blocks.\n"
            "- Favor dynamic angled brushstrokes, geometric polygons, intersecting rhythm lines, and rhythmic hatching bursts.\n"
            "- Emphasize visual motion, rhythm, and expressive graphic energy over photographic representation."
        ),
        wobble=0.6,
        outline_hardness=0.95,
        outline_size_scale=1.2,
        wash_hardness=0.85,
        wash_opacity=0.95,
        color_mood="Vibrant saturated clashes, high-contrast graphic planes, bold color pops",
    ),
    "sketchy": StylePreset(
        id="sketchy",
        name="Sketchy",
        description="Loose gestural graphite & charcoal pencil lines, directional cross-hatching, monochrome / sepia tones",
        ai_guidance=(
            "ARTISTIC STYLE: SKETCHY / GRAPHITE & CHARCOAL DRAFTING\n"
            "- Recreate an artist working with graphite pencils (2H, HB, 4B) and charcoal sticks on fine textured paper.\n"
            "- Keep pencil construction guides, gestural gesture ovals, tangent guide axes, and contour search lines visible.\n"
            "- Render shadows and volume using extensive directional cross-hatching and fine diagonal pencil strokes.\n"
            "- Use a monochromatic graphite, charcoal, or warm sepia palette (#1c2833, #566573, #7f8c8d, #a6acaf, #fdfefe paper)."
        ),
        wobble=0.75,
        outline_hardness=0.88,
        outline_size_scale=0.75,
        wash_hardness=0.5,
        wash_opacity=0.55,
        color_mood="Monochromatic graphite, warm sepia, raw paper backdrop, visible pencil hatching",
    ),
    "cartoon": StylePreset(
        id="cartoon",
        name="Cartoon",
        description="Vibrant cel-shaded animation, bold confident ink outlines, flat saturated colors, punchy highlight gleams",
        ai_guidance=(
            "ARTISTIC STYLE: CARTOON / ANIMATION CEL-SHADED\n"
            "- Recreate animation cel art with bold, confident ink contour outlines and punchy graphic clarity.\n"
            "- Use crisp, saturated, vibrant primary and secondary color fills with solid opacity (opacity 1.0, hardness 0.95).\n"
            "- Apply clear cel-shaded shadow bands with clean sharp cutlines rather than gradual gradients.\n"
            "- Use thick black ink outlines (size 5-8) and punchy crisp white specular highlight circles and dots."
        ),
        wobble=0.1,
        outline_hardness=1.0,
        outline_size_scale=1.35,
        wash_hardness=0.95,
        wash_opacity=1.0,
        color_mood="Vivid saturated primaries, crisp cel shadow bands, solid black outlines",
    ),
    "painterly": StylePreset(
        id="painterly",
        name="Painterly",
        description="Rich oil & acrylic impasto, expressive directional brushwork, textured color sweeps, warm/cool vibration",
        ai_guidance=(
            "ARTISTIC STYLE: PAINTERLY / OIL & IMPASTO\n"
            "- Recreate an expressive fine-art painting with visible textured brushstrokes and layered acrylic/oil pigment.\n"
            "- Use directional color sweeps following the organic form, with subtle warm/cool temperature vibrations across the surface.\n"
            "- Layer rich base washes, sculpted volumetric shadows, and expressive calligraphic brush contours.\n"
            "- Finish with confident impasto highlights and textured surface glints."
        ),
        wobble=0.4,
        outline_hardness=0.8,
        outline_size_scale=1.0,
        wash_hardness=0.6,
        wash_opacity=0.88,
        color_mood="Expressive impasto pigments, warm/cool temperature vibration, rich layered glazes",
    ),
}


def get_style(name: str | None) -> StylePreset:
    """Retrieve a style preset by name (case-insensitive), defaulting to 'realistic'."""
    if not name:
        return STYLE_PRESETS["realistic"]
    key = name.strip().lower()
    return STYLE_PRESETS.get(key, STYLE_PRESETS["realistic"])
