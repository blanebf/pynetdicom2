# Copyright (c) 2021 Pavel 'Blane' Tuchin
# Copyright (c) 2012 Patrice Munger
# This file is part of pynetdicom, released under a modified MIT license.
#    See the file license.txt included with this distribution, also
#    available at https://github.com/blanebf/pynetdicom2
#

"""
Module contains implementation of the DICOM Protocol Data Units (or PDU for
short). Each PDU is represented by class that follows the simple interface that
has only two methods:

    * ``encode`` - method that transforms PDU into raw byte string
    * ``decode`` - factory method that transforms raw byte string to PDU
      instance

In addition to PDUs, several items and sub-items classes can be found in this
module. These classes are:

        * :class:`~pynetdicom2.pdu.ApplicationContextItem`
        * :class:`~pynetdicom2.pdu.PresentationContextItemRQ`
        * :class:`~pynetdicom2.pdu.AbstractSyntaxSubItem`
        * :class:`~pynetdicom2.pdu.TransferSyntaxSubItem`
        * :class:`~pynetdicom2.pdu.UserInformationItem`
        * :class:`~pynetdicom2.pdu.PresentationContextItemAC`
        * :class:`~pynetdicom2.pdu.PresentationDataValueItem`

The rest sub-items for User Data Information Item can be found at
:doc:`userdataitems`.
"""
import struct
from io import BytesIO
from typing import ClassVar, Iterable, Optional, Type, Union, cast

from pydicom import uid

from . import exceptions, userdataitems


UserItem = Union[
    userdataitems.ImplementationClassUIDSubItem,
    userdataitems.MaximumLengthSubItem,
    userdataitems.ImplementationVersionNameSubItem,
    userdataitems.AsynchronousOperationsWindowSubItem,
    userdataitems.ScpScuRoleSelectionSubItem,
    userdataitems.SOPClassExtendedNegotiationSubItem,
    userdataitems.UserIdentityNegotiationSubItem,
    userdataitems.UserIdentityNegotiationSubItemAc,
    userdataitems.GenericUserDataSubItem
]


SUB_ITEM_TYPES: dict[int, Type[UserItem]] = {
    0x52: userdataitems.ImplementationClassUIDSubItem,
    0x51: userdataitems.MaximumLengthSubItem,
    0x55: userdataitems.ImplementationVersionNameSubItem,
    0x53: userdataitems.AsynchronousOperationsWindowSubItem,
    0x54: userdataitems.ScpScuRoleSelectionSubItem,
    0x56: userdataitems.SOPClassExtendedNegotiationSubItem,
    0x58: userdataitems.UserIdentityNegotiationSubItem,
    0x59: userdataitems.UserIdentityNegotiationSubItemAc
}


def _next_type(stream: BytesIO) -> Optional[int]:
    char = stream.read(1)
    if char == b'':
        return None  # we are at the end of the file
    stream.seek(-1, 1)
    return cast(int, struct.unpack('B', char)[0])


def _read_exact(stream: BytesIO, length: int) -> bytes:
    """Reads exactly ``length`` bytes from a data stream.

    Length fields of received items are untrusted peer data: reading without
    verifying the result would silently accept truncated items and shift the
    parsing of everything that follows.

    :param stream: raw data stream
    :param length: number of bytes to read
    :return: read bytes
    :raises exceptions.PDUProcessingError: if the stream is truncated and
        does not contain the requested amount of data
    """
    data = stream.read(length)
    if len(data) != length:
        raise exceptions.PDUProcessingError(
            f'PDU is truncated: expected {length} bytes, got {len(data)}'
        )
    return data


def _decode_ae_title(raw: bytes) -> str:
    """Decodes a fixed 16-byte AE title field (PS3.8 9.3.2).

    AE titles are padded with spaces (some implementations pad with NULL
    bytes) and shall consist of characters from the default character
    repertoire (ISO IR 6 / printable ASCII).

    :param raw: raw 16-byte field
    :return: decoded AE title without padding
    :raises exceptions.PDUProcessingError: if the title contains characters
        outside the default character repertoire
    """
    title = raw.strip(b' \0')
    for char in title:
        if not 0x20 <= char <= 0x7e:
            raise exceptions.PDUProcessingError(
                'Invalid AE title: contains characters outside the '
                f'default character repertoire: {title!r}'
            )
    return title.decode('ascii')


