"""Artistic brush stroke generator: curves, sketching gestures, pressure curves, and painterly strokes."""

from __future__ import annotations

import math
import random
from typing import Sequence


def pressure_profile_swell(t: float) -> float:
    """Natural brush pressure: starts soft, swells to peak in middle, tapers at finish."""
    # Sine curve from 0 to pi gives 0.0 at ends, 1.0 in middle
    base = math.sin(t * math.pi)
    return round(0.25 + 0.75 * (base ** 0.8), 2)


def stroke_line(
    x1: float,
    y1: float,
    x2: float,
    y2: float,
    steps: int = 25,
    wobble: float = 0.5,
) -> list[list[float]]:
    """Generate a hand-drawn stroke between two points with natural wobble and pressure."""
    pts = []
    dx = x2 - x1
    dy = y2 - y1
    length = math.hypot(dx, dy)
    actual_steps = max(steps, int(length / 4.0))

    # Perpendicular vector for wobble
    if length > 0.001:
        nx = -dy / length
        ny = dx / length
    else:
        nx, ny = 0.0, 0.0

    for i in range(actual_steps + 1):
        t = i / actual_steps
        # Subtle organic curve (sine bow) + random hand jitter
        bow = math.sin(t * math.pi) * wobble
        noise = random.uniform(-wobble * 0.3, wobble * 0.3)
        offset = bow + noise

        px = x1 + dx * t + nx * offset
        py = y1 + dy * t + ny * offset
        pressure = pressure_profile_swell(t)
        pts.append([round(px, 1), round(py, 1), pressure])

    return pts


def stroke_bezier(
    p0: tuple[float, float],
    p1: tuple[float, float],
    p2: tuple[float, float],
    p3: tuple[float, float],
    steps: int = 35,
    wobble: float = 0.4,
) -> list[list[float]]:
    """Generate a smooth cubic Bezier stroke with pressure tapering."""
    pts = []
    for i in range(steps + 1):
        t = i / steps
        u = 1.0 - t
        tt = t * t
        uu = u * u
        uuu = uu * u
        ttt = tt * t

        # Cubic Bezier formula
        bx = uuu * p0[0] + 3 * uu * t * p1[0] + 3 * u * tt * p2[0] + ttt * p3[0]
        by = uuu * p0[1] + 3 * uu * t * p1[1] + 3 * u * tt * p2[1] + ttt * p3[1]

        jitter_x = random.uniform(-wobble, wobble)
        jitter_y = random.uniform(-wobble, wobble)
        pressure = pressure_profile_swell(t)

        pts.append([round(bx + jitter_x, 1), round(by + jitter_y, 1), pressure])

    return pts


def stroke_arc(
    cx: float,
    cy: float,
    rx: float,
    ry: float,
    start_deg: float,
    end_deg: float,
    steps: int = 40,
    wobble: float = 0.6,
) -> list[list[float]]:
    """Generate a curved elliptical arc stroke with hand dynamics."""
    pts = []
    start_rad = math.radians(start_deg)
    end_rad = math.radians(end_deg)
    angle_span = end_rad - start_rad

    for i in range(steps + 1):
        t = i / steps
        angle = start_rad + angle_span * t
        r_jitter = random.uniform(-wobble, wobble)

        px = cx + (rx + r_jitter) * math.cos(angle)
        py = cy + (ry + r_jitter) * math.sin(angle)
        pressure = pressure_profile_swell(t)

        pts.append([round(px, 1), round(py, 1), pressure])

    return pts


def stroke_sketch_oval(
    cx: float,
    cy: float,
    rx: float,
    ry: float,
    tilt_deg: float = 0.0,
    passes: float = 1.15,
    steps: int = 60,
    wobble: float = 0.8,
) -> list[list[float]]:
    """Simulate a human artist sketching an oval/circle gesture (overlapping loop)."""
    pts = []
    total_angle = 2 * math.pi * passes
    rad_tilt = math.radians(tilt_deg)
    cos_t = math.cos(rad_tilt)
    sin_t = math.sin(rad_tilt)

    actual_steps = int(steps * passes)
    for i in range(actual_steps + 1):
        t = i / actual_steps
        angle = t * total_angle
        # Hand wobble variance increases towards the tail
        current_wobble = wobble * (1.0 + 0.3 * math.sin(t * 8))

        ox = rx * math.cos(angle) + random.uniform(-current_wobble, current_wobble)
        oy = ry * math.sin(angle) + random.uniform(-current_wobble, current_wobble)

        # Rotate by tilt
        px = cx + (ox * cos_t - oy * sin_t)
        py = cy + (ox * sin_t + oy * cos_t)

        # Pressure swells and tapers
        pressure = round(0.4 + 0.5 * math.sin(t * math.pi * 1.5), 2)
        pressure = max(0.2, min(0.95, pressure))

        pts.append([round(px, 1), round(py, 1), pressure])

    return pts


