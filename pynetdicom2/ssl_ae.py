"""
This module provides classes that add SSL support to DICOM network connections
As `ssl` module is optional in the python standard library this module is
considered optional too and won't work if your python distribution doesn't
contain an `ssl` module.
"""
from functools import partial
import ssl
import socket
import socketserver
from typing import Any, Optional, Union

from pydicom import uid

from . import applicationentity, asceprovider, dulprovider, exceptions, fsm


class SSLDULProvider(dulprovider.DULServiceProvider):
    """DUL Provider implementation that wraps its socket with `SSLContext`"""
    def __init__(
            self,
            context: ssl.SSLContext,
            store_in_file: set[uid.UID],
            get_file_cb: fsm.GetFileCB,
            dul_socket: Optional[socket.socket] = None,
            max_pdu_length: int = 65536
    ) -> None:
        super().__init__(
            store_in_file, get_file_cb, dul_socket, max_pdu_length
        )
        self.context = context

    def create_socket(self) -> None:
        if not self.called_presentation_address:
            raise exceptions.NetDICOMError(
                'Called presentation address is not set'
            )
        dul_socket = socket.create_connection(
            self.called_presentation_address,
            timeout=dulprovider.SOCKET_TIMEOUT
        )
        try:
            self.dul_socket = self.context.wrap_socket(dul_socket)
        except OSError:
            # The SSL handshake failed: release the underlying socket so it
            # does not leak.
            dul_socket.close()
            raise


class SSLAssociationRequester(asceprovider.AssociationRequester):
    """
    AssociationRequester implementation that uses SSL in its DUL Provider
    implementation.
    """
    def __init__(
            self,
            context: ssl.SSLContext,
            local_ae: asceprovider.AEBaseProto,
            max_pdu_length: int,
            remote_ae: Union[asceprovider.RemoteAEConfig, dict[str, Any]]
    ) -> None:
        self.context = context
        super().__init__(local_ae, max_pdu_length, remote_ae)

    def _create_dul(
            self,
            local_ae: asceprovider.AEBaseProto,
            dul_socket: Optional[socket.socket],
            max_pdu_length: int
    ) -> dulprovider.DULServiceProvider:
        return SSLDULProvider(
            self.context,
            local_ae.store_in_file,
            local_ae.get_file,
            dul_socket,
            max_pdu_length
        )


class SSLClientAE(applicationentity.ClientAE):
    """Just like its parent class provides a simple SCU-only application
    entity, but it also takes in an `SSLContext` to wrap all its network
    communication with it.
    """
    def __init__(
            self,
            context: ssl.SSLContext,
            ae_title: str,
            supported_ts: Optional[list[uid.UID]] = None,
            max_pdu_length: int = 65536
    ) -> None:
        """Initializes new ClientAE instance"""
        super().__init__(ae_title, supported_ts, max_pdu_length)
        self.context = context

    def _create_association(
            self,
            remote_ae: Union[asceprovider.RemoteAEConfig, dict[str, Any]]
    ) -> asceprovider.AssociationRequester:
        return SSLAssociationRequester(
            self.context, self, self.max_pdu_length, remote_ae
        )


class _SSLCPServer(socketserver.TCPServer):
    def __init__(
            self,
            context: ssl.SSLContext,
            server_address: tuple[str, int],
            RequestHandlerClass: Any,
            bind_and_activate: bool = True
    ) -> None:
        super().__init__(
            server_address,
            RequestHandlerClass,
            bind_and_activate
        )
        self.context = context

    def get_request(self) -> tuple[socket.socket, tuple[str, int]]:
        newsocket, fromaddr = super().get_request()
        connstream = self.context.wrap_socket(newsocket, server_side=True)
        return connstream, fromaddr


class _SSLThreadingTCPServer(socketserver.ThreadingMixIn, _SSLCPServer):
    # ``allow_reuse_address`` must be set before the socket is bound. As the
    # binding happens inside ``__init__`` (when ``bind_and_activate`` is
    # true), the attributes are defined on the class rather than set on the
    # instance.
    allow_reuse_address = True
    daemon_threads = True


class SSLApplicationEntity(applicationentity.AE):
    """The same as its parent class, but with added `SSLContext` parameter
    that it uses to wrap all network connections with.
    """
    def __init__(
            self,
            context: ssl.SSLContext,
            ae_title: str,
            port: int,
            supported_ts: Optional[list[uid.UID]] = None,
            max_pdu_length: int = 65536,
            bind_and_activate: bool = True
    ) -> None:
        self.context = context
        super().__init__(
            ae_title, port, supported_ts, max_pdu_length, bind_and_activate
        )

    def _create_server(
            self,
            port: int,
            bind_and_activate: bool,
            max_pdu_length: int
    ) -> socketserver.TCPServer:
        return _SSLThreadingTCPServer(
            self.context,
            ('', port),
            partial(
                applicationentity.RequestHandler,
                local_ae=self,
                max_pdu_length=max_pdu_length
            ),
            bind_and_activate
        )
