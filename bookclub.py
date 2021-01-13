import discord
from discord.ext import commands
import json
import requests
from collections import defaultdict

class Person:
	def __init__(self, user):
		self.id = user.id
		self.name = user.name

	def __eq__(self, other):
		return self.id == other.id

	def __hash__(self):
		return self.id

	def mention(self):
		return f"<@{self.id}>"

class Book:
	def __init__(self, id, volume_info):
		self.id = id
		self.author = volume_info["authors"][0] if "authors" in volume_info else "No author"
		self.title = volume_info["title"]
		self.thumbnail = volume_info["imageLinks"]["thumbnail"] if "imageLinks" in volume_info and "thumbnail" in volume_info["imageLinks"] else "https://raw.githubusercontent.com/amrojjeh/BookClubBot/main/default_cover.jpg"
		self.description = (volume_info["description"][:230] + ("..." if len(volume_info["description"]) > 230 else "")) if "description" in volume_info else "Description not found."
		self.pages = volume_info["pageCount"] if "pageCount" in volume_info else None

	def __eq__(self, other):
		return self.id == other.id

	def get_book(query):
		params = {"q": query}
		r = requests.get("https://www.googleapis.com/books/v1/volumes", params=params)
		j = json.loads(r.text)
		if j["totalItems"] == 0:
			return None
		return Book(j["items"][0]["id"], j["items"][0]["volumeInfo"])

	def embed(self):
		embed = discord.Embed()
		embed.color = discord.Color.blue()
		embed.title = self.title
		embed.description = self.description
		embed.set_thumbnail(url=self.thumbnail)\
		.set_author(name=self.author)
		return embed

class Nominations:
	class Voting:
		def __init__(self, parent):
			self.parent = parent
			self.voters = {}

		def vote(self, user, *noms):
			"""Add a voter and their votes. Assumes all nominations are within the parent nomination.
			"""
			if len(noms) <= self.parent.size() and len(noms) == len(set(noms)):
				self.voters[user] = noms
			else:
				raise Exception("Placements are not unique")

	class Nomination:
		def __init__(self, nominations, nominator, book):
			self.nominator = nominator
			self.book = book
			self.parent = nominations

		def get_votes(self):
			"""Returns a dictionary with the keys being places and values being list of voters.

			Example: {1: [Jack, John], 2: [Selina], 3: [], 4: [Berry McDonald]} 
			return: dict
			"""
			votes = defaultdict(lambda: [])

			for voter, nominations in self.parent.voting.voters.items():
				for place, n in enumerate(nominations, start=1):
					if self == n:
						votes[place].append(voter)
						break

			return votes

		def rank(self):
			rank = 0
			total_voters = 0
			for place, voters in self.get_votes().items():
				rank += len(voters) * place
				total_voters += len(voters)
			rank /= total_voters
			return rank

	def __init__(self):
		self.nominations = []
		self.voting = Nominations.Voting(self)

	def nominate(self, user, book):
		"""Returns the nomination created if operation was successful, with the boolean saying so
		Otherwise, it returns an already similar nomination without creating a new one.

		user: Person
		book: Book
		return: (boolean, Nominations.Nomination)
		"""
		for n in self.nominations:
			if n.book == book or n.nominator == user:
				return (False, n)
		n = Nominations.Nomination(self, user, book)
		self.nominations.append(n)
		return (True, n)

	def clear_nomination(self, user):
		"""Clears nomination made by the user.

		user: Person
		"""
		n = self.get_user_nomination(user)
		if n in self.nominations:
			self.nominations.remove(n)

	def embed(self):
		"""Return a Discord Embed that represents all nominations.

		return: discord.Embed
		"""
		embed = discord.Embed()
		embed.title = "Nominations"
		embed.set_author(name="Book Club")
		embed.color = discord.Color.blue()
		for identifier, n in enumerate(self.nominations, start=1):
			rankings = n.get_votes()
			vote_count = {1: 0, 2: 0, 3: 0}
			for i in range(1, self.size() + 1):
				vote_count[i] = len(rankings[i])
			value = f":first_place:{vote_count[1]} :second_place:{vote_count[2]} :third_place:{vote_count[3]}"

			for i in range(4, self.size() + 1):
				if vote_count[i] > 0:
					value += f" ({i}th) {vote_count[i]}"

			embed.add_field(name=f"{identifier}: {n.book.title} - {n.nominator.name}", value=value, inline=False)
		return embed

	def get_user_nomination(self, user):
		"""Returns the nomination associated with the user.

		user: Person
		return: Nominations.Nomination
		"""
		for n in self.nominations:
			if n.nominator == user:
				return n
		return None

	def remove_voter(self, user):
		for n in self.nominations:
			n.remove_voter(user)

	def get_nominations(self, *indicies):
		noms = []
		for i in indicies:
			if i <= self.size():
				noms.append(self.nominations[i - 1])
			else:
				raise IndexError(f"{i} is out of range")
		return noms

	def size(self):
		return len(self.nominations)

	def winner(self):
		"""Get the winner nomination.

		return: Nominations.Nomination"""
		if self.size() == 0:
			return None
		tied = []
		for n in self.nominations:
			rank = n.rank()
			if tied == []:
					tied = [(rank, n)]
			else:
				top_rank = tied[0]
				if rank < top_rank[0]:
					tied = [(rank, n)]
				elif rank == top_rank[0]:
					tied.append(rank, n)

		def tie_breaker(place=1):
			highest_count = (-1, None)
			for _, n in tied:
				count = len(n.get_votes()[place])
				if count > highest_count[0]:
					highest_count = (count, n)

			highest_counters = 0
			for _, n in tied:
				count = len(n.get_votes()[place])
				if highest_count[0] == count:
					highest_counters += 1

			if highest_counters > 1 and (place + 1) <= self.size():
				return tie_breaker(tied, place + 1)
			return highest_count[1]

		if len(tied) > 1:
			return tie_breaker()
		return tied[0][1]


