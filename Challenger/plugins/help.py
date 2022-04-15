import tanjun
import hikari
import math
from datetime import datetime
from hikari.interactions.base_interactions import ResponseType
# from Challenger.utils import *
#
from Challenger.config import Config

component = tanjun.Component(name="hi module")



bot_todo = """

**In order of priority**

in order of priority: 
• show when opponent declares result, and when there's a conflict
• Provisional Bayesian Elo for your first 5 games. https://www.remi-coulom.fr/Bayesian-Elo/
 https://www.warzone.com/Forum/362170-bayesian-elo-versus-regular-elo
• Leaderboard shows multiple pages (dropdown to select groups of 200, buttons to select groups of 20 players)
• remove player from queue after 10 mins
• Automatically assign roles based on Elo

Low priority:
• presets for elo roles
• reset data command
• Automatically register players on commands
• see distribution of everyone's elo
• /stats show your percentile
• Associate each match with a message id in match announcements, so that message can be edited
• /compare (player) show your expected probability of beating opponent, and your winrate against them. Elo change for winning and losing 
• make displayed results pretty
• /join records match time
• ping command
• fix leaderboard display on mobile
• shorthand for commands ex. declare match results /d
• rename /declare to /claim
"""

bot_features = """
Actual Matchmaking. When you join the queue, you get matched with people of similar elo, and the longer you wait, the broader the search
Ability to change old match results. When your elo change depends on the elo difference, fixing the result of an old match (for whatever reason, maybe it was declared wrong or someone was caught boosting and their impact needs to be reverted) has a cascading effect on all the subsequent players those players played against, and the players they played against, and so on... since your elo change depends on your and your opponent's prior elo.
Support for tournaments

Best of 3 and 5
"""
# Changing the result of an old match has a cascading effect on all the subsequent players those players played against, and the players they played against, and so on... since your elo change depends on your and your opponent's prior elo. If the changed match is very old, the calculation might take a while

@component.with_slash_command
@tanjun.as_slash_command("help", "About", default_to_ephemeral=True)
async def help_command(ctx: tanjun.abc.Context, bot:hikari.GatewayBot=tanjun.injected(type=hikari.GatewayBot)) -> None:

    basics_embed = hikari.Embed(title="Basic Use", description="To get started, type /register. Make sure you're in a channel with a 1v1 lobby. Join the queue to get matched with another player. When the queue is full, a match is created, and you can see its status in whichever channel is set up to record matches", colour=Colors.PRIMARY)
    basics_embed.add_field(name="Commands", value="`/register` - Register your username and gain access to most features!\n`/join` - Join the queue to be matched with another player\n`/leave` - Leave the queue\n`/declare [win, loss, draw, or cancel]` - declare the results of the match. Both players must agree for result to be decided. Staff can handle disputes", inline=True)

    util_embed = hikari.Embed(title="Utility", description="Useful and fun commands", colour=Colors.PRIMARY)
    util_embed.add_field(name="General", value="`/queue` - View the status of the queue\n`/stats` - View your stats\n`/leaderboard` - View the leaderboard\n", inline=True)
    util_embed.add_field(name="Bot related", value="`/about` - Get information about the bot\n`/help` - Get help on how to use the bot\n`/uptime` - See how long since the bot's last reset\n`/ping` - Check the bot's response time\n")

    staff_embed = hikari.Embed(title="Staff Commands", description="People with a staff role can use these commands. Enter the config commands without any parameters to see details", colour=Colors.PRIMARY)
    staff_embed.add_field(name="Staff settings", value="`/config-help` - Detailed help on staff config commands, which include:\n`/config-lobby`, `/config-staff`, `/config-eloroles`")
    staff_embed.add_field(name="Matches", value="/`setmatch` - force a match's result, in the event of a dispute or mistake\n`/reset` Reset all match history and everyone's elo in the server. Preserves all other settings. Use this, for example, when starting a new season")

    pages = {"Basics": basics_embed, "Staff Commands":staff_embed, "Utility":util_embed}

    page_dropdown = ctx.rest.build_action_row().add_select_menu("page select").set_min_values(1).set_max_values(1)
    for i in pages:
        page_dropdown = page_dropdown.add_option(i, i).set_is_default(i=="Basics").add_to_menu()
    page_dropdown = page_dropdown.add_to_container()

    await ctx.edit_initial_response(embeds=[basics_embed], components=[page_dropdown], user_mentions=[ctx.author])

    with bot.stream(hikari.InteractionCreateEvent, timeout=600).filter(("interaction.type", hikari.interactions.InteractionType.MESSAGE_COMPONENT)) as stream:
        async for event in stream:
            await event.interaction.create_initial_response(ResponseType.DEFERRED_MESSAGE_UPDATE)
            page = event.interaction.values[0]
            for i in page_dropdown.components[0]._options:
                i.set_is_default(i._label == page)

            await ctx.edit_initial_response(embed=pages[page], components=[page_dropdown])