class AAssociatePDUBase:
    """Base class for A-ASSOCIATE-RQ and A-ASSOCIATE-AC PDUs

    :ivar called_ae_title: called AE Title (remote AET)
    :ivar calling_ae_title: calling AE Title (local AET)
    :ivar variable_items: list of various variable items
    :ivar protocol_version: protocol version, should be 1
    :ivar reserved1: reserved field, defaults 0
    :ivar reserved2: reserved field, defaults 0
    :ivar reserved3: reserved field, defaults eight 0
    """
    pdu_type: ClassVar[int]
    header = struct.Struct('>B B I H H 16s 16s 8I')

    def __init__(
            self,
            called_ae_title: str,
            calling_ae_title: str,
            variable_items: list['VariableItems'],
            protocol_version: int = 1,
            reserved1: int = 0x00,
            reserved2: int = 0x00,
            reserved3: Optional[Iterable[int]] = None
    ) -> None:
        self.called_ae_title = called_ae_title  # string of length 16
        self.calling_ae_title = calling_ae_title  # string of length 16
        self.variable_items = variable_items
        self.protocol_version = protocol_version  # unsigned short
        self.reserved1 = reserved1  # unsigned byte
        self.reserved2 = reserved2  # unsigned short
        if not reserved3:  # 32 bytes
            self.reserved3: Iterable[int] = (0, 0, 0, 0, 0, 0, 0, 0)
        else:
            self.reserved3 = reserved3

    @property
    def pdu_length(self) -> int:
        """PDU length without the header

        :return: PDU length
        """
        return 68 + sum((i.total_length() for i in self.variable_items))

    def encode(self) -> bytes:
        """Encodes PDU into bytes

        :return: encoded PDU
        """
        called_ae_title = self.called_ae_title.encode()
        calling_ae_title = self.calling_ae_title.encode()
        return self.header.pack(
            self.pdu_type,
            self.reserved1,
            self.pdu_length,
            self.protocol_version,
            self.reserved2,
            called_ae_title,
            calling_ae_title,
            *self.reserved3
        ) + b''.join([item.encode() for item in self.variable_items])

    @classmethod
    def decode(cls, raw_bytes: bytes) -> 'AAssociatePDUBase':
        """Factory method. Decodes A-ASSOCIATE-RQ PDU instance from raw string.

        :param raw_bytes: bytes containing binary representation of the
                          A-ASSOCIATE-RQ PDU
        :return: decoded PDU
        """
        def iter_items() -> Iterable[VariableItems]:
            item_type = _next_type(stream)
            while item_type:
                if item_type == 0x10:
                    yield ApplicationContextItem.decode(stream)
                elif item_type == 0x20:
                    yield PresentationContextItemRQ.decode(stream)
                elif item_type == 0x21:
                    yield PresentationContextItemAC.decode(stream)
                elif item_type == 0x50:
                    yield UserInformationItem.decode(stream)
                else:
                    raise exceptions.PDUProcessingError(
                        'Invalid variable item'
                    )
                item_type = _next_type(stream)

        stream = BytesIO(raw_bytes)
        values = cls.header.unpack(stream.read(74))
        _, reserved1, _, protocol_version, reserved2, \
            called_ae_title, calling_ae_title = values[:7]
        reserved3 = values[7:]
        called_ae_title = _decode_ae_title(called_ae_title)
        calling_ae_title = _decode_ae_title(calling_ae_title)
        variable_items = list(iter_items())
        return cls(
            called_ae_title=called_ae_title,
            calling_ae_title=calling_ae_title,
            variable_items=variable_items,
            protocol_version=protocol_version,
            reserved1=reserved1,
            reserved2=reserved2,
            reserved3=reserved3
        )

    def total_length(self) -> int:
        """Returns total PDU length including the header

        :return: total PDU length
        """
        return 6 + self.pdu_length


class AAssociateRqPDU(AAssociatePDUBase):
    """This class represents the A-ASSOCIATE-RQ PDU

    Refer to DICOM PS3.8 9.3.2 for A-ASSOCIATE-RQ structure and fields"""

    pdu_type = 0x01
    """PDU Type"""

    def __repr__(self) -> str:
        return (
            f'AAssociateRqPDU(called_ae_title="{self.called_ae_title}", '
            f'calling_ae_title="{self.calling_ae_title}", '
            f'variable_items={self.variable_items}, '
            f'protocol_version={self.protocol_version}, '
            f'reserved1={self.reserved1}, reserved2={self.reserved2}, '
            f'reserved3={self.reserved3})'
        )


