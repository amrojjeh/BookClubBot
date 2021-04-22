import discord
from discord.ext import commands
from bookclub import Nominations, Book, Person, get_place_str
from collections import defaultdict
import os

guilds = defaultdict(lambda: GuildData())

description = """A bot that handles regular book club needs, primarily nominating books. It's designed so that it could be used without admin intervention """

intents = discord.Intents.default()
bot = commands.Bot(command_prefix=commands.when_mentioned_or("b!"), description=description, intents=intents)
bot.remove_command("help")

class GuildData:
    def __init__(self):
        self.nominations = None # Nominations()
        self.voting = False
        self.trust_needed = False
        self.prefix = "b!"

class Emojis:
    check_mark = "✅"
    cross = "❌"

def voting_started():
    async def predicate(ctx):
        guild_data = guilds[ctx.guild.id]
        if not guild_data.voting:
            await ctx.send(f"Start a voting session with `{guild_data.prefix}start` before nominating!")
            return False
        return True
    return commands.check(predicate)

def is_trusted():
    async def predicate(ctx):
        guild_data = guilds[ctx.guild.id]
        if not guild_data.trust_needed or "trusted" in [r.name.lower() for r in ctx.author.roles]:
            return True
        await ctx.send(f"You must be trusted in order to use the command. Owner can disable trusted with `{guild_data.prefix}trust`.")
        await ctx.message.add_reaction(Emojis.cross)
        return False
    return commands.check(predicate)


def help_embed(prefix, more: int=0):
    embed = discord.Embed()
    if more == 0:
        embed.title = "Help"
        embed.set_author(name="Book Club")
        embed.color = discord.Color.blue()

        embed.add_field(name="search", value=f"Search a book. `{prefix}search mexican gothic`", inline=False)
        embed.add_field(name="start", value=f"Start a voting session. Further help once executed", inline=False)
        embed.add_field(name="trust", value=f"`{prefix}trust 1` to require a 'trusted' role. `0` to disable.", inline=False)
        embed.add_field(name="help", value=f"Shows help. `{prefix}help 1` displays nomination help.", inline=False)
    else:
        embed.title = "Nomination Help"
        embed.set_author(name="Book Club")
        embed.color = discord.Color.blue()

        embed.add_field(name="nom", value=f"Nominates a book. ex: `{prefix}nom Voices from Chernobyl`.", inline=False)
        embed.add_field(name="vote", value=f"Vote books. ex: `{prefix}vote 2 1 3`.", inline=False)
        embed.add_field(name="ballot", value=f"Displays your ballot.", inline=False)
        embed.add_field(name="list", value=f"Lists nominated books.", inline=False)
        embed.add_field(name="ranks", value=f"List current rankings.", inline=False)
        embed.add_field(name="more", value=f"More about a nomination. ex: `{prefix}more 1`.", inline=False)
        embed.add_field(name="end", value=f"End the voting session. Declares the winner.", inline=False)

    return embed

@bot.event
async def on_ready():
    await bot.change_presence(activity=discord.Game("b!help for help"))
    print("Logged in as:")
    print(bot.user.name)
    print(bot.user.id)
    print("--------------")

@bot.command()
@commands.guild_only()
@is_trusted()
async def start(ctx):
    guild_data = guilds[ctx.guild.id]

    if guild_data.voting:
        await ctx.send("A voting session is already going. End with `b!end`")
    else:
        guild_data.voting = True
        guild_data.nominations = Nominations()
        await ctx.message.add_reaction(Emojis.check_mark)
        await ctx.send("Nomination started!")
        await ctx.send(embed=help_embed(guild_data.prefix, 1))

@bot.command(aliases=["nom"])
@commands.guild_only()
@voting_started()
@is_trusted()
async def nominate(ctx, *, book_name):
    guild_data = guilds[ctx.guild.id]
    person = Person(ctx.author)
    book = Book.get_book(book_name)
    if book is None:
        await ctx.send("Book does not exist")
        return
    created, nomination = guild_data.nominations.nominate(person, book)
    if created:
        await ctx.send(f"Added book **{book.title}**")
    elif person == nomination.nominator:
        await ctx.send(f"You've already nominated a book. Clear it with `{guild_data.prefix}rem`\nNote that all votes will be removed once the command is executed.")
    else:
        await ctx.send(f"Book already nominated by {nomination.nominator.name}")

