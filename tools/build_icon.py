"""Create the multi-resolution Windows icon used by the build pipeline."""

from pathlib import Path

from PIL import Image, ImageDraw


def render(size: int = 256) -> Image.Image:
    image = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(image)
    scale = size / 256
    draw.rounded_rectangle((5, 5, 251, 251), radius=52, fill="#07111F", outline="#28527E", width=max(2, int(5 * scale)))
    draw.rounded_rectangle((51, 59, 205, 166), radius=10, fill="#0B1A2B", outline="#9AC9FF", width=max(3, int(11 * scale)))
    draw.line((128, 172, 128, 202), fill="#4B9EFF", width=max(3, int(11 * scale)))
    draw.line((92, 204, 164, 204), fill="#4B9EFF", width=max(3, int(11 * scale)))
    return image


def main() -> None:
    output = Path(__file__).resolve().parent.parent / "build" / "monitor-dim-overlay.ico"
    output.parent.mkdir(parents=True, exist_ok=True)
    image = render()
    image.save(output, sizes=[(16, 16), (24, 24), (32, 32), (48, 48), (64, 64), (128, 128), (256, 256)])
    print(output)


if __name__ == "__main__":
    main()
