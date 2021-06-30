# Copyright (c) 2021 Pavel 'Blane' Tuchin
# Copyright (c) 2012 Patrice Munger
# This file is part of pynetdicom, released under a modified MIT license.
#    See the file license.txt included with this distribution, also
#    available at http://pynetdicom.googlecode.com
#
"""
Module contains two key classes for working with DICOM associations:

    * :class:`~pynetdicom2.asceprovider.AssociationAcceptor` for handling incoming association
      requests.
    * :class:`~pynetdicom2.asceprovider.AssociationRequester` for requesting association.

In most cases you won't have to create AssociationAcceptor or AssociationRequester directly, but
rather they will be created for you by either :class:`~pynetdicom2.applicationentity.ClientAE`
or :class:`~pynetdicom2.applicationentity.AE`. Please, refer to documentation on those classes
on how to request new association or how incoming association are handled.

Each association class is not only responsible for initial establishment, but also for all
association life-cycle until it's either released or aborted.
"""

from __future__ import absolute_import, unicode_literals

# This module provides association services
import collections
import functools
from itertools import chain
import time

import six
from six.moves import socketserver, range  # type: ignore
from pydicom import uid

from . import exceptions
from . import dulprovider

from . import pdu
from . import userdataitems

PContextDef = collections.namedtuple(
    'PContextDef',
    ['id', 'sop_class', 'supported_ts']
)


APPLICATION_CONTEXT_NAME = uid.UID('1.2.840.10008.3.1.1.1')
IMPLEMENTATION_UID = uid.UID('1.2.826.0.1.3680043.8.498.1.1.155105445218102811803000')


def build_pres_context_def_list(context_def_list):
    """Builds a list of Presntation Context Items

    :param context_def_list: list of tuples (presentation context ID and PContextDef)
    :type context_def_list: Tuple[int,PContextDef]
    :return: generator that yields :class:`pynetdicom2.pdu.PresentationContextItemRQ` instances
    """
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

    def __init__(self, local_ae, dul_socket, max_pdu_length):
        """Initializes Association instance with local AE title and DUL service
        provider

        :param local_ae: local AE title parameters
        :param dul_socket: socket for DUL provider or None if it's not needed
        :param max_pdu_length: Maximum PDU length
        """
        self.ae = local_ae
        self.dul = dulprovider.DULServiceProvider(
            self.ae.store_in_file, self.ae.get_file, dul_socket, max_pdu_length
        )
        self.association_established = False
        self.max_pdu_length = max_pdu_length
        self.accepted_contexts = {}

    def send(self, dimse_msg, pc_id):
        """Sends DIMSE message

        :param dimse_msg: DIMSE message
        :type dimse_msg: dimsemessages.DIMSEMessage
        :param pc_id: Presentation Context Definition
        :type pc_id: PContextDef
        """
        dimse_msg.set_length()
        self.dul.send(dimse_msg.encode(pc_id, self.max_pdu_length))

    def receive(self):
        """Receives DIMSE message

        :return: tuple, containing DIMSE message and presentation context ID
        :rtype: Tuple[dimsemessages.DIMSEMessage, int]
        """
        return self._get_dul_message()

    def kill(self):
        """Stops internal DUL service provider.

        In most cases you won't need to use this method directly. Refer to
        release and abort instead.
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
        """
        self.dul.send(pdu.AReleaseRqPDU())
        rsp = self.dul.receive(self.ae.timeout)
        self.kill()
        return rsp

    def _get_dul_message(self):
        dul_msg = self.dul.receive(self.ae.timeout)
        if isinstance(dul_msg, tuple):
            return dul_msg
        if dul_msg.pdu_type == pdu.AReleaseRqPDU.pdu_type:
            raise exceptions.AssociationReleasedError()
        if dul_msg.pdu_type == pdu.AAbortPDU.pdu_type:
            raise exceptions.AssociationAbortedError(dul_msg.source, dul_msg.reason_diag)
        if dul_msg.pdu_type == pdu.AAssociateRjPDU.pdu_type:
            raise exceptions.AssociationRejectedError(
                dul_msg.result, dul_msg.source, dul_msg.reason_diag)
        raise exceptions.NetDICOMError()


