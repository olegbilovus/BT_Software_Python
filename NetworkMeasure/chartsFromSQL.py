import os
import sys

_path_parent = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(_path_parent)

import argparse
import sqlite3
from datetime import datetime

import matplotlib.dates as mdates
import matplotlib.pyplot as plt
import pandas as pd

from Utility import sharedUtils

file_end = 'IP_Packets.db'
# Parse command line arguments
parser = argparse.ArgumentParser(description='Plot the stats from a SQL file generated with ipPacketsToStatsSQL.')
db_grp = parser.add_mutually_exclusive_group(required=True)
db_grp.add_argument('--db', help='sqlite3 database to read from', nargs='+', default=[])
db_grp.add_argument('--db_dir',
                    help=f'Paths to directory where to search for DB files. File\'s name have to end with "{file_end}"',
                    nargs='+', default=[])
parser.add_argument('--grp_freq', help='Grouping frequency. Default "1s"', default='1s')
parser.add_argument('--time', help='Show time on x axis', action='store_true')
parser.add_argument('--bytes', help='Show bytes sum on y axis', action='store_true')
parser.add_argument('--start', type=str, help='Start date, format: YYYY-MM-DD HH:MM:SS')
parser.add_argument('--end', type=str, help='End date, format: YYYY-MM-DD HH:MM:SS')
parser.add_argument('--line_style', help='Choose a custom line style', default='-')
parser.add_argument('--no_fill', help='Do not fill the area under the line', action='store_true')
parser.add_argument('-v', '--verbose', action='store_true', help='Verbose output')
args = parser.parse_args()

# Get the DB files
if args.db_dir:
    for dir_name in args.db_dir:
        for file in os.listdir(dir_name):
            if file.endswith(file_end):
                args.db.append(os.path.join(dir_name, file))
else:
    for db_name in args.db:
        if not os.path.isfile(db_name):
            exit(f'File {db_name} not found')

len_dbs = len(args.db)

if len_dbs > 1 and args.time:
    raise argparse.ArgumentTypeError('Cannot use --time with more than one DB file')

# Create the datasets
fields = ['timestamp', 'length']
SQL_BASE = 'SELECT ' + ','.join(fields) + ' FROM pcap_stats'
ORDER_BY = ' ORDER BY ' + fields[0]

datasets = []
for db_name in args.db:
    conn = sqlite3.connect(db_name)
    cur = conn.cursor()
    if args.start and args.end:
        cur.execute(SQL_BASE + ' WHERE timestamp BETWEEN ? AND ?' + ORDER_BY, (args.start, args.end))
    elif args.start:
        cur.execute(SQL_BASE + ' WHERE timestamp >= ?' + ORDER_BY, (args.start,))
    elif args.end:
        cur.execute(SQL_BASE + ' WHERE timestamp <= ?' + ORDER_BY, (args.end,))
    else:
        cur.execute(SQL_BASE + ORDER_BY)

    data = cur.fetchall()
    if data:
        df = pd.DataFrame(data, columns=fields)
        df[fields[0]] = pd.to_datetime(df[fields[0]])
        df = df.groupby(pd.Grouper(key=fields[0], freq=args.grp_freq))

        if args.bytes:
            df = df.sum()
        else:
            df = df.count()
        df = df.reset_index()

        datasets.append({
            'label': sharedUtils.file_name(db_name),
            'df': df,
            'first_timestamp': data[0][0],
            'last_timestamp': data[-1][0]
        })
    else:
        print(f'No data found in {db_name}')

    conn.close()

datasets_len = len(datasets)

# Plot the datasets
if datasets_len == 1:
    plot_data = [None, datasets[0]['df'][fields[1]]]
    if args.time:
        plt.gca().xaxis.set_major_formatter(mdates.DateFormatter('%H:%M:%S'))
        plot_data[0] = datasets[0]['df'][fields[0]]
        plt.xlabel('Time (HH:MM:SS)')
    else:
        plot_data[0] = range(1, len(plot_data[1]) + 1)
        plt.xlabel(f'Time ({args.grp_freq})')

    plt.title(
        f'{datasets[0]["label"]} - {datetime.fromisoformat(datasets[0]["first_timestamp"])} - {datetime.fromisoformat(datasets[0]["last_timestamp"])} (UCT)')
    plt.plot(*plot_data, args.line_style)
    if not args.no_fill:
        plt.fill_between(*plot_data, alpha=0.3)
else:
    for dataset in datasets:
        plot_data = [None, dataset['df'][fields[1]]]
        plot_data[0] = range(1, len(plot_data[1]) + 1)
        plt.plot(*plot_data, args.line_style, label=dataset['label'])
        if not args.no_fill:
            plt.fill_between(*plot_data, alpha=0.3)
    plt.xlabel(f'Time ({args.grp_freq})')
    plt.legend()

# Plot the data
if args.bytes:
    plt.ylabel(f'Bytes/{args.grp_freq}')
else:
    plt.ylabel(f'Packets/{args.grp_freq}')
plt.grid()
plt.show()