class AAssociateAcPDU(AAssociatePDUBase):
    """This class represents the A-ASSOCIATE-AC PDU

    Refer to DICOM PS3.8 9.3.3 for A-ASSOCIATE-AC structure and fields"""

    pdu_type = 0x02
    """PDU Type"""

    def __repr__(self) -> str:
        return (
            f'AAssociateAcPDU(called_ae_title="{self.called_ae_title}", '
            f'calling_ae_title="{self.calling_ae_title}", '
            f'variable_items={self.variable_items}, '
            f'protocol_version={self.protocol_version}, '
            f'reserved1={self.reserved1}, reserved2={self.reserved2}, '
            f'reserved3={self.reserved3})'
        )


class AAssociateRjPDU:
    """This class represents the A-ASSOCIATE-RJ PDU (PS 3.8 9.3.4)

    You can look up possible values for fields in DICOM standard
    (referenced above) or in documentation for
    :class:`~pynetdicom2.exceptions.AssociationRejectedError`

    :ivar result: Result PDU field. (unsigned byte)
    :ivar source: Source PDU field (unsigned byte)
    :ivar reason_diag: Reason/Diag. PDU field (unsigned byte)
    :ivar reserved1: Reserved field, defaults to 0 (unsigned byte)
    :ivar reserved2: Reserved field, defaults to 0 (unsigned byte)
    """

    pdu_type = 0x03
    """PDU Type"""

    pdu_length = 4
    """This PDU has fixed length of 4 bytes"""

    format = struct.Struct('>B B I B B B B')

    def __init__(
            self,
            result: int,
            source: int,
            reason_diag: int,
            reserved1: int = 0x00,
            reserved2: int = 0x00
    ) -> None:
        """
        Initializes new ASSOCIATE-RJ PDU with specified field values
        as described in PS 3.8 9.3.4.
        """

        self.reserved1 = reserved1
        self.reserved2 = reserved2
        self.result = result
        self.source = source
        self.reason_diag = reason_diag

    def __repr__(self) -> str:
        return (
            f'AAssociateRjPDU(result={self.result}, '
            f'source={self.source}, '
            f'reason_diag={self.reason_diag},'
            f' reserved1={self.reserved1}, '
            f'reserved2={self.reserved2})'
        )

    def encode(self) -> bytes:
        """Converts PDU class to its binary representation

        :return: PDU as a string of bytes
        """
        return self.format.pack(
            self.pdu_type,
            self.reserved1,
            self.pdu_length,
            self.reserved2,
            self.result,
            self.source,
            self.reason_diag
        )

    @classmethod
    def decode(cls, rawstring: bytes) -> 'AAssociateRjPDU':
        """Factory method. Decodes A-ASSOCIATE-RJ PDU instance from raw string.

        :param rawstring: rawstring containing binary representation of the
                          A-ASSOCIATE-RJ PDU
        :return: decoded PDU
        """
        stream = BytesIO(rawstring)
        _, reserved1, _, reserved2, result, source, \
            reason_diag = cls.format.unpack(stream.read(10))
        return cls(
            result=result,
            source=source,
            reason_diag=reason_diag,
            reserved1=reserved1,
            reserved2=reserved2
        )

    @staticmethod
    def total_length() -> int:
        """Returns PDU total length.

        This PDU has a fixed length of 10, so method always returns 10
        regardless of specific instance

        :return: PDU total length
        """
        return 10


