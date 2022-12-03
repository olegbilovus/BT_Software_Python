import os
import sys

_path_parent = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(_path_parent)

import argparse

import matplotlib

matplotlib.use('Qt5Agg')
import matplotlib.dates as mdates
import matplotlib.pyplot as plt

from Utility import sharedUtils

# Parse command line arguments
file_end = 'IP_Packets.db'
parser = argparse.ArgumentParser(description='Plot the stats from a SQL file generated with ipPacketsToStatsSQL.')
sharedUtils.parser_add_db_dir_args(parser, file_end)
sharedUtils.parser_add_sql_args(parser)
sharedUtils.parser_add_matplotlib_args(parser)
parser.add_argument('--grp_freq', help='Grouping frequency. Default "1s"', default='1s')
time_grp = parser.add_mutually_exclusive_group()
time_grp.add_argument('--time', help='Show time on x axis', action='store_true')
time_grp.add_argument('--h24', action='store_true', help='Compare dbs in 24h period starting from midnight')
parser.add_argument('--bytes', help='Show bytes sum on y axis', action='store_true')
parser.add_argument('-v', '--verbose', action='store_true', help='Verbose output')
args = parser.parse_args()

# Get the DB files
if args.db_dir:
    args.db = sharedUtils.get_db_paths_from_dirs(args.db_dir, file_end)
else:
    sharedUtils.check_db_files_exist(args.db)

len_dbs = len(args.db)

if len_dbs > 1 and args.time:
    raise argparse.ArgumentTypeError('Cannot use --time with more than one DB file')

# Create the datasets
fields = ['timestamp', 'length']
datasets = []
for db_path in args.db:
    data = sharedUtils.get_data_from_db(db_path, args.start, args.end, fields, 'pcap_stats', h24=args.h24)
    if data:
        data = data if not args.h24 else sharedUtils.data_start_from_midnight(data)
        df = sharedUtils.get_data_frame_from_data(data, fields, grp_freq=args.grp_freq)

        if args.bytes:
            df = df.sum()
        else:
            df = df.count()
        df = df.reset_index()

        datasets.append({
            'label': sharedUtils.file_name(db_path),
            'df': df,
            'first_timestamp': data[0][0],
            'last_timestamp': data[-1][0]
        })
    else:
        print(f'No data found in {db_path}')

datasets_len = len(datasets)

# Plot the datasets
fig, ax = plt.subplots()
if datasets_len == 1:
    title = sharedUtils.get_plot_title_one_db_from_dataset(datasets[0])
    legend = False
    sharedUtils.plot_data_from_dataset(datasets[0], fields, ax, args.time, args.no_fill, args.line_style,
                                       args.color, args.marker)
else:
    title = None
    legend = True
    for dataset in datasets:
        sharedUtils.plot_data_from_dataset(dataset, fields, ax, args.h24, args.no_fill, args.line_style,
                                           marker=args.marker)

# Show the plot
if args.time or args.h24:
    ax.xaxis.set_major_formatter(mdates.DateFormatter('%H:%M:%S'))
    x_label = 'Time (HH:MM:SS)'
else:
    x_label = f'Scale time (1:{args.grp_freq})'
if args.bytes:
    y_label = f'Bytes/{args.grp_freq}'
else:
    y_label = f'Packets/{args.grp_freq}'
sharedUtils.set_fig_ax(fig, ax, title, x_label, y_label, legend, args.no_grid, True, plt)
plt.show()
