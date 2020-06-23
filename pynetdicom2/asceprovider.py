# Copyright (c) 2014 Pavel 'Blane' Tuchin
# Copyright (c) 2012 Patrice Munger
# This file is part of pynetdicom, released under a modified MIT license.
#    See the file license.txt included with this distribution, also
#    available at http://pynetdicom.googlecode.com
#

from __future__ import absolute_import, unicode_literals

# This module provides association services
import collections
import functools
import time

import six
from six.moves import socketserver, range

from . import _dicom
from . import exceptions
from . import dulprovider
from . import dimsemessages
from . import dsutils

from . import pdu
from . import userdataitems

PContextDef = collections.namedtuple(
    'PContextDef',
    ['id', 'sop_class', 'supported_ts']
)


APPLICATION_CONTEXT_NAME = _dicom.UID('1.2.840.10008.3.1.1.1')


def build_pres_context_def_list(context_def_list):
    return (
        pdu.PresentationContextItemRQ(
            pc_id, pdu.AbstractSyntaxSubItem(ctx.sop_class),
            [pdu.TransferSyntaxSubItem(i) for i in ctx.supported_ts]
        )
        for pc_id, ctx in six.iteritems(context_def_list)
    )


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
        self.accepted_contexts = {}

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
        elif dul_msg.pdu_type == pdu.AAssociateRjPDU.pdu_type:
            raise exceptions.AssociationRejectedError(
                dul_msg.result, dul_msg.source, dul_msg.reason_diag)
        else:
            raise exceptions.NetDICOMError()

    def send(self, dimse_msg, pc_id):
        dimse_msg.set_length()
        for p_data in dimse_msg.encode(pc_id, self.max_pdu_length):
            self.dul.send(p_data)

    def receive(self):
        # TODO: Refactor this madness
        encoded_command_set = []
        encoded_data_set = []

        command_set_received = False
        data_set_received = False

        receiving = True
        dataset = None

        pc_id = None
        msg = None

        start = 0

        try:
            while receiving:
                p_data = self.get_dul_message()

                for value_item in p_data.data_value_items:
                    # must be able to read P-DATA with several PDVs
                    pc_id = value_item.context_id
                    marker = six.indexbytes(value_item.data_value, 0)
                    if marker in (1, 3):
                        encoded_command_set.append(value_item.data_value[1:])
                        if marker == 3:
                            command_set_received = True
                            command_set = dsutils.decode(
                                b''.join(encoded_command_set),
                                True, True
                            )

                            msg = self._command_set_to_message(command_set)
                            no_ds = command_set[(0x0000,
                                                 0x0800)].value == 0x0101
                            use_file = (msg.sop_class_uid in
                                        self.ae.store_in_file)
                            if not no_ds and use_file:
                                ctx = self.accepted_contexts[pc_id]
                                dataset, start = self.ae.get_file(ctx,
                                                                  command_set)
                                if encoded_data_set:
                                    dataset.writelines(encoded_data_set)
                            if no_ds or data_set_received:
                                receiving = False  # response: no dataset
                                break
                    elif marker in (0, 2):
                        if dataset:
                            dataset.write(value_item.data_value[1:])
                        else:
                            encoded_data_set.append(value_item.data_value[1:])
                        if marker == 2:
                            data_set_received = True
                            if command_set_received:
                                receiving = False
                                break
                    else:
                        raise exceptions.DIMSEProcessingError(
                            'Incorrect first PDV byte')
        except Exception:
            if dataset:
                dataset.close()
            raise

        if data_set_received:
            if dataset:
                dataset.seek(start)
                msg.data_set = dataset
            else:
                msg.data_set = b''.join(encoded_data_set)
        return msg, pc_id

    def kill(self):
        """Stops internal DUL service provider.

        In most cases you won't need to use this method directly. Refer to
        release and abort instead.
        :rtype : None
        """
        for _ in range(1000):
            if self.dul.stop():
                continue
            time.sleep(0.001)
        self.dul.kill()
        self.association_established = False

    def release(self):
        """Releases association.

        Requests the release of the association and waits for
        confirmation

        :rtype : None
        """
        self.dul.send(pdu.AReleaseRqPDU())
        rsp = self.dul.receive(self.ae.timeout)
        self.kill()
        return rsp

    @staticmethod
    def _command_set_to_message(command_set):
        command_field = command_set[(0x0000, 0x0100)].value
        msg_type = dimsemessages.MESSAGE_TYPE[command_field]
        msg = msg_type(command_set)
        return msg


