# Copyright (c) 2014 Pavel 'Blane' Tuchin
# Copyright (c) 2012 Patrice Munger
# This file is part of pynetdicom, released under a modified MIT license.
#    See the file license.txt included with this distribution, also
#    available at http://pynetdicom.googlecode.com
#


# This module provides association services
import time
import SocketServer

from dicom.UID import UID

import netdicom2.exceptions as exceptions
import netdicom2.dulprovider as dulprovider
import netdicom2.dimsemessages as dimsemessages

import netdicom2.pdu as pdu

import netdicom2.sopclass as sopclass
import netdicom2.userdataitems as userdataitems


APPLICATION_CONTEXT_NAME = '1.2.840.10008.3.1.1.1'


def build_pres_context_def_list(context_def_list):
    for context_def in context_def_list:
        context_id = context_def[0]
        abs_sub_item = pdu.AbstractSyntaxSubItem(context_def[1])
        ts_sub_items = [pdu.TransferSyntaxSubItem(i)
                        for i in context_def[2]]
        yield pdu.PresentationContextItemRQ(context_id, abs_sub_item,
                                            ts_sub_items)


class Association(object):
    """Base association class.

    Class is not intended for direct usage and meant to be sub-classed.
    Class provides basic association interface: creation, release and abort.
    """

    def __init__(self, local_ae, dul_socket):
        """Initializes Association instance with local AE title and DUL service
        provider

        :param local_ae: local AE title parameters
        :param dul_socket: socket for DUL provider or None if it's not needed
        """
        self.dul = dulprovider.DULServiceProvider(dul_socket)
        self.ae = local_ae
        self.association_established = False

        self.max_pdu_length = 16000
        self.accepted_presentation_contexts = []

    def get_dul_message(self):
        dul_msg = self.dul.receive(self.ae.timeout)
        if dul_msg.pdu_type == pdu.PDataTfPDU.pdu_type\
                or dul_msg.pdu_type == pdu.AAssociateAcPDU.pdu_type:
            return dul_msg
        elif dul_msg.pdu_type == pdu.AReleaseRqPDU.pdu_type:
            raise exceptions.AssociationReleasedError()
        elif dul_msg.pdu_type == pdu.AAbortPDU.pdu_type:
            raise exceptions.AssociationAbortedError(dul_msg.source,
                                                     dul_msg.reason_diag)
        else:
            raise exceptions.NetDICOMError()

    def send(self, dimse_msg, pc_id):
        dimse_msg.set_length()
        p_data_list = dimse_msg.encode(pc_id, self.ae.max_pdu_length)
        for p_data in p_data_list:
            self.dul.send(p_data)

    def receive(self):
        message = dimsemessages.DIMSEMessage()
        # loop until complete DIMSE message is received
        while not message.decode(self.get_dul_message()):
            pass
        return message, message.pc_id

    def kill(self):
        """Stops internal DUL service provider.

        In most cases you won't need to use this method directly. Refer to
        release and abort instead.
        :rtype : None
        """
        for _ in xrange(1000):
            if self.dul.stop():
                continue
            time.sleep(0.001)
        self.dul.kill()

    def release(self):
        """Releases association.

        Requests the release of the associations and waits for
        confirmation

        :rtype : None
        """
        self.dul.send(pdu.AReleaseRqPDU())
        rsp = self.dul.receive(self.ae.timeout)
        self.kill()
        return rsp


