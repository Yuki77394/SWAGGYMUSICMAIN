#
# Copyright (C) 2021-2022 by TheAloneteam@Github.
#
# This file is part of AloneMusic project.
# Released under GNU v3.0 License Agreement.
#

from typing import Union

from SWAGGYMUSIC.button_styles import (
    danger_button,
    primary_button,
    success_button,
)


# ==========================================================
# FIXED BUTTON STYLES
#
# Layouts and styles mirror KURIGRAMSWAG's utils/inline/play.py.
# Every button has one fixed style, so colours never change
# between renders.
# ==========================================================


# ==========================================================
# TRACK MARKUP
# ==========================================================

def track_markup(
    _,
    videoid,
    user_id,
    channel,
    fplay,
    thumb: Union[bool, str] = None,
):
    return [
        [
            primary_button(
                text="🎵",
                callback_data=(
                    f"MusicStream "
                    f"{videoid}|{user_id}|a|{channel}|{fplay}"
                ),
            ),
            primary_button(
                text="🎥",
                callback_data=(
                    f"MusicStream "
                    f"{videoid}|{user_id}|v|{channel}|{fplay}"
                ),
            ),
        ],
        [
            success_button(
                text="⎘",
                callback_data=(
                    f"MusicThumb "
                    f"{videoid}|{user_id}|"
                    f"{channel}|{fplay}"
                ),
            ),
            danger_button(
                text="⌯✖",
                callback_data=(
                    f"forceclose {videoid}|{user_id}"
                ),
            ),
        ],
    ]


# ==========================================================
# PLAYER KEYBOARD
#
# Normal player:
#     ▷   II   ‣‣I   ↻   ▢        (PRIMARY)
#     ☰ ᴍᴏʀᴇ (SUCCESS)   🗑 (DANGER)
#
# MORE menu (controls row stays on top):
#     ▷   II   ‣‣I   ↻   ▢        (PRIMARY)
#     Autoplay / ♫   Thumb / ⎘    (PRIMARY)
#     ⟵ ʙᴀᴄᴋ (SUCCESS)   🗑 (DANGER)
# ==========================================================

def _player_controls_row(chat_id):
    return [
        primary_button(
            text="▷",
            callback_data=f"ADMIN Resume|{chat_id}",
        ),
        primary_button(
            text="II",
            callback_data=f"ADMIN Pause|{chat_id}",
        ),
        primary_button(
            text="‣‣I",
            callback_data=f"ADMIN Skip|{chat_id}",
        ),
        primary_button(
            text="↻",
            callback_data=f"ADMIN Replay|{chat_id}",
        ),
        primary_button(
            text="▢",
            callback_data=f"ADMIN Stop|{chat_id}",
        ),
    ]


def _player_buttons(
    chat_id,
    more: bool,
    autoplay_text: str,
    thumb_text: str,
):
    if not more:
        return [
            _player_controls_row(chat_id),
            [
                success_button(
                    text="☰ ᴍᴏʀᴇ",
                    callback_data=f"ADMIN More|{chat_id}",
                ),
                danger_button(
                    text="🗑",
                    callback_data="close",
                ),
            ],
        ]

    return [
        _player_controls_row(chat_id),
        [
            primary_button(
                text=autoplay_text,
                callback_data=f"ADMIN Autoplay|{chat_id}",
            ),
            primary_button(
                text=thumb_text,
                callback_data=f"ADMIN Thumb|{chat_id}",
            ),
        ],
        [
            success_button(
                text="⟵ ʙᴀᴄᴋ",
                callback_data=f"ADMIN Back|{chat_id}",
            ),
            danger_button(
                text="🗑",
                callback_data="close",
            ),
        ],
    ]


# ==========================================================
# STREAM TIMER MARKUP
#
# Used for tracks with a known duration. KURIGRAMSWAG shows the
# same static player here (no progress row); its MORE row is
# labelled "Autoplay" / "Thumb".
# ==========================================================

def stream_markup_timer(
    _,
    chat_id,
    played,
    dur,
    autoplay: Union[bool, str] = None,
    thumb: Union[bool, str] = None,
    chat_filter: Union[bool, str] = None,
    more: bool = False,
):
    return _player_buttons(
        chat_id,
        more,
        autoplay_text="Autoplay",
        thumb_text="Thumb",
    )


