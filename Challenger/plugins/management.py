import hikari
import tanjun
import pandas as pd

from Challenger.utils import *
from Challenger.config import Config
from Challenger.database import Guild_DB


config = tanjun.slash_command_group("config", "Change the bot settings", default_to_ephemeral=False)


@config.with_command
@tanjun.with_own_permission_check(Config.REQUIRED_PERMISSIONS, error_message=Config.PERMS_ERR_MSG)
@tanjun.as_slash_command("help", "settings commands help", default_to_ephemeral=True, always_defer=True)
async def config_help(ctx:tanjun.abc.Context, client:tanjun.abc.Client=tanjun.injected(type=tanjun.abc.Client)):

    help_embed = hikari.Embed(title="Config Help", description="Staff can use the following commands to change the bot settings. Type `/config [command name]` to use them", color=Colors.PRIMARY)
    help_embed.add_field(name="`lobbies`", value="View, add, or remove lobbies")
    help_embed.add_field(name="`staff`", value="Link or unlink a role to bot staff")
    help_embed.add_field(name="`elo-roles`", value="Set or unset roles that are automatically assigned to players based on their elo")
    help_embed.add_field(name="`match-updates-channel`", value="Set the channel for match updates")
    help_embed.add_field(name="`reset`", value="Reset all player and match data. Other settings will be preserved.")


    DB = Guild_DB(ctx.guild_id)

    lobbies_list = ""
    all_lobbies = DB.get_lobbies()
    if all_lobbies.empty:
        lobbies_list = "No lobbies"
    for index, lobby in all_lobbies.iterrows():
        lobbies_list += "\nLobby \"**" + str(lobby["lobby_name"]) + "**\" in channel <#" + str(
            lobby["channel_id"]) + ">"
        if lobby["required_role"]:
            lobbies_list += "\nWith required role <#" + lobby["required_role"] + ">"

    staff_role = DB.get_config()["staff_role"]
    if staff_role is None:
        staff_list = "No staff role specified. Anyone with the \"manage server\" permission is considered staff"
    else:
        staff_list = "Current staff role: <@&" + str(staff_role) + ">\nStaff:"
    members = client.rest.fetch_members(ctx.guild_id)
    async for member in members:
        if staff_role in member.role_ids:
            staff_list += "\n" + member.username


    elo_roles_list = ""

    elo_roles = DB.get_elo_roles()
    if elo_roles.empty:
        elo_roles_list = "No elo roles"
    for index, role in elo_roles.iterrows():
        elo_roles_list += "\n<@&" + str(index) + ">: " + str(role["min_elo"]) + " to " + str(role["max_elo"])

    current_settings_embed = hikari.Embed(title="Current Settings", color=Colors.SECONDARY)
    current_settings_embed.add_field(name="Lobbies", value=lobbies_list)
    current_settings_embed.add_field(name="Staff", value=staff_list)
    current_settings_embed.add_field(name="Elo Roles", value=elo_roles_list)

    await ctx.edit_initial_response(embeds=[help_embed, current_settings_embed])




async def config_lobby_instructions(ctx:tanjun.abc.Context, action, name, channel:hikari.InteractionChannel, role_required):
    """
    Displays all configured lobbies in the guild as a field added onto the embed
    params:
        DB: Database object
        embed: hikari.Embed to add to
    """
    DB = Guild_DB(ctx.guild_id)

    embed = hikari.Embed(
        title="Setup 1v1 lobbies",
        description="Each lobby has its own separate 1v1 queue, and is assigned to a channel. Enter the lobby name and the channel id. To delete a lobby, select the delete option. Required roles are optional. If specified, only players with those roles can join the queue in the lobby. To remove required roles from a lobby, enter no roles.", color=Colors.PRIMARY)

    lobbies_list = ""
    all_lobbies = DB.get_lobbies()
    if all_lobbies.empty:
        lobbies_list = "No lobbies"
    for index, lobby in all_lobbies.iterrows():
        lobbies_list += "\nLobby \"**" + str(lobby["lobby_name"]) + "**\" in channel <#" + str(
            lobby["channel_id"]) + ">"
        if lobby["role_required"]:
            lobbies_list += "\nWith required role <#" + lobby["role_required"] + ">"

    selection = ""
    if action == "delete":
        selection += "**Deleting lobby:**\n"
    elif action == "update":
        selection += "**Updating or adding lobby:**\n"
    else:
        selection += "**No action**\n"

    selection += "In channel: <#" + str(channel.id) + ">\n"
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
@tanjun.as_slash_command("lobbies", "add, update, or delete a lobby and its roles", default_to_ephemeral=False, always_defer=True)
@ensure_staff
@confirm_cancel_input(input_instructions=config_lobby_instructions)
async def config_lobby(ctx, action, name, role_required, channel, bot=tanjun.injected(type=hikari.GatewayBot)) -> hikari.Embed:

    DB = Guild_DB(ctx.guild_id)

    def confirm():

        if channel is None:
            return "Please enter a channel", Embed_Type.ERROR

        existing_queues = DB.get_lobbies(channel_id=channel.id)

        if action == "delete":
            if existing_queues.empty:
                return "No lobby in <#" + str(channel.id) + ">", Embed_Type.ERROR

            DB.delete_lobby(channel.id)
            return "Deleted lobby from <#" + str(channel.id) + ">", Embed_Type.CONFIRM

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

    confirm_message, confirm_embed_type = confirm()
    confirm_embed = Custom_Embed(type=confirm_embed_type, description=confirm_message)

    return confirm_embed