class AssociationAcceptor(socketserver.StreamRequestHandler, Association):
    """'Server-side' association implementation.

    Class is intended for handling incoming association requests.
    """

    def __init__(self, request, client_address, local_ae, max_pdu_length):
        """Initializes AssociationAcceptor instance with specified client socket

        :param local_ae: local AE title
        :param request: client socket
        """
        Association.__init__(self, local_ae, request, max_pdu_length)
        self.is_killed = False
        self.sop_classes_as_scp = {}
        self.remote_ae = b''

        socketserver.StreamRequestHandler.__init__(self, request, client_address, local_ae)

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
        max_pdu_sub_item = user_items.user_data[0]
        if self.max_pdu_length > max_pdu_sub_item.maximum_length_received:
            self.max_pdu_length = max_pdu_sub_item.maximum_length_received
        max_pdu_sub_item.maximum_length_received = self.max_pdu_length

        # analyse proposed presentation contexts
        rsp = [assoc_req.variable_items[0]]
        requested = (
            (item.context_id, item.abs_sub_item.name, item.ts_sub_items)
            for item in assoc_req.variable_items[1:-1]
        )

        for pc_id, proposed_sop, proposed_ts in requested:
            if proposed_sop not in self.ae.supported_scp:
                # refuse sop class because of SOP class not supported
                rsp.append(pdu.PresentationContextItemAC(pc_id, 1, pdu.TransferSyntaxSubItem('')))
                continue

            for ts in proposed_ts:
                if ts.name in self.ae.supported_ts:
                    rsp.append(pdu.PresentationContextItemAC(pc_id, 0, ts))
                    ts_uid = uid.UID(ts.name)
                    self.sop_classes_as_scp[pc_id] = (pc_id, proposed_sop, ts_uid)
                    self.accepted_contexts[pc_id] = PContextDef(pc_id, proposed_sop, ts_uid)
                    break
            else:  # Refuse sop class because of TS not supported
                rsp.append(
                    pdu.PresentationContextItemAC(pc_id, 1, pdu.TransferSyntaxSubItem(''))
                )
        self.dul.accepted_contexts = self.accepted_contexts

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
        except exceptions.DCMTimeoutError:
            pass  # TODO: Handle timeout error
        finally:
            self.kill()

    def _establish(self):
        try:
            assoc_req = self.dul.receive(self.ae.timeout)
            self.ae.on_association_request(self, assoc_req)
        except exceptions.AssociationRejectedError as exc:
            self.reject(exc.result, exc.source, exc.diagnostic)
            raise

        self.accept(assoc_req)
        self.association_established = True

    def _loop(self):
        while not self.is_killed:
            dimse_msg, pc_id = self.receive()
            _uid = dimse_msg.sop_class_uid
            try:
                _, sop_class, ts = self.sop_classes_as_scp[pc_id]
                service = self.ae.supported_scp[_uid]
            except KeyError:
                raise exceptions.ClassNotSupportedError(
                    'SOP Class {0} not supported as SCP'.format(_uid))
            else:
                service(self, PContextDef(pc_id, sop_class, ts), dimse_msg)


