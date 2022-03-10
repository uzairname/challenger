from plugins._utils import *

nl = "\n"

component = tanjun.Component(name="hi module")

@component.with_slash_command
@tanjun.as_slash_command("hi", "a", default_to_ephemeral=False)
async def hi_test(ctx: tanjun.abc.Context) -> None:
    await ctx.respond(f"Hi {ctx.author.mention}!{nl}This is the testing version. More features coming soon")


@tanjun.as_loader
def load(client: tanjun.abc.Client) -> None:
    client.add_component(component.copy())