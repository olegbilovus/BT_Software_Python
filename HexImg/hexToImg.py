import os
import queue
import sys
import threading
import time

_path_parent = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(_path_parent)

from PIL import Image, ImageDraw, ImageFont
import argparse
from Utility import sharedUtils
from colors import XTERM_TO_HEX

config_path = os.path.join(_path_parent, 'config.ini')
file_end, img_fmt = (sharedUtils.get_single_value_from_config(config_path, 'HEXIMG', 'file_end'),
                     sharedUtils.get_single_value_from_config(config_path, 'HEXIMG', 'img_fmt'))

parser = argparse.ArgumentParser('Hex files to images')
file_grp = parser.add_mutually_exclusive_group(required=True)
file_grp.add_argument('--file', nargs='+', default=[], help='File containing Hex Stream')
file_grp.add_argument('--file_dir', nargs='+', default=[],
                      help=f'Paths to directory where to search for files. File\'s name have to end with "{file_end}"')
parser.add_argument('--threads', help='Number of threads to use. Each thread process a text file.', type=int, default=3)
parser.add_argument('--save', help='Save the images to files instead of displaying them.', action='store_true')
parser.add_argument('--text', help='Write the hex value on each block.', action='store_true')
parser.add_argument('--text_size', help='The text size', type=int, default=30)
parser.add_argument('--text_font', help='The font name', type=str, default='arial.ttf')
parser.add_argument('--highlight',
                    help='Highlight a pattern in the image. I will be highlighted by a border on the block', type=str)
parser.add_argument('--highlight_width', help='The highlight line width', type=int, default=15)
parser.add_argument('--width', help='The image width as number of blocks for each row', type=int, default=16)
parser.add_argument('--block_width', help='The block width as number of pixels', type=int, default=128)
parser.add_argument('--block_height', help='The block height as number of pixels', type=int, default=128)

args = parser.parse_args()
WIDTH_IMG = args.block_width * args.width
TEXT_POS = (args.block_width // 2, args.block_height // 2)
if not args.text_font.endswith('.ttf'):
    args.text_font += '.ttf'
text_font = ImageFont.truetype(args.text_font, args.text_size)
BLOCK_SIZE = (args.block_width, args.block_height)

if args.file_dir:
    args.file = sharedUtils.get_db_paths_from_dirs(args.file_dir, file_end)
else:
    sharedUtils.check_db_files_exist(args.file)

datasets = []

for file_path in args.file:
    with open(file_path) as f:
        hex_stream = f.read()
        len_f = len(hex_stream)

        data = []
        for i in range(0, len_f, 2):
            if (i / 2) % args.width == 0:
                data.append([])
            data[-1].append(hex_stream[i:i + 2])

        datasets.append({
            'label': sharedUtils.get_file_name_from_path(file_path).split('.')[0],
            'data': data,
            'len': len_f,
            'num_blocks_vert': len(data)
        })


# https://stackoverflow.com/questions/38478409/finding-out-complementary-opposite-color-of-a-given-color
def complementary_color(my_hex):
    if my_hex[0] == '#':
        my_hex = my_hex[1:]
    rgb = (my_hex[0:2], my_hex[2:4], my_hex[4:6])
    comp = ['%02X' % (255 - int(a, 16)) for a in rgb]
    return '#' + ''.join(comp)


def create_image(dataset):
    img = Image.new('RGB', (WIDTH_IMG, args.block_height * dataset['num_blocks_vert']), 'black')
    for r, data_r in enumerate(dataset['data']):
        for c, data_c in enumerate(dataset['data'][r]):
            hex_val = dataset['data'][r][c]
            color = XTERM_TO_HEX[int(hex_val, 16)]
            block = Image.new('RGB', BLOCK_SIZE, color)
            if args.text or args.highlight:
                dc = ImageDraw.Draw(block)
                comp_color = complementary_color(color)
                if args.text:
                    _, _, w, h = dc.textbbox((0, 0), hex_val, font=text_font)
                    dc.text(((args.block_width - w) / 2, (args.block_height - h) / 2), hex_val, font=text_font,
                            fill=comp_color)
                if args.highlight == hex_val:
                    dc.rectangle([(0, 0), BLOCK_SIZE], outline=comp_color, width=args.highlight_width)
            img.paste(block, (c * args.block_height, r * args.block_width))

    return img


def worker(jobs):
    while jobs.qsize() > 0:
        dataset = jobs.get()
        img = create_image(dataset)
        title = f"{dataset['label']}.{img_fmt}"
        if args.save:
            img.save(title)
        else:
            img.show(title)

        jobs.task_done()


img_jobs = queue.Queue()
for ds in datasets:
    img_jobs.put(ds)

threads = []
for _ in range(args.threads):
    p_t = threading.Thread(target=worker, args=(img_jobs,), daemon=True)
    p_t.start()
    threads.append(p_t)
    n_t = threading.Thread(target=worker, args=(img_jobs,), daemon=True)
    n_t.start()
    threads.append(n_t)

done = False
while not done:
    for t in threads:
        if t.is_alive():
            time.sleep(1)
            break
    else:
        done = img_jobs.empty()
