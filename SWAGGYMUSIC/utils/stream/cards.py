import asyncio

from pyrogram.errors import FloodWait
from pyrogram.types import InlineKeyboardMarkup, LinkPreviewOptions

from SWAGGYMUSIC import app
from SWAGGYMUSIC.misc import db
from SWAGGYMUSIC.utils.stream.autodelete import remember_player_message
from SWAGGYMUSIC.utils.thumbnails import get_thumb


async def _send_card(original_chat_id: int, img, caption: str, button):
    if img:
        return await app.send_photo(
            original_chat_id,
            photo=img,
            caption=caption,
            reply_markup=InlineKeyboardMarkup(button),
        )
    # No picture could be made at all: the panel is still sent, as text,
    # and its title link must not turn into a link preview.
    return await app.send_message(
        original_chat_id,
        caption,
        reply_markup=InlineKeyboardMarkup(button),
        link_preview_options=LinkPreviewOptions(is_disabled=True),
    )


async def _deliver_stream_card(
    chat_id: int,
    original_chat_id: int,
    videoid,
    user_id,
    caption: str,
    button,
    markup: str = "stream",
):
    try:
        queue = db.get(chat_id)
        if not queue or queue[0].get("vidid") != videoid:
            return

        # The card is drawn from the track being played, so its title,
        # duration and picture belong to the same video as the caption.
        track = queue[0]
        try:
            img = await get_thumb(
                videoid,
                user_id,
                title=track.get("title"),
                duration=track.get("dur"),
                live=str(track.get("file") or "").startswith("live_"),
            )
        except Exception:
            img = None

        queue = db.get(chat_id)
        if not queue or queue[0].get("vidid") != videoid:
            return

        try:
            run = await _send_card(original_chat_id, img, caption, button)
        except FloodWait as exc:
            await asyncio.sleep(exc.value)
            run = await _send_card(original_chat_id, img, caption, button)

        queue = db.get(chat_id)
        if not queue or queue[0].get("vidid") != videoid:
            try:
                await run.delete()
            except Exception:
                pass
            return

        db[chat_id][0]["mystic"] = run
        remember_player_message(chat_id, run)
        db[chat_id][0]["markup"] = markup
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
):
    asyncio.create_task(
        _deliver_stream_card(
            chat_id=chat_id,
            original_chat_id=original_chat_id,
            videoid=videoid,
            user_id=user_id,
            caption=caption,
            button=button,
            markup=markup,
        )
    )
