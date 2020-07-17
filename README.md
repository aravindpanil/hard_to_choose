# hard_to_choose
##Choose a game from your GOG Library when you do not know what to play

###Current Status
Building the Tabulated Data from the DB file as a CSV. The CSV acts as a 
source to the random game picker. 

##Tools Used
[SQLite Viewer](https://inloop.github.io/sqlite-viewer/) - Viewing the DB File
Structure to analyze and choose the right columns for optimal import of the 
database. 

[CSV Export Script](https://github.com/AB1908/GOG-Galaxy-Export-Script/) - The 
template for most of the importing from DB to Python and Python to CSV is taken
 from this repository.
