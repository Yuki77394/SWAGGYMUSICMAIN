import asyncio

from SWAGGYMUSIC.logging import LOGGER
from SWAGGYMUSIC.misc import db
from SWAGGYMUSIC.utils.database import get_autodelete


QUEUE_REF_KEYS = ("queue_chat_id", "queue_msg_id")
PLAYER_REF_KEYS = ("player_chat_id", "player_msg_id", "mystic")

# Queue Panel deletions in flight (kept referenced until they finish).
_queue_panel_tasks: set = set()


def _message_chat_id(message):
    chat = getattr(message, "chat", None)
    return getattr(chat, "id", None)


def _message_id(message):
    return getattr(message, "id", None) or getattr(message, "message_id", None)


def remember_queue_message(chat_id: int, message, index: int = -1) -> bool:
    try:
        queue = db.get(chat_id)
        if not queue:
            return False

        item = queue[index]
        chat = _message_chat_id(message)
        msg_id = _message_id(message)
        if not chat or not msg_id:
            return False

        item["queue_chat_id"] = int(chat)
        item["queue_msg_id"] = int(msg_id)
        return True
    except Exception:
        return False


def remember_player_message(chat_id: int, message) -> bool:
    try:
        queue = db.get(chat_id)
        if not queue or not isinstance(queue[0], dict):
            return False

        chat = _message_chat_id(message)
        msg_id = _message_id(message)
        if not chat or not msg_id:
            return False

        queue[0]["player_chat_id"] = int(chat)
        queue[0]["player_msg_id"] = int(msg_id)
        return True
    except Exception:
        return False


def _setting_chat_id(chat_id: int, track: dict | None) -> int:
    if isinstance(track, dict):
        try:
            return int(track.get("chat_id") or chat_id)
        except (TypeError, ValueError):
            return int(chat_id)
    return int(chat_id)


async def _delete_by_ref(message=None, chat_id=None, message_id=None) -> bool:
    if message is not None:
        try:
            await message.delete()
            return True
        except Exception:
            pass

    if not chat_id or not message_id:
        return False

    try:
        from SWAGGYMUSIC import app

        await app.delete_messages(int(chat_id), int(message_id))
        return True
    except Exception:
        return False


async def _delete_tracked_message(track: dict, keys: tuple[str, ...]) -> bool:
    message = track.get("mystic") if "mystic" in keys else None
    chat_id = None
    message_id = None
    if "queue_chat_id" in keys:
        chat_id = track.get("queue_chat_id")
        message_id = track.get("queue_msg_id")
    elif "player_chat_id" in keys:
        chat_id = track.get("player_chat_id")
        message_id = track.get("player_msg_id")

    # Detach the references before awaiting, so a concurrent caller for the
    # same track finds nothing left to delete.
    for key in keys:
        track.pop(key, None)
    return await _delete_by_ref(message, chat_id, message_id)


async def link_queue_message(chat_id: int, track: dict | None, message) -> bool:
    """
    Record ``message`` as the Queue Panel of ``track`` (the song it announced).

    The panel is deleted by ``delete_queue_message`` when that song starts.
    If the song already started while its panel was being sent, the panel is
    deleted now; if the song already left the queue, nothing is recorded.
    """
    queue = db.get(chat_id) or []
    index = next((i for i, item in enumerate(queue) if item is track), None)
    if index is None or not remember_queue_message(chat_id, message, index):
        return False
    if index == 0:
        await delete_queue_message(chat_id, track)
    return True


async def _delete_queue_panel(chat_id: int, refs: dict) -> None:
    if await _delete_tracked_message(refs, QUEUE_REF_KEYS):
        LOGGER(__name__).info("Deleted Queue Panel of the started track | chat_id=%s", chat_id)


async def delete_queue_message(chat_id: int, track: dict | None) -> bool:
    """
    Delete the Queue Panel recorded on ``track``; called when that queued
    track starts playing, whatever the /autodelete setting.

    The reference is detached before anything is awaited, so a panel is never
    deleted twice, and the deletion runs in the background so it never delays
    the stream.
    """
    if not isinstance(track, dict):
        return False
    refs = {key: track.pop(key, None) for key in QUEUE_REF_KEYS}
    if not refs["queue_chat_id"] or not refs["queue_msg_id"]:
        return False
    try:
        task = asyncio.get_running_loop().create_task(_delete_queue_panel(chat_id, refs))
    except RuntimeError:
        return False
    _queue_panel_tasks.add(task)
    task.add_done_callback(_queue_panel_tasks.discard)
    return True


async def delete_player_message(
    chat_id: int,
    track: dict | None,
    force: bool = False,
) -> bool:
    """
    Delete the player card recorded on ``track``.

    ``force=True`` deletes it regardless of the /autodelete setting; it is
    used when a track finishes and leaves the queue.
    """
    if not isinstance(track, dict):
        return False
    if not force and not await get_autodelete(_setting_chat_id(chat_id, track)):
        return False
    deleted = await _delete_tracked_message(track, PLAYER_REF_KEYS)
    if deleted:
        LOGGER(__name__).info("Auto-deleted stream card | chat_id=%s", chat_id)
    return deleted


async def delete_track_messages(chat_id: int, track: dict | None) -> None:
    if not isinstance(track, dict):
        return
    if not await get_autodelete(_setting_chat_id(chat_id, track)):
        return
    # A Queue Panel is only deleted when its own track starts playing
    # (delete_queue_message), never because the track left the queue.
    await _delete_tracked_message(track, PLAYER_REF_KEYS)
