# -*- coding: utf-8 -*-

import logging
import os
import sys
import io

def get_logger(name, logpath, level='INFO'):
    log = logging.getLogger(name)
    log.setLevel(level)
    log.handlers.clear()
    dirpath = os.path.join('.' + os.path.dirname(logpath))
    os.makedirs(dirpath, exist_ok=True)
    formatter = logging.Formatter('%(asctime)s %(levelname)-8s [%(filename)s:%(lineno)d] %(message)s')
    fileHandler = logging.FileHandler(logpath, 'w', 'utf-8')
    fileHandler.setFormatter(formatter)

    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

    stdErrHandler = logging.StreamHandler(sys.stderr)
    stdErrHandler.setFormatter(formatter)
    log.addHandler(fileHandler)
    log.addHandler(stdErrHandler)
    return log