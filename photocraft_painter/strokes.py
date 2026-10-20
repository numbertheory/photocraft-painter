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
    """Take coarse waypoints and generate a silky smooth Catmull-Rom stroke with pressure.
    
    If the waypoints form a closed loop (start and end points meet), the curve is wrapped cyclically
    with solid boundary pressure and closure overlap to guarantee a watertight barrier for paint bucket fills.
    """
    if len(coarse_points) < 2:
        return [[float(p[0]), float(p[1]), 0.8] for p in coarse_points]

    pts = [[float(p[0]), float(p[1])] for p in coarse_points]
    is_closed = (
        len(pts) >= 4
        and math.hypot(pts[0][0] - pts[-1][0], pts[0][1] - pts[-1][1]) < 15.0
    )
    if is_closed:
        pts[-1] = [pts[0][0], pts[0][1]]

    # Soften sharp angular corners on coarse waypoints so organic contours (heads, faces, eyes,
    # torsos, limbs, fish, trees) curve smoothly like in nature instead of looking polygonal.
    if len(pts) <= 28:
        seg_dists = [
            math.hypot(pts[i + 1][0] - pts[i][0], pts[i + 1][1] - pts[i][1])
            for i in range(len(pts) - 1)
        ]
        avg_seg = sum(seg_dists) / max(1, len(seg_dists))
        if avg_seg >= 8.0:
            if is_closed and len(pts) >= 4:
                ring = pts[:-1]
                n_ring = len(ring)
                if n_ring >= 3:
                    smoothed_ring: list[list[float]] = []
                    for i in range(n_ring):
                        p_prev = ring[(i - 1) % n_ring]
                        p_curr = ring[i]
                        p_next = ring[(i + 1) % n_ring]
                        sx = 0.70 * p_curr[0] + 0.15 * p_prev[0] + 0.15 * p_next[0]
                        sy = 0.70 * p_curr[1] + 0.15 * p_prev[1] + 0.15 * p_next[1]
                        smoothed_ring.append([sx, sy])
                    pts = smoothed_ring + [[smoothed_ring[0][0], smoothed_ring[0][1]]]
            elif not is_closed and len(pts) >= 3:
                smoothed_open: list[list[float]] = [pts[0]]
                for i in range(1, len(pts) - 1):
                    p_prev = pts[i - 1]
                    p_curr = pts[i]
                    p_next = pts[i + 1]
                    sx = 0.72 * p_curr[0] + 0.14 * p_prev[0] + 0.14 * p_next[0]
                    sy = 0.72 * p_curr[1] + 0.14 * p_prev[1] + 0.14 * p_next[1]
                    smoothed_open.append([sx, sy])
                smoothed_open.append(pts[-1])
                pts = smoothed_open

    total_segments = len(pts) - 1
    result: list[list[float]] = []

    for seg in range(total_segments):
        if is_closed:
            p0 = pts[-2] if seg == 0 else pts[seg - 1]
            p1 = pts[seg]
            p2 = pts[seg + 1]
            p3 = pts[1] if seg + 1 == total_segments else (pts[seg + 2] if seg + 2 < len(pts) else pts[0])
        else:
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
            pressure = 0.9 if is_closed else pressure_profile_swell(global_t)
            result.append([round(x, 1), round(y, 1), pressure])

    last_p = pts[-1]
    if is_closed:
        # Guarantee exact seal by touching start point and overlapping 2 extra points
        result.append([round(pts[0][0], 1), round(pts[0][1], 1), 0.95])
        if len(result) > 4:
            result.append([result[1][0], result[1][1], 0.95])
            result.append([result[2][0], result[2][1], 0.95])
    else:
        result.append([round(last_p[0], 1), round(last_p[1], 1), 0.3])
    return result


