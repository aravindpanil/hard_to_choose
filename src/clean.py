import json
import os
import re

import pandas as pd

from src import read_db, xbox_spreadsheet, origin_parse

os.chdir('D:\Projects\hard_to_choose\src')

# Import Other classes


# Import DB into Python
df = pd.DataFrame(read_db.import_master(conn=read_db.open_db()), columns=['releaseKey', 'typeID', 'metadata'])


# Remove unwanted metadata portions
def remove_metadata(data):
    eliminate = [1, 4, 5, 6, 7, 10, 19, 47, 1377, 1378, 1421, 1422, 1423, 1424, 3465, 3466]

    # Remove any rows whose metadata type was in eliminate since they were not needed
    return (data[~data['typeID'].isin(eliminate)]).reset_index(drop=True)


df = remove_metadata(df)


# Split Metadata into title and meta
def split_metadata(data):
    meta_types = {8: 'originalMeta', 9: 'originalTitle', 46: 'meta', 48: 'title'}

    # Create New rows for each item in meta_types
    for key, value in meta_types.items():
        data[value] = data.loc[data['typeID'] == key, 'metadata']

    # Split the metadata into title and meta and remove the other details
    data = data.groupby('releaseKey')[list(meta_types.values())].first().reset_index()
    data.dropna(inplace=True)
    data = data.drop(['originalTitle', 'originalMeta'], axis=1).reset_index(drop=True)
    return data


df = split_metadata(df)

# Remove the brackets
df['title'] = df['title'].apply(lambda x: x[10:-2])


# Format title to remove brackets and certain keywords
def format_title(data, column):
    # Remove trademark and copyright
    data[column] = data[column].str.replace('\u2122|\u00AE', '')

    # Remove all text within a bracket
    data[column] = data[column].str.replace('\(.*\)', '')

    # Generate Regex Expression with Keywords from keywords.txt
    with open('TXT/keywords.txt') as f:
        remove_strings = f.read().splitlines()
    pattern = '|'.join(remove_strings)

    # Remove all words with titles that contain keywords from keywords.txt
    data[column] = data[column].str.replace(pattern, '', case=False)

    # Remove trailing hyphens, colons and spaces
    df[column] = df[column].str.strip()
    data[column] = data[column].str.replace('(-|:)$', '')
    df[column] = df[column].str.strip()
    return data


df = format_title(df, 'title')
df.reset_index(drop=True, inplace=True)


# Extract Date from meta and delete meta
def extract_date(data):
    date_pattern = 'releaseDate\":(\d{9,10})'

    def format_date(x):
        date = re.search(date_pattern, x)
        if date:
            return pd.to_datetime(date.group(0)[13:], unit='s').year
        else:
            return pd.to_datetime(0, unit='s').year

    data['date'] = data['meta'].apply(format_date)
    return data


df = extract_date(df)

# Delete meta since we do not need it anymore
df = (df.drop(['meta'], axis=1)).reset_index(drop=True)


# Extract and create Platform Column
def create_platform(data):
    with open('platforms.json') as f:
        platform = json.load(f)

    # Create a regex pattern of all platforms to match and then return the actual platform name
    platform_keys = list(platform.keys())
    platform_pattern = re.compile(r"(\b{}\b)".format("|".join(platform_keys)))

    def platform_extract(x):
        m = platform_pattern.match(x)
        if m:
            return platform[m.group(1)]

    data['platform'] = data['releaseKey'].apply(platform_extract)
    return df


df = create_platform(df)


# Extract and create Length and Status Tags
def create_tag():
    # Import tags database
    tagdf = pd.DataFrame(read_db.import_tag(conn=read_db.open_db()), columns=['releaseKey', 'tag'])
    temp = df.merge(tagdf, how='left', left_on=['releaseKey'], right_on=['releaseKey'])

    def correct_tag(x):

        tag_correction = {
            "Infinite": "L - Infinite",
            "Tried": "S - Tried",
            "Short": "L - Short",
            "Completed": "S - Completed"
        }
        tag_pattern = re.compile(r"(\b{}\b)".format("|".join(list(tag_correction.keys()))))

        if pd.isnull(x):
            return "No Tag"
        m = tag_pattern.match(x)
        if m:
            return tag_correction[m.group(1)]
        else:
            return x

    temp['tag'] = temp['tag'].apply(correct_tag)

    def create_status(x):
        pattern = re.compile(r"S - (\w+)")
        if pattern.match(x):
            return pattern.match(x).group(1)
        return float('nan')

    def create_length(x):
        pattern = re.compile(r"L - (\w+)")
        if pattern.match(x):
            return pattern.match(x).group(1)
        return float('nan')

    # Create Status and Length as two separate Columns
    temp['Status'] = temp['tag'].apply(create_status)
    temp['Length'] = temp['tag'].apply(create_length)
    temp.drop(['tag'], axis=1, inplace=True)
    temp = temp.groupby('releaseKey')[['Status', 'Length']].first().reset_index()
    return temp


