"""Unit tests for :mod:`pynetdicom2.commands` helpers."""
import pathlib
import socket
import tempfile
import unittest

from pynetdicom2 import applicationentity
from pynetdicom2 import commands


def _free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(('127.0.0.1', 0))
        return sock.getsockname()[1]


class CMoveResponseTestCase(unittest.TestCase):
    def test_dataclass_is_frozen(self) -> None:
        resp = commands.CMoveResponse(1, 2, 3, 4)
        self.assertEqual(resp.num_of_remaining_sub_ops, 1)
        self.assertEqual(resp.num_of_completed_sub_ops, 2)
        self.assertEqual(resp.num_of_failed_sub_ops, 3)
        self.assertEqual(resp.num_of_warning_sub_ops, 4)
        with self.assertRaises(Exception):
            resp.num_of_failed_sub_ops = 9  # type: ignore[misc]


class StorageContextManagerTestCase(unittest.TestCase):
    def test_storage_starts_and_stops_scp(self) -> None:
        port = _free_port()
        with tempfile.TemporaryDirectory() as tmp:
            with commands.storage(pathlib.Path(tmp), 'AET', port):
                # While the context is active a server should accept a TCP
                # connection on the configured port.
                with socket.create_connection(
                    ('127.0.0.1', port), timeout=5
                ):
                    pass
            # After exit the server must no longer accept connections.
            with self.assertRaises(OSError):
                with socket.create_connection(
                    ('127.0.0.1', port), timeout=1
                ):
                    pass

    def test_storage_builds_storage_ae(self) -> None:
        port = _free_port()
        with tempfile.TemporaryDirectory() as tmp:
            with commands.storage(pathlib.Path(tmp), 'AET', port):
                pass
        # Constructing directly should also succeed with the same signature.
        ae = applicationentity.StorageAE(
            pathlib.Path(tmp), 'AET', _free_port(), bind_and_activate=False
        )
        self.assertEqual(str(ae.storage_dir), tmp)


if __name__ == '__main__':
    unittest.main()