class PDataTfPDU:
    """This class represents the P-DATA-TF PDU (as described in PS 3.8 9.3.5).

    :ivar reserved: reserved field, defaults 0
    :ivar data_value_items: list of one of more PresentationDataValueItem
    """

    pdu_type = 0x04
    """PDU Type"""

    header = struct.Struct('>B B I')

    def __init__(
            self,
            data_value_items: list['PresentationDataValueItem'],
            reserved: int = 0x00
    ) -> None:
        self.reserved = reserved  # unsigned byte

        # List of one of more PresentationDataValueItem
        self.data_value_items = data_value_items

    def __repr__(self) -> str:
        return (
            f'PDataTfPDU(pdu_length={self.pdu_length}, '
            f'data_value_items='
            f'{self.data_value_items}, '
            f'reserved={self.reserved})'
        )

    @property
    def pdu_length(self) -> int:
        """PDU length without the header

        :return: PDU length
        """
        return sum((i.total_length() for i in self.data_value_items))

    def encode(self) -> bytes:
        """Encodes PDataTfPDU into bytes

        :return: encoded PDU
        """
        return self.header.pack(
            self.pdu_type,
            self.reserved,
            self.pdu_length
        ) + b''.join(item.encode() for item in self.data_value_items)

    @classmethod
    def decode(cls, rawstring: bytes) -> 'PDataTfPDU':
        """Factory method. Decodes P-DATA-TF PDU instance from raw string.

        :param rawstring: rawstring containing binary representation of the
                          P-DATA-TF PDU
        :return: decoded PDU
        """
        def iter_items() -> Iterable[PresentationDataValueItem]:
            length_read = 0
            while length_read != pdu_length:
                item = PresentationDataValueItem.decode(stream)
                length_read += item.total_length()
                yield item

        stream = BytesIO(rawstring)
        _, reserved, pdu_length = cls.header.unpack(stream.read(6))
        data_value_items = list(iter_items())
        return cls(data_value_items, reserved)

    def total_length(self) -> int:
        """Returns total PDU length including the header

        :return: total PDU length
        """
        return 6 + self.pdu_length


class AReleasePDUBase:
    """Base class for the A-RELEASE-* PDUs.

    :ivar reserved1: reserved field, defaults 0
    :ivar reserved2: reserved field, defaults 0
    """

    pdu_type: ClassVar[int]
    pdu_length = 4
    """Association Release PDUs have fixed length of 4 bytes"""

    format = struct.Struct('>B B I I')

    def __init__(self, reserved1: int = 0x00, reserved2: int = 0x00) -> None:
        self.reserved1 = reserved1  # unsigned byte
        self.reserved2 = reserved2  # unsigned int

    def __repr__(self) -> str:
        return (
            'AReleaseRqPDU('
            f'reserved1={self.reserved1}, '
            f'reserved2={self.reserved2})'
        )

    def encode(self) -> bytes:
        """Encodes PDU into bytes

        :return: encoded PDU
        """
        return self.format.pack(
            self.pdu_type,
            self.reserved1,
            self.pdu_length,
            self.reserved2
        )

    @classmethod
    def decode(cls, rawstring: bytes) -> 'AReleasePDUBase':
        """Factory method. Decodes A-RELEASE-* PDU instance from raw string.

        :param rawstring: rawstring containing binary representation of the
                          A-RELEASE-* PDU
        :return: decoded PDU
        """
        stream = BytesIO(rawstring)
        _, reserved1, _, reserved2 = cls.format.unpack(stream.read(10))
        return cls(reserved1=reserved1, reserved2=reserved2)

    @staticmethod
    def total_length() -> int:
        """Returns PDU total length.

        This PDU has a fixed length of 10, so method always returns 10
        regardless of specific instance

        :return: PDU total length
        """
        return 10


class AReleaseRqPDU(AReleasePDUBase):
    """This class represents the A-RELEASE-RQ PDU as described in
    PS 3.8 9.3.6
    """

    pdu_type = 0x05
    """PDU Type"""

    def __repr__(self) -> str:
        return (
            'AReleaseRqPDU('
            f'reserved1={self.reserved1}, '
            f'reserved2={self.reserved2})'
        )


class AReleaseRpPDU(AReleasePDUBase):
    """This class represents the A-RELEASE-RP PDU as described in
    PS 3.8 9.3.7
    """

    pdu_type = 0x06
    """PDU Type"""

    def __repr__(self) -> str:
        return (
            'AReleaseRpPDU('
            f'reserved1={self.reserved1}, '
            f'reserved2={self.reserved2})'
        )