def stroke_enclosed_loop(
    waypoints: Sequence[Sequence[float]],
    steps_per_segment: int = 15,
    linear: bool = False,
) -> list[list[float]]:
    """Generate a watertight closed bounding contour where points[0] seamlessly closes into points[-1].
    
    By default, coarse waypoints (<= 40 points) are first curved with a smooth Catmull-Rom spline
    so organic subjects (faces, bodies, ears, fins, trees) have natural curved contours rather than
    straight polygon edges. Pass linear=True when sharp straight edges are desired (e.g. rectangles).
    Guarantees that boundaries are completely enclosed with dense sampling and overlap
    so flood fill (paint.bucket) will not leak.
    """
    if len(waypoints) < 3:
        return []

    pts = [[float(p[0]), float(p[1])] for p in waypoints]
    # Ensure closed
    if math.hypot(pts[0][0] - pts[-1][0], pts[0][1] - pts[-1][1]) > 0.001:
        pts.append([pts[0][0], pts[0][1]])

    if not linear and len(pts) <= 40:
        curved = smooth_path(pts, samples_per_segment=6)
        pts = [[float(p[0]), float(p[1])] for p in curved]
        if math.hypot(pts[0][0] - pts[-1][0], pts[0][1] - pts[-1][1]) > 0.001:
            pts.append([pts[0][0], pts[0][1]])

    result: list[list[float]] = []
    n = len(pts) - 1
    for seg in range(n):
        p1 = pts[seg]
        p2 = pts[seg + 1]
        dx = p2[0] - p1[0]
        dy = p2[1] - p1[1]
        dist = math.hypot(dx, dy)
        actual_steps = max(2 if not linear else steps_per_segment, int(dist / 1.5))
        for step in range(actual_steps):
            t = step / actual_steps
            px = p1[0] + dx * t
            py = p1[1] + dy * t
            result.append([round(px, 1), round(py, 1), 1.0])

    # Overlap past the start point by 3 samples to seal any sub-pixel raster gaps
    start_x, start_y = pts[0][0], pts[0][1]
    result.append([round(start_x, 1), round(start_y, 1), 1.0])
    if len(result) > 4:
        result.append([result[1][0], result[1][1], 1.0])
        result.append([result[2][0], result[2][1], 1.0])

    return result


def stroke_enclosed_rect(
    x: float,
    y: float,
    w: float,
    h: float,
    steps_per_side: int = 15,
) -> list[list[float]]:
    """Generate a strictly watertight closed rectangular bounding box."""
    c0 = (x, y)
    c1 = (x + w, y)
    c2 = (x + w, y + h)
    c3 = (x, y + h)
    return stroke_enclosed_loop([c0, c1, c2, c3], steps_per_segment=steps_per_side, linear=True)


def stroke_enclosed_oval(
    cx: float,
    cy: float,
    rx: float,
    ry: float,
    tilt_deg: float = 0.0,
    steps: int = 72,
) -> list[list[float]]:
    """Generate a watertight closed elliptical boundary."""
    pts: list[tuple[float, float]] = []
    rad_tilt = math.radians(tilt_deg)
    cos_t = math.cos(rad_tilt)
    sin_t = math.sin(rad_tilt)

    for i in range(steps):
        angle = (i / steps) * 2 * math.pi
        ox = rx * math.cos(angle)
        oy = ry * math.sin(angle)
        px = cx + (ox * cos_t - oy * sin_t)
        py = cy + (ox * sin_t + oy * cos_t)
        pts.append((px, py))

    return stroke_enclosed_loop(pts, steps_per_segment=2)


def stroke_polygon(
    vertices: Sequence[Sequence[float]],
    wobble: float = 0.0,
    steps_per_side: int = 15,
    closed: bool = True,
) -> list[list[float]]:
    """Generate a crisp, straight-edged geometric polygon stroke with sharp vertices.

    Linearly interpolates between each vertex to guarantee flat, straight edges and sharp corners.
    Never curves or bows the sides like a Catmull-Rom spline, strictly avoiding 'gum drop' rounding.
    Watertight overlap is applied at vertices so flood fill (paint.bucket) never leaks.
    """
    if len(vertices) < 2:
        return [[float(v[0]), float(v[1]), 1.0] for v in vertices]

    pts = [[float(v[0]), float(v[1])] for v in vertices]
    if closed and (len(pts) < 3 or math.hypot(pts[0][0] - pts[-1][0], pts[0][1] - pts[-1][1]) > 0.001):
        pts.append([pts[0][0], pts[0][1]])

    result: list[list[float]] = []
    n = len(pts) - 1
    for seg in range(n):
        p1 = pts[seg]
        p2 = pts[seg + 1]
        dx = p2[0] - p1[0]
        dy = p2[1] - p1[1]
        dist = math.hypot(dx, dy)
        actual_steps = max(steps_per_side, int(dist / 1.5))

        if dist > 0.001 and wobble > 0.001:
            nx = -dy / dist
            ny = dx / dist
        else:
            nx, ny = 0.0, 0.0

        for step in range(actual_steps):
            t = step / actual_steps
            px = p1[0] + dx * t
            py = p1[1] + dy * t

            if wobble > 0.001:
                jitter = random.uniform(-wobble * 0.4, wobble * 0.4)
                px += nx * jitter
                py += ny * jitter

            result.append([round(px, 1), round(py, 1), 1.0])

    if closed and len(result) > 4:
        result.append([round(pts[0][0], 1), round(pts[0][1], 1), 1.0])
        result.append([result[1][0], result[1][1], 1.0])
        result.append([result[2][0], result[2][1], 1.0])
    elif not closed and pts:
        result.append([round(pts[-1][0], 1), round(pts[-1][1], 1), 1.0])

    return result


