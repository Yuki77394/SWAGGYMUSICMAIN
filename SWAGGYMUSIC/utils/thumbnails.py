import asyncio
import os
import re
import uuid
from io import BytesIO

import aiohttp
from PIL import Image, ImageDraw, ImageEnhance, ImageFilter, ImageFont, ImageOps

# Constants
CACHE_DIR = "cache"
os.makedirs(CACHE_DIR, exist_ok=True)

# v4 cards were drawn from an unverified search result and can show another
# video's picture, title, views or duration, so no v4 file is served again.
CACHE_VERSION = "v5"
LEGACY_CACHE_VERSIONS = ("v4",)

PANEL_W, PANEL_H = 763, 545
PANEL_X = (1280 - PANEL_W) // 2
PANEL_Y = 88
TRANSPARENCY = 170
INNER_OFFSET = 36

THUMB_W, THUMB_H = 542, 273
THUMB_X = PANEL_X + (PANEL_W - THUMB_W) // 2
THUMB_Y = PANEL_Y + INNER_OFFSET

TITLE_X = 377
META_X = 377
TITLE_Y = THUMB_Y + THUMB_H + 10
META_Y = TITLE_Y + 45

BAR_X, BAR_Y = 388, META_Y + 45
BAR_RED_LEN = 280
BAR_TOTAL_LEN = 480

ICONS_W, ICONS_H = 415, 45
ICONS_X = PANEL_X + (PANEL_W - ICONS_W) // 2
ICONS_Y = BAR_Y + 48

MAX_TITLE_WIDTH = 580

VIDEO_ID = re.compile(r"[A-Za-z0-9_-]{11}")
# The video's own pictures, best first (hqdefault exists for every video).
PICTURE_URLS = (
    "https://i.ytimg.com/vi/{}/maxresdefault.jpg",
    "https://i.ytimg.com/vi/{}/hqdefault.jpg",
)
# Used only when the video's picture cannot be downloaded.
NEUTRAL_BACKGROUND = (34, 36, 44, 255)
NEUTRAL_PICTURE = (70, 72, 82, 255)
UNKNOWN_DURATIONS = {"", "0:00", "00:00", "none", "unknown"}

_locks = {}


def trim_to_width(text: str, font: ImageFont.FreeTypeFont, max_w: int) -> str:
    ellipsis = "…"
    if font.getlength(text) <= max_w:
        return text
    for i in range(len(text) - 1, 0, -1):
        if font.getlength(text[:i] + ellipsis) <= max_w:
            return text[:i] + ellipsis
    return ellipsis


def _cache_path(key: str, version: str = CACHE_VERSION) -> str:
    return os.path.join(CACHE_DIR, f"{key}_{version}.png")


async def _fetch_picture(videoid: str):
    """The video's own YouTube thumbnail as a 1280x720 image, or None."""
    try:
        timeout = aiohttp.ClientTimeout(total=10)
        async with aiohttp.ClientSession(timeout=timeout) as session:
            for url in PICTURE_URLS:
                try:
                    async with session.get(url.format(videoid)) as resp:
                        if resp.status != 200:
                            continue
                        data = await resp.read()
                    with Image.open(BytesIO(data)) as picture:
                        return ImageOps.fit(picture.convert("RGBA"), (1280, 720))
                except Exception:
                    continue
    except Exception:
        pass
    return None


async def _video_result(videoid: str) -> dict:
    """YouTube's search result for exactly this video (views, length), or {}."""
    try:
        from SWAGGYMUSIC.platforms.Youtube import exact_video_result

        return await exact_video_result(videoid, timeout=8)
    except Exception:
        return {}