class AAbortPDU:
    """This class represents the A-ABORT PDU as described in PS 3.8 9.3.8

    :ivar reserved1: reserved field, defaults 0
    :ivar reserved2: reserved field, defaults 0
    :ivar reserved3: reserved field, defaults 0
    :ivar reserved3: reserved field, defaults 0
    :ivar source: abort source:

                        * 0 - DICOM UL service-user (initiated abort)
                        * 1 - reserved
                        * 2 - DICOM UL service-provider (initiated abort)
    :ivar reason_diag: Reason/Diag. value:

                        * 0 - reason-not-specified
                        * 1 - unrecognized-PDU
                        * 2 - unexpected-PDU
                        * 3 - reserved
                        * 4 - unrecognized-PDU parameter
                        * 5 - unexpected-PDU parameter
                        * 6 - invalid-PDU-parameter value
    """
    pdu_type = 0x07
    """PDU Type"""

    pdu_length = 4
    """Association Abort PDU have fixed length of 4 bytes"""

    format = struct.Struct('>B B I B B B B')

    def __init__(
            self,
            source: int,
            reason_diag: int,
            reserved1: int = 0x00,
            reserved2: int = 0x00,
            reserved3: int = 0x00
    ) -> None:
        self.reserved1 = reserved1  # unsigned byte
        self.reserved2 = reserved2  # unsigned byte
        self.reserved3 = reserved3  # unsigned byte
        self.source = source  # unsigned byte
        self.reason_diag = reason_diag  # unsigned byte

    def __repr__(self) -> str:
        return (
            f'AAbortPDU(source={self.source}, '
            f'reason_diag={self.reason_diag}, '
            f'reserved1={self.reserved1}, '
            f'reserved2={self.reserved2}, '
            f'reserved3={self.reserved3})'
        )

    def encode(self) -> bytes:
        """Encodes AAbortPDU into bytes

        :return: encoded PDU
        """
        return self.format.pack(
            self.pdu_type,
            self.reserved1,
            self.pdu_length,
            self.reserved2,
            self.reserved3,
            self.source,
            self.reason_diag
        )

    @classmethod
    def decode(cls, rawstring: bytes) -> 'AAbortPDU':
        """Factory method. Decodes A-ABORT PDU instance from raw string.

        :param rawstring: rawstring containing binary representation of
                          the A-ABORT PDU
        :return: decoded PDU
        """
        stream = BytesIO(rawstring)
        _, reserved1, _, reserved2, reserved3, abort_source, \
            reason_diag = cls.format.unpack(stream.read(10))
        return cls(
            reserved1=reserved1,
            reserved2=reserved2,
            reserved3=reserved3,
            source=abort_source,
            reason_diag=reason_diag
        )

    @staticmethod
    def total_length() -> int:
        """Returns PDU total length.

        This PDU has a fixed length of 10, so method always returns 10
        regardless of specific instance

        :return: PDU total length
        """
        return 10


# Items and sub-items classes


class ApplicationContextItem:
    """Application Context Item (PS 3.8 9.3.2.1)

    :ivar reserved: reserved field, defaults 0
    :ivar context_name: application context name (OID)
    """

    item_type = 0x10
    """PDU Item-type"""

    header = struct.Struct('> B B H')

    def __init__(self, context_name: str, reserved: int = 0x00) -> None:
        self.reserved = reserved  # unsigned byte
        self.context_name = context_name  # string

    def __repr__(self) -> str:
        return (
            'ApplicationContextItem(context_name="{self.context_name}", '
            f'reserved={self.reserved})'
        )

    @property
    def item_length(self) -> int:
        """Item length, excluding the header

        :return: item length
        """
        return len(self.context_name)

    def encode(self) -> bytes:
        """Encodes item into bytes

        :return: encoded item
        """
        return self.header.pack(
            self.item_type,
            self.reserved,
            self.item_length
        ) + self.context_name.encode()

    @classmethod
    def decode(cls, stream: BytesIO) -> 'ApplicationContextItem':
        """Decodes application context item from data stream

        :param stream: raw data stream
        :return: decoded item
        """
        _, reserved, item_length = cls.header.unpack(stream.read(4))
        context_name = _read_exact(stream, item_length).decode()
        return cls(reserved=reserved, context_name=context_name)

    def total_length(self) -> int:
        """Total item length, including the header

        :return: total item length
        """
        return 4 + self.item_length


