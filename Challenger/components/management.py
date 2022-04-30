import hikari
import tanjun
import pandas as pd

from Challenger.helpers import *
from Challenger.config import App
from Challenger.database import *


config = tanjun.slash_command_group("config", "Change the bot settings", default_to_ephemeral=False)



# @config.with_command
# @tanjun.with_own_permission_check(App.REQUIRED_PERMISSIONS, error_message=App.PERMS_ERR_MSG)
# @tanjun.with_str_slash_option("name", "lobby name", default=None)
# @tanjun.with_channel_slash_option("channel", "the channel to update or delete", default=None)

@config.with_command
@tanjun.with_str_slash_option("leaderboard", "the leaderboard to connect this lobby to")
@tanjun.with_channel_slash_option("channel", "The channel for the 1v1 lobby")
@tanjun.as_slash_command("lobby", "Add or remove lobbies")
async def config_lobby(ctx:tanjun.abc.Context, channel, leaderboard):

    leaderboard_name = leaderboard

    guild = Guild.objects(guild_id=ctx.guild_id).first()
    if not guild:
        guild = Guild(guild_id=ctx.guild_id)

    #get a lobby matching the channel id if it exists
    lobby = None
    for lb in guild.leaderboards:
        lobby = lb.lobbies.filter(channel_id=channel.id).first()
        if lobby:
            break

    #get the specified leaderboard
    leaderboard = guild.leaderboards.filter(name=leaderboard_name).first()
    if not leaderboard:
        await ctx.respond("No leaderboard found with that name")
        return

    #add or update the lobby
    if lobby:
        await ctx.respond("Nothing updated")
    else:
        lobby = Lobby(channel_id=channel.id)
        leaderboard.lobbies.append(lobby)


    guild.save()



@config.with_command
@tanjun.with_str_slash_option("name", "leaderboard's name", default=None)
@tanjun.as_slash_command("leaderboard", "Add or remove leaderboards")
async def config_leaderboard(ctx:tanjun.abc.Context, name):

    guild = Guild.objects(guild_id=ctx.guild_id).first()
    if not guild:
        guild = Guild(guild_id=ctx.guild_id)

    leaderboard = guild.leaderboards.filter(name=name).first()

    if leaderboard:
        leaderboard.name = name
    else:
        leaderboard = Leaderboard(name=name)
        guild.leaderboards.append(leaderboard)

    guild.save()






@config.with_command
@tanjun.with_own_permission_check(App.REQUIRED_PERMISSIONS, error_message=App.PERMS_ERR_MSG)
@tanjun.as_slash_command("help", "settings commands help", default_to_ephemeral=True, always_defer=True)
async def config_help(ctx:tanjun.abc.Context, client:tanjun.abc.Client=tanjun.injected(type=tanjun.abc.Client)):

    help_embed = hikari.Embed(title="Config Help", description="Staff can use the following commands to change the bot settings. Type `/config [command name]` to use them. Enter the command without any parameters too view the command instructions.", color=Colors.PRIMARY)
    help_embed.add_field(name="`lobbies`", value="View, add, or remove lobbies")
    help_embed.add_field(name="`staff`", value="Specify a role to link to bot staff. To reset this to the default, set the option \"action\" to \"unlink role\"")
    help_embed.add_field(name="`elo-roles`", value="Set or unset roles that are automatically assigned to players based on their elo")
    help_embed.add_field(name="`match-updates-channel`", value="Set the channel where results of 1v1s are announced. By default, announcements are made in the channel where players declare the results of their 1v1s")
    help_embed.add_field(name="`reset`", value="Reset all player and match data. Other settings will be preserved.")


    DB = Guild_DB(ctx.guild_id)

    lobbies_list = ""
    all_lobbies = DB.get_lobbies()
    if all_lobbies.empty:
        lobbies_list = "No lobbies"
    for index, lobby in all_lobbies.iterrows():
        lobbies_list += "\nLobby \"**" + str(lobby["lobby_name"]) + "**\" in channel <#" + str(
            lobby["channel_id"]) + ">"

    staff_role = DB.get_config()["staff_role"]
    if staff_role is None:
        staff_list = "No staff role specified. Anyone with the \"manage server\" permission is considered staff"
    else:
        staff_list = "Current staff role: <@&" + str(staff_role) + ">"


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

    selection = ""
    if action == "delete":
        selection += "**Deleting lobby:**\n"
    elif action == "update":
        selection += "**Updating or adding lobby:**\n"
    else:
        selection += "**No action**\n"

    if channel:
        selection += "In channel: <#" + str(channel.id) + ">\n"
        if name:
            selection += "With name: " + name + "\n"
        if role_required:
            selection += "With required role: " + role_required.mention + "\n"
    else:
        selection = ""

    embed.add_field(name="Current lobbies", value=lobbies_list)
    if selection:
        embed.add_field(name="Your selection", value=selection)
    return embed

