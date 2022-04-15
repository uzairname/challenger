import typing
import hikari


@typing.final
class Config:

    OWNER_ID = 623257053879861248  # Lilapela's ID
    TESTING_GUILD_ID = 907729885726933043
    PX_GUILD_ID = 947184983120957452
    TESTING_INVITE_LINK = "https://discord.com/api/oauth2/authorize?client_id=951132825803964447&permissions=544857254992&scope=bot%20applications.commands"
    INVITE_LINK = "https://discord.com/api/oauth2/authorize?client_id=908432840566374450&permissions=544857254992&scope=bot%20applications.commands"


    DEFAULT_TIMEOUT = 120

    REQUIRED_PERMISSIONS = hikari.Permissions.NONE.SEND_MESSAGES
    PERMS_ERR_MSG = f"Make sure the bot has the following permissions: ```{REQUIRED_PERMISSIONS}```"


    all_plugins = ["help", "management", "matches", "misc", "player", "queue"]


@typing.final
class Colors: #TODO move to utils
    PRIMARY = "#ffc07d"
    SECONDARY = "#03212e"
    NEUTRAL = "#a5a5a5"
    SUCCESS = "#5dde07"
    ERROR = "#db4737"