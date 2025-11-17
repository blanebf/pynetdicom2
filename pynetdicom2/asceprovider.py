# Copyright (c) 2021 Pavel 'Blane' Tuchin
# Copyright (c) 2012 Patrice Munger
# This file is part of pynetdicom, released under a modified MIT license.
#    See the file license.txt included with this distribution, also
#    available at http://pynetdicom.googlecode.com
#
"""
Module contains two key classes for working with DICOM associations:

    * :class:`~pynetdicom2.asceprovider.AssociationAcceptor` for handling
      incoming association requests.
    * :class:`~pynetdicom2.asceprovider.AssociationRequester` for requesting
      association.

In most cases you won't have to create AssociationAcceptor or
AssociationRequester directly, but rather they will be created for you by
either :class:`~pynetdicom2.applicationentity.ClientAE` or
:class:`~pynetdicom2.applicationentity.AE`. Please, refer to documentation
on those classes on how to request new association or how incoming association
are handled.

Each association class is not only responsible for initial establishment, but
also for all association life-cycle until it's either released or aborted.
"""
from abc import abstractmethod
import contextlib
import dataclasses
import functools
from itertools import chain
import time
import socket
import socketserver
from typing import (
    Any, BinaryIO, Callable, Iterable, Iterator, Optional, Protocol, TypeVar,
    Union
)

import pydicom
from pydicom import uid

from pynetdicom2 import dimsemessages

from . import exceptions, dulprovider, fsm, pdu, statuses, userdataitems

# backwards compatability
from .fsm import PContextDef  # pylint: disable=unused-import. # noqa F401


@dataclasses.dataclass(frozen=True)
class RemoteAEConfig:
    aet: str
    address: str
    port: int
    username: Optional[str] = None
    password: Optional[str] = None
    kerberos: Optional[str] = None
    saml: Optional[str] = None
    jwt: Optional[str] = None
    user_data: list[pdu.UserItem] = dataclasses.field(default_factory=list)


@dataclasses.dataclass(frozen=True)
class AETParams:
    address: str
    aet: str
    port: Optional[int] = None


@dataclasses.dataclass(frozen=True)
class PContextDefList:
    id: int
    sop_class: uid.UID
    supported_ts: frozenset[uid.UID]


T = TypeVar('T', bound=dimsemessages.DIMSERequestMessage, contravariant=True)


class SCPServiceWithSOPClass(Protocol[T]):
    sop_classes: list[uid.UID]
    store_in_file: bool

    @abstractmethod
    def __call__(
            self,
            asce: 'AssociationAcceptor',
            ctx: fsm.PContextDef,
            msg: T
    ) -> None:
        ...


class SCPService(Protocol[T]):
    @abstractmethod
    def __call__(
            self,
            asce: 'AssociationAcceptor',
            ctx: fsm.PContextDef,
            msg: T
     ) -> None:
        ...


class SCUService(Protocol):
    def __call__(
            self,
            asce: 'AssociationRequester',
            ctx: fsm.PContextDef,
            *args: Any,
            **kwargs: Any
    ) -> Any:
        ...


class SCUServiceWithSOPClass(Protocol):
    sop_classes: list[uid.UID]
    store_in_file: bool

    @abstractmethod
    def __call__(
            self,
            asce: 'AssociationRequester',
            ctx: fsm.PContextDef,
            *args: Any,
            **kwargs: Any
    ) -> Any:
        ...


