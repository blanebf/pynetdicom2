"""Unit tests for :mod:`pynetdicom2.dulprovider`.

These tests avoid real network associations by exercising the provider's
socket-handling helpers in isolation. ``DULServiceProvider.__init__`` starts a
background thread, so the tests build a bare instance with
``object.__new__`` and populate only the attributes required by the method
under test.
"""
import collections
import socket
import time
import unittest

from pynetdicom2 import dulprovider
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
        # block forever: it should time out, close the socket and emit EVT_17.
        left, right = socket.socketpair()
        self.addCleanup(right.close)
        provider = _make_bare_provider()
        provider.dul_socket = left

        start = time.monotonic()
        result = provider._close()
        elapsed = time.monotonic() - start

        self.assertTrue(result)
        self.assertLess(elapsed, 5, 'close() blocked far longer than timeout')
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


if __name__ == '__main__':
    unittest.main()
