# What is this?
Remembers is based off a site created for Hurricane Hackers that pulled data from a google docs spreadsheet, and rendered it into a dynamic gallery/slate like page for remembering people that died in hurricane Sandy. Shortly thereafter it was adapted to allow anyone to easily create a memorial page

# How does it work?
We pull data from the Google Docs JSON API to load rows of information about people based on a simple structure, from there we parse the data and return a rendered HTML page (thats also cached to lower load server side (and to keep within googles API limits))

# Whats it built on?
Remembers is built off Python, Flask and Redis. It was designed to be extremely fast, simple and lightweight for easy deploys.

# What can I do?
The css needs some work, and we can always use some bug testers ;)