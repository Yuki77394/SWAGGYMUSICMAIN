from datetime import datetime

from pyrogram import filters
from pyrogram.types import Message

from SWAGGYMUSIC import app
from SWAGGYMUSIC.core.call import JARVIS
from SWAGGYMUSIC.utils import bot_sys_stats
from SWAGGYMUSIC.utils.decorators.language import language
from SWAGGYMUSIC.utils.inline import supp_markup
from config import BANNED_USERS, PING_IMG_URL


@app.on_message(filters.command(["ping", "alive"], prefixes=["/"]) & ~BANNED_USERS)
@language
async def ping_com(client, message: Message, _):
    start = datetime.now()
    response = await message.reply_photo(
        photo=PING_IMG_URL,
        caption=_["ping_1"].format(app.mention),
    )
    pytgping = await JARVIS.ping()
    UP, CPU, RAM, DISK = await bot_sys_stats()
    resp = (datetime.now() - start).total_seconds() * 1000
    await response.edit_caption(
        caption=_["ping_2"].format(resp, app.mention, UP, RAM, CPU, DISK, pytgping),
        reply_markup=supp_markup(_),
    )
