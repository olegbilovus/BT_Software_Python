import argparse
import json
import os
import sqlite3
import webbrowser
from datetime import datetime

import matplotlib.dates as mdates
import matplotlib.pyplot as plt
import utils
from jinja2 import Template, Environment, FileSystemLoader

parser = argparse.ArgumentParser(description='Plot power data from SQL')
db_grp = parser.add_mutually_exclusive_group(required=True)
db_grp.add_argument('--db', type=str, nargs='+', default=[],
                    help='SQLite DB file name. Default: DB_NAME env var ')
db_grp.add_argument('--db_dir', type=str, nargs='+', default=[],
                    help='Paths to directories where to search for DB files')
parser.add_argument('--chartjs', action='store_true', help='Use charts.js')
parser.add_argument('--matplotlib', action='store_true', help='Use matplotlib')
parser.add_argument('--start', type=str, help='Start date, format: YYYY-MM-DD HH:MM:SS')
parser.add_argument('--end', type=str, help='End date, format: YYYY-MM-DD HH:MM:SS')
parser.add_argument('--time', action='store_true', help='Show time on x axis')
args = parser.parse_args()

if args.db_dir:
    for dir_name in args.db_dir:
        for file in os.listdir(dir_name):
            if file.endswith('.db'):
                args.db.append(os.path.join(dir_name, file))

if len(args.db) > 1 and args.time:
    raise argparse.ArgumentTypeError('Cannot use --time with more than one DB file')

for db_name in args.db:
    if not os.path.isfile(db_name):
        exit(f'File {db_name} not found')

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

    data = cur.fetchall()
    if data:
        datasets.append({
            'label': utils.file_name(db_name),
            'data': data
        })
    else:
        print(f'No data found in {db_name}')
    conn.close()

datasets_len = len(datasets)
max_number_of_rows = max([len(dataset['data']) for dataset in datasets])

for dataset in datasets:
    dataset['first_timestamp'] = dataset['data'][0][0]
    dataset['last_timestamp'] = dataset['data'][-1][0]

    if args.time:
        dataset['timestamps'] = []

    for i in range(len(dataset['data'])):
        if args.time:
            dataset['timestamps'].append(dataset['data'][i][0])
        dataset['data'][i] = dataset['data'][i][1]

if args.chartjs:
    env = Environment(loader=FileSystemLoader('.'))
    template = env.get_template('chartjs_template.html')

    with open('chartjs.html', 'w') as f:
        chart_datasets = []
        for dataset in datasets:
            chart_datasets.append({
                'label': dataset['label'],
                'data': dataset['data'],
                'fill': True if datasets_len > 1 else False,
            })

        f.write(template.render(labels=[i for i in range(1, max_number_of_rows + 1)],
                                datasets=json.dumps(chart_datasets)))

    webbrowser.open('file://' + os.path.realpath('chartjs.html'))

if args.matplotlib:
    if datasets_len == 1:
        plot_data = [[], datasets[0]['data']]
        if args.time:
            plt.gca().xaxis.set_major_formatter(mdates.DateFormatter('%H:%M:%S'))
            plot_data[0] = [datetime.fromisoformat(t) for t in datasets[0]['timestamps']]
            plt.xlabel('Time (HH:MM:SS)')
        else:
            for i in range(1, len(plot_data[1]) + 1):
                plot_data[0].append(i)

        plt.title(
            f'Plug Power from {utils.file_name(args.db[0])} [{datetime.fromisoformat(datasets[0]["first_timestamp"])} - {datetime.fromisoformat(datasets[0]["last_timestamp"])}] (UTC)')
        plt.plot(plot_data[0], plot_data[1], color='green')

    else:
        for dataset in datasets:
            plot_data = [[i for i in range(1, len(dataset['data']) + 1)], dataset['data']]

            if datasets_len > 1:
                plt.plot(plot_data[0], plot_data[1], label=dataset['label'])
                plt.fill_between(plot_data[0], plot_data[1], alpha=0.3)

        plt.xlabel('Seconds since capture')
        plt.legend()

    plt.ylabel('Power (W)')
    plt.grid()
    plt.show()
