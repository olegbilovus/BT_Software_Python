import os
import sys

_path_parent = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(_path_parent)

import argparse
from datetime import datetime

import matplotlib

matplotlib.use('Qt5Agg')
import matplotlib.dates as mdates
import matplotlib.pyplot as plt

from Utility import sharedUtils

file_end = 'Power.db'
parser = argparse.ArgumentParser(description='Plot power data from SQL')
sharedUtils.parser_add_db_dir_args(parser, file_end)
sharedUtils.parser_add_sql_args(parser)
sharedUtils.parser_add_matplotlib_args(parser, default_color='green')
parser.add_argument('--grp_freq', help='Grouping frequency. Default "1s"', default='1s')
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

fields = ['timestamp', 'power']
WHERE_DATA = 'is_valid = 1'
datasets = []
for db_path in args.db:
    data = sharedUtils.get_data_from_db(db_path, args.start, args.end, fields, 'plug_load', WHERE_DATA, h24=args.h24)

    if data:
        data = data if not args.h24 else sharedUtils.data_start_from_midnight(data)
        df = sharedUtils.get_data_frame_from_data(data, fields, grp_freq=args.grp_freq)
        df = df.mean()
        df = df.reset_index()

        datasets.append({
            'label': sharedUtils.file_name(db_path),
            'df': df,
            'first_timestamp': data[0][0],
            'last_timestamp': data[-1][0]
        })
    else:
        print(f'No data found in {db_path}')

# Plot the data
y_label = f'Power (W) /{args.grp_freq}'
sharedUtils.plot_data_from_datasets(plt, datasets, fields, y_label, no_fill=args.no_fill, line_style=args.line_style,
                                    color=args.color, marker=args.marker,
                                    no_grid=args.no_grid, time=args.time, h24=args.h24,
                                    date_format=mdates.DateFormatter('%H:%M:%S'), grp_freq=args.grp_freq)

# Show plot
plt.show()
