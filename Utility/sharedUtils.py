import ntpath
import os
import sqlite3
from datetime import datetime

import pandas as pd


# Get the filename from a path
def file_name(file_path):
    head, tail = ntpath.split(file_path)
    return tail or ntpath.basename(head)


# Move data in a dataset to start from midnight
def data_start_from_midnight(data):
    i = 0
    flag = True
    for j in range(len(data)):
        if datetime.fromisoformat(data[j][0]).hour != 0 and not flag:
            i += 1
        else:
            flag = False
        data[j] = (set_same_date(data[j][0]), data[j][1])

    _data = data[i:]
    _data.extend(data[:i])

    return _data


# Set same date for a data
def set_same_date(timestamp, year=2020, month=1, day=1):
    return datetime.fromisoformat(timestamp).replace(year, month, day).isoformat()


# Add basic arguments to manage the db to a parser
def parser_add_db_args(parser):
    parser.add_argument('--db', required=True, help='sqlite3 database to write to')
    parser.add_argument('--db_reset', action='store_true', help='Reset the database')


# Add basic arguments to manage db_dir to a parser
def parser_add_db_dir_args(parser, file_end):
    db_grp = parser.add_mutually_exclusive_group(required=True)
    db_grp.add_argument('--db', nargs='+', default=[], help='sqlite3 database to write to')
    db_grp.add_argument('--db_dir', nargs='+', default=[],
                        help=f'Paths to directory where to search for DB files. File\'s name have to end with "{file_end}"')


# Add basic arguments to manage SQL timestamp to a parser
def parser_add_sql_args(parser):
    parser.add_argument('--start', type=str, help='Start timestamp, format: YYYY-MM-DD HH:MM:SS')
    parser.add_argument('--end', type=str, help='End timestamp, format: YYYY-MM-DD HH:MM:SS')


# Add basic arguments to manage matplotlib to a parser
def parser_add_matplotlib_args(parser, default_line_style='-', default_color=None):
    parser.add_argument('--no_fill', help='Do not fill the area under the line', action='store_true')
    parser.add_argument('--line_style', help='Choose a custom line style', default=default_line_style)
    parser.add_argument('--color', help='Choose a custom color', default=default_color)


# Get db paths for directories
def get_db_paths_from_dirs(db_dirs, file_end):
    db_paths = []
    for dir_name in db_dirs:
        for file in os.listdir(dir_name):
            if file.endswith(file_end):
                db_paths.append(os.path.join(dir_name, file))

    return db_paths


# Check db files exist
def check_db_files_exist(db_paths):
    for db_path in db_paths:
        if not os.path.isfile(db_path):
            raise FileNotFoundError(f'DB file {db_path} does not exist')


# Choose the right SQL query to execute
# "where data" should be a string with the SQL data of conditions
def choose_sql_query(start, end, fields, table, where_data=None):
    sql_base = f'SELECT {",".join(fields)} FROM {table}'
    order_by = f'ORDER BY {fields[0]}'
    where_data = 'true' if not where_data else f' {where_data}'
    if start and end:
        return f'{sql_base} WHERE {where_data} AND {fields[0]} BETWEEN ? AND ? {order_by}', (start, end)
    elif start:
        return f'{sql_base} WHERE {where_data} AND {fields[0]} >= ? {order_by}', (start,)
    elif end:
        return f'{sql_base} WHERE {where_data} AND {fields[0]} <= ? {order_by}', (end,)
    else:
        return f'{sql_base} WHERE {where_data} {order_by}', ()


# Get data from a db
def get_data_from_db(db_path, start, end, fields, table, where_data=None):
    with sqlite3.connect(db_path) as conn:
        sql_query, sql_args = choose_sql_query(start, end, fields, table, where_data)
        return conn.execute(sql_query, sql_args).fetchall()


# Get data frame from data
def get_data_frame_from_data(data, fields, grp_freq='1s'):
    df = pd.DataFrame(data, columns=fields)
    df[fields[0]] = pd.to_datetime(df[fields[0]])
    df = df.groupby(pd.Grouper(key=fields[0], freq=grp_freq))

    return df
