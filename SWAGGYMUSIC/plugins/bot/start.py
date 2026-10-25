import asyncio
import html
import json
import random
import re
import time

import aiohttp

from pyrogram import filters
from pyrogram.enums import ChatType
from pyrogram.types import InlineKeyboardMarkup, Message
from youtubesearchpython.future import VideosSearch

import config
from SWAGGYMUSIC import app
from SWAGGYMUSIC.button_styles import primary_button, success_button
from SWAGGYMUSIC.misc import _boot_
from SWAGGYMUSIC.plugins.sudo.sudoers import sudoers_list
from SWAGGYMUSIC.utils import bot_sys_stats
from SWAGGYMUSIC.utils.database import (
    add_served_chat,
    add_served_user,
    blacklisted_chats,
    get_lang,
    get_served_chats,
    get_served_users,
    is_banned_user,
    is_on_off,
)
from SWAGGYMUSIC.utils.decorators.language import LanguageStart
from SWAGGYMUSIC.utils.formatters import get_readable_time
from SWAGGYMUSIC.utils.inline.help import first_page
from SWAGGYMUSIC.utils.inline.start import private_panel, start_panel
from config import BANNED_USERS, AYUV, HELP_IMG_URL, START_VIDS, STICKERS
from strings import get_string


CELEBRATION_EFFECT_ID = 5046509860389126442

# Same rotating image pool used by the current Kurigram repo.
START_IMAGES = [
    "https://files.catbox.moe/jf0yqq.jpg",
    "https://files.catbox.moe/7w0ec2.jpg",
    "https://files.catbox.moe/dfj1l8.jpg",
    "https://files.catbox.moe/e7pbwj.jpg",
    "https://files.catbox.moe/bta4qz.jpg",
    "https://files.catbox.moe/1a1pu2.jpg",
    "https://files.catbox.moe/xvirq4.jpg",
    "https://files.catbox.moe/8dyj3u.jpg",
    "https://files.catbox.moe/x63yfj.jpg",
    "https://files.catbox.moe/3rtw9v.jpg",
    "https://files.catbox.moe/0u6db2.jpg",
]


def _escape_html_ampersands(text: str) -> str:
    return re.sub(r"&(?!#(?:[0-9]+|x[0-9A-Fa-f]+);|[A-Za-z][A-Za-z0-9]+;)", "&amp;", text)


def _build_start_caption(message: Message, template: str) -> str:
    template = _escape_html_ampersands(template)
    # Some Queenupdate translations use Markdown while Kurigram's English
    # start caption uses HTML. Normalize the common Markdown forms for the
    # Bot API HTML parse mode without disturbing existing HTML tags.
    template = re.sub(r"\*\*(.+?)\*\*", r"<b>\1</b>", template, flags=re.DOTALL)
    template = re.sub(
        r"\[([^\]]+)\]\((https?://[^)]+)\)",
        r'<a href="\2">\1</a>',
        template,
    )
    user = message.from_user
    user_name = " ".join(part for part in (user.first_name, user.last_name) if part).strip() or "User"
    user_mention = f'<a href="tg://user?id={int(user.id)}">{html.escape(user_name, quote=False)}</a>'
    bot_username = getattr(app, "username", None)
    bot_name = getattr(app, "name", None) or bot_username or "Bot"
    safe_bot_name = html.escape(str(bot_name).strip(), quote=False)
    bot_mention = f'<a href="https://t.me/{bot_username}">{safe_bot_name}</a>' if bot_username else safe_bot_name
    return template.format(user_mention, bot_mention)


async def _send_start_photo_with_effect(message: Message, photo: str, caption: str, out):
    keyboard = []
    for row in out:
        buttons = []
        for button in row:
            item = {"text": button.text}
            if button.url:
                item["url"] = button.url
            elif button.callback_data is not None:
                item["callback_data"] = button.callback_data
            elif button.user_id:
                item["url"] = f"tg://user?id={button.user_id}"
            else:
                continue
            style = getattr(button, "style", None)
            style_name = str(getattr(style, "value", style)).lower()
            for supported_style in ("primary", "success", "danger"):
                if style_name.endswith(supported_style):
                    item["style"] = supported_style
                    break
            buttons.append(item)
        if buttons:
            keyboard.append(buttons)
    payload = {
        "chat_id": message.chat.id, "photo": photo, "caption": caption,
        "parse_mode": "HTML", "has_spoiler": True,
        "message_effect_id": str(CELEBRATION_EFFECT_ID),
        "reply_markup": json.dumps({"inline_keyboard": keyboard}),
        "reply_parameters": json.dumps({"message_id": message.id}),
    }
    url = f"https://api.telegram.org/bot{config.BOT_TOKEN}/sendPhoto"
    timeout = aiohttp.ClientTimeout(total=30)
    async with aiohttp.ClientSession(timeout=timeout) as session:
        async with session.post(url, data=payload) as response:
            result = await response.json(content_type=None)
            if response.status != 200 or not result.get("ok"):
                raise RuntimeError(f"Telegram Bot API sendPhoto failed: {result}")
            return result


async def delete_sticker_after_delay(message: Message, delay: int) -> None:
    await asyncio.sleep(delay)
    try:
        await message.delete()
    except Exception:
        pass


