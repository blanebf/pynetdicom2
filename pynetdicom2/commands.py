"""Module provides high-level wrappers over DICOM services."""
from typing import Callable, Iterable, Optional, Union, cast

from pydicom import dataset, filereader, uid

from . import applicationentity, asceprovider, sopclass, statuses, uids


BoundFind = Callable[
    [dataset.Dataset, int],
    Iterable[tuple[Optional[dataset.Dataset], statuses.Status]]
]


def verify(local_aet: str, remote_ae: asceprovider.RemoteAEConfig) -> bool:
    """Makes a verification request (C-ECHO) to a remote Verification SCP.
    In case or rejection the function will throw an exception.

    :param local_aet: local AE title
    :param remote_ae: remote AE connection parameters
    :return: `True` if request result is successfull, `False` otherwise
    """
    ae = applicationentity.ClientAE(local_aet)
    ae.add_scu(sopclass.verification_scu)
    with ae.request_association(remote_ae) as assoc:
        service = assoc.get_scu(uids.VERIFICATION_SOP_CLASS)
        result = cast(statuses.Status, service(1))
        return result.is_success


def find(
        local_aet: str,
        remote_ae: asceprovider.RemoteAEConfig,
        request: dataset.Dataset,
        root: uid.UID = uids.STUDY_ROOT_FIND_SOP_CLASS
) -> Iterable[tuple[Optional[dataset.Dataset], statuses.Status]]:
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
        yield from service(request, 1)


def store(
        local_aet: str,
        remote_ae: asceprovider.RemoteAEConfig,
        ds: Union[str, dataset.Dataset]
) -> bool:
    """Stores a DICOM file or dataset in a remote Storage SCP

    :param local_aet: local AE title
    :param remote_ae: remote AE connection parameters
    :param ds: DICOM dataset or a path to file to store
    :return: `True` if file/dataset is successfully store, `False` otherwise
    """
    file_meta = filereader.read_file_meta_info(ds)
    sop_class = file_meta.MediaStorageSOPClassUID
    transfer_syntax = file_meta.TransferSyntax
    ae = applicationentity.ClientAE(local_aet, supported_ts=[transfer_syntax])
    ae.add_scu(sopclass.storage_scu, [sop_class])
    with ae.request_association(remote_ae) as assoc:
        service = assoc.get_scu(sop_class)
        result = cast(statuses.Status, service(ds, 1))
        return result.is_success