class GuildData:
	def __init__(self):
		self.nominations = Nominations()
		self.voting = True


guilds = {}

description = """A bot that handles regular book club needs, primarily nominating books. It's designed so that it could be used without admin intervention """

intents = discord.Intents.default()
bot = commands.Bot(command_prefix="b!", description=description, intents=intents)

class Emojis:
	check_mark = "✅"
	cross = "❌"

# Example:
help = f"""Nominate books with `{bot.command_prefix}nom [BOOK_NAME]` or vote with `{bot.command_prefix}vote [FIRST PLACE ID] [SECOND PLACE ID] [THIRD PLACE ID]`.
List books with `{bot.command_prefix}list`. Remove a book you nominated with `{bot.command_prefix}remove [ID]`.
Finish the voting stage with `{bot.command_prefix}end`
Note: Using any of these commands requires the "trusted" role"""

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
		await ctx.send("You must be trusted in order to ues the command")
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
@is_trusted()
async def start(ctx):
	if ctx.guild.id in guilds:
		guild_data = guilds[ctx.guild.id]
		if guild_data.voting:
			await ctx.send("A voting session is already going. End with `b!end`")
		else:
			guild_data.voting = True
			await ctx.send(help)
	else:
		guilds[ctx.guild.id] = GuildData()
		await ctx.send(help)

@bot.command(aliases=["nom"])
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
@voting_started()
@is_trusted()
async def remove(ctx):
	guild_data = guilds[ctx.guild.id]
	guild_data.nominations.clear_nomination(Person(ctx.author))
	await ctx.message.add_reaction(Emojis.check_mark)

@bot.command(aliases=["v"])
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
@voting_started()
@is_trusted()
async def end(ctx):
	# TODO: Save previous nominations
	guild_data = guilds[ctx.guild.id]
	nomination = guild_data.nominations.winner()
	guild_data.voting = False
	if nomination is not None:
		await ctx.send(f"The winner is: **{nomination.book.title}**, submitted by {nomination.nominator.mention()}")
	else:
		await ctx.send("Voting session ended without declaring winner")

@bot.command()
@voting_started()
async def list(ctx):
	guild_data = guilds[ctx.guild.id]
	await ctx.send(embed=guild_data.nominations.embed())

@bot.command()
async def search(ctx, *, book_name):
	book = Book.get_book(book_name)
	if book is None:
		await ctx.send("Book not found")
	else:
		await ctx.send(embed=book.embed())

token = ""
with open("token.txt", "r") as f:
	token = f.read()
bot.run(token)
