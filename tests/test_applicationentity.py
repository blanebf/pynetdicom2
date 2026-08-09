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


if __name__ == '__main__':
    unittest.main()