class AssociationAcceptor(SocketServer.StreamRequestHandler, Association):
    """'Server-side' association implementation.

    Class is intended for handling incoming association requests.
    """

    def __init__(self, request, client_address, local_ae):
        """Initializes AssociationAcceptor instance with specified client socket

        :param local_ae: local AE title
        :param request: client socket
        """
        Association.__init__(self, local_ae, request)
        self.is_killed = False
        self.sop_classes_as_scp = []

        SocketServer.StreamRequestHandler.__init__(self,
                                                   request,
                                                   client_address,
                                                   local_ae)

    def kill(self):
        """Overrides base class kill method to set stop-flag for running thread

        :rtype : None
        """
        self.is_killed = True
        super(AssociationAcceptor, self).kill()

    def abort(self, reason):
        """Aborts association with specified reason

        :rtype : None
        :param reason: abort reason
        """
        self.dul.send(pdu.AAbortPDU(source=2, reason_diag=reason))
        self.kill()

    def reject(self, result, source, diag):
        """Rejects association with specified parameters

        :param result:
        :param source:
        :param diag:
        """
        self.dul.send(pdu.AAssociateRjPDU(result, source, diag))

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

    def handle(self):
        try:
            self._establish()
            self._loop()
        except exceptions.AssociationReleasedError:
            self.dul.send(pdu.AReleaseRpPDU())
        except exceptions.AssociationAbortedError:
            pass  # TODO: Log abort
        except exceptions.TimeoutError:
            pass  # TODO: Handle timeout error
        finally:
            self.kill()

    def _establish(self):
        try:
            assoc_req = self.dul.receive(self.ae.timeout)
            self.ae.on_association_request(assoc_req)
        except exceptions.AssociationRejectedError as e:
            self.reject(e.result, e.source, e.diagnostic)
            raise

        self.accept(assoc_req, self.ae.acceptable_presentation_contexts)

        # build list of SOPClasses supported
        self.sop_classes_as_scp = [(c[0], c[1], c[2]) for c in
                                   self.accepted_presentation_contexts]
        self.association_established = True

    def _loop(self):
        while not self.is_killed:
            time.sleep(0.001)
            dimse_msg, pcid = self.receive()
            if dimse_msg:  # dimse message received
                uid = dimse_msg.affected_sop_class_uid
                try:
                    pcid, sop_class, transfer_syntax = \
                        [x for x in self.sop_classes_as_scp if x[0] == pcid][0]
                except IndexError:
                    raise exceptions.ClassNotSupportedError(
                        'SOP Class {0} not supported as SCP'.format(uid))
                obj = sopclass.SOP_CLASSES[uid](self, sop_class, pcid,
                                                transfer_syntax)
                obj.scp(dimse_msg)  # run SCP


class AssociationRequester(Association):
    def __init__(self, local_ae, remote_ae=None):
        super(AssociationRequester, self).__init__(local_ae, None)
        self.ae = local_ae
        self.remote_ae = remote_ae
        self.sop_classes_as_scu = []
        self.association_refused = False
        self._request()

    def abort(self, reason=0):
        """Aborts association with specified reason

        :rtype : None
        :param reason: abort reason
        """
        self.dul.send(pdu.AAbortPDU(source=0, reason_diag=reason))
        self.kill()

    def request(self, local_ae, remote_ae, mp, pcdl, users_pdu=None):
        """Requests an association with a remote AE and waits for association
        response."""
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

        variable_items = [pdu.ApplicationContextItem(APPLICATION_CONTEXT_NAME)]
        variable_items.extend(build_pres_context_def_list(pcdl))
        variable_items.append(pdu.UserInformationItem(user_information))
        assoc_rq = pdu.AAssociateRqPDU(
            called_ae_title=remote_ae['aet'],
            calling_ae_title=local_ae['aet'],
            variable_items=variable_items
        )
        # FIXME pass parameter properly
        assoc_rq.called_presentation_address = (remote_ae['address'],
                                                remote_ae['port'])
        self.dul.send(assoc_rq)
        response = self.get_dul_message()
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

    def _request(self):
        ext = [userdataitems.ScpScuRoleSelectionSubItem(i[0], 0, 1)
               for i in self.ae.acceptable_presentation_contexts]
        response = self.request(
            self.ae.local_ae, self.remote_ae, self.ae.max_pdu_length,
            self.ae.context_def_list, users_pdu=ext
        )
        self.ae.on_association_response(response)
        self.sop_classes_as_scu = [(context[0], context[1], context[2])
                                   for context in
                                   self.accepted_presentation_contexts]
        self.association_established = True

    def scu(self, ds, msg_id):
        uid = ds.SOPClassUID
        try:
            pcid, _, transfer_syntax = \
                [x for x in self.sop_classes_as_scu if x[1] == uid][0]
        except IndexError:
            raise exceptions.ClassNotSupportedError(
                'SOP Class %s not supported as SCU')

        obj = sopclass.SOP_CLASSES[uid](self, uid, pcid, transfer_syntax)
        return obj.scu(ds, msg_id)

    def get_scu(self, sop_class):
        try:
            pcid, _, transfer_syntax = \
                [x for x in self.sop_classes_as_scu if x[1] == sop_class][0]
        except IndexError:
            raise exceptions.ClassNotSupportedError(
                'SOP Class %s not supported as SCU' % sop_class)
        obj = sopclass.SOP_CLASSES[sop_class](self, sop_class, pcid,
                                              transfer_syntax)
        return obj
