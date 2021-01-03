# Copyright (c) 2014 Pavel 'Blane' Tuchin
# Copyright (c) 2012 Patrice Munger
# This file is part of pynetdicom, released under a modified MIT license.
#    See the file license.txt included with this distribution, also
#    available at http://pynetdicom.googlecode.com

from __future__ import absolute_import, unicode_literals

import threading
import tempfile
import platform
import copy
import contextlib

from itertools import count
from threading import Lock

from six.moves import socketserver, zip


from . import _dicom
from . import sopclass
from . import asceprovider
from . import exceptions
from . import statuses


# current implementation UID. Generated by pydicom
IMPLEMENTATION_UID = _dicom.UID('1.2.826.0.1.3680043.8.498.1.1.155105445218102811803000')
PREAMBLE = b"\0" * 128


def write_meta(fp, command_set, ts):
    """Writes file meta information.

    This is a small utility function that can be useful when overriding
    :meth:`~netdicom2.applicationentity.AEBase.get_file` method of the
    :class:`~netdicom2.applicationentity.AEBase` class

    :param fp: file or file-like object where dataset will be stored
    :param command_set: command dataset of received message
    :param ts: dataset transfer syntax
    """
    fp.write(PREAMBLE)
    meta = _dicom.Dataset()
    meta.MediaStorageSOPClassUID = command_set.AffectedSOPClassUID
    meta.MediaStorageSOPInstanceUID = command_set.AffectedSOPInstanceUID
    meta.TransferSyntaxUID = ts
    meta.ImplementationClassUID = IMPLEMENTATION_UID
    _dicom.write_file_meta_info(_dicom.DicomFileLike(fp), meta)


