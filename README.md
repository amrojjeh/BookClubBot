# BookClubBot

## Description
The bot has two purposes. Make book searching easier, and support a ranked voting system for book selection. As both purposes are fulfilled, future updates will primarily consist of refining the bot. Searching uses Google Books, and the ranked voting system works by allowing readers to vote for their most preferred book, followed by their second, third, and so on.

I hope this simple bot can improve your book club experience! For feedback, questions, or comments, email me at: amrojjeh@outlook.com.

## How to
The prefix is set to `b!`. The prefix cannot be changed.

Here are some essential commands:

`search [query]`: Just like using google books. Enter the query, and receive the description of the first book that's returned by Google.\
`b!start`: Starts a voting session. Allows you to nominate books and vote.\
`b!list`: List all the nominated books during a voting session.\
`b!end`: Ends the voting session. Also declares the winner.\
`b!vote [id1] [id2] [id3]...`: Vote for the selected books. Each `id` can be retrieved from `b!list`.\
`b!nominate`: Nominate a book during a voing session. This allows users to vote on it.

## Screenshots
![test](Screenshots/Searching.jpg)
![test](Screenshots/Listing%20nominations.jpg)

