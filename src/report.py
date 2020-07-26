import datetime
import pickle

import pandas as pd

import global_imports


def main():
    """Create a report with new games added since last run and log it to logs/ folder"""

    # Import current database and last run's database
    current_db = pd.read_pickle('data/main_db')
    old_db = pd.read_pickle('data/main_db_old')

    # Check for new games added since last run
    added_titles = current_db[~current_db['Title'].isin(old_db['Title'])]
    added_title_list = added_titles['Title']

    # Check for new games removed since last run
    removed_titles = old_db[~old_db['Title'].isin(current_db['Title'])]
    removed_title_list = removed_titles['Title']

    # Load last runtime
    last_runtime = pickle.load(open('data/lastrun.p', 'rb'))
    current_runtime = datetime.datetime.now()
    pickle.dump(current_runtime, open('data/lastrun.p', 'wb'))

    # Generate report text
    report_text = "\nReport for Game Database\n"

    report_text += 'Successfully generated Game database on '
    report_text += str(current_runtime)
    report_text += '\n'

    report_text += 'Total number of games - '
    report_text += str(len(current_db.index))
    report_text += '\n'

    report_text += 'Last run at - '
    report_text += str(last_runtime)
    report_text += '\n'

    if len(added_title_list):
        report_text += 'Number of games added since last run - '
        report_text += str(len(added_title_list))
        report_text += '\n'

        report_text += 'New Games Added - '
        report_text += '\n'
        for i in added_title_list:
            report_text += str(i)

    elif len(removed_title_list):
        report_text += 'Number of games removed since last run - '
        report_text += str(len(removed_title_list))
        report_text += '\n'

        report_text += 'New Games Added - '
        report_text += '\n'
        for i in removed_title_list:
            report_text += str(i)

    else:
        report_text += 'No new games added since last run\n'

    # Print report text to console as well. This also prints to powershell if run via script
    print(report_text)

    # Write report to file. Each date gets a new file. Same day report runs are appended
    with open(str(global_imports.log_folder_path) + '/' + str(datetime.date.today()) + '.txt', 'a+') as logfile:
        logfile.write(report_text)


if __name__ == '__main__':
    main()
