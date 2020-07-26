import os

import pandas as pd


def main():
    main_db = pd.read_pickle('data/main_db')
    xbox_db = pd.read_pickle('data/xbox_db')
    origin_db = pd.read_pickle('data/origin_db')
    dbase_dict = {'Games': main_db, 'Xbox Gamepass': xbox_db, 'Origin Access': origin_db}

    os.chdir('excel')
    filename = 'Games.xlsx'

    writer = pd.ExcelWriter(filename, engine='xlsxwriter')
    for sheetname, db in dbase_dict.items():  # loop through `dict` of dataframes
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
    os.chdir('..')
    print("Successfully written to excel/Games.xlsx")


if __name__ == '__main__':
    main()
