# Copyright (c) 2014 Pavel 'Blane' Tuchin
# Copyright (c) 2012 Patrice Munger
# This file is part of pynetdicom, released under a modified MIT license.
#    See the file license.txt included with this distribution, also
#    available at http://pynetdicom.googlecode.com
#


# This module provides association services
import logging

from dicom.UID import UID

import netdicom2.pdu as pdu
import netdicom2.userdataitems as userdataitems
import netdicom2.exceptions as exceptions


logger = logging.getLogger(__name__)


class ACSEServiceProvider(object):
    def __init__(self, dul):
        self.dul = dul
        self.application_context_name = '1.2.840.10008.3.1.1.1'
        self.local_ae = None
        self.remote_ae = None
        self.max_pdu_length = 16000
        self.accepted_presentation_contexts = []

    @staticmethod
    def build_pres_context_def_list(context_def_list):
        for context_def in context_def_list:
            context_id = context_def[0]
            abs_sub_item = pdu.AbstractSyntaxSubItem(context_def[1])
            ts_sub_items = [pdu.TransferSyntaxSubItem(i)
                            for i in context_def[2]]
            yield pdu.PresentationContextItemRQ(context_id, abs_sub_item,
                                                ts_sub_items)

    def request(self, local_ae, remote_ae, mp, pcdl, users_pdu=None,
                timeout=30):
        """Requests an association with a remote AE and waits for association
        response."""
        self.local_ae = local_ae
        self.remote_ae = remote_ae
        self.max_pdu_length = mp

        max_pdu_length_par = userdataitems.MaximumLengthSubItem(mp)
        user_information = [max_pdu_length_par] + users_pdu \
            if users_pdu else [max_pdu_length_par]
        username = remote_ae.get('username')
        password = remote_ae.get('password')
        if username and password:
            user_information.append(
                userdataitems.UserIdentityNegotiationSubItem(username,
                                                             password))
        elif username:
            user_information.append(
                userdataitems.UserIdentityNegotiationSubItem(
                    username, user_identity_type=1))

        variable_items = [
            pdu.ApplicationContextItem(self.application_context_name)]
        variable_items.extend(self.build_pres_context_def_list(pcdl))
        variable_items.append(pdu.UserInformationItem(user_information))
        assoc_rq = pdu.AAssociateRqPDU(
            called_ae_title=self.local_ae['aet'],
            calling_ae_title=self.remote_ae['aet'],
            variable_items=variable_items
        )
        # FIXME pass parameter properly
        assoc_rq.called_presentation_address = (self.remote_ae['address'],
                                                self.remote_ae['port'])
        self.dul.send(assoc_rq)
        response = self.dul.receive(True, timeout)
        if not response:
            return False
        if response.pdu_type == pdu.AAssociateRjPDU.pdu_type:
            raise exceptions.AssociationRejectedError(
                response.result, response.source, response.reason_diag)
        # Get maximum pdu length from answer
        user_data = response.variable_items[-1].user_data
        try:
            self.max_pdu_length = user_data[0].maximum_length_received
        except IndexError:
            self.max_pdu_length = 16000

        # Get accepted presentation contexts
        self.accepted_presentation_contexts = []
        for context in response.variable_items[1:-1]:
            if context.result_reason == 0:
                uid = [x[1] for x in pcdl if x[0] == context.context_id][0]
                self.accepted_presentation_contexts.append(
                    (context.context_id, uid, UID(context.ts_sub_item.name)))
        return response

    def accept(self, assoc_req, acceptable_pres_contexts=None):
        """Waits for an association request from a remote AE. Upon reception
        of the request sends association response based on
        acceptable_presentation_contexts"""
        user_items = assoc_req.variable_items[-1]
        self.max_pdu_length = user_items.user_data[0].maximum_length_received

        # analyse proposed presentation contexts
        rsp = [assoc_req.variable_items[0]]
        self.accepted_presentation_contexts = []
        acceptable_sop = [x[0] for x in acceptable_pres_contexts]
        for item in assoc_req.variable_items[1:-1]:
            context_id = item.context_id
            proposed_sop = item.abs_sub_item.name
            proposed_ts = item.ts_sub_items
            if proposed_sop not in acceptable_sop:
                # Refuse sop class because of SOP class not supported
                rsp.append(pdu.PresentationContextItemAC(
                    context_id, 1, pdu.TransferSyntaxSubItem('')))
                continue

            acceptable_ts = [x[1] for x in acceptable_pres_contexts
                             if x[0] == proposed_sop][0]
            for ts in proposed_ts:
                if ts.name in acceptable_ts:
                    # accept sop class and ts
                    rsp.append(pdu.PresentationContextItemAC(context_id, 0, ts))
                    self.accepted_presentation_contexts.append(
                        (item.context_id, proposed_sop, UID(ts.name)))
                    break
            else:  # Refuse sop class because of TS not supported
                rsp.append(pdu.PresentationContextItemAC(
                    context_id, 1, pdu.TransferSyntaxSubItem('')))
        rsp.append(user_items)
        res = pdu.AAssociateAcPDU(
            called_ae_title=assoc_req.called_ae_title,
            calling_ae_title=assoc_req.calling_ae_title,
            variable_items=rsp
        )
        self.dul.send(res)



    def check_release(self):
        """Checks for release request from the remote AE. Upon reception of
        the request a confirmation is sent"""
        rel = self.dul.peek()
        if isinstance(rel, pdu.AReleaseRqPDU):
            self.dul.receive(wait=False)
            self.dul.send(pdu.AReleaseRpPDU())
            return True
        else:
            return False

    def check_abort(self):
        """Checks for abort indication from the remote AE. """
        rel = self.dul.peek()
        if isinstance(rel, pdu.AAbortPDU):
            self.dul.receive(wait=False)
            return True
        else:
            return False

    def status(self):
        return self.dul.state_machine.current_state()

    def kill(self):
        self.dul.kill()
