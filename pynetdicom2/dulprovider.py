# Copyright (c) 2021 Pavel 'Blane' Tuchin
# Copyright (c) 2012 Patrice Munger
# This file is part of pynetdicom, released under a modified MIT license.
#    See the file license.txt included with this distribution, also
#    available at https://github.com/blanebf/pynetdicom2
#

"""
This module implements the DUL service provider, allowing a DUL service user to
send and receive DUL messages (PDUs).  The User and Provider talk to each
other using a TCP socket. The DULServer runs in a thread, polling TCP socket
for incoming messages and sending messages from user queue.
Underlying logic of the service is implemented via state machine that is
described in DICOM standard.

In most of the cases you would not need to access
:class:`~pynetdicom2.dulprovider.DULServiceProvider` directly, but rather would
use higher level objects like sub-classes of
:class:`~pynetdicom2.asceprovider.Association` or various services.
"""
import collections
from collections.abc import Iterator
import logging
import select
import socket
import struct
import threading
import queue
from typing import Optional, Type, Union, cast

from pydicom import uid

from . import dimsemessages, fsm, pdu, exceptions


logger = logging.getLogger(__name__)


#: Maximum time (in seconds) to wait for the remote peer to close its side of
#: the connection during :meth:`DULServiceProvider._close`. Without a bound a
#: half-open or misbehaving peer would block the DUL thread indefinitely.
CLOSE_TIMEOUT = 10


PDU_TYPES: dict[int, tuple[Type[fsm.PDUType], fsm.Events]] = {
    0x01: (pdu.AAssociateRqPDU, fsm.Events.EVT_6),
    0x02: (pdu.AAssociateAcPDU, fsm.Events.EVT_3),
    0x03: (pdu.AAssociateRjPDU, fsm.Events.EVT_4),
    0x04: (pdu.PDataTfPDU, fsm.Events.EVT_10),
    0x05: (pdu.AReleaseRqPDU, fsm.Events.EVT_12),
    0x06: (pdu.AReleaseRpPDU, fsm.Events.EVT_13),
    0x07: (pdu.AAbortPDU, fsm.Events.EVT_16)
}

PDU_TO_EVENT = {
    # A-ASSOCIATE Request
    pdu.AAssociateRqPDU.pdu_type: fsm.Events.EVT_1,
    # A-ASSOCIATE Response (accept)
    pdu.AAssociateAcPDU.pdu_type: fsm.Events.EVT_7,
    # A-ASSOCIATE Response (reject)
    pdu.AAssociateRjPDU.pdu_type: fsm.Events.EVT_8,
    # A-Release Request
    pdu.AReleaseRqPDU.pdu_type: fsm.Events.EVT_11,
    # A-Release Response
    pdu.AReleaseRpPDU.pdu_type: fsm.Events.EVT_14,
    pdu.AAbortPDU.pdu_type: fsm.Events.EVT_15,
    pdu.PDataTfPDU.pdu_type: fsm.Events.EVT_9
}


