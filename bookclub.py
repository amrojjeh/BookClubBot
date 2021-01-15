import json
from collections import defaultdict
from itertools import chain

import discord # Used for embeds
import requests

def get_place_str(place: int):
    if place == 1:
        return ":first_place:"
    if place == 2:
        return ":second_place:"
    if place == 3:
        return ":third_place:"
    return f"({place}th)"

class Person:
    def __init__(self, user):
        self.id = user.id
        self.name = user.name

    def __eq__(self, other):
        return self.id == other.id

    def __hash__(self):
        return self.id

    def __str__(self):
        return f"{name}"

    def __repr__(self):
        return f"Person({self.name})"

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

    def __repr__(self):
        return f"Book({self.id})"

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
        .set_author(name=self.author)\
        .add_field(name="Pages", value=self.pages, inline=True)
        return embed

class Nominations:
    class Rankings:
        def __init__(self, parent, ranks):
            """parent: Nominations
            ranks: [(rank: int, nomination: Nominations.Nomination)]
            """
            ranks.sort(key=lambda x: x[0])
            self.ranks = ranks
            self.parent = parent

        def tied(self):
            """Get highest tied results. Tie breaker is not applied here.

            Results
            --------
            [Nominations.Nomination]
                List of tied nominations
            """
            if len(self.ranks) == 0:
                return []
            tied = []
            common_rank = self.ranks[0][0]
            for rank, n in self.ranks:
                if rank == common_rank:
                    tied.append(n)
                else:
                    break
            return tied

        def winners_after_tiebreaker(self):
            if len(self.ranks) == 0:
                return []
            tied_winners = self.tied()
            if len(tied_winners) == 1:
                return tied_winners

            for place in range(1, self.parent.size() + 1):
                max_count = 0
                for n in tied_winners:
                    count = len(n.get_votes()[place])
                    max_count = count if count > max_count else max_count
                result = []
                for n in tied_winners:
                    if len(n.get_votes()[place]) == max_count:
                        result.append(n)
                tied_winners = result
                if len(tied_winners) == 1:
                    return tied_winners
            return tied_winners

        def embed(self):
            embed = discord.Embed()
            embed.color = discord.Color.blue()
            embed.title = "Rankings"
            embed.set_author(name="Book Club")
            tied_winners = self.winners_after_tiebreaker()
            for i in tied_winners:
                embed.add_field(name=f":crown:{i.book.title} by {i.book.author}", value=f"{i.scores_str()} - rank {i.rank():.2f}", inline=False)
            for i in range(len(tied_winners), len(self.ranks)):
                i = self.ranks[i][1]
                embed.add_field(name=f"{i.book.title} by {i.book.author}", value=f"{i.scores_str()} - rank {i.rank():.2f}", inline=False)
            return embed

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

        def get_voter_nominations(self, user):
            """Returns all the votes made by the user

            user: Person
            returns: [Nominations.Nomination]
            """
            for v, noms in self.voters.items():
                if v == user:
                    return noms
            return None

    class Nomination:
        def __init__(self, nominations, nominator, book):
            self.nominator = nominator
            self.book = book
            self.parent = nominations

        def __repr__(self):
            return f"Nominations.Nomination({self.book})"

        def get_votes(self):
            """Returns a default dictionary with the keys being places and values being list of voters.
            Return
            -------
            defaultdict
                Example: {1: [Jack, John], 2: [Selina], 3: [], 4: [Berry McDonald]} 
            """
            votes = defaultdict(lambda: [])

            for voter, nominations in self.parent.voting.voters.items():
                for place, n in enumerate(nominations, start=1):
                    if self == n:
                        votes[place].append(voter)
                        break

            return votes

        def get_non_voters(self):
            """Returns a list of people who did not vote

            return: [Person]
            """
            all_voters = self.parent.voting.voters.keys()
            nominee_voters = chain.from_iterable(self.get_votes().values())
            non_voters = []

            # Find voters who didn't vote
            for v in all_voters:
                if not (v in nominee_voters):
                    non_voters.append(v)
            return non_voters

        def rank(self):
            rank = 0
            total_voters = 0
            didnt_vote = []
            for place, voters in self.get_votes().items():
                rank += len(voters) * place
                total_voters += len(voters)
            non_voters = len(self.get_non_voters())
            total_voters += non_voters
            rank += non_voters * self.parent.size()
            rank = (rank / total_voters) if total_voters != 0 else 0
            return rank

        def scores_str(self):
            rankings = self.get_votes()
            value = ""
            for i in range(1, self.parent.size() + 1):
                vote_count = len(rankings[i])
                if i < 4 or vote_count > 0:
                    value += f"{get_place_str(i)} {vote_count} "
            return value

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
            embed.add_field(name=f"{identifier}: {n.book.title} - {n.nominator.name}", value=n.scores_str(), inline=False)
        return embed

    def get_user_nomination(self, user):
        """Returns the nomination associated with the user.

        Parameters
        -----------
        user: Person
            The nominator
        Return
        -------
        Nominations.Nomination
            The nomination nominated by the nominator
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

    def ranks(self):
        """Returns the current state of the ranks

        Return
        ------
        Nominations.Rankings
            Represents a sorted list of ranked nominations
        """
        result = []
        for i in self.nominations:
            result.append((i.rank(), i))
        return Nominations.Rankings(self, result)

    def winners(self):
        """Returns the nominations with the best rankings

        Return
        ------
        [Nominations.Nomination]
            The list of nominations that had the best scores"""
        winners = self.ranks().winners_after_tiebreaker()
        return winners