class PresentationContextItemRQ:
    """Presentation Context Item (request) PS 3.8 9.3.2.2

    :ivar context_id: presentation context ID
    :ivar abs_sub_item: Abstract Syntax sub-item
    :ivar ts_sub_items: list of Transfer Syntax sub-items
    :ivar reserved1: reserved field, defaults 0
    :ivar reserved2: reserved field, defaults 0
    :ivar reserved3: reserved field, defaults 0
    :ivar reserved4: reserved field, defaults 0
    """

    item_type = 0x20
    """PDU Item-type"""

    header = struct.Struct('>B B H B B B B')

    def __init__(
            self,
            context_id: int,
            abs_sub_item: 'AbstractSyntaxSubItem',
            ts_sub_items: list['TransferSyntaxSubItem'],
            reserved1: int = 0x00,
            reserved2: int = 0x00,
            reserved3: int = 0x00,
            reserved4: int = 0x00
    ) -> None:
        self.context_id = context_id  # unsigned byte
        self.abs_sub_item = abs_sub_item  # AbstractSyntaxSubItem
        self.ts_sub_items = ts_sub_items  # TransferSyntaxSubItems

        self.reserved1 = reserved1  # unsigned byte
        self.reserved2 = reserved2  # unsigned byte
        self.reserved3 = reserved3  # unsigned byte
        self.reserved4 = reserved4  # unsigned byte

    def __repr__(self) -> str:
        return (
            f'PresentationContextItemRQ(context_id={self.context_id}, '
            f'abs_sub_item={self.abs_sub_item}, '
            f'ts_sub_items={self.ts_sub_items}, '
            f'reserved1={self.reserved1}, reserved2={self.reserved2}, '
            f'reserved3={self.reserved3}, '
            f'reserved4={self.reserved4})'
        )

    @property
    def item_length(self) -> int:
        """Item length, excluding the header

        :return: item length
        """
        return 4 + (self.abs_sub_item.total_length() +
                    sum(i.total_length() for i in self.ts_sub_items))

    def encode(self) -> bytes:
        """Encodes item into bytes

        :return: encoded item
        """
        return (
            self.header.pack(
                self.item_type,
                self.reserved1,
                self.item_length,
                self.context_id,
                self.reserved2,
                self.reserved3,
                self.reserved4
            ) +
            self.abs_sub_item.encode() +
            b''.join([item.encode() for item in self.ts_sub_items])
        )

    @classmethod
    def decode(cls, stream: BytesIO) -> 'PresentationContextItemRQ':
        """Decodes presentation context item 'request' from data stream

        :param stream: raw data stream
        :return: decoded context item
        """
        def iter_items() -> Iterable[TransferSyntaxSubItem]:
            while _next_type(stream) == 0x40:
                yield TransferSyntaxSubItem.decode(stream)

        _, reserved1, _, context_id, \
            reserved2, reserved3, reserved4 = cls.header.unpack(stream.read(8))
        abs_sub_item = AbstractSyntaxSubItem.decode(stream)
        ts_sub_items = list(iter_items())
        return cls(
            context_id=context_id,
            abs_sub_item=abs_sub_item,
            ts_sub_items=ts_sub_items,
            reserved1=reserved1,
            reserved2=reserved2,
            reserved3=reserved3,
            reserved4=reserved4
        )

    def total_length(self) -> int:
        """Total item length, including the header

        :return: total item length
        """
        return 4 + self.item_length


class PresentationContextItemAC:
    """Presentation Context Item (response) PS 3.8 9.3.3.2

    :ivar context_id:
    :ivar result_reason: result/reason, can be one of the following:

                                * 0 - acceptance
                                * 1 - user-rejection
                                * 2 - no-reason (provider rejection)
                                * 3 - abstract-syntax-not-supported (provider rejection)
                                * 4 - transfer-syntaxes-not-supported (provider rejection)

    :ivar ts_sub_item: list of Transfer Syntax sub-items
    :ivar reserved1: reserved field, defaults 0
    :ivar reserved2: reserved field, defaults 0
    :ivar reserved3: reserved field, defaults 0
    """  # noqa E501

    item_type = 0x21
    """PDU Item-type"""

    header = struct.Struct('>B B H B B B B')

    def __init__(
            self,
            context_id: int,
            result_reason: int,
            ts_sub_item: 'TransferSyntaxSubItem',
            reserved1: int = 0x00,
            reserved2: int = 0x00,
            reserved3: int = 0x00
    ) -> None:
        self.context_id = context_id  # unsigned byte
        self.result_reason = result_reason  # unsigned byte
        self.ts_sub_item = ts_sub_item  # TransferSyntaxSubItem object

        self.reserved1 = reserved1  # unsigned byte
        self.reserved2 = reserved2  # unsigned byte
        self.reserved3 = reserved3  # unsigned byte

    def __repr__(self) -> str:
        return (
            'PresentationContextItemAC('
            f'context_id={self.context_id}, '
            f'result_reason={self.result_reason}, '
            f'ts_sub_item={self.ts_sub_item}, '
            f'reserved1={self.reserved1}, '
            f'reserved2={self.reserved2}, '
            f'reserved3={self.reserved3})'
        )

    @property
    def item_length(self) -> int:
        """Item length, excluding the header

        :return: item length
        """
        return 4 + self.ts_sub_item.total_length()

    def encode(self) -> bytes:
        """Encodes item into bytes

        :return: encoded item
        """
        return b''.join(
            [
                self.header.pack(
                    self.item_type,
                    self.reserved1,
                    self.item_length,
                    self.context_id,
                    self.reserved2,
                    self.result_reason,
                    self.reserved3
                ),
                self.ts_sub_item.encode()
            ]
        )

    @classmethod
    def decode(cls, stream: BytesIO) -> 'PresentationContextItemAC':
        """Decodes presentation context item 'accepted' from data stream

        :param stream: raw data stream
        :return: decoded context item
        """
        _, reserved1, _, context_id, reserved2, result_reason, \
            reserved3 = cls.header.unpack(stream.read(8))
        ts_sub_item = TransferSyntaxSubItem.decode(stream)
        return cls(
            context_id=context_id,
            result_reason=result_reason,
            ts_sub_item=ts_sub_item,
            reserved1=reserved1,
            reserved2=reserved2,
            reserved3=reserved3
        )

    def total_length(self) -> int:
        """Total item length, including the header

        :return: total item length
        """
        return 4 + self.item_length


