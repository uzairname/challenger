import tanjun
import hikari
import math
from datetime import datetime, timedelta
from hikari.interactions.base_interactions import ResponseType
import typing

from Challenger.utils import *
from Challenger.config import Config

component = tanjun.Component(name="hi module")


todo_str = """
**In order of priority**
• Provisional Bayesian Elo for your first 5 games. [read more](https://www.remi-coulom.fr/Bayesian-Elo/
 https://www.warzone.com/Forum/362170-bayesian-elo-versus-regular-elo)
• Implement a variable confidence factor in elo calculation [read more](http://www.glicko.net/glicko/glicko.pdf)
• option to show details in match history
• Extension to store match info like map played, strategy used, etc
• Ban players from playing
• presets for elo roles
• reset data command
• Automatically register players on commands
• see distribution of everyone's elo
• /stats show your percentile
• /compare (player) show your expected probability of beating opponent, and your winrate against them. Elo change for winning and losing 
• shorthand for commands ex. declare match results /d
"""

coming_soon_str = """
Actual Matchmaking. When you join the queue, you get matched with people of similar elo, and the longer you wait, the broader the search.
Support for tournaments.
In-discord charts and graphs to visualize key trends and stats.

Associating each match with a map played or other game info.
Support for best of 3 and 5 matches.
"""
# Changing the result of an old match has a cascading effect on all the subsequent players those players played against, and the players they played against, and so on... since your elo change depends on your and your opponent's prior elo. If the changed match is very old, the calculation might take a while



@component.with_slash_command
@tanjun.with_own_permission_check(Config.REQUIRED_PERMISSIONS, error_message=Config.PERMS_ERR_MSG)
@tanjun.as_slash_command("help", "how to use", default_to_ephemeral=True, always_defer=True)
async def help_command(ctx: tanjun.abc.Context, bot:hikari.GatewayBot=tanjun.injected(type=hikari.GatewayBot)) -> None:

    basics_embed = hikari.Embed(title="Basic Use",
                                description="To get started, type /register. Make sure you're in a channel with a 1v1 lobby. Join the queue to get matched with another player. When the queue is full, a match is created, and you can see its future updates in whichever channel is set up to record matches",
                                colour=Colors.PRIMARY)
    basics_embed.add_field(name="Commands", value=
    "`/about` - Learn about the bot\n"
    "`/register` - Register your username and gain access to most features!\n"
    "`/join` - Join the queue to be matched with another player\n"
    "`/leave` - Leave the queue\n"
    "`/declare [win, loss, draw, or cancel]` - declare the results of the match. **Both players must declare and agree for result to be decided**. You can change your declared result for your most recent match at any time. Staff can handle disputes",
                           inline=True)

    util_embed = hikari.Embed(title="Utility", description="Useful and fun commands", colour=Colors.PRIMARY)
    util_embed.add_field(name="General", value=
    "`/queue` - Get the status of the queue\n"
    "`/stats` - View your elo stats\n"
    "`/lb` - View the leaderboard\n"
    "`/match-history [player](optional)` - View your or another player's match history, and see the status of your most recent match",
                         inline=True)
    util_embed.add_field(name="Bot related", value=
    "`/help` - Get help on how to use the bot\n"
    "`/uptime` - See how long since the bot's last reset\n"
    "`/ping` - Check the bot's response time\n")

    staff_embed = hikari.Embed(title="Staff Commands", description="People with a staff role can use these commands. Enter the config commands without any parameters to see details", colour=Colors.PRIMARY)
    staff_embed.add_field(name="Staff settings", value=
    "`/config-help` - Detailed help on staff config commands\n"
    "`/reset` Reset all match history and everyone's elo in the server. Preserves all other settings. Use this, for example, when starting a new season\n")
    staff_embed.add_field(name="Matches", value=
    "`/set-match` - Force a match's result in the event of a dispute or mistake\n"
    "`/refresh-all-matches` - Recalculate every match and everyone's elo and ranked status\n")

    pages = {"Basics": [basics_embed], "Staff Commands":[staff_embed], "Utility":[util_embed]}

    await create_page_dropdown(ctx, bot, pages)