class AssociationAcceptor(socketserver.StreamRequestHandler, Association):
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
        self.sop_classes_as_scp = {}
        self.remote_ae = b''

        socketserver.StreamRequestHandler.__init__(self,
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

    def accept(self, assoc_req):
        """Waits for an association request from a remote AE. Upon reception
        of the request sends association response based on
        acceptable_pr_contexts"""
        user_items = assoc_req.variable_items[-1]
        self.max_pdu_length = user_items.user_data[0].maximum_length_received

        # analyse proposed presentation contexts
        rsp = [assoc_req.variable_items[0]]
        requested = (
            (item.context_id, item.abs_sub_item.name, item.ts_sub_items)
            for item in assoc_req.variable_items[1:-1]
        )

        for pc_id, proposed_sop, proposed_ts in requested:
            if proposed_sop not in self.ae.supported_scp:
                # refuse sop class because of SOP class not supported
                rsp.append(
                    pdu.PresentationContextItemAC(
                        pc_id, 1, pdu.TransferSyntaxSubItem(''))
                )
                continue

            for ts in proposed_ts:
                if ts.name in self.ae.supported_ts:
                    rsp.append(pdu.PresentationContextItemAC(pc_id, 0, ts))
                    ts_uid = _dicom.UID(ts.name)
                    self.sop_classes_as_scp[pc_id] = (pc_id, proposed_sop,
                                                      ts_uid)
                    self.accepted_contexts[pc_id] = PContextDef(
                        pc_id, proposed_sop, ts_uid
                    )
                    break
            else:  # Refuse sop class because of TS not supported
                rsp.append(
                    pdu.PresentationContextItemAC(
                        pc_id, 1, pdu.TransferSyntaxSubItem(''))
                )

        rsp.append(user_items)
        res = pdu.AAssociateAcPDU(
            called_ae_title=assoc_req.called_ae_title,
            calling_ae_title=assoc_req.calling_ae_title,
            variable_items=rsp
        )
        self.dul.send(res)
        self.remote_ae = assoc_req.calling_ae_title

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
            self.ae.on_association_request(self, assoc_req)
        except exceptions.AssociationRejectedError as e:
            self.reject(e.result, e.source, e.diagnostic)
            raise

        self.accept(assoc_req)
        self.association_established = True

    def _loop(self):
        while not self.is_killed:
            dimse_msg, pc_id = self.receive()
            uid = dimse_msg.sop_class_uid
            try:
                _, sop_class, ts = self.sop_classes_as_scp[pc_id]
                service = self.ae.supported_scp[uid]
            except KeyError:
                raise exceptions.ClassNotSupportedError(
                    'SOP Class {0} not supported as SCP'.format(uid))
            else:
                service(self, PContextDef(pc_id, sop_class, ts), dimse_msg)


class AssociationRequester(Association):
    def __init__(self, local_ae, remote_ae=None):
        super(AssociationRequester, self).__init__(local_ae, None)
        self.context_def_list = local_ae.copy_context_def_list()
        self.remote_ae = remote_ae
        self.sop_classes_as_scu = {}

    def abort(self, reason=0):
        """Aborts association with specified reason

        :rtype : None
        :param reason: abort reason
        """
        self.dul.send(pdu.AAbortPDU(source=0, reason_diag=reason))
        self.kill()

    def _request(self, local_ae, remote_ae, mp, pcdl, users_pdu=None):
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
                userdataitems.UserIdentityNegotiationSubItem(username, password))
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

        # Get maximum pdu length from answer
        user_data = response.variable_items[-1].user_data
        try:
            self.max_pdu_length = user_data[0].maximum_length_received
        except IndexError:
            self.max_pdu_length = 16000

        # Get accepted presentation contexts
        accepted = (ctx for ctx in response.variable_items[1:-1]
                    if ctx.result_reason == 0)
        for ctx in accepted:
            pc_id = ctx.context_id
            sop_class = pcdl[ctx.context_id].sop_class
            ts_uid = _dicom.UID(ctx.ts_sub_item.name)
            self.sop_classes_as_scu[sop_class] = (pc_id, ts_uid)
            self.accepted_contexts[pc_id] = PContextDef(pc_id, sop_class,
                                                        ts_uid)
        return response

    def request(self):
        ext = [userdataitems.ScpScuRoleSelectionSubItem(uid, 0, 1)
               for uid in self.ae.supported_scp.keys()]
        custom_items = self.remote_ae.get('user_data', [])
        response = self._request(
            self.ae.local_ae, self.remote_ae, self.ae.max_pdu_length,
            self.context_def_list, users_pdu=ext+custom_items
        )
        self.ae.on_association_response(response)
        self.association_established = True

    def scu(self, ds, msg_id):
        uid = ds.SOPClassUID
        try:
            pc_id, transfer_syntax = self.sop_classes_as_scu[uid]
            service = self.ae.supported_scu[uid]
        except KeyError:
            raise exceptions.ClassNotSupportedError(
                'SOP Class %s not supported as SCU')
        else:
            return service(self, PContextDef(pc_id, uid, transfer_syntax),
                           ds, msg_id)

    def get_scu(self, sop_class):
        try:
            pc_id, ts = self.sop_classes_as_scu[sop_class]
            service = self.ae.supported_scu[sop_class]
        except KeyError:
            raise exceptions.ClassNotSupportedError(
                'SOP Class %s not supported as SCU' % sop_class)
        else:
            return functools.partial(service, self,
                                     PContextDef(pc_id, sop_class, ts))
