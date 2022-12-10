import os
import sys

_path_parent = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(_path_parent)

import matplotlib

matplotlib.use('Qt5Agg')
import matplotlib.dates as mdates
import matplotlib.pyplot as plt

from Utility import sharedUtils

# Parse config file
config_path = os.path.join(_path_parent, 'config.ini')
file_end = sharedUtils.get_file_end_from_config(config_path)
fields, table_name, where_data = sharedUtils.get_config_from_file(config_path, 'NETWORK')

# Parse command line arguments
parser = sharedUtils.get_basic_parser('Plot the stats from a SQL file generated with ipPacketsToStatsSQL.py', file_end)
parser.add_argument('--bytes', help='Show bytes sum on y axis. Default is packets count', action='store_true')
args = parser.parse_args()

# Get the DB files
if args.db_dir:
    args.db = sharedUtils.get_db_paths_from_dirs(args.db_dir, file_end)
else:
    sharedUtils.check_db_files_exist(args.db)

sharedUtils.validate_args(args)

# Create the datasets
datasets = []
for db_path in args.db:
    data = sharedUtils.get_data_from_db(db_path, args.start, args.end, fields, table_name, where_data, args.h24)

    if data:
        data = data if not args.h24 else sharedUtils.data_start_from_midnight(data)
        df = sharedUtils.get_data_frame_from_data(data, fields, grp_freq=args.grp_freq)

        if args.bytes:
            df = df.sum()
        else:
            df = df.count()
        df = df.reset_index()

        datasets.append({
            'label': sharedUtils.get_file_name_from_path(db_path),
            'df': df,
            'first_timestamp': data[0][0],
            'last_timestamp': data[-1][0]
        })
    else:
        print(f'No data found in {db_path}')

# Plot the data
if args.bytes:
    y_label = f'Bytes/{args.grp_freq}'
else:
    y_label = f'Packets/{args.grp_freq}'
if args.line_style == 'None':
    args.line_style = '-'
sharedUtils.plot_data_from_datasets(plt, 'plot', sharedUtils.get_file_name_from_path(__file__), datasets, fields,
                                    y_label, no_fill=args.no_fill, line_style=args.line_style, color=args.color,
                                    marker=args.marker, no_grid=args.no_grid, time=args.time, h24=args.h24,
                                    date_format=mdates.DateFormatter('%H:%M:%S'), grp_freq=args.grp_freq)

# Show plot
plt.show()
