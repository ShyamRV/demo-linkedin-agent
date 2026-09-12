import os
from io import BytesIO
from pathlib import Path
from typing import List, Optional, Tuple

from PIL import Image, ImageDraw, ImageEnhance, ImageFilter, ImageFont


POSTER_SIZE = 1200
CREAM = (247, 250, 252, 255)
TEAL = (64, 224, 208, 255)
MUTED = (210, 222, 232, 255)
GOLD = (247, 201, 108, 255)


def _windows_fonts() -> Path:
    return Path(os.environ.get("WINDIR", r"C:\Windows")) / "Fonts"


def _font_path(names: List[str]) -> Optional[Path]:
    folders = [
        _windows_fonts(),
        Path("/System/Library/Fonts"),
        Path("/Library/Fonts"),
        Path("/usr/share/fonts/truetype/dejavu"),
        Path("/usr/share/fonts/truetype"),
    ]
    for folder in folders:
        for name in names:
            candidate = folder / name
            if candidate.exists():
                return candidate
    return None


def load_font(size: int, bold: bool = False) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    names = (
        [
            "segoeuisemibold.ttf",
            "seguisb.ttf",
            "calibrib.ttf",
            "arialbd.ttf",
            "Georgia Bold.ttf",
            "DejaVuSans-Bold.ttf",
        ]
        if bold
        else [
            "segoeui.ttf",
            "calibri.ttf",
            "arial.ttf",
            "georgia.ttf",
            "DejaVuSans.ttf",
        ]
    )
    path = _font_path(names)
    if path:
        return ImageFont.truetype(str(path), size)
    return ImageFont.load_default()


def wrap_text(
    draw: ImageDraw.ImageDraw,
    text: str,
    font,
    max_width: int,
    max_lines: int,
) -> str:
    if not text:
        return ""
    words = text.split()
    lines: List[str] = []
    current = ""
    for word in words:
        trial = f"{current} {word}".strip()
        if draw.textlength(trial, font=font) <= max_width:
            current = trial
            continue
        if current:
            lines.append(current)
        current = word
        if len(lines) == max_lines - 1:
            break
    if current and len(lines) < max_lines:
        lines.append(current)
    if len(lines) == max_lines:
        while lines[-1] and draw.textlength(lines[-1] + "…", font=font) > max_width:
            lines[-1] = lines[-1][:-1].rstrip()
        if lines[-1] and not lines[-1].endswith("…"):
            lines[-1] = lines[-1].rstrip(".,;:") + "…"
    return "\n".join(lines)


