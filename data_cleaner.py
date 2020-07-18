import json
import re

import pandas as pd

from read_db import create_master, open_db

# Import the database from db
out = create_master(conn=open_db())
df = pd.DataFrame(out, columns=['releaseKey', 'typeID', 'metadata'])

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
    date_pattern = 'releaseDate\":(\d{9,10})'
    date = re.search(date_pattern, x)
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
    pattern = re.compile(r"(\b{}\b)".format("|".join(platform_keys)))


def platform_extract(x):
    m = pattern.match(x)
    if m:
        return platform[m.group(1)]


df['platform'] = df['releaseKey'].apply(platform_extract)
