import os
import sys

_path_parent = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(_path_parent)

import matplotlib

import matplotlib.pyplot as plt
import pandas as pd

from Utility import sharedUtils

# Parse config file
config_path = os.path.join(_path_parent, 'config.ini')
sharedUtils.set_matplotlib_backend(matplotlib, config_path)
file_end = sharedUtils.get_file_end_from_config(config_path)
power_fields, power_table_name, power_where_data = sharedUtils.get_chart_config_from_file(config_path, 'POWER')
pkt_fields, pkt_table_name, pkt_where_data = sharedUtils.get_chart_config_from_file(config_path, 'NETWORK')
fields = [power_fields[1], pkt_fields[1]]

# Parse command line arguments
parser = sharedUtils.get_basic_parser('Plot power and packet charts from SQL database', file_end)
parser.add_argument('--power_sum', help='Use power sum. Default is power mean', action='store_true')
parser.add_argument('--bytes', help='Use bytes sum. Default is packets count', action='store_true')
parser.add_argument('--invert_axis', help='Display on x axe what would normally be displayed n y axe and vice-versa',
                    action='store_true')
args = parser.parse_args()

sharedUtils.validate_args(args)

# Get the DB files
if args.db_dir:
    args.db = sharedUtils.get_db_paths_from_dirs(args.db_dir, file_end)
else:
    sharedUtils.check_db_files_exist(args.db)

# Create the datasets
datasets = []
for db_path in args.db:
    power_data = sharedUtils.get_data_from_db(db_path, power_fields, power_table_name, args.start, args.end,
                                              power_where_data, args.h24)
    pkt_data = sharedUtils.get_data_from_db(db_path, pkt_fields, pkt_table_name, args.start, args.end, pkt_where_data,
                                            args.h24)

    if power_data and pkt_data:
        power_df = sharedUtils.get_data_frame_from_data(power_data, power_fields, grp_freq=args.grp_freq)
        pkt_df = sharedUtils.get_data_frame_from_data(pkt_data, pkt_fields, grp_freq=args.grp_freq)

        if args.power_sum:
            power_df = power_df.sum()
        else:
            power_df = power_df.mean()
        if args.bytes:
            pkt_df = pkt_df.sum()
        else:
            pkt_df = pkt_df.count()

        power_df = power_df.reset_index()
        pkt_df = pkt_df.reset_index()

        df_merge = pd.merge(power_df, pkt_df, on=pkt_fields[0], how='inner').dropna().reset_index()
        label = f'{sharedUtils.get_file_name_from_path(db_path)} ({sharedUtils.get_correlation_dataframe(df_merge, *fields)})'
        datasets.append({
            'label': label,
            'first_timestamp': power_data[0][0],
            'last_timestamp': power_data[-1][0],
            'df': df_merge
        })
    else:
        print(f'No data found in {db_path}')

# Plot the scatter plot
if args.power_sum:
    x_label = f'Power (W) sum/{args.grp_freq}'
else:
    x_label = f'Power (W) /{args.grp_freq}'
if args.bytes:
    y_label = f'Bytes/{args.grp_freq}'
else:
    y_label = f'Packets/{args.grp_freq}'

if args.invert_axis:
    fields = fields[::-1]
    x_label, y_label = y_label, x_label
sharedUtils.plot_data_from_datasets(plt, 'scatter', sharedUtils.get_file_name_from_path(__file__), datasets, fields,
                                    y_label, x_label=x_label, no_fill=True, color=args.color, marker=args.marker,
                                    no_grid=args.no_grid, legend=not args.no_legend, grp_freq=args.grp_freq,
                                    keep_xdata=True, force_legend=True)

plt.show()
