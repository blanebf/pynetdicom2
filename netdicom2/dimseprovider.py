#
# Copyright (c) 2012 Patrice Munger
# This file is part of pynetdicom, released under a modified MIT license.
#    See the file license.txt included with this distribution, also
#    available at http://pynetdicom.googlecode.com
#

import time
import logging

import dimsemessages
from dimsemessages import DIMSEMessage
from dulparameters import PDataServiceParameters
from netdicom2 import dimseparameters


logger = logging.getLogger(__name__)


class DIMSEServiceProvider(object):

    def __init__(self, dul):
        self.dul = dul
        self.message = None

    def send(self, primitive, id_, max_pdu_length):
        # take a DIMSE primitive, convert it to one or more DUL primitive
        # and send it
        dimse_msg = None
        if isinstance(primitive, dimseparameters.CEchoServiceParameters):
            if primitive.message_id is not None:
                dimse_msg = dimsemessages.CEchoRQMessage()
            else:
                dimse_msg = dimsemessages.CEchoRSPMessage()
        if isinstance(primitive, dimseparameters.CStoreServiceParameters):
            if primitive.message_id is not None:
                dimse_msg = dimsemessages.CStoreRQMessage()
            else:
                dimse_msg = dimsemessages.CStoreRSPMessage()
        if isinstance(primitive, dimseparameters.CFindServiceParameters):
            if primitive.message_id is not None:
                dimse_msg = dimsemessages.CFindRQMessage()
            else:
                dimse_msg = dimsemessages.CFindRSPMessage()
        if isinstance(primitive, dimseparameters.CGetServiceParameters):
            if primitive.message_id is not None:
                dimse_msg = dimsemessages.CGetRQMessage()
            else:
                dimse_msg = dimsemessages.CGetRSPMessage()
        if isinstance(primitive, dimseparameters.CMoveServiceParameters):
            if primitive.message_id is not None:
                dimse_msg = dimsemessages.CMoveRQMessage()
            else:
                dimse_msg = dimsemessages.CMoveRSPMessage()

        if dimse_msg is None:
            # TODO: Replace exception type
            raise RuntimeError("Failed to get message")

        if logger.isEnabledFor(logging.DEBUG):
            logger.debug('DIMSE message of class %s' % dimse_msg.__class__)
        dimse_msg.from_params(primitive)
        if logger.isEnabledFor(logger.DEBUG):
            logger.debug('DIMSE message: %s', str(dimse_msg))
        pdatas = dimse_msg.encode(id_, max_pdu_length)
        if logger.isEnabledFor(logging.DEBUG):
            logger.debug('encoded %d fragments' % len(pdatas))
        for ii, pp in enumerate(pdatas):
            if logger.isEnabledFor(logging.DEBUG):
                logger.debug('sending pdata %d of %d' % (ii + 1, len(pdatas)))
            self.dul.send(pp)
        if logger.isEnabledFor(logging.DEBUG):
            logger.debug('DIMSE message sent')

    def receive(self, wait=False, timeout=None):
        if logger.isEnabledFor(logging.DEBUG):
            logger.debug("In DIMSEprovider.receive")
        if self.message is None:
            self.message = DIMSEMessage()
        if wait:
            # loop until complete DIMSE message is received
            if logger.isEnabledFor(logging.DEBUG):
                logger.debug('Entering loop for receiving DIMSE message')
            while 1:
                time.sleep(0.001)
                nxt = self.dul.peek()
                if nxt is None:
                    continue
                if nxt.__class__ is not PDataServiceParameters:
                    return None, None
                if self.message.decode(self.dul.receive(wait, timeout)):
                    tmp, self.message = self.message, None
                    if logger.isEnabledFor(logging.DEBUG):
                        logger.debug('Decoded DIMSE message: %s', str(tmp))
                    return tmp.to_params(), tmp.id_
        else:
            cls = self.dul.peek().__class__
            if cls not in (type(None), PDataServiceParameters):
                if logger.isEnabledFor(logging.DEBUG):
                    logger.debug('Waiting for P-DATA but received %s', cls)
                return None, None
            if self.message.decode(self.dul.receive(wait, timeout)):
                tmp, self.message = self.message, None
                if logger.isEnabledFor(logging.DEBUG):
                    logger.debug('received DIMSE message: %s', tmp)
                return tmp.to_params(), tmp.id_
            else:
                return None, None
