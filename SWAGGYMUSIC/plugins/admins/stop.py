from pyrogram import filters
from pyrogram.types import Message

from SWAGGYMUSIC import app
from SWAGGYMUSIC.core.call import JARVIS, schedule_player_card_removal
from SWAGGYMUSIC.misc import db
from SWAGGYMUSIC.utils.database import set_loop
from SWAGGYMUSIC.utils.decorators import AdminRightsCheck
from SWAGGYMUSIC.utils.inline import close_markup
from config import BANNED_USERS


@app.on_message(
    filters.command(["end"], prefixes=["/", "!"]) & filters.group & ~BANNED_USERS
)
@AdminRightsCheck
async def stop_music(cli, message: Message, _, chat_id):
    if not len(message.command) == 1:
        return
    queue = db.get(chat_id)
    playing = queue[0] if queue and isinstance(queue[0], dict) else None
    await JARVIS.stop_stream(chat_id)
    # Playback has stopped (stop_stream raises otherwise): the song's Started
    # Streaming message goes too, whatever the /autodelete setting. Only that
    # track's own message is deleted, in the background.
    schedule_player_card_removal(chat_id, playing)
    await set_loop(chat_id, 0)
    await message.reply_text(
        _["admin_5"].format(message.from_user.mention), reply_markup=close_markup(_)
    )
