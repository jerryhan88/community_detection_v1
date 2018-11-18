import os.path as opath
import sys, os
import csv
import numpy as np
import configparser
from functools import reduce
from datetime import datetime
from bisect import bisect
from collections import deque
#
from __util_logger import get_logger
from __util_geoFunctions import get_sgGrid
from __path_organizer import TAXI_RAW_DATA_HOME, dp_dpath
from a1_singleShift import ss_dpath 


logger = get_logger()
dtpp_dpath = opath.join(dp_dpath, '2_dwellTimeNpriorPresence')
if not opath.exists(dtpp_dpath):
    os.mkdir(dtpp_dpath)

config = configparser.ConfigParser()
config.read('config.properties')
HISTORY_LOOKUP_LENGTH = eval(config['DEFAULT']['HISTORY_LOOKUP_LENGTH'])

MON, TUE, WED, THR, FRI, SAT, SUN = range(7)
AM10, PM8 = 10, 20
# Singapore Public Holidays
HOLIDAYS2009 = [
            (2009, 1, 1),    # New Year's Day, Thursday, 1 January 2009
            (2009, 1, 26),    # Chinese New Year, Monday, 26 January 2009
            (2009, 1, 27),    # Chinese New Year, Tuesday, 27 January 2009
            (2009, 4, 10),    # Good Friday, Friday, 10 April 2009
            (2009, 5, 1),     # Labour Day, Friday, 1 May 2009
            (2009, 5, 9),     # Vesak Day, Saturday, 9 May 2009
            (2009, 8, 10),    # National Day, Sunday*, 9 August 2009
            (2009, 9, 21),    # Hari Raya Puasa, Sunday*, 20 September 2009
            (2009, 11, 16),   # Deepavali, Sunday*, 15 November 2009
            (2009, 11, 27),   # Hari Raya Haji, Friday, 27 November 2009
            (2009, 12, 25),   # Christmas Day, Friday, 25 December 2009
]
FREE = 0


def process_month(yymm):
    from traceback import format_exc
    #
    try:
        logger.info('handle the file; %s' % yymm)
        yymm_dt = datetime.strptime(yymm, '%y%m')
        yy, mm = yymm_dt.strftime('%y'), yymm_dt.strftime('%m')
        yyyy = yymm_dt.strftime('%Y')

        normal_fpath = reduce(opath.join, [TAXI_RAW_DATA_HOME,
                                           yyyy, mm, 'trips', 'trips-%s-normal.csv' % yymm])
        ext_fpath = reduce(opath.join, [TAXI_RAW_DATA_HOME,
                                        yyyy, mm, 'trips', 'trips-%s-normal-ext.csv' % yymm])

        log_fpath = reduce(opath.join, [TAXI_RAW_DATA_HOME,
                                        yyyy, mm, 'logs', 'logs-%s-normal.csv' % yymm])
        if not opath.exists(normal_fpath):
            logger.info('The file X exists; %s' % yymm)
            return None
        ss_drivers = set(np.load(opath.join(ss_dpath, 'singleShift-%s.npy' % yymm), 'r+'))
        lats, lngs = map(list, get_sgGrid())
        ofpath, handling_dayT = None, 0
        handling_dayL = 0
        drivers, zones = None, None
        with open(normal_fpath) as tripFileN:
            tripReaderN = csv.DictReader(tripFileN)
            with open(ext_fpath) as tripFileE:
                tripReaderE = csv.DictReader(tripFileE)
                with open(log_fpath) as logFile:
                    logReader = csv.DictReader(logFile)
                    for rowN in tripReaderN:
                        rowE = next(tripReaderE)
                        #
                        didT = int(rowE['driver-id'])
                        if didT not in ss_drivers:
                            continue
                        #
                        tripTime = eval(rowN['start-time'])
                        cur_dtT = datetime.fromtimestamp(tripTime)
                        if cur_dtT.weekday() in [FRI, SAT, SUN]:
                            continue
                        if (cur_dtT.year, cur_dtT.month, cur_dtT.day) in HOLIDAYS2009:
                            continue
                        if cur_dtT.hour < AM10:
                            continue
                        if PM8 <= cur_dtT.hour:
                            continue
                        #
                        if handling_dayT != cur_dtT.day:
                            handling_dayT = cur_dtT.day
                            logger.info('Processing %s %dth day' % (yymm, cur_dtT.day))
                            ofpath = opath.join(dtpp_dpath,
                                                'dwellTimeNpriorPresence-%d%02d%02d.csv' % (cur_dtT.year, cur_dtT.month, cur_dtT.day))
                            with open(ofpath, 'wt') as w_csvfile:
                                writer = csv.writer(w_csvfile, lineterminator='\n')
                                writer.writerow(['year', 'month', 'day', 'hour',
                                                 'time', 'lon', 'lat',
                                                 'distance', 'duration', 'fare',
                                                 'did',
                                                 'zi', 'zj', 'dwellTime', 'priorPresence'])
                            drivers, zones = {}, {}
                            for zi in range(len(lngs)):
                                for zj in range(len(lats)):
                                    zones[zi, zj] = zone(zi, zj)
                        #
                        while True:
                            rowL = next(logReader)
                            logTime = eval(rowL['time'])
                            cur_dtL = datetime.fromtimestamp(logTime)
                            if handling_dayL != cur_dtL.day:
                                handling_dayL = cur_dtL.day
                                logger.info('\t Log processing %s %dth day' % (yymm, handling_dayL))
                            if not drivers and handling_dayL != handling_dayT:
                                continue
                            didL = int(rowL['driver-id'])
                            if didL not in ss_drivers:
                                continue
                            if cur_dtL.hour < AM10:
                                continue
                            if PM8 <= cur_dtL.hour:
                                continue
                            lng, lat = eval(rowL['longitude']), eval(rowL['latitude'])
                            zi, zj = bisect(lngs, lng) - 1, bisect(lats, lat) - 1
                            if zi < 0 or zj < 0:
                                continue
                            state = eval(rowL['state'])
                            if didL not in drivers:
                                drivers[didL] = driver(didL, logTime, zi, zj, state)
                            else:
                                drivers[didL].update(logTime, zi, zj, state)
                            if tripTime <= logTime:
                                break
                        #
                        lng, lat = eval(rowN['start-long']), eval(rowN['start-lat'])
                        zi, zj = bisect(lngs, lng) - 1, bisect(lats, lat) - 1
                        if zi < 0 or zj < 0:
                            continue
                        if didT not in drivers:
                            continue
                        dwellTime = tripTime - drivers[didT].firstFreeStateTime \
                                    if drivers[didT].firstFreeStateTime != -1 else 0
                        prevDriverLonLat = drivers[didT].get_prevDriverLonLat(tripTime, lng, lat, zones[(zi, zj)])
                        #
                        with open(ofpath, 'a') as w_csvfile:
                            writer = csv.writer(w_csvfile, lineterminator='\n')
                            new_row = [cur_dtT.year, cur_dtT.month, cur_dtT.day, cur_dtT.hour,
                                       tripTime, lng, lat,
                                       rowN['distance'], rowN['duration'], rowN['fare'],
                                       didT,
                                       zi, zj, dwellTime]
                            writer.writerow(new_row + ['|'.join(prevDriverLonLat)])
    except Exception as _:
        import sys
        with open('%s_%s.txt' % (sys.argv[0], yymm), 'w') as f:
            f.write(format_exc())
        raise


