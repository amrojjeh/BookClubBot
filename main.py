import discord
from discord.ext import commands
from bookclub import Nominations, Book, Person

guilds = {}

description = """A bot that handles regular book club needs, primarily nominating books. It's designed so that it could be used without admin intervention """

intents = discord.Intents.default()
bot = commands.Bot(command_prefix="b!", description=description, intents=intents)
bot.remove_command("help")

class GuildData:
	def __init__(self):
		self.nominations = Nominations()
		self.voting = True

class Emojis:
	check_mark = "✅"
	cross = "❌"

def voting_started():
	async def predicate(ctx):
		if ctx.guild.id in guilds:
			guild_data = guilds[ctx.guild.id]
			if not guild_data.voting:
				await ctx.send(f"Start a voting session with `{bot.command_prefix}start` before nominating!")
				return False
			return True
		else:
			await ctx.send(f"Start a voting session with `{bot.command_prefix}start` before nominating!")
			return False
	return commands.check(predicate)

def is_trusted():
	async def predicate(ctx):
		if "trusted" in [r.name.lower() for r in ctx.author.roles]:
			return True
		await ctx.send("You must be trusted in order to use the command")
		await ctx.message.add_reaction(Emojis.cross)
		return False
	return commands.check(predicate)

@bot.event
async def on_ready():
	print("Logged in as:")
	print(bot.user.name)
	print(bot.user.id)
	print("--------------")

@bot.command()
@commands.guild_only()
@is_trusted()
async def start(ctx):
	help_msg = f"""Nominate books with `{bot.command_prefix}nom [BOOK_NAME]` or vote with `{bot.command_prefix}vote [FIRST PLACE ID] [SECOND PLACE ID]...`.
List books with `{bot.command_prefix}list`. Remove a book you nominated with `{bot.command_prefix}rem`.
Finish the voting stage with `{bot.command_prefix}end` to delcare the winner
Note: Using any of these commands requires the "trusted" role"""

	if ctx.guild.id in guilds:
		guild_data = guilds[ctx.guild.id]
		if guild_data.voting:
			await ctx.send("A voting session is already going. End with `b!end`")
		else:
			guild_data.voting = True
			guild_data.nominations = Nominations()
			await ctx.send(help_msg)
	else:
		guilds[ctx.guild.id] = GuildData()
		await ctx.send(help_msg)

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
		await ctx.send(f"You've already nominated a book. Clear it with `{bot.command_prefix}rem`\nNote that all votes will be removed once the command is executed.")
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
		await ctx.send(f"""Vote by picking the index of the book. For instance, `{bot.command_prefix}vote 1` to vote for the first book
You can also pick second and third place by executing `{bot.command_prefix}vote 1 2 3`""")
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
async def ballot(ctx):
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
async def help(ctx):
	embed = discord.Embed()
	embed.title = "Help"
	embed.set_author(name="Book Club")
	embed.color = discord.Color.blue()

	embed.add_field(name="search", value=f"Search a book. `{bot.command_prefix}search mexican gothic", inline=False)
	embed.add_field(name="start", value=f"Start a voting session. Further help once executed", inline=False)
	embed.add_field(name="end", value=f"End a voting session. Declares the winner", inline=False)

	await ctx.send(embed=embed)

token = ""
with open("token.txt", "r") as f:
	token = f.read()
bot.run(token)
