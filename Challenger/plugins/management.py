import hikari
import tanjun
import pandas as pd

from Challenger.utils import *
from Challenger.config import Config
from Challenger.database import Session



config = tanjun.slash_command_group("config", "Change the bot settings", default_to_ephemeral=False)


async def config_help_instructions(**kwargs):
    embed = Custom_Embed(type=Embed_Type.INFO, title="Config Help", description="Config settings help")
    return embed

@config.with_command
@tanjun.with_own_permission_check(Config.REQUIRED_PERMISSIONS, error_message=Config.PERMS_ERR_MSG)
@tanjun.as_slash_command("help", "settings commands help", default_to_ephemeral=False, always_defer=True)
@take_input(input_instructions=config_help_instructions)
@ensure_staff
async def config_help(event, bot=tanjun.injected(type=hikari.GatewayBot), **kwargs) -> hikari.Embed:

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



async def config_lobby_instructions(ctx:tanjun.abc.Context, action, name, channel, role_required, **kwargs):
    """
    Displays all configured lobbies in the guild as a field added onto the embed
    params:
        DB: Database object
        embed: hikari.Embed to add to
    """
    DB = Session(ctx.guild_id)

    embed = Custom_Embed(type=Embed_Type.INFO,
        title="Setup 1v1 lobbies",
        description="Each lobby has its own separate 1v1 queue, and is assigned to a channel. Enter the lobby name and the channel id. To delete a lobby, select the delete option. Required roles are optional. If specified, only players with those roles can join the queue in the lobby. To remove required roles from a lobby, enter no roles.")

    lobbies_list = ""
    all_lobbies = DB.get_lobbies()
    if all_lobbies.empty:
        lobbies_list = "No lobbies"
    for index, lobby in all_lobbies.iterrows():
        lobbies_list += "\nLobby \"**" + str(lobby["lobby_name"]) + "**\" in channel <#" + str(
            lobby["channel_id"]) + ">"
        if lobby["role_required"]:
            lobbies_list += "\nWith required role " + lobby[role_required].mention

    selection = ""
    if action == "delete":
        selection += "**Deleting lobby:**\n"
    elif action == "update":
        selection += "**Updating or adding lobby:**\n"
    else:
        selection += "**No action**\n"

    selection += "In channel: " + channel.mention + "\n"
    if name:
        selection += "With name: " + name + "\n"
    if role_required:
        selection += "With required role: " + role_required.mention + "\n"

    embed.add_field(name="Current lobbies", value=lobbies_list)
    embed.add_field(name="Your selection", value=selection)
    return embed

@config.with_command
@tanjun.with_own_permission_check(Config.REQUIRED_PERMISSIONS, error_message=Config.PERMS_ERR_MSG)
@tanjun.with_str_slash_option("action", "what to do", choices={"update":"update", "delete":"delete"}, default="update")
@tanjun.with_str_slash_option("name", "lobby name", default=None)
@tanjun.with_role_slash_option("role_required", "role required", default=None)
@tanjun.with_channel_slash_option("channel", "the channel to update or delete", default=None)
@tanjun.as_slash_command("lobby", "add, update, or delete a lobby and its roles", default_to_ephemeral=False, always_defer=True)
@take_input(input_instructions=config_lobby_instructions)
@ensure_staff
async def config_lobby(ctx, event, action, name, role_required, channel, bot=tanjun.injected(type=hikari.GatewayBot), **kwargs) -> hikari.Embed:

    DB = Session(ctx.guild_id)

    user_input = InputParser(str(name))

    def process_response():

        if channel is None:
            return "Please enter a channel", Embed_Type.ERROR

        existing_queues = DB.get_lobbies(channel_id=channel.id)

        if action == "delete":
            if existing_queues.empty:
                return "No lobby in " + channel.mention, Embed_Type.ERROR

            DB.remove_lobby(channel.id)
            return "Deleted lobby from " + channel.mention, Embed_Type.CONFIRM

        if existing_queues.empty:
            new_queue = DB.get_new_lobby(channel.id)
            if name is None:
                return "Please enter a name", Embed_Type.ERROR
            new_queue["lobby_name"] = name
            new_queue["role_required"] = role_required
            DB.upsert_lobby(new_queue)
            return "Added new lobby", Embed_Type.CONFIRM

        existing_queue = existing_queues.loc[0]

        if name:
            existing_queue["lobby_name"] = name

        existing_queue["role_required"] = role_required
        DB.upsert_lobby(existing_queue)
        return "Updated existing lobby", Embed_Type.CONFIRM

    confirm_message, embed_type = process_response()
    confirm_embed = Custom_Embed(type=embed_type, title="", description=confirm_message)

    return confirm_embed