class AbstractSyntaxSubItem:
    """Abstract Syntax Sub-Item (PS 3.8 9.3.2.2.1)

    :ivar name: Abstract Syntax name (UID) as byte string
    :ivar reserved: reserved field. In most cases value should be default
                    (0x00). Standard advises against testing this field value.
    """
    item_type = 0x30
    """Item type"""

    header = struct.Struct('>B B H')

    def __init__(self, name: str, reserved: int = 0x00) -> None:
        self.reserved = reserved  # unsigned byte
        self.name = name  # string

    def __repr__(self) -> str:
        return 'AbstractSyntaxSubItem('\
               f'name="{self.name}", reserved={self.reserved})'

    @property
    def item_length(self) -> int:
        """Item length, excluding the header

        :return: item length
        """
        return len(self.name)

    def encode(self) -> bytes:
        """Encodes item into bytes

        :return: encoded item
        """
        return b''.join([
            self.header.pack(self.item_type, self.reserved, self.item_length),
            self.name.encode()
        ])

    @classmethod
    def decode(cls, stream: BytesIO) -> 'AbstractSyntaxSubItem':
        """Decodes abstract syntax sub-item from data stream

        :param stream: raw data stream
        :return: decoded abstract syntax sub-item
        """
        _, reserved, item_length = cls.header.unpack(stream.read(4))
        name = uid.UID(_read_exact(stream, item_length).decode())
        return cls(name=name, reserved=reserved)

    def total_length(self) -> int:
        """Total item length, including the header

        :return: total item length
        """
        return 4 + self.item_length


class TransferSyntaxSubItem:
    """Transfer Syntax Sub-Item (PS 3.8 9.3.2.2.2)

    :ivar name: Transfer Syntax name (UID) as byte string
    :ivar reserved: reserved field. In most cases value should be default
                    (0x00). Standard advises against testing this field value.
    """
    item_type = 0x40
    """Item type"""

    header = struct.Struct('>B B H')

    def __init__(self, name: str, reserved: int = 0x00) -> None:
        self.reserved = reserved  # unsigned byte
        self.name = uid.UID(name)  # string

    def __repr__(self) -> str:
        return (
            'TransferSyntaxSubItem('
            f'name="{self.name}", reserved={self.reserved})'
        )

    @property
    def item_length(self) -> int:
        """Item length, excluding the header

        :return: item length
        """
        return len(self.name)

    def encode(self) -> bytes:
        """Encodes item into bytes

        :return: encoded item
        """
        return b''.join([
            self.header.pack(self.item_type, self.reserved, self.item_length),
            self.name.encode()
        ])

    @classmethod
    def decode(cls, stream: BytesIO) -> 'TransferSyntaxSubItem':
        """Decodes transfer syntax sub-item from data stream

        :param stream: raw data stream
        :return: decoded transfer syntax sub-item
        """
        _, reserved, item_length = cls.header.unpack(stream.read(4))
        name = _read_exact(stream, item_length)
        return cls(name=name.decode(), reserved=reserved)

    def total_length(self) -> int:
        """Total item length, including the header

        :return: total item length
        """
        return 4 + self.item_length