class AEBase(object):
    """Base Application Entity class.

    This class is intended for sub-classing and should not be used directly.
    Use :class:`~netdicom2.applicationentity.ClientAE` or
    :class:`~netdicom2.applicationentity.AE` instead

    Class provides common API for application entities, such as:
        * requesting association
        * adding services as SCU
        * handful of useful public properties (presentation context definition
          list, supported transfer syntax list, maximum pdu size)

    :ivar supported_ts:  Set of transfer syntaxes supported by this
                         application entity. This attribute defaults to
                         :attr:`~netdicom2.applicationentity.AEBase.default_ts`.
    :ivar timeout: Connection timeout in seconds. Default value is 15.
    :ivar max_pdu_length: Maximum size of PDU in bytes.
    :ivar supported_scu: Dictionary that maps Abstract syntax UIDs to specific
                         services that are support in SCU role.
                         This attribute is populated by adding services using
                         :meth:`~netdicom2.applicationentity.AEBase.add_scu`
                         method.
                         This attribute is intended for **read-only** use
                         by class clients.

    :ivar supported_scp: Dictionary that maps Abstract syntax UIDs to
                         specific services that are support in SCP role.
                         This attribute is populated by adding services using
                         :meth:`~netdicom2.applicationentity.AE.add_scp` method
                         of the full AE class
                         This attribute is intended for **read-only** use by
                         class clients.

    """
    default_ts = [_dicom.ExplicitVRLittleEndian, _dicom.ImplicitVRLittleEndian,
                  _dicom.ExplicitVRBigEndian]
    """
    Default list of supported transfer syntaxes.
    """

    def __init__(self, supported_ts, max_pdu_length):
        if supported_ts is None:
            supported_ts = self.default_ts

        self.supported_ts = frozenset(supported_ts)
        self.timeout = 15
        self.max_pdu_length = max_pdu_length

        self.context_def_list = {}
        self.store_in_file = set()
        self.supported_scu = {}
        self.supported_scp = {}
        self.lock = Lock()

    def add_scu(self, service, sop_classes=None):
        """Adds service as SCU to the AE.

        Presentation context definition list is updated based on SOP Class UIDs
        that are handled by this service. Calls to this method could be
        chained, so you can add multiple services in one statement.

        :param service: DICOM service
        :param sop_classes overrides list of SOP Class UIDs provided by the service
        """
        sop_classes = sop_classes or service.sop_classes
        self.supported_scu.update({
            uid: service for uid in sop_classes
        })
        store_in_file = (hasattr(service, 'store_in_file') and
                         service.store_in_file)
        self.update_context_def_list(sop_classes, store_in_file)
        return self

    def update_context_def_list(self, sop_classes, store_in_file=False):
        """Updates presentation context definition list.

        :param sop_classes: new SOP Class UIDs that should be added to
                            presentation contexts definition list
        :param store_in_file: indicates if incoming datasets for these SOP
                              Classes should be stored in file.
        """
        start = max(self.context_def_list.keys()) + 2 if self.context_def_list \
            else 1

        self.context_def_list.update(
            self._build_context_def_list(sop_classes, start, store_in_file)
        )

    def copy_context_def_list(self):
        """Makes a shallow copy of presentation context definition list.

        .. note::

            This method is tread-safe.

        :return: copy of the presentation context definition list.
        """
        with self.lock:
            return copy.copy(self.context_def_list)

    @contextlib.contextmanager
    def request_association(self, remote_ae):
        """Requests association to a remote application entity.

        Request is formed based on configuration dictionary that is passed in.
        Currently supported parameters are:

            * **aet** - remote AE title
            * **address** - remote AE IP address
            * **port** - remote AE port
            * **username** - username for DICOM authentication
            * **password** - password for DICOM authentication

        :param remote_ae: dictionary that contains remote AE configuration.
        """
        assoc = None
        try:
            assoc = asceprovider.AssociationRequester(self, remote_ae=remote_ae)
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

    def get_file(self, context, command_set):
        """Method is used by association to get file-like object to store
        dataset.

        Method is only called when service SOP Class UID is present in
        `self.store_in_file` set. Method itself does not own the file object.
        So it's service implementation responsibility to close the file after
        it's done when handling received message.
        Default implementation is based on temporary file. User may choose
        to override this method to provide a permanent storage for dataset.

        :param context: presentation context
        :param command_set: command dataset of the received message
        :return: file where association can store received dataset and file
                 starting position.
        """
        tmp = tempfile.TemporaryFile()
        start = tmp.tell()
        try:
            write_meta(tmp, command_set, context.supported_ts)
        except Exception:
            tmp.close()
            raise
        else:
            return tmp, start

    def on_association_request(self, asce, assoc):
        """Extra processing of the association request.

        Default implementation of the method does nothing and thus accepts all
        incoming association requests.
        If association should be rejected user should override this method
        in a sub-class and raise `AssociationRejectedError` when appropriate

        :param asce: association object itself
        :param assoc: association request parameters
        """
        pass

    def on_association_response(self, response):
        """Extra processing for association response.

        Default implementation does nothing.

        :param response: response received from remote AE
        """
        pass

    def on_receive_echo(self, context):
        """Default handling of C-ECHO command. Always returns SUCCESS code

        User should override this method in sub-class to provide custom
        handling of the command.

        :param context: presentation context (contains ID, SOP Class UID and
                        Transfer Syntax)
        :return: status that should be sent in response
        """
        return statuses.SUCCESS

    def on_receive_store(self, context, ds):
        """Default handling of C-STORE command. Always returns
        ELEMENT_DISCARDED code.

        User should override this method in sub-class to provide custom handling
        of the command

        :param context: presentation context (contains ID, SOP Class UID and
                        Transfer Syntax)
        :param ds: dataset that should be stored
        :return: status code
        """
        return statuses.C_STORE_ELEMENTS_DISCARDED

    def on_receive_find(self, context, ds):
        """Default handling of C-FIND command. Returns empty iterator.

        :param context: presentation context (contains ID, SOP Class UID and
                        Transfer Syntax)
        :param ds: dataset with C-FIND parameters
        :return: iterator that returns tuples: (<result dataset>, <status code>)
        """
        return iter([])

    def on_receive_move(self, context, ds, destination):
        """Default handling of C-MOVE command. Returns empty empty values

        :param context: presentation context (contains ID, SOP Class UID and
                        Transfer Syntax)
        :param ds: dataset with C-MOVE parameters
        :param destination: C-MOVE command destination
        :return: tuple: remote AE parameters, number of operations and iterator
                 that will return datasets for moving
        """
        return None, 0, iter([])

    def on_commitment_request(self, remote_ae, uids):
        """Handle storage commitment request.

        Method should return three values:
            * remote AE parameters (IP address, port, etc.)
            * iterable or None for successfully stored SOP Instance UIDs
            * iterable or None for failed SOP Instance UIDs

        Default implementation is not provided. Method raises
        `exceptions.EventHandlingError`

        :param remote_ae: remote AE title
        :param uids: iterable of tuples (SOP Class UID, SOP Instance UID)
        """
        raise exceptions.EventHandlingError('Not implemented')

    def on_commitment_response(self, transaction_uid, success, failure):
        """Handle storage commitment response.

        Default implementation is not provided. Method raises
        `exceptions.EventHandlingError`

        :param transaction_uid: Transaction UID
        :param success: iterable of tuples (SOP Class UID, SOP Instance UID)
        :param failure: iterable of tuples (SOP Class UID, SOP Instance UID,
                        Failure Reason
        """
        raise exceptions.EventHandlingError('Not implemented')

    def _build_context_def_list(self, sop_classes, start, store_in_file):
        if store_in_file:
            self.store_in_file.update(sop_classes)
        return {pc_id: asceprovider.PContextDef(pc_id, _dicom.UID(sop_class),
                                                self.supported_ts)
                for sop_class, pc_id in zip(sop_classes,
                                            count(start, 2))}


