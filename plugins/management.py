import typing

from utils.utils import *
from database import Database
import tanjun
import hikari
from __main__ import Bot

component = tanjun.Component(name="management module")

class settings:
    LOBBY = "lobbies"
    RESULTS = "results channel"
    REMOVE_LOBBY = "remove lobby"
    ELO_ROLES = "elo to roles"
    STAFF = "staff"


async def config_help_instructions(**kwargs):
    embed = Custom_Embed(type=Embed_Type.INFO, title="Config Help", description="Config settings help")
    return embed

@component.with_slash_command
@tanjun.with_own_permission_check(Config.REQUIRED_PERMISSIONS, error_message=Config.PERMS_ERR_MSG)
@tanjun.as_slash_command("config-help", "settings commands help", default_to_ephemeral=False, always_defer=True)
@check_errors
@take_input(input_instructions=config_help_instructions)
@check_staff_perms
async def config_help(event, bot=tanjun.injected(type=Bot), **kwargs) -> hikari.Embed:

    button_id = event.interaction.custom_id

    def process_input():
        if button_id == "Cancel":
            return "Cancelled", Embed_Type.CANCEL
        if button_id != "Confirm":
            return "Invalid button", Embed_Type.ERROR
        return "Confirmed", Embed_Type.CONFIRM

    confirm_message, type = process_input()
    confirm_embed = Custom_Embed(type=type, description=confirm_message)
    return confirm_embed



async def config_lobby_instructions(ctx:tanjun.abc.Context, action, name, channel, roles, **kwargs):
    """
    Displays all configured lobbies in the guild as a field added onto the embed
    params:
        DB: Database object
        embed: hikari.Embed to add to
    """
    DB = Database(ctx.guild_id)

    embed = Custom_Embed(type=Embed_Type.INFO,
        title="Setup 1v1 lobbies",
        description="Each channel can have one lobby with its own separate queue. To add, edit, or delete a lobby, enter the channel name followed by its name (optional) and allowed roles. To remove required roles from a lobby, enter no roles. A registered player with at least one of these roles can join the lobby")

    lobbies_list = ""
    all_lobbies = DB.get_queues()
    if all_lobbies.empty:
        lobbies_list = "No lobbies"
    for index, lobby in all_lobbies.iterrows():
        lobbies_list += "\nLobby \"**" + str(lobby["lobby_name"]) + "**\" in channel <#" + str(
            lobby["channel_id"]) + "> Roles allowed: "
        for role in lobby["roles"]:
            lobbies_list += "<@&" + str(role) + ">"

    selection = ""
    if action == "delete":
        selection += "**Deleting lobby:**\n"
    elif action == "update":
        selection += "**Updating or adding lobby:**\n"
    else:
        selection += "**No action**\n"
    input_params = InputParams(str(name) + str(channel) + str(roles))
    selection += input_params.describe()

    embed.add_field(name="Current lobbies", value=lobbies_list)
    embed.add_field(name="Your selection", value=selection)
    return embed

@component.with_slash_command
@tanjun.with_own_permission_check(Config.REQUIRED_PERMISSIONS, error_message=Config.PERMS_ERR_MSG)
@tanjun.with_role_slash_option("roles", "roles allowed", default="")
@tanjun.with_str_slash_option("name", "lobby name", default="")
@tanjun.with_str_slash_option("channel", "the channel to update or delete", default="")
@tanjun.with_str_slash_option("action", "what to do", choices={"update":"update", "delete":"delete"}, default="")
@tanjun.as_slash_command("config-lobby", "add, update, or delete a lobby and its roles", default_to_ephemeral=False, always_defer=True)
@check_errors
@take_input(input_instructions=config_lobby_instructions)
@check_staff_perms
async def config_lobby(ctx, event, action, name, roles, channel, bot=tanjun.injected(type=Bot), **kwargs) -> hikari.Embed:

    DB = Database(ctx.guild_id)

    user_input = InputParams(str(name) + str(channel) + str(roles))

    def process_response():

        if user_input.channels.size != 1:
            return "Please enter one channel", Embed_Type.ERROR

        existing_queues = DB.get_queues(channel_id=user_input.channels[0])

        if action == "delete":
            if existing_queues.empty:
                return "No lobby in <#" + str(user_input.channels[0]) + ">", Embed_Type.ERROR

            queue = existing_queues.iloc[0]
            DB.remove_queue(queue)
            return "Deleted lobby in <#" + str(user_input.channels[0]) + ">", Embed_Type.CONFIRM

        if existing_queues.empty:
            new_queue = DB.get_new_queue(user_input.channels[0])
            new_queue["lobby_name"] = user_input.text
            new_queue["roles"] = user_input.roles
            DB.upsert_queue(new_queue)
            return "Added new lobby", Embed_Type.CONFIRM

        existing_queue = existing_queues.loc[0]
        if user_input.text:
            existing_queue["lobby_name"] = user_input.text

        existing_queue["roles"] = user_input.roles
        DB.upsert_queue(existing_queue)
        return "Updated existing lobby", Embed_Type.CONFIRM

    confirm_message, embed_type = process_response()
    confirm_embed = Custom_Embed(type=embed_type, title="", description=confirm_message)

    return confirm_embed