@component.with_slash_command
# @tanjun.with_own_permission_check(Config.REQUIRED_PERMISSIONS, error_message=Config.PERMS_ERR_MSG)
@tanjun.as_slash_command("about", "About", default_to_ephemeral=False)
async def about_command(ctx: tanjun.abc.Context, bot:hikari.GatewayBot=tanjun.injected(type=hikari.GatewayBot), client:tanjun.abc.Client=tanjun.injected(type=tanjun.abc.Client)) -> None:

    user = await bot.rest.fetch_my_user()
    avatar = user.avatar_url
    about_embed = hikari.Embed(title="About", description=f"Hi {ctx.author.mention}! This is a ranking bot. 1v1 other players to climb the elo leaderboards!", colour=Colors.PRIMARY).set_thumbnail(avatar)

    about_embed.add_field(name=f"How to use", value=f"Use `/help` for instructions and commands", inline=True)
    about_embed.add_field(name="Github", value="View the source code\nhttps://github.com/lilapela/competition", inline=True)
    about_embed.add_field(name=f"Invite link", value=f"[**Invite**]({Config.INVITE_LINK}) or click the link in my profile", inline=True)
    about_embed.set_footer("By Lilapela#5348")

    member = bot.cache.get_member(ctx.guild_id, user.id)
    bot_perms = await tanjun.utilities.fetch_permissions(client, member)
    if Config.REQUIRED_PERMISSIONS & bot_perms == bot_perms:
        about_embed.add_field(name="Permissions", value=f":white_check_mark: This bot has all the required permissions", inline=True)
    else:
        about_embed.add_field(name="Permissions", value=f":x: This bot is missing the following required permissions: {Config.REQUIRED_PERMISSIONS}", inline=True)

    permissions_embed = hikari.Embed(title="Permissions", description="Reasons for every permission required by the bot", color=Colors.PRIMARY)
    permissions_embed.add_field("View Channels", "Required for the bot to view channels")

    todo_embed = hikari.Embed(title="Todo", description="This bot is still in development. Any bug reports or suggested features would be appreciated!", colour=Colors.PRIMARY)
    todo_embed.add_field(name="What I'm working on", value=bot_todo[0:1000])
    todo_embed.add_field(name="Possible Future Features", value=bot_features)
    todo_embed.add_field(name="Github", value="View the source code\nhttps://github.com/lilapela/competition")

    pages = {"About": about_embed, "Todo": todo_embed}

    page_dropdown = ctx.rest.build_action_row().add_select_menu("page select").set_min_values(1).set_max_values(1)
    for i in pages:
        page_dropdown = page_dropdown.add_option(i, i).set_is_default(i=="About").add_to_menu()
    page_dropdown = page_dropdown.add_to_container()

    await ctx.edit_initial_response(embeds=[about_embed], components=[page_dropdown], user_mentions=True)

    with bot.stream(hikari.InteractionCreateEvent, timeout=Config.DEFAULT_TIMEOUT).filter(("interaction.type", hikari.interactions.InteractionType.MESSAGE_COMPONENT)) as stream:
        async for event in stream:
            await event.interaction.create_initial_response(ResponseType.DEFERRED_MESSAGE_UPDATE)
            page = event.interaction.values[0]
            for i in page_dropdown.components[0]._options:
                i.set_is_default(i._label == page)

            await ctx.edit_initial_response(embed=pages[page], components=[page_dropdown])

    await ctx.edit_initial_response(embed=about_embed, components=[])


@component.with_slash_command
@tanjun.as_slash_command("uptime", "get Pela's uptime", default_to_ephemeral=False)
async def uptime(ctx:tanjun.abc.Context, client:tanjun.Client = tanjun.injected(type=tanjun.abc.Client)) -> None: #TODO ping
    time_diff = datetime.now() - client.metadata["start_time"]
    await ctx.respond("Challenger's current session's uptime is: " + str(datetime.timedelta(seconds=time_diff)))


help = tanjun.Component(name="help", strict=True).load_from_scope().make_loader()