# hard_to_choose
Choose a game from your GOG Library when you do not know what to 
play
***
This project contains two parts - 
1. The first is to extract the database from the GOG 
Galaxy 2.0 Client and store as a CSV. This will contain Title,
 Release Year, Platform and any custom tags. The CSV will also 
 have a personal categorization of the tags into Length and 
 Status. The project is a personal one and not aimed at general use
 by the public even though it can be forked, cloned and the code be
 reused. 
2. The second part is the development of a GUI tool to choose a
 random game. This GUI tool will have adjustable parameters based 
 on platform and tags. The GUI tool will use the CSV as a data 
 source. 
 ***
 ## Resources
 [SQLite Viewer](https://inloop.github.io/sqlite-viewer/) - Used to
 view the db file of the Galaxy Client. It is an online tool and 
 does not require download. 
 
[GOG-Galaxy-Export-Script](https://github.com/AB1908/GOG-Galaxy-Export-Script)
Much of the code to get the CSV is based on this script which
generates a CSV containing your GOG Galaxy Database. This is a more
generalized tool and works based on command line parameters. If you
are looking to export your GOG Galaxy data as a CSV, I would 
recommend using this tool.