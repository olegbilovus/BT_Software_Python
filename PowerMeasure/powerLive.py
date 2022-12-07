import os
import sys

_path_parent = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(_path_parent)

import argparse
import queue
import re
import sqlite3
import threading
import time
from abc import ABC, abstractmethod
from datetime import datetime

import matplotlib

matplotlib.use('Qt5Agg')
import matplotlib.pyplot as plt
import requests
from matplotlib.animation import FuncAnimation

from Utility import sharedUtils


class Plug(ABC):

    @property
    @abstractmethod
    def name(self) -> str:
        pass

    @abstractmethod
    def get_load(self) -> float:
        pass

    @abstractmethod
    def turn_on(self) -> bool:
        pass

    @abstractmethod
    def turn_off(self) -> bool:
        pass


class ShellyPlugS(Plug):
    def __init__(self, ip):
        self.ip = ip
        self.session = requests.Session()

        self._url_load = f'http://{self.ip}/meter/0'

    @property
    def name(self):
        return 'Shelly Plug S'

    def get_load(self):
        return self.session.get(self._url_load).json()['power']

    def turn_on(self):
        self.session.get(f'http://{self.ip}/settings?led_status_disable=false')
        self.session.get(f'http://{self.ip}/settings?led_power_disable=false')
        return self.session.get(f'http://{self.ip}/relay/0?turn=on').json()['ison']

    def turn_off(self):
        return not self.session.get(f'http://{self.ip}/relay/0?turn=off').json()['ison']


class NetioPowerCableRest101(Plug):
    def __init__(self, ip):
        self.ip = ip
        self.session = requests.Session()

        self._url_load = f'http://{self.ip}/netio.json'

    @property
    def name(self):
        return 'Netio Power Cable REST 101'

    def get_load(self):
        return self.session.get(self._url_load).json()['Outputs'][0]['Load']

    def turn_on(self):
        return self.session.post(f'http://{self.ip}/netio.json',
                                 json={'Outputs': [{'ID': 1, 'Action': 1}]}).status_code == 200

    def turn_off(self):
        return self.session.post(f'http://{self.ip}/netio.json',
                                 json={'Outputs': [{'ID': 1, 'Action': 0}]}).status_code == 200


class PowerLive:
    def __init__(self, plug: Plug, db_name, db_reset=False, no_graph=False, n_threads=3, captures_limit=None,
                 interval=1000, verbose=False):
        self.plug = plug
        self.verbose = verbose
        self.captures_limit = captures_limit
        self.captures = 0
        self.file_end, self.fields, self.table_name, _ = sharedUtils.get_config_from_file(
            os.path.join(_path_parent, 'config.ini'), 'POWER')

        self.db_name = db_name if sharedUtils.check_file_end(db_name, self.file_end) else db_name + self.file_end
        self.conn = sqlite3.connect(self.db_name, check_same_thread=False)
        self.cur = self.conn.cursor()

        if db_reset:
            self.cur.execute('DROP TABLE IF EXISTS ' + self.table_name)
            self.conn.commit()
            print('Deleted all rows from table')

        try:
            self.cur.execute(
                'CREATE TABLE ' + self.table_name + ' (timestamp TIMESTAMP PRIMARY KEY, load REAL)')
            self.conn.commit()
            print('Created table')
        except sqlite3.OperationalError:
            pass
        self._sql_query = 'INSERT INTO ' + self.table_name + ' VALUES (?, ?)'

        print(f'Data will be saved to {self.db_name}')

        if not self.plug.turn_on():
            sys.exit('Failed to turn on plug')

        start = queue.Queue()
        self._lock = threading.Lock()
        if not no_graph:
            init_data = self.get_data()
            self.x1 = [1.0]
            self.y1 = [init_data[self.fields[1]]]
            self.send_to_sql(init_data)

            self.fig, self.ax1 = plt.subplots()
            self.fig.suptitle(f'{self.plug.name} Power Live [{datetime.utcnow()}] (UTC)')
            self.ax1.set_xlabel(f'Time (s) / Interval: {interval}ms')
            self.ax1.set_ylabel('Power (W)')
            self.ax1.grid()
            self.ln1, = self.ax1.plot([], [], 'g-')

            for _ in range(n_threads):
                threading.Thread(target=self.update, args=(start,), daemon=True).start()
            self.ani = FuncAnimation(self.fig, start.put, interval=interval)

            plt.show()
        else:
            for _ in range(n_threads):
                threading.Thread(target=self.worker_no_graph, args=(start,), daemon=True).start()
            while True:
                start.put(True)
                time.sleep(interval / 1000)

    def get_data(self):
        data = {self.fields[0]: datetime.utcnow().isoformat(), self.fields[1]: self.plug.get_load()}
        self.captures += 1
        if self.verbose:
            print(f'[#{self.captures}]{data}')

        return data

    def update(self, start):
        while True:
            start.get()
            self.check_captures_limit()
            data = self.get_data()
            self.update_full_graph(data)
            self.send_to_sql(data)

    def update_full_graph(self, data):
        self.x1.append(self.x1[-1] + self.ani._interval / 1000)
        self.y1.append(data[self.fields[1]])
        self.ln1.set_data(self.x1, self.y1)
        self.ax1.relim()
        self.ax1.autoscale_view()

    def send_to_sql(self, data):
        with self._lock:
            self.cur.execute(self._sql_query, (data[self.fields[0]], data[self.fields[1]]))
            self.conn.commit()

    def worker_no_graph(self, start):
        while True:
            start.get()
            self.check_captures_limit()
            data = self.get_data()
            self.send_to_sql(data)

    def check_captures_limit(self):
        if self.captures_limit is not None and self.captures >= self.captures_limit:
            print('Captures limit reached')
            os._exit(1)

    def __del__(self):
        self.conn.close()


if __name__ == '__main__':
    def ip_type(value):
        if not re.match(r'\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}', value):
            raise argparse.ArgumentTypeError(f'{value} is an invalid IP address')

        return value


    parser = argparse.ArgumentParser('Plug Power Live')
    parser.add_argument('--ip', type=ip_type, required=True, help='Plug IP')
    parser.add_argument('--plug_type', choices=[1, 2], default=1, type=int,
                        help='1 for Shelly Plug S, 2 for Netio PowerCable REST 101x. Default: 1')
    sharedUtils.parser_add_db_args(parser)
    parser.add_argument('--no_graph', action='store_true', help='Do not show graph')
    parser.add_argument('--threads', type=int, default=3, help='Number of threads to use. Default: 3')
    parser.add_argument('--captures_limit', type=int, help='Number of captures to make before exiting')
    parser.add_argument('--interval', type=int, default=1000,
                        help='Interval between captures in milliseconds. Default: 1000')
    parser.add_argument('-v', '--verbose', action='store_true', help='Verbose mode, print data to console')
    args = parser.parse_args()

    if args.plug_type == 2:
        plug_chosen = NetioPowerCableRest101(args.ip)
    else:
        plug_chosen = ShellyPlugS(args.ip)

    if not args.db:
        args.db = plug_chosen.name

    PowerLive(plug_chosen, db_name=args.db, db_reset=args.db_reset,
              no_graph=args.no_graph, n_threads=args.threads, captures_limit=args.captures_limit,
              interval=args.interval, verbose=args.verbose)