class AssociationRequester(Association):
    """Class for managing association request.

    Generally you would not need to construct this class directly, rather it would be created
    for you, when using :class:`~pynetdicom2.applicationentity.AE` or
    :class:`~pynetdicom2.applicationentity.ClientAE`.

    :ivar context_def_list: presentation context definitions in a form of dict
                            (PC ID -> Presentation Context)
    :ivar remote_ae: dictionary, containing remote AET, address, port and other information
    :ivar sop_classes_as_scu: dictionary which maps accepted SOP Classes to presentation contexts.
                              empty, until association is established.
    """

    def __init__(self, local_ae, max_pdu_length, remote_ae):
        super(AssociationRequester, self).__init__(local_ae, None, max_pdu_length)
        self.context_def_list = local_ae.copy_context_def_list()
        self.remote_ae = remote_ae
        self.sop_classes_as_scu = {}

    def request(self):
        """Requests association with remote AET."""
        ext = [userdataitems.ScpScuRoleSelectionSubItem(uid, 0, 1)
               for uid in self.ae.supported_scp.keys()]
        custom_items = self.remote_ae.get('user_data', [])
        response = self._request(
            self.ae.local_ae, self.remote_ae, users_pdu=ext+custom_items
        )
        self.ae.on_association_response(response)
        self.association_established = True

    def get_scu(self, sop_class):
        """Get SCU function to use (like for making a C-FIND request).

        SCU are generally provided by `sopclass` module. First argument of the service
        would be bound to current association and second would be bound to current presentation
        contexnt.

        :param sop_class: SOP Class UID
        :type sop_class: Union[str,pydicom.uid.UID]
        :raises exceptions.ClassNotSupportedError: raised if provided SOP Class UID is not
                                                   supported by association.
        :return: SCU function
        """
        try:
            pc_id, ts = self.sop_classes_as_scu[sop_class]
            service = self.ae.supported_scu[sop_class]
        except KeyError:
            raise exceptions.ClassNotSupportedError(
                'SOP Class {} not supported as SCU'.format(sop_class)
            )
        else:
            return functools.partial(service, self, PContextDef(pc_id, sop_class, ts))

    def abort(self, reason=0):
        """Aborts association with specified reason

        :param reason: abort reason
        """
        self.dul.send(pdu.AAbortPDU(source=0, reason_diag=reason))
        self.kill()

    def _request(self, local_ae, remote_ae, users_pdu=None):
        """Requests an association with a remote AE and waits for association
        response."""
        max_pdu_length_par = userdataitems.MaximumLengthSubItem(self.max_pdu_length)
        implementation_uid = userdataitems.ImplementationClassUIDSubItem(IMPLEMENTATION_UID)
        user_information = [max_pdu_length_par, implementation_uid] + users_pdu \
            if users_pdu else [max_pdu_length_par, implementation_uid]
        username = remote_ae.get('username')
        password = remote_ae.get('password')
        if username and password:
            user_information.append(
                userdataitems.UserIdentityNegotiationSubItem(username, password))
        elif username:
            user_information.append(
                userdataitems.UserIdentityNegotiationSubItem(
                    username, user_identity_type=1))
        elif 'kerberos' in remote_ae:
            user_information.append(
                userdataitems.UserIdentityNegotiationSubItem(
                    remote_ae['kerberos'], user_identity_type=3))
        elif 'saml' in remote_ae:
            user_information.append(
                userdataitems.UserIdentityNegotiationSubItem(
                    remote_ae['saml'], user_identity_type=4))
        elif 'jwt' in remote_ae:
            user_information.append(
                userdataitems.UserIdentityNegotiationSubItem(
                    remote_ae['jwt'], user_identity_type=5))

        variable_items = list(chain(
            [pdu.ApplicationContextItem(APPLICATION_CONTEXT_NAME)],
            build_pres_context_def_list(self.context_def_list),
            [pdu.UserInformationItem(user_information)]
        ))
        assoc_rq = pdu.AAssociateRqPDU(
            called_ae_title=remote_ae['aet'],
            calling_ae_title=local_ae['aet'],
            variable_items=variable_items
        )
        # FIXME pass parameter properly
        assoc_rq.called_presentation_address = (remote_ae['address'], remote_ae['port'])
        self.dul.send(assoc_rq)
        response = self.dul.receive(self.ae.timeout)
        if isinstance(response, tuple) or response.pdu_type != pdu.AAssociateAcPDU.pdu_type:
            return exceptions.AssociationError('Invalid repsonse')

        # Get maximum pdu length from answer
        user_data = response.variable_items[-1].user_data
        try:
            max_pdu_length = user_data[0].maximum_length_received
            if max_pdu_length and self.max_pdu_length > max_pdu_length:
                self.max_pdu_length = max_pdu_length
        except IndexError:
            pass

        # Get accepted presentation contexts
        accepted = (ctx for ctx in response.variable_items[1:-1] if ctx.result_reason == 0)
        for ctx in accepted:
            pc_id = ctx.context_id
            sop_class = self.context_def_list[ctx.context_id].sop_class
            ts_uid = uid.UID(ctx.ts_sub_item.name)
            self.sop_classes_as_scu[sop_class] = (pc_id, ts_uid)
            self.accepted_contexts[pc_id] = PContextDef(pc_id, sop_class, ts_uid)
        self.dul.accepted_contexts = self.accepted_contexts
        return response
