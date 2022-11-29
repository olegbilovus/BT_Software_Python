import ntpath
from datetime import datetime


def file_name(file_path):
    head, tail = ntpath.split(file_path)
    return tail or ntpath.basename(head)


def data_start_from_midnight(data):
    i = 0
    while i < len(data):
        if datetime.fromisoformat(data[i][0]).hour == 0:
            break
        i += 1

    _data = data[i:]
    _data.extend(data[:i])

    return _data


def set_same_date(timestamp):
    return datetime.fromisoformat(timestamp).replace(year=2000, month=1, day=1).isoformat()