@config.with_command
@tanjun.with_own_permission_check(App.REQUIRED_PERMISSIONS, error_message=App.PERMS_ERR_MSG)
@tanjun.with_str_slash_option("action", "what to do", choices={"update":"update", "delete":"delete"}, default="update")
@tanjun.with_str_slash_option("name", "lobby name", default=None)
@tanjun.with_channel_slash_option("channel", "the channel to update or delete", default=None)
@tanjun.as_slash_command("lobbies", "add, update, or delete a lobby and its roles", default_to_ephemeral=False, always_defer=True)
@ensure_staff
@confirm_cancel_input(input_instructions=config_lobby_instructions)
async def config_lobby(ctx:tanjun.abc.Context, action, name, channel, bot=tanjun.injected(type=hikari.GatewayBot)) -> hikari.Embed:

    DB = Guild_DB(ctx.guild_id)

    def confirm():

        if channel is None:
            return "Please enter a channel", Embed_Type.ERROR

        existing_queues = DB.get_lobbies(channel_id=channel.channel_id)

        if action == "delete":
            if existing_queues.empty:
                return "No lobby in <#" + str(channel.channel_id) + ">", Embed_Type.ERROR

            DB.delete_lobby(channel.channel_id)
            return "Deleted lobby from <#" + str(channel.channel_id) + ">", Embed_Type.CONFIRM

        if existing_queues.empty:
            new_queue = DB.get_new_lobby(channel.channel_id)
            if name is None:
                return "Please enter a name", Embed_Type.ERROR
            new_queue["lobby_name"] = name
            DB.upsert_lobby(new_queue)
            return "Added new lobby", Embed_Type.CONFIRM

        existing_queue = existing_queues.loc[0]

        if name:
            existing_queue["lobby_name"] = name

        DB.upsert_lobby(existing_queue)
        return "Updated existing lobby", Embed_Type.CONFIRM

    confirm_message, confirm_embed_type = confirm()
    confirm_embed = Custom_Embed(type=confirm_embed_type, description=confirm_message)

    return confirm_embed



async def config_staff_instructions(ctx:tanjun.abc.Context, action, role:hikari.PartialRole):

    DB = Guild_DB(ctx.guild_id)

    selection = ""
    if action == "link role":
        selection += "**Linking**\n"
        if role is None:
            selection = "No role specified"
        else:
            selection += "Role: " + role.mention + ""

    elif action == "unlink role":
        selection += "**Removing staff role. Anyone with the manage server permissions will be considered staff**\n"
    else:
        selection += "**No action specified**\n"


    embed = hikari.Embed(title="Add or remove staff members",
                        description="Link a role to bot staff. Staff are able to force match results, and have access to all config commands",
                        color=Colors.PRIMARY)
    embed.add_field(name="Selection", value=selection)
    return embed

@config.with_command
@tanjun.with_own_permission_check(App.REQUIRED_PERMISSIONS, error_message=App.PERMS_ERR_MSG)
@tanjun.with_str_slash_option("action", "what to do", choices={"link role":"link role", "unlink role":"unlink role"}, default="link role")
@tanjun.with_role_slash_option("role", "role", default=None)
@tanjun.as_slash_command("staff", "link a role to bot staff", default_to_ephemeral=False, always_defer=True)
@ensure_staff
@confirm_cancel_input(input_instructions=config_staff_instructions)
async def config_staff(ctx: tanjun.abc.Context, action, role, bot=tanjun.injected(type=hikari.GatewayBot), **kwargs) -> hikari.Embed:

    DB = Guild_DB(ctx.guild_id)

    def confirm():

        config = DB.get_config()

        if action == "unlink role":
            config["staff_role"] = None
            DB.upsert_config(config)
            return "Removed staff role", Embed_Type.CONFIRM

        if role is None:
            return "Select one role", Embed_Type.ERROR

        if action == "link role":
            config["staff_role"] = role.channel_id
            DB.upsert_config(config)
            return "Bot staff is now " + role.mention, Embed_Type.CONFIRM

    confirm_message, embed_type = confirm()
    confirm_embed = Custom_Embed(type=embed_type, description=confirm_message)
    return confirm_embed


#config elo roles
async def config_elo_roles_instructions(ctx:tanjun.abc.Context, action, role, min_elo, max_elo, **kwargs):

    DB = Guild_DB(ctx.guild_id)

    selection_str = ""
    action_str = ""
    if role is not None:
        if action == "link role":
            action_str = "**Connecting role**\n"
        elif action == "unlink role":
            action_str = "**Removing**\n"

        selection_str += role.mention
        selection_str += "\nTo elo range: **" + str(min_elo) + " to " + str(max_elo) + "**"
    else:
        selection_str = "No role specified. Confirming will refresh everyone's roles"

    embed = hikari.Embed(title="Add or remove elo roles",
                        description="Link a role to an elo rank. Roles are automatically updated when a user's elo changes. Leave the min or max option blank to set them to infinity",
                        color=Colors.PRIMARY)
    if action_str:
        embed.add_field(name=action_str, value=selection_str)

    return embed

@config.with_command
@tanjun.with_own_permission_check(App.REQUIRED_PERMISSIONS, error_message=App.PERMS_ERR_MSG)
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
    action_str = ""
    if channel is not None:
        if action == "update":
            action_str = "**Setting channel to**\n"
        elif action == "remove":
            action_str += "**Removing channel**\n"

        selection += "<#" + str(channel.channel_id) + ">"

    embed = hikari.Embed(title="Add or remove results channel",
                        description="Set a channel for match announcements. Results are posted in the channel when a match is initially created, when the result is decided by the players, and when staff updates a match's result",
                        color=Colors.PRIMARY)
    embed.add_field(name="Current Results Channel", value=cur_results_channel)

    if action_str:
        embed.add_field(name=action_str, value=selection)

    return embed

@config.with_command
@tanjun.with_own_permission_check(App.REQUIRED_PERMISSIONS, error_message=App.PERMS_ERR_MSG)
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

        config["results_channel"] = channel.channel_id
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
@tanjun.with_own_permission_check(App.REQUIRED_PERMISSIONS, error_message=App.PERMS_ERR_MSG)
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