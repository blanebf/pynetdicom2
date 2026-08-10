"""Unit tests for :mod:`pynetdicom2.fsm` state machine and timer."""
import queue
import time
import unittest
from typing import Any, Optional

from pynetdicom2 import exceptions, fsm
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

    def test_unknown_local_transition_raises_descriptive_error(self) -> None:
        sm = _make_sm()
        # EVT_9 (local P-DATA request) has no mapping from STA_1.
        with self.assertRaises(exceptions.NetDICOMError) as ctx:
            sm.action(fsm.Events.EVT_9)
        self.assertIn('EVT_9', str(ctx.exception))
        self.assertIn('STA_1', str(ctx.exception))

    def test_unexpected_peer_pdu_aborts_instead_of_raising(self) -> None:
        # An A-ASSOCIATE-RQ arriving while the transport connection is still
        # being opened is a peer protocol violation: abort it instead of
        # letting a KeyError crash the DUL thread.
        sm = _make_sm()
        sm.current_state = fsm.States.STA_4

        sm.action(fsm.Events.EVT_6)  # A-ASSOCIATE-RQ in STA_4

        self.assertEqual(sm.current_state, fsm.States.STA_13)
        self.assertIsInstance(sm.primitive, pdu.AAbortPDU)
        self.assertEqual(sm.primitive.source, 2)


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

    def test_evt14_approved_in_both_collision_states(self) -> None:
        # PS3.7 7.2.4: the local A-RELEASE response primitive sends
        # A-RELEASE-RP in both collision states (requestor and acceptor
        # side).
        for state in (fsm.States.STA_9, fsm.States.STA_10):
            with self.subTest(state=state):
                sm = _make_sm()
                sm.current_state = state
                sm.action(fsm.Events.EVT_14)
                self.assertEqual(sm.current_state, fsm.States.STA_11)
                self.assertTrue(sm.provider.dul_socket.sent)


class RejectActionTestCase(unittest.TestCase):
    def test_ae_8_sends_reject_and_starts_timer(self) -> None:
        # AE-8 sends the A-ASSOCIATE-RJ, moves to Sta13 and starts the
        # ARTIM timer so the wait for the connection close is bounded.
        sm = _make_sm()
        sm.primitive = pdu.AAssociateRjPDU(1, 1, 1)
        result = sm.ae_8()
        self.assertEqual(result, fsm.States.STA_13)
        self.assertTrue(sm.provider.dul_socket.sent)
        self.assertIsNotNone(sm.timer._start_time)


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

    def test_aa_4_issues_provider_origin_abort(self) -> None:
        # An unexpected transport close is a DICOM UL service-provider
        # initiated abort (source 2), not a service-user one (source 0).
        sm = _make_sm()
        result = sm.aa_4()
        self.assertEqual(result, fsm.States.STA_1)
        self.assertIsInstance(sm.primitive, pdu.AAbortPDU)
        self.assertEqual(sm.primitive.source, 2)
        indication = sm.provider.to_service_user.get_nowait()
        self.assertIs(indication, sm.primitive)


class UnrecognizedPduAbortTestCase(unittest.TestCase):
    """EVT_19 is raised for an unrecognized/invalid PDU, at which point no
    decoded primitive exists. The machine must respond with an explicit
    provider-initiated A-ABORT instead of re-using whatever primitive it
    currently holds (which may be ``None`` or a stale, unrelated PDU)."""

    def test_evt19_in_sta2_sends_provider_abort(self) -> None:
        sm = _make_sm()
        sm.action(fsm.Events.EVT_5)  # STA_1 -> STA_2
        self.assertEqual(sm.current_state, fsm.States.STA_2)
        sm.primitive = None  # no decoded PDU exists

        sm.action(fsm.Events.EVT_19)

        self.assertEqual(sm.current_state, fsm.States.STA_13)
        self.assertIsInstance(sm.primitive, pdu.AAbortPDU)
        self.assertEqual(sm.primitive.source, 2)
        self.assertTrue(sm.provider.dul_socket.sent)
        # The A-P-ABORT indication is issued to the service user too.
        self.assertFalse(sm.provider.to_service_user.empty())

    def test_evt19_in_sta13_sends_provider_abort(self) -> None:
        sm = _make_sm()
        sm.current_state = fsm.States.STA_13
        sm.primitive = None

        sm.action(fsm.Events.EVT_19)

        self.assertEqual(sm.current_state, fsm.States.STA_13)
        self.assertIsInstance(sm.primitive, pdu.AAbortPDU)
        self.assertEqual(sm.primitive.source, 2)


if __name__ == '__main__':
    unittest.main()
