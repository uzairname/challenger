import hikari

import interactions
from plugins.utils import *
from __init__ import *
from __main__ import PelaBot
from __main__ import bot
import time
from hikari.interactions.base_interactions import ResponseType


component = tanjun.Component(name="hi module")


bot_todo = """
**In order of priority**
• Provisional Bayesian Elo for your first 5 games beause it's more accurate. https://www.remi-coulom.fr/Bayesian-Elo/. But at the same time, it's most effective when a small number of games are played and computationally expensive. https://www.warzone.com/Forum/362170-bayesian-elo-versus-regular-elo
• Staff commands parameters should be an option within the slash command
• Give better instructions with /help
• Link staff roles with discord role
• Automatically assign roles based on Elo
Players are unranked until provisional elo is done (2 games)
• /configure option to select map when match starts, and /map choose random map
• remove player from queue after 10 mins
• show when opponent declares result, and when there's a conflict
• /join records match time
• /history show your recent matches
• see distribution of everyone's elo
• /stats show your percentile
• Associate each match with a message id in match announcements, so that message can be edited
• /compare (player) show your expected probability of beating opponent. Elo change for winning and losing 
• make displayed results pretty
• make a better bot icon
• shorthand for commands ex. declare match results /d"""

bot_features = """
Actual Matchmaking. When you join the queue, you get matched with people of similar elo, and the longer you wait, the broader the search.

Ability to change old match results. When your elo change depends on the elo difference, fixing the result of an old match (for whatever reason, maybe it was declared wrong or someone was caught boosting and their impact needs to be reverted) has a cascading effect on all the subsequent players those players played against, and the players they played against, and so on... since your elo change depends on your and your opponent's prior elo."""

@component.with_slash_command
@tanjun.as_slash_command("help", "About", default_to_ephemeral=True)
async def hi_test(ctx: tanjun.abc.Context) -> None:

    about_embed = hikari.Embed(title="About", description=f"Hi {ctx.author.mention}😋! This is a competetive ranking bot. 1v1 other players to climb the elo leaderboards! \n\nDM me with any comments, questions, or suggestions", colour=PELA_CYAN)
    about_embed.set_footer("Lilapela#1234")

    basic_embed = hikari.Embed(title="Getting Started", description="To get started, type /register", colour=PELA_CYAN)
    basic_embed.add_field(name="Queue", value="**/join** - Join the queue to be matched with another player\n**/leave** - Leave the queue\n**/queue** - View the status of the queue\n**/declare [win, loss, draw, or cancel]** - declare the results of the match. Both players must agree for result to be decided. If there's a dispute, ask staff to handle it", inline=True)
    basic_embed.add_field(name="Players", value="**/register** - Register your username and gain access to most features!\n**/stats** - View your stats\n/leaderboard - View the leaderboard\n", inline=True)

    util_embed = hikari.Embed(title="Utility", description="Useful and fun commands", colour=PELA_CYAN)
    util_embed.add_field(name="Other commands", value="**/uptime** - See how long since the bot's last reset\n**/invite-pela** - Get the link to invite the bot to your own server")

    staff_embed = hikari.Embed(title="Staff Commands", description="People with a staff role can use these commands. Enter the config commands without any parameters to see details", colour=PELA_CYAN)
    staff_embed.add_field(name="commands", value="**/lobby-config**\n**/elo-roles**\n/**set** - force a match's result, in the event of a dispute or mistake\n**/reset** Reset all match history and everyone's elo in the server. Preserves all other settings. Use this, for example, when starting a new season")

    notes_embed = hikari.Embed(title="Notes", description="This bot is still in development. Any bug reports or suggested features would be appreciated!", colour=PELA_CYAN)
    notes_embed.add_field(name="What I'm working on", value=bot_todo[0:1000])
    notes_embed.add_field(name="Possible Future Features", value=bot_features)
    notes_embed.add_field(name="Github", value="View the source code\nhttps://github.com/lilapela/competition")


    pages = {"About": about_embed, "Basics": basic_embed, "Staff Commands": staff_embed, "Development Notes": notes_embed}

    page_dropdown = ctx.rest.build_action_row().add_select_menu("page select")
    for i in pages:
        page_dropdown = page_dropdown.add_option(i, i).set_is_default(i=="About").add_to_menu()
    page_dropdown = page_dropdown.add_to_container()

    cur_page = "About"

    await ctx.edit_initial_response(embeds=[about_embed], components=[page_dropdown], user_mentions=True)

    with bot.stream(hikari.InteractionCreateEvent, timeout=DEFAULT_TIMEOUT).filter(("interaction.type", interactions.InteractionType.MESSAGE_COMPONENT)) as stream:
        async for event in stream:
            await event.interaction.create_initial_response(ResponseType.DEFERRED_MESSAGE_UPDATE)
            page = event.interaction.values[0]
            print(str(page_dropdown.components[0]) + "\n\n")
            for i in page_dropdown.components[0]._options:
                i.set_is_default(i._label == page)

            await ctx.edit_initial_response(embed=pages[page], components=[page_dropdown])


@component.with_slash_command
@tanjun.as_slash_command("invite-pela", "invite pela to your own server", default_to_ephemeral=False)
async def hi_test(ctx: tanjun.abc.Context) -> None:
    await ctx.respond(f"This is the invite link: " + INVITE_LINK)


@component.with_slash_command
@tanjun.as_slash_command("uptime", "get Pela's uptime", default_to_ephemeral=False)
async def uptime(ctx:tanjun.abc.Context, bot:PelaBot=tanjun.injected(type=PelaBot)) -> None:
    time_diff = time.time() - bot.start_time
    await ctx.respond("Pela's current session's uptime is: " + str(round(time_diff/3600)) + " hours, " + str(round((time_diff/60)%60)) + " minutes, " + str(round(time_diff%60)) + " seconds")



@component.with_slash_command
@tanjun.with_str_slash_option("name", "name")
@tanjun.as_slash_command("name", "Change the bot's nickname lol", default_to_ephemeral=False)
async def nickname(ctx:tanjun.abc.Context, name, bot:PelaBot = tanjun.injected(type=PelaBot)):

    try:
        await bot.rest.edit_my_member(guild=ctx.guild_id, nickname=f"{name}")
    except hikari.errors.BadRequestError as err:
        await ctx.edit_initial_response("```" + str(err.errors) + "```")
        return
    await ctx.respond(f"{ctx.author.mention} Changed my name to \"**" + str(name) + "**\" !!", user_mentions=True)


@tanjun.as_loader
def load(client: tanjun.abc.Client) -> None:
    client.add_component(component.copy())