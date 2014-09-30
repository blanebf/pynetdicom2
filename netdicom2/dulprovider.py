# Copyright (c) 2014 Pavel 'Blane' Tuchin
# Copyright (c) 2012 Patrice Munger
# This file is part of pynetdicom, released under a modified MIT license.
#    See the file license.txt included with this distribution, also
#    available at http://pynetdicom.googlecode.com
#

"""
This module implements the DUL service provider, allowing a DUL service user to
send and receive DUL messages.  The User and Provider talk to each other using
a TCP socket. The DULServer runs in a thread, so that and implements an event
loop whose events will drive the state machine.
"""

import collections

import threading
import socket
import time
import select
import Queue
import struct

import netdicom2.timer as timer
import netdicom2.fsm as fsm
import netdicom2.pdu as pdu
import netdicom2.exceptions as exceptions


def recv_n(sock, n):
    ret = []
    read_length = 0
    while read_length < n:
        tmp = sock.recv(n - read_length)
        ret.append(tmp)
        read_length += len(tmp)
    if read_length != n:
        raise exceptions.NetDICOMError('Low level network error')
    return ''.join(ret)


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
    def __init__(self, dul_socket=None):
        """
        Three ways to call DULServiceProvider. If a port number is given,
        the DUL will wait for incoming connections on this port. If a socket
        is given, the DUL will use this socket as the client socket. If none
        is given, the DUL will not be able to accept connections (but will
        be able to initiate them.)
        """
        super(DULServiceProvider, self).__init__()

        self.primitive = None  # current pdu
        self.event = collections.deque()

        self.to_service_user = Queue.Queue()
        self.from_service_user = Queue.Queue()

        # Setup the timer and finite state machines
        self.timer = timer.Timer(10)
        self.state_machine = fsm.StateMachine(self)
        self._is_killed = threading.Event()

        if dul_socket:  # A client socket has been given. Generate an event 5
            self.event.append('Evt5')

        self.dul_socket = dul_socket

        self.is_killed = False
        self.start()

    def kill(self):
        """Immediately interrupts the thread"""
        self.is_killed = True
        self._is_killed.wait()

    def stop(self):
        """Interrupts the thread if state is "Sta1" """
        if self.state_machine.current_state == 'Sta1':
            self.is_killed = True
            return True
        else:
            return False

    def send(self, primitive):
        self.from_service_user.put(primitive)

    def receive(self, wait=False, timeout=None):
        # if not self.dul_socket: return None
        try:
            tmp = self.to_service_user.get(wait, timeout)
            return tmp
        except Queue.Empty:
            return None

    def check_incoming_pdu(self):
        # There is something to read
        try:
            raw_pdu = self.dul_socket.recv(1)
        except socket.error:
            self.event.append('Evt17')
            self.dul_socket.close()
            self.dul_socket = None
            return

        if raw_pdu == '':
            # Remote port has been closed
            self.event.append('Evt17')
            self.dul_socket.close()
            self.dul_socket = None
            return
        else:
            res = recv_n(self.dul_socket, 1)
            raw_pdu += res
            length = recv_n(self.dul_socket, 4)
            raw_pdu += length
            length = struct.unpack('>L', length)
            tmp = recv_n(self.dul_socket, length[0])
            raw_pdu += tmp

            # Determine the type of PDU coming on remote port and set the event
            # accordingly
            try:
                pdu_type, event = PDU_TYPES[struct.unpack('B', raw_pdu[0])[0]]
                self.primitive = pdu_type.decode(raw_pdu)
                self.event.append(event)
            except KeyError:
                self.event.append('Evt19')

    def check_timer(self):
        if self.timer.check() is False:
            self.event.append('Evt18')  # Timer expired
            return True
        else:
            return False

    def check_incoming_primitive(self):
        try:
            self.primitive = self.from_service_user.get(False, None)
            self.event.append(PDU_TO_EVENT[self.primitive.pdu_type])
            return True
        except KeyError:
            raise exceptions.PDUProcessingError(
                'Unknown PDU {0} with type {1}'.format(self.primitive,
                                                       self.primitive.pdu_type))
        except Queue.Empty:
            return False

    def check_network(self):
        if self.state_machine.current_state == 'Sta13':
            # wainting for connection to close
            if self.dul_socket is None:
                return False

            # wait for remote connection to close
            try:
                while self.dul_socket.recv(1) != '':
                    continue
            except socket.error:
                return False

            self.dul_socket.close()
            self.dul_socket = None
            self.event.append('Evt17')
            return True

        if self.dul_socket:
            if self.state_machine.current_state == 'Sta4':
                self.event.append('Evt2')
                return True

            # check if something comes in the client socket
            if select.select([self.dul_socket], [], [], 0)[0]:
                self.check_incoming_pdu()
                return True
        else:
            return False

    def run(self):
        try:
            while not self.is_killed:
                time.sleep(0.001)
                # catch an event
                self.check_network() or self.check_incoming_primitive() or\
                    self.check_timer()
                try:
                    evt = self.event.popleft()
                except IndexError:
                    continue
                self.state_machine.action(evt, self)
        except Exception:
            self.event.append(pdu.AAbortPDU(source=0, reason_diag=0))
            raise
        finally:
            self._is_killed.set()
