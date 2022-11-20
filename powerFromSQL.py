import argparse
import json
import ntpath
import os
import sqlite3
from datetime import datetime

import matplotlib.dates as mdates
import matplotlib.pyplot as plt
from dotenv import load_dotenv
from jinja2 import Template, Environment, FileSystemLoader

load_dotenv()

parser = argparse.ArgumentParser(description='Plot power data from SQL')
parser.add_argument('--db', type=str, nargs='+', default=[os.getenv('DB_NAME')],
                    help='SQLite DB file name. Default: DB_NAME env var ')
parser.add_argument('--chartjs', action='store_true', help='Use charts.js')
parser.add_argument('--matplotlib', action='store_true', help='Use matplotlib')
parser.add_argument('--start', type=str, help='Start date, format: YYYY-MM-DD HH:MM:SS')
parser.add_argument('--end', type=str, help='End date, format: YYYY-MM-DD HH:MM:SS')
args = parser.parse_args()

if not args.chartjs and not args.matplotlib:
    print('No chart library selected, using matplotlib')
    args.matplotlib = True

datasets = []

for db_name in args.db:
    conn = sqlite3.connect(db_name)
    cur = conn.cursor()
    SQL_BASE = 'SELECT timestamp, power FROM plug_load WHERE is_valid = 1'
    ORDER_BY = ' ORDER BY timestamp'

    if args.start and args.end:
        cur.execute(SQL_BASE + ' AND timestamp BETWEEN ? AND ?' + ORDER_BY, (args.start, args.end))
    elif args.start:
        cur.execute(SQL_BASE + ' AND timestamp >= ?' + ORDER_BY, (args.start,))
    elif args.end:
        cur.execute(SQL_BASE + ' AND timestamp <= ?' + ORDER_BY, (args.end,))
    else:
        cur.execute(SQL_BASE + ORDER_BY)

    datasets.append({'data': cur.fetchall(), 'label': ntpath.basename(db_name)})
    conn.close()

datasets_len = len(datasets)
max_number_of_rows = max([len(dataset['data']) for dataset in datasets])

for dataset in datasets:
    dataset['first_timestamp'] = dataset['data'][0][0]
    dataset['last_timestamp'] = dataset['data'][-1][0]
    for i in range(len(dataset['data'])):
        dataset['data'][i] = dataset['data'][i][1]

if args.chartjs:
    env = Environment(loader=FileSystemLoader('.'))
    template = env.get_template('chartjs_template.html')
    with open('chartjs.html', 'w') as f:
        f.write(template.render(labels=[i for i in range(1, max_number_of_rows + 1)],
                                datasets=json.dumps(datasets)))

if args.matplotlib:
    for dataset in datasets:
        plot_data = [[i for i in range(1, len(dataset['data']) + 1)], dataset['data']]

        if datasets_len > 1:
            plt.plot(plot_data[0], plot_data[1], label=dataset['label'])
        else:
            plt.plot(plot_data[0], plot_data[1], 'g-')

    plt.xlabel('Seconds since capture')
    plt.ylabel('Power (W)')
    plt.grid()
    if datasets_len > 1:
        plt.legend()
    else:
        head, tail = ntpath.split(args.db[0])
        file_name = tail or ntpath.basename(head)
        plt.title(
            f'Plug Power from {file_name} [{datetime.fromisoformat(datasets[0]["first_timestamp"])} - {datetime.fromisoformat(datasets[0]["last_timestamp"])}] (UTC)')

    plt.show()
