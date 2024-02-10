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
from dotenv import load_dotenv
from stocks import QuoteException, get_stock_price
from errors import handle_exceptions

load_dotenv()


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
        QuonkBot allows you to paper trade Q-Shares of most known stocks. 
        1. Use the `/register` command to get started with a cash balance of $10,000.
        2. Use the `/quote` command to get price quotes on stocks.
        3. Use the `/buy` command to buy shares of stocks.
        4. Use the `/holdings` command to check the value of your owned stocks.
        5. Use the `/sell` command to sell stocks.
    """
    embed.add_field(name="Getting Started", value=dedent(value))
    value = """
        Q-shares, or Quantum-Shares, are a dream come true. Built with state of the art 
        science, Q-shares are shares that exist in a simultaneous state of long and 
        short. With our patented quantum entanglement Quonk technology, Q-shares are 
        short when the current price of the stock is lower than when you originally 
        bought them, and long when it is higher. This means your Q-shares always go up! 
        You simply can't lose money. Isn't that wonderful?
    """
    embed.add_field(name="What are Q-Shares?", value=dedent(value))
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
@lightbulb.command("holdings", "Shows your current stock holdings and values")
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
    stocks = ""
    shares = ""
    values = ""
    # Get ticker information
    for holding in db.get_holdings(member_id):
        # Get current price
        price = get_stock_price(holding.ticker)
        # Calculate current value based on current price
        value = db.get_value(member_id, holding.ticker, price)
        # Add the value to our total value
        total += price * holding.shares
        # Add the stats to the embed field values
        stocks += f"{holding.ticker}\n"
        shares += f"{holding.shares}\n"
        values += f"${value:.2f}\n"
    # Add embed fields
    if stocks != "":
        embed.add_field(name="Stock", value=stocks, inline=True)
        embed.add_field(name="Q-Shares", value=shares, inline=True)
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
@lightbulb.option("shares", "Number of shares to buy", type=int, min_value=1)
@lightbulb.option("ticker", "The stock you want to buy", type=str)
@lightbulb.command("buy", "Buy stocks")
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
    # Buy stock
    db.buy_stock(member_id, ticker, shares, yf_price)
    await ctx.respond(
        f"<@{member_id}> bought {shares} shares of ${ticker} @ ${yf_price:.2f}."
    )


@bot.command
@lightbulb.option("shares", "Number of shares to sell", type=int, min_value=1)
@lightbulb.option("ticker", "The stock to sell", type=str)
@lightbulb.command("sell", "Sell stocks")
@lightbulb.implements(lightbulb.SlashCommand)
@handle_exceptions(QuoteException, UserDoesNotExistException, InvalidSharesException)
async def sell(ctx: lightbulb.Context):
    # Member id
    member_id = int(ctx.author.id)
    db.validate_user(member_id)
    ticker = str(ctx.options.ticker).upper()
    shares = int(ctx.options.shares)
    # Get price
    yf_price = get_stock_price(ticker)
    # Buy stock
    db.sell_stock(member_id, ticker, shares, yf_price)
    await ctx.respond(
        f"<@{member_id}> sold {shares} shares of ${ticker} @ ${yf_price:2f}."
    )


if __name__ == "__main__":
    bot.run()
