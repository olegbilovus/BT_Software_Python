import os
import sys

_path_parent = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(_path_parent)

import sqlite3
import csv
import argparse
import os
import sharedUtils

config_path = os.path.join(_path_parent, 'config.ini')

parser = argparse.ArgumentParser()
parser.add_argument('--db', required=True, help='Database file')
parser.add_argument('--csv', required=True, help='CSV file')
args = parser.parse_args()

_, table_name, _ = sharedUtils.get_chart_config_from_file(config_path, 'NETWORK')

conn = sqlite3.connect(args.db)
cur = conn.cursor()
cur.execute(f'SELECT * FROM {table_name}')
sql_data = cur.fetchall()

with open(args.csv, 'r') as f:
    csv_dict = csv.DictReader(f)

    with open(f'{args.csv[:-4]}_new.csv', 'w') as f2:
        csv_file = csv.DictWriter(f2, fieldnames=csv_dict.fieldnames)
        csv_file.writeheader()

        for i, row in enumerate(csv_dict):
            row['No.'] = sql_data[i][0]
            row['Length'] = sql_data[i][7]
            row['Time'] = sql_data[i][1]
            csv_file.writerow(row)

conn.close()

os.remove(args.csv)
os.rename(f'{args.csv[:-4]}_new.csv', args.csv)
