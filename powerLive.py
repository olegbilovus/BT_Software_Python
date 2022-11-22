import argparse
import re
import sqlite3
from abc import ABC, abstractmethod
from datetime import datetime

import matplotlib.pyplot as plt
import requests
from matplotlib.animation import FuncAnimation


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
    def __init__(self, plug: Plug, buffer_length, vertical=True, db_name=None, db_reset=False, verbose=False):
        self.plug = plug
        self.buffer_length = buffer_length
        self.verbose = verbose

        self.db_name = db_name
        if self.db_name:
            self.conn = sqlite3.connect(db_name)
            self.cur = self.conn.cursor()
            try:
                self.cur.execute(
                    'CREATE TABLE plug_load (timestamp TIMESTAMP PRIMARY KEY, power REAL, is_valid BOOLEAN)')
                self.conn.commit()
                print('Created table')
            except sqlite3.OperationalError:
                pass
            if db_reset:
                self.cur.execute('DELETE FROM plug_load')
                self.conn.commit()
                print('Deleted all rows from table')
            self.cur.execute('INSERT INTO plug_load VALUES (?, ?, ?)', (datetime.utcnow(), 0, 0))
            print(f'Data will be saved to {db_name}')

        self.x1 = [1]
        self.y1 = [self.plug.get_load()]
        self.x2 = [1]
        self.y2 = [self.y1[0]]

        if vertical:
            self.fig, (self.ax1, self.ax2) = plt.subplots(2)
        else:
            self.fig, (self.ax1, self.ax2) = plt.subplots(1, 2)

        self.fig.suptitle(f'{self.plug.name} Power Live [{datetime.utcnow()}] (UTC)')
        x1_label = 'Seconds since capture'
        self.ax1.set_xlabel(x1_label)
        y1_label = 'Power (W)'
        self.ax1.set_ylabel(y1_label)
        self.ax1.grid()
        x2_label = f'{x1_label}, Buffer Length: {self.buffer_length}s'
        self.ax2.set_xlabel(x2_label)
        self.ax2.set_ylabel(y1_label)
        self.ax2.grid()
        line_style = 'g-'
        self.ln1, = self.ax1.plot([], [], line_style)
        self.ln2, = self.ax2.plot([], [], line_style)
        self.ani = FuncAnimation(self.fig, self.update, interval=1000)

        if not self.plug.turn_on():
            exit('Failed to turn on plug')

        plt.show()

    def update(self, frame):
        data = {'timestamp': datetime.utcnow(), 'power': self.plug.get_load(), 'is_valid': 1}
        if self.verbose:
            print(data)
        self.update_full_graph(data)
        self.update_buffer_graph(data)
        if self.db_name:
            self.send_to_sql(data)

        return self.ln1, self.ln2

    def update_full_graph(self, data):
        self.x1.append(self.x1[-1] + 1)
        self.y1.append(data['power'])
        self.update_set_data(self.ax1, self.ln1, self.x1, self.y1)

    def update_buffer_graph(self, data):
        if len(self.x2) < self.buffer_length:
            self.x2.append(self.x2[-1] + 1)
            self.y2.append(data['power'])
        else:
            self.x2.pop(0)
            self.x2.append(self.x2[-1] + 1)
            self.y2.pop(0)
            self.y2.append(data['power'])
        self.update_set_data(self.ax2, self.ln2, self.x2, self.y2)

    @staticmethod
    def update_set_data(ax, ln, x, y):
        ln.set_data(x, y)
        ax.relim()
        ax.autoscale_view()

    def send_to_sql(self, data):
        self.cur.execute('INSERT INTO plug_load VALUES (?, ?, ?)',
                         (data['timestamp'], data['power'], data['is_valid']))
        self.conn.commit()

    def __del__(self):
        if self.db_name:
            self.conn.close()


if __name__ == '__main__':
    def buffer_length_type(value):
        ivalue = int(value)
        if ivalue < 2:
            raise argparse.ArgumentTypeError(f'{value} is an invalid positive int value, must be >= 2')

        return ivalue


    def ip_type(value):
        if not re.match(r'\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}', value):
            raise argparse.ArgumentTypeError(f'{value} is an invalid IP address')

        return value


    parser = argparse.ArgumentParser('Plug Power Live')
    parser.add_argument('--ip', type=ip_type, help='Plug IP. Default: PLUG_IP env var')
    parser.add_argument('-b', '--buffer_length', type=buffer_length_type, default=30,
                        help='buffer length in seconds, must be a positive int value >= 2. Default: 30')
    parser.add_argument('--plug_type', choices=[1, 2], default=1, type=int,
                        help='1 for Shelly Plug S, 2 for Netio PowerCable REST 101x. Default: 1')
    parser.add_argument('--hr', action='store_true', help='horizontal layout. Default: vertical')
    parser.add_argument('--db', help='SQLite DB file name. Default: DB_NAME env var')
    parser.add_argument('--db_reset', action='store_true', help='delete all rows from DB table')
    parser.add_argument('-v', '--verbose', action='store_true',
                        help='verbose mode, print data to console')
    args = parser.parse_args()

    if not args.ip:
        exit('IP is not set, please set it in .env file or pass it as argument')

    if args.plug_type == 2:
        plug_chosen = NetioPowerCableRest101(args.ip)
    else:
        plug_chosen = ShellyPlugS(args.ip)

    PowerLive(plug_chosen, args.buffer_length, vertical=not args.hr, db_name=args.db, db_reset=args.db_reset,
              verbose=args.verbose)