class AEBaseProto(Protocol):
    default_ts: list[uid.UID]

    local_ae: AETParams
    supported_ts: frozenset[uid.UID]
    dcm_timeout: int
    max_pdu_length: int

    context_def_list: dict[int, PContextDefList]
    store_in_file: set[uid.UID] = set()
    supported_scu: dict[uid.UID, SCUServiceWithSOPClass]
    supported_scp: dict[
        uid.UID, SCPServiceWithSOPClass[dimsemessages.DIMSERequestMessage]
    ]

    def add_scu(
            self,
            service: SCUServiceWithSOPClass,
            sop_classes: Optional[list[uid.UID]] = None
    ) -> 'AEBaseProto':
        ...

    def update_context_def_list(
            self, sop_classes: Iterable[uid.UID], store_in_file: bool = False
    ) -> None:
        ...

    def copy_context_def_list(self) -> dict[int, PContextDefList]:
        ...

    def get_file(
            self,
            context: fsm.PContextDef,
            command_set: pydicom.Dataset
    ) -> tuple[BinaryIO, int]:
        ...

    @contextlib.contextmanager
    def request_association(
            self,
            remote_ae: Union[RemoteAEConfig, dict[str, Any]]
    ) -> Iterator['AssociationRequester']:
        ...

    def on_association_request(
            self, asce: 'AssociationAcceptor', assoc: pdu.AAssociateRqPDU
    ) -> None:
        ...

    def on_association_response(self, response: pdu.AAssociateAcPDU) -> None:
        ...

    def on_receive_echo(self, context: fsm.PContextDef) -> statuses.Status:
        ...

    def on_receive_store(
            self, context: fsm.PContextDef, ds: Union[BinaryIO, bytes]
    ) -> statuses.Status:
        ...

    def on_receive_find(
            self, context: fsm.PContextDef, ds: pydicom.Dataset
    ) -> Iterator[tuple[pydicom.Dataset, statuses.Status]]:
        ...

    def on_receive_move(
            self,
            context: fsm.PContextDef,
            ds: pydicom.Dataset,
            destination: str
     ) -> tuple[RemoteAEConfig, int, Iterator[pydicom.Dataset]]:
        ...

    def on_commitment_request(
            self,
            remote_ae: str,
            uids: Iterable[tuple[uid.UID, uid.UID]]
    ) -> tuple[
        RemoteAEConfig,
        Iterable[tuple[uid.UID, uid.UID]],
        Iterable[tuple[uid.UID, uid.UID, int]]
    ]:
        ...

    def on_commitment_response(
            self,
            transaction_uid: uid.UID,
            success: Iterable[tuple[uid.UID, uid.UID]],
            failure: Iterable[tuple[uid.UID, uid.UID, int]]
    ) -> None:
        ...


class AEBaseServerProto(AEBaseProto, socketserver.BaseServer):
    pass


APPLICATION_CONTEXT_NAME = uid.UID('1.2.840.10008.3.1.1.1')
IMPLEMENTATION_UID = uid.UID(
    '1.2.826.0.1.3680043.8.498.1.1.155105445218102811803000'
)


def build_pres_context_def_list(
        context_def_list: dict[int, PContextDefList]
) -> Iterable[pdu.PresentationContextItemRQ]:
    """Builds a list of Presntation Context Items

    :param context_def_list: list of tuples (presentation context ID and
                             PContextDef)
    :return: generator that yields
             :class:`pynetdicom2.pdu.PresentationContextItemRQ` instances
    """
    return (
        pdu.PresentationContextItemRQ(
            pc_id, pdu.AbstractSyntaxSubItem(ctx.sop_class),
            [pdu.TransferSyntaxSubItem(i) for i in ctx.supported_ts]
        )
        for pc_id, ctx in context_def_list.items()
    )


class Association:
    """Base association class.

    Class is not intended for direct usage and meant to be sub-classed.
    Class provides basic association interface: creation, release and abort.
    """

    def __init__(
            self,
            local_ae: AEBaseProto,
            dul_socket: Optional[socket.socket],
            max_pdu_length: int
    ) -> None:
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
        self.association_established: bool = False
        self.max_pdu_length = max_pdu_length
        self.accepted_contexts: dict[int, fsm.PContextDef] = {}

    def send(self, dimse_msg: dimsemessages.DIMSEMessage, pc_id: int) -> None:
        """Sends DIMSE message

        :param dimse_msg: DIMSE message
        :param pc_id: Presentation Context Definition
        """
        dimse_msg.set_length()
        self.dul.send(dimse_msg.encode(pc_id, self.max_pdu_length))

    def receive(self) -> tuple[dimsemessages.DIMSEMessage, int]:
        """Receives DIMSE message

        :return: tuple, containing DIMSE message and presentation context ID
        """
        return self._get_dul_message()

    def kill(self) -> None:
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

    def release(self) -> pdu.AReleaseRpPDU:
        """Releases association.

        Requests the release of the association and waits for
        confirmation
        """
        self.dul.send(pdu.AReleaseRqPDU())
        rsp = self.dul.receive(self.ae.dcm_timeout)
        if isinstance(rsp, tuple):
            raise exceptions.NetDICOMError(
                f'Unexpected DIMSE message on release: {rsp}'
            )
        if not isinstance(rsp, pdu.AReleaseRpPDU):
            raise exceptions.NetDICOMError(
                f'Unexpected PDU on release {rsp}'
            )
        self.kill()
        return rsp

    def _get_dul_message(self) -> tuple[dimsemessages.DIMSEMessage, int]:
        dul_msg = self.dul.receive(self.ae.dcm_timeout)
        if isinstance(dul_msg, tuple):
            return dul_msg
        self._handle_errors(dul_msg)
        raise exceptions.NetDICOMError()

    @staticmethod
    def _handle_errors(dul_msg: Union[fsm.PDUType]) -> None:
        if isinstance(dul_msg, pdu.AReleaseRqPDU):
            raise exceptions.AssociationReleasedError()
        if isinstance(dul_msg, pdu.AAbortPDU):
            raise exceptions.AssociationAbortedError(
                dul_msg.source, dul_msg.reason_diag
            )
        if isinstance(dul_msg, pdu.AAssociateRjPDU):
            raise exceptions.AssociationRejectedError(
                dul_msg.result, dul_msg.source, dul_msg.reason_diag
            )


