import tanjun
import functools
import logging
import typing

import hikari
from hikari.interactions.base_interactions import ResponseType
from .style import *
from Challenger.database import Guild_DB
from Challenger.config import Config


async def on_error(ctx: tanjun.abc.Context, exception: BaseException) -> None:
    """
    Handle an unexpected error during command execution.
    """
    embed = hikari.Embed(
        title=f"Unexpected {type(exception).__name__}",
        color=Colors.ERROR,
        description=f"```python\n{str(exception)[:1950]}```",
    )
    await ctx.respond(embed=embed)


def ensure_registered(func):
    @functools.wraps(func)
    async def wrapper(ctx, *args, **kwargs):
        DB = Guild_DB(ctx.guild_id)

        player = DB.get_players(user_id=ctx.author.id)
        if player.empty:
            await ctx.respond(f"Hi {ctx.author.mention}! Please register with /register to play", user_mentions=True)
            return

        return await func(ctx=ctx, *args, **kwargs)

    return wrapper


def get_channel_lobby(func) -> typing.Callable:
    #checks if there's a lobby in the channel and if so, passes it to the function

    @functools.wraps(func)
    async def wrapper(ctx, *args, **kwargs):
        DB = Guild_DB(ctx.guild_id)

        queues = DB.get_lobbies(ctx.channel_id)
        if queues.empty:
            await ctx.edit_initial_response("This channel doesn't have a lobby")
            return

        return await func(ctx=ctx, lobby=queues.iloc[0], *args, **kwargs)

    return wrapper



def ensure_staff(func):
    @functools.wraps(func)
    async def wrapper(ctx, *args, **kwargs):

        async def is_staff():
            if ctx.author.id == Config.OWNER_ID:
                return True

            DB = Guild_DB(ctx.guild_id)

            staff_role = DB.get_config()["staff_role"]

            if staff_role is None:
                guild = await ctx.fetch_guild()

                roles = ctx.member.role_ids
                role_mapping = {}
                for role_id in roles:
                    role_mapping[role_id] = guild.get_role(role_id)

                user_perms = tanjun.utilities.calculate_permissions(member=ctx.member, guild=guild, roles=role_mapping)
                return user_perms & hikari.Permissions.MANAGE_GUILD == user_perms

            return bool(staff_role in ctx.member.role_ids)

        if not await is_staff():
            await ctx.respond("Missing permissions")
            return

        return await func(ctx=ctx, *args, **kwargs)

    return wrapper



def confirm_cancel_input(input_instructions:typing.Callable):

    """
    Calls function with input and lets the user confirm/cancel the command
    params:
        decorated function: slash command function called when confirm button is pressed. function that takes in a hikari.ComponentInteraction event and/or additional kwargs and returns an embed to show when the command is executed.
        input_instructions: function that takes in a tanjun.abc.Context, Database, and optional kwargs and returns an embed to show before user confirms their input
    """

    def wrapper_2(func):

        @functools.wraps(func)
        async def wrapper(ctx, bot, **kwargs):

            confirm_cancel_row = ctx.rest.build_action_row()
            confirm_cancel_row.add_button(hikari.messages.ButtonStyle.SUCCESS, "Confirm").set_label("Confirm").set_emoji("✔️").add_to_container()
            confirm_cancel_row.add_button(hikari.messages.ButtonStyle.DANGER, "Cancel").set_label("Cancel").set_emoji("✖").add_to_container()

            instructions_embed = await input_instructions(ctx=ctx, **kwargs)
            response = await ctx.respond(embeds=[instructions_embed], components=[confirm_cancel_row], ensure_result=True)

            confirm_embed = None

            with bot.stream(hikari.InteractionCreateEvent, timeout=Config.COMPONENT_TIMEOUT).filter(
                ("interaction.type", hikari.interactions.InteractionType.MESSAGE_COMPONENT),
                ("interaction.message.id", response.id)
            ) as stream:
                async for event in stream:
                    await event.interaction.create_initial_response(hikari.ResponseType.DEFERRED_MESSAGE_UPDATE)
                    if event.interaction.user.id != ctx.author.id:
                        continue

                    if event.interaction.custom_id == "Confirm":
                        confirm_embed = await func(ctx=ctx, bot=bot, **kwargs)
                        break
                    elif event.interaction.custom_id == "Cancel":
                        confirm_embed = hikari.Embed(title="Cancelled", description="Command cancelled", color=Colors.DARK)
                        break

            if confirm_embed is not None:
                await ctx.edit_initial_response(embeds=[instructions_embed, confirm_embed], components=[])
            else:
                await ctx.edit_initial_response(embeds=[instructions_embed, hikari.Embed(title="Timed Out", description="timed out", color=Colors.DARK)], components=[])

        return wrapper
    return wrapper_2




