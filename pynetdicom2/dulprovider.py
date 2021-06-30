# Copyright (c) 2021 Pavel 'Blane' Tuchin
# Copyright (c) 2012 Patrice Munger
# This file is part of pynetdicom, released under a modified MIT license.
#    See the file license.txt included with this distribution, also
#    available at http://pynetdicom.googlecode.com
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

from __future__ import absolute_import

import collections

import threading
from typing import FrozenSet  # pylint: disable=unused-import
import time
import socket
import select
import struct

import six
from six.moves import queue  # type: ignore

from . import fsm
from . import pdu
from . import exceptions


PDU_TYPES = {
    0x01: (pdu.AAssociateRqPDU, fsm.Events.EVT_6),
    0x02: (pdu.AAssociateAcPDU, fsm.Events.EVT_3),
    0x03: (pdu.AAssociateRjPDU, fsm.Events.EVT_4),
    0x04: (pdu.PDataTfPDU, fsm.Events.EVT_10),
    0x05: (pdu.AReleaseRqPDU, fsm.Events.EVT_12),
    0x06: (pdu.AReleaseRpPDU, fsm.Events.EVT_13),
    0x07: (pdu.AAbortPDU, fsm.Events.EVT_16)
}

PDU_TO_EVENT = {
    pdu.AAssociateRqPDU.pdu_type: fsm.Events.EVT_1,  # A-ASSOCIATE Request
    pdu.AAssociateAcPDU.pdu_type: fsm.Events.EVT_7,  # A-ASSOCIATE Response (accept)
    pdu.AAssociateRjPDU.pdu_type: fsm.Events.EVT_8,  # A-ASSOCIATE Response (reject)
    pdu.AReleaseRqPDU.pdu_type: fsm.Events.EVT_11,   # A-Release Request
    pdu.AReleaseRpPDU.pdu_type: fsm.Events.EVT_14,   # A-Release Response
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

    Underlying implementation relies on state machine that is defined in :doc:`fsm`

    :ivar primitive: current PDU
    :ivar dimse_gen: generator, used break current outgoing DIMSE message into P-DATA-TF PDUs
    :ivar event: current event
    :ivar max_pdu_length: maximum PDU length for incoming P-DATA-TF PDUs
    :ivar to_service_user: outgoing data queue
    :ivar from_service_user: incoming data queue
    :ivar dul_socket: socket, that service uses
    :ivar is_killed: DUL service termination flag
    """

    def __init__(
            self,
            store_in_file,  # type: FrozenSet[str]
            get_file_cb,
            dul_socket=None,  # type: socket.socket
            max_pdu_length=65536  # type: int
        ):
        """Initializes DUL service.

        If no socket is provided service will act as 'client' and will open
        new client socket when sending :class:`~pynetdicom2.pdu.AAssociateRqPDU`
        instance.

        :param store_in_file: set of SOP Class UIDs, for which incoming dataset should be stored
                              in a file.
        :param get_file_cb: callback for getting a file to store incoming dataset
        :param dul_socket: remote client socket that will be used to send and
                           receive PDUs.
        """
        super(DULServiceProvider, self).__init__()

        self.primitive = None  # current pdu
        self.dimse_gen = None
        self.event = collections.deque()
        self.max_pdu_length = max_pdu_length

        self.to_service_user = queue.Queue()
        self.from_service_user = queue.Queue()

        # Setup the timer and finite state machines
        self.timer = Timer(10)
        self.state_machine = fsm.StateMachine(self, self.timer, store_in_file, get_file_cb)
        self._is_killed = threading.Event()

        if dul_socket:  # A client socket has been given. Generate an event 5
            self.event.append(fsm.Events.EVT_5)

        self.dul_socket = dul_socket
        self.raw_pdu = b''

        self.is_killed = False
        self.start()

    @property
    def accepted_contexts(self):
        """Accepted presentation contexts in the current association"""
        return self.state_machine.accepted_contexts

    @accepted_contexts.setter
    def accepted_contexts(self, value):
        self.state_machine.accepted_contexts = value

    def send(self, primitive):
        """Puts PDU into outgoing queue.

        .. note::

            PDU is not immediately written into the socket, but rather put into
            queue that is processed by the service event loop.

        :param primitive: outgoing PDU. Possible PDU types are described in :doc:`pdu`
        """
        self.from_service_user.put(primitive)

    def receive(self, timeout):
        """Tries to get PDU from incoming queue.

        If timeout is exceeded method
        rises :class:`~pynetdicom2.exceptions.DCMTimeoutError` exception.

        :param timeout: the amount of seconds method waits for PDU to appear in incoming queue
        :return: PDU instance or a tuple containing DIMSE Message and Presentation Context ID.
                 Possible PDU types are described in :doc:`pdu`. Possible DIMSE messages are
                 described in :doc:`dimsemessages`.
        :raise exceptions.DCMTimeoutError: If specified timeout is exceeded
        """
        try:
            return self.to_service_user.get(timeout=timeout)
        except queue.Empty:
            raise exceptions.DCMTimeoutError()

    def stop(self):
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

    def kill(self):
        """Sets termination flag for event loop and waits for thread to exit."""
        self.is_killed = True
        self._is_killed.wait()

    def run(self):
        try:
            while not self.is_killed:
                self._check_network() or self._check_outgoing_pdu() or self._check_timer()  # pylint: disable=expression-not-assigned
                try:
                    evt = self.event.popleft()
                except IndexError:
                    continue
                self.state_machine.action(evt)
        except Exception:
            self.to_service_user.put(pdu.AAbortPDU(source=0, reason_diag=0))
            raise
        finally:
            self._is_killed.set()

    def _check_network(self):
        if self.state_machine.current_state == fsm.States.STA_13:
            return self._close()

        if not self.dul_socket:
            return False

        if self.state_machine.current_state == fsm.States.STA_4:
            self.event.append(fsm.Events.EVT_2)
            return True

        # check if something comes in the client socket
        if select.select([self.dul_socket], [], [], 0.05)[0]:
            if self._check_incoming_pdu():
                return True

        return self._process_incoming()

    def _check_outgoing_pdu(self):
        try:
            if self.dimse_gen:
                try:
                    self.primitive = next(self.dimse_gen)
                    self.event.append(PDU_TO_EVENT[self.primitive.pdu_type])
                    return True
                except StopIteration:
                    self.dimse_gen = None
            incoming = self.from_service_user.get(False, None)
            if hasattr(incoming, 'pdu_type'):
                self.primitive = incoming
            else:
                self.dimse_gen = incoming
                self.primitive = next(self.dimse_gen)
            self.event.append(PDU_TO_EVENT[self.primitive.pdu_type])
            return True
        except KeyError:
            raise exceptions.PDUProcessingError(
                'Unknown PDU {0} with type {1}'.format(self.primitive, self.primitive.pdu_type)
            )
        except queue.Empty:
            return False

    def _check_timer(self):
        if self.timer.check() is False:
            self.event.append(fsm.Events.EVT_18)  # Timer expired
            return True
        return False

    def _check_incoming_pdu(self):
        # type: () -> bool
        # There is something to read
        try:
            data = self.dul_socket.recv(self.max_pdu_length)
        except socket.error:
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

    def _process_incoming(self):
        if len(self.raw_pdu) < 6:
            return False

        length = self.raw_pdu[2:6]
        length = struct.unpack('>L', length)[0]
        full_length = length + 6
        if len(self.raw_pdu) < full_length:
            return False

        raw_pdu = self.raw_pdu[:full_length]
        self.raw_pdu = self.raw_pdu[full_length:]

        # Determine the type of PDU coming on remote port and set the event accordingly
        try:
            pdu_type, event = PDU_TYPES[six.indexbytes(raw_pdu, 0)]
            self.primitive = pdu_type.decode(raw_pdu)
            self.event.append(event)
        except KeyError:
            self.event.append(fsm.Events.EVT_19)
        return True

    def _close(self):
        # waiting for connection to close
        if self.dul_socket is None:
            return False

        # wait for remote connection to close
        try:
            while self.dul_socket.recv(1) != b'':
                continue
        except socket.error:
            return False

        self.dul_socket.close()
        self.dul_socket = None
        self.event.append(fsm.Events.EVT_17)
        return True


class Timer(object):
    """A small helper timer class"""

    def __init__(self, max_seconds):
        # type: (int) -> None
        self._max_seconds = max_seconds
        self._start_time = None

    def start(self):
        """Sets a timer"""
        self._start_time = time.time()

    def stop(self):
        """Stops a timer"""
        self._start_time = None

    def restart(self):
        """Restarts a timer"""
        self.stop()
        self.start()

    def check(self):
        # type: () -> bool
        """Checks if timer has expired"""
        if self._start_time and (time.time() - self._start_time > self._max_seconds):
            return False
        return True
