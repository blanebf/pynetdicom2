"""Unit tests for :mod:`pynetdicom2.dulprovider`.

These tests avoid real network associations by exercising the provider's
socket-handling helpers in isolation. ``DULServiceProvider.__init__`` starts a
background thread, so the tests build a bare instance with
``object.__new__`` and populate only the attributes required by the method
under test.
"""
import collections
import queue
import socket
import struct
import threading
import time
import unittest
from unittest import mock

from pynetdicom2 import dulprovider
from pynetdicom2 import exceptions
from pynetdicom2 import fsm
from pynetdicom2 import pdu


def _make_bare_provider() -> dulprovider.DULServiceProvider:
    """Creates a provider instance without starting its worker thread."""
    provider = object.__new__(dulprovider.DULServiceProvider)
    provider.event = collections.deque()
    provider.dul_socket = None
    provider.raw_pdu = b''
    provider.primitive = None
    provider.dimse_gen = None
    provider.max_pdu_length = 65536
    provider._close_deadline = None
    return provider


class CloseTimeoutTestCase(unittest.TestCase):
    def setUp(self) -> None:
        # Keep the real value so a bug in the test cannot slow the whole suite.
        self._original = dulprovider.CLOSE_TIMEOUT
        dulprovider.CLOSE_TIMEOUT = 0.2
        self.addCleanup(self._restore)

    def _restore(self) -> None:
        dulprovider.CLOSE_TIMEOUT = self._original

    def test_close_returns_when_peer_never_closes(self) -> None:
        # The peer keeps its side open and never sends EOF. _close must not
        # block forever: one non-blocking step is performed per call, and
        # after CLOSE_TIMEOUT elapses the socket is closed and EVT_17 is
        # emitted.
        left, right = socket.socketpair()
        self.addCleanup(right.close)
        provider = _make_bare_provider()
        provider.dul_socket = left

        start = time.monotonic()
        while not provider._close():
            pass
        elapsed = time.monotonic() - start

        self.assertLess(elapsed, 5, 'close() blocked far longer than timeout')
        self.assertIsNone(provider.dul_socket)
        self.assertIn(fsm.Events.EVT_17, provider.event)

    def test_close_steps_are_non_blocking(self) -> None:
        # A single _close call must not block for the whole CLOSE_TIMEOUT
        # while the peer keeps its side open: it performs one short step.
        left, right = socket.socketpair()
        self.addCleanup(right.close)
        provider = _make_bare_provider()
        provider.dul_socket = left

        start = time.monotonic()
        result = provider._close()
        elapsed = time.monotonic() - start

        self.assertFalse(result)
        self.assertLess(
            elapsed, dulprovider.POLL_INTERVAL * 4,
            'a single _close() step blocked far longer than POLL_INTERVAL'
        )

    def test_close_processes_remaining_pdus(self) -> None:
        # Bytes still in flight when the association enters STA_13 may
        # contain complete PDUs: they must be processed, not discarded.
        left, right = socket.socketpair()
        self.addCleanup(right.close)
        provider = _make_bare_provider()
        provider.dul_socket = left
        right.sendall(pdu.AAbortPDU(source=0, reason_diag=0).encode())

        self.assertTrue(provider._close())
        self.assertIn(fsm.Events.EVT_16, provider.event)
        # Socket is still open: the provider keeps waiting for the peer.
        self.assertIsNotNone(provider.dul_socket)

        right.close()
        while not provider._close():
            pass
        self.assertIsNone(provider.dul_socket)
        self.assertIn(fsm.Events.EVT_17, provider.event)

    def test_close_when_peer_closes(self) -> None:
        left, right = socket.socketpair()
        provider = _make_bare_provider()
        provider.dul_socket = left
        right.close()  # peer closes immediately -> recv returns b''

        result = provider._close()

        self.assertTrue(result)
        self.assertIsNone(provider.dul_socket)
        self.assertIn(fsm.Events.EVT_17, provider.event)

    def test_close_without_socket(self) -> None:
        provider = _make_bare_provider()
        provider.dul_socket = None
        self.assertFalse(provider._close())


