# Copyright (c) 2014 Pavel 'Blane' Tuchin
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
:class:`~netdicom2.dulprovider.DULServiceProvider` directly, but rather would
use higher level objects like sub-classes of
:class:`~netdicom2.asceprovider.Association` or various services.
"""

from __future__ import absolute_import

import collections

import threading
import socket
import select
import struct

import six
from six.moves import queue

from . import timer
from . import fsm
from . import pdu
from . import exceptions


def _recv_n(sock, n):
    ret = []
    read_length = 0
    while read_length < n:
        tmp = sock.recv(n - read_length)
        ret.append(tmp)
        read_length += len(tmp)
    if read_length != n:
        raise exceptions.NetDICOMError('Low level network error')
    return b''.join(ret)


PDU_TYPES = {
    0x01: (pdu.AAssociateRqPDU, 'Evt6'),
    0x02: (pdu.AAssociateAcPDU, 'Evt3'),
    0x03: (pdu.AAssociateRjPDU, 'Evt4'),
    0x04: (pdu.PDataTfPDU, 'Evt10'),
    0x05: (pdu.AReleaseRqPDU, 'Evt12'),
    0x06: (pdu.AReleaseRpPDU, 'Evt13'),
    0x07: (pdu.AAbortPDU, 'Evt16')
}

PDU_TO_EVENT = {
    pdu.AAssociateRqPDU.pdu_type: 'Evt1',  # A-ASSOCIATE Request
    pdu.AAssociateAcPDU.pdu_type: 'Evt7',  # A-ASSOCIATE Response (accept)
    pdu.AAssociateRjPDU.pdu_type: 'Evt8',  # A-ASSOCIATE Response (reject)
    pdu.AReleaseRqPDU.pdu_type: 'Evt11',   # A-Release Request
    pdu.AReleaseRpPDU.pdu_type: 'Evt14',   # A-Release Response
    pdu.AAbortPDU.pdu_type: 'Evt15',
    pdu.PDataTfPDU.pdu_type: 'Evt9'
}


class DULServiceProvider(threading.Thread):
    """Implements DUL service.

    This class is responsible for low-level operations with incoming and
    outgoing PDUs.

    Service can be initialized by providing open socket that service would
    use for sending and receiving PDUs. In case if socket is not provider
    service opens a client socket by itself when sending
    :class:`~netdicom2.pdu.AAssociateRqPDU` instance.

    Underlying implementation relies on state machine that is defined in :doc:`fsm`

    """

    def __init__(self, dul_socket=None):
        """Initializes DUL service.

        If no socket is provided service will act as 'client' and will open
        new client socket when sending :class:`~netdicom2.pdu.AAssociateRqPDU`
        instance.

        :param dul_socket: remote client socket that will be used to send and
                           receive PDUs.
        """
        super(DULServiceProvider, self).__init__()

        self.primitive = None  # current pdu
        self.event = collections.deque()

        self.to_service_user = queue.Queue()
        self.from_service_user = queue.Queue()

        # Setup the timer and finite state machines
        self.timer = timer.Timer(10)
        self.state_machine = fsm.StateMachine(self)
        self._is_killed = threading.Event()

        if dul_socket:  # A client socket has been given. Generate an event 5
            self.event.append('Evt5')

        self.dul_socket = dul_socket

        self.is_killed = False
        self.start()

    def send(self, primitive):
        """Puts PDU into outgoing queue.

        .. note::

            PDU is not immediately written into the socket, but rather put into
            queue that is processed by service event loop.

        :param primitive: outgoing PDU. Possible PDU types are described
                          in :doc:`pdu`
        """
        self.from_service_user.put(primitive)

    def receive(self, timeout):
        """Tries to get PDU from incoming queue.

        If timeout is exceeded method
        rises :class:`~netdicom2.exceptions.TimeoutError` exception.

        :param timeout: the amount of seconds method waits for PDU to appear
                        in incoming queue
        :return: PDU instance. Possible PDU types are described
                 in :doc:`pdu`
        :raise exceptions.TimeoutError: If specified timeout is exceeded
        """
        try:
            return self.to_service_user.get(timeout=timeout)
        except queue.Empty:
            raise exceptions.TimeoutError()

    def stop(self):
        """Tries to stop service for idle association.

        If association is not in idle state, method will return ``False`` and
        association will not be stopped.

        :return: ``True`` if service termination flag was successfully set
                 (current association state was 'idle'), ``False`` otherwise
        """
        if self.state_machine.current_state == 'Sta1':
            self.is_killed = True
            return True
        else:
            return False

    def kill(self):
        """Sets termination flag for event loop and waits for thread to exit."""
        self.is_killed = True
        self._is_killed.wait()

    def run(self):
        try:
            while not self.is_killed:
                self._check_network() or self._check_outgoing_pdu() or\
                    self._check_timer()
                try:
                    evt = self.event.popleft()
                except IndexError:
                    continue
                self.state_machine.action(evt, self)
        except Exception:
            self.to_service_user.put(pdu.AAbortPDU(source=0, reason_diag=0))
            raise
        finally:
            self._is_killed.set()

    def _check_network(self):
        if self.state_machine.current_state == 'Sta13':
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
            self.event.append('Evt17')
            return True

        if not self.dul_socket:
            return False

        if self.state_machine.current_state == 'Sta4':
            self.event.append('Evt2')
            return True

        # check if something comes in the client socket
        if select.select([self.dul_socket], [], [], 0.05)[0]:
            self._check_incoming_pdu()
            return True
        else:
            return False

    def _check_outgoing_pdu(self):
        try:
            self.primitive = self.from_service_user.get(False, None)
            self.event.append(PDU_TO_EVENT[self.primitive.pdu_type])
            return True
        except KeyError:
            raise exceptions.PDUProcessingError(
                'Unknown PDU {0} with type {1}'.format(self.primitive,
                                                       self.primitive.pdu_type))
        except queue.Empty:
            return False

    def _check_timer(self):
        if self.timer.check() is False:
            self.event.append('Evt18')  # Timer expired
            return True
        else:
            return False

    def _check_incoming_pdu(self):
        # There is something to read
        try:
            raw_pdu = self.dul_socket.recv(1)
        except socket.error:
            self.event.append('Evt17')
            self.dul_socket.close()
            self.dul_socket = None
            return

        if raw_pdu == b'':
            # Remote port has been closed
            self.event.append('Evt17')
            self.dul_socket.close()
            self.dul_socket = None
            return
        else:
            res = _recv_n(self.dul_socket, 1)
            raw_pdu += res
            length = _recv_n(self.dul_socket, 4)
            raw_pdu += length
            length = struct.unpack('>L', length)
            tmp = _recv_n(self.dul_socket, length[0])
            raw_pdu += tmp

            # Determine the type of PDU coming on remote port and set the event
            # accordingly
            try:
                pdu_type, event = PDU_TYPES[six.indexbytes(raw_pdu, 0)]
                self.primitive = pdu_type.decode(raw_pdu)
                self.event.append(event)
            except KeyError:
                self.event.append('Evt19')
