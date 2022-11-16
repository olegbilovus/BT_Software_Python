import argparse
import ntpath
import os
import sqlite3
from datetime import datetime

import matplotlib.dates as mdates
import matplotlib.pyplot as plt
from dotenv import load_dotenv

load_dotenv()

parser = argparse.ArgumentParser(description='Plot power data from SQL')
parser.add_argument('--db', type=str, default=os.getenv('DB_NAME'),
                    help='SQLite DB file name. Default: DB_NAME env var ')
parser.add_argument('--start', type=str, help='Start date, format: YYYY-MM-DD HH:MM:SS')
parser.add_argument('--end', type=str, help='End date, format: YYYY-MM-DD HH:MM:SS')
parser.add_argument('--time', action='store_true', help='Plot time instead of seconds since captures on x axis')
args = parser.parse_args()

conn = sqlite3.connect(args.db)
cur = conn.cursor()
SQL_BASE = 'SELECT timestamp, power, is_valid FROM plug_load'

if args.start and args.end:
    cur.execute(SQL_BASE + ' WHERE timestamp BETWEEN ? AND ?', (args.start, args.end))
elif args.start:
    cur.execute(SQL_BASE + ' WHERE timestamp >= ?', (args.start,))
elif args.end:
    cur.execute(SQL_BASE + ' WHERE timestamp <= ?', (args.end,))
else:
    cur.execute(SQL_BASE)

data = cur.fetchall()
conn.close()

plot_data = [[], []]
if args.time:
    for row in data:
        if row[2] == 1:
            plot_data[0].append(datetime.fromisoformat(row[0]))
            plot_data[1].append(row[1])
else:
    for i, row in enumerate(data):
        if row[2] == 1:
            plot_data[0].append(i)
            plot_data[1].append(row[1])

fig, ax = plt.subplots()
if args.time:
    ax.xaxis.set_major_formatter(mdates.DateFormatter('%H:%M:%S'))
    ax.set_xlabel('Time (HH:MM:SS)')
else:
    ax.set_xlabel('Seconds since capture')
ax.grid()
head, tail = ntpath.split(args.db)
file_name = tail or ntpath.basename(head)
fig.suptitle(
    f'Plug Power from {file_name} [{datetime.fromisoformat(data[0][0])} - {datetime.fromisoformat(data[-1][0])}] (UTC)')
ax.set_ylabel('Power (W)')
ax.plot(plot_data[0], plot_data[1], 'g-')

plt.show()
