"""Unit tests for :mod:`pynetdicom2.applicationentity` server creation.

``allow_reuse_address`` must be in effect when the listening socket is bound.
Previously the flag was set only after the ``TCPServer`` constructor had
already bound the socket, so it had no effect for the default
``bind_and_activate=True`` path.
"""
import socket
import ssl
import unittest

from pynetdicom2 import applicationentity, ssl_ae
from pynetdicom2 import sopclass


def _reuse_addr(server: socket.socket) -> bool:
    return bool(server.getsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR))


class ServerReuseAddressTestCase(unittest.TestCase):
    def test_ae_server_socket_has_reuse_address(self) -> None:
        # Port 0 lets the OS pick a free port. The AE binds immediately
        # because bind_and_activate defaults to True.
        ae = applicationentity.AE('AET', 0)
        try:
            self.assertTrue(_reuse_addr(ae.server.socket))
            self.assertTrue(ae.server.daemon_threads)
        finally:
            ae.server.server_close()

    def test_ssl_ae_server_socket_has_reuse_address(self) -> None:
        context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
        ae = ssl_ae.SSLApplicationEntity(context, 'AET', 0)
        try:
            self.assertTrue(_reuse_addr(ae.server.socket))
            self.assertTrue(ae.server.daemon_threads)
        finally:
            ae.server.server_close()


class ServeThreadLifecycleTestCase(unittest.TestCase):
    def test_activated_attribute_spelling(self) -> None:
        ae = applicationentity.AE('AET', 0)
        try:
            self.assertTrue(hasattr(ae, 'activated'))
            self.assertFalse(hasattr(ae, 'activted'))
        finally:
            ae.server.server_close()

    def test_serve_thread_tracked_and_joined_on_quit(self) -> None:
        ae = applicationentity.AE('AET', 0)
        ae.add_scp(sopclass.verification_scp)
        with ae:
            thread = ae._serve_thread
            self.assertIsNotNone(thread)
            self.assertTrue(thread.is_alive())
        # __exit__ -> quit() must have joined the serve thread and cleared
        # the reference.
        self.assertFalse(thread.is_alive())
        self.assertIsNone(ae._serve_thread)


if __name__ == '__main__':
    unittest.main()
