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


# Read the json file
def create_platform(db):
    """Extraction of platform by reading json from data/platform.json"""
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
