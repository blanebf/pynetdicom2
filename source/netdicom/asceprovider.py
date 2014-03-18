#
# Copyright (c) 2012 Patrice Munger
# This file is part of pynetdicom, released under a modified MIT license.
#    See the file license.txt included with this distribution, also
#    available at http://pynetdicom.googlecode.com
#


# This module provides association services
import time
import logging

from dicom.UID import UID

import dulparameters
from pdu import MaximumLengthParameters
import dulprovider

logger = logging.getLogger(__name__)


class AssociationRefused(Exception):

    def __init__(self, data=None):
        self.data = data


class NoAcceptablePresentationContext(Exception):

    def __init__(self, data=None):
        self.data = data


class ACSEServiceProvider(object):

    def __init__(self, dul):
        self.dul = dul
        self.application_context_name = '1.2.840.10008.3.1.1.1'
        self.local_ae = None
        self.remote_ae = None
        self.max_pdu_length = 16000
        self.accepted_presentation_contexts = []

    def request(self, local_ae, remote_ae, mp, pcdl, users_pdu=None, timeout=30):
        """Requests an association with a remote AE and waits for association
        response."""
        self.local_ae = local_ae
        self.remote_ae = remote_ae
        self.max_pdu_length = mp

        # build association service parameters object
        assoc_rq = dulparameters.AAssociateServiceParameters()
        assoc_rq.application_context_name = self.application_context_name
        assoc_rq.calling_ae_title = self.local_ae['AET']
        assoc_rq.called_ae_title = self.remote_ae['AET']
        max_pdu_length_par = MaximumLengthParameters()
        max_pdu_length_par.maximum_length_received = mp
        if users_pdu:
            assoc_rq.user_information = [max_pdu_length_par] + users_pdu
        else:
            assoc_rq.user_information = [max_pdu_length_par]
        assoc_rq.calling_presentation_address = (self.local_ae['Address'], self.local_ae['Port'])
        assoc_rq.called_presentation_address = (self.remote_ae['Address'], self.remote_ae['Port'])
        assoc_rq.presentation_context_definition_list = pcdl
        logger.debug(pcdl)
        # send A-Associate request
        logger.debug("Sending Association Request")
        self.dul.send(assoc_rq)

        # get answer
        logger.debug("Waiting for Association Response")

        assoc_rsp = self.dul.receive(True, timeout)
        if not assoc_rsp:
            return False
        logger.debug(assoc_rsp)

        try:
            if assoc_rsp.result != 'Accepted':
                return False
        except AttributeError:
            return False

        # Get maximum pdu length from answer
        try:
            self.max_pdu_length = assoc_rsp.user_information[0].maximum_length_received
        except IndexError:
            self.max_pdu_length = 16000

        # Get accepted presentation contexts
        self.accepted_presentation_contexts = []
        for cc in assoc_rsp.presentation_context_definition_result_list:
            if cc[1] == 0:
                uid = [x[1] for x in pcdl if x[0] == cc[0]][0]
                self.accepted_presentation_contexts.append((cc[0], uid, UID(cc[2])))
        return True

    def accept(self, client_socket=None, acceptable_presentation_contexts=None, wait=True):
        """Waits for an association request from a remote AE. Upon reception
        of the request sends association response based on
        acceptable_presentation_contexts"""
        if self.dul is None:
            self.dul = dulprovider.DULServiceProvider(socket_=client_socket)
        assoc = self.dul.receive(wait=True)
        if not assoc:
            return None

        self.max_pdu_length = assoc.user_information[0].maximum_length_received

        # analyse proposed presentation contexts
        rsp = []
        self.accepted_presentation_contexts = []
        acceptable_sop = [x[0] for x in acceptable_presentation_contexts]
        for ii in assoc.presentation_context_definition_list:
            proposed_sop = ii[1]
            proposed_ts = ii[2]
            if proposed_sop in acceptable_sop:
                acceptable_ts = [x[1] for x in acceptable_presentation_contexts if x[0] == proposed_sop][0]
                for ts in proposed_ts:
                    if ts in acceptable_ts:
                        # accept sop class and ts
                        rsp.append((ii[0], 0, ts))
                        self.accepted_presentation_contexts.append((ii[0], proposed_sop, UID(ts)))
                        break
                else:  # Refuse sop class because of TS not supported
                    rsp.append((ii[0], 1, ''))
            else:  # Refuse sop class because of SOP class not supported
                rsp.append((ii[0], 1, ''))

        # Send response
        res = assoc
        res.presentation_context_definition_list = []
        res.presentation_context_definition_result_list = rsp
        res.result = 0
        res.user_information = assoc.user_information
        self.dul.send(res)
        return True

    def release(self, reason):
        """Requests the release of the associations and waits for
        confirmation"""
        rel = dulparameters.AReleaseServiceParameters()
        rel.reason = reason
        self.dul.send(rel)
        rsp = self.dul.receive(wait=True)
        return rsp
        # self.dul.kill()

    def abort(self):
        """Signifies the abortion of the association."""
        self.dul.send(dulparameters.AAbortServiceParameters())
        time.sleep(0.5)
        # self.dul.kill()

    def check_release(self):
        """Checks for release request from the remote AE. Upon reception of
        the request a confirmation is sent"""
        rel = self.dul.peek()
        if isinstance(rel, dulparameters.AReleaseServiceParameters):
            self.dul.receive(wait=False)
            release_rsp = dulparameters.AReleaseServiceParameters()
            release_rsp.result = 0
            self.dul.send(release_rsp)
            return True
        else:
            return False

    def check_abort(self):
        """Checks for abort indication from the remote AE. """
        rel = self.dul.peek()
        if isinstance(rel, (dulparameters.AAbortServiceParameters, dulparameters.APAbortServiceParameters)):
            self.dul.receive(wait=False)
            return True
        else:
            return False

    def status(self):
        return self.dul.state_machine.current_state()

    def kill(self):
        self.dul.kill()
