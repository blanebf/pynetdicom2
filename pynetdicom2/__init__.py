"""Package "entry point". Provides most of commonly used classes and functions
from overall pynetdicom2 package.
"""
from . import __version__

__version_info__ = __version__.__version__.split('.')


# convenience imports
from .applicationentity import (  # noqa F401
    AE,
    ClientAE,
    ClientStorageAE,
    StorageAE
)
from .commands import (  # noqa F401
    CMoveResponse,
    find,
    move,
    storage,
    store,
    verify
)
from .asceprovider import (  # noqa F401
    AssociationAcceptor, AssociationRequester
)
from .fsm import PContextDef  # noqa F401
from .sopclass import (  # noqa F401
    verification_scp,
    verification_scu,
    storage_scp,
    storage_scu,
    qr_find_scp,
    qr_find_scu,
    qr_move_scp,
    qr_move_scu,
    qr_get_scu,
    modality_work_list_scp,
    modality_work_list_scu,
    StorageCommitment,
    storage_commitment_scu
)
from .statuses import (  # noqa F401
    Status,
    SUCCESS,
    PROCESSING_FAILURE
)

__all__ = [
    # application entities
    'AE',
    'ClientAE',
    'ClientStorageAE',
    'StorageAE',
    # high-level commands
    'CMoveResponse',
    'find',
    'move',
    'storage',
    'store',
    'verify',
    # associations
    'AssociationAcceptor',
    'AssociationRequester',
    'PContextDef',
    # service classes
    'verification_scp',
    'verification_scu',
    'storage_scp',
    'storage_scu',
    'qr_find_scp',
    'qr_find_scu',
    'qr_move_scp',
    'qr_move_scu',
    'qr_get_scu',
    'modality_work_list_scp',
    'modality_work_list_scu',
    'StorageCommitment',
    'storage_commitment_scu',
    # statuses
    'Status',
    'SUCCESS',
    'PROCESSING_FAILURE',
]
