# Copyright (c) 2014 Pavel 'Blane' Tuchin
# Copyright (c) 2012 Patrice Munger
# This file is part of pynetdicom, released under a modified MIT license.
#    See the file license.txt included with this distribution, also
#    available at http://pynetdicom.googlecode.com

import threading
import platform
import contextlib

import SocketServer

from dicom.UID import ExplicitVRLittleEndian, ImplicitVRLittleEndian, \
    ExplicitVRBigEndian, UID

import netdicom2.sopclass as sopclass
import netdicom2.asceprovider as asceprovider


def _build_context_def_list(sop_classes, supported_ts):
    count = 1
    context_def_list = []
    for sop_class in sop_classes:
        context_def_list.append(
            [count, UID(sop_class), [x for x in supported_ts]]
        )
        count += 2
    return context_def_list


class AEBase(object):
    default_ts = [ExplicitVRLittleEndian, ImplicitVRLittleEndian,
                  ExplicitVRBigEndian]

    @contextlib.contextmanager
    def request_association(self, remote_ae):
        """Requests association to a remote application entity"""
        assoc = asceprovider.AssociationRequester(self, remote_ae=remote_ae)
        yield assoc
        if assoc.association_established:
            assoc.release()
        else:
            assoc.kill()

    def on_association_request(self, assoc):
        """Extra processing of the association request.

        Default implementation of the method does nothing and thus accepts all
        incoming association requests.
        If association should be rejected user should override this method
        in a sub-class and raise `AssociationRejectedError` when appropriate

        :param assoc: association request parameters
        """
        pass

    def on_association_response(self, response):
        """Extra processing for association response.

        Default implementation does nothing.

        :param response: response received from remote AE
        """
        pass

    def on_receive_echo(self, service):
        """Default handling of C-ECHO command. Always returns SUCCESS code

        User should override this method in sub-class to provide custom
        handling of the command.

        :param service: service instance that received C-ECHO
        :return: status that should be sent in response
        """
        return sopclass.SUCCESS

    def on_receive_store(self, service, ds):
        """Default handling of C-STORE command. Always returns
        ELEMENT_DISCARDED code.

        User should override this method in sub-class to provide custom handling
        of the command

        :param service: service that received command
        :param ds: dataset that should be stored
        :return: status code
        """
        return sopclass.ELEMENT_DISCARDED

    def on_receive_find(self, service, ds):
        """Default handling of C-FIND command. Returns empty iterator.

        :param service: service that received command
        :param ds: dataset with C-FIND parameters
        :return: iterator that returns tuples: (<result dataset>, <status code>)
        """
        return iter([])

    def on_receive_move(self, service, ds, destination):
        """Default handling of C-MOVE command. Returns empty empty values

        :param service: service that received command
        :param ds: dataset with C-MOVE parameters
        :param destination: C-MOVE command destination
        :return: tuple: remote AE parameters, number of operations and iterator
        that will return datasets for moving
        """
        return None, 0, iter([])


class ClientAE(AEBase):
    def __init__(self, ae_title, sop_scu, supported_ts=None,
                 max_pdu_length=16000):
        if supported_ts is None:
            supported_ts = AE.default_ts

        self.local_ae = {'address': platform.node(), 'aet': ae_title}
        self.max_pdu_length = max_pdu_length
        self.context_def_list = _build_context_def_list(sop_scu, supported_ts)
        self.acceptable_presentation_contexts = []


class AE(AEBase, SocketServer.ThreadingTCPServer):
    """Represents a DICOM application entity

    Instance if this class represent an application entity. Once
    instantiated, it starts a new thread and enters an event loop,
    where events are association requests from remote AEs. Events
    trigger callback functions that perform user defined actions based
    on received events.
    """

    def __init__(self, ae_title, port, sop_scu, sop_scp,
                 supported_ts=None, max_pdu_length=16000):
        SocketServer.ThreadingTCPServer.__init__(
            self,
            ('', port),
            asceprovider.AssociationAcceptor
        )

        self.daemon_threads = True
        self.allow_reuse_address = True

        if supported_ts is None:
            supported_ts = AE.default_ts

        self.local_ae = {'address': platform.node(), 'port': port,
                         'aet': ae_title}

        self.max_pdu_length = max_pdu_length
        self.context_def_list = _build_context_def_list(
            sop_scu + sop_scp,
            supported_ts
        )

        # build acceptable context definition list used to decide whether an
        # association from a remote AE will be accepted or not.
        # This is based on the supported_sop_classes_as_scp and
        # supported_transfer_syntax values set for this AE.
        self.acceptable_presentation_contexts = [
            [sop_class, [x for x in supported_ts]] for sop_class in sop_scp
        ]

    def __enter__(self):
        threading.Thread(target=self.serve_forever).start()

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.quit()

    def quit(self):
        """Stops AE.

        This will close any open associations and will break from event loop
        for AEs that supports service SOP Classes as SCP.
        """
        self.shutdown()
        self.server_close()
