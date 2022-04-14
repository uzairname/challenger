import tanjun
import functools
import logging
import typing
from Challenger.utils.utils import *

from Challenger.database import Session

def check_errors(func):
    # for slash commands, respond with an error if it doesn't work
    @functools.wraps(func)
    async def wrapper_check_errors(ctx: tanjun.abc.Context, *args, **kwargs):
        try:
            await func(ctx, *args, **kwargs)
        except Exception as e:
            await ctx.respond(Custom_Embed(Embed_Type.ERROR, description="```" + str(e) + "\n```"))
            logging.error(f"Error in {func.__name__}", exc_info=True)
    return wrapper_check_errors


def ensure_registered(func):
    @functools.wraps(func)
    async def wrapper(ctx, *args, **kwargs):
        DB = Session(ctx.guild_id)

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
        DB = Session(ctx.guild_id)

        queues = DB.get_queues(ctx.channel_id)
        if queues.empty:
            await ctx.edit_initial_response("This channel doesn't have a lobby")
            return

        return await func(ctx=ctx, queue=queues.iloc[0], *args, **kwargs)

    return wrapper


def ensure_staff(func):
    @functools.wraps(func)
    async def wrapper(ctx, *args, **kwargs):

        async def is_staff():
            if ctx.author.id == Config.OWNER_ID:
                return True

            DB = Session(ctx.guild_id)

            staff_role = DB.get_config()["staff_role"]

            if staff_role is None:
                guild = await ctx.fetch_guild()

                roles = ctx.member.role_ids
                role_mapping = {}
                for role_id in roles:
                    role_mapping[role_id] = guild.get_role(role_id)

                user_perms = tanjun.utilities.calculate_permissions(member=ctx.member, guild=guild, roles=role_mapping)
                if user_perms & hikari.Permissions.MANAGE_GUILD == user_perms:
                    return True
                return False

            return bool(staff_role in ctx.member.role_ids)

        if not await is_staff():
            await ctx.respond("Missing permissions")
            return

        return await func(ctx=ctx, *args, **kwargs)

    return wrapper


def take_input(input_instructions:typing.Callable):

    """
    Calls function with input and lets the user confirm/cancel the command
    params:
        decorated function: slash command function called when confirm button is pressed. function that takes in a hikari.ComponentInteraction event and/or additional kwargs and returns an embed to show when the command is executed.
        input_instructions: function that takes in a tanjun.abc.Context, Database, and/or additional kwargs and returns an embed to show before user confirms their input
    """

    def wrapper_take_input(func):

        @functools.wraps(func)
        async def wrapper(ctx, bot=tanjun.injected(type=hikari.GatewayBot), **kwargs):

            confirm_cancel_row = ctx.rest.build_action_row()
            confirm_cancel_row.add_button(hikari.messages.ButtonStyle.SUCCESS, "Confirm").set_label("Confirm").set_emoji("✔️").add_to_container()
            confirm_cancel_row.add_button(hikari.messages.ButtonStyle.DANGER, "Cancel").set_label("Cancel").set_emoji("❌").add_to_container()

            instructions_embed = await input_instructions(ctx=ctx, **kwargs)
            response = await ctx.respond(embeds=[instructions_embed], components=[confirm_cancel_row], ensure_result=True)

            confirm_embed = Custom_Embed(type=Embed_Type.INFO, title="Confirm?", description="Nothing selected")

            with bot.stream(hikari.InteractionCreateEvent, timeout=Config.DEFAULT_TIMEOUT).filter(
                ("interaction.type", hikari.interactions.InteractionType.MESSAGE_COMPONENT),
                ("interaction.user.id", ctx.author.id),
                ("interaction.message.id", response.id)
            ) as stream:
                async for event in stream:
                    await event.interaction.create_initial_response(hikari.ResponseType.DEFERRED_MESSAGE_UPDATE)
                    if event.interaction.custom_id == "Confirm":
                        confirm_embed = await func(event=event, ctx=ctx, **kwargs)
                        break
                    elif event.interaction.custom_id == "Cancel":
                        confirm_embed = Custom_Embed(type=Embed_Type.CANCEL)
                        break
                    else:
                        confirm_embed = Custom_Embed(type=Embed_Type.ERROR, description="Invalid action.")

            await ctx.edit_initial_response(embeds=[instructions_embed, confirm_embed], components=[])

        return wrapper
    return wrapper_take_input