"""Module provides high-level wrappers over DICOM services."""
import contextlib
import dataclasses
import pathlib
from typing import Callable, Iterable, Iterator, Optional, Union, cast

from pydicom import dataset, filereader, uid

from . import (
    applicationentity,
    asceprovider,
    dimsemessages,
    exceptions,
    sopclass,
    statuses,
    uids
)


BoundFind = Callable[
    [dataset.Dataset, int],
    Iterable[tuple[Optional[dataset.Dataset], statuses.Status]]
]


BoundMove = Callable[
    [dataset.Dataset, str, int],
    Iterable[tuple[statuses.Status, dimsemessages.CMoveRSPMessage]]
]


def verify(
        local_aet: str,
        remote_ae: asceprovider.RemoteAEConfig
) -> statuses.Status:
    """Makes a verification request (C-ECHO) to a remote Verification SCP.
    In case or rejection the function will throw an exception.

    :param local_aet: local AE title
    :param remote_ae: remote AE connection parameters
    :return: resulting verification status
    """
    ae = applicationentity.ClientAE(local_aet)
    ae.add_scu(sopclass.verification_scu)
    with ae.request_association(remote_ae) as assoc:
        service = assoc.get_scu(uids.VERIFICATION_SOP_CLASS)
        result = cast(statuses.Status, service(1))
        return result


def find(
        local_aet: str,
        remote_ae: asceprovider.RemoteAEConfig,
        request: dataset.Dataset,
        root: uid.UID = uids.STUDY_ROOT_FIND_SOP_CLASS
) -> Iterable[dataset.Dataset]:
    """Makes a find request to a remote Q/R SCP service.

    :param local_aet: local AE title
    :param remote_ae: remote AE connection parameters
    :param request: C-FIND request
    :param root: Q/R search root, defaults to uids.STUDY_ROOT_FIND_SOP_CLASS
    :yield: responses from Q/R SCP
    """
    ae = applicationentity.ClientAE(local_aet)
    ae.add_scu(sopclass.qr_find_scu)
    with ae.request_association(remote_ae) as assoc:
        service = cast(BoundFind, assoc.get_scu(root))
        for response, status in service(request, 1):
            if status.is_failure:
                raise exceptions.NetDICOMError(f'C-FIND failure: {status}')
            if response:
                yield response


def store(
        local_aet: str,
        remote_ae: asceprovider.RemoteAEConfig,
        ds: Union[str, dataset.Dataset]
) -> statuses.Status:
    """Stores a DICOM file or dataset in a remote Storage SCP

    :param local_aet: local AE title
    :param remote_ae: remote AE connection parameters
    :param ds: DICOM dataset or a path to file to store
    :return: storage request status
    """
    file_meta = filereader.read_file_meta_info(ds)
    sop_class = file_meta.MediaStorageSOPClassUID
    transfer_syntax = file_meta.TransferSyntax
    ae = applicationentity.ClientAE(local_aet, supported_ts=[transfer_syntax])
    ae.add_scu(sopclass.storage_scu, [sop_class])
    with ae.request_association(remote_ae) as assoc:
        service = assoc.get_scu(sop_class)
        result = cast(statuses.Status, service(ds, 1))
        return result


@contextlib.contextmanager
def storage(
        storage_dir: pathlib.Path,
        local_aet: str,
        port: int,
        supported_ts: Optional[list[uid.UID]] = None
) -> Iterator[None]:
    """Simple context manager to start a Storage SCP to recieve datasets to
    a folder.

    :param storage_dir: where to store incoming datasets
    :param local_aet: local AE title
    :param port: port that AE listens on for incoming connection
    :param supported_ts: what Transfer Syntaxes should be accepted, defaults
                         to None. If none provided, all transfer syntaxes will
                         be accepted
    :yield: None
    """
    if not supported_ts:
        supported_ts = uids.ALL_TS
    ae = applicationentity.StorageAE(
        storage_dir, local_aet, port, supported_ts
    )
    with ae:
        yield


def move(
        local_aet: str,
        remote_ae: asceprovider.RemoteAEConfig,
        request: dataset.Dataset,
        dest_ae: str,
        root: uid.UID = uids.STUDY_ROOT_MOVE_SOP_CLASS
) -> 'CMoveResponse':
    """Send a move request

    :param local_aet: local AE title
    :param remote_ae: remote AE connection parameters
    :param request: C-FIND request
    :param dest_ae: move destination AE title
    :param root: Q/R move root, defaults to uids.STUDY_ROOT_MOVE_SOP_CLASS
    :raises exceptions.NetDICOMError: _description_
    :return: resulting move response with success/failure/warnings total
    """
    ae = applicationentity.ClientAE(local_aet)
    ae.add_scu(sopclass.qr_move_scu)
    with ae.request_association(remote_ae) as asce:
        service = cast(BoundMove, asce.get_scu(root))
        last_response = CMoveResponse(None, None, None, None)
        for status, msg in service(request, dest_ae, 1):
            if status.is_failure:
                raise exceptions.NetDICOMError(f'C-MOVE failure: {status}')
            last_response = CMoveResponse(
                msg.num_of_remaining_sub_ops,
                msg.num_of_completed_sub_ops,
                msg.num_of_failed_sub_ops,
                msg.num_of_warning_sub_ops
            )
    return last_response


@dataclasses.dataclass(frozen=True)
class CMoveResponse:
    """Simplified move response"""
    num_of_remaining_sub_ops: Optional[int]
    num_of_completed_sub_ops: Optional[int]
    num_of_failed_sub_ops: Optional[int]
    num_of_warning_sub_ops: Optional[int]
