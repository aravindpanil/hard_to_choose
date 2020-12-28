import os

import pandas as pd


def main():
    main_db = pd.read_pickle('data/main_db')
    os.chdir('excel')
    filename = 'Games.xlsx'

    writer = pd.ExcelWriter(filename, engine='xlsxwriter')
    main_db.to_excel(writer, sheet_name='Games', index=False)  # send df to writer
    worksheet = writer.sheets['Games']  # pull worksheet object
    for idx, col in enumerate(main_db):  # loop through all columns
        series = main_db[col]
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
