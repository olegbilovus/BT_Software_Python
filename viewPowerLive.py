import os
import requests
import matplotlib.pyplot as plt
import numpy as np
import argparse

from matplotlib.animation import FuncAnimation
from dotenv import load_dotenv

load_dotenv()

SHELLYPLUG_IP = os.getenv('SHELLYPLUG_IP')


class PowerLive:
    def __init__(self, buffer_length, vertical=True):
        self.buffer_length = buffer_length

        self.x1 = np.zeros(1, dtype=int)
        self.y1 = np.zeros(1, dtype=np.float32)
        self.x2 = np.zeros(self.buffer_length, dtype=int)
        self.y2 = np.zeros(self.buffer_length, dtype=np.float32)

        if vertical:
            self.fig, (self.ax1, self.ax2) = plt.subplots(2)
        else:
            self.fig, (self.ax1, self.ax2) = plt.subplots(1, 2)

        self.fig.suptitle('Shelly Plug Power Live')
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
        print(data)
        self.update_append(data)
        self.update_no_append(data)

        return self.ln1, self.ln2

    def update_append(self, data):
        self.x1 = np.append(self.x1, self.x1[-1] + 1)
        self.y1 = np.append(self.y1, data['power'])
        self.update_set_data(self.ax1, self.ln1, self.x1, self.y1)

    def update_no_append(self, data):
        self.x2 = np.roll(self.x2, -1)
        self.x2[-1] = self.x2[-2] + 1
        self.y2 = np.roll(self.y2, -1)
        self.y2[-1] = data['power']
        self.update_set_data(self.ax2, self.ln2, self.x2, self.y2)

    @staticmethod
    def update_set_data(ax, ln, x, y):
        ln.set_data(x, y)
        ax.relim()
        ax.autoscale_view()

    def __del__(self):
        requests.get(f'http://{SHELLYPLUG_IP}/relay/0?turn=off')


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('-hr', '--horizontal', action='store_true')
    parser.add_argument('-b', '--buffer_length', type=int, default=30)
    args = parser.parse_args()
    PowerLive(args.buffer_length, not args.horizontal)
