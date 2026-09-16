"""Draw the sample sketch in samples/sketch.jpg. Run it again only to redraw the sample."""

import random
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

WIDTH, HEIGHT = 1600, 2000
PAPER = (246, 243, 236)
INK = (58, 58, 64)
FONT_PATHS = ("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",)


def font(size: int):
    for path in FONT_PATHS:
        if Path(path).is_file():
            return ImageFont.truetype(path, size)
    return ImageFont.load_default(size)


def wobble(draw, points, width=7):
    jittered = [(x + random.uniform(-6, 6), y + random.uniform(-6, 6)) for x, y in points]
    draw.line(jittered, fill=INK, width=width, joint="curve")


def box(draw, left, top, right, bottom):
    corners = [(left, top), (right, top), (right, bottom), (left, bottom), (left, top)]
    for start, end in zip(corners, corners[1:]):
        steps = 6
        points = [
            (start[0] + (end[0] - start[0]) * step / steps, start[1] + (end[1] - start[1]) * step / steps)
            for step in range(steps + 1)
        ]
        wobble(draw, points)


def text(draw, position, value, size):
    draw.text(position, value, font=font(size), fill=INK)


def rule(draw, left, right, y, width=6):
    wobble(draw, [(left, y), ((left + right) / 2, y), (right, y)], width)


def main() -> None:
    random.seed(11)
    image = Image.new("RGB", (WIDTH, HEIGHT), PAPER)
    draw = ImageDraw.Draw(image)

    box(draw, 120, 120, 1480, 320)
    text(draw, (200, 185), "HEADER", 90)
    rule(draw, 900, 1400, 220, 5)

    box(draw, 120, 380, 1480, 900)
    text(draw, (200, 470), "BIG TITLE", 120)
    for offset in range(3):
        rule(draw, 200, 1180 - offset * 120, 650 + offset * 55)
    box(draw, 200, 790, 580, 880)
    text(draw, (245, 805), "BUTTON", 55)

    for index in range(3):
        left = 120 + index * 460
        box(draw, left, 980, left + 400, 1500)
        text(draw, (left + 60, 1040), f"CARD {index + 1}", 70)
        for line in range(4):
            rule(draw, left + 60, left + 340 - line * 40, 1200 + line * 70, 5)

    box(draw, 120, 1580, 1480, 1820)
    text(draw, (200, 1650), "FOOTER", 80)
    rule(draw, 200, 1400, 1760, 5)

    target = Path(__file__).resolve().parent.parent / "samples" / "sketch.jpg"
    target.parent.mkdir(parents=True, exist_ok=True)
    image.save(target, format="JPEG", quality=88)
    print(f"Wrote {target} ({target.stat().st_size} bytes)")


if __name__ == "__main__":
    main()
