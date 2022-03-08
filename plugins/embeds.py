import hikari
import tanjun

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
    embed = hikari.Embed(title="New Embed")
    row = ctx.rest.build_action_row()
    (
        row.add_button(hikari.ButtonStyle.PRIMARY, "📋")
            .set_label("Change Title")
            .set_emoji("📋")
            .add_to_container()
    )
    await ctx.edit_initial_response("Click/Tap your choice below, then watch the embed update!", embed=embed, components=[row, ])


@ tanjun.as_loader
def load(client: tanjun.abc.Client) -> None:
    client.add_component(component.copy())