"""Unit tests for :mod:`pynetdicom2.ssl_ae`."""
import socket
import ssl
import unittest
from unittest import mock

from pynetdicom2 import exceptions, ssl_ae


def _make_bare_ssl_provider() -> ssl_ae.SSLDULProvider:
    """Creates an SSL provider without starting its worker thread."""
    return object.__new__(ssl_ae.SSLDULProvider)


class SSLCreateSocketTestCase(unittest.TestCase):
    def test_create_socket_wraps_connected_socket(self) -> None:
        provider = _make_bare_ssl_provider()
        provider.called_presentation_address = ('localhost', 11112)
        context = mock.MagicMock()
        provider.context = context
        raw_socket = mock.MagicMock()
        wrapped = mock.MagicMock()
        context.wrap_socket.return_value = wrapped
        with mock.patch.object(
            socket, 'create_connection', return_value=raw_socket
        ) as connect_mock:
            ssl_ae.SSLDULProvider.create_socket(provider)
        connect_mock.assert_called_once_with(
            ('localhost', 11112), timeout=mock.ANY
        )
        context.wrap_socket.assert_called_once_with(raw_socket)
        self.assertIs(provider.dul_socket, wrapped)

    def test_create_socket_closes_socket_on_handshake_failure(self) -> None:
        # If the SSL handshake fails, the raw socket must not leak.
        provider = _make_bare_ssl_provider()
        provider.called_presentation_address = ('localhost', 11112)
        context = mock.MagicMock()
        provider.context = context
        raw_socket = mock.MagicMock()
        context.wrap_socket.side_effect = ssl.SSLError('handshake')
        with mock.patch.object(
            socket, 'create_connection', return_value=raw_socket
        ):
            with self.assertRaises(ssl.SSLError):
                ssl_ae.SSLDULProvider.create_socket(provider)
        raw_socket.close.assert_called_once()

    def test_create_socket_without_address_raises(self) -> None:
        provider = _make_bare_ssl_provider()
        provider.called_presentation_address = None
        with self.assertRaises(exceptions.NetDICOMError):
            ssl_ae.SSLDULProvider.create_socket(provider)


if __name__ == '__main__':
    unittest.main()
