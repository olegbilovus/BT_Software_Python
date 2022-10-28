import os
import requests
import matplotlib.pyplot as plt

from matplotlib.animation import FuncAnimation
from dotenv import load_dotenv

load_dotenv()

SHELLYPLUG_IP = os.getenv('SHELLYPLUG_IP')

fig = plt.figure()
plt.title('Shelly Plug Power Consumption')
plt.xlabel('Seconds since started')
plt.ylabel('Power (W)')
plt.grid()

x = [0]
y = [0]

ln, = plt.plot(x, y, 'g-')


def update(frame):
    data = requests.get(f'http://{SHELLYPLUG_IP}/meter/0').json()
    print(data)
    x.append(x[-1] + 1)
    y.append(data['power'])
    ln.set_data(x, y)
    fig.gca().relim()
    fig.gca().autoscale_view()
    return ln,


animation = FuncAnimation(fig, update, interval=1000)
plt.show()
