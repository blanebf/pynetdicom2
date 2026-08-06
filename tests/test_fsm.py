"""Unit tests for :mod:`pynetdicom2.fsm` state machine and timer."""
import queue
import time
import unittest
from typing import Any, Optional

from pynetdicom2 import fsm
from pynetdicom2 import pdu


class FakeSocket:
    def __init__(self) -> None:
        self.sent: list[bytes] = []
        self.closed = False

    def sendall(self, data: bytes) -> None:
        self.sent.append(data)

    def close(self) -> None:
        self.closed = True


class FakeProvider:
    """Minimal stand-in for the DUL provider used by the state machine."""

    def __init__(self, is_acceptor: bool = False) -> None:
        self.primitive: Optional[Any] = None
        self.dul_socket: Any = FakeSocket()
        self.to_service_user: queue.Queue = queue.Queue()
        self.is_acceptor = is_acceptor

    def create_socket(self) -> None:
        self.dul_socket = FakeSocket()


def _make_sm(is_acceptor: bool = False) -> fsm.StateMachine:
    provider = FakeProvider(is_acceptor)
    timer = fsm.Timer(10)
    return fsm.StateMachine(provider, timer, set(), lambda ctx, ds: (None, 0))


class TimerTestCase(unittest.TestCase):
    def test_not_expired_before_timeout(self) -> None:
        timer = fsm.Timer(10)
        timer.start()
        self.assertTrue(timer.check())

    def test_expired_after_timeout(self) -> None:
        timer = fsm.Timer(0)
        timer.start()
        time.sleep(0.01)
        # check() returns False when the timer has expired.
        self.assertFalse(timer.check())

    def test_stopped_timer_is_not_expired(self) -> None:
        timer = fsm.Timer(0)
        timer.start()
        timer.stop()
        self.assertTrue(timer.check())


class StateMachineDispatchTestCase(unittest.TestCase):
    def test_initial_state(self) -> None:
        sm = _make_sm()
        self.assertEqual(sm.current_state, fsm.States.STA_1)

    def test_evt5_starts_timer_and_moves_to_sta2(self) -> None:
        sm = _make_sm()
        sm.action(fsm.Events.EVT_5)
        self.assertEqual(sm.current_state, fsm.States.STA_2)

    def test_unknown_transition_raises_keyerror(self) -> None:
        sm = _make_sm()
        # EVT_9 has no mapping from STA_1.
        with self.assertRaises(KeyError):
            sm.action(fsm.Events.EVT_9)


class ReleaseCollisionTestCase(unittest.TestCase):
    """`ar_8` picks the next state based on ``provider.is_acceptor``."""

    def test_requestor_side_goes_to_sta9(self) -> None:
        sm = _make_sm(is_acceptor=False)
        sm.primitive = pdu.AReleaseRqPDU()
        self.assertEqual(sm.ar_8(), fsm.States.STA_9)

    def test_acceptor_side_goes_to_sta10(self) -> None:
        sm = _make_sm(is_acceptor=True)
        sm.primitive = pdu.AReleaseRqPDU()
        self.assertEqual(sm.ar_8(), fsm.States.STA_10)


class AbortAndCloseTestCase(unittest.TestCase):
    def test_aa_2_stops_and_closes(self) -> None:
        sm = _make_sm()
        sock = sm.provider.dul_socket
        result = sm.aa_2()
        self.assertEqual(result, fsm.States.STA_1)
        self.assertTrue(sock.closed)

    def test_ar_5_stops_timer_returns_sta1(self) -> None:
        sm = _make_sm()
        sm.timer.start()
        self.assertEqual(sm.ar_5(), fsm.States.STA_1)

    def test_aa_1_sends_abort_and_restarts_timer(self) -> None:
        sm = _make_sm()
        sm.primitive = pdu.AAbortPDU(source=0, reason_diag=0)
        sock = sm.provider.dul_socket
        result = sm.aa_1()
        self.assertEqual(result, fsm.States.STA_13)
        self.assertTrue(sock.sent)


if __name__ == '__main__':
    unittest.main()
