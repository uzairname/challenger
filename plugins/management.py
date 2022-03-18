import tanjun

from plugins.utils import *
from __main__ import DB
import hikari
from __main__ import PelaBot
import re


component = tanjun.Component(name="management module")


def parse_input(string):
    text_pat = r"[a-zA-Z\d\s]+"
    channel_pat = r"<#(\d{17,19})>"
    role_pat = r"<@&(\d{17,19})>"

    name = re.match(text_pat, string)
    if name:
        name = name[0].strip()

    channels = re.findall(channel_pat, string)
    roles = re.findall(role_pat, string)

    return {"name": name, "channels": channels, "roles": roles}



class settings:
    LOBBY = "lobby channels"
    RESULTS = "results channel"
@component.with_slash_command
@tanjun.with_str_slash_option("setting", "setting", choices={"lobby channels":settings.LOBBY, "results channel":settings.RESULTS})
@tanjun.as_slash_command("config", "settings (admin only)", default_to_ephemeral=True)
async def config_command(ctx:tanjun.abc.SlashContext, setting, bot: PelaBot = tanjun.injected(type=PelaBot), client: tanjun.Client = tanjun.injected(type=tanjun.Client)):

    if setting == settings.LOBBY:

        row = ctx.rest.build_action_row()
        (
            row.add_button(hikari.messages.ButtonStyle.SUCCESS, "Confirm")
                .set_label("Confirm")
                .set_emoji("✔️")
                .add_to_container()
        )
        (
            row.add_button(hikari.messages.ButtonStyle.DANGER, "Cancel")
                .set_label("Cancel")
                .set_emoji("❌")
                .add_to_container()
        )
        client.metadata["confirm row"] = row
        embed = hikari.Embed(title="Add a Lobby", description="Type the lobby name followed by its channels and allowed roles.\nFor example, \"Beginner Lobby #channel @beginner-role @verified-role\"\n")
        await ctx.edit_initial_response(embed=embed)

        with bot.stream(hikari.MessageCreateEvent, timeout=60).filter(('author', ctx.author)) as stream:
            async for event in stream:
                await event.message.delete()

                input_params = parse_input(event.content)

                embed.description += "\nLobby name: **" + str(input_params["name"]) + "**\n"
                embed.description += "Selected channels:\n"
                for i in input_params["channels"]:
                    embed.description += "<#" + str(i) + ">\n"
                embed.description += "Selected roles:\n"
                for i in input_params["roles"]:
                    embed.description += "<@&" + str(i) + ">\n"

                valid_input = True
                if not input_params["name"]:
                    valid_input = False
                elif not input_params["channels"]:
                    valid_input = False

                await ctx.edit_initial_response(embed=embed, components=[])

                if valid_input:
                    client.metadata['embed'] = embed
                    client.metadata['input'] = input_params
                    if await confirm_lobby_update(ctx, bot, client):
                        return
                else:
                    embed.description += "/n❗Invalid input"

                await ctx.edit_initial_response(embed=embed, components=[])
                embed.description="Type the lobby name followed by its channels and allowed roles.\nFor example, \"Beginner Lobby #channel @beginner-role @verified-role\"\n"


        await ctx.edit_initial_response("Timed out", embeds=[], components=[])
    elif setting == settings.RESULTS:
        embed = hikari.Embed(title="Add a results channel", description="Select a channel to configure. Type in chat")
        await ctx.edit_initial_response(embed=embed)




async def confirm_lobby_update(ctx: tanjun.abc.SlashContext, bot: PelaBot, client: tanjun.Client):

    embed = client.metadata["embed"]
    btn_row = client.metadata["confirm row"]

    if not client.metadata["input"]["roles"]:
        embed.description += "\n❗No roles entered. No one will be able to join this lobby\n"

    await ctx.edit_initial_response(embed=embed, components=[btn_row])

    with bot.stream(hikari.InteractionCreateEvent, timeout=60).filter(("interaction.user.id", ctx.author.id)) as stream:
        async for event in stream:
            button = event.interaction.custom_id
            print(button)

            if button == "Cancel":
                print("cancel")
                return False
            elif button != "Confirm":
                print("Not Confirm")
                return False
            #button is confirm

            i = client.metadata["input"]
            message = update_lobby(ctx, i["name"], i["channels"], i["roles"])

            embed.description += message

            await ctx.edit_initial_response(embed=embed)
            return True

    await ctx.edit_initial_response("Timed out in confirmlobbyupdate", embeds=[], components=[])


def update_lobby(ctx:tanjun.abc.Context, name, channels, roles):

    DB.open_connection(ctx.guild_id)
    q_df = DB.get_all_queues()

    new_q = construct_df([[name, channels, roles]], ["queue_name", "channels", "roles"])

    replaced = q_df.loc[q_df["queue_name"] == new_q.loc[0, "queue_name"]]
    new_q_df = replace_row_if_col_matches(q_df, new_q, "queue_name")

    DB.set_all_queues(new_q_df)
    DB.close_connection()

    if not replaced.empty:
        return "Updated existing lobby \"" + str(replaced.loc[0, "queue_name"]) + "\""
    else:
        return "Added new lobby \"" + str(name) + "\""



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