async def config_staff_instructions(ctx:tanjun.abc.Context, action, role:hikari.PartialRole, client=tanjun.injected(type=tanjun.abc.Client)):

    DB = Guild_DB(ctx.guild_id)

    staff_role = DB.get_config()["staff_role"]

    if staff_role is None:
        staff_list = "No staff role specified. Anyone with the \"manage server\" permission is considered staff"
    else:
        staff_list = "Current staff role: <@&" + str(staff_role) + ">\nStaff:"
        members = client.rest.fetch_members(ctx.guild_id)
        async for member in members:
            if staff_role in member.role_ids:
                staff_list += "\n" + member.username

    selection = ""
    if action == "link role":
        selection += "**Linking**\n"
    elif action == "unlink role":
        selection += "**Unlinking**\n"
    else:
        selection += "**No action specified**\n"

    if role is None:
        selection = "No role specified"
    else:
        selection += "Role: " + role.mention + ""

    embed = hikari.Embed(title="Add or remove staff members",
                        description="Link a role to bot staff. Staff are able to force match results, and have access to all config commands",
                        color=Colors.PRIMARY)
    embed.add_field(name="Current staff", value=staff_list)
    embed.add_field(name="Selection", value=selection)
    return embed

@config.with_command
@tanjun.with_own_permission_check(Config.REQUIRED_PERMISSIONS, error_message=Config.PERMS_ERR_MSG)
@tanjun.with_str_slash_option("action", "what to do", choices={"link role":"link role", "unlink role":"unlink role"}, default="link role")
@tanjun.with_role_slash_option("role", "role", default=None)
@tanjun.as_slash_command("staff", "link a role to bot staff", default_to_ephemeral=False, always_defer=True)
@ensure_staff
@confirm_cancel_input(input_instructions=config_staff_instructions)
async def config_staff(ctx: tanjun.abc.Context, action, role, bot=tanjun.injected(type=hikari.GatewayBot), **kwargs) -> hikari.Embed:

    DB = Guild_DB(ctx.guild_id)

    def confirm():

        if role is None:
            return "Select one role", Embed_Type.ERROR

        config = DB.get_config()

        if action == "link role":
            config["staff_role"] = role.id
            DB.upsert_config(config)
            return "Bot staff is now " + role.mention, Embed_Type.CONFIRM
        elif action == "unlink role":
            config["staff_role"] = None
            DB.upsert_config(config)
            return "Removed staff role", Embed_Type.CONFIRM

    confirm_message, embed_type = confirm()
    confirm_embed = Custom_Embed(type=embed_type, description=confirm_message)
    return confirm_embed


#config elo roles
async def config_elo_roles_instructions(ctx:tanjun.abc.Context, action, role, min_elo, max_elo, **kwargs):

    DB = Guild_DB(ctx.guild_id)

    selection = ""

    if role is not None:
        if action == "link role":
            selection += "**Connecting role**\n"
        else:
            selection += "**Removing**\n"

        selection += role.mention
        selection += "\nTo elo range: **" + str(min_elo) + " to " + str(max_elo) + "**"
    else:
        selection = "No role specified. Confirming will refresh everyone's roles"

    embed = hikari.Embed(title="Add or remove elo roles",
                        description="Link a role to an elo rank. Roles are automatically updated when a user's elo changes",
                        color=Colors.PRIMARY)

    embed.add_field(name="Selection", value=selection)

    return embed

