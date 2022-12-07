import argparse
import sqlite3
from datetime import datetime

from influxdb_client import InfluxDBClient, Point
from influxdb_client.client.write_api import SYNCHRONOUS
from tqdm import tqdm

from sharedUtils import set_same_date

# Parse command line arguments
parser = argparse.ArgumentParser(description='SQLite to InfluxDB')
parser.add_argument('-s', '--sql', help='SQLite database file', required=True)
parser.add_argument('-i', '--influx', help='InfluxDB URL', required=True)
parser.add_argument('-t', '--token', help='InfluxDB token', required=True)
parser.add_argument('-o', '--org', help='InfluxDB organization', required=True)
parser.add_argument('-b', '--bucket', help='InfluxDB bucket', required=True)
parser.add_argument('--now',
                    help='Set the date of the data to the current one - 1 to easier find it. Time will not change',
                    action='store_true')
argparse = parser.parse_args()

# Connect to SQLite database
conn = sqlite3.connect(argparse.sql)
c = conn.cursor()

# Connect to InfluxDB
client = InfluxDBClient(url=argparse.influx,
                        token=argparse.token, org=argparse.org)
write_api = client.write_api(write_options=SYNCHRONOUS)

# Get list of tables
c.execute("SELECT name FROM sqlite_master WHERE type='table';")
tables = c.fetchall()

# Loop through tables
for table in tqdm(tables, unit='tables', desc='Processing tables'):
    # Get table name
    table_name = table[0]

    # Get column names
    c.execute("PRAGMA table_info(" + table_name + ")")
    columns = c.fetchall()
    ts_index = None
    for col in columns:
        if col[2] == 'TIMESTAMP':
            ts_index = col[0]
            break
    if ts_index is None:
        print('No timestamp column found in table ' + table_name)
        exit(1)

    # Get data
    c.execute("SELECT * FROM " + table_name)
    data = c.fetchall()
    today = datetime.now()

    # Send data to InfluxDB
    for row in tqdm(data, unit='rows', desc='Processing rows'):
        point = Point(table_name)
        ts = row[ts_index]
        if argparse.now:
            ts = set_same_date(ts, year=today.year,
                               month=today.month, day=today.day - 1)
        point.time(datetime.fromisoformat(ts))
        for i in range(len(columns)):
            if i != ts_index:
                point.field(columns[i][1], row[i])
        write_api.write(argparse.bucket, argparse.org, point)

# Close connections
write_api.close()
conn.close()
