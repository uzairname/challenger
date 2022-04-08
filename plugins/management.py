import typing

from utils.utils import *
from database import Database
import hikari
from __main__ import Bot
from __main__ import bot as bot_instance
from __init__ import *
import re

component = tanjun.Component(name="management module")

class settings:
    LOBBY = "lobbies"
    RESULTS = "results channel"
    REMOVE_LOBBY = "remove lobby"
    ELO_ROLES = "elo to roles"
    STAFF = "staff"


async def config_help_instructions(**kwargs):
    action = kwargs.get("action")
    embed = Custom_Embed(type=Embed_Type.INFO, title="Config Help", description="Config settings help")
    embed.description += "\n" + action
    return embed


@component.with_slash_command
@tanjun.with_str_slash_option("action", "action to perform")
@tanjun.as_slash_command("config-help", "settings commands help", default_to_ephemeral=False)
@take_input(input_instructions=config_help_instructions)
async def config_help(event, **kwargs) -> hikari.Embed:

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
@tanjun.with_str_slash_option("roles", "roles allowed", default="")
@tanjun.with_str_slash_option("name", "lobby name", default="")
@tanjun.with_str_slash_option("channel", "the channel to update or delete", default="")
@tanjun.with_str_slash_option("action", "what to do", choices={"update":"update", "delete":"delete"}, default="")
@tanjun.as_slash_command("config-lobby", "add, update, or delete a lobby and its roles", default_to_ephemeral=False)
@take_input(input_instructions=config_lobby_instructions)
async def config_lobby(ctx, event, action, name, roles, channel, **kwargs) -> hikari.Embed:

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



async def config_staff_instructions(ctx:tanjun.abc.Context, **kwargs):

    DB = Database(ctx.guild_id)

    staff_role = DB.get_config()["staff_role"]

    staff_list = "Staff role: <@&" + str(staff_role) + ">\n"
    if staff_role is None:
        staff_list = "No staff"
    else:
        members = bot_instance.rest.fetch_members(ctx.guild_id)
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

@component.with_slash_command
@tanjun.with_str_slash_option("role", "role", default="")
@tanjun.with_str_slash_option("action", "what to do", choices={"link role":"link role", "unlink role":"unlink role"}, default="Nothing")
@tanjun.as_slash_command("config-staff", "link a role to bot staff", default_to_ephemeral=False)
@take_input(input_instructions=config_staff_instructions)
async def config_staff(ctx:tanjun.abc.Context, event, action, role, **kwargs) -> hikari.Embed:

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
    if action == "link role":
        selection += "**Linking**\n"
    elif action == "unlink role":
        selection += "**Unlinking**\n"
    else:
        selection += "**No action specified**\n"
    input_params = InputParams(str(role))
    selection += input_params.describe()

    if min_elo and max_elo:
        selection += "Elo range:\n> " + str(min_elo) + " - " + str(max_elo)

    embed = hikari.Embed(title="Add or remove elo roles",
                        description="Link a role to an elo rank. Elo roles are displayed in the lobby and can be used to force match results",
                        color=Colors.PRIMARY)

    embed.add_field(name="Selection", value=selection)

    return embed

@component.with_slash_command()
@tanjun.with_str_slash_option("max_elo", "max elo", default="")
@tanjun.with_str_slash_option("min_elo", "min elo", default="")
@tanjun.with_str_slash_option("role", "role", default="")
@tanjun.with_str_slash_option("action", "what to do", choices={"link role":"link role", "unlink role":"unlink role"}, default="")
@tanjun.as_slash_command("config-elo-roles", "link a role to an elo range", default_to_ephemeral=False)
@take_input(input_instructions=config_elo_roles_instructions)
async def config_elo_roles(ctx, event, min_elo, max_elo, role, **kwargs) -> hikari.Embed:

    def process_response():
        input_params = InputParams(str(role))

        if len(input_params.roles) != 1:
            return "Select one role", Embed_Type.ERROR
        role_id = input_params.roles[0]

        elo_min = float(min_elo) if min_elo else float("-inf")
        elo_max = float(max_elo) if max_elo else float("inf")

        if elo_min > elo_max:
            return "Min elo cannot be greater than max elo", Embed_Type.ERROR

        DB = Database(ctx.guild_id)

        df = DB.get_elo_roles()

        df = df.loc[df["role"] != role].sort_values("priority")
        df["priority"] = range(len(df.index))
        row = pd.Series([role_id, len(df.index), elo_min, elo_max], index=["role", "priority", "elo_min", "elo_max"])
        df = pd.concat([df, pd.DataFrame(row).T])

        print(df)

        DB.upsert_elo_roles(df)
        return "Updated Elo Role", Embed_Type.CONFIRM

    confirm_message, embed_type = process_response()
    confirm_embed = Custom_Embed(type=embed_type, description=confirm_message)
    return confirm_embed




