import asyncio
import hikari
import tanjun

from hikari import InteractionCreateEvent
from hikari.interactions.base_interactions import ResponseType
from hikari.messages import ButtonStyle

from tanjun.abc import SlashContext

component = tanjun.Component()

embed = component.with_slash_command(tanjun.slash_command_group("embed", "Work with Embeds!", default_to_ephemeral=False))

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

@tanjun.as_loader
def load(client: tanjun.abc.Client) -> None:
    client.add_component(component.copy())