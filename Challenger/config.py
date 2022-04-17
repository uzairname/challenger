import typing
import hikari


@typing.final
class Config:

    OWNER_ID = 623257053879861248  # Lilapela's ID
    TESTING_GUILD_ID = 907729885726933043
    PX_GUILD_ID = 947184983120957452
    TESTING_INVITE_LINK = "https://discord.com/api/oauth2/authorize?client_id=951132825803964447&permissions=544857254992&scope=bot%20applications.commands"
    INVITE_LINK = "https://discord.com/api/oauth2/authorize?client_id=908432840566374450&permissions=544857254992&scope=bot%20applications.commands"


    COMPONENT_TIMEOUT = 120
    QUEUE_TIMEOUT = 60

    REQUIRED_PERMISSIONS = hikari.Permissions.NONE.SEND_MESSAGES
    PERMS_ERR_MSG = f"The bot is missing some required permissions. Type /about to see them"



class Database_Config:
    TEST_GUILD_ID = 1 # Used for unit tests

    # known names for some known discord servers, for ease of use
    KNOWN_GUILDS = {Config.TESTING_GUILD_ID: "pela", Config.PX_GUILD_ID: "PX", TEST_GUILD_ID: "testing"}