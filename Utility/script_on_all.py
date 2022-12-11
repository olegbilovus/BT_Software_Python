# This script is not intended to be run directly. It has to be edited to fit your needs.

import ntpath
import os
import subprocess
import threading

dir_name = ""
script_loc = ""
threads = []

for file in os.listdir(dir_name):
    if file.endswith('.db'):
        file_name = ntpath.basename(file)[0:-3]
        pcap_name = f'{file_name}'
        db_loc = os.path.join(dir_name, file)
        pcap_loc = os.path.join(dir_name, pcap_name)
        cmd = f'py {script_loc} --pcap {pcap_loc} --db {db_loc} --db_reset'
        print(cmd)
        t = threading.Thread(target=subprocess.call, args=(cmd,), daemon=True)
        threads.append(t)
        t.start()

for t in threads:
    t.join()

print('All done')