def stroke_regular_polygon_vertices(
    cx: float,
    cy: float,
    radius: float,
    sides: int = 3,
    orientation_deg: float = 0.0,
) -> list[list[float]]:
    """Calculate the exact Cartesian vertices of a regular polygon with `sides` (sides >= 3).

    For a triangle (sides=3), first vertex is at the top (apex), followed by bottom-right and bottom-left.
    """
    sides = max(3, int(sides))
    rad_offset = math.radians(orientation_deg) - math.pi / 2.0
    angle_step = 2.0 * math.pi / sides

    vertices: list[list[float]] = []
    for i in range(sides):
        ang = rad_offset + i * angle_step
        vx = cx + radius * math.cos(ang)
        vy = cy + radius * math.sin(ang)
        vertices.append([round(vx, 1), round(vy, 1)])
    return vertices


def stroke_triangle(
    cx: float,
    cy: float,
    radius: float,
    orientation_deg: float = 0.0,
    wobble: float = 0.0,
    steps_per_side: int = 20,
) -> list[list[float]]:
    """Generate a watertight 3-sided triangle polygon with straight sides and sharp vertices."""
    verts = stroke_regular_polygon_vertices(cx, cy, radius, sides=3, orientation_deg=orientation_deg)
    return stroke_polygon(verts, wobble=wobble, steps_per_side=steps_per_side, closed=True)


def stroke_sketchy_polygon_lines(
    vertices: Sequence[Sequence[float]],
    overshoot: float = 14.0,
    wobble: float = 0.35,
) -> list[list[list[float]]]:
    """Generate authentic drafting pencil strokes for a polygon with visible corner extensions.

    Real artists and architectural draftsmen sketch triangles and geometric shapes with straight lines
    that overshoot the vertices slightly, giving an unmistakable classical sketched look.
    """
    pts = [[float(v[0]), float(v[1])] for v in vertices]
    if len(pts) < 3:
        return []

    strokes: list[list[list[float]]] = []
    n = len(pts)
    for i in range(n):
        p1 = pts[i]
        p2 = pts[(i + 1) % n]
        dx = p2[0] - p1[0]
        dy = p2[1] - p1[1]
        dist = math.hypot(dx, dy)
        if dist < 1.0:
            continue

        ux = dx / dist
        uy = dy / dist

        # Line 1: Main edge with overshoot past both corners
        sx = p1[0] - ux * overshoot
        sy = p1[1] - uy * overshoot
        ex = p2[0] + ux * overshoot
        ey = p2[1] + uy * overshoot
        strokes.append(stroke_line(sx, sy, ex, ey, steps=25, wobble=wobble))

        # Line 2: Subtle secondary drafting search line
        sx2 = p1[0] - ux * (overshoot * 0.5) + random.uniform(-1.0, 1.0)
        sy2 = p1[1] - uy * (overshoot * 0.5) + random.uniform(-1.0, 1.0)
        ex2 = p2[0] + ux * (overshoot * 0.7) + random.uniform(-1.0, 1.0)
        ey2 = p2[1] + uy * (overshoot * 0.7) + random.uniform(-1.0, 1.0)
        strokes.append(stroke_line(sx2, sy2, ex2, ey2, steps=20, wobble=wobble * 1.2))

    return strokes
