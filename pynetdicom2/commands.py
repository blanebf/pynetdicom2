from __future__ import absolute_import

from typing import Any, Dict

from pydicom import filereader

from . import applicationentity
from . import sopclass
from . import statuses
from . import uids


def verify(local_aet, remote_ae):
    # type: (str,Dict[str,Any]) -> bool
    ae = applicationentity.ClientAE(local_aet)
    ae.add_scu(sopclass.verification_scu)
    with ae.request_association(remote_ae) as assoc:
        service = assoc.get_scu(uids.VERIFICATION_SOP_CLASS)
        result = service(1)  # type: statuses.Status
        return result.is_success


def find(local_aet, remote_ae, level, request, root=uids.STUDY_ROOT_FIND_SOP_CLASS):
    ae = applicationentity.ClientAE(local_aet)
    ae.add_scu(sopclass.qr_find_scu)
    with ae.request_association(remote_ae) as assoc:
        service = assoc.get_scu(root)


def store(local_aet, remote_ae, file_name):
    # type: (str,Dict[str,Any],str) -> bool
    file_meta = filereader.read_file_meta_info(file_name)
    sop_class = file_meta.MediaStorageSOPClassUID
    transfer_syntax = file_meta.TransferSyntax
    ae = applicationentity.ClientAE(local_aet, supported_ts=[transfer_syntax])  # type: ignore
    ae.add_scu(sopclass.storage_scu, [sop_class])
    with ae.request_association(remote_ae) as assoc:
        service = assoc.get_scu(sop_class)
        result = service(file_name, 1)  # type: statuses.Status
        return result.is_success


def get(local_aet, remote_ae, level, request, root=uids.STUDY_ROOT_GET_SOP_CLASS):
    pass


def move(local_aet, remote_ae, level, request, root=uids.STUDY_ROOT_MOVE_SOP_CLASS):
    pass
