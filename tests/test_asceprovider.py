"""Unit tests for :mod:`pynetdicom2.asceprovider`.

Association normally starts a DUL service provider thread, so the tests build
a bare instance with ``object.__new__`` and populate only the attributes used
by the method under test. The DUL provider itself is replaced with a mock so
no real socket or thread is involved.
"""
import unittest
from unittest import mock

from pynetdicom2 import asceprovider
from pynetdicom2 import dimsemessages
from pynetdicom2 import pdu


def _make_bare_association() -> asceprovider.Association:
    """Creates an association without starting its DUL provider."""
    assoc = object.__new__(asceprovider.Association)
    assoc.dul = mock.MagicMock()
    assoc.association_established = True
    return assoc


class KillTestCase(unittest.TestCase):
    def test_kill_stops_gracefully_and_waits(self) -> None:
        # If the provider reports it stopped gracefully, kill() still calls
        # the provider's kill() so the service thread is guaranteed to have
        # exited before returning, and the association is no longer marked
        # established.
        assoc = _make_bare_association()
        assoc.dul.stop.return_value = True

        assoc.kill()

        assoc.dul.stop.assert_called()
        assoc.dul.kill.assert_called_once()
        self.assertFalse(assoc.association_established)

    def test_kill_does_not_busy_spin_when_idle(self) -> None:
        # Once the provider stops gracefully, kill() must stop retrying the
        # graceful path immediately rather than looping over stop().
        assoc = _make_bare_association()
        assoc.dul.stop.return_value = True

        assoc.kill()

        self.assertEqual(assoc.dul.stop.call_count, 1)

    def test_kill_retries_then_forces_termination(self) -> None:
        # When the association never becomes idle, kill() retries graceful
        # stopping a bounded number of times and then forces termination.
        assoc = _make_bare_association()
        assoc.dul.stop.return_value = False

        with mock.patch('pynetdicom2.asceprovider.time.sleep') as sleep_mock:
            assoc.kill()

        self.assertEqual(assoc.dul.stop.call_count, 1000)
        self.assertEqual(sleep_mock.call_count, 1000)
        assoc.dul.kill.assert_called_once()
        self.assertFalse(assoc.association_established)


class ReleaseTestCase(unittest.TestCase):
    def test_release_normal_flow(self) -> None:
        assoc = _make_bare_association()
        assoc.ae = mock.MagicMock()
        assoc.dul.receive.return_value = pdu.AReleaseRpPDU()

        rsp = assoc.release()

        self.assertIsInstance(rsp, pdu.AReleaseRpPDU)
        rq = assoc.dul.send.call_args_list[0].args[0]
        self.assertIsInstance(rq, pdu.AReleaseRqPDU)
        assoc.dul.kill.assert_called_once()

    def test_release_collision_approves_remote_request(self) -> None:
        # PS3.7 7.2.4: if the remote AE requested release while our request
        # was in flight, approve it (send A-RELEASE-RP) and then complete our
        # own release once the remote confirmation arrives.
        assoc = _make_bare_association()
        assoc.ae = mock.MagicMock()
        assoc.dul.receive.side_effect = [
            pdu.AReleaseRqPDU(),  # remote release request
            pdu.AReleaseRpPDU()   # confirmation of our request
        ]

        rsp = assoc.release()

        self.assertIsInstance(rsp, pdu.AReleaseRpPDU)
        sent = [call.args[0] for call in assoc.dul.send.call_args_list]
        self.assertIsInstance(sent[0], pdu.AReleaseRqPDU)
        self.assertIsInstance(sent[1], pdu.AReleaseRpPDU)
        assoc.dul.kill.assert_called_once()


class CancelHandlingTestCase(unittest.TestCase):
    def test_cancel_is_accepted_without_tearing_down(self) -> None:
        # A C-CANCEL must not raise (previously it triggered a
        # DIMSEProcessingError that tore down the association): it is
        # acknowledged and the message loop keeps running.
        class StopLoop(Exception):
            pass

        cancel = dimsemessages.CCancelRQMessage()
        cancel.message_id_being_responded_to = 5

        assoc = object.__new__(asceprovider.AssociationAcceptor)
        assoc.is_killed = False
        assoc.ae = mock.MagicMock()
        assoc.dul = mock.MagicMock()
        assoc.dul.receive.side_effect = [(cancel, 1), StopLoop()]

        # StopLoop proves the loop survived the C-CANCEL and kept iterating.
        with self.assertRaises(StopLoop):
            assoc._loop()


if __name__ == '__main__':
    unittest.main()
