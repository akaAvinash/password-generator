"""Generates assets/icon.ico — a simple padlock glyph — for the packaged app.

Run once (or whenever the icon design changes):
    python build_tools/make_icon.py
"""

from pathlib import Path

from PIL import Image, ImageDraw

OUT_DIR = Path(__file__).resolve().parent.parent / "assets"
OUT_DIR.mkdir(exist_ok=True)

SIZE = 256
BG = (30, 32, 40, 255)
ACCENT = (124, 92, 255, 255)
BODY = (240, 240, 245, 255)


def draw_lock(size: int) -> Image.Image:
    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)

    margin = size * 0.08
    draw.rounded_rectangle(
        [margin, margin, size - margin, size - margin],
        radius=size * 0.22,
        fill=BG,
    )

    cx, cy = size / 2, size * 0.56
    body_w, body_h = size * 0.46, size * 0.34
    draw.rounded_rectangle(
        [cx - body_w / 2, cy - body_h / 2, cx + body_w / 2, cy + body_h / 2],
        radius=size * 0.06,
        fill=ACCENT,
    )

    shackle_r = size * 0.16
    shackle_top = cy - body_h / 2 - shackle_r
    draw.arc(
        [cx - shackle_r, shackle_top - shackle_r, cx + shackle_r, shackle_top + shackle_r],
        start=180, end=360, fill=BODY, width=int(size * 0.045),
    )
    draw.line(
        [cx - shackle_r, shackle_top, cx - shackle_r, cy - body_h / 2 + 2],
        fill=BODY, width=int(size * 0.045),
    )
    draw.line(
        [cx + shackle_r, shackle_top, cx + shackle_r, cy - body_h / 2 + 2],
        fill=BODY, width=int(size * 0.045),
    )

    keyhole_r = size * 0.045
    draw.ellipse(
        [cx - keyhole_r, cy - keyhole_r * 1.3, cx + keyhole_r, cy + keyhole_r * 0.7],
        fill=BG,
    )
    draw.polygon(
        [
            (cx - keyhole_r * 0.5, cy),
            (cx + keyhole_r * 0.5, cy),
            (cx + keyhole_r * 0.9, cy + keyhole_r * 1.8),
            (cx - keyhole_r * 0.9, cy + keyhole_r * 1.8),
        ],
        fill=BG,
    )

    return img


def main():
    base = draw_lock(SIZE)
    ico_path = OUT_DIR / "icon.ico"
    base.save(ico_path, format="ICO", sizes=[(16, 16), (32, 32), (48, 48), (64, 64), (128, 128), (256, 256)])
    print(f"Wrote {ico_path}")


if __name__ == "__main__":
    main()
