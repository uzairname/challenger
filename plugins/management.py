import tanjun

from plugins.utils import *
from database import Database
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

    return {"text": name, "channels": channels, "roles": roles, "users":users}



class options:
    LOBBY = "lobbies"
    RESULTS = "results channel"
@component.with_slash_command
@tanjun.with_str_slash_option("setting", "setting", choices={"lobby channels":options.LOBBY, "results channel":options.RESULTS})
@tanjun.as_slash_command("config", "settings (admin only)", default_to_ephemeral=True)
async def config_command(ctx:tanjun.abc.SlashContext, setting, bot: PelaBot = tanjun.injected(type=PelaBot), client: tanjun.Client = tanjun.injected(type=tanjun.Client)):



    if setting == options.LOBBY:
        instructions_embed = hikari.Embed(
            title="Add a Lobby",
            description="Type the lobby name followed by its channel and allowed roles.\nFor example, \"Beginner Lobby #channel @beginner-role @verified-role\"\nEach lobby can only be set to one channel, but each channel can have multiple lobbies")

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

            if input_params["text"]:
                input_embed.description += "Name: **" + str(input_params["text"]) + "**\n"

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
        if not input_params["text"]:
            return "No name entered"
        elif not len(input_params["channels"]) == 1:
            return "Choose one channel"
        else:
            return

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

    channel_id, roles, lobby_name = input_params["channels"][0], input_params["roles"], input_params["text"]

    DB = Database(ctx.guild_id)

    queue_info = DB.get_queues(channel_id)

    if not queue_info.empty:
        queue_info = queue_info.loc[0]
        queue_info["lobby_name"] = lobby_name
        queue_info["roles"] = roles
        DB.upsert_queue(queue_info)
        message = "Updated existing lobby for<#" + str(queue_info["channel_id"]) + ">"
    else:
        DB.add_new_queue(channel_id, lobby_name=lobby_name, roles=roles)
        message = "Added new lobby \"" + str(input_params["text"]) + "\""

    return message


def remove_lobby(ctx:tanjun.abc.Client, input_params):
    pass



@component.with_slash_command
@tanjun.as_slash_command("reset", "reset the data for this server", default_to_ephemeral=True)
async def reset_cmd(ctx: tanjun.abc.Context):
    if ctx.author.id != 623257053879861248:
        await ctx.respond("not authorized")
        return



@tanjun.as_loader
def load(client: tanjun.abc.Client) -> None:
    client.add_component(component.copy())