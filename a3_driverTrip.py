import os.path as opath
import sys, os
import threading
import time
import csv
import configparser
from traceback import format_exc
#
from __util_logger import get_logger
from __path_organizer import dp_dpath
from a2_dwellTimeNpriorPresence import dtpp_dpath


logger = get_logger()
dt_dpath = opath.join(dp_dpath, '3_driverTrip')
if not opath.exists(dt_dpath):
    os.mkdir(dt_dpath)

locks_driverFile = {}


config = configparser.ConfigParser()
config.read('config.properties')
NUM_WORKERS = int(config['DEFAULT']['NUM_WORKERS'])


def run():
    whole_files = [[] for _ in range(NUM_WORKERS)]
    for i, fn in enumerate(os.listdir(dtpp_dpath)):
        if not fn.endswith('.csv'):
            continue
        whole_files[i % NUM_WORKERS] += [fn]
    for i, file_subset in enumerate(whole_files):
        t = threading.Thread(name='w%d' % i, target = process_files, args=(file_subset,))
        t.start()
        logger.info('thread w%d started' % i)

    logger.info('End the whole processes')


def process_files(fileNames):
    def append_row(fpath, row):
        locks_driverFile[did] = True
        with open(fpath, 'a') as w_csvfile:
            writer = csv.writer(w_csvfile, lineterminator='\n')
            writer.writerow(row)
        locks_driverFile[did] = False
    #
    for fn in fileNames:
        try:
            _, yyyymmdd = fn[:-len('.csv')].split('-')
            logger.info('handling %s' % yyyymmdd)
            yyyy = yyyymmdd[:4]
            ifpath = opath.join(dtpp_dpath, fn)
            with open(ifpath, 'rb') as r_csvfile:
                reader = csv.reader(r_csvfile)
                header = reader.next()
                hid = {h: i for i, h in enumerate(header)}
                for row in reader:
                    did = int(row[hid['did']])
                    ofpath = opath.join(dt_dpath, 'driverTrip-%s-%d.csv' % (yyyy, did))
                    if did not in locks_driverFile:
                        locks_driverFile[did] = True
                        with open(ofpath, 'wt') as w_csvfile:
                            writer = csv.writer(w_csvfile, lineterminator='\n')
                            writer.writerow(header)
                        locks_driverFile[did] = False
                    if not locks_driverFile[did]:
                        append_row(ofpath, row)
                    else:
                        while True:
                            time.sleep(1)
                            if not locks_driverFile[did]:
                                append_row(ofpath, row)
                                break
        except Exception as _:
            with open('%s_%s.txt' % (sys.argv[0], yyyymmdd), 'w') as f:
                f.write(format_exc())
            raise




if __name__ == '__main__':
    run()