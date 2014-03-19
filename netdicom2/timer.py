#
# Copyright (c) 2012 Patrice Munger
# This file is part of pynetdicom, released under a modified MIT license.
#    See the file license.txt included with this distribution, also
#    available at http://pynetdicom.googlecode.com
#

# Timer class
import time
import logging

logger = logging.getLogger(__name__)


class Timer(object):

    def __init__(self, max_seconds):
        self._max_seconds = max_seconds
        self._start_time = None

    def start(self):
        logger.debug("Timer started")
        self._start_time = time.time()

    def stop(self):
        logger.debug("Timer stopped")
        self._start_time = None

    def restart(self):
        self.stop()
        self.start()

    def check(self):
        if self._start_time and (time.time() - self._start_time > self._max_seconds):
            logger.warning("Timer expired")
            return False
        else:
            return True


if __name__ == '__main__':
    t = Timer(3)
    t.start()
    for ii in range(32):
        time.sleep(0.2)
        print t.check()
