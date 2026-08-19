#!/usr/bin/env python
"""Генерация PWA-иконок из фирменного знака (капля на скруглённом фоне).

Создаёт PNG-иконки нужных размеров в app/static/icons/. Запускается локально
один раз; сгенерированные файлы коммитятся как статические ассеты. Pillow нужен
только для генерации и НЕ входит в рантайм-зависимости.

Использование: python -m tools.gen_icons
"""
from __future__ import annotations

import os

from PIL import Image, ImageDraw

OUT = "app/static/icons"
BRAND = (3, 105, 161, 255)      # #0369a1
WHITE = (255, 255, 255, 255)
SCALE = 4                        # супер-сэмплинг для гладких краёв


def _draw_drop(draw: ImageDraw.ImageDraw, cx: float, cy: float, s: float) -> None:
    """Рисует стилизованную каплю воды (как в favicon), центр (cx,cy), масштаб s."""
    # Капля: круг снизу + треугольная вершина.
    top = (cx, cy - 1.15 * s)
    left = (cx - 0.95 * s, cy + 0.25 * s)
    right = (cx + 0.95 * s, cy + 0.25 * s)
    draw.polygon([top, left, right], fill=WHITE)
    draw.ellipse(
        [cx - 0.95 * s, cy - 0.55 * s, cx + 0.95 * s, cy + 1.15 * s],
        fill=WHITE,
    )


def make_icon(size: int, maskable: bool = False, transparent_bg: bool = False) -> Image.Image:
    S = size * SCALE
    img = Image.new("RGBA", (S, S), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)

    if not transparent_bg:
        radius = int(S * (0.5 if maskable else 0.22))
        draw.rounded_rectangle([0, 0, S - 1, S - 1], radius=radius, fill=BRAND)

    # Для maskable оставляем безопасную зону: капля меньше (в центральных ~66%).
    drop_scale = S * (0.24 if maskable else 0.30)
    _draw_drop(draw, S / 2, S / 2 + S * 0.03, drop_scale)

    return img.resize((size, size), Image.LANCZOS)


def main() -> None:
    os.makedirs(OUT, exist_ok=True)
    targets = [
        ("icon-192.png", 192, False, False),
        ("icon-512.png", 512, False, False),
        ("icon-maskable-192.png", 192, True, False),
        ("icon-maskable-512.png", 512, True, True),  # maskable без своего фона? нет — с фоном
        ("apple-touch-icon.png", 180, False, False),
        ("icon-256.png", 256, False, False),
    ]
    # Поправка: maskable-512 должен иметь фон (иначе прозрачные углы).
    for name, size, maskable, _bad in targets:
        transparent = False
        img = make_icon(size, maskable=maskable, transparent_bg=transparent)
        img.save(os.path.join(OUT, name))
        print("wrote", os.path.join(OUT, name), f"{size}x{size}")


if __name__ == "__main__":
    main()
