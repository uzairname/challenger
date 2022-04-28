import os
import typing

import hikari
import pandas as pd
from hikari import Embed
from hikari import InteractionCreateEvent
from hikari.interactions.base_interactions import ResponseType
from hikari.messages import ButtonStyle

from Challenger.helpers import *
from Challenger.database import *
from Challenger.config import *

import functools
import asyncio
import tanjun
from tanjun.abc import SlashContext


import matplotlib.pyplot as plt
import seaborn as sns
import math



@tanjun.as_slash_command("temp-test", "something", default_to_ephemeral=False, always_defer=True)
@ensure_staff
async def temp_test(ctx: tanjun.abc.SlashContext, bot: hikari.GatewayBot = tanjun.injected(type=hikari.GatewayBot)) -> None:


    DB = Guild_DB(Database_Config.B2T_GUILD_ID)

    matches = DB.get_matches(chronological=True)

    matches.to_csv("matches.csv")


    plt.figure(figsize=(6,3))

    plt.savefig("plot.png", bbox_inches="tight")
    plt.show()

    embed = hikari.Embed(title="test", description="test")
    embed.set_image("plot.png")


    await ctx.edit_initial_response(embed=embed)


    os.remove("plot.png")





def player_col_for_match(match, user_id, column): #useful probably
    if match["p1_id"] == user_id:
        return match["p1_" + column]
    elif match["p2_id"] == user_id:
        return match["p2_" + column]
    else:
        raise ValueError("Player not in match")

@tanjun.with_user_slash_option("player", "player")
@tanjun.as_slash_command("lol", "lol", always_defer=True)
async def lol(ctx: tanjun.abc.Context, player):

    DB = Guild_DB(ctx.guild_id)

    matches = DB.get_matches(user_id=ctx.author.id, chronological=True)
    matches2 = DB.get_matches(user_id=player.channel_id, chronological=True)

    print(matches)

    times1 = matches["time_started"]
    times2 = matches2["time_started"]

    elos = []
    elos2 = []

    for id, match in matches.iterrows():
        elos.append(player_col_for_match(match, ctx.author.id, "elo_after"))
    for id, match in matches2.iterrows():
        elos2.append(player_col_for_match(match, player.channel_id, "elo_after"))


    for i in plt.rcParams:
        if plt.rcParams[i] == "black":
            plt.rcParams[i] = "w"
    # black background
    params = {"legend.framealpha":0}
    plt.rcParams.update(params)

    plt.figure(figsize=(6,3))
    plt.plot(times1, elos, label="You")
    plt.plot(times2, elos2, label=player.username)
    plt.legend()
    plt.title("Elo History Comparison")
    plt.savefig("plot.png", transparent=True)
    plt.show()

    embed = hikari.Embed(title="test", description="test")
    embed.set_image("plot.png")
    await ctx.edit_initial_response(embed=embed)
    os.remove("plot.png")





@tanjun.as_slash_command("histogram", "lol matches", always_defer=True)
async def histogram(ctx: tanjun.abc.Context):

    DB = Guild_DB(DB.B2T_GUILD_ID)

    matches = DB.get_matches(chronological=True)


    times = matches["time_started"].dropna()


    for i in plt.rcParams:
        if plt.rcParams[i] == "black":
            plt.rcParams[i] = "w"
    # black background
    params = {"legend.framealpha":0}
    plt.rcParams.update(params)

    plt.figure(figsize=(6,3))

    times = pd.to_datetime(times)

    sns.distplot(times, hist=False, kde=True, color = 'w',
             hist_kws={'edgecolor':'black'},
             kde_kws={'linewidth': 4})


    plt.xlabel("Hour of Day (UTC)")

    plt.savefig("plot.png", transparent=True, bbox_inches="tight")
    plt.show()

    embed = hikari.Embed(title="test", description="test")
    embed.set_image("plot.png")
    await ctx.edit_initial_response(embed=embed)
    os.remove("plot.png")




embed = tanjun.slash_command_group("embed", "Work with Embeds!", default_to_ephemeral=False)