def stroke_painterly_fill(
    cx: float,
    cy: float,
    rx: float,
    ry: float,
    spacing: float = 24.0,
    angle_deg: float = 10.0,
) -> list[list[list[float]]]:
    """Generate multiple sweeping brush strokes that paint in an area with organic coverage."""
    strokes = []
    rad = math.radians(angle_deg)
    cos_a = math.cos(rad)
    sin_a = math.sin(rad)

    # Sweep from top to bottom of the ellipse
    y_min = -ry * 0.9
    y_max = ry * 0.9
    curr_y = y_min

    left_to_right = True
    while curr_y <= y_max:
        # Width of ellipse at curr_y
        normalized_y = curr_y / ry
        if abs(normalized_y) < 0.98:
            half_w = rx * math.sqrt(1.0 - normalized_y * normalized_y) * 0.95
            if half_w > 4.0:
                p_start = (-half_w, curr_y) if left_to_right else (half_w, curr_y)
                p_end = (half_w, curr_y) if left_to_right else (-half_w, curr_y)

                # Rotate and translate
                x1 = cx + (p_start[0] * cos_a - p_start[1] * sin_a)
                y1 = cy + (p_start[0] * sin_a + p_start[1] * cos_a)
                x2 = cx + (p_end[0] * cos_a - p_end[1] * sin_a)
                y2 = cy + (p_end[0] * sin_a + p_end[1] * cos_a)

                # Create sweeping curve with slight bow
                mid_x = (x1 + x2) * 0.5 + random.uniform(-3, 3)
                mid_y = (y1 + y2) * 0.5 + random.uniform(-2, 4)

                stroke = stroke_bezier(
                    (x1, y1),
                    ((x1 + mid_x) * 0.5, (y1 + mid_y) * 0.5),
                    ((mid_x + x2) * 0.5, (mid_y + y2) * 0.5),
                    (x2, y2),
                    steps=18,
                    wobble=0.8,
                )
                strokes.append(stroke)
                left_to_right = not left_to_right

        curr_y += spacing

    return strokes


def stroke_hatching(
    cx: float,
    cy: float,
    w: float,
    h: float,
    count: int = 6,
    angle_deg: float = 45.0,
) -> list[list[list[float]]]:
    """Generate rhythmic cross-hatch shading strokes."""
    strokes = []
    step_x = w / (count + 1)
    for i in range(1, count + 1):
        sx = cx - w * 0.5 + i * step_x + random.uniform(-2, 2)
        sy = cy - h * 0.4 + random.uniform(-3, 3)
        ex = sx + h * 0.6 * math.tan(math.radians(angle_deg * 0.4))
        ey = cy + h * 0.4 + random.uniform(-3, 3)
        strokes.append(stroke_line(sx, sy, ex, ey, steps=12, wobble=0.4))
    return strokes


def smooth_path(coarse_points: Sequence[Sequence[float]], samples_per_segment: int = 8) -> list[list[float]]:
    """Take coarse waypoints and generate a silky smooth Catmull-Rom stroke with pressure."""
    if len(coarse_points) < 2:
        return [[float(p[0]), float(p[1]), 0.8] for p in coarse_points]

    pts = [[float(p[0]), float(p[1])] for p in coarse_points]
    total_segments = len(pts) - 1
    result: list[list[float]] = []

    for seg in range(total_segments):
        p0 = pts[max(0, seg - 1)]
        p1 = pts[seg]
        p2 = pts[seg + 1]
        p3 = pts[min(total_segments, seg + 2)]

        for i in range(samples_per_segment):
            t = i / samples_per_segment
            global_t = (seg + t) / total_segments
            t2 = t * t
            t3 = t2 * t

            # Catmull-Rom spline formula
            x = 0.5 * (
                (2 * p1[0])
                + (-p0[0] + p2[0]) * t
                + (2 * p0[0] - 5 * p1[0] + 4 * p2[0] - p3[0]) * t2
                + (-p0[0] + 3 * p1[0] - 3 * p2[0] + p3[0]) * t3
            )
            y = 0.5 * (
                (2 * p1[1])
                + (-p0[1] + p2[1]) * t
                + (2 * p0[1] - 5 * p1[1] + 4 * p2[1] - p3[1]) * t2
                + (-p0[1] + 3 * p1[1] - 3 * p2[1] + p3[1]) * t3
            )
            pressure = pressure_profile_swell(global_t)
            result.append([round(x, 1), round(y, 1), pressure])

    last_p = pts[-1]
    result.append([round(last_p[0], 1), round(last_p[1], 1), 0.3])
    return result
