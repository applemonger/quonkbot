import lightbulb
import hikari
import os
from dotenv import load_dotenv
import yfinance as yf
import logging
from database import (
    Database,
    InvalidSharesException,
    NotEnoughCashException,
    UserExistsException,
)

load_dotenv()


COLOR = hikari.Color.of((59, 165, 93))


bot = lightbulb.BotApp(
    token=os.getenv("TOKEN"), prefix=None, intents=hikari.Intents.ALL_UNPRIVILEGED
)


db = Database()


@bot.command
@lightbulb.command("register", "Registers the user and gives you $10,000.")
@lightbulb.implements(lightbulb.SlashCommand)
async def register(ctx: lightbulb.Context) -> None:
    member_id = int(ctx.author.id)
    try:
        db.register_user(member_id)
        await ctx.respond(f"Successfully registered user: <@{member_id}>")
    except UserExistsException as e:
        await ctx.respond(e, flags=hikari.MessageFlag.EPHEMERAL)


@bot.command
@lightbulb.option("ticker", "Stock ticker", type=str)
@lightbulb.command("quote", "Responds with a ticker quote")
@lightbulb.implements(lightbulb.SlashCommand)
async def quote(ctx: lightbulb.Context) -> None:
    try:
        # Get ticker information
        ticker = yf.Ticker(ctx.options.ticker)
        price = ticker.info.get("currentPrice")
        # Create embed
        embed = hikari.Embed(title=ctx.options.ticker, color=COLOR)
        embed.add_field(name="Price", value=price)
        await ctx.respond(embed, flags=hikari.MessageFlag.EPHEMERAL)
    except Exception:
        await ctx.respond(
            f"Unable to quote ticker: ${ctx.options.ticker}",
            flags=hikari.MessageFlag.EPHEMERAL,
        )


@bot.command
@lightbulb.command("holdings", "Shows your current stock holdings and values")
@lightbulb.implements(lightbulb.SlashCommand)
async def holdings(ctx: lightbulb.Context) -> None:
    # Member id
    member_id = int(ctx.author.id)
    if not db.user_exists(member_id):
        await ctx.respond(
            "Please use /register first to register yourself and receive a starting balance."
        )
        return
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
        ticker = yf.Ticker(holding.ticker)
        price = ticker.info.get("currentPrice")
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
async def buy(ctx: lightbulb.Context):
    # Member id
    member_id = int(ctx.author.id)
    if not db.user_exists(member_id):
        await ctx.respond(
            "Please use /register first to register yourself and receive a starting balance."
        )
        return
    ticker = str(ctx.options.ticker).upper()
    shares = int(ctx.options.shares)
    # Get price
    try:
        yf_ticker = yf.Ticker(ticker)
        yf_price = yf_ticker.info.get("currentPrice")
    except Exception:
        await ctx.respond(
            f"Unable to get price for ticker: ${ticker}",
            flags=hikari.MessageFlag.EPHEMERAL,
        )
        return
    # Buy stock
    try:
        db.buy_stock(member_id, ticker, shares, yf_price)
        await ctx.respond(
            f"<@{member_id}> bought {shares} shares of ${ticker} @ ${yf_price:.2f}."
        )
    except InvalidSharesException as e:
        await ctx.respond(e, flags=hikari.MessageFlag.EPHEMERAL)
    except NotEnoughCashException as e:
        await ctx.respond(e, flags=hikari.MessageFlag.EPHEMERAL)
    except Exception as e:
        logging.error(e)
        pass


@bot.command
@lightbulb.option(
    "shares", "Number of shares you would like to sell", type=int, min_value=1
)
@lightbulb.option("ticker", "The stock you would like to sell", type=str)
@lightbulb.command("sell", "Sell stocks")
@lightbulb.implements(lightbulb.SlashCommand)
async def sell(ctx: lightbulb.Context):
    # Member id
    member_id = int(ctx.author.id)
    if not db.user_exists(member_id):
        await ctx.respond(
            "Please use /register first to register yourself and receive a starting balance."
        )
        return
    ticker = str(ctx.options.ticker).upper()
    shares = int(ctx.options.shares)
    # Get price
    try:
        yf_ticker = yf.Ticker(ticker)
        yf_price = yf_ticker.info.get("currentPrice")
    except Exception:
        await ctx.respond(
            f"Unable to get price for ticker: ${ticker}",
            flags=hikari.MessageFlag.EPHEMERAL,
        )
        return
    # Buy stock
    try:
        db.sell_stock(member_id, ticker, shares, yf_price)
        await ctx.respond(
            f"<@{member_id}> sold {shares} shares of ${ticker} @ ${yf_price:2f}."
        )
    except InvalidSharesException as e:
        await ctx.respond(e, flags=hikari.MessageFlag.EPHEMERAL)
    except Exception as e:
        logging.error(e)
        pass


if __name__ == "__main__":
    bot.run()
