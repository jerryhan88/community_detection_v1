import os.path as opath
import platform
import os
from functools import reduce

TAXI_RAW_DATA_HOME = reduce(opath.join, [opath.expanduser("~"), '..', 'taxi'])

if platform.system().startswith('Darwin'):
    DATA_HOME = reduce(opath.join, [opath.expanduser("~"), 'Dropbox' '_researchData', 'community_detection'])
else:
    DATA_HOME = reduce(opath.join, [opath.expanduser("~"), 'research', '_data', 'community_detection'])

dp_dpath = opath.join(DATA_HOME, 'a_DataProcessing')

dir_paths = [DATA_HOME,
                dp_dpath
             ]
for dpath in dir_paths:
    if not opath.exists(dpath):
        os.mkdir(dpath)
