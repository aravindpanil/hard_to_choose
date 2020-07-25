import json
import os
import re
import sqlite3

import numpy as np
import pandas as pd

import global_imports
from src import xbox_spreadsheet, origin_parse


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

    # Import Tag Database
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

    # Create Status and Length as two separate Columns
    temp['tag'] = temp['tag'].fillna('No tag')
    temp['Status'] = temp['tag'].apply(create_status)
    temp['Length'] = temp['tag'].apply(create_length)
    temp.drop(['tag'], axis=1, inplace=True)
    temp = temp.groupby('releaseKey')[['Status', 'Length']].first().reset_index()
    db = db.merge(temp, how='left', on='releaseKey')
    return db


def format_xbox(db):
    """Import Xbox Gamepass Details from Xbox Gamepass Masterlist in r/XboxGamePass subreddit"""

    db = pd.DataFrame(db[0], columns=db[1]).reset_index(drop=True)

    # Remove the header and make the first row as header
    new_header = db.iloc[0]
    db = db[1:]
    db.columns = new_header
    db.reset_index(drop=True, inplace=True)

    # Remove Xbox Games and unnecessary columns from the list
    db = db.drop(['Metacritic', 'Genre (Giantbomb)', 'Completion', 'Age', 'Release', 'Months'], axis=1).reset_index(
        drop=True)
    db = db[~(db['System'] == 'Xbox One')]
    db = db.drop(['System'], axis=1).reset_index(drop=True)
    return db


def remove_xboxgamepass(db, xdb):
    """Games removed from GP are still in main_db. Delete them"""

    temp = db.loc[db['platform'] == 'Xbox Gamepass'].copy()
    xtemp = xdb.loc[xdb['Status'].str.match(r'Active|Leaving Soon')].copy()

    # Temporarily remove special characters and convert to lowercase for comparison
    def temp_format_xbox(x):
        x = x.lower()
        x = re.sub('\s\(.*\)', '', x)
        x = re.sub('\'', '', x)
        x = re.sub(': (\w+\sedition)', '', x)
        x = re.sub(': (\w+\scut)', '', x)
        x = re.sub(' iii', '3', x)
        x = re.sub(' ii', '2', x)
        x = re.sub(' iv', '4', x)
        x = re.sub(' ix', '9', x)
        x = re.sub(' xv', '15', x)
        x = re.sub('[^A-Za-z0-9]+', '', x)
        return x

    temp.loc[:, 'title'] = temp['title'].apply(temp_format_xbox)
    xtemp.loc[:, 'Game'] = xtemp['Game'].apply(temp_format_xbox)

    # Fetch index of all the games in main but not in Xbox Gamepass list and delete them
    out = temp[~temp['title'].isin(xtemp['Game'])].index
    db.drop(out, inplace=True)
    db.reset_index(drop=True, inplace=True)
    return db


def import_origin():
    """Import Origin Access Database by scraping from PCGamingWiki"""

    basic, premiere = origin_parse.origin_games()
    data = pd.DataFrame(basic, columns=['Title', 'Subscription'])
    data = data.append(pd.DataFrame(premiere, columns=data.columns))
    data = data.sort_values('Title').reset_index(drop=True)
    return data


def group_platform(db):
    """Group games owned in multiple platforms to one row"""

    temp = db.groupby('Title').agg({'Platform': '; '.join})
    db = db.merge(temp, how='inner', left_on=['Title'], right_on=['Title'])
    db = db.drop('Platform_x', axis=1)
    db = db.drop_duplicates(subset=['Title', 'Platform_y'], keep='last')
    db = db.reset_index(drop=True)
    db = db.rename(columns={"Platform_y": "Platform"})
    return db


def manual_tagging(db):
    """Some tags are glitched. Add Game title, Status Tag and length to data/tag"""

    with open('data/tag.txt') as f:
        row = f.read().split('\n')
        for i in row:
            col = i.split(',')
            db.loc[db['Title'].str.contains(col[0]), 'Length'] = col[1]
            db.loc[db['Title'].str.contains(col[0]), 'Status'] = col[2]
    return db


def write_excel(data_dict):
    """Export main_db, xbox_db and origin_db to excel/Games.xlsx and auto adjust column width"""

    filename = 'Games.xlsx'
    writer = pd.ExcelWriter(filename, engine='xlsxwriter')
    for sheetname, db in data_dict.items():  # loop through `dict` of dataframes
        db.to_excel(writer, sheet_name=sheetname, index=False)  # send df to writer
        worksheet = writer.sheets[sheetname]  # pull worksheet object
        for idx, col in enumerate(db):  # loop through all columns
            series = db[col]
            max_len = max((
                series.astype(str).map(len).max(),  # len of largest item
                len(str(series.name))  # len of column name/header
            )) + 1  # adding a little extra space
            worksheet.set_column(idx, idx, max_len)  # set column width
    writer.save()


def main():
    """Import mainDB based on GamePieceTypes and GamePieces"""

    # Import GamePieceTypes table for mapping the types of data to extract from GamePieces
    game_piece_type_query = 'SELECT * FROM GamePieceTypes'
    game_piece_type = import_database_from_sql(game_piece_type_query, global_imports.main_db_path)

    # Import the GamePieces table which contains all the values about library games. Perform join on gamepieces to
    # get the metadata mapping
    main_db_query = """SELECT GamePieces.releaseKey, GamePieces.gamePieceTypeId, GamePieces.value
        FROM GameLinks
    	JOIN GamePieces ON GameLinks.releaseKey = GamePieces.releaseKey"""
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

    """Import Xbox Gamepass Games as a Dataframe"""
    xbox_db = format_xbox(xbox_spreadsheet.import_xbox_gsheet())
    # Format Xbox Gamepass DB Titles
    xbox_db = format_titles(xbox_db, 'Game')

    """Remove games not in XboX Gamepass. Some games removed from GP is still in main_db"""
    main_db = remove_xboxgamepass(main_db, xbox_db)

    """Rename Columns and import Origin"""
    origin_db = import_origin()

    main_db = main_db.rename(columns={"title": "Title", "date": "Release", "platform": "Platform"})
    xbox_db = xbox_db.rename(columns={"Game": "Title"})
    main_db.reset_index(drop=True, inplace=True)
    xbox_db.reset_index(drop=True, inplace=True)

    """Group games owned on multiple platforms"""
    main_db = group_platform(main_db)

    """Manually tag glitched tags"""
    main_db = manual_tagging(main_db)

    """Sort values by Title ignoring case"""
    main_db['Upper'] = main_db['Title'].str.upper()
    main_db.sort_values(by='Upper', inplace=True)
    del main_db['Upper']

    """Write output to excel"""
    os.chdir('excel')
    dbase_dict = {'Games': main_db, 'XboxGamepass': xbox_db, 'Origin Access': origin_db}
    write_excel(dbase_dict)

    print("Successfully generated DB. Total games - ", len(main_db.index))
    return main_db


if __name__ == '__main__':
    main()
