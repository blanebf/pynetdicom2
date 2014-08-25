# Copyright (c) 2014 Pavel 'Blane' Tuchin
# Copyright (c) 2012 Patrice Munger
# This file is part of pynetdicom, released under a modified MIT license.
#    See the file license.txt included with this distribution, also
#    available at http://pynetdicom.googlecode.com
#

import time

import netdicom2.dimsemessages as dimsemessages


class DIMSEServiceProvider(object):
    def __init__(self, asce):
        self.asce = asce
        self.message = None

    def send(self, dimse_msg, id_, max_pdu_length):
        # take a DIMSE primitive, convert it to one or more DUL primitive
        # and send it
        dimse_msg.set_length()
        p_data_list = dimse_msg.encode(id_, max_pdu_length)
        for p_data in p_data_list:
            self.asce.send(p_data)

    def receive(self, wait=False, timeout=None):
        if self.message is None:
            self.message = dimsemessages.DIMSEMessage()
        if wait:
            # loop until complete DIMSE message is received
            while 1:
                time.sleep(0.001)
                if self.message.decode(self.asce.get_dul_message(timeout)):
                    tmp, self.message = self.message, None
                    return tmp, tmp.id_
        else:
            if self.message.decode(self.asce.get_dul_message(timeout)):
                tmp, self.message = self.message, None
                return tmp, tmp.id_
            else:
                return None, None