# @component.with_slash_command
# @tanjun.with_str_slash_option("setting", "What setting?",
#                               choices={"Add/edit a Lobby":settings.LOBBY, #config-lobby
#                                        "Delete a Lobby":settings.REMOVE_LOBBY,
#                                        "Results Channel":settings.RESULTS, #config-results
#                                        "Elo Roles":settings.ELO_ROLES, #config-eloroles
#                                        "Staff Members":settings.STAFF}) #config-staff
# @tanjun.as_slash_command("config", "settings (admin only)", default_to_ephemeral=True)
async def config_command(ctx:tanjun.abc.SlashContext, setting, bot: Bot = tanjun.injected(type=Bot), client: tanjun.Client = tanjun.injected(type=tanjun.Client)):

    #check that player is staff or lilapela

    DB = Database(ctx.guild_id)

    player_info = DB.get_players(ctx.author.id)
    if player_info.empty:
        await ctx.respond("pls register")
        return
    player_info = player_info.iloc[0]

    if player_info["staff"] != status.STAFF and player_info["user_id"] != LILAPELA:
        await ctx.respond("Missing permissions")
        return


    cancel_row = ctx.rest.build_action_row()
    (cancel_row.add_button(hikari.messages.ButtonStyle.DANGER, "Cancel")
            .set_label("Cancel")
            .set_emoji("❌")
            .add_to_container())

    if setting == settings.LOBBY:
        instructions_embed = hikari.Embed(
            title="Add a Lobby",
            description="Type the lobby name followed by its channel and allowed roles. Players must have at least one of your specified roles to join this lobby. \n\nFor example, \"Beginner Lobby #channel @beginner-role @verified-role\"")
    elif setting == settings.RESULTS:
        instructions_embed = hikari.Embed(
            title="Set the Result Announcements Channel",
            description="Select a channel to configure by typing it in chat")
    elif setting == settings.REMOVE_LOBBY:
        instructions_embed = hikari.Embed(
            title="Remove a Lobby",
            description="Type a channel to remove its lobby")
    elif setting == settings.ELO_ROLES:

        rbe_df = DB.get_config()["roles_by_elo"]

        rbe_list = "```\n"
        for i in rbe_df.index:
            guild_roles = (await ctx.fetch_guild()).get_roles()
            role_name = guild_roles[i]
            rbe_list += "\"" + str(role_name) + "\": " + str(rbe_df.loc[i]["min"]) + " to " + str(rbe_df.loc[i]["max"]) + " elo\n"
        rbe_list += "```"

        instructions_embed = hikari.Embed(
            title="Edit an elo Role",
            description="Automatically assign players in a certain elo range to a role. Type an elo range followed by the role to set it to. \n([min elo] to [max elo]) For example: \"`50 to 70 @gold-rank`\" \n(Negative elo is also possible lol)")
        instructions_embed.add_field(name="Current roles", value=rbe_list)

    elif setting == settings.STAFF:

        all_staff = DB.get_players(staff=status.STAFF)
        staff_list = "```\n"
        for i in all_staff["tag"]:
            staff_list += i + "\n"
        staff_list += "```"

        instructions_embed = hikari.Embed(
            title="Add/remove members from staff",
            description="Mention the players that you want to toggle staff permissions for")
        instructions_embed.add_field(name="Current staff", value=staff_list)

    await ctx.edit_initial_response(embed=instructions_embed)

    with bot.stream(hikari.MessageCreateEvent, timeout=DEFAULT_TIMEOUT).filter(('author', ctx.author)) as stream:
        async for event in stream:
            if event.message:
                await event.message.delete()

            input_embed = hikari.Embed(title="Updating Settings", description="")
            input_params = InputParams(event.content)

            if input_params.text:
                input_embed.description += "Input: **" + str(input_params["text"]) + "**\n"

            if input_params["channels"].size > 0:
                input_embed.description += "Selected channels:\n"
                for i in input_params["channels"]:
                    input_embed.description += "<#" + str(i) + ">\n"

            if input_params["roles"].size > 0:
                input_embed.description += "Selected roles:\n"
                for i in input_params["roles"]:
                    input_embed.description += "<@&" + str(i) + ">\n"

            if input_params["users"].size > 0:
                input_embed.description += "Selected users:\n"
                for i in input_params["users"]:
                    input_embed.description += "<@" + str(i) + ">\n"

            client.metadata['instructions embed'] = instructions_embed
            client.metadata['input embed'] = input_embed
            client.metadata['input params'] = input_params
            client.metadata['done embed'] = hikari.Embed(title="Done", description=" ")

            await ctx.edit_initial_response(embeds=[instructions_embed, input_embed], components=[])
            input_error = await confirm_settings_update(ctx, bot, client, setting)
            if input_error is not None:
                error_embed = hikari.Embed(title="**" + str(input_error) + "**")
                await ctx.edit_initial_response(embeds=[instructions_embed, error_embed], components=[])
            else:
                await ctx.edit_initial_response("Done", embeds=[client.metadata["done embed"]], components=[])
                return

    await ctx.edit_initial_response("Timed out", embeds=[], components=[])