class driver(object):
    def __init__(self, did, cl_time, cl_zi, cl_zj, cl_state):
        self.did = did
        self.pl_time, self.pl_zi, self.pl_zj, self.pl_state = cl_time, cl_zi, cl_zj, cl_state
        if self.pl_state == FREE:
            self.firstFreeStateTime = self.pl_time
        else:
            self.firstFreeStateTime = -1
        #
        self.zoneEnteredTime = {}
        self.zoneEnteredTime[self.pl_zi, self.pl_zj] = self.pl_time

    def update(self, cl_time, cl_zi, cl_zj, cl_state):
        if (self.pl_zi, self.pl_zj) != (cl_zi, cl_zj):
            self.zoneEnteredTime[cl_zi, cl_zj] = cl_time
        #
        if cl_state != FREE:
            self.firstFreeStateTime = -1
        else:
            if (self.pl_zi, self.pl_zj) != (cl_zi, cl_zj):
                self.firstFreeStateTime = cl_time
            else:
                if self.pl_state != FREE:
                    self.firstFreeStateTime = cl_time
        self.pl_time, self.pl_zi, self.pl_zj, self.pl_state = cl_time, cl_zi, cl_zj, cl_state

    def get_prevDriverLonLat(self, pickUpTime, lon, lat, z):
        z.update_logQ(pickUpTime)
        if (z.zi, z.zj) not in self.zoneEnteredTime:
            did1_zEnteredTime = pickUpTime
        else:
            did1_zEnteredTime = self.zoneEnteredTime[z.zi, z.zj]
        prevDriverLonLat = {}
        for _, d, lon, lat in z.logQ:
            if d.did == self.did:
                continue
            if (z.zi, z.zj) not in d.zoneEnteredTime:
                did0_zEnteredTime = d.zoneEnteredTime[z.zi, z.zj]
                if did0_zEnteredTime < did1_zEnteredTime:
                    prevDriverLonLat[d.did] = '%d&%f&%f' % (d.did, lon, lat)
            else:
                prevDriverLonLat[d.did] = '%d&%f&%f' % (d.did, lon, lat)
        z.add_driver_in_logQ(pickUpTime, self, lon, lat)
        return prevDriverLonLat.values()


class zone(object):
    def __init__(self, zi, zj):
        self.zi, self.zj = zi, zj
        self.logQ = deque()

    def add_driver_in_logQ(self, pickUpTime, d, lon, lat):
        self.logQ += [[pickUpTime, d, lon, lat]]

    def update_logQ(self, pickUpTime):
        while self.logQ and self.logQ[0][0] < pickUpTime - HISTORY_LOOKUP_LENGTH:
            self.logQ.popleft()


if __name__ == '__main__':
    if len(sys.argv) <= 1:
        process_month('0901')
    else:
        assert len(sys.argv)
        yymm = sys.argv[1]
        process_month(yymm)