@tanjun.with_str_slash_option("elo", "elo")
@tanjun.with_user_slash_option("player", "player")
@tanjun.as_slash_command("set-elo", "set elo", always_defer=True)
async def set_elo(ctx:tanjun.abc.Context, players:hikari.User, elo, bot=tanjun.injected(type=hikari.GatewayBot)):

    DB = Guild_DB(ctx.guild_id)
    players = DB.get_players(user_id=players.id)
    if players is None:
        await ctx.edit_initial_response("Player not found!")
        return
    players = players.iloc[0:1]
    players["elo"] = elo
    DB.upsert_player(players)

    await update_players_elo_roles(ctx, bot, )
    await ctx.edit_initial_response("Done")


@tanjun.with_str_slash_option("input", "input")
@tanjun.as_slash_command("bayeselo", "bayeselo", always_defer=True)
async def test_bayeselo(ctx: tanjun.abc.Context, input, bot=tanjun.injected(type=hikari.GatewayBot)):

    DB = Guild_DB(ctx.guild_id)
    match = DB.get_matches(match_id=2).iloc[0]

    embed = describe_match(match, DB)

    all_matches = DB.get_matches()
    latest_match_id = 2
    player_id = 623257053879861248


    await ctx.respond(embed=embed)
    calc_bayeselo()



#-----------------------------------------------------------------------------------------------------------------------doesn't work
def decorator2(func):
    @functools.wraps(func)
    async def wrapper(ctx: tanjun.abc.Context, bot=tanjun.injected(type=hikari.GatewayBot)):
        await bot.rest.fetch_my_user()
        return func(ctx)
    return wrapper

@tanjun.as_slash_command("test2", "test2", always_defer=True)
@decorator2
async def test2(ctx):
    await ctx.respond("done")


# -----------------------------------------------------------------------------------------------------------------------doesnt work
def decorator3(func):
    @functools.wraps(func)
    async def wrapper(ctx: tanjun.abc.Context, bot=tanjun.injected(type=hikari.GatewayBot)):
        await bot.rest.fetch_my_user() # 'InjectedDescriptor' object has no attribute 'rest'
        return func(ctx)
    return wrapper

@tanjun.as_slash_command("test3", "test3", always_defer=True)
@decorator3
async def test3(ctx:tanjun.abc.Context):
    await ctx.respond("done")


#-----------------------------------------------------------------------------------------------------------------------works
def decorator1(func):
    @functools.wraps(func)
    async def wrapper(ctx:tanjun.abc.Context, bot):
        await bot.rest.fetch_my_user()
        await func(ctx, bot)
    return wrapper

@tanjun.as_slash_command("test1", "test1", always_defer=True)
@decorator1
async def test1(ctx: tanjun.abc.Context, bot=tanjun.injected(type=hikari.GatewayBot)):
    await ctx.respond("done")


#-----------------------------------------------------------------------------------------------------------------------works
def decorator4(func):
    @functools.wraps(func)
    async def wrapper(ctx: tanjun.abc.Context, bot=tanjun.injected(type=hikari.GatewayBot)):
        return func(ctx, bot)
    return wrapper

@tanjun.as_slash_command("test4", "test4", always_defer=True)
@decorator4
async def test4(bot):
    await bot.rest.fetch_my_user()







import string
import random

@tanjun.as_slash_command("long-lb", "very big sample lb", always_defer=True)
async def long_lb(ctx: tanjun.abc.Context):

    embeds = []
    # made up mock sample players and elo
    for i in range(0, 10):
        num_lines = 20
        num_fields = 3
        Embed = hikari.Embed(title="_", description=BLANK)
        for k in range(num_fields):
            string_ = ""
            for j in range(num_lines):
                name = ''.join(random.choices(string.ascii_letters, k=random.randint(1, 10)))
                elo = random.randint(0, 1000)
                string_ = string_ + f"{j+k*num_lines+i*num_fields*num_lines}. {name} - {elo}" + "\n"
            Embed.add_field(name=f"_", value=string_)

        await ctx.get_channel().send(embed=Embed)




