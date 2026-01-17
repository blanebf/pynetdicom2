import argparse
import dataclasses
import pathlib
import sys
from typing import Callable, Iterable, Optional, Literal, Union

import pydicom
import pydicom.datadict
import pydicom.errors
import pydicom.valuerep
import pydicom.uid

from . import asceprovider, commands, uids


def main() -> None:
    """Main CLI routine"""
    parser = get_parser()
    args = parse_args(parser, sys.argv[1:])
    if not args.func:
        return

    for output in args.func(args):
        print(output)


@dataclasses.dataclass
class Args:
    """Dataclass for storing parsed arguments"""
    func: Optional[Callable[['Args'], Iterable[str]]] = None

    # Connection parameters
    local_aet: str = 'PYNETDICOM2'
    aet: str = 'AET'
    address: str = '127.0.0.1'
    port: int = 104

    username: Optional[str] = None
    password: Optional[str] = None
    kerberos: Optional[str] = None
    saml: Optional[str] = None
    jwt: Optional[str] = None

    # storage args
    file_or_dir: str = ''

    # root and level
    root: Literal['patient', 'study'] = 'study'
    level: Literal['patient', 'study', 'series', 'image'] = 'study'

    encoding: str = 'ISO_IR 192'

    # attributes
    attr: list[str] = dataclasses.field(default_factory=list)

    # SCP attributes
    local_port: Optional[int] = None
    storage_dir: Optional[str] = None

    # move attributes
    dest_aet: str = 'PYNETDICOM2'


def verify(args: Args) -> Iterable[str]:
    """Make a verification request sending a C-ECHO command

    :param args: parsed arguments
    :yield: verification output
    """
    remote_ae = _args_to_remote_ae(args)
    status = commands.verify(args.local_aet, remote_ae)
    yield f'Verification result {status}'


def find(args: Args) -> Iterable[str]:
    """Make a find request sending a C-FIND command

    :param args: parsed arguments
    :yield: find request output (resulting datasets)
    """
    remote_ae = _args_to_remote_ae(args)
    request = _parse_attrs(args.attr)
    request.QueryRetrieveLevel = args.level.upper()
    request.SpecificCharacterSet = args.encoding
    if args.root == 'patient':
        root = uids.PATIENT_ROOT_FIND_SOP_CLASS
    else:
        root = uids.STUDY_ROOT_FIND_SOP_CLASS
    for ds in commands.find(args.local_aet, remote_ae, request, root):
        yield f'C-FIND resposne:\n{ds}'


def store(args: Args) -> Iterable[str]:
    """Store a dataset or datasets from a directory (and its sub-directories)
    Files that can't be read as proper DICOM datasets are skipped

    :param args: parsed arguments
    :yield: store result(s)
    """
    remote_ae = _args_to_remote_ae(args)
    file_or_dir = pathlib.Path(args.file_or_dir)
    if not file_or_dir.is_dir():
        yield _store(args.local_aet, remote_ae, args.file_or_dir)
        return

    for filename in file_or_dir.glob('**/*'):
        if filename.is_dir():
            continue
        yield _store(args.local_aet, remote_ae, str(filename))


def _store(
        local_aet: str,
        remote_ae: asceprovider.RemoteAEConfig,
        filename: str
) -> str:
    try:
        status = commands.store(local_aet, remote_ae, filename)
        return f'Store result: {status}'
    except pydicom.errors.InvalidDicomError:
        return f'Invalid DICOM file {filename}, skipping'


def move(args: Args) -> Iterable[str]:
    remote_ae = _args_to_remote_ae(args)
    request = _parse_attrs(args.attr)
    request.QueryRetrieveLevel = args.level.upper()
    request.SpecificCharacterSet = args.encoding
    if args.root == 'patient':
        root = uids.PATIENT_ROOT_MOVE_SOP_CLASS
    else:
        root = uids.STUDY_ROOT_MOVE_SOP_CLASS
    if args.local_port and args.storage_dir:
        with commands.storage(
            pathlib.Path(args.storage_dir), args.local_aet, args.local_port
        ):
            yield _move(args, remote_ae, request, root)
    else:
        yield _move(args, remote_ae, request, root)


def _move(
        args: Args,
        remote_ae: asceprovider.RemoteAEConfig,
        request: pydicom.Dataset,
        root: pydicom.uid.UID
) -> str:
    results = commands.move(
        args.local_aet, remote_ae, request, args.dest_aet, root
    )
    return f'Move results: {results}'


def parse_args(parser: argparse.ArgumentParser, args: list[str]) -> Args:
    parsed_args = Args()
    return parser.parse_args(args, parsed_args)


def get_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        'pynetdicom2', usage='%(prog)s [command] [options]',
        description='pynetdicom2 CLI interface, providing simple ways '
        'to use DICOM network services',
    )
    subparsers = parser.add_subparsers(
        title='commands',
        description='available commands to use DICOM network services'
    )
    _create_verification_parser(subparsers)
    _create_find_parser(subparsers)
    _create_store_parser(subparsers)
    _create_move_parser(subparsers)
    return parser


