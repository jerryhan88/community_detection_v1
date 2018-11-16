import sys, logging


def get_logger():
    py_fname = sys.argv[0][:-len('.py')]
    if '/' in py_fname:
        logger_name = '___log_%s' % py_fname.split('/')[-1]
    else:
        logger_name = '___log_%s' % py_fname
    logger = logging.getLogger('%s' % (logger_name))
    logger.setLevel(logging.DEBUG)
    fh = logging.FileHandler('%s.log' % (logger_name))
    fh.setLevel(logging.DEBUG)
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    fh.setFormatter(formatter)
    logger.addHandler(fh)
    return logger
