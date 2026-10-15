"""Artistic style definitions and aesthetic presets for PhotoCraft Painter.

Provides overarching art styles (realistic, dreamlike, abstract, sketchy, cartoon, painterly, cubism, pencil)
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
            elif self.id == "cubism":
                # Earthy analytical cubism palette: ochre, sienna, slate, and heightened facet relief chiaroscuro
                gray = int(0.299 * r + 0.587 * g + 0.114 * b)
                r_c = int(min(255, (r * 0.6 + gray * 0.4 + 18) * (1.18 if gray > 120 else 0.82)) * factor)
                g_c = int(min(255, (g * 0.55 + gray * 0.4 + 8) * (1.12 if gray > 120 else 0.80)) * factor)
                b_c = int(min(255, (b * 0.42 + gray * 0.4) * (1.05 if gray > 120 else 0.78)) * factor)
                r, g, b = r_c, g_c, b_c
            elif self.id == "pencil":
                # Pure monochromatic graphite pencil tones: map luminance to medium-light graphite range
                gray = int(0.299 * r + 0.587 * g + 0.114 * b)
                graphite = int(45 + (gray / 255.0) * 145)
                r = int(graphite * factor)
                g = int(graphite * factor)
                b = int(min(255, graphite + 2) * factor)
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
    "cubism": StylePreset(
        id="cubism",
        name="Cubism",
        description="Deconstructed multi-perspective planar facets, angular geometric 3D relief, and interlocking analytical planes leaping off the canvas",
        ai_guidance=(
            "ARTISTIC STYLE: CUBISM (ANALYTICAL & SYNTHETIC CUBISM)\n"
            "- Deconstruct subjects into interpenetrating geometric planes, polyhedral facets, and angular shards.\n"
            "- Break free from single-point perspective: depict the subject from MULTIPLE PERSPECTIVES simultaneously (e.g. interlocking profile and frontal views of faces, simultaneous top and side views of objects).\n"
            "- Use very angular, sharp edges: faceted polygons, intersecting diagonal planes, triangles, trapezoids, and geometric bevels.\n"
            "- Render facets with high value and temperature contrast (light warm facet next to deep cool shadow facet) so 3D objects dramatically leap off the 2D surface.\n"
            "- Palette: Earthy analytical ochre, raw sienna, burnt umber, charcoal, slate gray, and muted olive, accented with synthetic pops of terracotta, cadmium yellow, or cobalt.\n"
            "- Emphasize intersecting structural lines, transparent overlapping planes, and faceted architectural geometry."
        ),
        wobble=0.1,
        outline_hardness=0.98,
        outline_size_scale=1.2,
        wash_hardness=0.92,
        wash_opacity=0.95,
        color_mood="Earthy ochre, warm terracotta, slate gray, burnt umber, and high-contrast volumetric facet lighting",
    ),
    "pencil": StylePreset(
        id="pencil",
        name="Pencil",
        description="Animation style pencil test roughs: light graphite pencil strokes, minimal cross-hatching, no hard ink or paint, single drawing layer",
        ai_guidance=(
            "ARTISTIC STYLE: PENCIL (ANIMATION PENCIL TEST / ROUGHS)\n"
            "- Recreate an authentic animation studio pencil test drawing (rough keyframe animation drawings on animation paper).\n"
            "- Use ONLY light, delicate brush strokes of a graphite pencil (2H, HB, 2B pencil lead).\n"
            "- ABSOLUTELY NO hard inked lines, heavy solid black ink contours, or marker outlines.\n"
            "- ABSOLUTELY NO paint fills, paint bucket fills, solid color washes, or digital airbrush gradients.\n"
            "- Keep shading to an absolute minimum: NO paint blending. Volume and form must be suggested ONLY through light, directional cross-hatching and diagonal pencil strokes.\n"
            "- Loose construction guides, gestural rough circles, action lines, and motion rhythms are encouraged to give the authentic feel of a hand-drawn animation pencil test.\n"
            "- Palette: Pure graphite pencil tones (#2d3436, #4b5563, #6b7280, #9ca3af) on clean white/off-white animation paper (#ffffff or #fdfefe).\n"
            "- The entire finished drawing exists as a single transparent drawing layer above the background."
        ),
        wobble=0.32,
        outline_hardness=0.65,
        outline_size_scale=0.65,
        wash_hardness=0.55,
        wash_opacity=0.45,
        color_mood="Monochromatic graphite pencil (#2d3436, #4b5563, #718096), clean white animation paper, delicate cross-hatching, no paint",
    ),
}


def get_style(name: str | None) -> StylePreset:
    """Retrieve a style preset by name (case-insensitive), defaulting to 'realistic'."""
    if not name:
        return STYLE_PRESETS["realistic"]
    key = name.strip().lower()
    return STYLE_PRESETS.get(key, STYLE_PRESETS["realistic"])
