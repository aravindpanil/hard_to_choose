import json
import re
import sqlite3

import numpy as np
import pandas as pd

import global_imports


def import_database_from_sql(sql_query, db_path):
    """Imports database from db or sqlite file as a pandas dataframe. Provide the SQL query and database path
as arguments"""

    connector = sqlite3.connect(db_path)
    db = pd.read_sql(sql_query, connector)
    return db


# Import GamePieceTypes table for mapping the types of data to extract from GamePieces
game_piece_type_query = 'SELECT * FROM GamePieceTypes'
game_piece_type = import_database_from_sql(game_piece_type_query, global_imports.main_db_path)

# Import the GamePieces table which contains all the values about library games. Perform join on gamepieces to get the
# metadata mapping
main_db_query = """SELECT GamePieces.releaseKey, GamePieces.gamePieceTypeId, GamePieces.value
    FROM GameLinks
	JOIN GamePieces ON GameLinks.releaseKey = GamePieces.releaseKey"""
main_db = import_database_from_sql(main_db_query, global_imports.main_db_path)
########################################################################################################################

"""Filter table for necessary metadata"""

# Add any metadata needed to this list. Valid values are type names
# from GamePieceTypes
column_names = ['title', 'meta']


def split_metadata_into_columns(column_list, db):
    """Splits metadata of the main_db into different rows. Arguments are a list of column_names
    and the dataframe"""

    # Creates columns for each item in column_list
    for val in column_list:
        type_id = int(game_piece_type.loc[game_piece_type['type'] == val, 'id'])
        db[val] = db.loc[db['gamePieceTypeId'] == type_id, 'value']

    # Drop rows that are null in all of the generated columns. This will remove every row that
    # is not in column_list
    db = db.dropna(subset=column_list, how='all')

    # Drop every other row we do not need anymore
    db = db.drop(['value', 'gamePieceTypeId'], axis=1)

    # Group by releaseKey since the data is in its own rows. Fill row with NAN if every row is NAN
    db = db.groupby('releaseKey', as_index=True).agg(lambda x: np.nan if x.isnull().all() else x.dropna()) \
        .reset_index(drop=True).reset_index()
    return db


main_db = split_metadata_into_columns(column_names, main_db)
########################################################################################################################

"""Extract Date from meta"""


def extract_date(db):
    """Extract Release Date from metadata and convert it into YYYY MM format"""

    date_pattern = 'releaseDate\":(\d{9,10})'

    def format_date(x):
        """Takes epoch time as argument and returns date in YYYY MM format"""
        date = re.search(date_pattern, x)
        if date:
            val = pd.to_datetime(date.group(1), unit='s')
            val = val.strftime('%Y %b')
            return val
        else:
            return 'No Date'

    db['date'] = db['meta'].apply(format_date)
    db = db.drop('meta', axis=1)
    return db


main_db = extract_date(main_db)
########################################################################################################################

"""Extract platform from releaseKey and add it as a row"""


def create_platform(db):
    """Extraction of platform by reading json from data/platform.json"""

    # Read the json file
    with open(global_imports.platforms_json) as platform_file:
        platform = json.load(platform_file)

    # Create a regex pattern of all platforms to match and then return the actual platform name
    platform_keys = list(platform.keys())
    platform_pattern = re.compile(r"(\b{}\b)".format("|".join(platform_keys)))

    def platform_extract(x):
        """Returns matching platform by using above generated regex as a pattern"""
        m = platform_pattern.match(x)
        if m:
            return platform[m.group(1)]

    db['platform'] = db['releaseKey'].apply(platform_extract)
    return db


main_db = create_platform(main_db)
########################################################################################################################

"""Delete games from ReleaseProperties"""


def remove_hidden_games_by_gog(db):
    """Imports ReleaseProperties and deletes any games marked as hidden or DLC"""

    hidden_db_query = 'SELECT releaseKey, isDlc, isVisibleInLibrary FROM ReleaseProperties'
    hidden_db = import_database_from_sql(hidden_db_query, global_imports.main_db_path)

    # Delete everything marked as DLC or not visible in library
    db = db[~db['releaseKey'].isin(hidden_db.loc[hidden_db['isVisibleInLibrary'] == 0, 'releaseKey'])]
    db = db[~db['releaseKey'].isin(hidden_db.loc[hidden_db['isDlc'] == 1, 'releaseKey'])]
    db = db.reset_index(drop=True)
    return db


main_db = remove_hidden_games_by_gog(main_db)
########################################################################################################################

"""Remove games marked as DLC and hidden by user"""


def remove_manual_hidden_games_by_user(db):
    """Imports UserReleaseProperties and deletes any games marked as hidden or not in table"""

    user_hidden_db_query = 'SELECT releaseKey, isHidden FROM UserReleaseProperties'
    user_hidden_db = import_database_from_sql(user_hidden_db_query, global_imports.main_db_path)

    # Remove games in main_db but not in user_hidden_db as these were never owned
    db = db.drop(db[~db['releaseKey'].isin(user_hidden_db['releaseKey'])].index)

    # Remove all games marked hidden
    db = db[~db['releaseKey'].isin(user_hidden_db.loc[user_hidden_db['isHidden'] == 1, 'releaseKey'])]
    db = db.reset_index(drop=True)
    return db


main_db = remove_manual_hidden_games_by_user(main_db)
########################################################################################################################

"""Remove brackets and quotes around title"""

main_db['title'] = main_db['title'].apply(lambda x: x[10:-2])


def format_titles(db, column):
    """Format Title by removing special and unicode characters like trademark"""

    # Remove Trademark and Copyright Symbols
    db[column] = db[column].str.replace('\u2122|\u00AE', '')

    # Remove Windows, Windows 10 and any word before it. for Windows 10, - Windows 10 would be removed
    db[column] = db[column].str.replace('\S+ Windows(?: 10)?', '')

    # Remove special apostrophe
    db[column] = db[column].str.replace('’', '')

    # Make any game with The in the middle of the sentence lower case
    db[column] = db[column].str.replace('\sthe\s', ' the ', flags=re.IGNORECASE)

    # Remove the at the beginning of the word
    db[column] = db[column].str.replace('^The\s', '')

    # Make any game with at in the middle of the sentence lower case
    db[column] = db[column].str.replace('\sat\s', ' at ', flags=re.IGNORECASE)
    db[column] = db[column].str.strip()

    return db


format_titles(main_db, 'title')
########################################################################################################################

"""Remove duplicates which have same title and platform"""

main_db = main_db.drop_duplicates(subset=['title', 'platform'], keep='first')
