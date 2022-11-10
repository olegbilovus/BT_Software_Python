import os
import requests
import matplotlib.pyplot as plt
import argparse

from matplotlib.animation import FuncAnimation
from dotenv import load_dotenv
from datetime import datetime

load_dotenv()

SHELLYPLUG_IP = os.getenv('SHELLYPLUG_IP')


class PowerLive:
    def __init__(self, buffer_length, vertical=True, verbose=False):
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

        self.fig.suptitle(f'Shelly Plug Power Live - {datetime.utcnow()}')
        self.ax1.set_xlabel('Time (s)')
        self.ax1.set_ylabel('Power (W)')
        self.ax1.grid()
        self.ax2.set_xlabel(f'Time (s), Buffer Length: {self.buffer_length}s')
        self.ax2.set_ylabel('Power (W)')
        self.ax2.grid()
        self.ln1, = self.ax1.plot([], [], 'g-')
        self.ln2, = self.ax2.plot([], [], 'g-')
        self.ani = FuncAnimation(self.fig, self.update, interval=1000)

        requests.get(f'http://{SHELLYPLUG_IP}/relay/0?turn=on')

        plt.show()

    def update(self, frame):
        data = requests.get(f'http://{SHELLYPLUG_IP}/meter/0').json()
        if self.verbose:
            print(data)
        self.update_append(data)
        self.update_no_append(data)

        return self.ln1, self.ln2

    def update_append(self, data):
        self.x1.append(self.x1[-1] + 1)
        self.y1.append(data['power'])
        self.update_set_data(self.ax1, self.ln1, self.x1, self.y1)

    def update_no_append(self, data):
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
        requests.get(f'http://{SHELLYPLUG_IP}/relay/0?turn=off')


if __name__ == '__main__':
    def buffer_length_type(value):
        ivalue = int(value)
        if ivalue < 2:
            raise argparse.ArgumentTypeError(f'{value} is an invalid positive int value, must be >= 2')

        return ivalue


    parser = argparse.ArgumentParser()
    parser.add_argument('-hr', '--horizontal', action='store_true', help='horizontal layout, default is vertical')
    parser.add_argument('-b', '--buffer_length', type=buffer_length_type, default=30,
                        help='buffer length in seconds, must be a positive int value >= 2. Default is 30')
    parser.add_argument('-v', '--verbose', action='store_true',
                        help='verbose mode, print data to console. Default is False')
    args = parser.parse_args()
    PowerLive(args.buffer_length, not args.horizontal)
