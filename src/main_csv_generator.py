import json
import os
import re
import sqlite3

import numpy as np
import pandas as pd

import global_imports
from src import write_to_excel, report


def import_database_from_sql(sql_query, db_path):
    """Imports database from db or sqlite file as a pandas dataframe. Provide the SQL query and database path
as arguments"""

    connector = sqlite3.connect(db_path)
    db = pd.read_sql(sql_query, connector)
    return db


def split_metadata_into_columns(column_list, db, gpt):
    """Splits metadata of the main_db into different rows. Arguments are a list of column_names
    and the dataframe"""

    # Creates columns for each item in column_list
    for val in column_list:
        type_id = int(gpt.loc[gpt['type'] == val, 'id'])
        db[val] = db.loc[db['gamePieceTypeId'] == type_id, 'value']

    # Drop rows that are null in all of the generated columns. This will remove every row that
    # is not in column_list
    db = db.dropna(subset=column_list, how='all')

    # Drop every other row we do not need anymore
    db = db.drop(['value', 'gamePieceTypeId'], axis=1)

    # Group by releaseKey since the data is in its own rows. Fill row with NAN if every row is NAN
    db = db.groupby('releaseKey', as_index=True).agg(lambda x: np.nan if x.isnull().all() else x.dropna()).reset_index()
    db = db.set_index(np.arange(1, len(db) + 1))
    return db


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


def remove_hidden_games_by_gog(db):
    """Imports ReleaseProperties and deletes any games marked as hidden or DLC"""

    hidden_db_query = 'SELECT releaseKey, isDlc, isVisibleInLibrary FROM ReleaseProperties'
    hidden_db = import_database_from_sql(hidden_db_query, global_imports.main_db_path)

    # Delete everything marked as DLC or not visible in library
    db = db[~db['releaseKey'].isin(hidden_db.loc[hidden_db['isVisibleInLibrary'] == 0, 'releaseKey'])]
    db = db[~db['releaseKey'].isin(hidden_db.loc[hidden_db['isDlc'] == 1, 'releaseKey'])]
    db = db.reset_index(drop=True)
    return db


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


def format_titles(db, column):
    """Format Title by removing unneccessary items"""

    # Remove special apostrophe
    db[column] = db[column].str.replace('’', '')

    # Remove the at the beginning of the word
    db[column] = db[column].str.replace('^The\s', '')

    # Remove Trademark and Copyright Symbols
    db[column] = db[column].str.replace('\u2122|\u00AE', '')

    return db


def remove_duplicates(db):
    """Remove duplicates by various categories"""
    # Delete rows with same title and platform
    db = db.drop_duplicates(subset=['title', 'platform'], keep='last').reset_index(drop=True)

    # Delete rows with same title in 'Other' Platform
    dup = db[db.duplicated(subset=['title'], keep=False)].sort_values('title')
    db = db.drop(dup[dup['platform'].str.match('Other')].index).reset_index(drop=True)
    db = db[~db['title'].str.contains('trial$', flags=re.IGNORECASE)]

    return db


def create_tag(db):
    """Extracts tags from UserRelease and formats them into Length and Status"""

    # Import tags database
    tag_db_query = 'SELECT releaseKey, tag FROM UserReleaseTags'
    tag_db = import_database_from_sql(tag_db_query, global_imports.main_db_path)
    temp = db.merge(tag_db, how='left', left_on=['releaseKey'], right_on=['releaseKey'])

    def create_status(x):
        pattern = re.compile(r"S - (\w+)")
        if pattern.match(x):
            return pattern.match(x).group(1)
        return np.nan

    def create_length(x):
        pattern = re.compile(r"L - (\w+)")
        if pattern.match(x):
            return pattern.match(x).group(1)
        return np.nan

    def create_platform_other(x):
        pattern = re.compile(r"P - (\w+)")
        if pattern.match(x):
            return pattern.match(x).group(1)
        return np.nan

    # Create Status and Length as two separate Columns
    temp['tag'] = temp['tag'].fillna('No tag')
    temp['Status'] = temp['tag'].apply(create_status)
    temp['Length'] = temp['tag'].apply(create_length)
    temp['other_platform'] = temp['tag'].apply(create_platform_other)
    temp.drop(['tag'], axis=1, inplace=True)
    temp = temp.groupby('releaseKey')[['Status', 'Length', 'other_platform']].first().reset_index()
    db = db.merge(temp, how='left', on='releaseKey')
    return db


def platform_tag_correction(db):
    """Adds miscellaneous platforms like disc, pirated etc to original platform"""

    db.loc[db['platform'] == 'Other', 'platform'] = np.NaN
    db.loc[db['platform'] == 'Xbox Gamepass', 'platform'] = np.NaN
    db['platform'] = db['platform'].combine_first(db['other_platform'])
    db.drop(['other_platform'], axis=1, inplace=True)
    return db


