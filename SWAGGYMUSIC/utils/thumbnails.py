import logging
import os
import re
import uuid
from io import BytesIO

import aiohttp
from PIL import Image, ImageDraw, ImageEnhance, ImageFilter, ImageFont
from py_yt import VideosSearch
from config import YOUTUBE_IMG_URL

LOGGER = logging.getLogger(__name__)

# Constants
CACHE_DIR = "cache"
os.makedirs(CACHE_DIR, exist_ok=True)

# A card is cached as "<video id>_v6.png", and only when it was drawn from that
# video's own search result and its own picture. Older "<video id>_v4.png" files
# may hold another video's card or the generic YOUTUBE_IMG_URL picture, so they
# are never read (they are left in place; /restart clears the cache folder).
CACHE_VERSION = "v6"

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

def trim_to_width(text: str, font: ImageFont.FreeTypeFont, max_w: int) -> str:
    ellipsis = "…"
    if font.getlength(text) <= max_w:
        return text
    for i in range(len(text) - 1, 0, -1):
        if font.getlength(text[:i] + ellipsis) <= max_w:
            return text[:i] + ellipsis
    return ellipsis


def _same_video_picture(videoid) -> str:
    # YouTube's standard picture file of exactly this video (not a search).
    return f"https://i.ytimg.com/vi/{videoid}/hqdefault.jpg"


async def _download_picture(session, videoid, url):
    """The picture at ``url`` sized for the card, or None (the reason is logged)."""
    try:
        async with session.get(url) as resp:
            if resp.status != 200:
                LOGGER.warning(
                    "Thumbnail picture unavailable | video_id=%s | url=%s | HTTP %s",
                    videoid, str(url).split("?")[0], resp.status,
                )
                return None
            data = await resp.read()
        return Image.open(BytesIO(data)).resize((1280, 720)).convert("RGBA")
    except Exception as err:
        LOGGER.warning(
            "Thumbnail picture failed | video_id=%s | url=%s | %s: %s",
            videoid, str(url).split("?")[0], type(err).__name__, err,
        )
        return None


def _save(image, path: str) -> str:
    # Written under a unique name first, so a card that is being uploaded is
    # never read half-written while another play of the same video saves it.
    tmp = f"{path}.{uuid.uuid4().hex}.tmp"
    try:
        image.save(tmp, format="PNG")
        os.replace(tmp, path)
    finally:
        if os.path.exists(tmp):
            os.remove(tmp)
    return path


async def get_thumb(videoid, user_id=None, title=None, duration=None):
    """
    Play Panel card of ``videoid``: the path of a PNG card, or YOUTUBE_IMG_URL
    when no picture of this video can be downloaded (that generic image is
    only shown, never cached as the video's card).

    ``title`` and ``duration`` are the playing track's own values. They are
    drawn only when YouTube's search does not return this video.
    """
    cache_path = os.path.join(CACHE_DIR, f"{videoid}_{CACHE_VERSION}.png")
    if os.path.exists(cache_path):
        return cache_path
    try:
        return await _make_card(videoid, cache_path, title, duration)
    except Exception as err:
        # A card problem must never stop the Play Panel or the playback.
        LOGGER.warning("Thumbnail card failed | video_id=%s | %s: %s", videoid, type(err).__name__, err)
        return YOUTUBE_IMG_URL