@config.with_command
@tanjun.with_own_permission_check(Config.REQUIRED_PERMISSIONS, error_message=Config.PERMS_ERR_MSG)
@tanjun.with_str_slash_option("action", "what to do", choices={"link role":"link role", "unlink role":"unlink role"}, default="link role")
@tanjun.with_str_slash_option("max_elo", "max elo", default=float("inf"))
@tanjun.with_str_slash_option("min_elo", "min elo", default=float("-inf"))
@tanjun.with_role_slash_option("role", "role", default=None)
@tanjun.as_slash_command("elo-roles", "link a role to an elo range", default_to_ephemeral=False, always_defer=True)
@ensure_staff
@confirm_cancel_input(input_instructions=config_elo_roles_instructions)
async def config_elo_roles(ctx:tanjun.abc.Context, min_elo, max_elo, action, role:hikari.Role, bot=tanjun.injected(type=hikari.GatewayBot)) -> hikari.Embed:

    async def process_response(bot):

        if role is None:
            return "Select one role", Embed_Type.ERROR
        role_id = role.id

        DB = Guild_DB(ctx.guild_id)

        if action == "unlink role":
            DB.delete_elo_role(role_id)
            return "Unlinked role", Embed_Type.CONFIRM

        elo_min = float(min_elo)
        elo_max = float(max_elo)

        if elo_min > elo_max:
            return "Min elo cannot be greater than max elo", Embed_Type.ERROR

        df = DB.get_elo_roles()

        df = df.loc[df.index != role]
        row = pd.Series([elo_min, elo_max], index=["min_elo", "max_elo"], name=role_id)
        df = pd.concat([df, pd.DataFrame(row).T])

        DB.upsert_elo_roles(df)

        players = DB.get_players()
        await ctx.respond("Updating roles...")
        async for message in update_players_elo_roles(ctx, bot, players, role_ids=[role_id]):
            await ctx.edit_last_response(message)



        return "Updated Elo Role", Embed_Type.CONFIRM

    confirm_message, embed_type = await process_response(bot)
    confirm_embed = Custom_Embed(type=embed_type, description=confirm_message)
    return confirm_embed



async def config_results_channel_instructions(ctx:tanjun.abc.Context, action, channel, **kwargs):

    DB = Guild_DB(ctx.guild_id)

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
    selection += "<#" + str(channel.id) + ">"

    embed = hikari.Embed(title="Add or remove results channel",
                        description="Set a channel for match announcements. Results are posted in the channel when a match is initially created, when the result is decided by the players, and when staff updates a match's result",
                        color=Colors.PRIMARY)
    embed.add_field(name="Current Results Channel", value=cur_results_channel)
    embed.add_field(name="Selection", value=selection)

    return embed

@config.with_command
@tanjun.with_own_permission_check(Config.REQUIRED_PERMISSIONS, error_message=Config.PERMS_ERR_MSG)
@tanjun.with_str_slash_option("action", "what to do", choices={"update":"add/update channel", "remove":"reset to default"}, default="update")
@tanjun.with_channel_slash_option("channel", "channel", default=None)
@tanjun.as_slash_command("match-updates-channel", "Set a channel to send match results announcements to", default_to_ephemeral=False, always_defer=True)
@ensure_staff
@confirm_cancel_input(input_instructions=config_results_channel_instructions)
async def config_results_channel(ctx:tanjun.abc.Context, action, channel, bot=tanjun.injected(type=hikari.GatewayBot), **kwargs) -> hikari.Embed:

    def process_repsonse():

        DB = Guild_DB(ctx.guild_id)
        config = DB.get_config()

        if action == "remove":
            config["results_channel"] = None
            DB.upsert_config(config)
            return "Removed results channel", Embed_Type.CONFIRM

        if channel is None:
            return "Select a channel", Embed_Type.ERROR

        config["results_channel"] = channel.id
        DB.upsert_config(config)
        return "Updated results channel", Embed_Type.CONFIRM

    confirm_message, embed_type = process_repsonse()
    confirm_embed = Custom_Embed(type=embed_type, description=confirm_message)
    return confirm_embed


async def reset_instructions(**kwargs):

    embed = hikari.Embed(title="Reset all player and match data",
                        description="All players will be unregistered and all match history will be deleted for this server. Config settigs will remain the same, such as elo roles, staff, etc. This is useful when starting a new season.\n\n:warning:**WARNING:** This action cannot be undone",
                        color=Colors.PRIMARY)
    return embed

@config.with_command
@tanjun.with_own_permission_check(Config.REQUIRED_PERMISSIONS, error_message=Config.PERMS_ERR_MSG)
@tanjun.as_slash_command("reset", "reset player and match data (asks for confirmation)", default_to_ephemeral=False)
@ensure_staff
@confirm_cancel_input(input_instructions=reset_instructions)
async def reset_data(ctx: tanjun.abc.SlashContext, bot=tanjun.injected(type=hikari.GatewayBot), **kwargs) -> hikari.Embed:

    def process_response():

        DB = Guild_DB(ctx.guild_id)

        DB.delete_all_matches()
        DB.delete_all_players()

        return "Reset all data", Embed_Type.CONFIRM

    confirm_message, embed_type = process_response()
    confirm_embed = Custom_Embed(type=embed_type, description=confirm_message)
    return confirm_embed



management = tanjun.Component(name="management", strict=True).load_from_scope().make_loader()