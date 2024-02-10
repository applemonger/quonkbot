from typing import Callable
import lightbulb
import hikari


def handle_exceptions(*exceptions: tuple[Exception]):
    def wrapper(f: Callable):
        async def wrapped_function(ctx: lightbulb.Context):
            try:
                await f(ctx)
            except exceptions as e:
                await ctx.respond(e, flags=hikari.MessageFlag.EPHEMERAL)
                return

        return wrapped_function

    return wrapper
