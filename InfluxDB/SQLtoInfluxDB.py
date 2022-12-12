import os
import sys
import time

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
_, p_table_name, _ = sharedUtils.get_chart_config_from_file(config_path, 'POWER')
_, n_table_name, _ = sharedUtils.get_chart_config_from_file(config_path, 'NETWORK')
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

ip_utils = utils.IPUtils(args.geoIP)

# Get the DB files
if args.db_dir:
    args.db = sharedUtils.get_db_paths_from_dirs(args.db_dir, file_end)
else:
    sharedUtils.check_db_files_exist(args.db)

datasets = []
for db_path in args.db:
    with sqlite3.connect(db_path) as conn:
        c = conn.cursor()
        try:
            c.execute(f'SELECT * FROM {p_table_name}')
            p_data = c.fetchall()
        except sqlite3.OperationalError:
            p_data = None
            print(f'No power data in {db_path}')
        try:
            c.execute(f'SELECT * FROM {n_table_name}')
            n_data = c.fetchall()
        except sqlite3.OperationalError:
            n_data = None
            print(f'No network data in {db_path}')

        p_columns = sharedUtils.get_db_table_columns_obj(db_path, p_table_name, conn) if p_data else None
        n_columns = sharedUtils.get_db_table_columns_obj(db_path, n_table_name, conn) if n_data else None

    if p_data or n_data:
        p_ts_index = sharedUtils.get_timestamp_column_index(p_columns) if p_data else None
        n_ts_index = sharedUtils.get_timestamp_column_index(n_columns) if n_data else None
        n_dst_index = sharedUtils.get_column_index(n_columns, n_dst_field) if n_data else None

        error_msg = 'No {} column in {} table of {}, skipping the table'

        if p_ts_index == -1:
            print(error_msg.format('timestamp', p_table_name, db_path))
            p_data = None
        if n_ts_index == -1:
            print(error_msg.format('timestamp', n_table_name, db_path))
            n_data = None
        if n_dst_index == -1:
            print(error_msg.format(n_dst_field, n_table_name, db_path))
            n_data = None

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


def worker_power(jobs):
    while jobs.qsize() > 0:
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
    while jobs.qsize() > 0:
        dataset = jobs.get()
        for data in tqdm(dataset['n_data'], unit='network_data', desc=f'Processing {dataset["label"]} network data'):
            point = Point(n_measurement).tag('label', dataset['label'])
            for i, column in enumerate(dataset['n_columns']):
                if i != dataset['n_ts_index']:
                    point = point.field(column[1], data[i])
            point = point.time(datetime.fromisoformat(data[dataset['n_ts_index']]))
            if args.geoIP:
                geo_data = ip_utils.get_relevant_geoip_data(data[dataset['n_dst_index']])
                if geo_data:
                    point = point.field('lat', geo_data['lat']).field('lon', geo_data['lon'])
                    point = point.field('country', geo_data['country'])
            point = point.field('hostname', ip_utils.get_hostname_from_ip(data[dataset['n_dst_index']]))
            write_api.write(bucket, args.org, point)

        jobs.task_done()


# Write data to InfluxDB
p_jobs = queue.Queue()
n_jobs = queue.Queue()
for ds in datasets:
    if ds['p_data']:
        p_jobs.put(ds)
    if ds['n_data']:
        n_jobs.put(ds)

threads = []
for _ in range(args.threads):
    p_t = threading.Thread(target=worker_power, args=(p_jobs,), daemon=True)
    p_t.start()
    threads.append(p_t)
    n_t = threading.Thread(target=worker_network, args=(n_jobs,), daemon=True)
    n_t.start()
    threads.append(n_t)

done = False
while not done:
    for t in threads:
        if t.is_alive():
            time.sleep(1)
            break
    else:
        done = True

write_api.close()
client.close()

print('\n' * (args.threads * 2))
print(f'Not found IPs for GeoIP: {ip_utils.geoip2.not_found_ips}')
print(f'Number of hostnames: {len(ip_utils.hostname_ips_known)}')