class ClientAE(AEBase):
    """Simple SCU-only application entity.

    Use this class if you only intend to use SCUs service roles. This AE won't
    handle any incoming connections.

    :param ae_title: AE title (up to 16 characters)
    :param supported_ts: list of supported transfer syntaxes. If you are
                         using Storage or Q/R C-GET services be sure to
                         add only transfer syntax of the expected dataset.
    :param max_pdu_length: maximum PDU length in bytes (defaults to 64kb).
    """
    def __init__(self, ae_title, supported_ts=None,
                 max_pdu_length=65536):
        """Initializes new ClientAE instance"""
        super(ClientAE, self).__init__(supported_ts, max_pdu_length)
        self.local_ae = {'address': platform.node(), 'aet': ae_title}


class AE(AEBase, socketserver.ThreadingTCPServer):
    """Represents a DICOM application entity based on
    ``SocketServer.ThreadingTCPServer``

    Unlike :class:`~netdicom2.applicationentity.ClientAE` this one is fully
    functional application entity that can take on both SCU and SCP roles.
    For convenience :class:`~netdicom2.applicationentity.AE` supports context
    manager interface so it can be used like this::

        from netdicom2.sopclass import verification_scp

        ae = AE('AET', 104).add_scp(verification_scp)
        with ae:
            pass  # AE is running and accepting connection.

    Upon exiting context AE is stopped.

    :param ae_title: AE title (up to 16 characters)
    :param port: port that AE listens on for incoming connection
    :param supported_ts: list of transfer syntaxes supported by AE
    :param max_pdu_length: maximum PDU length in bytes (defaults to 64kb).
    """

    def __init__(self, ae_title, port, supported_ts=None, max_pdu_length=65536):
        """Initializes new AE instance."""
        socketserver.ThreadingTCPServer.__init__(
            self,
            ('', port),
            asceprovider.AssociationAcceptor
        )
        AEBase.__init__(self, supported_ts, max_pdu_length)

        self.daemon_threads = True
        self.allow_reuse_address = True

        self.local_ae = {'address': platform.node(), 'port': port,
                         'aet': ae_title}

    def add_scp(self, service):
        """Adds service as SCP to the AE.

        Method is similar to ``add_scu`` method of the
        :class:`~netdicom2.applicationentity.AEBase` base class.

        :param service: DICOM service.
        """
        self.supported_scp.update({
            uid: service for uid in service.sop_classes
        })
        store_in_file = (hasattr(service, 'store_in_file') and
                         service.store_in_file)
        self.update_context_def_list(service.sop_classes, store_in_file)
        return self

    def quit(self):
        """Stops AE from accepting any more connections."""
        self.shutdown()
        self.server_close()

    def __enter__(self):
        threading.Thread(target=self.serve_forever).start()

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.quit()