# Add the Status and Length to the main Table
df = df.merge(create_tag(), how='left', left_on=['releaseKey'], right_on=['releaseKey'])


# Remove Duplicate titles
def remove_duplicates(data):
    # Delete rows with same title and platform
    data = data.drop_duplicates(subset=['title', 'platform'], keep='first').reset_index(drop=True)

    # Delete rows with same title in 'Other' Platform
    dup = data[data.duplicated(subset=['title'], keep=False)]
    data = data.drop(dup[dup['platform'].str.match('Other')].index).reset_index(drop=True)
    return data


df = remove_duplicates(df)

# Import data from hidden games database
hidden = pd.DataFrame(read_db.import_hidden(conn=read_db.open_db()), columns=['releaseKey', 'dlc', 'visible'])
user_hidden = pd.DataFrame(read_db.import_user_hidden(conn=read_db.open_db()), columns=['releaseKey', 'hidden'])


# Remove games marked as DLC or hidden
def remove_hidden(x, data):
    return data[~data['releaseKey'].isin(x)]


# Get Release Key of hidden Games and remove them with the remove_hidden function
df = remove_hidden(hidden.loc[(hidden['dlc'] == 1) | (hidden['visible'] == 0), 'releaseKey'], df)
df = remove_hidden(df.loc[~df['releaseKey'].isin(user_hidden['releaseKey']), 'releaseKey'], df)
df = remove_hidden(user_hidden.loc[user_hidden['hidden'] == 1, 'releaseKey'], df)
df.reset_index(drop=True, inplace=True)


# Remove games manually added by reading hidden.txt
def remove_manually_hidden(data):
    with open('TXT/hidden.txt') as f:
        hidden_games = f.read().splitlines()
    data = data[~data['releaseKey'].isin(hidden_games)]
    return data


df = remove_manually_hidden(df)
df.reset_index(drop=True, inplace=True)

# Import Xbox Gamepass from Masterlist Google Sheet
xdf = xbox_spreadsheet.import_xbox_gsheet()


def format_xbox(data):
    data = pd.DataFrame(data[0], columns=data[1]).reset_index(drop=True)

    # Remove the header and make the first row as header
    new_header = data.iloc[0]
    data = data[1:]
    data.columns = new_header
    data.reset_index(drop=True, inplace=True)

    # Remove Xbox Games and unnecessary columns from the list
    data = data.drop(['Metacritic', 'Genre (Giantbomb)', 'Completion', 'Age', 'Release', 'Months'], axis=1).reset_index(
        drop=True)
    data = data[~(data['System'] == 'Xbox One')]
    data = data.drop(['System'], axis=1).reset_index(drop=True)

    return data


xdf = format_xbox(xdf)

# Rename Columns
df = df.rename(columns={"title": "Title", "date": "Release", "platform": "Platform"})
xdf = xdf.rename(columns={"Game": "Title"})
df.reset_index(drop=True, inplace=True)
xdf.reset_index(drop=True, inplace=True)

# Format Xbox Gamepass List Titles
xdf = format_title(xdf, 'Title')


# Remove games in main DB but not in Xbox Gamepass (Removed or Coming Soon)
def remove_xboxgamepass(data, xdata):
    temp = data.loc[df['Platform'] == 'Xbox Gamepass'].copy()
    xtemp = xdata.loc[xdf['Status'].str.match(r'Active|Leaving Soon')].copy()

    # Temporarily remove special characters and convert to lowercase for comparison
    def temp_format_xbox(x):
        x = x.lower()
        x = re.sub('(\w+\s+edition)', '', x)
        x = re.sub('[^A-Za-z0-9]+', '', x)
        x = re.sub('iii', '3', x)
        x = re.sub('ii', '2', x)
        x = re.sub('adeventure', 'adventure', x)
        x = x.strip()
        return x

    temp['Title'] = temp['Title'].apply(temp_format_xbox)
    xtemp['Title'] = xtemp['Title'].apply(temp_format_xbox)

    # Fetch index of all the games in main database but not in Xbox Gamepass list and delete them
    out = temp[~temp['Title'].isin(xtemp['Title'])].index
    data.drop(out, inplace=True)
    data.reset_index(drop=True, inplace=True)
    return data


df = remove_xboxgamepass(df, xdf)


# Import Origin Access Games Database
def import_origin():
    basic, premiere = origin_parse.origin_games()
    data = pd.DataFrame(basic, columns=['Title', 'Subscription'])
    data = data.append(pd.DataFrame(premiere, columns=data.columns))
    data = data.sort_values('Title').reset_index(drop=True)
    return data


odf = import_origin()
