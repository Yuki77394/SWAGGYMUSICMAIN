from typing import Union

from pyrogram.types import InlineKeyboardMarkup

from SWAGGYMUSIC.button_styles import (
    danger_button,
    primary_button,
    success_button,
)


# ==========================================================
# FIXED BUTTON STYLES
#
# Styles mirror KURIGRAMSWAG's utils/inline/queue.py:
# Queue = PRIMARY, Timer = SUCCESS, Back = PRIMARY,
# Close = DANGER. Colours never change between renders.
# ==========================================================


# ==========================================================
# QUEUE MARKUP
# ==========================================================

def queue_markup(
    _,
    DURATION,
    CPLAY,
    videoid,
    played: Union[bool, int] = None,
    dur: Union[bool, int] = None,
):
    not_dur = [
        [
            primary_button(
                text=_["QU_B_1"],
                callback_data=f"GetQueued {CPLAY}|{videoid}",
            ),
            danger_button(
                text=_["CLOSE_BUTTON"],
                callback_data="close",
            ),
        ]
    ]

    dur = [
        [
            success_button(
                text=_["QU_B_2"].format(played, dur),
                callback_data="GetTimer",
            )
        ],
        [
            primary_button(
                text=_["QU_B_1"],
                callback_data=f"GetQueued {CPLAY}|{videoid}",
            ),
            danger_button(
                text=_["CLOSE_BUTTON"],
                callback_data="close",
            ),
        ],
    ]

    upl = InlineKeyboardMarkup(
        not_dur if DURATION == "Unknown" else dur
    )

    return upl


# ==========================================================
# QUEUE BACK
# ==========================================================

def queue_back_markup(_, CPLAY):
    upl = InlineKeyboardMarkup(
        [
            [
                primary_button(
                    text=_["BACK_BUTTON"],
                    callback_data=f"queue_back_timer {CPLAY}",
                ),
                danger_button(
                    text=_["CLOSE_BUTTON"],
                    callback_data="close",
                ),
            ]
        ]
    )

    return upl


# ==========================================================
# ADMIN QUEUE CONTROLS
#
# The controls use the same fixed PRIMARY style as the player
# controls; Close uses DANGER.
# ==========================================================

def aq_markup(_, chat_id):
    buttons = [
        [
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
                text="▢",
                callback_data=f"ADMIN Stop|{chat_id}",
            ),
        ],
        [
            danger_button(
                text=_["CLOSE_BUTTON"],
                callback_data="close",
            )
        ],
    ]

    return buttons
