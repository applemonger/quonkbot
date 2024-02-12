import lightbulb
import hikari
import os
from database import (
    Database,
    InvalidSharesException,
    NotEnoughCashException,
    UserDoesNotExistException,
    UserExistsException,
)
from textwrap import dedent
from stocks import QuoteException, get_stock_price
from errors import handle_exceptions


COLOR = hikari.Color.of((59, 165, 93))


bot = lightbulb.BotApp(
    token=os.getenv("TOKEN"), prefix=None, intents=hikari.Intents.ALL_UNPRIVILEGED
)


db = Database()


@bot.command
@lightbulb.command("help", "Learn more about QuonkBot!")
@lightbulb.implements(lightbulb.SlashCommand)
async def help(ctx: lightbulb.Context) -> None:
    embed = hikari.Embed(title="QuonkBot Help", color=COLOR)
    value = """
        QuonkBot allows you to paper trade Quonks. 
        1. Use the `/register` command to get started with a cash balance of $10,000.
        2. Use the `/quote` command to get price quotes on stocks.
        3. Use the `/buy` command to buy Quonks.
        4. Use the `/holdings` command to check the value of your owned Quonks.
        5. Use the `/sell` command to sell Quonks.
    """
    embed.add_field(name="Getting Started", value=dedent(value))
    value = """
        Quonks, or Quantum Stonks, are a dream come true. Built with state of the art 
        science, Quonks are stocks that exist in a simultaneous state of long and 
        short. With our patented quantum entanglement Quonk technology, Quonks are 
        short when the current price of the stock is lower than when you last observed
        the price, and long when it is higher. This means your Quonks always go up! 
        You simply can't lose money. Isn't that wonderful?
    """
    embed.add_field(name="What are Quonks?", value=dedent(value))
    await ctx.respond(embed)


@bot.command
@lightbulb.command("register", "Registers the user and gives you $10,000.")
@lightbulb.implements(lightbulb.SlashCommand)
@handle_exceptions(UserExistsException)
async def register(ctx: lightbulb.Context) -> None:
    member_id = int(ctx.author.id)
    db.register_user(member_id)
    await ctx.respond(f"Successfully registered user: <@{member_id}>")


@bot.command
@lightbulb.option("ticker", "Stock ticker", type=str)
@lightbulb.command("quote", "Responds with a ticker quote")
@lightbulb.implements(lightbulb.SlashCommand)
@handle_exceptions(QuoteException)
async def quote(ctx: lightbulb.Context) -> None:
    # Get ticker information
    price = get_stock_price(ctx.options.ticker)
    # Create embed
    embed = hikari.Embed(title=ctx.options.ticker, color=COLOR)
    embed.add_field(name="Price", value=price)
    await ctx.respond(embed, flags=hikari.MessageFlag.EPHEMERAL)


@bot.command
@lightbulb.command("holdings", "Shows your current Quonk holdings and values")
@lightbulb.implements(lightbulb.SlashCommand)
@handle_exceptions(QuoteException, UserDoesNotExistException)
async def holdings(ctx: lightbulb.Context) -> None:
    # Format and validate user
    member_id = int(ctx.author.id)
    db.validate_user(member_id)
    # Create embed
    embed = hikari.Embed(title="Your Holdings", color=COLOR)
    # Track total
    total = 0
    # Create embed field values
    tickers = ""
    quonks = ""
    values = ""
    # Get ticker information
    for holding in db.get_holdings(member_id):
        # Get current price
        price = get_stock_price(holding.ticker)
        # Observe the price
        db.observe_price(member_id, holding.ticker, price)
        # Get observed
        # Add the value to our total value
        value = holding.value
        total += value
        # Add the stats to the embed field values
        tickers += f"{holding.ticker}\n"
        quonks += f"{holding.shares}\n"
        values += f"${value:.2f}\n"
    # Add embed fields
    if tickers != "":
        embed.add_field(name="Ticker", value=tickers, inline=True)
        embed.add_field(name="Quonks", value=quonks, inline=True)
        embed.add_field(name="Value", value=values, inline=True)
    # Add cash
    cash_value = db.get_cash(member_id)
    total += cash_value
    embed.add_field(name="Cash", value=f"${cash_value:.2f}")
    # Add total
    embed.add_field(name="Total Value", value=f"${total:.2f}")
    # Response
    await ctx.respond(embed, flags=hikari.MessageFlag.EPHEMERAL)


@bot.command
@lightbulb.option("shares", "Number of Quonks to buy", type=int, min_value=1)
@lightbulb.option("ticker", "The stock you want to buy", type=str)
@lightbulb.command("buy", "Buy Quonks")
@lightbulb.implements(lightbulb.SlashCommand)
@handle_exceptions(QuoteException, UserDoesNotExistException, NotEnoughCashException)
async def buy(ctx: lightbulb.Context):
    # Format and validate inputs
    member_id = int(ctx.author.id)
    db.validate_user(member_id)
    ticker = str(ctx.options.ticker).upper()
    shares = int(ctx.options.shares)
    # Get price
    yf_price = get_stock_price(ctx.options.ticker)
    # Buy Quonks
    db.buy_quonks(member_id, ticker, shares, yf_price)
    await ctx.respond(
        f"<@{member_id}> bought {shares} quonks of ${ticker} @ ${yf_price:.2f}."
    )


@bot.command
@lightbulb.option("shares", "Number of Quonks to sell", type=int, min_value=1)
@lightbulb.option("ticker", "The stock to sell", type=str)
@lightbulb.command("sell", "Sell Quonks")
@lightbulb.implements(lightbulb.SlashCommand)
@handle_exceptions(QuoteException, UserDoesNotExistException, InvalidSharesException)
async def sell(ctx: lightbulb.Context):
    # Member id
    member_id = int(ctx.author.id)
    db.validate_user(member_id)
    ticker = str(ctx.options.ticker).upper()
    shares = int(ctx.options.shares)
    # Get current price
    yf_price = get_stock_price(ticker)
    # Sell Quonks
    quonk_price = db.sell_quonks(member_id, ticker, shares, yf_price)
    await ctx.respond(
        f"<@{member_id}> sold {shares} quonks of ${ticker} @ ${quonk_price:2f} per quonk."
    )


@bot.command
@lightbulb.command("leaderboard", "Top quonk traders", guilds=[1204946032807645304])
@lightbulb.implements(lightbulb.SlashCommand)
async def leaderboard(ctx: lightbulb.Context):
    # Create embed
    embed = hikari.Embed(title="Top Quonkers", color=COLOR)
    # Get leaderboard values
    leaders = ""
    for i, leader in enumerate(db.leaderboard()):
        leaders += f"#{i+1}. <@{leader.member_id}> ${leader.value:,.2f}\n"
    # Add embed fields
    embed.add_field("Cash + Quonk Value", value=leaders, inline=True)
    await ctx.respond(embed)


if __name__ == "__main__":
    bot.run()
