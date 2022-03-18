import tanjun

from plugins.utils import *
from __main__ import DB
import hikari
from __main__ import PelaBot
import re

DEFAULT_TIMEOUT = 120


component = tanjun.Component(name="management module")


def parse_input(string):
    text_pat = r"[a-zA-Z\d\s]+"

    channel_pat = r"<#(\d{17,19})>"
    role_pat = r"<@&(\d{17,19})>"
    user_pat = r"<@(\d{17,19})>"

    name = re.match(text_pat, string)
    if name:
        name = name[0].strip()

    channels = re.findall(channel_pat, string)
    roles = re.findall(role_pat, string)
    users = re.findall(user_pat, string)

    return {"name": name, "channels": channels, "roles": roles, "users":users}



class options:
    LOBBY = "lobby channels"
    RESULTS = "results channel"
@component.with_slash_command
@tanjun.with_str_slash_option("setting", "setting", choices={"lobby channels":options.LOBBY, "results channel":options.RESULTS})
@tanjun.as_slash_command("config", "settings (admin only)", default_to_ephemeral=True)
async def config_command(ctx:tanjun.abc.SlashContext, setting, bot: PelaBot = tanjun.injected(type=PelaBot), client: tanjun.Client = tanjun.injected(type=tanjun.Client)):



    if setting == options.LOBBY:
        instructions_embed = hikari.Embed(
            title="Add a Lobby",
            description="Type the lobby name followed by its channels and allowed roles.\nFor example, \"Beginner Lobby #channel @beginner-role @verified-role\"\n")

    elif setting == options.RESULTS:
        instructions_embed = hikari.Embed(
            title="Add a Results Channel",
            description="Select a channel to configure by typing it in chat")

    await ctx.edit_initial_response(embed=instructions_embed)

    with bot.stream(hikari.MessageCreateEvent, timeout=DEFAULT_TIMEOUT).filter(('author', ctx.author)) as stream:
        async for event in stream:
            await event.message.delete()

            input_embed = hikari.Embed(title="Your Selection", description="")
            input_params = parse_input(event.content)

            if input_params["name"]:
                input_embed.description += "Name: **" + str(input_params["name"]) + "**\n"

            input_embed.description += "Selected channels:\n"
            for i in input_params["channels"]:
                input_embed.description += "<#" + str(i) + ">\n"

            input_embed.description += "Selected roles:\n"
            for i in input_params["roles"]:
                input_embed.description += "<@&" + str(i) + ">\n"

            await ctx.edit_initial_response(embeds=[instructions_embed, input_embed], components=[])

            input_error = check_input(setting, input_params)
            if input_error:
                instructions_embed.description += "/n" + str(input_error)
            else:
                client.metadata['input embed'] = input_embed
                client.metadata['input params'] = input_params
                if await confirm_settings_update(ctx, bot, client, setting):
                    return

            await ctx.edit_initial_response(embed=instructions_embed, components=[])

    await ctx.edit_initial_response("Timed out", embeds=[], components=[])


def check_input(settings_category, input_params): #returns an error message to the command user, or returns nothing if input is fine

    if settings_category == options.LOBBY:
        if not input_params["name"]:
            return "No name entered"
        elif not input_params["channels"]:
            return "Enter a channel"

    if settings_category == options.RESULTS:
        return


async def confirm_settings_update(ctx: tanjun.abc.SlashContext, bot: PelaBot, client: tanjun.Client, setting):

    input_embed = client.metadata["input embed"]

    row = ctx.rest.build_action_row()
    (row.add_button(hikari.messages.ButtonStyle.SUCCESS, "Confirm")
            .set_label("Confirm")
            .set_emoji("✔️")
            .add_to_container())
    (row.add_button(hikari.messages.ButtonStyle.DANGER, "Cancel")
            .set_label("Cancel")
            .set_emoji("❌")
            .add_to_container())

    confirm_embed = hikari.Embed(title= "", description="")

    if setting == options.LOBBY:
        confirm_embed.title = "Updating/adding a Lobby"
        if not client.metadata["input params"]["roles"]:
            confirm_embed.description += "\n❗No roles entered. No one will be able to join this lobby\n"

    await ctx.edit_initial_response(embeds=[input_embed, confirm_embed], components=[row])

    with bot.stream(hikari.InteractionCreateEvent, timeout=DEFAULT_TIMEOUT).filter(("interaction.user.id", ctx.author.id)) as stream:
        async for event in stream:
            button_id = event.interaction.custom_id

            if button_id == "Cancel":
                return False
            elif button_id != "Confirm":
                return False

            i = client.metadata["input params"]
            if setting == options.LOBBY:
                message = update_lobby(ctx, i)

            confirm_embed.description += message
            await ctx.edit_initial_response(embed=confirm_embed)
            return True

    await ctx.edit_initial_response("Timed out in confirmlobbyupdate", embeds=[], components=[])
    return True


def update_lobby(ctx:tanjun.abc.Context, input_params):

    DB.open_connection(ctx.guild_id)
    q_df = DB.get_all_queues()
    new_q = pd.Series([input_params["name"], input_params["channels"], input_params["roles"]], ["queue_name", "channels", "roles"])
    replaced = q_df.loc[q_df["queue_name"] == new_q["queue_name"]] #the name of the existing queues that was replaced, if any
    new_q_df = replace_row_if_col_matches(q_df, new_q, "queue_name")
    DB.set_all_queues(new_q_df)
    DB.close_connection()

    if replaced.empty:
        return "Added new lobby \"" + str(input_params["name"]) + "\""
    else:
        return "Updated existing lobby \"" + str(replaced.loc[0, "queue_name"]) + "\""


def remove_lobby(ctx:tanjun.abc.Client, input_params):
    pass



@component.with_slash_command
@tanjun.as_slash_command("reset", "reset the data for this server", default_to_ephemeral=True)
async def reset_cmd(ctx: tanjun.abc.Context):
    if ctx.author.id != 623257053879861248:
        await ctx.respond("not authorized")
        return

    DB.open_connection(ctx.guild_id)

    def reset_all_tables():
        DB.reset_players_table()
        DB.reset_matches_table()
        DB.reset_queues_table()

    reset_all_tables()
    await ctx.respond("reset")

    DB.close_connection()



@tanjun.as_loader
def load(client: tanjun.abc.Client) -> None:
    client.add_component(component.copy())