class PduDispatchTestCase(unittest.TestCase):
    def test_known_pdu_types_mapped_to_events(self) -> None:
        # Every PDU type byte maps to a decoder class and an FSM event.
        self.assertEqual(
            dulprovider.PDU_TYPES[0x01][0], pdu.AAssociateRqPDU
        )
        self.assertEqual(dulprovider.PDU_TYPES[0x04][0], pdu.PDataTfPDU)

    def test_process_incoming_unknown_pdu_maps_to_evt_19(self) -> None:
        provider = _make_bare_provider()
        # 0x99 is not a known PDU type byte.
        provider.raw_pdu = b'\x99\x00\x00\x00\x00\x00'
        result = provider._process_incoming()
        self.assertTrue(result)
        self.assertIn(fsm.Events.EVT_19, provider.event)

    def test_process_incoming_malformed_pdu_maps_to_evt_19(self) -> None:
        provider = _make_bare_provider()
        # A-ASSOCIATE-RQ (type 0x01) declaring a 4-byte body while the fixed
        # header alone is 68 bytes: decoding raises struct.error, which must
        # be reported as EVT_19 instead of crashing the DUL thread.
        provider.raw_pdu = b'\x01\x00\x00\x00\x00\x04\x00\x00\x00\x00'
        result = provider._process_incoming()
        self.assertTrue(result)
        self.assertIn(fsm.Events.EVT_19, provider.event)


class PduLengthCapTestCase(unittest.TestCase):
    """A peer must never be able to make the provider buffer an unbounded
    amount of data by declaring an absurd PDU length."""

    def _pdu_header(self, pdu_type: int, length: int) -> bytes:
        return bytes([pdu_type, 0x00]) + struct.pack('>L', length)

    def test_data_pdu_over_max_length_aborts(self) -> None:
        provider = _make_bare_provider()
        provider.max_pdu_length = 100
        # P-DATA-TF (0x04) declaring 101 bytes, over the negotiated max.
        provider.raw_pdu = self._pdu_header(0x04, 101) + b'\x00' * 101
        result = provider._process_incoming()
        self.assertTrue(result)
        self.assertIn(fsm.Events.EVT_19, provider.event)
        self.assertEqual(provider.raw_pdu, b'')

    def test_association_pdu_over_fixed_cap_aborts(self) -> None:
        provider = _make_bare_provider()
        cap = dulprovider.MAX_ASSOCIATION_PDU_LENGTH
        # A-ASSOCIATE-RQ (0x01) declaring over the fixed association cap.
        provider.raw_pdu = self._pdu_header(0x01, cap + 1)
        result = provider._process_incoming()
        self.assertTrue(result)
        self.assertIn(fsm.Events.EVT_19, provider.event)
        self.assertEqual(provider.raw_pdu, b'')

    def test_pdu_within_limits_not_aborted(self) -> None:
        provider = _make_bare_provider()
        provider.max_pdu_length = 100
        # Declares a length within the cap but provides only the header so
        # far: provider must keep waiting for the rest, not abort.
        provider.raw_pdu = self._pdu_header(0x04, 100)
        result = provider._process_incoming()
        self.assertFalse(result)
        self.assertNotIn(fsm.Events.EVT_19, provider.event)


class CheckNetworkPacingTestCase(unittest.TestCase):
    """While no socket exists (client mode before connect, or after the
    connection has been torn down) the event loop must not busy-spin at 100%
    CPU."""

    def test_check_network_paces_when_no_socket(self) -> None:
        provider = _make_bare_provider()
        provider.dul_socket = None
        with mock.patch.object(dulprovider.time, 'sleep') as sleep_mock:
            result = provider._check_network()
        self.assertFalse(result)
        sleep_mock.assert_called_once_with(dulprovider.POLL_INTERVAL)