@bot.command(aliases=["clear","rem"])
@commands.guild_only()
@voting_started()
@is_trusted()
async def remove(ctx):
    guild_data = guilds[ctx.guild.id]
    guild_data.nominations.clear_nomination(Person(ctx.author))
    await ctx.message.add_reaction(Emojis.check_mark)

@bot.command(aliases=["v"])
@commands.guild_only()
@voting_started()
@is_trusted()
async def vote(ctx, *ids):
    ids = tuple(map(int, ids))
    guild_data = guilds[ctx.guild.id]
    person = Person(ctx.author)
    if len(ids) == 0:
        await ctx.send(f"""Vote by picking the index of the book. For instance, `{guild_data.prefix}vote 1` to vote for the first book
You can also pick second and third place by executing `{guild_data.prefix}vote 1 2 3`""")
        return
    try:
        nominations = guild_data.nominations.get_nominations(*ids)
        guild_data.nominations.voting.vote(person, *nominations)
        await ctx.message.add_reaction(Emojis.check_mark)
    except IndexError:
        await ctx.send("One of your values is out of bounds!")
        await ctx.message.add_reaction(Emojis.cross)
    except Exception:
        await ctx.send("Duplicate votes")
        await ctx.message.add_reaction(Emojis.cross)

@bot.command()
@commands.guild_only()
@voting_started()
@is_trusted()
async def ballot(ctx, book_id: int=0):
    if (book_id > 0):
        nomination = guilds[ctx.guild.id].nominations.nominations[book_id - 1]
        await ctx.send(embed=nomination.embed())
        return
    person = Person(ctx.author)
    nominations = guilds[ctx.guild.id].nominations.voting.get_voter_nominations(person)
    embed = discord.Embed()
    embed.color = discord.Color.blue()
    embed.title = "My Ballot"
    embed.set_author(name="Book Club")
    if nominations != None:
        for place, nom in enumerate(nominations):
            embed.add_field(name=f"{get_place_str(place + 1)} {nom.book.title}", value=f"By {nom.book.author}", inline=False)
    await ctx.send(embed=embed)

@bot.command()
@commands.guild_only()
@voting_started()
async def more(ctx, id: int):
    guild_data = guilds[ctx.guild.id]
    book = guild_data.nominations.nominations[id - 1].book
    await ctx.send(embed=book.embed())

@bot.command()
@commands.guild_only()
@voting_started()
@is_trusted()
async def end(ctx):
    # TODO: Save previous nominations
    guild_data = guilds[ctx.guild.id]
    nominations = guild_data.nominations.winners()
    guild_data.voting = False
    if len(nominations) == 1:
        nomination = nominations[0]
        await ctx.send(f"The winner is: **{nomination.book.title}**, submitted by {nomination.nominator.mention()}")
    elif len(nominations) == 0:
        await ctx.send("Voting session ended without declaring winner")
    else:
        names = nominations[0].book.title
        for n in nominations[1:]:
            names += ", " + n.book.title
        await ctx.send(f"The winners are: **{names}**")
    guild_data.nominations = None

@bot.command()
@commands.guild_only()
@voting_started()
async def list(ctx):
    guild_data = guilds[ctx.guild.id]
    await ctx.send(embed=guild_data.nominations.embed())

@bot.command()
@commands.guild_only()
@voting_started()
async def ranks(ctx):
    guild_data = guilds[ctx.guild.id]
    await ctx.send(embed=guild_data.nominations.ranks().embed())

@bot.command()
async def search(ctx, *, book_name):
    book = Book.get_book(book_name)
    if book is None:
        await ctx.send("Book not found")
    else:
        await ctx.send(embed=book.embed())

@bot.command()
@commands.is_owner()
async def trust(ctx, val:bool):
    guild_data = guilds[ctx.guild.id]
    guild_data.trust_needed = val
    await ctx.message.add_reaction(Emojis.check_mark)

@bot.command()
async def ping(ctx):
    await ctx.send(f"Pong! Latency: {bot.latency} seconds")

@bot.command()
async def help(ctx, more: int=0):
    guild_data = guilds[ctx.guild.id]
    await ctx.send(embed=help_embed(guild_data.prefix, more))

token = ""
with open("token.txt", "r") as f:
    token = f.read()
if os.getenv("DISCORD_TOKEN") != None:
    token = os.getenv("DISCORD_TOKEN")

bot.run(token)
