import os
import gc
import sys


__author__ = 'bchoi'


def disable_stdout_buffering():
    # Disable stdout buffering
    os.environ['PYTHONUNBUFFERED'] = '1'
    sys.stdout = os.fdopen(sys.stdout.fileno(), 'w', 0)
    gc.garbage.append(sys.stdout)
