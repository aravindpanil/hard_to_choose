import json
import re

import pandas as pd

from read_db import create_master, open_db, create_tag

# Import the database from db
df = pd.DataFrame(create_master(conn=open_db()), columns=['releaseKey', 'typeID', 'metadata'])

# Remove unnecessary data from metadata
eliminate = [1, 4, 5, 6, 7, 10, 19, 47, 1377, 1378, 1421, 1422, 1423, 1424, 3465, 3466]
df = (df[~df['typeID'].isin(eliminate)]).reset_index(drop=True)

# Define Additional Columns to be added
meta_types = {8: 'originalMeta', 9: 'originalTitle', 46: 'meta', 48: 'title'}
for key, value in meta_types.items():
    df[value] = df.loc[df['typeID'] == key, 'metadata']
df = df.groupby('releaseKey')[list(meta_types.values())].first().reset_index()

# delete duplicate Columns
df.dropna(inplace=True)
df.drop(['originalTitle', 'originalMeta'], axis=1, inplace=True)
df.reset_index(inplace=True, drop=True)

# Format date and drop meta
df['title'] = df['title'].apply(lambda x: x[10:-2])


def date_format(x):
    pattern = 'releaseDate\":(\d{9,10})'
    date = re.search(pattern, x)
    if date:
        return pd.to_datetime(date.group(0)[13:], unit='s').year
    else:
        return pd.to_datetime(0, unit='s').year


df['date'] = df['meta'].apply(date_format)

df.drop(['meta'], axis=1, inplace=True)
df.reset_index(inplace=True, drop=True)

# Extract Platform from releaseKey

with open('platforms.json') as f:
    platform = json.load(f)
    platform_keys = list(platform.keys())
    platform_pattern = re.compile(r"(\b{}\b)".format("|".join(platform_keys)))


def platform_extract(x):
    m = platform_pattern.match(x)
    if m:
        return platform[m.group(1)]


df['platform'] = df['releaseKey'].apply(platform_extract)

# Extract Tags
tagdf = pd.DataFrame(create_tag(conn=open_db()), columns=['releaseKey', 'tag'])
temp = df.merge(tagdf, how='left', left_on=['releaseKey'], right_on=['releaseKey'])


def tag_correct(x):
    tag_correction = {
        "Infinite": "L - Infinite",
        "Tried": "S - Tried",
        "Short": "L - Short",
        "Completed": "S - Completed"
    }
    tag_keys = list(tag_correction.keys())
    tag_pattern = re.compile(r"(\b{}\b)".format("|".join(tag_keys)))

    if pd.isnull(x):
        return "No Tag"
    m = tag_pattern.match(x)
    if m:
        return tag_correction[m.group(1)]
    else:
        return x


temp['tag'] = temp['tag'].apply(tag_correct)


def status_create(x):
    pattern = re.compile(r"S - (\w+)")
    if pattern.match(x):
        return pattern.match(x).group(1)
    return float('nan')


def length_create(x):
    pattern = re.compile(r"L - (\w+)")
    if pattern.match(x):
        return pattern.match(x).group(1)
    return float('nan')


temp['Status'] = temp['tag'].apply(status_create)
temp['Length'] = temp['tag'].apply(length_create)
temp.drop(['tag'], axis=1, inplace=True)
temp = temp.groupby('releaseKey')[['Status', 'Length']].first().reset_index()
df = df.merge(temp, how='left', left_on=['releaseKey'], right_on=['releaseKey'])