class DULServiceProvider(threading.Thread):
    """Implements DUL service.

    This class is responsible for low-level operations with incoming and
    outgoing PDUs.

    Service can be initialized by providing open socket that service would
    use for sending and receiving PDUs. In case if socket is not provider
    service opens a client socket by itself when sending
    :class:`~pynetdicom2.pdu.AAssociateRqPDU` instance.

    Underlying implementation relies on state machine that is defined in
    :doc:`fsm`

    :ivar primitive: current PDU
    :ivar dimse_gen: generator, used break current outgoing DIMSE message into
                     P-DATA-TF PDUs
    :ivar event: current event
    :ivar max_pdu_length: maximum PDU length for incoming P-DATA-TF PDUs
    :ivar to_service_user: outgoing data queue
    :ivar from_service_user: incoming data queue
    :ivar dul_socket: socket, that service uses
    :ivar is_killed: DUL service termination flag
    """

    def __init__(
            self,
            store_in_file: set[uid.UID],
            get_file_cb: fsm.GetFileCB,
            dul_socket: Optional[socket.socket] = None,
            max_pdu_length: int = 65536,
            artim_timeout: int = 10,
    ) -> None:
        """Initializes DUL service.

        If no socket is provided service will act as 'client' and will open
        new client socket when sending
        :class:`~pynetdicom2.pdu.AAssociateRqPDU` instance.

        :param store_in_file: set of SOP Class UIDs, for which incoming dataset
                              should be stored in a file.
        :param get_file_cb: callback for getting a file to store incoming
                            dataset
        :param dul_socket: remote client socket that will be used to send and
                           receive PDUs.
        """
        super().__init__()

        self.primitive: Optional[fsm.PDUType] = None  # current pdu
        self.dimse_gen: Optional[Iterator[pdu.PDataTfPDU]] = None
        self.event: collections.deque[fsm.Events] = collections.deque()
        self.max_pdu_length = max_pdu_length

        self.to_service_user: fsm.IncomingQueue = queue.Queue()
        self.from_service_user: fsm.OutgoingQueue = queue.Queue()

        # Setup the timer and finite state machines
        self.timer = fsm.Timer(artim_timeout)
        self.state_machine = fsm.StateMachine(
            self, self.timer, store_in_file, get_file_cb
        )
        self._is_killed = threading.Event()
        self.called_presentation_address: Optional[tuple[str, int]] = None

        if dul_socket:  # A client socket has been given. Generate an event 5
            self.event.append(fsm.Events.EVT_5)
            self.is_acceptor = True
        else:
            self.is_acceptor = False

        self.dul_socket = dul_socket
        self.raw_pdu: bytes = b''

        self.is_killed: bool = False
        self.start()

    @property
    def accepted_contexts(self) -> dict[int, fsm.PContextDef]:
        """Accepted presentation contexts in the current association"""
        return self.state_machine.accepted_contexts

    @accepted_contexts.setter
    def accepted_contexts(self, value: dict[int, fsm.PContextDef]) -> None:
        self.state_machine.accepted_contexts = value

    def create_socket(self) -> None:
        """Creates a client socket and establishes a connection"""
        self.dul_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        if not self.called_presentation_address:
            raise exceptions.NetDICOMError(
                'Called presentation address is not set'
            )
        self.dul_socket.connect(self.called_presentation_address)

    def send(
            self,
            primitive: Union[Iterator[pdu.PDataTfPDU], fsm.PDUType]
    ) -> None:
        """Puts PDU into outgoing queue.

        .. note::

            PDU is not immediately written into the socket, but rather put into
            queue that is processed by the service event loop.

        :param primitive: outgoing PDU. Possible PDU types are described
                          in :doc:`pdu`
        """
        self.from_service_user.put(primitive)

    def receive(
            self,
            timeout: float
    ) -> Union[tuple[dimsemessages.DIMSEMessage, int], fsm.PDUType]:
        """Tries to get PDU from incoming queue.

        If timeout is exceeded method
        rises :class:`~pynetdicom2.exceptions.DCMTimeoutError` exception.

        :param timeout: the amount of seconds method waits for PDU to appear
                        in incoming queue
        :return: PDU instance or a tuple containing DIMSE Message and
                 Presentation Context ID. Possible PDU types are described
                 in :doc:`pdu`. Possible DIMSE messages are described
                 in :doc:`dimsemessages`.
        :raise exceptions.DCMTimeoutError: If specified timeout is exceeded
        """
        try:
            return self.to_service_user.get(timeout=timeout)
        except queue.Empty as exc:
            raise exceptions.DCMTimeoutError() from exc

    def stop(self) -> bool:
        """Tries to stop service for idle association.

        If association is not in idle state, method will return ``False`` and
        association will not be stopped.

        :return: ``True`` if service termination flag was successfully set
                 (current association state was 'idle'), ``False`` otherwise
        """
        if self.state_machine.current_state == fsm.States.STA_1:
            self.is_killed = True
            return True
        return False

    def kill(self) -> None:
        """Sets termination flag for event loop and waits for thread to exit.
        """
        self.is_killed = True
        self._is_killed.wait()

    def run(self) -> None:
        try:
            while not self.is_killed:
                (  # pylint: disable=expression-not-assigned
                    self._check_outgoing_pdu() or
                    self._check_network() or
                    self._check_timer()
                )
                try:
                    evt = self.event.popleft()
                except IndexError:
                    continue
                self.state_machine.action(evt)
        except Exception as exc:
            logger.exception('DUL failure: %s', exc)
            self.to_service_user.put(pdu.AAbortPDU(source=0, reason_diag=0))
            raise
        finally:
            self._is_killed.set()

    def _check_network(self) -> bool:
        if self.state_machine.current_state == fsm.States.STA_13:
            return self._close()

        if not self.dul_socket:
            return False

        if self.state_machine.current_state == fsm.States.STA_4:
            self.event.append(fsm.Events.EVT_2)
            return True

        if self.raw_pdu and self._process_incoming():
            return True

        # check if something comes in the client socket
        try:
            if select.select([self.dul_socket], [], [], 0.05)[0]:
                if self._check_incoming_pdu():
                    return True
        except ValueError:
            # Invalid socket state, nothing to select
            return False

        return self._process_incoming()

    def _queue_pdu_event(self, primitive: fsm.PDUType) -> None:
        """Maps a PDU to its FSM event and appends it to the event queue.

        :raises exceptions.PDUProcessingError: if the PDU type is unknown.
        """
        try:
            event = PDU_TO_EVENT[primitive.pdu_type]
        except KeyError as exc:
            raise exceptions.PDUProcessingError(
                f'Unknown PDU {primitive} with type {primitive.pdu_type}'
            ) from exc
        self.event.append(event)

    def _check_outgoing_pdu(self) -> bool:
        if self.dimse_gen:
            try:
                self.primitive = next(self.dimse_gen)
            except StopIteration:
                self.dimse_gen = None
            else:
                self._queue_pdu_event(self.primitive)
                return True

        try:
            incoming = self.from_service_user.get(block=False)
        except queue.Empty:
            return False

        if isinstance(incoming, Iterator):
            self.dimse_gen = incoming
            self.primitive = next(self.dimse_gen)
        else:
            self.primitive = incoming
        self._queue_pdu_event(self.primitive)
        return True

    def _check_timer(self) -> bool:
        if self.timer.check() is False:
            self.event.append(fsm.Events.EVT_18)  # Timer expired
            return True
        return False

    def _check_incoming_pdu(self) -> bool:
        # There is something to read
        if not self.dul_socket:
            return True

        try:
            data = self.dul_socket.recv(self.max_pdu_length)
        except socket.error as exc:
            logger.exception('DUL socket failure: %s', exc)
            self.event.append(fsm.Events.EVT_17)
            self.dul_socket.close()
            self.dul_socket = None
            return True

        if not data:
            # Remote port has been closed
            self.event.append(fsm.Events.EVT_17)
            self.dul_socket.close()
            self.dul_socket = None
            return True

        self.raw_pdu += data
        return False

    def _process_incoming(self) -> bool:
        if len(self.raw_pdu) < 6:
            return False

        length = self.raw_pdu[2:6]
        _length = struct.unpack('>L', length)[0]
        full_length = _length + 6
        if len(self.raw_pdu) < full_length:
            return False

        raw_pdu = self.raw_pdu[:full_length]
        self.raw_pdu = self.raw_pdu[full_length:]

        # Determine the type of PDU coming on remote port and set the event
        # accordingly
        try:
            pdu_type, event = PDU_TYPES[raw_pdu[0]]
            self.primitive = pdu_type.decode(raw_pdu)
            self.event.append(event)
        except KeyError:
            self.event.append(fsm.Events.EVT_19)
        return True

    def _close(self) -> bool:
        # waiting for connection to close
        if self.dul_socket is None:
            return False

        # Wait for the remote connection to close, but never block the DUL
        # thread forever: a bounded timeout is applied so a half-open or
        # misbehaving peer that never closes its side cannot hang the provider.
        previous_timeout = self.dul_socket.gettimeout()
        try:
            self.dul_socket.settimeout(CLOSE_TIMEOUT)
            while self.dul_socket.recv(1) != b'':
                continue
        except (socket.timeout, socket.error):
            # Timed out or the socket errored out: treat as "peer did not
            # cleanly close" and fall through to close it ourselves.
            pass
        finally:
            try:
                self.dul_socket.settimeout(previous_timeout)
            except socket.error:
                pass

        self.dul_socket.close()
        self.dul_socket = None
        self.event.append(fsm.Events.EVT_17)
        return True
