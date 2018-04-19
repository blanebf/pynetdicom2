from __future__ import absolute_import

import os
import threading
import dicom

from . import __version__

__version_info__ = __version__.__version__.split('.')

from . import applicationentity
from . import sopclass

PDU_SIZE = 1024 * 1024

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


def _get_file_name(fp):
    ds = dicom.read_file(fp, stop_before_pixels=True)
    return '{}.dcm'.format(ds.SOPInstanceUID)


def c_get(storage_dir, remote_ae, local_ae, sop_class, ts, ds, timeout=None):
    """Executes C-GET request synchronously.

    :rtype : list
    :param storage_dir: directory where moved files should be stored
    :param remote_ae: remote AE parameters
    :param local_ae: local AE
    :param sop_class: instance SOP Class UID or list of UIDs that should be
    received via C-GET
    :param ts: Transfer syntax
    :param ds: search parameters. Either tags (tuple 0xXX, 0xXX) or
    keywords (SOPInstanceUID, PatientID, etc.)
    :param timeout: operation timeout

    :return: list of received files
    """
    sop_classes = [sop_class] if isinstance(sop_class, basestring) \
        else sop_class
    entity = ClientStorageAE(storage_dir, ae_title=local_ae, supported_ts=[ts],
                             max_pdu_length=PDU_SIZE)\
        .add_scu(sopclass.qr_get_scu)
    if timeout:
        entity.timeout = timeout

    entity.update_context_def_list(sop_classes, store_in_file=True)
    with entity.request_association(remote_ae) as assoc:
        it = assoc.get_scu(sopclass.PATIENT_ROOT_GET_SOP_CLASS)(ds, 1)
        return [os.path.join(storage_dir, _get_file_name(fp)) for _, fp in it if fp]


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