@app.on_message(filters.command(["start"]) & filters.private & ~BANNED_USERS)
@LanguageStart
async def start_pm(client, message: Message, _):
    try:
        await add_served_user(message.from_user.id)
    except Exception:
        pass

    try:
        await message.react("❤️", big=True)
    except Exception:
        pass

    if len(message.text.split()) > 1:
        name = message.text.split(None, 1)[1]

        if name.startswith("help"):
            keyboard = first_page(_)

            return await message.reply_photo(
                photo=HELP_IMG_URL,
                caption=_["help_1"].format(config.SUPPORT_CHAT),
                reply_markup=keyboard,
            )

        if name.startswith("sud"):
            await sudoers_list(client=client, message=message, _=_)

            if await is_on_off(2):
                username = (
                    f"@{message.from_user.username}"
                    if message.from_user.username
                    else "(none)"
                )

                await app.send_message(
                    chat_id=config.LOGGER_ID,
                    text=(
                        f"{message.from_user.mention} ᴊᴜsᴛ sᴛᴀʀᴛᴇᴅ "
                        f"ᴛʜᴇ ʙᴏᴛ ᴛᴏ ᴄʜᴇᴄᴋ <b>sᴜᴅᴏʟɪsᴛ</b>.\n\n"
                        f"<b>ᴜsᴇʀ ɪᴅ :</b> "
                        f"<code>{message.from_user.id}</code>\n"
                        f"<b>ᴜsᴇʀɴᴀᴍᴇ :</b> {username}"
                    ),
                )

            return

        if name.startswith("inf"):
            m = await message.reply_text("🔎")

            try:
                vid_id = str(name).replace("info_", "", 1)
                query = f"https://www.youtube.com/watch?v={vid_id}"

                results = VideosSearch(query, limit=1)
                data = await results.next()
                result = (data.get("result") or [None])[0]

                if not result:
                    return await m.edit_text("No results found.")

                title = result.get("title") or "Unknown"
                duration = result.get("duration") or "Unknown"

                views = (
                    (result.get("viewCount") or {}).get("short")
                    or "Unknown"
                )

                thumbnail = (
                    (result.get("thumbnails") or [{}])[0].get("url")
                    or ""
                ).split("?")[0]

                channellink = (
                    (result.get("channel") or {}).get("link")
                    or "https://youtube.com"
                )

                channel = (
                    (result.get("channel") or {}).get("name")
                    or "Unknown"
                )

                link = result.get("link") or query
                published = result.get("publishedTime") or "Unknown"

                searched_text = _["start_6"].format(
                    title,
                    duration,
                    views,
                    published,
                    channellink,
                    channel,
                    app.mention,
                )

                key = InlineKeyboardMarkup(
                    [[
                        primary_button(
                            text=_["S_B_6"],
                            url=link,
                        ),
                        success_button(
                            text=_["S_B_4"],
                            url=config.SUPPORT_CHAT,
                        ),
                    ]]
                )

                await m.delete()

                await app.send_photo(
                    chat_id=message.chat.id,
                    photo=thumbnail or HELP_IMG_URL,
                    caption=searched_text,
                    reply_markup=key,
                )

            except Exception as e:
                await m.edit_text(f"Error: {e}")

            return

    out = private_panel(_)
    await _send_start_photo_with_effect(
        message=message,
        photo=random.choice(START_IMAGES),
        caption=_build_start_caption(message, _["start_2"]),
        out=out,
    )

    if await is_on_off(2):
        username = (
            f"@{message.from_user.username}"
            if message.from_user.username
            else "(none)"
        )

        await app.send_message(
            chat_id=config.LOGGER_ID,
            text=(
                f"{message.from_user.mention} ᴊᴜsᴛ sᴛᴀʀᴛᴇᴅ "
                f"ᴛʜᴇ ʙᴏᴛ.\n\n"
                f"<b>ᴜsᴇʀ ɪᴅ :</b> "
                f"<code>{message.from_user.id}</code>\n"
                f"<b>ᴜsᴇʀɴᴀᴍᴇ :</b> {username}"
            ),
        )


@app.on_message(filters.command(["start"]) & filters.group & ~BANNED_USERS)
@LanguageStart
async def start_gp(client, message: Message, _):
    out = start_panel(_)
    uptime = int(time.time() - _boot_)

    try:
        await message.reply_photo(
            photo=random.choice(START_IMAGES),
            has_spoiler=True,
            caption=_["start_1"].format(
                app.mention,
                get_readable_time(uptime),
            ),
            reply_markup=InlineKeyboardMarkup(out),
        )

    except Exception as ex:
        print(f"START GROUP ERROR: {ex}")

    return await add_served_chat(message.chat.id)


@app.on_message(filters.new_chat_members, group=-1)
async def welcome(client, message: Message):
    for member in message.new_chat_members:
        try:
            language = await get_lang(message.chat.id)
            _ = get_string(language)

            if await is_banned_user(member.id):
                try:
                    await message.chat.ban_member(member.id)
                except Exception:
                    pass

            if member.id == app.id:
                if message.chat.type != ChatType.SUPERGROUP:
                    await message.reply_text(_["start_4"])
                    return await app.leave_chat(message.chat.id)

                if message.chat.id in await blacklisted_chats():
                    await message.reply_text(
                        _["start_5"].format(
                            app.mention,
                            f"https://t.me/{app.username}?start=sudolist",
                            config.SUPPORT_CHAT,
                        ),
                        disable_web_page_preview=True,
                    )

                    return await app.leave_chat(message.chat.id)

                out = start_panel(_)

                # BOT ADD HONE PAR IMAGE
                await message.reply_photo(
                    photo=random.choice(START_VIDS),
                    caption=_["start_3"].format(
                        message.from_user.mention,
                        app.mention,
                        message.chat.title,
                        app.mention,
                    ),
                    reply_markup=InlineKeyboardMarkup(out),
                )

                await add_served_chat(message.chat.id)
                await message.stop_propagation()

        except Exception as ex:
            print(f"WELCOME ERROR: {ex}")