async def config_staff_instructions(ctx:tanjun.abc.Context, client=tanjun.injected(type=tanjun.abc.Client), **kwargs):

    DB = Database(ctx.guild_id)

    staff_role = DB.get_config()["staff_role"]

    if staff_role is None:
        staff_list = "No staff role specified. Anyone with the \"manage server\" permission is considered staff"
    else:
        staff_list = "Current staff role: <@&" + str(staff_role) + ">\nStaff:"
        members = client.rest.fetch_members(ctx.guild_id)
        async for member in members:
            if staff_role in member.role_ids:
                staff_list += "\n" + member.username

    action = kwargs.get("action")
    role = kwargs.get("role")

    selection = ""
    if action == "link role":
        selection += "**Linking**\n"
    elif action == "unlink role":
        selection += "**Unlinking**\n"
    else:
        selection += "**No action specified**\n"
    input_params = InputParams(str(role))
    selection += input_params.describe()

    embed = hikari.Embed(title="Add or remove staff members",
                        description="Link a role to bot staff. Staff are able to force match results, and have access to all config commands",
                        color=Colors.PRIMARY)

    embed.add_field(name="Current staff", value=staff_list)
    embed.add_field(name="Selection", value=selection)

    return embed


def get_client(client:tanjun.abc.Client=tanjun.injected(type=tanjun.abc.Client)):
    return client

@component.with_slash_command
@tanjun.with_own_permission_check(Config.REQUIRED_PERMISSIONS, error_message=Config.PERMS_ERR_MSG)
@tanjun.with_role_slash_option("role", "role", default="")
@tanjun.with_str_slash_option("action", "what to do", choices={"link role":"link role", "unlink role":"unlink role"}, default="Nothing")
@tanjun.as_slash_command("config-staff", "link a role to bot staff", default_to_ephemeral=False, always_defer=True)
@check_errors
@take_input(input_instructions=config_staff_instructions)
@check_staff_perms
async def config_staff(ctx: tanjun.abc.Context, event, action, role, bot=tanjun.injected(type=Bot), **kwargs) -> hikari.Embed:

    DB = Database(ctx.guild_id)

    def process_response():
        input_params = InputParams(str(role))

        if len(input_params.roles) != 1:
            return "Select one role", Embed_Type.ERROR

        config = DB.get_config()
        staff_role = config["staff_role"]

        if action == "link role":
            staff_role = input_params.roles[0]
            config["staff_role"] = staff_role
            DB.upsert_config(config)
            return "Linked staff with " + "<@&" + str(staff_role) + ">", Embed_Type.CONFIRM
        elif action == "unlink role":
            staff_role = None
            config["staff_role"] = staff_role
            DB.upsert_config(config)
            return "Removed staff role", Embed_Type.CONFIRM

    confirm_message, embed_type = process_response()
    confirm_embed = Custom_Embed(type=embed_type, description=confirm_message)
    return confirm_embed


#config elo roles
async def config_elo_roles_instructions(ctx:tanjun.abc.Context, action, role, min_elo, max_elo, **kwargs):

    DB = Database(ctx.guild_id)

    selection = ""

    if role is not None:
        if action == "link role":
            selection += "**Linking**\n"
        else:
            selection += "**Unlinking**\n"

        selection += role.mention

    selection += "\nElo range:\n> **" + str(min_elo) + " to " + str(max_elo) + "**"

    embed = hikari.Embed(title="Add or remove elo roles",
                        description="Link a role to an elo rank. Elo roles are displayed in the lobby and can be used to force match results",
                        color=Colors.PRIMARY)

    embed.add_field(name="Selection", value=selection)

    return embed

