from __future__ import absolute_import

import os
import threading

from . import __version__

__version_info__ = __version__.__version__.split('.')

from . import applicationentity
from . import sopclass


_tls = threading.local()


def _new_msg_id():
    msg_id = getattr(_tls, 'msg_id', None)
    if msg_id is None:
        _tls.msg_id = 1
        return _tls.msg_id
    else:
        _tls.msg_id += 1
        return _tls.msg_id


def c_find(remote_ae, local_aet, ds, root=sopclass.PATIENT_ROOT_FIND_SOP_CLASS):
    """Executes Query/Retrieve C-FIND.

    For each result generator yields result dataset (None in case of failure
    and status code).

    :param remote_ae: dictionary or dictionary-like object containing remote
                      application entity configuration
    :param local_aet: local AE Title (byte-string)
    :param ds: dataset with C-FIND request
    :param root: patient or study root (defaults to patient root SOP Class)
    """
    ae = applicationentity.ClientAE(local_aet).add_scu(sopclass.qr_find_scu)
    with ae.request_association(remote_ae) as asce:
        srv = asce.get_scu(root)
        for result, status in srv(ds, _new_msg_id()):
            yield result, status


def _get_storage_file(context, command_set, path):
    file_name = '{}.dcm'.format(command_set.AffectedSOPInstanceUID)
    full_name = os.path.join(path, file_name)
    i = 0
    while os.path.exists(full_name):
        i += 1
        full_name = '{}_{}'.format(full_name, i)

    ds = open(os.path.join(path, file_name), 'w+b')
    start = ds.tell()
    try:
        applicationentity.write_meta(ds, command_set, context.supported_ts)
    except Exception:
        ds.close()
        raise
    else:
        return ds, start


class ClientStorageAE(applicationentity.ClientAE):
    def __init__(self, storage_dir, ae_title, supported_ts=None,
                 max_pdu_length=65536):
        super(ClientStorageAE, self).__init__(ae_title, supported_ts,
                                              max_pdu_length)
        self.storage_dir = storage_dir

    def get_file(self, context, command_set):
        return _get_storage_file(context, command_set, self.storage_dir)


class StorageAE(applicationentity.AE):

    def __init__(self, storage_dir, ae_title, port, supported_ts=None,
                 max_pdu_length=65536):

        super(StorageAE, self).__init__(ae_title, port, supported_ts,
                                        max_pdu_length)
        self.storage_dir = storage_dir

    def get_file(self, context, command_set):
        return _get_storage_file(context, command_set, self.storage_dir)
