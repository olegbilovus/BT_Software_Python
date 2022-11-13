import os
import requests
import matplotlib.pyplot as plt
import argparse
import re

from matplotlib.animation import FuncAnimation
from dotenv import load_dotenv
from datetime import datetime


class PowerLive:
    def __init__(self, ip, buffer_length, vertical=True, verbose=False):
        self.ip = ip
        self._ip_data = f'http://{self.ip}/meter/0'
        self.buffer_length = buffer_length
        self.verbose = verbose

        self.x1 = [0]
        self.y1 = [0]
        self.x2 = [0 for _ in range(self.buffer_length + 1)]
        self.y2 = [0 for _ in range(self.buffer_length + 1)]

        if vertical:
            self.fig, (self.ax1, self.ax2) = plt.subplots(2)
        else:
            self.fig, (self.ax1, self.ax2) = plt.subplots(1, 2)

        self.fig.suptitle(f'Shelly Plug Power Live - {datetime.utcnow()} (UTC)')
        self.ax1.set_xlabel('Time (s)')
        self.ax1.set_ylabel('Power (W)')
        self.ax1.grid()
        self.ax2.set_xlabel(f'Time (s), Buffer Length: {self.buffer_length}s')
        self.ax2.set_ylabel('Power (W)')
        self.ax2.grid()
        self.ln1, = self.ax1.plot([], [], 'g-')
        self.ln2, = self.ax2.plot([], [], 'g-')
        self.ani = FuncAnimation(self.fig, self.update, interval=1000)

        requests.get(f'http://{self.ip}/settings?led_status_disable=false')
        requests.get(f'http://{self.ip}/settings?led_power_disable=false')
        requests.get(f'http://{self.ip}/relay/0?turn=on')

        plt.show()

    def update(self, frame):
        data = requests.get(self._ip_data).json()
        if self.verbose:
            print(data)
        self.update_full_graph(data)
        self.update_buffer_graph(data)

        return self.ln1, self.ln2

    def update_full_graph(self, data):
        self.x1.append(self.x1[-1] + 1)
        self.y1.append(data['power'])
        self.update_set_data(self.ax1, self.ln1, self.x1, self.y1)

    # A better solution would be to use the original data in x1 and y1 and pass to the buffer only the indexes.
    # But it seems it can not be done in Python. If you use Slice operator, it will create a copy of the list arr[a:b]
    # from index a to b which means at every interval a list of length b-a will be created. The current solution only
    # requires 2 operations on the list and additional space for the list, compared to the Slice which would requires
    # b-a operations.
    def update_buffer_graph(self, data):
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

    def __del__(self):
        requests.get(f'http://{self.ip}/relay/0?turn=off')


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


    load_dotenv()

    parser = argparse.ArgumentParser()
    parser.add_argument('-ip', '--ip', type=ip_type, default=os.getenv('SHELLYPLUG_IP'), help='Shelly Plug IP')
    parser.add_argument('-hr', '--horizontal', action='store_true', help='horizontal layout, default is vertical')
    parser.add_argument('-b', '--buffer_length', type=buffer_length_type, default=30,
                        help='buffer length in seconds, must be a positive int value >= 2. Default is 30')
    parser.add_argument('-v', '--verbose', action='store_true',
                        help='verbose mode, print data to console. Default is False')
    args = parser.parse_args()

    if not args.ip:
        exit('Shelly Plug IP is not set, please set it in .env file or pass it as argument')

    PowerLive(args.ip, args.buffer_length, vertical=not args.horizontal)
