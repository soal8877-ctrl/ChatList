"""Генерация app.ico со случайными фигурами разных цветов."""

from __future__ import annotations

import math
import random
from typing import Callable

from PIL import Image, ImageDraw

SIZES = [(256, 256), (128, 128), (64, 64), (48, 48), (32, 32), (16, 16)]


def _random_color(rng: random.Random) -> tuple[int, int, int]:
    return (
        rng.randint(30, 255),
        rng.randint(30, 255),
        rng.randint(30, 255),
    )


def _scale(value: float, size: int) -> int:
    return int(value * size)


def _bbox(
    rng: random.Random,
    size: int,
    *,
    min_span: float = 0.15,
    max_left: float = 0.75,
) -> tuple[int, int, int, int]:
    x1 = _scale(rng.uniform(0.0, max_left), size)
    y1 = _scale(rng.uniform(0.0, max_left), size)
    x2 = _scale(rng.uniform(min_span, 1.0), size)
    y2 = _scale(rng.uniform(min_span, 1.0), size)
    return min(x1, x2), min(y1, y2), max(x1, x2), max(y1, y2)


def _draw_ellipse(
    draw: ImageDraw.ImageDraw,
    rng: random.Random,
    size: int,
    color: tuple[int, int, int],
) -> None:
    draw.ellipse(
        list(_bbox(rng, size)),
        fill=color,
        outline=_random_color(rng),
        width=max(1, size // 64),
    )


def _draw_rectangle(
    draw: ImageDraw.ImageDraw,
    rng: random.Random,
    size: int,
    color: tuple[int, int, int],
) -> None:
    draw.rectangle(
        list(_bbox(rng, size)),
        fill=color,
        outline=_random_color(rng),
        width=max(1, size // 64),
    )


def _draw_polygon(
    draw: ImageDraw.ImageDraw,
    rng: random.Random,
    size: int,
    color: tuple[int, int, int],
) -> None:
    sides = rng.randint(3, 7)
    cx = rng.uniform(0.2, 0.8)
    cy = rng.uniform(0.2, 0.8)
    radius = rng.uniform(0.08, 0.28)
    points: list[tuple[int, int]] = []
    for index in range(sides):
        angle = (2 * 3.14159265 * index / sides) + rng.uniform(-0.3, 0.3)
        x = cx + radius * math.cos(angle)
        y = cy + radius * math.sin(angle)
        points.append((_scale(x, size), _scale(y, size)))
    draw.polygon(points, fill=color, outline=_random_color(rng))


def _draw_line(
    draw: ImageDraw.ImageDraw,
    rng: random.Random,
    size: int,
    color: tuple[int, int, int],
) -> None:
    x1 = _scale(rng.uniform(0.0, 1.0), size)
    y1 = _scale(rng.uniform(0.0, 1.0), size)
    x2 = _scale(rng.uniform(0.0, 1.0), size)
    y2 = _scale(rng.uniform(0.0, 1.0), size)
    draw.line([x1, y1, x2, y2], fill=color, width=max(2, size // 32))


def _draw_arc(
    draw: ImageDraw.ImageDraw,
    rng: random.Random,
    size: int,
    color: tuple[int, int, int],
) -> None:
    x1, y1, x2, y2 = _bbox(rng, size, min_span=0.2, max_left=0.6)
    start = rng.randint(0, 180)
    end = start + rng.randint(60, 270)
    draw.arc([x1, y1, x2, y2], start=start, end=end, fill=color, width=max(2, size // 32))


SHAPE_DRAWERS: list[Callable[[ImageDraw.ImageDraw, random.Random, int, tuple[int, int, int]], None]] = [
    _draw_ellipse,
    _draw_rectangle,
    _draw_polygon,
    _draw_line,
    _draw_arc,
]


def draw_icon(size: int, seed: int | None = None) -> Image.Image:
    """Рисует иконку со случайными фигурами разных цветов."""
    rng = random.Random(seed)
    background = _random_color(rng)
    img = Image.new("RGB", (size, size), background)
    draw = ImageDraw.Draw(img)

    shape_count = rng.randint(6, 14)
    for _ in range(shape_count):
        color = _random_color(rng)
        drawer = rng.choice(SHAPE_DRAWERS)
        drawer(draw, rng, size, color)

    return img


def main() -> None:
    seed = random.randint(0, 2**32 - 1)
    icons = [draw_icon(size, seed=seed) for size, _ in SIZES]

    rgb_icons: list[Image.Image] = []
    for icon in icons:
        rgb_icons.append(icon if icon.mode == "RGB" else icon.convert("RGB"))

    try:
        rgb_icons[0].save(
            "app.ico",
            format="ICO",
            sizes=SIZES,
            append_images=rgb_icons[1:],
        )
        print("Иконка 'app.ico' создана.")
        print(f"  Seed: {seed}")
        print("  Дизайн: случайные фигуры разных цветов")
        print("  Фигуры: круг/овал, прямоугольник, многоугольник, линия, дуга")
    except Exception as exc:
        print(f"Ошибка при сохранении: {exc}")
        print("Попытка альтернативного метода сохранения...")
        rgb_icons[0].save("app.ico", format="ICO")
        print("Иконка 'app.ico' создана (только один размер)")


if __name__ == "__main__":
    main()
