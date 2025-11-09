from typing import Callable, Iterable, Optional, cast

from pydicom import dataset, filereader, uid

from . import applicationentity, asceprovider, sopclass, statuses, uids


BoundFind = Callable[
    [dataset.Dataset, int],
    Iterable[tuple[Optional[dataset.Dataset], statuses.Status]]
]


def verify(local_aet: str, remote_ae: asceprovider.RemoteAEConfig) -> bool:
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
    ae = applicationentity.ClientAE(local_aet)
    ae.add_scu(sopclass.qr_find_scu)
    with ae.request_association(remote_ae) as assoc:
        service = cast(BoundFind, assoc.get_scu(root))
        yield from service(request, 1)


def store(
        local_aet: str,
        remote_ae: asceprovider.RemoteAEConfig,
        file_name: str
) -> bool:
    file_meta = filereader.read_file_meta_info(file_name)
    sop_class = file_meta.MediaStorageSOPClassUID
    transfer_syntax = file_meta.TransferSyntax
    ae = applicationentity.ClientAE(local_aet, supported_ts=[transfer_syntax])
    ae.add_scu(sopclass.storage_scu, [sop_class])
    with ae.request_association(remote_ae) as assoc:
        service = assoc.get_scu(sop_class)
        result = cast(statuses.Status, service(file_name, 1))
        return result.is_success
