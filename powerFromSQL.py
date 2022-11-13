import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import sqlite3
import os
import argparse

from datetime import datetime
from dotenv import load_dotenv

load_dotenv()

parser = argparse.ArgumentParser(description='Plot power data from SQL of a Shelly Plug')
parser.add_argument('--db', type=str, default=os.getenv('DB_NAME'), help='Database name')
parser.add_argument('--start', type=str, default=None, help='Start date, format: YYYY-MM-DD HH:MM:SS')
parser.add_argument('--end', type=str, default=None, help='End date, format: YYYY-MM-DD HH:MM:SS')
args = parser.parse_args()

conn = sqlite3.connect(args.db)
cur = conn.cursor()
SQL_BASE = 'SELECT timestamp, power FROM meter_0'

if args.start and args.end:
    cur.execute(SQL_BASE + ' WHERE timestamp BETWEEN ? AND ?', (args.start, args.end))
elif args.start:
    cur.execute(SQL_BASE + ' WHERE timestamp >= ?', (args.start,))
elif args.end:
    cur.execute(SQL_BASE + ' WHERE timestamp <= ?', (args.end,))
else:
    cur.execute(SQL_BASE)

data = cur.fetchall()

fig, ax = plt.subplots()
xformatter = mdates.DateFormatter('%H:%M:%S')
plt.gcf().axes[0].xaxis.set_major_formatter(xformatter)
ax.grid()
fig.suptitle(
    f'Shelly Plug Power from {args.db} [{datetime.fromisoformat(data[0][0])} - {datetime.fromisoformat(data[-1][0])}] (UTC)')
ax.set_xlabel('Time (HH:MM:SS)')
ax.set_ylabel('Power (W)')
ax.plot([datetime.fromisoformat(x[0]) for x in data], [x[1] for x in data], 'g-')
plt.show()
