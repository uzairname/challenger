import os
import typing
import hikari


@typing.final
class Config:

    # version based on current month
    VERSION = '2022-04 2'

    OWNER_ID = 623257053879861248  # Lilapela's ID
    TESTING_GUILD_ID = 907729885726933043
    PX_GUILD_ID = 947184983120957452

    GITHUB_LINK = "https://github.com/lilapela/competition"




    COMPONENT_TIMEOUT = 120
    QUEUE_TIMEOUT = 300

    REQUIRED_PERMISSIONS = hikari.Permissions.NONE.SEND_MESSAGES.VIEW_CHANNEL.MANAGE_ROLES
    PERMS_ERR_MSG = f"The bot is missing some required permissions. Type /about to see them"

    if os.environ.get("ENVIRONMENT") == "development":
        INVITE_LINK = "https://discord.com/api/oauth2/authorize?client_id=951132825803964447&permissions=" + str(REQUIRED_PERMISSIONS.value) + "&scope=bot%20applications.commands"
    elif os.environ.get("ENVIRONMENT") == "production":
        INVITE_LINK =  ""




class Database_Config:
    TEST_GUILD_ID = 1 # Used for unit tests

    # known names for some known discord servers, for ease of use
    KNOWN_GUILDS = {Config.TESTING_GUILD_ID: "pela", Config.PX_GUILD_ID: "PX", TEST_GUILD_ID: "testing"}