async def create_paginator(ctx:tanjun.abc.Context, bot:hikari.GatewayBot, get_page:typing.Callable, starting_page=0, nextlabel="Next", prevlabel="Previous", nextemoji="➡️", prevemoji="⬅️"):
    """
    params:
        ctx: context of the command
        response: message that the page navigator will be attached to
        get_page: function that takes in a page number and returns a list of embeds to show on the page, or None if page is blank
    """

    response = await ctx.fetch_initial_response()

    def is_first_page(page_num):
        return get_page(page_num - 1) is None

    def is_last_page(page_num):
        return get_page(page_num + 1) is None

    cur_page = starting_page

    page_navigator = ctx.rest.build_action_row()
    page_navigator.add_button(hikari.messages.ButtonStyle.PRIMARY, prevlabel).set_label(prevlabel).set_emoji(
        prevemoji).set_is_disabled(is_first_page(cur_page)).add_to_container()
    page_navigator.add_button(hikari.messages.ButtonStyle.PRIMARY, nextlabel).set_label(nextlabel).set_emoji(
        nextemoji).set_is_disabled(is_last_page(cur_page)).add_to_container()

    embeds = get_page(cur_page)

    await ctx.edit_initial_response(embeds=embeds, component=page_navigator)

    with bot.stream(hikari.InteractionCreateEvent, timeout=Config.COMPONENT_TIMEOUT).filter(
            ("interaction.type", hikari.interactions.InteractionType.MESSAGE_COMPONENT),
            ("interaction.message.id", response.id)) as stream:
        async for event in stream:
            await event.interaction.create_initial_response(ResponseType.DEFERRED_MESSAGE_UPDATE)
            if event.interaction.user.id != ctx.author.id:
                continue

            if event.interaction.custom_id == nextlabel and not is_last_page(cur_page):
                cur_page += 1
            elif event.interaction.custom_id == prevlabel and not is_first_page(cur_page):
                cur_page -= 1

            for i in page_navigator.components:
                if i.label == prevlabel:
                    i.set_is_disabled(is_first_page(cur_page))
                elif i.label == nextlabel:
                    i.set_is_disabled(is_last_page(cur_page))

            embeds = get_page(cur_page)

            await ctx.edit_initial_response(embeds=embeds, component=page_navigator)

    try:
        await ctx.edit_initial_response(embeds=embeds, components=[])
    except hikari.UnauthorizedError: # The ephemeral message was deleted
        pass




async def create_page_dropdown(ctx:tanjun.abc.Context, bot, page_embeds: typing.Mapping[str, list[hikari.Embed]], page_components=None):
    """
        pages: a mapping of page name to a list of embeds. Length can't be more than 25
    """

    if page_components is None:
        page_components = {}

    response = await ctx.fetch_initial_response()
    page_dropdown = ctx.rest.build_action_row().add_select_menu("page select").set_min_values(1).set_max_values(1)

    default_page = list(page_embeds)[0]

    for i in page_embeds:
        page_dropdown = page_dropdown.add_option(i, i).set_is_default(i==default_page).add_to_menu()
    page_dropdown = page_dropdown.add_to_container()

    await ctx.edit_initial_response(embeds=page_embeds[default_page], components=page_components.get(default_page, [])+[page_dropdown])

    with bot.stream(hikari.InteractionCreateEvent, timeout=Config.COMPONENT_TIMEOUT).filter(
            ("interaction.type", hikari.interactions.InteractionType.MESSAGE_COMPONENT),
            ("interaction.user.id", ctx.author.id),
            ("interaction.message.id", response.id)) as stream:
        async for event in stream:
            await event.interaction.create_initial_response(ResponseType.DEFERRED_MESSAGE_UPDATE)
            page = event.interaction.values[0]
            for i in page_dropdown.components[0]._options:
                i.set_is_default(i._label == page)

            await ctx.edit_initial_response(embeds=page_embeds[page], components=page_components.get(page, []) + [page_dropdown])


__all__ = ["ensure_staff", "get_channel_lobby", "ensure_registered", "confirm_cancel_input", "on_error", "create_paginator", "create_page_dropdown"]