async def confirm_settings_update(ctx: tanjun.abc.SlashContext, bot: Bot, client: tanjun.Client, setting):

    instructions_embed = client.metadata["instructions embed"]
    input_embed = client.metadata["input embed"]

    confirm_cancel = ctx.rest.build_action_row()
    (confirm_cancel.add_button(hikari.messages.ButtonStyle.SUCCESS, "Confirm")
            .set_label("Confirm")
            .set_emoji("✔️")
            .add_to_container())
    (confirm_cancel.add_button(hikari.messages.ButtonStyle.DANGER, "Cancel")
            .set_label("Cancel")
            .set_emoji("❌")
            .add_to_container())

    input_embed.title = "Confirm?"

    if setting == settings.LOBBY:
        if client.metadata["input params"]["roles"].size == 0:
            input_embed.description += "\n❗Warning: No roles entered. No one will be able to join this lobby\n"

    await ctx.edit_initial_response(embeds=[instructions_embed, input_embed], components=[confirm_cancel])

    with bot.stream(hikari.InteractionCreateEvent, timeout=DEFAULT_TIMEOUT).filter(("interaction.user.id", ctx.author.id)) as stream:
        async for event in stream:

            button_id = event.interaction.custom_id

            if button_id == "Cancel":
                return
            elif button_id != "Confirm":
                return "idk lol"

            if setting == settings.LOBBY:
                return update_lobby(ctx, client)
            elif setting == settings.RESULTS:
                return update_results_channel(ctx, client.metadata["input params"])
            elif setting == settings.ELO_ROLES:
                return update_elo_roles(ctx, client.metadata["input params"])

    await ctx.edit_initial_response("Timed out in confirmlobbyupdate", embeds=[], components=[])
    return


def update_lobby(ctx:tanjun.abc.Context, client:tanjun.Client):

    input_params = client.metadata["input params"]

    if not input_params["text"]:
        return "No name entered"
    elif not input_params["channels"].size == 1:
        return "Choose one channel"

    channel_id, roles, lobby_name = input_params["channels"][0], input_params["roles"], input_params["text"]

    DB = Database(ctx.guild_id)

    queue = DB.get_queues(channel_id)

    if not queue.empty:
        queue = queue.loc[0]
        queue["lobby_name"] = lobby_name
        queue["roles"] = roles
        DB.upsert_queue(queue)
    else:
        queue = DB.get_new_queue(channel_id)
        queue["lobby_name"] = lobby_name
        queue["roles"] = roles
        DB.upsert_queue(queue)

    client.metadata["done embed"].description="Updated lobby"


def update_results_channel(ctx:tanjun.abc.Context, input_params):

    if input_params["channels"].size != 1:
        return "Enter one channel to send results to"

    DB = Database(ctx.guild_id)

    config = DB.get_config()
    config["results_channel"] = input_params["channels"][0]
    DB.upsert_config(config)


def update_elo_roles(ctx:tanjun.abc.Context, input_params):

    if input_params["roles"].size != 1:
        return "Enter one role"

    pat = r"(-?[\d]+) to (-?[\d]+)"

    res = re.match(pat, input_params["text"])

    try:
        minelo = int(res.groups()[0])
        maxelo = int(res.groups()[1])
    except:
        return "Invalid input"

    role = input_params["roles"][0]

    DB = Database(ctx.guild_id)

    config = DB.get_config()
    rbe_df = config["roles_by_elo"]

    rbe_df = rbe_df.loc[rbe_df.index != role].sort_values("priority")
    rbe_df["priority"] = range(len(rbe_df.index))
    role_info = pd.Series([len(rbe_df.index), minelo, maxelo], index=["priority", "min", "max"], name=role)
    rbe_df = pd.concat([rbe_df, pd.DataFrame(role_info).T])

    config["roles_by_elo"] = rbe_df
    DB.upsert_config(config)





@component.with_slash_command
@tanjun.as_slash_command("reset", "reset the data for this server", default_to_ephemeral=False)
async def reset_cmd(ctx: tanjun.abc.Context):
    if ctx.author.id != 623257053879861248:
        await ctx.respond("not authorized")
        return



@tanjun.as_loader
def load(client: tanjun.abc.Client) -> None:
    client.add_component(component.copy())