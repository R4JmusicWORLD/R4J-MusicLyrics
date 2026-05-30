"""Thumbnail generation for music playback cards."""

from __future__ import annotations

import os
import textwrap
from io import BytesIO

from PIL import Image, ImageDraw, ImageFont
import aiohttp

from config import Config

_DOWNLOADS = Config.DOWNLOADS_DIR
_THUMB_DIR = os.path.join(_DOWNLOADS, "thumbnails")
os.makedirs(_THUMB_DIR, exist_ok=True)

# Canvas dimensions
WIDTH, HEIGHT = 1280, 720

# Colours
BG_COLOR = (30, 30, 30)
OVERLAY_COLOR = (0, 0, 0, 160)
ACCENT_COLOR = (29, 185, 84)
TEXT_COLOR = (255, 255, 255)
SUB_TEXT_COLOR = (180, 180, 180)
BRAND_COLOR = (29, 185, 84)


def _get_font(size: int, bold: bool = False) -> ImageFont.FreeTypeFont:
    """Return a TrueType font, falling back to the default bitmap font."""
    font_paths = [
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
        if bold
        else "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf"
        if bold
        else "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf",
        "/usr/share/fonts/truetype/freefont/FreeSansBold.ttf"
        if bold
        else "/usr/share/fonts/truetype/freefont/FreeSans.ttf",
    ]
    for path in font_paths:
        if os.path.isfile(path):
            return ImageFont.truetype(path, size)
    try:
        return ImageFont.truetype("arial.ttf", size)
    except OSError:
        return ImageFont.load_default()


def _format_dur(seconds: int) -> str:
    mins, secs = divmod(seconds, 60)
    hours, mins = divmod(mins, 60)
    if hours:
        return f"{hours}:{mins:02d}:{secs:02d}"
    return f"{mins:02d}:{secs:02d}"


async def gen_thumbnail(
    title: str,
    artist: str,
    duration: int,
    thumbnail_url: str,
    requester: str,
) -> str:
    """Generate a styled thumbnail image and return the file path.

    Parameters
    ----------
    title:
        Song title.
    artist:
        Artist / channel name.
    duration:
        Duration in seconds.
    thumbnail_url:
        URL of the cover / thumbnail image.
    requester:
        Display name of the user who requested the track.

    Returns
    -------
    str
        Absolute path of the generated PNG file.
    """
    # -- Download the thumbnail image ------------------------------------------
    thumb_img: Image.Image | None = None
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(thumbnail_url, timeout=aiohttp.ClientTimeout(total=15)) as resp:
                if resp.status == 200:
                    raw = await resp.read()
                    thumb_img = Image.open(BytesIO(raw)).convert("RGB")
    except Exception:
        thumb_img = None

    # -- Build canvas ----------------------------------------------------------
    canvas = Image.new("RGB", (WIDTH, HEIGHT), BG_COLOR)

    if thumb_img:
        # Resize thumbnail to fill left half
        thumb_img = thumb_img.resize((WIDTH, HEIGHT), Image.LANCZOS)
        canvas.paste(thumb_img, (0, 0))

    # Semi-transparent overlay
    overlay = Image.new("RGBA", (WIDTH, HEIGHT), OVERLAY_COLOR)
    canvas = Image.alpha_composite(canvas.convert("RGBA"), overlay)

    draw = ImageDraw.Draw(canvas)

    # -- Fonts -----------------------------------------------------------------
    font_title = _get_font(48, bold=True)
    font_artist = _get_font(34)
    font_info = _get_font(28)
    font_brand = _get_font(36, bold=True)

    # -- Layout ----------------------------------------------------------------
    y_cursor = 200

    # Title (wrapped)
    wrapped_title = textwrap.fill(title, width=35)
    draw.multiline_text(
        (80, y_cursor), wrapped_title, fill=TEXT_COLOR, font=font_title, spacing=8
    )
    title_lines = wrapped_title.count("\n") + 1
    y_cursor += title_lines * 58 + 20

    # Artist
    draw.text((80, y_cursor), artist, fill=SUB_TEXT_COLOR, font=font_artist)
    y_cursor += 55

    # Duration bar background
    bar_y = y_cursor + 10
    bar_width = WIDTH - 160
    draw.rounded_rectangle(
        [(80, bar_y), (80 + bar_width, bar_y + 8)],
        radius=4,
        fill=(80, 80, 80),
    )
    # Filled portion (visual decoration -- 40%)
    draw.rounded_rectangle(
        [(80, bar_y), (80 + int(bar_width * 0.4), bar_y + 8)],
        radius=4,
        fill=ACCENT_COLOR,
    )
    y_cursor = bar_y + 25

    # Duration text
    draw.text((80, y_cursor), _format_dur(duration), fill=SUB_TEXT_COLOR, font=font_info)

    # Requested by
    y_cursor += 50
    draw.text(
        (80, y_cursor),
        f"Requested by: {requester}",
        fill=SUB_TEXT_COLOR,
        font=font_info,
    )

    # -- Branding (bottom-right) -----------------------------------------------
    brand_text = Config.BOT_NAME
    bbox = draw.textbbox((0, 0), brand_text, font=font_brand)
    tw = bbox[2] - bbox[0]
    draw.text(
        (WIDTH - tw - 60, HEIGHT - 70),
        brand_text,
        fill=BRAND_COLOR,
        font=font_brand,
    )

    # -- Save ------------------------------------------------------------------
    out_path = os.path.join(_THUMB_DIR, f"thumb_{hash(title) & 0xFFFFFFFF}.png")
    canvas.convert("RGB").save(out_path, "PNG")
    return out_path
