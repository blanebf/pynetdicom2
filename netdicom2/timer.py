# Copyright (c) 2014 Pavel 'Blane' Tuchin
# Copyright (c) 2012 Patrice Munger
# This file is part of pynetdicom, released under a modified MIT license.
#    See the file license.txt included with this distribution, also
#    available at http://pynetdicom.googlecode.com


import time


class Timer(object):

    def __init__(self, max_seconds):
        self._max_seconds = max_seconds
        self._start_time = None

    def start(self):
        self._start_time = time.time()

    def stop(self):
        self._start_time = None

    def restart(self):
        self.stop()
        self.start()

    def check(self):
        if self._start_time and \
                (time.time() - self._start_time > self._max_seconds):
            return False
        else:
            return True
