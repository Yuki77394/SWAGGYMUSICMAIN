import asyncio
import itertools

from pyrogram.errors import FloodWait
from pyrogram.types import InlineKeyboardMarkup

from SWAGGYMUSIC import app
from SWAGGYMUSIC.misc import db
from SWAGGYMUSIC.utils.stream.autodelete import remember_player_message
from SWAGGYMUSIC.utils.thumbnails import get_thumb

# Each scheduled card gets a number that is stored on its own track. A card is
# only sent and kept while that very queue entry, with that number, is still
# playing: a card of a skipped, stopped or replayed track can never become the
# next track's Play Panel, even when both tracks are the same video.
CARD_TOKEN_KEY = "card_token"
_card_numbers = itertools.count(1)

# Card deliveries in flight (kept referenced until they finish).
_card_tasks: set = set()


def _still_current(chat_id: int, track: dict, token: int) -> bool:
    queue = db.get(chat_id)
    return bool(queue) and queue[0] is track and track.get(CARD_TOKEN_KEY) == token


async def _deliver_stream_card(
    chat_id: int,
    original_chat_id: int,
    videoid,
    user_id,
    caption: str,
    button,
    markup: str = "stream",
    track: dict = None,
    token: int = None,
):
    try:
        if not _still_current(chat_id, track, token):
            return

        img = await get_thumb(videoid, user_id, title=track.get("title"), duration=track.get("dur"))

        if not _still_current(chat_id, track, token):
            return

        try:
            run = await app.send_photo(
                original_chat_id,
                photo=img,
                caption=caption,
                reply_markup=InlineKeyboardMarkup(button),
                has_spoiler=True,
            )
        except FloodWait as exc:
            await asyncio.sleep(exc.value)
            if not _still_current(chat_id, track, token):
                return
            run = await app.send_photo(
                original_chat_id,
                photo=img,
                caption=caption,
                reply_markup=InlineKeyboardMarkup(button),
                has_spoiler=True,
            )

        if not _still_current(chat_id, track, token):
            # The song changed while its card was being sent.
            try:
                await run.delete()
            except Exception:
                pass
            return

        track["mystic"] = run
        remember_player_message(chat_id, run)
        track["markup"] = markup
    except Exception:
        return


def schedule_stream_card(
    chat_id: int,
    original_chat_id: int,
    videoid,
    user_id,
    caption: str,
    button,
    markup: str = "stream",
    track: dict = None,
):
    """
    Send the Play Panel of ``track`` (default: the track that has just become
    the head of the queue) in the background, without delaying playback.
    """
    if track is None:
        queue = db.get(chat_id)
        track = queue[0] if queue and isinstance(queue[0], dict) else None
    if not isinstance(track, dict) or track.get("vidid") != videoid:
        return
    token = next(_card_numbers)
    track[CARD_TOKEN_KEY] = token
    task = asyncio.create_task(
        _deliver_stream_card(
            chat_id=chat_id,
            original_chat_id=original_chat_id,
            videoid=videoid,
            user_id=user_id,
            caption=caption,
            button=button,
            markup=markup,
            track=track,
            token=token,
        )
    )
    _card_tasks.add(task)
    task.add_done_callback(_card_tasks.discard)
