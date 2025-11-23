import contextlib
from functools import partial
import ssl
import socket
import socketserver
from typing import Any, Iterator, Optional, Union

from pydicom import uid

from . import applicationentity, asceprovider, dulprovider, exceptions, fsm


class SSLDULProvider(dulprovider.DULServiceProvider):
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
        dul_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        if not self.called_presentation_address:
            raise exceptions.NetDICOMError(
                'Called presentation address is not set'
            )
        dul_socket.connect(self.called_presentation_address)
        self.dul_socket = self.context.wrap_socket(dul_socket)


class SSLAssociationRequester(asceprovider.AssociationRequester):
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

    @contextlib.contextmanager
    def request_association(
            self,
            remote_ae: Union[asceprovider.RemoteAEConfig, dict[str, Any]]
    ) -> Iterator[asceprovider.AssociationRequester]:
        assoc = None
        try:
            assoc = SSLAssociationRequester(
                self.context, self, self.max_pdu_length, remote_ae
            )
            assoc.request()
            yield assoc
            if assoc.association_established:
                assoc.release()
            else:
                assoc.kill()
        except Exception:
            if assoc and assoc.association_established:
                assoc.abort()
            elif assoc:
                assoc.kill()
            raise


class SSLCPServer(socketserver.TCPServer):
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


class SSLThreadingTCPServer(socketserver.ThreadingMixIn, SSLCPServer):
    pass


class SSLApplicationEntity(applicationentity.AE):
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
        server = SSLThreadingTCPServer(
            self.context,
            ('', port),
            partial(
                applicationentity.RequestHandler,
                local_ae=self,
                max_pdu_length=max_pdu_length
            ),
            bind_and_activate
        )
        server.daemon_threads = True
        server.allow_reuse_address = True
        return server
