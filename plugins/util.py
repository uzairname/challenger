import tanjun

nl = "\n"

component = tanjun.Component()

@component.with_slash_command
@tanjun.as_slash_command("hi", "a", default_to_ephemeral=False)
async def hello_test(ctx: tanjun.abc.Context) -> None:
    await ctx.respond(f"Hi {ctx.author.mention}!{nl}More features coming soon")


@tanjun.as_loader
def load(client: tanjun.abc.Client) -> None:
    client.add_component(component.copy())