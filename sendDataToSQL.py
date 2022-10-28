import os
import requests
import psycopg2
import logs

from dotenv import load_dotenv
from time import sleep

load_dotenv()

logger = logs.get_logger('ShellyPlug', token=os.getenv('LOGTAIL_SHELLYPLUG'), stdout_r=True, stderr_r=True, file=True)

conn = psycopg2.connect(os.getenv('DATABASE_URL'))
cur = conn.cursor()
cur.execute('SELECT version()')
logger.info(cur.fetchone())

SHELLYPLUG_IP = os.getenv('SHELLYPLUG_IP')
while True:
    try:
        data = requests.get(f'http://{SHELLYPLUG_IP}/meter/0').json()
        logger.info('Received data from Shelly Plug', extra=data)
        cur.execute('INSERT INTO meter_0 (timestamp, power, overpower, is_valid) VALUES (%s, %s, %s, %s)',
                    (data['timestamp'], data['power'], data['overpower'], data['is_valid']))
        conn.commit()
        sleep(1)
    except KeyboardInterrupt:
        logger.info('KeyboardInterrupt')
        break
    except Exception as e:
        logger.error(e)
        conn.close()
        conn = psycopg2.connect(os.getenv('DATABASE_URL'))
        cur = conn.cursor()
        sleep(1)