def _create_verification_parser(
        subparsers: 'argparse._SubParsersAction[argparse.ArgumentParser]'
) -> None:
    parser = subparsers.add_parser(
        'verify',
        help='Run verification service sending C-ECHO to remote AET'
    )
    parser.set_defaults(func=verify)
    _add_conn_params(parser)


def _create_find_parser(
        subparsers: 'argparse._SubParsersAction[argparse.ArgumentParser]'
) -> None:
    parser = subparsers.add_parser(
        'find', help='Performer a find request and print results'
    )
    parser.set_defaults(func=find)
    _add_conn_params(parser)
    _add_root_and_level(parser)
    _add_attr(parser)
    _add_encoding(parser)


def _create_store_parser(
        subparsers: 'argparse._SubParsersAction[argparse.ArgumentParser]'
) -> None:
    parser = subparsers.add_parser(
        'store', help='Perform storage request from a provided file or folder'
    )
    parser.add_argument(
        '--file_or_dir', required=True,
        help='Path to a file or folder to store'
    )
    parser.set_defaults(func=store)
    _add_conn_params(parser)


def _create_move_parser(
        subparsers: 'argparse._SubParsersAction[argparse.ArgumentParser]'
) -> None:
    parser = subparsers.add_parser(
        'move', help='Perform a move request optionally receiving and'
        ' storing incoming datasets in a provided folder'
    )
    parser.set_defaults(func=move)
    parser.add_argument(
        '--local_port', default=None, type=int,
        help='Optional local port to start a storage SCP to receive incoming'
        ' datasets. Provide to actually receive incoming datasets.'
    )
    parser.add_argument(
        '--storage_dir', default=pathlib.Path.cwd(),
        help='Path where to store incoming datasets. Defaults to the '
        'current dir'
    )
    _add_conn_params(parser)
    _add_root_and_level(parser)
    _add_attr(parser)
    _add_encoding(parser)


def _add_conn_params(parser: argparse.ArgumentParser) -> None:
    parser.add_argument(
        '--local_aet', default='PYNETDICOM2', help='Local AE Title',
    )

    parser.add_argument('--aet', help='Remote AE Title', required=True)
    parser.add_argument('--address', help='Remote IP address', required=True)
    parser.add_argument('--port', type=int, help='Remote port', required=True)
    parser.add_argument(
        '--username', required=False, help='Username for DICOM authorization'
    )
    parser.add_argument(
        '--password', required=False, help='Password for DICOM authorization'
    )
    parser.add_argument(
        '--kerberos', required=False,
        help='Kerboros key for DICOM authorization'
    )
    parser.add_argument(
        '--saml', required=False,
        help='SAML key for DICOM authorization'
    )
    parser.add_argument(
        '--jwt', required=False,
        help='JWT for DICOM authorization'
    )


def _add_root_and_level(parser: argparse.ArgumentParser) -> None:
    parser.add_argument(
        '--level',
        choices=['patient', 'study', 'series', 'image'],
        default='study',
        help='level of the request: patient, study, series or image'
    )
    parser.add_argument(
        '--root',
        choices=['patient', 'study'],
        default='study',
        help='request root (either patient or study)'
    )


def _add_encoding(parser: argparse.ArgumentParser) -> None:
    parser.add_argument(
        '--encoding', default='ISO_IR 192',
        help='Character set encoding to use. Defaults to UTF-8'
    )


def _add_attr(parser: argparse.ArgumentParser) -> None:
    parser.add_argument(
        '--attr', nargs='*', action='extend',
        help='Search attribute in the following format: '
        '<Attribute Name or Tag value>=<Attribute value>. For example: '
        'PatientName=Test^Patient^Name or 00100010=Test^Patient^Name'
    )


def _args_to_remote_ae(args: Args) -> asceprovider.RemoteAEConfig:
    remote_ae = asceprovider.RemoteAEConfig(
        aet=args.aet,
        address=args.address,
        port=args.port,
        username=args.username,
        password=args.password,
        kerberos=args.kerberos,
        saml=args.saml,
        jwt=args.jwt
    )
    return remote_ae


def _parse_attrs(attrs: list[str]) -> pydicom.Dataset:
    ds = pydicom.Dataset()
    for attr_and_value in attrs:
        attr, value = attr_and_value.split('=')
        vr, _, _, _, keyword = pydicom.datadict.get_entry(
            _convert_tag(attr.strip())
        )
        parsed_value = _convert_value(vr, value.strip())
        setattr(ds, keyword, parsed_value)
    return ds


def _convert_tag(attr: str) -> Union[str, int]:
    try:
        return int(attr, base=16)
    except ValueError:
        return attr


def _convert_value(vr: str, value: str) -> Union[str, float, int, None]:
    if not value:
        return None
    if vr in pydicom.valuerep.INT_VR:
        return int(value)
    if vr in pydicom.valuerep.FLOAT_VR:
        return float(value)
    return value
