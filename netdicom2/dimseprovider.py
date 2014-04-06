# Copyright (c) 2014 Pavel 'Blane' Tuchin
# Copyright (c) 2012 Patrice Munger
# This file is part of pynetdicom, released under a modified MIT license.
#    See the file license.txt included with this distribution, also
#    available at http://pynetdicom.googlecode.com
#

import time
import logging

import netdicom2.dimsemessages as dimsemessages
import netdicom2.dulparameters as dulparameters


logger = logging.getLogger(__name__)


class DIMSEServiceProvider(object):

    def __init__(self, dul):
        self.dul = dul
        self.message = None

    def send(self, primitive, id_, max_pdu_length):
        # take a DIMSE primitive, convert it to one or more DUL primitive
        # and send it
        dimse_msg = primitive.to_message()
        p_data_list = dimse_msg.encode(id_, max_pdu_length)
        logger.debug('encoded %d fragments', len(p_data_list))
        for p_data in p_data_list:
            self.dul.send(p_data)
        logger.debug('DIMSE message sent')

    def receive(self, wait=False, timeout=None):
        logger.debug("In DIMSEprovider.receive")
        if self.message is None:
            self.message = dimsemessages.DIMSEMessage()
        if wait:
            # loop until complete DIMSE message is received
            logger.debug('Entering loop for receiving DIMSE message')
            while 1:
                time.sleep(0.001)
                nxt = self.dul.peek()
                if nxt is None:
                    continue
                if nxt.__class__ is not dulparameters.PDataServiceParameters:
                    return None, None
                if self.message.decode(self.dul.receive(wait, timeout)):
                    tmp, self.message = self.message, None
                    logger.debug('Decoded DIMSE message: %s', str(tmp))
                    return tmp.to_params(), tmp.id_
        else:
            cls = self.dul.peek().__class__
            if cls not in (type(None), dulparameters.PDataServiceParameters):
                logger.debug('Waiting for P-DATA but received %s', cls)
                return None, None
            if self.message.decode(self.dul.receive(wait, timeout)):
                tmp, self.message = self.message, None
                logger.debug('received DIMSE message: %s', tmp)
                return tmp.to_params(), tmp.id_
            else:
                return None, None