async def _make_card(videoid, cache_path, track_title, track_duration):
    # YouTube video data fetch. Still one search request; YouTube can rank
    # other videos first for it, so only this video's own result is used.
    results = VideosSearch(f"https://www.youtube.com/watch?v={videoid}", limit=10)
    try:
        results_data = await results.next()
        result_items = [item for item in results_data.get("result", []) if item.get("id") == videoid]
        if not result_items:
            raise ValueError("this video is not among its search results")
        data = result_items[0]
        title = re.sub(r"\W+", " ", data.get("title", "Unsupported Title")).title()
        thumbnail = (data.get("thumbnails") or [{}])[0].get("url")
        duration = data.get("duration")
        views = data.get("viewCount", {}).get("short", "Unknown Views")
        from_search = True
    except Exception as err:
        LOGGER.warning("Thumbnail metadata unavailable | video_id=%s | %s: %s", videoid, type(err).__name__, err)
        # The playing track's own title and length; the picture is still this
        # video's own (below), never another video's or a generic one.
        title = re.sub(r"\W+", " ", str(track_title or "")).strip().title() or "Unsupported Title"
        thumbnail = None
        duration = None if str(track_duration or "").strip().lower() == "live track" else track_duration
        views = "Unknown Views"
        from_search = False

    is_live = not duration or str(duration).strip().lower() in {"", "live", "live now"}
    duration_text = "Live" if is_live else duration or "Unknown Mins"

    # Download thumbnail: the result's own picture, else this same video's
    # standard picture file.
    base = None
    used = None
    async with aiohttp.ClientSession() as session:
        for url in dict.fromkeys(u for u in (thumbnail, _same_video_picture(videoid)) if u):
            base = await _download_picture(session, videoid, url)
            if base is not None:
                used = url
                break
    if base is None:
        LOGGER.warning(
            "Thumbnail: no picture of this video could be downloaded; showing YOUTUBE_IMG_URL (not cached) | video_id=%s",
            videoid,
        )
        return YOUTUBE_IMG_URL

    # Create base image
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

    thumb = base.resize((THUMB_W, THUMB_H))
    tmask = Image.new("L", thumb.size, 0)
    ImageDraw.Draw(tmask).rounded_rectangle((0, 0, THUMB_W, THUMB_H), 20, fill=255)
    bg.paste(thumb, (THUMB_X, THUMB_Y), tmask)

    draw.text((TITLE_X, TITLE_Y), trim_to_width(title, title_font, MAX_TITLE_WIDTH), fill="black", font=title_font)
    draw.text((META_X, META_Y), f"YouTube | {views}", fill="black", font=regular_font)

    # Progress bar
    draw.line([(BAR_X, BAR_Y), (BAR_X + BAR_RED_LEN, BAR_Y)], fill="red", width=6)
    draw.line([(BAR_X + BAR_RED_LEN, BAR_Y), (BAR_X + BAR_TOTAL_LEN, BAR_Y)], fill="gray", width=5)
    draw.ellipse([(BAR_X + BAR_RED_LEN - 7, BAR_Y - 7), (BAR_X + BAR_RED_LEN + 7, BAR_Y + 7)], fill="red")

    draw.text((BAR_X, BAR_Y + 15), "00:00", fill="black", font=regular_font)
    end_text = "Live" if is_live else duration_text
    draw.text((BAR_X + BAR_TOTAL_LEN - (90 if is_live else 60), BAR_Y + 15), end_text, fill="red" if is_live else "black", font=regular_font)

    # Icons
    icons_path = "SWAGGYMUSIC/assets/thumb/play_icons.png"
    if os.path.isfile(icons_path):
        ic = Image.open(icons_path).resize((ICONS_W, ICONS_H)).convert("RGBA")
        r, g, b, a = ic.split()
        black_ic = Image.merge("RGBA", (r.point(lambda *_: 0), g.point(lambda *_: 0), b.point(lambda *_: 0), a))
        bg.paste(black_ic, (ICONS_X, ICONS_Y), black_ic)

    if from_search and used == thumbnail:
        # This video's own search result and own picture: cached.
        return _save(bg, cache_path)
    # Drawn with fallback data: shown for this play only and not stored under
    # the video's cache name, so the next play tries again.
    LOGGER.info("Thumbnail fallback card (not cached) | video_id=%s | picture=%s", videoid, str(used).split("?")[0])
    return _save(bg, os.path.join(CACHE_DIR, f"{videoid}_{CACHE_VERSION}_fallback.png"))
