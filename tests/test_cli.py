"""Unit tests for :mod:`pynetdicom2.cli` argument parsing and helpers.

None of these tests perform any network I/O: they exercise the pure argument
parsing and conversion logic only.
"""
import contextlib
import io
import sys
import unittest
from collections.abc import Iterable
from unittest import mock

from pydicom import dataset, uid

from pynetdicom2 import asceprovider, cli, commands
from pynetdicom2 import uids


def _parse(argv: list[str]) -> cli.Args:
    return cli.parse_args(cli.get_parser(), argv)


class ParserWiringTestCase(unittest.TestCase):
    def test_no_command_leaves_func_none(self) -> None:
        args = _parse([])
        self.assertIsNone(args.func)

    def test_verify_command(self) -> None:
        args = _parse(
            ['verify', '--aet', 'AET2', '--address', '1.2.3.4', '--port', '11']
        )
        self.assertIs(args.func, cli.verify)
        self.assertEqual(args.aet, 'AET2')
        self.assertEqual(args.address, '1.2.3.4')
        self.assertEqual(args.port, 11)

    def test_find_command_defaults(self) -> None:
        args = _parse(
            ['find', '--aet', 'A', '--address', 'h', '--port', '104']
        )
        self.assertIs(args.func, cli.find)
        self.assertEqual(args.level, 'study')
        self.assertEqual(args.root, 'study')

    def test_store_requires_file_or_dir(self) -> None:
        with self.assertRaises(SystemExit):
            _parse(['store', '--aet', 'A', '--address', 'h', '--port', '1'])

    def test_store_command(self) -> None:
        args = _parse(
            ['store', '--file_or_dir', '/tmp/x', '--aet', 'A',
             '--address', 'h', '--port', '1']
        )
        self.assertIs(args.func, cli.store)
        self.assertEqual(args.file_or_dir, '/tmp/x')

    def test_move_command(self) -> None:
        args = _parse(
            ['move', '--aet', 'A', '--address', 'h', '--port', '1',
             '--local_port', '2000', '--root', 'patient']
        )
        self.assertIs(args.func, cli.move)
        self.assertEqual(args.local_port, 2000)
        self.assertEqual(args.root, 'patient')


class RemoteAeConversionTestCase(unittest.TestCase):
    def test_args_to_remote_ae(self) -> None:
        args = _parse(
            ['verify', '--aet', 'AET2', '--address', '10.0.0.1',
             '--port', '11112', '--username', 'admin', '--password', 'pw']
        )
        remote = cli._args_to_remote_ae(args)
        self.assertEqual(remote.aet, 'AET2')
        self.assertEqual(remote.address, '10.0.0.1')
        self.assertEqual(remote.port, 11112)
        self.assertEqual(remote.username, 'admin')
        self.assertEqual(remote.password, 'pw')


class AttributeParsingTestCase(unittest.TestCase):
    def test_convert_tag_hex(self) -> None:
        self.assertEqual(cli._convert_tag('00100010'), 0x00100010)

    def test_convert_tag_keyword(self) -> None:
        self.assertEqual(cli._convert_tag('PatientName'), 'PatientName')

    def test_convert_value_empty_is_none(self) -> None:
        self.assertIsNone(cli._convert_value('LO', ''))

    def test_convert_value_int(self) -> None:
        self.assertEqual(cli._convert_value('US', '5'), 5)

    def test_convert_value_float(self) -> None:
        self.assertEqual(cli._convert_value('FL', '1.5'), 1.5)

    def test_convert_value_str(self) -> None:
        self.assertEqual(cli._convert_value('LO', 'abc'), 'abc')

    def test_parse_attrs_by_keyword(self) -> None:
        ds = cli._parse_attrs(['PatientName=Doe^John'])
        self.assertEqual(ds.PatientName, 'Doe^John')

    def test_parse_attrs_by_tag(self) -> None:
        ds = cli._parse_attrs(['00100020=ID-1'])
        self.assertEqual(ds.PatientID, 'ID-1')

    def test_parse_attrs_multiple(self) -> None:
        ds = cli._parse_attrs(
            ['PatientName=Doe^John', 'PatientID=ID-1']
        )
        self.assertEqual(ds.PatientName, 'Doe^John')
        self.assertEqual(ds.PatientID, 'ID-1')

    def test_convert_tag_comma_format(self) -> None:
        self.assertEqual(cli._convert_tag('0010,0010'), 0x00100010)

    def test_parse_attrs_rejects_missing_equals(self) -> None:
        with self.assertRaises(ValueError):
            cli._parse_attrs(['NoEqualsSign'])

    def test_parse_attrs_rejects_unknown_attribute(self) -> None:
        with self.assertRaises(ValueError):
            cli._parse_attrs(['NotARealDICOMAttribute=value'])

    def test_parse_attrs_value_may_contain_equals(self) -> None:
        ds = cli._parse_attrs(['PatientName=Doe=John'])
        self.assertEqual(ds.PatientName, 'Doe=John')


class StorageDirDefaultTestCase(unittest.TestCase):
    def test_storage_dir_defaults_to_none(self) -> None:
        # The default must not be evaluated at parser construction time.
        args = _parse(
            ['move', '--aet', 'A', '--address', 'h', '--port', '1']
        )
        self.assertIsNone(args.storage_dir)


class MainNoCommandTestCase(unittest.TestCase):
    def test_main_without_command_exits_nonzero(self) -> None:
        with mock.patch.object(sys, 'argv', ['pynetdicom2']):
            with contextlib.redirect_stdout(io.StringIO()) as output:
                with self.assertRaises(SystemExit) as ctx:
                    cli.main()
        self.assertEqual(ctx.exception.code, 1)
        self.assertIn('usage', output.getvalue())


class FindRootSelectionTestCase(unittest.TestCase):
    """`find` chooses the Q/R root SOP class based on the --root argument."""

    def test_patient_root(self) -> None:
        args = _parse(
            ['find', '--aet', 'A', '--address', 'h', '--port', '1',
             '--root', 'patient', '--attr', 'PatientName=X']
        )
        captured: dict[str, object] = {}

        def fake_find(
                local_aet: str,
                remote_ae: asceprovider.RemoteAEConfig,
                request: dataset.Dataset,
                root: uid.UID = uids.STUDY_ROOT_FIND_SOP_CLASS
        ) -> Iterable[dataset.Dataset]:
            captured['root'] = root
            captured['level'] = request.QueryRetrieveLevel
            return iter([])

        original = commands.find
        commands.find = fake_find
        try:
            list(cli.find(args))
        finally:
            commands.find = original

        self.assertEqual(captured['root'], uids.PATIENT_ROOT_FIND_SOP_CLASS)


if __name__ == '__main__':
    unittest.main()