# ==========================================================
# NORMAL STREAM MARKUP
#
# Used when the player is first sent and for live streams.
# Its MORE row uses the ♫ / ⎘ symbols, as in KURIGRAMSWAG.
# ==========================================================

def stream_markup(
    _,
    chat_id,
    autoplay: Union[bool, str] = None,
    thumb: Union[bool, str] = None,
    chat_filter: Union[bool, str] = None,
    more: bool = False,
):
    return _player_buttons(
        chat_id,
        more,
        autoplay_text="♫",
        thumb_text="⎘",
    )


# ==========================================================
# PLAYLIST MARKUP
# ==========================================================

def playlist_markup(
    _,
    videoid,
    user_id,
    ptype,
    channel,
    fplay,
    thumb: Union[bool, str] = None,
):
    return [
        [
            primary_button(
                text="🎵",
                callback_data=(
                    f"AlonePlaylists "
                    f"{videoid}|"
                    f"{user_id}|"
                    f"{ptype}|a|"
                    f"{channel}|"
                    f"{fplay}"
                ),
            ),
            primary_button(
                text="🎥",
                callback_data=(
                    f"AlonePlaylists "
                    f"{videoid}|"
                    f"{user_id}|"
                    f"{ptype}|v|"
                    f"{channel}|"
                    f"{fplay}"
                ),
            ),
        ],
        [
            success_button(
                text="⎘",
                callback_data=(
                    f"PlaylistThumb "
                    f"{videoid}|"
                    f"{user_id}|"
                    f"{ptype}|"
                    f"{channel}|"
                    f"{fplay}"
                ),
            ),
            danger_button(
                text="✖",
                callback_data=(
                    f"forceclose "
                    f"{videoid}|{user_id}"
                ),
            ),
        ],
    ]


# ==========================================================
# LIVESTREAM MARKUP
# ==========================================================

def livestream_markup(
    _,
    videoid,
    user_id,
    mode,
    channel,
    fplay,
    thumb: Union[bool, str] = None,
):
    return [
        [
            primary_button(
                text="🎬",
                callback_data=(
                    f"LiveStream "
                    f"{videoid}|"
                    f"{user_id}|"
                    f"{mode}|"
                    f"{channel}|"
                    f"{fplay}"
                ),
            ),
        ],
        [
            success_button(
                text="⎘",
                callback_data=(
                    f"LiveThumb "
                    f"{videoid}|"
                    f"{user_id}|"
                    f"{mode}|"
                    f"{channel}|"
                    f"{fplay}"
                ),
            ),
            danger_button(
                text="✖",
                callback_data=(
                    f"forceclose "
                    f"{videoid}|{user_id}"
                ),
            ),
        ],
    ]


# ==========================================================
# SLIDER MARKUP
# ==========================================================

def slider_markup(
    _,
    videoid,
    user_id,
    query,
    query_type,
    channel,
    fplay,
    thumb: Union[bool, str] = None,
):
    query = str(query)[:20]

    return [
        [
            primary_button(
                text="🎵",
                callback_data=(
                    f"MusicStream "
                    f"{videoid}|"
                    f"{user_id}|a|"
                    f"{channel}|"
                    f"{fplay}"
                ),
            ),
            primary_button(
                text="🎥",
                callback_data=(
                    f"MusicStream "
                    f"{videoid}|"
                    f"{user_id}|v|"
                    f"{channel}|"
                    f"{fplay}"
                ),
            ),
        ],
        [
            success_button(
                text="◁",
                callback_data=(
                    f"slider B|"
                    f"{query_type}|"
                    f"{query}|"
                    f"{user_id}|"
                    f"{channel}|"
                    f"{fplay}"
                ),
            ),
            success_button(
                text="⎘",
                callback_data=(
                    f"SliderThumb "
                    f"{videoid}|"
                    f"{user_id}|"
                    f"{query}|"
                    f"{query_type}|"
                    f"{channel}|"
                    f"{fplay}"
                ),
            ),
            success_button(
                text="▷",
                callback_data=(
                    f"slider F|"
                    f"{query_type}|"
                    f"{query}|"
                    f"{user_id}|"
                    f"{channel}|"
                    f"{fplay}"
                ),
            ),
        ],
        [
            danger_button(
                text="✖",
                callback_data=(
                    f"forceclose "
                    f"{query}|{user_id}"
                ),
            ),
        ],
    ]
