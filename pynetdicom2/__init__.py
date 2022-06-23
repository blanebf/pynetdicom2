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