class UserInformationItem:
    """User Information Item (PS 3.8 9.3.2.3)

    :ivar reserved: reserved field. In most cases value should be default
                    (0x00). Standard advises against testing this field value.
    :ivar user_data: list containing the following:

                            * one :class:`~pynetdicom2.userdataitems.MaximumLengthSubItem`
                            * zero or more User Information sub-items from
                              :doc:`userdataitems`

    """  # noqa E501
    item_type = 0x50
    header = struct.Struct('>B B H')

    def __init__(
            self,
            user_data: list[
                Union[UserItem, userdataitems.GenericUserDataSubItem]
            ],
            reserved: int = 0x00
    ) -> None:
        self.reserved = reserved  # unsigned byte
        self.user_data = user_data

    def __repr__(self) -> str:
        return (
            'UserInformationItem('
            f'user_data={self.user_data}, reserved={self.reserved})'
        )

    @property
    def item_length(self) -> int:
        """Item length, excluding the header

        :return: item length
        """
        return sum(i.total_length for i in self.user_data)

    def encode(self) -> bytes:
        """Encodes item into bytes

        :return: encoded item
        """
        return self.header.pack(
            self.item_type,
            self.reserved,
            self.item_length
        ) + b''.join([data.encode() for data in self.user_data])

    @staticmethod
    def sub_items(
            stream: BytesIO
    ) -> Iterable[Union[UserItem, userdataitems.GenericUserDataSubItem]]:
        """Reads User Information sub-items from a data stream

        :param stream: raw data stream
        :raises exceptions.PDUProcessingError: [description]
        :yield: User Information sub-item
        """
        item_type = _next_type(stream)
        while item_type:
            try:
                factory = SUB_ITEM_TYPES.get(
                    item_type, userdataitems.GenericUserDataSubItem
                )
                yield factory.decode(stream)
                item_type = _next_type(stream)
            except KeyError as exc:
                raise exceptions.PDUProcessingError(
                    f'Invalid sub-item 0x{item_type}'
                ) from exc

    @classmethod
    def decode(cls, stream: BytesIO) -> 'UserInformationItem':
        """Decodes user information item from data stream

        :param stream: raw data stream
        :return: decoded user information item
        """
        _, reserved, _ = cls.header.unpack(stream.read(4))
        # read the rest of user info
        user_data = list(cls.sub_items(stream))
        return cls(user_data=user_data, reserved=reserved)

    def total_length(self) -> int:
        """Total item length, including the header

        :return: total item length
        """
        return 4 + self.item_length


VariableItems = Union[
    ApplicationContextItem,
    PresentationContextItemRQ,
    PresentationContextItemAC,
    UserInformationItem
]


class PresentationDataValueItem:
    """Presentation Data Value Item (PS 3.8 9.3.5.1)

    :ivar context_id: presentation context ID
    :ivar data_value: item value (bytes)
    """
    header = struct.Struct('>I B')

    def __init__(self, context_id: int, data_value: bytes) -> None:
        self.context_id = context_id  # unsigned byte
        self.data_value = data_value  # bytes

    def __repr__(self) -> str:
        return (
            f'PresentationDataValueItem(context_id={self.context_id}, '
            f'data_value="{str(self.data_value)}")'
        )

    @property
    def item_length(self) -> int:
        """Item length, excluding the header

        :return: item length
        """
        return len(self.data_value) + 1

    def encode(self) -> bytes:
        """Encodes item into bytes

        :return: encoded item
        """
        return b''.join([
            self.header.pack(self.item_length, self.context_id),
            self.data_value
        ])

    @classmethod
    def decode(cls, stream: BytesIO) -> 'PresentationDataValueItem':
        """Decodes presentation data value item from data stream

        Presentation data value is left in raw string format.
        The Application Entity is responsible for dealing with it.

        :param stream: raw data stream
        :return: decoded presentation data value item
        """
        item_length, context_id = cls.header.unpack(
            _read_exact(stream, cls.header.size)
        )
        if item_length < 1:
            # Per PS3.8 9.3.5.1 the item length covers at least the
            # presentation context ID byte. A value of 0 is invalid and
            # would make the read below consume the whole remaining stream.
            raise exceptions.PDUProcessingError(
                f'Invalid presentation data value item length {item_length}'
            )
        data_value = _read_exact(stream, item_length - 1)
        return cls(context_id, data_value)

    def total_length(self) -> int:
        """Total item length, including the header

        :return: total item length
        """
        return 4 + self.item_length