async def config_staff_instructions(ctx:tanjun.abc.Context, client=tanjun.injected(type=tanjun.abc.Client), **kwargs):

    DB = Session(ctx.guild_id)

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
    input_params = InputParser(str(role))
    selection += input_params.describe()

    embed = hikari.Embed(title="Add or remove staff members",
                        description="Link a role to bot staff. Staff are able to force match results, and have access to all config commands",
                        color=Colors.PRIMARY)

    embed.add_field(name="Current staff", value=staff_list)
    embed.add_field(name="Selection", value=selection)

    return embed

@config.with_command
@tanjun.with_own_permission_check(Config.REQUIRED_PERMISSIONS, error_message=Config.PERMS_ERR_MSG)
@tanjun.with_role_slash_option("role", "role", default="")
@tanjun.with_str_slash_option("action", "what to do", choices={"link role":"link role", "unlink role":"unlink role"}, default="Nothing")
@tanjun.as_slash_command("staff", "link a role to bot staff", default_to_ephemeral=False, always_defer=True)
@take_input(input_instructions=config_staff_instructions)
@ensure_staff
async def config_staff(ctx: tanjun.abc.Context, event, action, role, bot=tanjun.injected(type=hikari.GatewayBot), **kwargs) -> hikari.Embed:

    DB = Session(ctx.guild_id)

    def process_response():
        input_params = InputParser(str(role))

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

    DB = Session(ctx.guild_id)

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

@config.with_command
@tanjun.with_own_permission_check(Config.REQUIRED_PERMISSIONS, error_message=Config.PERMS_ERR_MSG)
@tanjun.with_str_slash_option("max_elo", "max elo", default=float("inf"))
@tanjun.with_str_slash_option("min_elo", "min elo", default=float("-inf"))
@tanjun.with_role_slash_option("role", "role", default=None)
@tanjun.with_str_slash_option("action", "what to do", choices={"link role":"link role", "unlink role":"unlink role"}, default="link role")
@tanjun.as_slash_command("elo-roles", "link a role to an elo range", default_to_ephemeral=False, always_defer=True)
@take_input(input_instructions=config_elo_roles_instructions)
@ensure_staff
async def config_elo_roles(ctx, event, min_elo, max_elo, role:hikari.Role, bot=tanjun.injected(type=hikari.GatewayBot), **kwargs) -> hikari.Embed:

    def process_response():

        if role is None:
            return "Select one role", Embed_Type.ERROR
        role_id = role.id

        elo_min = float(min_elo)
        elo_max = float(max_elo)

        if elo_min > elo_max:
            return "Min elo cannot be greater than max elo", Embed_Type.ERROR

        DB = Session(ctx.guild_id)
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

    DB = Session(ctx.guild_id)

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
    input_params = InputParser(str(channel))
    selection += input_params.describe()

    embed = hikari.Embed(title="Add or remove results channel",
                        description="Link a channel to the results channel. Results channel is where match results are posted",
                        color=Colors.PRIMARY)
    embed.add_field(name="Current Results Channel", value=cur_results_channel)
    embed.add_field(name="Selection", value=selection)

    return embed

@config.with_command
@tanjun.with_own_permission_check(Config.REQUIRED_PERMISSIONS, error_message=Config.PERMS_ERR_MSG)
@tanjun.with_str_slash_option("action", "what to do", choices={"update":"add/update channel", "remove":"reset to default"}, default="update")
@tanjun.with_str_slash_option("channel", "channel", default="")
@tanjun.as_slash_command("results-channel", "Set a results channel", default_to_ephemeral=False, always_defer=True)
@take_input(input_instructions=config_results_channel_instructions)
async def config_results_channel(ctx:tanjun.abc.Context, event, action, channel, bot=tanjun.injected(type=hikari.GatewayBot), **kwargs) -> hikari.Embed:

    def process_repsonse():
        input_params = InputParser(str(channel))

        DB = Session(ctx.guild_id)
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


@config.with_command
@tanjun.with_own_permission_check(Config.REQUIRED_PERMISSIONS, error_message=Config.PERMS_ERR_MSG)
@tanjun.with_str_slash_option("reset_config", "also reset config settings", choices={"yes":"yes", "no":"no"}, default="no")
@tanjun.as_slash_command("reset", "reset the bot's data for this server", default_to_ephemeral=False)
@take_input(input_instructions=reset_instructions)
async def reset_data(ctx: tanjun.abc.SlashContext, event, reset_config, bot=tanjun.injected(type=hikari.GatewayBot), **kwargs) -> hikari.Embed:
    raise NotImplementedError()


management = tanjun.Component(name="management", strict=True).load_from_scope().make_loader()