import os
import sys

_path_parent = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(_path_parent)

import argparse
import json
import sqlite3
import webbrowser
from datetime import datetime

import matplotlib
matplotlib.use('Qt5Agg')
import matplotlib.dates as mdates
import matplotlib.pyplot as plt
from jinja2 import Environment, FileSystemLoader

from Utility import sharedUtils

file_end = 'Power.db'
parser = argparse.ArgumentParser(description='Plot power data from SQL')
sharedUtils.parser_add_db_dir_args(parser, file_end)
sharedUtils.parser_add_sql_args(parser)
sharedUtils.parser_add_matplotlib_args(parser, default_color='green')
parser.add_argument('--chartjs', action='store_true', help='Use charts.js')
time_grp = parser.add_mutually_exclusive_group()
time_grp.add_argument('--time', action='store_true', help='Show time on x axis')
time_grp.add_argument('--h24', action='store_true', help='Compare dbs in 24h period starting from midnight')
args = parser.parse_args()

# Get the DB files
if args.db_dir:
    args.db = sharedUtils.get_db_paths_from_dirs(args.db_dir, file_end)
else:
    sharedUtils.check_db_files_exist(args.db)

len_dbs = len(args.db)

if len_dbs > 1 and args.time:
    raise argparse.ArgumentTypeError('Cannot use --time with more than one DB file, use --h24 instead')

if args.h24 and len_dbs < 2:
    raise argparse.ArgumentTypeError('Cannot use --h24 with less than two DB files')

if not args.chartjs and not args.matplotlib:
    print('No chart library selected, using matplotlib')
    args.matplotlib = True

fields = ['timestamp', 'power']
WHERE_DATA = 'is_valid = 1'
datasets = []
for db_name in args.db:
    conn = sqlite3.connect(db_name)
    cur = conn.cursor()
    cur.execute(*sharedUtils.choose_sql_query(args.start, args.end, fields, 'plug_load', WHERE_DATA))

    data = cur.fetchall()
    if data:
        dataset = {
            'label': sharedUtils.file_name(db_name),
            'data': data if not args.h24 else sharedUtils.data_start_from_midnight(data),
            'first_timestamp': data[0][0],
            'last_timestamp': data[-1][0]
        }

        if args.time or args.h24:
            dataset['timestamps'] = []
        for i in range(len(dataset['data'])):
            if args.time or args.h24:
                dataset['timestamps'].append(dataset['data'][i][0])

            dataset['data'][i] = dataset['data'][i][1]

        datasets.append(dataset)
    else:
        print(f'No data found in {db_name}')
    conn.close()

datasets_len = len(datasets)
max_number_of_rows = max([len(dataset['data']) for dataset in datasets])

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

        f.write(template.render(labels=range(1, max_number_of_rows + 1),
                                datasets=json.dumps(chart_datasets)))

    webbrowser.open('file://' + os.path.realpath('chartjs.html'))

if args.matplotlib:
    if datasets_len == 1:
        plot_data = [None, datasets[0]['data']]
        if args.time:
            plt.gca().xaxis.set_major_formatter(mdates.DateFormatter('%H:%M:%S'))
            plot_data[0] = [datetime.fromisoformat(t) for t in datasets[0]['timestamps']]
            plt.xlabel('Time (HH:MM:SS)')
        else:
            plot_data[0] = range(1, max_number_of_rows + 1)

        plt.title(
            f'Plug Power from {sharedUtils.file_name(args.db[0])} [{datetime.fromisoformat(datasets[0]["first_timestamp"])} - {datetime.fromisoformat(datasets[0]["last_timestamp"])}] (UTC)')
        plt.plot(*plot_data, color=args.color, linestyle=args.line_style)
        if not args.no_fill:
            plt.fill_between(*plot_data, alpha=0.3, color=args.color)

    else:
        for dataset in datasets:
            plot_data = [None, dataset['data']]
            if args.h24:
                plot_data[0] = [datetime.fromisoformat(sharedUtils.set_same_date(t)) for t in dataset['timestamps']]
                plt.plot(*plot_data, label=dataset['label'], alpha=0.6)
            else:
                plot_data[0] = range(1, len(plot_data[1]) + 1)
                plt.plot(*plot_data, args.line_style, label=dataset['label'])
                if not args.no_fill:
                    plt.fill_between(*plot_data, alpha=0.3)

        if args.h24:
            plt.gca().xaxis.set_major_formatter(mdates.DateFormatter('%H:%M:%S'))
            plt.xlabel('Time (HH:MM:SS)')
        else:
            plt.xlabel('Seconds since capture')
        plt.legend()

    plt.ylabel('Power (W)')
    plt.grid()
    plt.show()