@component.with_slash_command()
@tanjun.with_own_permission_check(Config.REQUIRED_PERMISSIONS, error_message=Config.PERMS_ERR_MSG)
@tanjun.with_str_slash_option("max_elo", "max elo", default=float("inf"))
@tanjun.with_str_slash_option("min_elo", "min elo", default=float("-inf"))
@tanjun.with_role_slash_option("role", "role", default=None)
@tanjun.with_str_slash_option("action", "what to do", choices={"link role":"link role", "unlink role":"unlink role"}, default="link role")
@tanjun.as_slash_command("config-elo-roles", "link a role to an elo range", default_to_ephemeral=False, always_defer=True)
@check_errors
@take_input(input_instructions=config_elo_roles_instructions)
@check_staff_perms
async def config_elo_roles(ctx, event, min_elo, max_elo, role:hikari.Role, bot=tanjun.injected(type=Bot), **kwargs) -> hikari.Embed:

    def process_response():

        if role is None:
            return "Select one role", Embed_Type.ERROR
        role_id = role.id

        elo_min = float(min_elo)
        elo_max = float(max_elo)

        if elo_min > elo_max:
            return "Min elo cannot be greater than max elo", Embed_Type.ERROR

        DB = Database(ctx.guild_id)
        df = DB.get_elo_roles()

        df = df.loc[df["role"] != role].sort_values("priority")
        df["priority"] = range(len(df.index))
        row = pd.Series([role_id, len(df.index), elo_min, elo_max], index=["role", "priority", "elo_min", "elo_max"])
        df = pd.concat([df, pd.DataFrame(row).T]).reset_index(drop=True)

        DB.upsert_elo_roles(df)
        return "Updated Elo Role", Embed_Type.CONFIRM

    confirm_message, embed_type = process_response()
    confirm_embed = Custom_Embed(type=embed_type, description=confirm_message)
    return confirm_embed



async def config_results_channel_instructions(ctx:tanjun.abc.Context, action, channel, **kwargs):

    DB = Database(ctx.guild_id)

    results_channel = DB.get_config()["results_channel"]

    if results_channel is not None:
        cur_results_channel = "<#" + str(results_channel) + ">"
    else:
        cur_results_channel = "No results channel set"

    selection = ""
    if action == "update":
        selection += "**Setting channel to**\n"
    elif action == "remove":
        selection += "**Removing channel**\n"
    else:
        selection += "**No action specified**\n"
    input_params = InputParams(str(channel))
    selection += input_params.describe()

    embed = hikari.Embed(title="Add or remove results channel",
                        description="Link a channel to the results channel. Results channel is where match results are posted",
                        color=Colors.PRIMARY)
    embed.add_field(name="Current Results Channel", value=cur_results_channel)
    embed.add_field(name="Selection", value=selection)

    return embed

@component.with_slash_command()
@tanjun.with_own_permission_check(Config.REQUIRED_PERMISSIONS, error_message=Config.PERMS_ERR_MSG)
@tanjun.with_str_slash_option("action", "what to do", choices={"update":"add/update channel", "remove":"reset to default"}, default="update")
@tanjun.with_str_slash_option("channel", "channel", default="")
@tanjun.as_slash_command("config-results-channel", "Set a results channel", default_to_ephemeral=False, always_defer=True)
@check_errors
@take_input(input_instructions=config_results_channel_instructions)
async def config_results_channel(ctx:tanjun.abc.Context, event, action, channel, bot=tanjun.injected(type=Bot), **kwargs) -> hikari.Embed:

    def process_repsonse():
        input_params = InputParams(str(channel))

        DB = Database(ctx.guild_id)
        config = DB.get_config()

        if action == "remove":
            config["results_channel"] = None
            DB.upsert_config(config)
            return "Removed results channel", Embed_Type.CONFIRM

        if len(input_params.channels) != 1:
            return "Select one channel", Embed_Type.ERROR

        config["results_channel"] = input_params.channels[0]
        DB.upsert_config(config)
        return "Updated results channel", Embed_Type.CONFIRM

    confirm_message, embed_type = process_repsonse()
    confirm_embed = Custom_Embed(type=embed_type, description=confirm_message)
    return confirm_embed


async def reset_instructions(ctx:tanjun.abc.Context, reset_config, **kwargs):

    embed = hikari.Embed(title="Reset all player data",
                        description="All players will be unregistered. Config settigs will be preserved, unless reset config is selected",
                        color=Colors.PRIMARY)
    embed.add_field(name="Resetting config: " + str(reset_config), value="*_ _*")

    return embed

@component.with_slash_command
@tanjun.with_own_permission_check(Config.REQUIRED_PERMISSIONS, error_message=Config.PERMS_ERR_MSG)
@tanjun.with_str_slash_option("reset_config", "also reset config settings", choices={"yes":"yes", "no":"no"}, default="no")
@tanjun.as_slash_command("reset", "reset the data for this server", default_to_ephemeral=False)
@check_errors
@take_input(input_instructions=reset_instructions)
async def reset_data(ctx: tanjun.abc.SlashContext, event, reset_config, bot=tanjun.injected(type=Bot), **kwargs) -> hikari.Embed:
    raise NotImplementedError("Not implemented")


@tanjun.as_loader
def load(client: tanjun.abc.Client) -> None:
    client.add_component(component.copy())