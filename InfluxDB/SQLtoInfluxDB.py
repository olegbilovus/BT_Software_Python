import os
import sys

_path_parent = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(_path_parent)

import argparse
import sqlite3
from datetime import datetime
from tqdm import tqdm

from influxdb_client import InfluxDBClient, Point
from influxdb_client.client.write_api import SYNCHRONOUS
import utils
import threading
import queue

from Utility import sharedUtils

# Parse config file
config_path = os.path.join(_path_parent, 'config.ini')
file_end = sharedUtils.get_file_end_from_config(config_path)
_, p_table_name, _ = sharedUtils.get_config_from_file(config_path, 'POWER')
_, n_table_name, _ = sharedUtils.get_config_from_file(config_path, 'NETWORK')
n_dst_field = sharedUtils.get_single_value_from_config(config_path, 'NETWORK', 'dst_field')

# Parse command line arguments
parser = argparse.ArgumentParser(description='SQLite DB of power and network to InfluxDB')
sharedUtils.parser_add_db_dir_args(parser, file_end)
parser.add_argument('-u', '--url', help='InfluxDB URL. Default from config.ini')
parser.add_argument('-t', '--token', help='InfluxDB token', required=True)
parser.add_argument('-o', '--org', help='InfluxDB organization', required=True)
parser.add_argument('-g', '--geoIP', help='GeoIP MaxMind DB directory path')
parser.add_argument('--threads', help='Number of threads to use for each job. If specify x threads, 2*x will be used.',
                    type=int, default=3)
args = parser.parse_args()

url, bucket, p_measurement, n_measurement = sharedUtils.get_config_influxdb_from_file(config_path)
url = args.url if args.url else url

if args.geoIP:
    geoIP = utils.GeoIP2(args.geoIP)
else:
    geoIP = None

# Get the DB files
if args.db_dir:
    args.db = sharedUtils.get_db_paths_from_dirs(args.db_dir, file_end)
else:
    sharedUtils.check_db_files_exist(args.db)

datasets = []
for db_path in args.db:
    with sqlite3.connect(db_path) as conn:
        c = conn.cursor()
        c.execute(f'SELECT * FROM {p_table_name}')
        p_data = c.fetchall()
        c.execute(f'SELECT * FROM {n_table_name}')
        n_data = c.fetchall()

        p_columns = sharedUtils.get_db_table_columns_obj(db_path, p_table_name, conn)
        n_columns = sharedUtils.get_db_table_columns_obj(db_path, n_table_name, conn)

    if p_data and n_data:
        p_ts_index = sharedUtils.get_timestamp_column_index(p_columns)
        n_ts_index = sharedUtils.get_timestamp_column_index(n_columns)
        n_dst_index = sharedUtils.get_column_index(n_columns, n_dst_field)

        if p_ts_index == -1:
            print(f'No timestamp column found in {p_table_name} table, skipping the whole database {db_path}')
            continue
        if n_ts_index == -1:
            print(f'No timestamp column found in {n_table_name} table, skipping the whole database {db_path}')
            continue
        if n_dst_index == -1:
            print(f'No {n_dst_field} column found in {n_table_name} table, skipping the whole database {db_path}')
            continue

        datasets.append({
            'label': sharedUtils.get_file_name_from_path(db_path),
            'p_data': p_data,
            'n_data': n_data,
            'p_columns': p_columns,
            'n_columns': n_columns,
            'p_ts_index': p_ts_index,
            'n_ts_index': n_ts_index,
            'n_dst_index': n_dst_index
        })
    else:
        print(f'No data in {db_path}')

# Connect to InfluxDB
client = InfluxDBClient(url=url, token=args.token, org=args.org)
write_api = client.write_api(write_options=SYNCHRONOUS)

starting_points = []


def worker_power(jobs):
    while True:
        dataset = jobs.get()
        for data in tqdm(dataset['p_data'], unit='power_data', desc=f'Processing {dataset["label"]} power data'):
            point = Point(p_measurement).tag('label', dataset['label'])
            for i, column in enumerate(dataset['p_columns']):
                if i != dataset['p_ts_index']:
                    point = point.field(column[1], data[i])
            point = point.time(datetime.fromisoformat(data[dataset['p_ts_index']]))
            write_api.write(bucket, args.org, point)

        jobs.task_done()


def worker_network(jobs):
    while True:
        dataset = jobs.get()
        for data in tqdm(dataset['n_data'], unit='network_data', desc=f'Processing {dataset["label"]} network data'):
            point = Point(n_measurement).tag('label', dataset['label'])
            for i, column in enumerate(dataset['n_columns']):
                if i != dataset['n_ts_index']:
                    point = point.field(column[1], data[i])
            point = point.time(datetime.fromisoformat(data[dataset['n_ts_index']]))
            if geoIP:
                geo_data = geoIP.get_relevant_data(data[dataset['n_dst_index']])
                if geo_data:
                    point = point.field('lat', geo_data['lat']).field('lon', geo_data['lon']).field('country',
                                                                                                    geo_data['country'])
            write_api.write(bucket, args.org, point)

        starting_points.append((dataset['label'], dataset['p_data'][0][dataset['p_ts_index']]))
        jobs.task_done()


# Write data to InfluxDB
p_jobs = queue.Queue()
n_jobs = queue.Queue()
threads = []
for _ in range(args.threads):
    p_t = threading.Thread(target=worker_power, args=(p_jobs,), daemon=True)
    p_t.start()
    threads.append(p_t)
    n_t = threading.Thread(target=worker_network, args=(n_jobs,), daemon=True)
    n_t.start()
    threads.append(n_t)

for ds in datasets:
    p_jobs.put(ds)
    n_jobs.put(ds)

p_jobs.join()
n_jobs.join()

write_api.close()
client.close()

print('\n' * (args.threads * 2))
print(f'Not found IPs for GeoIP: {geoIP.not_found_ips}')
print('Starting points:')
for sp in starting_points:
    print(f'{sp[0]}: {sp[1]}')
