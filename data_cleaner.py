import pandas as pd

from read_db import create_master, open_db

# Import the database from db
out = create_master(conn=open_db())
df = pd.DataFrame(out, columns=['releaseKey', 'typeID', 'metadata', 'tag'])

# Remove unnecessary data from metadata
eliminate = [1, 4, 5, 6, 7, 10, 19, 47, 1377, 1378, 1421, 1422, 1423, 1424, 3465, 3466]
df = (df[~df['typeID'].isin(eliminate)]).reset_index(drop=True)

# Define Additional Columns to be added
meta_types = {8: 'originalMeta', 9: 'originalTitle', 46: 'meta', 48: 'title'}
for key, value in meta_types.items():
    df[value] = df.loc[df['typeID'] == key, 'metadata']
df = df.groupby('releaseKey')[list(meta_types.values())].first().reset_index()

df.dropna(inplace=True)
df.drop(['originalTitle', 'originalMeta'], axis=1, inplace=True)
df.reset_index(inplace=True, drop=True)
