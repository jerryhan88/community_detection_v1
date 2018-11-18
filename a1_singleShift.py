import os.path as opath
import sys, os
from functools import reduce
from datetime import datetime
import numpy as np
import csv
#
from __util_logger import get_logger
from __path_organizer import TAXI_RAW_DATA_HOME, dp_dpath

logger = get_logger()
ss_dpath = opath.join(dp_dpath, '1_singleShift')
if not opath.exists(ss_dpath):
    os.mkdir(ss_dpath)


def process_month(yymm):
    logger.info('handle the file; %s' % yymm)
    yymm_dt = datetime.strptime(yymm, '%y%m')
    yy, mm = yymm_dt.strftime('%y'), yymm_dt.strftime('%m')
    yyyy = yymm_dt.strftime('%Y')
    normal_fpath = reduce(opath.join, [TAXI_RAW_DATA_HOME,
                                       yyyy, mm, 'trips', 'trips-%s-normal.csv' % yymm])
    ext_fpath = reduce(opath.join, [TAXI_RAW_DATA_HOME,
                                    yyyy, mm, 'trips', 'trips-%s-normal-ext.csv' % yymm])
    if not opath.exists(normal_fpath):
        logger.info('The file X exists; %s' % yymm)
        return None
    ofpath = opath.join(ss_dpath, 'singleShift-%s' % yymm)
    if opath.exists(ofpath + '.npy'):
        logger.info('Already handled; %s' % yymm)
        return None
    #
    vehicle_sharing = {}
    with open(normal_fpath, 'rt') as tripFileN:
        tripReaderN = csv.DictReader(tripFileN)
        with open(ext_fpath, 'rt') as tripHeaderE:
            tripReaderE = csv.DictReader(tripHeaderE)
            for rowN in tripReaderN:
                rowE = tripReaderE.next()
                did = int(rowE['driver-id'])
                if did == int('-1'):
                    continue
                vid = int(rowN['vehicle-id'])
                if not vehicle_sharing.has_key(vid):
                    vehicle_sharing[vid] = set()
                vehicle_sharing[vid].add(did)
    #
    ss_drivers = np.array([], dtype=int)
    for vid, drivers in vehicle_sharing.iteritems():
        if len(drivers) > 1:
            continue
        ss_drivers = np.append(ss_drivers, drivers.pop())
    np.save(ofpath, ss_drivers)
    logger.info('Filtering single-shift drivers; %s' % yymm)


if __name__ == '__main__':
    if len(sys.argv) <= 1:
        process_month('0901')
    else:
        assert len(sys.argv)
        yymm = sys.argv[1]
        process_month(yymm)
