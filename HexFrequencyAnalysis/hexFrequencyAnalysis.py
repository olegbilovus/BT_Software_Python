import os
import sys
from pprint import pprint

import matplotlib.pyplot as plt

_path_parent = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(_path_parent)

import matplotlib
import argparse

from Utility import sharedUtils

config_path = os.path.join(_path_parent, 'config.ini')
sharedUtils.set_matplotlib_backend(matplotlib, config_path)
file_end = sharedUtils.get_single_value_from_config(config_path, 'FREQUENCYANALYSIS', 'file_end')

parser = argparse.ArgumentParser('Frequency analysis')
parser.add_argument('--file', help='File containing Hex Stream', required=True)
parser.add_argument('--lower', help='Case insensitive', action='store_true')
parser.add_argument('--color', help='Choose a custom color', default='#1f77b4')
parser.add_argument('--grid', help='Show the grid', action='store_true')
parser.add_argument('--threshold', help='Color in red the bars which are equal or higher than the set threshold',
                    type=int)
parser.add_argument('--threshold_color', help='Choose a custom color for the threshold', default='red')
parser.add_argument('--top_labels', help='Add label on top of bars instead of on x axe', action='store_true')
parser.add_argument('--top_labels_size', help='Top labels text size', type=int, default=6)

args = parser.parse_args()

with open(args.file) as f:
    hex_stream = f.read()
    len_f = len(hex_stream)

    data = {}
    for i in range(0, len_f, 2):
        hex_values = hex_stream[i:i + 2] if not args.lower else hex_stream[i:i + 2].lower()
        if hex_values in data:
            data[hex_values] += 1
        else:
            data[hex_values] = 1

    data = {i: data[i] for i in sorted(data.keys())}

    dataset = {
        'label': sharedUtils.get_file_name_from_path(args.file).split('.')[0],
        'data': data,
        'len': len_f,
        'colors': [args.color if v < args.threshold else args.threshold_color for v in
                   data.values()] if args.threshold else args.color
    }

pprint(dataset['data'])
fig, ax = plt.subplots()
ax.bar(dataset['data'].keys(), dataset['data'].values(), label=dataset['label'], color=dataset['colors'])
sharedUtils.set_fig_ax(fig, ax, dataset['label'], 'Symbol', 'Frequency', dataset['label'], no_grid=not args.grid,
                       maximize=True, plt=plt, skip_ticklabel=True)

if args.top_labels:
    ax.set_xticks([])
    for i, (k, v) in enumerate(dataset['data'].items()):
        ax.text(i, v, k, ha='center', size=args.top_labels_size)

plt.show()
