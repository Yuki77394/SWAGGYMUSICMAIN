import config
from SWAGGYMUSIC import app
from SWAGGYMUSIC.button_styles import primary_button, success_button


def start_panel(_):
    return [[
        primary_button(text=_["S_B_1"], url=f"https://t.me/{app.username}?startgroup=true", icon_custom_emoji_id=6100125944381444896),
        success_button(text=_["S_B_4"], url=config.SUPPORT_CHAT),
    ]]


def private_panel(_):
    return [
        [primary_button(text=_["S_B_1"], url=f"https://t.me/{app.username}?startgroup=true", icon_custom_emoji_id=6100125944381444896)],
        [primary_button(text=_["S_B_3"], callback_data="open_help", icon_custom_emoji_id=5260512129240276089)],
        [
            success_button(text="⌯ ᴏᴡɴᴇʀ ⌯", user_id=config.OWNER_ID, icon_custom_emoji_id=6237864166879663987),
            success_button(text="⌯ ɴᴇᴛᴡᴏʀᴋ ⌯", url="https://t.me/SpIcYxNeTwOrK", icon_custom_emoji_id=6039381989985882045),
        ],
    ]