@component.with_slash_command
@tanjun.as_slash_command("about", "About", default_to_ephemeral=False, always_defer=True)
async def about_command(ctx: tanjun.abc.Context, bot:hikari.GatewayBot=tanjun.injected(type=hikari.GatewayBot), client:tanjun.abc.Client=tanjun.injected(type=tanjun.abc.Client)) -> None:
    response = await ctx.fetch_initial_response()

    user = await bot.rest.fetch_my_user()
    member = bot.cache.get_member(ctx.guild_id, user.id)
    avatar = user.avatar_url

    #about
    about_embed = hikari.Embed(title="About", description=f"Hi {ctx.author.mention}! Challenger is an Elo ranking bot. 1v1 other players to climb the leaderboards, and have access to a variety of competitive features entirely within discord! Use the dropdown to explore more, and use /help for usage instructions", colour=Colors.PRIMARY).set_thumbnail(avatar)

    about_embed.add_field(name=f"How to use", value=f"Use `/help` for instructions and commands", inline=True)
    bot_perms = await tanjun.utilities.fetch_permissions(client, member)
    missing_perms = Config.REQUIRED_PERMISSIONS & ~bot_perms
    if missing_perms:
        perms_message = f":x: This bot is missing the following required permissions: `{missing_perms}`\n\n Re-invite the bot with the link above"
    else:
        perms_message = f":white_check_mark: This bot has all the required permissions"
    about_embed.add_field(name="Permissions", value=perms_message, inline=True)
    about_embed.add_field(name="Version", value=f"{Config.VERSION}", inline=True)
    about_embed.set_footer(text="Lilapela#5348")

    about_btn_row = ctx.rest.build_action_row()
    about_btn_row.add_button(hikari.messages.ButtonStyle.LINK, Config.DISCORD_INVITE_LINK).set_label("Support Server").add_to_container()
    about_btn_row.add_button(hikari.messages.ButtonStyle.LINK, Config.INVITE_LINK).set_label("Bot Invite").add_to_container()
    about_btn_row.add_button(hikari.messages.ButtonStyle.LINK, Config.GITHUB_LINK).set_label("Github").add_to_container()


    features_embed = hikari.Embed(title="Features", description="*_ _*", colour=Colors.PRIMARY).set_thumbnail(avatar)
    features_embed.add_field(name=":crossed_swords: 1v1 Matches", value="<:reply:966765324013801532>Easy to use lobbies and leaderboard. Players can enter a queue, get matched with one another, and declare the results. Staff can handle disputes by overriding match results")
    features_embed.add_field(name=":trophy: Scoring", value="Most scoring is based on the [Elo rating system](https://medium.com/purple-theory/what-is-elo-rating-c4eb7a9061e0). See a visualization of how it works here [here](https://www.desmos.com/calculator/jh0wbxfkjp)")
    features_embed.add_field(name=":large_orange_diamond: Elo Ranks", value="You can specify roles to be automatically assigned to players of a certain elo")
    features_embed.add_field(name=":chart_with_upwards_trend: Leaderboard", value="Compare everyone's elo with a leaderboard for your discord server")
    features_embed.add_field(name=":scroll: History and stats", value="View everyone's match history and detailed competetive stats")
    features_embed2 = hikari.Embed(title="Special", description="Features that set Challenger apart from other elo bots", colour=Colors.PRIMARY)
    features_embed2.add_field(name=":star: Advanced provisional elo (coming soon)", value="For everyone's first few games, Challenger uses a provisional elo system based on [Bayesian Elo](https://www.remi-coulom.fr/Bayesian-Elo/) to find the players most probable skill level just based on a few matches. This means you don't have to grind at first to reach your appropriate elo.")
    features_embed2.add_field(name=":star: Independent and flexible match calculation", value="The way elo is calculated allows for much greater control. Want to customize the elo parameters, even after several games have been played, want to ban a certain player and undo the effect they had on everyone's elo, or change an old match's result? Challenger makes it easy. Make any change to an old match, player, or elo setting, and all following affected players' and matches' elo will be recalculated.")


    permissions_embed = hikari.Embed(title="Permissions", description="Reasons for every permission required by the bot", color=Colors.PRIMARY)
    permissions_embed.add_field("View Channels", "Required for the bot to view channels")

    future_embed = hikari.Embed(title="Todo", description="This bot is still in development. Any bug reports or suggested features would be appreciated!", colour=Colors.PRIMARY)
    future_embed.add_field(name="What I'm working on", value=todo_str[0:1000])
    future_embed.add_field(name="Features Coming Soon", value=coming_soon_str)


    pages = {"About": [about_embed], "Features":[features_embed, features_embed2], "Future Plans": [future_embed]}
    components = {"About": [about_btn_row]}

    await create_page_dropdown(ctx, bot, pages, page_components=components)


info = tanjun.Component(name="info", strict=True).load_from_scope().make_loader()