import asyncio
from datetime import datetime

from pyrogram.enums import ChatType
from pyrogram.errors import FloodWait

import config
from SWAGGYMUSIC import LOGGER, app
from SWAGGYMUSIC.core.call import JARVIS, autoend
from SWAGGYMUSIC.misc import db
from SWAGGYMUSIC.utils.database import get_client, is_active_chat, is_autoend


# ==========================================================
# ASSISTANT AUTO-LEAVE
#
# Every AUTO_LEAVE_ASSISTANT_TIME seconds (default 7200 = 2 h)
# each assistant leaves groups/channels where nothing is
# playing. Chats with an active or queued stream are skipped,
# and the check is repeated right before each leave, so the
# sweep never interrupts music.
# ==========================================================

AUTO_LEAVE_DEFAULT_INTERVAL = 7200
AUTO_LEAVE_MIN_INTERVAL = 60
AUTO_LEAVE_MAX_PER_ASSISTANT = 20
# Pause between two leaves, as in KURIGRAMSWAG, to stay clear of flood limits.
AUTO_LEAVE_PAUSE_SECONDS = 5
AUTO_LEAVE_EXEMPT_CHATS = {-1002077986660, -1002166290494}
AUTO_LEAVE_CHAT_TYPES = (ChatType.SUPERGROUP, ChatType.GROUP, ChatType.CHANNEL)

_auto_leave_task = None


def _auto_leave_interval() -> int:
    try:
        interval = int(config.AUTO_LEAVE_ASSISTANT_TIME)
    except (TypeError, ValueError):
        return AUTO_LEAVE_DEFAULT_INTERVAL
    if interval < AUTO_LEAVE_MIN_INTERVAL:
        # A zero/negative value would turn the sweep into a busy loop.
        return AUTO_LEAVE_DEFAULT_INTERVAL
    return interval


async def _chat_is_busy(chat_id: int) -> bool:
    return (
        await is_active_chat(chat_id)
        or chat_id in JARVIS.active_calls
        or bool(db.get(chat_id))
    )


async def _leave_idle_chats(num: int) -> int:
    client = await get_client(num)
    if client is None or not getattr(client, "is_connected", False):
        LOGGER(__name__).warning("Auto-leave skipped assistant %s: not connected", num)
        return 0

    left = 0
    async for dialog in client.get_dialogs():
        chat = dialog.chat
        if chat.type not in AUTO_LEAVE_CHAT_TYPES:
            continue
        if chat.id == config.LOGGER_ID or chat.id in AUTO_LEAVE_EXEMPT_CHATS:
            continue
        # Decide from the live state at the moment of leaving.
        if await _chat_is_busy(chat.id):
            continue
        try:
            await client.leave_chat(chat.id)
        except FloodWait as err:
            LOGGER(__name__).warning(
                "Auto-leave paused for assistant %s: flood wait %ss", num, err.value
            )
            break
        except Exception as err:
            LOGGER(__name__).warning(
                "Auto-leave could not leave %s with assistant %s: %s", chat.id, num, err
            )
            continue
        left += 1
        if left >= AUTO_LEAVE_MAX_PER_ASSISTANT:
            break
        await asyncio.sleep(AUTO_LEAVE_PAUSE_SECONDS)
    return left


async def auto_leave():
    if not config.AUTO_LEAVING_ASSISTANT:
        return

    interval = _auto_leave_interval()
    LOGGER(__name__).info("Assistant auto-leave enabled: every %s seconds", interval)

    while True:
        await asyncio.sleep(interval)

        from SWAGGYMUSIC.core.userbot import assistants

        for num in list(assistants):
            try:
                left = await _leave_idle_chats(num)
            except Exception as err:
                # Disconnects and API errors only skip this assistant for
                # this sweep. Cancellation is not caught and stops the task.
                LOGGER(__name__).warning("Auto-leave failed for assistant %s: %s", num, err)
                continue
            if left:
                LOGGER(__name__).info("Auto-leave: assistant %s left %s idle chat(s)", num, left)


def start_auto_leave():
    """Start the auto-leave loop once; a second call reuses the running task."""
    global _auto_leave_task
    if _auto_leave_task is not None and not _auto_leave_task.done():
        return _auto_leave_task
    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        LOGGER(__name__).warning("Auto-leave not started: no running event loop")
        return None
    _auto_leave_task = loop.create_task(auto_leave())
    return _auto_leave_task


def stop_auto_leave():
    task = _auto_leave_task
    if task is not None and not task.done():
        task.cancel()


start_auto_leave()


async def auto_end():
    while not await asyncio.sleep(5):
        ender = await is_autoend()
        if not ender:
            continue
        for chat_id in autoend:
            timer = autoend.get(chat_id)
            if not timer:
                continue
            if datetime.now() > timer:
                if not await is_active_chat(chat_id):
                    autoend[chat_id] = {}
                    continue
                autoend[chat_id] = {}
                try:
                    await JARVIS.stop_stream(chat_id)
                except:
                    continue
                try:
                    await app.send_message(
                        chat_id,
                        "» ʙᴏᴛ ᴀᴜᴛᴏᴍᴀᴛɪᴄᴀʟʟʏ ʟᴇғᴛ ᴠɪᴅᴇᴏᴄʜᴀᴛ ʙᴇᴄᴀᴜsᴇ ɴᴏ ᴏɴᴇ ᴡᴀs ʟɪsᴛᴇɴɪɴɢ ᴏɴ ᴠɪᴅᴇᴏᴄʜᴀᴛ.",
                    )
                except:
                    continue


asyncio.create_task(auto_end())
