# Copyright (c) 2014 Pavel 'Blane' Tuchin
# Copyright (c) 2012 Patrice Munger
# This file is part of pynetdicom, released under a modified MIT license.
#    See the file license.txt included with this distribution, also
#    available at http://pynetdicom.googlecode.com
#

import time

import netdicom2.dimsemessages as dimsemessages
import netdicom2.pdu as pdu


class DIMSEServiceProvider(object):

    def __init__(self, dul):
        self.dul = dul
        self.message = None

    def send(self, primitive, id_, max_pdu_length):
        # take a DIMSE primitive, convert it to one or more DUL primitive
        # and send it
        dimse_msg = primitive.to_message()
        p_data_list = dimse_msg.encode(id_, max_pdu_length)
        for p_data in p_data_list:
            self.dul.send(p_data)

    def receive(self, wait=False, timeout=None):
        if self.message is None:
            self.message = dimsemessages.DIMSEMessage()
        if wait:
            # loop until complete DIMSE message is received
            while 1:
                time.sleep(0.001)
                nxt = self.dul.peek()
                if nxt is None:
                    continue
                if nxt.__class__ is not pdu.PDataTfPDU:
                    return None, None
                if self.message.decode(self.dul.receive(wait, timeout)):
                    tmp, self.message = self.message, None
                    return tmp.to_params(), tmp.id_
        else:
            cls = self.dul.peek().__class__
            if cls not in (type(None), pdu.PDataTfPDU):
                return None, None
            if self.message.decode(self.dul.receive(wait, timeout)):
                tmp, self.message = self.message, None
                return tmp.to_params(), tmp.id_
            else:
                return None, None