def group_platform(db):
    """Group games owned in multiple platforms to one row"""

    temp = db.groupby('Title').agg({'Platform': '; '.join})
    db = db.merge(temp, how='inner', left_on=['Title'], right_on=['Title'])
    db = db.drop('Platform_x', axis=1)
    db = db.drop_duplicates(subset=['Title', 'Platform_y'], keep='last')
    db = db.reset_index(drop=True)
    db = db.rename(columns={"Platform_y": "Platform"})
    return db


def add_gameplay_time(db):
    """Extract Gameplay time from Gameplay Time Tracker and add it as a row to the main database"""

    time_query = 'SELECT ProductName, StatTotalFullRuntime FROM Applications'
    time_db = import_database_from_sql(time_query, global_imports.gtt_db_path)
    db = db.merge(time_db, how='left', left_on='Title', right_on='ProductName')
    db = db.drop('ProductName', axis=1)
    db['StatTotalFullRuntime'] = db['StatTotalFullRuntime'].fillna(0)
    db = db.rename(columns={"StatTotalFullRuntime": "GameplayTime"})

    def convert_to_hours(x):
        if x:

            # The value of gameplay has additional zeroes. Remove zeroes and convert to minutes
            x = x / (10000000 * 60)
            hours = int(x / 60)
            minutes = int(x % 60)

            # Return output according to whether minutes or hours are zero
            if hours and minutes:
                return str(hours) + ' Hours ' + str(minutes) + ' Minutes'
            elif hours:
                return str(hours) + ' Hours'
            elif minutes:
                return str(minutes) + ' Minutes'
        else:
            return 0

    db['GameplayTime'] = db['GameplayTime'].apply(convert_to_hours)
    return db


def save_dataframe(db):
    """Removes old database, marks the new database as old and generates a new database as a new database"""

    old = 'data/main_db_old'
    new = 'data/main_db'
    os.remove(old)
    os.rename(new, old)
    db.to_pickle(new)


def main():
    """Import mainDB based on GamePieceTypes and GamePieces"""

    # Import GamePieceTypes table for mapping the types of data to extract from GamePieces
    game_piece_type_query = 'SELECT * FROM GamePieceTypes'
    game_piece_type = import_database_from_sql(game_piece_type_query, global_imports.main_db_path)

    # Import the GamePieces table which contains all the values about library games. Perform join on gamepieces to
    # get the metadata mapping
    main_db_query = """SELECT GamePieces.releaseKey, GamePieces.gamePieceTypeId, GamePieces.value
        FROM GameLinks
    	JOIN GamePieces ON GameLinks.releaseKey = GamePieces.releaseKey
    	JOIN LibraryReleases ON GameLinks.releaseKey = LibraryReleases.releaseKey"""
    main_db = import_database_from_sql(main_db_query, global_imports.main_db_path)

    """Split the metadata into columns and delete all other metadata"""

    # Add any metadata needed to this list. Valid values are type names from GamePieceTypes
    column_names = ['title', 'meta']
    main_db = split_metadata_into_columns(column_names, main_db, game_piece_type)

    """Extract Release Date of games from metadata"""
    main_db = extract_date(main_db)

    """Extract platform from releaseKey and add it as a row"""
    main_db = create_platform(main_db)

    """Some games are hidden by GOG in ReleaseProperties. Import the table and delete these games"""
    main_db = remove_hidden_games_by_gog(main_db)

    """Delete games hidden by the user from UserReleaseProperties"""
    main_db = remove_manual_hidden_games_by_user(main_db)

    """Remove brackets and quotes around title"""
    main_db['title'] = main_db['title'].apply(lambda x: x[10:-2])

    """Format the Title and remove special Characters, certain keywords"""
    main_db = format_titles(main_db, 'title')

    """Remove duplicates by various categories"""
    main_db = remove_duplicates(main_db)

    """Extracts tags from UserRelease and formats them into Length and Status"""
    main_db = create_tag(main_db)

    """Combines miscellanous platforms like pirated, disc into main platform"""
    main_db = platform_tag_correction(main_db)

    main_db = main_db.rename(columns={"title": "Title", "date": "Release", "platform": "Platform"})
    main_db.reset_index(drop=True, inplace=True)

    """Group games owned on multiple platforms"""
    main_db = group_platform(main_db)

    """Sort values by Title ignoring case"""
    main_db['Upper'] = main_db['Title'].str.upper()
    main_db.sort_values(by='Upper', inplace=True)
    del main_db['Upper']

    """Extract Gameplay from Gameplay Time Tracker and add it as a row"""
    main_db = add_gameplay_time(main_db)

    """Replaces old dataframe and new dataframe with newer updates"""
    save_dataframe(main_db)

    """Write database to excel"""
    write_to_excel.main()

    """Call report function to generate log"""
    report.main()


if __name__ == '__main__':
    main()