def _draw_card(picture, title: str, views: str, end_text: str, is_live: bool):
    base = picture if picture is not None else Image.new("RGBA", (1280, 720), NEUTRAL_BACKGROUND)
    bg = ImageEnhance.Brightness(base.filter(ImageFilter.BoxBlur(10))).enhance(0.6)

    # Frosted glass panel
    panel_area = bg.crop((PANEL_X, PANEL_Y, PANEL_X + PANEL_W, PANEL_Y + PANEL_H))
    overlay = Image.new("RGBA", (PANEL_W, PANEL_H), (255, 255, 255, TRANSPARENCY))
    frosted = Image.alpha_composite(panel_area, overlay)
    mask = Image.new("L", (PANEL_W, PANEL_H), 0)
    ImageDraw.Draw(mask).rounded_rectangle((0, 0, PANEL_W, PANEL_H), 50, fill=255)
    bg.paste(frosted, (PANEL_X, PANEL_Y), mask)

    # Draw details
    draw = ImageDraw.Draw(bg)
    try:
        title_font = ImageFont.truetype("SWAGGYMUSIC/assets/thumb/font2.ttf", 32)
        regular_font = ImageFont.truetype("SWAGGYMUSIC/assets/thumb/font.ttf", 18)
    except OSError:
        title_font = regular_font = ImageFont.load_default()

    if picture is not None:
        thumb = base.resize((THUMB_W, THUMB_H))
    else:
        thumb = Image.new("RGBA", (THUMB_W, THUMB_H), NEUTRAL_PICTURE)
    tmask = Image.new("L", thumb.size, 0)
    ImageDraw.Draw(tmask).rounded_rectangle((0, 0, THUMB_W, THUMB_H), 20, fill=255)
    bg.paste(thumb, (THUMB_X, THUMB_Y), tmask)

    draw.text((TITLE_X, TITLE_Y), trim_to_width(title, title_font, MAX_TITLE_WIDTH), fill="black", font=title_font)
    draw.text((META_X, META_Y), f"YouTube | {views}" if views else "YouTube", fill="black", font=regular_font)

    # Progress bar
    draw.line([(BAR_X, BAR_Y), (BAR_X + BAR_RED_LEN, BAR_Y)], fill="red", width=6)
    draw.line([(BAR_X + BAR_RED_LEN, BAR_Y), (BAR_X + BAR_TOTAL_LEN, BAR_Y)], fill="gray", width=5)
    draw.ellipse([(BAR_X + BAR_RED_LEN - 7, BAR_Y - 7), (BAR_X + BAR_RED_LEN + 7, BAR_Y + 7)], fill="red")

    draw.text((BAR_X, BAR_Y + 15), "00:00", fill="black", font=regular_font)
    if end_text:
        draw.text((BAR_X + BAR_TOTAL_LEN - (90 if is_live else 60), BAR_Y + 15), end_text, fill="red" if is_live else "black", font=regular_font)

    # Icons
    icons_path = "SWAGGYMUSIC/assets/thumb/play_icons.png"
    if os.path.isfile(icons_path):
        ic = Image.open(icons_path).resize((ICONS_W, ICONS_H)).convert("RGBA")
        r, g, b, a = ic.split()
        black_ic = Image.merge("RGBA", (r.point(lambda *_: 0), g.point(lambda *_: 0), b.point(lambda *_: 0), a))
        bg.paste(black_ic, (ICONS_X, ICONS_Y), black_ic)
    return bg


def _save(image, path: str) -> str:
    # Written under a unique name first, so nobody ever reads a half-written file.
    tmp = f"{path}.{uuid.uuid4().hex}.tmp"
    try:
        image.save(tmp, format="PNG")
        os.replace(tmp, path)
    finally:
        if os.path.exists(tmp):
            os.remove(tmp)
    return path


async def _make_thumb(videoid: str, key: str, valid: bool, title, duration, live) -> str:
    cache_path = _cache_path(key)
    if valid and os.path.isfile(cache_path):
        return cache_path

    if valid:
        picture, result = await asyncio.gather(_fetch_picture(videoid), _video_result(videoid))
    else:
        picture, result = None, {}

    duration = str(duration or "").strip()
    is_live = bool(live) or duration == "Live Track"
    known = not is_live and duration.lower() not in UNKNOWN_DURATIONS
    if not known and not is_live and result:
        if result.get("duration"):
            duration, known = str(result["duration"]), True
        else:
            is_live = True  # YouTube lists this very video without a length
    title = re.sub(r"\W+", " ", str(title or result.get("title") or "")).strip().title() or "Unknown Title"
    views = str((result.get("viewCount") or {}).get("short") or "").strip()
    end_text = "Live" if is_live else (duration if known else "")

    card = _draw_card(picture, title, views, end_text, is_live)
    if picture is None:
        # Not cached under the video's name, so the next play tries again.
        return _save(card, _cache_path(key, f"{CACHE_VERSION}_fallback"))
    _save(card, cache_path)
    for version in LEGACY_CACHE_VERSIONS:
        try:
            os.remove(_cache_path(key, version))
        except OSError:
            pass
    return cache_path


async def get_thumb(videoid, user_id=None, title=None, duration=None, live=False):
    """
    Play Panel picture for exactly ``videoid``; returns a PNG path, or None.

    ``title``, ``duration`` and ``live`` come from the track being played (the
    video that was selected), so the card matches its caption. The picture is
    that video's own YouTube thumbnail, and views are shown only when YouTube
    returns this very video. When the thumbnail cannot be downloaded the card
    is drawn on a neutral background; an unrelated image is never used.
    """
    videoid = str(videoid or "").strip()
    valid = bool(VIDEO_ID.fullmatch(videoid))
    key = videoid if valid else (re.sub(r"[^A-Za-z0-9_-]", "_", videoid)[:64] or "unknown")
    lock = _locks.setdefault(key, asyncio.Lock())
    try:
        async with lock:  # one card per video at a time; later callers reuse it
            return await _make_thumb(videoid, key, valid, title, duration, live)
    except Exception:
        return None
    finally:
        if not lock.locked() and _locks.get(key) is lock:
            _locks.pop(key, None)
