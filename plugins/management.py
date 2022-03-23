import tanjun

from plugins.utils import *
from database import Database
import hikari
from __main__ import PelaBot
from __init__ import *
import re



component = tanjun.Component(name="management module")





class settings:
    LOBBY = "lobbies"
    RESULTS = "results channel"
    REMOVE_LOBBY = "remove lobby"
    ELO_ROLES = "elo to roles"
    STAFF = "staff"

@component.with_slash_command
@tanjun.with_str_slash_option("setting", "What setting?",
                              choices={"Add/edit a Lobby":settings.LOBBY,
                                       "Delete a Lobby":settings.REMOVE_LOBBY,
                                       "Results Channel":settings.RESULTS,
                                       "Elo Roles":settings.ELO_ROLES,
                                       "Staff Members":settings.STAFF})
@tanjun.as_slash_command("config", "settings (admin only)", default_to_ephemeral=True)
async def config_command(ctx:tanjun.abc.SlashContext, setting, bot: PelaBot = tanjun.injected(type=PelaBot), client: tanjun.Client = tanjun.injected(type=tanjun.Client)):

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
            input_params = parse_input(event.content)

            if input_params["text"]:
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


async def confirm_settings_update(ctx: tanjun.abc.SlashContext, bot: PelaBot, client: tanjun.Client, setting):

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
            elif setting == settings.STAFF:
                return update_staff(ctx, client)

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


def remove_lobby(ctx:tanjun.abc.Client, input_params):

    pass


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


def update_staff(ctx:tanjun.abc.Context, client):

    input_params = client.metadata["input params"]

    toggle_users = input_params["users"]

    if toggle_users.size == 0:
        return "Enter at least 1 user"

    DB = Database(ctx.guild_id)

    message = ""

    for id in toggle_users:
        players = DB.get_players(user_id=id)
        if players.empty:
            message += "\n Unknown or unregistered user: <@!" + str(id) + ">"
            continue
        player = players.iloc[0]
        if player["staff"] != status.STAFF:
            player["staff"] = status.STAFF
        else:
            player["staff"] = None
        DB.upsert_player(player)

    #
    # config = DB.get_config()
    # cur_staff = config["staff"]
    #
    # new_staff = np.union1d(np.setdiff1d(cur_staff, toggle_users), np.setdiff1d(toggle_users, cur_staff))
    # print("new staff: "+ str(new_staff))
    #
    # config["staff"] = new_staff
    # DB.upsert_config(config)





@component.with_slash_command
@tanjun.as_slash_command("reset", "reset the data for this server", default_to_ephemeral=True)
async def reset_cmd(ctx: tanjun.abc.Context):
    if ctx.author.id != 623257053879861248:
        await ctx.respond("not authorized")
        return



@tanjun.as_loader
def load(client: tanjun.abc.Client) -> None:
    client.add_component(component.copy())