"""Captions of the Play Panel and the Queue Panels.

The layouts are the language strings ``stream_1`` (Play Panel), ``queue_4``
(song added to the queue) and ``queue_8`` + ``queue_10`` (/queue), taken from
ADVSWAGGYMUSIC's ``play_media``, ``play_queued``, ``queue_curr`` and
``queue_item``. These helpers fill them the way the reference does: shortened
titles, the requester as a clickable mention and the numbered upcoming list.
"""
import html
import re

import config

# The bot parses Markdown as well as HTML (ParseMode.DEFAULT). Characters that
# form Markdown markup are written as character references, so a title, name
# or link containing them is shown literally instead of becoming formatting.
_MARKDOWN_SAFE = str.maketrans({char: f"&#{ord(char)};" for char in "*_-~|`[]"})

# Telegram's limit for a photo caption, counted after the markup is parsed.
CAPTION_LIMIT = 1024


def _text(value) -> str:
    return html.escape(str(value), quote=True).translate(_MARKDOWN_SAFE)


def _title(title, limit: int, ellipsis: bool = True) -> str:
    title = str(title or "").strip()
    if len(title) > limit:
        title = title[:limit].rstrip() + "..." if ellipsis else title[:limit]
    return _text(title)


def requester(name, user_id=None) -> str:
    """The requester as a clickable mention (like ``User.mention``)."""
    try:
        user_id = int(user_id or 0)
    except (TypeError, ValueError):
        user_id = 0
    name = _text(name or "Unknown")
    if user_id > 0:
        return f"<a href=tg://user?id={user_id}>{name}</a>"
    return name  # e.g. "Autoplay", or a track stored without a user id


def track_link(track: dict) -> str:
    """Where a queued track's title links to, the same as on its Play Panel."""
    videoid = str(track.get("vidid") or "")
    if videoid in {"telegram", "soundcloud"} or str(track.get("file") or "").startswith("index_"):
        return config.SUPPORT_CHAT
    from SWAGGYMUSIC import app

    return f"https://t.me/{app.username}?start=info_{videoid}"


def play_caption(_, link, title, duration, user, user_id=None) -> str:
    """Play Panel (reference ``play_media``)."""
    return _["stream_1"].format(
        _text(link),
        _title(title, 25),
        _text(duration),
        requester(user, user_id),
    )


def queued_caption(_, position, link, title, duration, user, user_id=None) -> str:
    """Queue Panel sent when a song is added to the queue (reference ``play_queued``)."""
    return _["queue_4"].format(
        position,
        _text(link),
        _title(title, 40),
        _text(duration),
        requester(user, user_id),
    )


def _visible_length(caption: str) -> int:
    text = html.unescape(re.sub(r"<[^>]*>", "", caption)).strip()
    return len(text.encode("utf-16-le")) // 2


def queue_caption(_, queue: list, title, user) -> str:
    """Queue Panel of /queue (reference ``queue_curr`` + ``queue_item``).

    ``queue[0]`` is the current track; up to 14 upcoming tracks follow,
    numbered from 2. Entries that would push the photo caption past
    Telegram's limit are left out, so /queue always gets a panel.
    """
    current = queue[0]
    caption = _["queue_8"].format(
        _text(track_link(current)),
        _title(title, 50, ellipsis=False),
        _text(current.get("dur")),
        requester(user, current.get("user_id")),
    )
    items = ""
    for number, item in enumerate(queue[1:15], start=2):
        line = _["queue_10"].format(number, _text(item.get("title")), _text(item.get("dur")))
        if _visible_length(caption + items + line) > CAPTION_LIMIT:
            break
        items += line
    if items:
        caption += f"<blockquote expandable>{items}</blockquote>"
    return caption