def draw_cute_agent(canvas: Image.Image, cx: int, cy: int, scale: float = 1.0) -> None:
    """Paint a small Fetch.ai agent mascot onto the poster."""
    layer = Image.new("RGBA", canvas.size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(layer)
    s = scale

    def box(x1, y1, x2, y2):
        return (
            int(cx + x1 * s),
            int(cy + y1 * s),
            int(cx + x2 * s),
            int(cy + y2 * s),
        )

    draw.ellipse(box(-70, -14, 70, 82), fill=(64, 224, 208, 34))
    draw.rounded_rectangle(
        box(-32, 10, 32, 70),
        radius=int(20 * s),
        fill=(42, 214, 196, 255),
    )
    draw.ellipse(
        box(-44, -52, 44, 24),
        fill=(245, 248, 252, 255),
        outline=(20, 32, 48, 255),
        width=max(2, int(3 * s)),
    )
    draw.ellipse(box(-24, -26, -4, -4), fill=(18, 28, 44, 255))
    draw.ellipse(box(4, -26, 24, -4), fill=(18, 28, 44, 255))
    draw.ellipse(box(-18, -24, -10, -14), fill=(255, 255, 255, 230))
    draw.ellipse(box(10, -24, 18, -14), fill=(255, 255, 255, 230))
    draw.ellipse(box(-16, 2, -6, 10), fill=(255, 176, 186, 180))
    draw.ellipse(box(6, 2, 16, 10), fill=(255, 176, 186, 180))
    draw.arc(
        box(-12, -6, 12, 14),
        start=20,
        end=160,
        fill=(20, 32, 48, 255),
        width=max(2, int(3 * s)),
    )
    draw.line(box(0, -70, 0, -52), fill=TEAL, width=max(3, int(4 * s)))
    draw.ellipse(box(-7, -84, 7, -70), fill=GOLD)
    draw.ellipse(box(-52, 22, -32, 42), fill=(42, 214, 196, 255))
    draw.ellipse(box(32, 22, 52, 42), fill=(42, 214, 196, 255))
    draw.rounded_rectangle(
        box(-24, 66, -8, 88),
        radius=int(7 * s),
        fill=(30, 40, 62, 255),
    )
    draw.rounded_rectangle(
        box(8, 66, 24, 88),
        radius=int(7 * s),
        fill=(30, 40, 62, 255),
    )
    canvas.paste(Image.alpha_composite(canvas, layer))


def crop_model_marks(image: Image.Image) -> Image.Image:
    """Trim edges where badges and fake titles are often stamped."""
    width, height = image.size
    inset_x = max(8, int(width * 0.03))
    inset_top = max(16, int(height * 0.10))  # kill garbled top titles
    inset_bottom = max(8, int(height * 0.03))
    return image.crop(
        (inset_x, inset_top, width - inset_x, height - inset_bottom)
    )


def cover_corners(image: Image.Image, ratio: float = 0.06) -> Image.Image:
    """Gently cover only the extreme corners."""
    canvas = image.convert("RGB")
    draw = ImageDraw.Draw(canvas)
    width, height = canvas.size
    size = max(16, int(min(width, height) * ratio))
    samples = [
        (size, size, 0, 0, size, size),
        (width - size - 1, size, width - size, 0, width, size),
        (size, height - size - 1, 0, height - size, size, height),
        (
            width - size - 1,
            height - size - 1,
            width - size,
            height - size,
            width,
            height,
        ),
    ]
    pixels = canvas.load()
    for sample_x, sample_y, x1, y1, x2, y2 in samples:
        fill = pixels[
            max(0, min(width - 1, sample_x)),
            max(0, min(height - 1, sample_y)),
        ]
        draw.rounded_rectangle(
            (x1, y1, x2, y2),
            radius=max(8, size // 4),
            fill=fill,
        )
    return canvas


def sanitize_generated_scene(image: Image.Image) -> Image.Image:
    """Light cleanup that preserves most of the generated artwork."""
    scene = crop_model_marks(image.convert("RGB"))
    return cover_corners(scene)


def _fit_cover(image: Image.Image, size: int, bias_y: float = 0.35) -> Image.Image:
    """Scale and crop to a sharp square, keeping the subject higher in frame."""
    width, height = image.size
    scale = max(size / width, size / height)
    resized = image.resize(
        (max(1, int(width * scale)), max(1, int(height * scale))),
        Image.Resampling.LANCZOS,
    )
    left = (resized.width - size) // 2
    max_top = max(0, resized.height - size)
    top = int(max_top * max(0.0, min(1.0, bias_y)))
    return resized.crop((left, top, left + size, top + size))


def _polish(image: Image.Image) -> Image.Image:
    """Subtle clarity pass for LinkedIn feed sharpness."""
    sharpened = image.filter(
        ImageFilter.UnsharpMask(radius=1.4, percent=120, threshold=2)
    )
    contrast = ImageEnhance.Contrast(sharpened).enhance(1.06)
    color = ImageEnhance.Color(contrast).enhance(1.08)
    return ImageEnhance.Sharpness(color).enhance(1.1)


def validate_linkedin_image(image_bytes: bytes, min_edge: int = 1024) -> None:
    """Reject weak or tiny images before they are uploaded."""
    if not image_bytes or len(image_bytes) < 25_000:
        raise ValueError("Generated image is too small to be high quality")
    image = Image.open(BytesIO(image_bytes))
    width, height = image.size
    if min(width, height) < min_edge:
        raise ValueError(
            f"Generated image is {width}x{height}; need at least {min_edge}px"
        )


def compose_story_card(
    image_bytes: bytes,
    headline: str,
    subhead: str = "",
    output_size: int = POSTER_SIZE,
) -> bytes:
    """Build a full-bleed LinkedIn creative that keeps the artwork visible."""
    target = max(1024, int(output_size or POSTER_SIZE))
    scene = sanitize_generated_scene(Image.open(BytesIO(image_bytes)))
    # Bias toward the upper subject so the agent is not buried under text.
    scene = _polish(_fit_cover(scene, target, bias_y=0.25)).convert("RGBA")

    poster = scene.copy()
    overlay = Image.new("RGBA", poster.size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(overlay)

    # Soft fade only in the bottom fifth — never a hard mid-frame black box.
    fade_top = int(target * 0.78)
    for y in range(fade_top, target):
        progress = (y - fade_top) / max(1, target - fade_top)
        alpha = int(210 * (progress ** 1.35))
        draw.line((0, y, target, y), fill=(8, 14, 28, alpha))

    poster = Image.alpha_composite(poster, overlay)
    draw = ImageDraw.Draw(poster, "RGBA")

    # Thin premium frame.
    draw.rectangle(
        (18, 18, target - 18, target - 18),
        outline=(*TEAL[:3], 150),
        width=3,
    )

    kicker_font = load_font(max(18, target // 55), bold=True)
    title_font = load_font(max(40, target // 26), bold=True)
    body_font = load_font(max(22, target // 48), bold=False)
    title = wrap_text(draw, headline.strip(), title_font, target - 180, 2)
    supporting = wrap_text(draw, subhead.strip(), body_font, target - 180, 2)

    text_top = int(target * 0.82)
    draw.text((64, text_top), "FETCH.AI AGENTS", font=kicker_font, fill=TEAL)
    draw.multiline_text(
        (64, text_top + 30),
        title,
        font=title_font,
        fill=CREAM,
        spacing=8,
    )
    title_box = draw.multiline_textbbox(
        (64, text_top + 30),
        title,
        font=title_font,
        spacing=8,
    )
    if supporting:
        draw.multiline_text(
            (64, title_box[3] + 10),
            supporting,
            font=body_font,
            fill=MUTED,
            spacing=5,
        )

    draw_cute_agent(poster, target - 100, target - 95, scale=0.7)

    output = BytesIO()
    poster.convert("RGB").save(output, format="PNG", optimize=True, compress_level=4)
    return output.getvalue()


def fallback_visual_copy(post: str) -> Tuple[str, str]:
    cleaned = " ".join(
        word
        for word in post.replace("\n", " ").split()
        if not word.startswith("#")
    )
    pieces = [
        item.strip(" \"'")
        for item in cleaned.replace("?", "?|").replace("!", "!|").replace(". ", ".|").split("|")
        if item.strip()
    ]
    headline = (pieces[0] if pieces else "A useful idea, shown clearly")[:72].rstrip(" .,;:")
    subhead = pieces[1][:90].rstrip(" .,;:") if len(pieces) > 1 else ""
    return headline, subhead