class AssociationAcceptor(socketserver.StreamRequestHandler, Association):
    """'Server-side' association implementation.

    Class is intended for handling incoming association requests.
    """

    def __init__(
            self,
            request: socket.socket,
            client_address: tuple[str, int],
            local_ae: AEBaseServerProto,
            max_pdu_length: int
    ) -> None:
        """Initializes AssociationAcceptor instance with specified client
        socket

        :param local_ae: local AE title
        :param request: client socket
        """
        Association.__init__(self, local_ae, request, max_pdu_length)
        self.is_killed = False
        self.sop_classes_as_scp: dict[int, tuple[int, uid.UID, uid.UID]] = {}
        self.remote_ae: str = ''
        self.local_ae: str = ''

        socketserver.StreamRequestHandler.__init__(
            self, request, client_address, local_ae
        )

    def kill(self) -> None:
        """Overrides base class kill method to set stop-flag for running thread
        """
        self.is_killed = True
        super().kill()

    def abort(self, reason: int) -> None:
        """Aborts association with specified reason

        :param reason: abort reason
        """
        self.dul.send(pdu.AAbortPDU(source=2, reason_diag=reason))
        self.kill()

    def reject(self, result: int, source: int, diag: int) -> None:
        """Rejects association with specified parameters

        :param result:
        :param source:
        :param diag:
        """
        self.dul.send(pdu.AAssociateRjPDU(result, source, diag))

    def accept(self, assoc_req: pdu.AAssociateRqPDU) -> None:
        """Waits for an association request from a remote AE. Upon reception
        of the request sends association response based on
        acceptable_pr_contexts"""
        user_items = assoc_req.variable_items[-1]
        if not isinstance(user_items, pdu.UserInformationItem):
            raise AssertionError(f'Unexpected sub-item: {user_items}')
        max_pdu_sub_item = user_items.user_data[0]
        if not isinstance(
                max_pdu_sub_item, userdataitems.MaximumLengthSubItem
        ):
            raise exceptions.AssociationError(
                'First sub-item is not MaximumLengthSubItem: '
                f'{max_pdu_sub_item}'
            )
        if self.max_pdu_length > max_pdu_sub_item.maximum_length_received:
            self.max_pdu_length = max_pdu_sub_item.maximum_length_received
        max_pdu_sub_item.maximum_length_received = self.max_pdu_length

        # analyse proposed presentation contexts
        rsp = [assoc_req.variable_items[0]]
        requested = (
            (item.context_id, item.abs_sub_item.name, item.ts_sub_items)
            for item in assoc_req.variable_items[1:-1]
            if isinstance(item, pdu.PresentationContextItemRQ)
        )

        for pc_id, proposed_sop, proposed_ts in requested:
            if proposed_sop not in self.ae.supported_scp:
                # refuse sop class because of SOP class not supported
                rsp.append(
                    pdu.PresentationContextItemAC(
                        pc_id,
                        1,
                        pdu.TransferSyntaxSubItem('')
                    )
                )
                continue

            for ts in proposed_ts:
                if ts.name in self.ae.supported_ts:
                    rsp.append(pdu.PresentationContextItemAC(pc_id, 0, ts))
                    ts_uid = uid.UID(ts.name)
                    self.sop_classes_as_scp[pc_id] = (
                        pc_id, uid.UID(proposed_sop), ts_uid
                    )
                    self.accepted_contexts[pc_id] = fsm.PContextDef(
                        pc_id, uid.UID(proposed_sop), ts_uid
                    )
                    break
            else:  # Refuse sop class because of TS not supported
                rsp.append(
                    pdu.PresentationContextItemAC(
                        pc_id, 1, pdu.TransferSyntaxSubItem('')
                    )
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
        self.local_ae = assoc_req.called_ae_title

    def handle(self) -> None:
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

    def _establish(self) -> None:
        try:
            assoc_req = self.dul.receive(self.ae.dcm_timeout)
            if not isinstance(assoc_req, pdu.AAssociateRqPDU):
                raise exceptions.AssociationError(
                    f'Invalid request on associaction: {assoc_req}'
                )

            self.ae.on_association_request(self, assoc_req)
        except exceptions.AssociationRejectedError as exc:
            self.reject(exc.result, exc.source, exc.diagnostic)
            raise

        self.accept(assoc_req)
        self.association_established = True

    def _loop(self) -> None:
        while not self.is_killed:
            dimse_msg, pc_id = self.receive()
            _uid = dimse_msg.sop_class_uid
            try:
                if not isinstance(
                        dimse_msg, dimsemessages.DIMSERequestMessage
                ):
                    raise exceptions.DIMSEProcessingError(
                        f'Expected DIMSE Request message but got: {dimse_msg}'
                    )
                _, sop_class, ts = self.sop_classes_as_scp[pc_id]
                service = self.ae.supported_scp[_uid]
            except KeyError as exc:
                raise exceptions.ClassNotSupportedError(
                    f'SOP Class {_uid} not supported as SCP'
                ) from exc
            else:
                service(self, fsm.PContextDef(pc_id, sop_class, ts), dimse_msg)


class AssociationRequester(Association):
    """Class for managing association request.

    Generally you would not need to construct this class directly, rather it
    would be created for you, when using
    :class:`~pynetdicom2.applicationentity.AE` or
    :class:`~pynetdicom2.applicationentity.ClientAE`.

    :ivar context_def_list: presentation context definitions in a form of dict
                            (PC ID -> Presentation Context)
    :ivar remote_ae: dictionary, containing remote AET, address, port and other
                     information
    :ivar sop_classes_as_scu: dictionary which maps accepted SOP Classes
                              to presentation contexts. empty, until
                              association is established.
    """

    def __init__(
            self,
            local_ae: AEBaseProto,
            max_pdu_length: int,
            remote_ae: Union[RemoteAEConfig, dict[str, Any]]
    ) -> None:
        super().__init__(local_ae, None, max_pdu_length)
        if isinstance(remote_ae, dict):
            remote_ae = RemoteAEConfig(**remote_ae)

        self.context_def_list = local_ae.copy_context_def_list()
        self.remote_ae = remote_ae
        self.sop_classes_as_scu: dict[uid.UID, tuple[int, uid.UID]] = {}

    def request(self) -> None:
        """Requests association with remote AET."""
        ext = [userdataitems.ScpScuRoleSelectionSubItem(uid, 0, 1)
               for uid in self.ae.supported_scp.keys()]
        custom_items = self.remote_ae.user_data
        response = self._request(
            self.ae.local_ae, self.remote_ae, users_pdu=ext+custom_items
        )
        self.ae.on_association_response(response)
        self.association_established = True

    def get_scu(self, sop_class: uid.UID) -> Callable[..., Any]:
        """Get SCU function to use (like for making a C-FIND request).

        SCU are generally provided by `sopclass` module. First argument of the
        service would be bound to current association and second would be bound
        to current presentation contexnt.

        :param sop_class: SOP Class UID
        :raises exceptions.ClassNotSupportedError: raised if provided SOP
                                                   Class UID is not supported
                                                   by association.
        :return: SCU function
        """
        try:
            pc_id, ts = self.sop_classes_as_scu[sop_class]
            service = self.ae.supported_scu[sop_class]
        except KeyError as exc:
            raise exceptions.ClassNotSupportedError(
                f'SOP Class {sop_class} not supported as SCU'
            ) from exc
        else:
            return functools.partial(
                service, self, fsm.PContextDef(pc_id, sop_class, ts)
            )

    def abort(self, reason: int = 0) -> None:
        """Aborts association with specified reason

        :param reason: abort reason
        """
        self.dul.send(pdu.AAbortPDU(source=0, reason_diag=reason))
        self.kill()

    def _request(
            self,
            local_ae: AETParams,
            remote_ae: RemoteAEConfig,
            users_pdu: Optional[list[pdu.UserItem]] = None
    ) -> pdu.AAssociateAcPDU:
        """Requests an association with a remote AE and waits for association
        response."""
        max_pdu_length_par = userdataitems.MaximumLengthSubItem(
            self.max_pdu_length
        )
        implementation_uid = userdataitems.ImplementationClassUIDSubItem(
            IMPLEMENTATION_UID
        )
        user_information: list[pdu.UserItem] = [
            max_pdu_length_par, implementation_uid
        ]
        if users_pdu:
            user_information.extend(users_pdu)
        username = remote_ae.username
        password = remote_ae.password
        if username and password:
            user_information.append(
                userdataitems.UserIdentityNegotiationSubItem(
                    username, password
                )
            )
        elif username:
            user_information.append(
                userdataitems.UserIdentityNegotiationSubItem(
                    username, user_identity_type=1
                )
            )
        elif remote_ae.kerberos:
            user_information.append(
                userdataitems.UserIdentityNegotiationSubItem(
                    remote_ae.kerberos, user_identity_type=3
                )
            )
        elif remote_ae.saml:
            user_information.append(
                userdataitems.UserIdentityNegotiationSubItem(
                    remote_ae.saml, user_identity_type=4
                )
            )
        elif remote_ae.jwt:
            user_information.append(
                userdataitems.UserIdentityNegotiationSubItem(
                    remote_ae.jwt, user_identity_type=5
                )
            )

        variable_items: list[pdu.VariableItems] = list(chain(
            [pdu.ApplicationContextItem(APPLICATION_CONTEXT_NAME)],
            build_pres_context_def_list(self.context_def_list),
            [pdu.UserInformationItem(user_information)]
        ))
        assoc_rq = pdu.AAssociateRqPDU(
            called_ae_title=remote_ae.aet,
            calling_ae_title=local_ae.aet,
            variable_items=variable_items
        )
        self.dul.called_presentation_address = (
            remote_ae.address, remote_ae.port
        )
        self.dul.send(assoc_rq)
        response = self.dul.receive(self.ae.dcm_timeout)
        if isinstance(response, tuple):
            raise exceptions.AssociationError(
                f'Unexpected response: {response}'
            )
        self._handle_errors(response)
        if not isinstance(response, pdu.AAssociateAcPDU):
            raise exceptions.AssociationError('Invalid repsonse')

        # Get maximum pdu length from answer
        user_item = response.variable_items[-1]
        if not isinstance(user_item, pdu.UserInformationItem):
            raise exceptions.AssociationError(
                f'Unexpected item in place of UserInformation item {user_item}'
            )
        max_pdu_sub_item = user_item.user_data[0]
        if not isinstance(
                max_pdu_sub_item, userdataitems.MaximumLengthSubItem
        ):
            raise exceptions.AssociationError(
                'First sub-item is not MaximumLengthSubItem:'
                f' {max_pdu_sub_item}'
            )
        max_pdu_length = max_pdu_sub_item.maximum_length_received
        if max_pdu_length and self.max_pdu_length > max_pdu_length:
            self.max_pdu_length = max_pdu_length

        # Get accepted presentation contexts
        accepted = (
            ctx for ctx in response.variable_items[1:-1]
            if (
                isinstance(ctx, pdu.PresentationContextItemAC) and
                ctx.result_reason == 0
            )
        )
        for ctx in accepted:
            pc_id = ctx.context_id
            sop_class = self.context_def_list[ctx.context_id].sop_class
            ts_uid = uid.UID(ctx.ts_sub_item.name)
            self.sop_classes_as_scu[sop_class] = (pc_id, ts_uid)
            self.accepted_contexts[pc_id] = fsm.PContextDef(
                pc_id, sop_class, ts_uid
            )
        self.dul.accepted_contexts = self.accepted_contexts
        return response