@embed.with_command
@tanjun.as_slash_command("interactive-post", f"Build an Embed!")
async def interactive_post(
    ctx: SlashContext,
    bot: hikari.GatewayBot = tanjun.injected(type=hikari.GatewayBot),
    client: tanjun.Client = tanjun.injected(type=tanjun.Client)
) -> None:
    client.metadata['embed'] = hikari.Embed(title="New Embed")
    row = ctx.rest.build_action_row()
    (
        row.add_button(ButtonStyle.PRIMARY, "📋")
        .set_label("Change Title")
        .set_emoji("📋")
        .add_to_container()
    )
    (
        row.add_button(ButtonStyle.DANGER, "❌")
        .set_label("Exit")
        .set_emoji("❌")
        .add_to_container()
    )
    await ctx.edit_initial_response("Click/Tap your choice below, then watch the embed update!", embed=client.metadata['embed'], components=[row, ])
    try:
        with bot.stream(InteractionCreateEvent, timeout=60).filter(('interaction.user.id', ctx.author.id)) as stream:
            async for event in stream:
                await event.interaction.create_initial_response(
                    ResponseType.DEFERRED_MESSAGE_UPDATE,
                )
                key = event.interaction.custom_id
                if key == "❌":
                    await ctx.edit_initial_response(content=f"Exiting!", components=[])
                    return
                elif key == "📋":
                    await title(ctx, bot, client)

                await ctx.edit_initial_response("Click/Tap your choice below, then watch the embed update!", embed=client.metadata['embed'], components=[row])
    except asyncio.TimeoutError:
        await ctx.edit_initial_response("Waited for 60 seconds... Timeout.", embed=None, components=[])


async def title(ctx: SlashContext, bot: hikari.GatewayBot, client: tanjun.Client):
    embed_dict, *_ = bot.entity_factory.serialize_embed(client.metadata['embed'])
    await ctx.edit_initial_response(content="Set Title for embed:", components=[])
    try:
        with bot.stream(hikari.GuildMessageCreateEvent, timeout=60).filter(('author', ctx.author)) as stream:
            async for event in stream:
                embed_dict['title'] = event.content[:200]
                client.metadata['embed'] = bot.entity_factory.deserialize_embed(embed_dict)
                await ctx.edit_initial_response(content="Title updated!", embed=client.metadata['embed'], components=[])
                await event.message.delete()
                return
    except asyncio.TimeoutError:
        await ctx.edit_initial_response("Waited for 60 seconds... Timeout.", embed=None, components=[])




@tanjun.with_own_permission_check(
    hikari.Permissions.SEND_MESSAGES
    | hikari.Permissions.VIEW_CHANNEL
    | hikari.Permissions.EMBED_LINKS
    | hikari.Permissions.ADD_REACTIONS
)
@tanjun.with_str_slash_option("suggestion", "a suggestion")
@tanjun.as_slash_command("suggest", "make a suggestion!")
async def suggest_command(ctx: tanjun.abc.Context, *, suggestion: str) -> None:
    react_emojis = ["✅", "❌"]
    embed = Embed(
        color=0xF1C40F,
    )
    embed.add_field(name="Suggestion", value=suggestion)
    embed.set_author(name=f"Suggestion by {ctx.author}", icon=ctx.author.avatar_url)
    msg = await ctx.respond(embed=embed, ensure_result=True)
    for emoji in react_emojis:
        await msg.add_reaction(emoji)



@tanjun.with_str_slash_option("message_id", "Message ID of the suggestion")
@tanjun.as_slash_command("approve", "approve a suggestion!")
async def approve_command(ctx: tanjun.abc.Context, message_id: str) -> None:
    channel = await ctx.fetch_channel()
    msg = await ctx.rest.fetch_message(channel, int(message_id))

    if not msg.embeds:
        return
    embed = msg.embeds[0]
    embed.set_footer(text=f"Approved by {ctx.author}")
    embed.color = hikari.Color(0x00FF00)
    await msg.edit(embed=embed)
    await msg.remove_all_reactions()
    response = await ctx.respond("Done :ok_hand:", ensure_result=True)
    await asyncio.sleep(3)
    await response.delete()


demo = tanjun.Component(name="demo", strict=True).load_from_scope().make_loader()