class RunFailureTestCase(unittest.TestCase):
    def test_run_reports_provider_origin_abort_on_failure(self) -> None:
        # An internal DUL failure is a DICOM UL service-provider initiated
        # abort (source 2), not a service-user one (source 0).
        provider = _make_bare_provider()
        provider.is_killed = False
        provider._is_killed = threading.Event()
        provider.to_service_user = queue.Queue()
        # Bypass the event-loop helpers so the only thing that can raise is
        # the state machine action.
        provider._check_outgoing_pdu = lambda: False
        provider._check_network = lambda: False
        provider._check_timer = lambda: False
        provider.state_machine = mock.MagicMock()
        provider.state_machine.action.side_effect = RuntimeError('boom')
        provider.event.append(fsm.Events.EVT_5)

        with self.assertRaises(RuntimeError):
            provider.run()

        abort = provider.to_service_user.get_nowait()
        self.assertIsInstance(abort, pdu.AAbortPDU)
        self.assertEqual(abort.source, 2)
        self.assertTrue(provider._is_killed.is_set())


class KillTimeoutTestCase(unittest.TestCase):
    """``kill()`` must not block forever if the DUL thread is stuck on a
    stalled peer."""

    def test_kill_returns_when_thread_terminates(self) -> None:
        provider = _make_bare_provider()
        provider.is_killed = False
        provider._is_killed = threading.Event()
        provider._is_killed.set()  # thread has already terminated
        provider.kill()
        self.assertTrue(provider.is_killed)

    def test_kill_does_not_block_past_timeout(self) -> None:
        provider = _make_bare_provider()
        provider.is_killed = False
        # Event never set: simulates a thread stuck on a stalled peer.
        provider._is_killed = threading.Event()
        start = time.monotonic()
        with mock.patch.object(dulprovider, 'KILL_TIMEOUT', 0.2):
            provider.kill()
        elapsed = time.monotonic() - start
        self.assertLess(elapsed, 1.0)
        self.assertTrue(provider.is_killed)


class CreateSocketTestCase(unittest.TestCase):
    def test_create_socket_uses_bounded_connect(self) -> None:
        # The client socket must be created with a bounded connect timeout
        # so a stalled remote host cannot block forever.
        provider = _make_bare_provider()
        provider.called_presentation_address = ('localhost', 11112)
        fake_socket = mock.MagicMock()
        with mock.patch.object(
            dulprovider.socket, 'create_connection',
            return_value=fake_socket
        ) as connect_mock:
            provider.create_socket()
        connect_mock.assert_called_once_with(
            ('localhost', 11112), timeout=dulprovider.SOCKET_TIMEOUT
        )
        self.assertIs(provider.dul_socket, fake_socket)

    def test_create_socket_without_address_raises(self) -> None:
        provider = _make_bare_provider()
        provider.called_presentation_address = None
        with self.assertRaises(exceptions.NetDICOMError):
            provider.create_socket()

    def test_create_socket_wraps_connect_errors(self) -> None:
        # A failed connection attempt must not leak a socket and must
        # surface as NetDICOMError.
        provider = _make_bare_provider()
        provider.called_presentation_address = ('localhost', 11112)
        with mock.patch.object(
            dulprovider.socket, 'create_connection',
            side_effect=ConnectionRefusedError('refused')
        ):
            with self.assertRaises(exceptions.NetDICOMError):
                provider.create_socket()

    def test_init_sets_timeout_on_provided_socket(self) -> None:
        # A socket handed to the provider (acceptor path) must also carry a
        # bounded timeout.
        left, right = socket.socketpair()
        try:
            provider = dulprovider.DULServiceProvider(
                set(), lambda ctx, ds: (None, 0), dul_socket=left
            )
            try:
                self.assertEqual(left.gettimeout(), dulprovider.SOCKET_TIMEOUT)
            finally:
                provider.kill()
        finally:
            left.close()
            right.close()

    def test_provider_thread_is_daemon(self) -> None:
        # The DUL thread is started in the constructor and can leak if the
        # enclosing object fails to finish initializing; as a daemon it
        # cannot block interpreter shutdown.
        left, right = socket.socketpair()
        try:
            provider = dulprovider.DULServiceProvider(
                set(), lambda ctx, ds: (None, 0), dul_socket=left
            )
            try:
                self.assertTrue(provider.daemon)
            finally:
                provider.kill()
        finally:
            left.close()
            right.close()


if __name__ == '__main__':
    unittest.main()
