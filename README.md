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

## Level of Personilzation

The project is extremely specific to my use case. As mentioned earlier, the code can be reused. However, much of the project code, specifically tag imports and hiding of files will not work unless you have the exact same tagging system. The tagging system is as follows - 
* Create a tag called S - Status_value. This status can have any value you wish. Example values are Backlog, Playing, Tried etc. 
* Create a tag called L - Length_value. The length value can be any value such as Short, Long or infinite. 

Some of the modules that can be reused are - 
* The Xbox Gamepass import function is perfectly reusable. It fetches the data from [here](https://docs.google.com/spreadsheets/d/1kspw-4paT-eE5-mrCrc4R9tg70lH2ZTFrJOUmOtOytg/edit#gid=0). This publicly maintained sheet is manually updated by the owner. I have filtered it for PC Games only and removed some unnecessary information that I do not need for my use case. 
* The Origin Import function is usable. It scrapes the data from [PCGamingWiki](https://www.pcgamingwiki.com/wiki/List_of_Origin_Access_games). It sorts the values into two rows with information on whether the game is basic access or premiere access. 
* The import_database_from_sql, split_metadata_into_columns, extract_date, remove_manual_games_hidden_by_user, remove_games_hidden_by_gog are all reusable with small modifications. Documentation for each function is added in the code as docstrings. 
* Create Platform and data/platforms.json is perfectly reusable. 
* Most of the GUI code in src/randomizer_gui.py is reusable. 

## Files and purposes

* data folder - Contains files that are being read for cleaning the data. Sometimes there are rows which simply have the wrong data due to bugs with GOG Galaxy or the way the database is stored. Example - SUPERHOT tags are always NAN and cannot be rectified. These exceptions are being dealt with these text files. 
* notebooks - Contains all the jupyter notebooks being used for cleaning. Use this only as a reference
* main_csv_generator.py - Generates a CSV file which has the columns - releaseKey, Title, Release Year, Platform, Status and Length. 
* origin_parse.py - Generates a dataframe with games in Origin Vault or EA Access.
* randomizer_gui.py - Opens a GUI created using pykinter that filters based on the main database and generates a random game. 
* xbox_spreadsheet.py - Imports details from the google spreadsheet (public) and cleans the data for PC Specific use. Contains details such as Games added, Games removed, dates.

Most of the files are commented for public usage of the code and not the application as a whole. Feel free to raise an issue on github for any questions with the label 'question'. 
