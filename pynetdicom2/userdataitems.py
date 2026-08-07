# Copyright (c) 2021 Pavel 'Blane' Tuchin
# This file is part of pynetdicom2, released under a modified MIT license.
#    See the file license.txt included with this distribution.
"""
This module contains User Data sub-item helper classes.
Each sub-item class provides means for serialization and deserialization
to and from binary formats as specified in PS 3.7 of DICOM standard.
"""

from io import BytesIO
import struct
from typing import Union

from pydicom import uid

from . import exceptions


def _read_exact(stream: BytesIO, length: int) -> bytes:
    """Reads exactly ``length`` bytes from a data stream.

    Length fields of received sub-items are untrusted peer data: reading
    without verifying the result would silently accept truncated sub-items
    and shift the parsing of everything that follows.

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


class MaximumLengthSubItem:
    """Represents sub-item described in PS 3.8 D.1 Maximum Length Negotiation

    Note that item is used in both A-ASSOCIATE-RQ and A-ASSOCIATE-AC PDUs.

    :ivar reserved: this reserved field shall be sent with a value 00H but not
                    tested to this value when received.
    :ivar item_length: item length, in the case of this item it's fixed to
                       0x0004
    :ivar maximum_length_received: P-DATA-TF PDUs size limit
    """
    item_type = 0x51
    item_format = struct.Struct('>B B H I')

    def __init__(
            self,
            maximum_length_received: int,
            reserved: int = 0x00,
            item_length: int = 0x0004
    ) -> None:
        self.reserved = reserved  # unsigned byte
        self.item_length = item_length  # unsigned short
        self.maximum_length_received = maximum_length_received  # unsigned int

    def __repr__(self) -> str:
        return (
            f'MaximumLengthSubItem('
            f'maximum_length_received={self.maximum_length_received}, '
            f'reserved={self.reserved}, '
            f'item_length={self.item_length})'
        )

    @property
    def total_length(self) -> int:
        """Returns item total length.

        This item has a fixed length of 8, so method always returns 8
        regardless of specific instance
        :return item total length
        """
        return 0x08

    def encode(self) -> bytes:
        """Encodes itself into binary form

        :return: binary representation of an item
        """
        return self.item_format.pack(
            self.item_type,
            self.reserved,
            self.item_length,
            self.maximum_length_received
        )

    @classmethod
    def decode(cls, stream: BytesIO) -> 'MaximumLengthSubItem':
        """Decodes maximum length sub-item from data stream

        :param stream: raw data stream
        :return decoded maximum length sub-item
        """
        (
            _, reserved, item_length, maximum_length_received
        ) = cls.item_format.unpack(stream.read(8))
        return cls(
            reserved=reserved,
            item_length=item_length,
            maximum_length_received=maximum_length_received
        )


class ImplementationClassUIDSubItem:
    """Represents sub-item described in PS 3.8 D.3.3.2 Implementation
    Identification Notification

    Note that item is used in both A-ASSOCIATE-RQ and A-ASSOCIATE-AC PDUs.

    :ivar reserved: this reserved field shall be sent with a value 00H but not
                    tested to this value when received.
    :ivar implementation_class_uid: This variable field shall contain the
                                    Implementation-class-uid
    """
    item_type = 0x52
    header = struct.Struct('>B B H')

    def __init__(
            self,
            implementation_class_uid: str,
            reserved: int = 0x00
    ) -> None:
        self.reserved = reserved  # unsigned byte
        self.implementation_class_uid = implementation_class_uid  # string

    def __repr__(self) -> str:
        return (
            f'ImplementationClassUIDSubItem('
            f'implementation_class_uid="{self.implementation_class_uid}", '
            f'reserved={self.reserved})'
        )

    @property
    def item_length(self) -> int:
        """Calculates item length

        :return: item length
        """
        return len(self.implementation_class_uid)

    @property
    def total_length(self) -> int:
        """Returns total item length, including header.

        :return: total item length
        """
        return 4 + self.item_length

    def encode(self) -> bytes:
        """Encodes itself into binary form

        :return: binary representation of an item
        """
        return b''.join(
            [
                self.header.pack(
                    self.item_type,
                    self.reserved,
                    self.item_length
                ),
                self.implementation_class_uid.encode()
            ]
        )

    @classmethod
    def decode(cls, stream: BytesIO) -> 'ImplementationClassUIDSubItem':
        """Decodes Implementation Class UID sub-item from data stream

        :param stream: raw data stream
        :return: decoded maximum length sub-item
        """
        _, reserved, item_length = cls.header.unpack(stream.read(4))
        implementation_class_uid = uid.UID(
            _read_exact(stream, item_length).decode()
        )
        return cls(
            reserved=reserved,
            implementation_class_uid=implementation_class_uid
        )


class ImplementationVersionNameSubItem:
    """Represents sub-item described in PS 3.8 D.3.3.2 Implementation
    Identification Notification

    Note that item is used in both A-ASSOCIATE-RQ and A-ASSOCIATE-AC PDUs.

    :ivar reserved: this reserved field shall be sent with a value 00H but not
                    tested to this value when received.
    :ivar implementation_version_name: This variable field shall contain the
                                       Implementation-version-name
    """
    item_type = 0x55
    header = struct.Struct('> B B H')

    def __init__(
            self,
            implementation_version_name: str,
            reserved: int = 0x00
    ) -> None:
        self.reserved = reserved  # unsigned byte

        # string
        self.implementation_version_name = implementation_version_name

    def __repr__(self) -> str:
        return (
            'ImplementationVersionNameSubItem('
            f'implementation_version_name='
            f'"{self.implementation_version_name}", '
            f'reserved={self.reserved})'
        )

    @property
    def item_length(self) -> int:
        """Calculates item length

        :return: item length
        """
        return len(self.implementation_version_name)

    @property
    def total_length(self) -> int:
        """Returns total item length, including header.

        :return: total item length
        """
        return 4 + self.item_length

    def encode(self) -> bytes:
        """Encodes itself into binary form

        :return: binary representation of an item
        """
        return b''.join([
            self.header.pack(self.item_type, self.reserved, self.item_length),
            self.implementation_version_name.encode()
        ])

    @classmethod
    def decode(cls, stream: BytesIO) -> 'ImplementationVersionNameSubItem':
        """Decodes Implementation Version Name sub-item from data stream

        :param stream: raw data stream
        :return decoded Implementation Version Name sub-item
        """
        _, reserved, item_length = cls.header.unpack(stream.read(4))
        implementation_version_name = _read_exact(
            stream, item_length
        ).decode()
        return cls(
            implementation_version_name=implementation_version_name,
            reserved=reserved
        )


class AsynchronousOperationsWindowSubItem:
    """Represents sub-item described in PS 3.8 D.3.3.3 Asynchronous Operations
    (And Sub-Operations) Window Negotiation

    Note that item is used in both A-ASSOCIATE-RQ and A-ASSOCIATE-AC PDUs.

    :ivar reserved: this reserved field shall be sent with a value 00H but not
                    tested to this value when received.
    :ivar item_length: item length, in the case of this item it's fixed to
                       0x0004
    :ivar max_num_ops_invoked: This field shall contain the
                               Maximum-number-operations-invoked
    :ivar max_num_ops_performed: This field shall contain the
                                 Maximum-number-operations-performed
    """
    item_type = 0x53
    item_format = struct.Struct('>B B H H H')

    def __init__(
            self,
            max_num_ops_invoked: int,
            max_num_ops_performed: int,
            reserved: int = 0x00,
            item_length: int = 0x0004
    ) -> None:
        self.reserved = reserved  # unsigned byte
        self.item_length = item_length  # unsigned short
        self.max_num_ops_invoked = max_num_ops_invoked  # unsigned short
        self.max_num_ops_performed = max_num_ops_performed  # unsigned short

    def __repr__(self) -> str:
        return (
            'AsynchronousOperationsWindowSubItem('
            f'max_num_ops_invoked={self.max_num_ops_invoked}, '
            f'max_num_ops_performed={self.max_num_ops_performed}, '
            f'reserved={self.reserved}, '
            f'item_length={self.item_length})'
        )

    @property
    def total_length(self) -> int:
        """Returns total item length, including header.

        :return: total item length
        """
        return 4 + self.item_length

    def encode(self) -> bytes:
        """Encodes itself into binary form

        :return: binary representation of an item
        """
        return self.item_format.pack(
            self.item_type,
            self.reserved,
            self.item_length,
            self.max_num_ops_invoked,
            self.max_num_ops_performed
        )

    @classmethod
    def decode(cls, stream: BytesIO) -> 'AsynchronousOperationsWindowSubItem':
        """Decodes Asynchronous Operations Window sub-item from data stream

        :param stream: raw data stream
        :return decoded Asynchronous Operations Window sub-item
        """
        _, reserved, item_length, max_num_ops_invoked, \
            max_num_ops_performed = cls.item_format.unpack(stream.read(8))
        return cls(
            reserved=reserved,
            item_length=item_length,
            max_num_ops_invoked=max_num_ops_invoked,
            max_num_ops_performed=max_num_ops_performed
        )


class ScpScuRoleSelectionSubItem:
    """Represents sub-item described in PS 3.8 D.3.3.4 SCP/SCU Role Selection
    Negotiation

    Note that item is used in both A-ASSOCIATE-RQ and A-ASSOCIATE-AC PDUs.

    :ivar reserved: this reserved field shall be sent with a value 00H but not
                    tested to this value when received.
    :ivar sop_class_uid: SOP Class UID or Meta SOP Class UID
    :ivar scu_role: 0 - non support of the SCU role,
                    1 - support of the SCU role
    :ivar scp_role: 0 - non support of the SCP role,
                    1 - support of the SCP role.
    """
    item_type = 0x54
    header = struct.Struct('>B B H H')

    def __init__(
            self,
            sop_class_uid: uid.UID,
            scu_role: int,
            scp_role: int,
            reserved: int = 0x00
    ) -> None:
        self.reserved = reserved  # unsigned byte 0x00
        self.sop_class_uid = sop_class_uid  # string
        self.scu_role = scu_role  # unsigned byte
        self.scp_role = scp_role  # unsigned byte

    def __repr__(self) -> str:
        return (
            'ScpScuRoleSelectionSubItem('
            f'sop_class_uid="{self.sop_class_uid}", '
            f'scu_role={self.scu_role}, scp_role={self.scp_role}, '
            f'reserved={self.reserved})'
        )

    @property
    def item_length(self) -> int:
        """Calculates item length

        :return: item length
        """
        return 4 + len(self.sop_class_uid)

    @property
    def total_length(self) -> int:
        """Returns total item length, including header.

        :return: total item length
        """
        return 4 + self.item_length

    def encode(self) -> bytes:
        """Encodes itself into binary form

        :return: binary representation of an item
        """
        return b''.join([
            self.header.pack(
                self.item_type,
                self.reserved,
                self.item_length,
                len(self.sop_class_uid)
            ),
            self.sop_class_uid.encode(),
            struct.pack('B B', self.scu_role, self.scp_role)
        ])

    @classmethod
    def decode(cls, stream: BytesIO) -> 'ScpScuRoleSelectionSubItem':
        """Decodes SCP/SCU Role Selection sub-item from data stream

        :param stream: raw data stream
        :return decoded SCP/SCU Role Selection sub-item
        """
        _, reserved, item_length, uid_length = cls.header.unpack(
            stream.read(6)
        )
        # Per PS3.8 D.3.3.4 the item length covers the 2-byte UID length
        # field, the UID itself and the two role bytes.
        if item_length != uid_length + 4:
            raise exceptions.PDUProcessingError(
                'Invalid SCP/SCU role selection sub-item: item length '
                f'{item_length} does not match UID length {uid_length}'
            )
        sop_class_uid = uid.UID(_read_exact(stream, uid_length).decode())
        scu_role, scp_role = struct.unpack('B B', _read_exact(stream, 2))
        return cls(
            reserved=reserved,
            sop_class_uid=sop_class_uid,
            scu_role=scu_role,
            scp_role=scp_role
        )


class SOPClassExtendedNegotiationSubItem:
    """Represents sub-item described in D.3.3.5 Service-Object Pair (SOP) Class
    Extended Negotiation.

    Note that item is used in both A-ASSOCIATE-RQ and A-ASSOCIATE-AC PDUs.

    :ivar sop_class_uid: service's SOP Class UID
    :ivar app_info: application information specific to Service Class
    :ivar reserved: reserved field, defaults to 0x00. In most cases you
                    should not change it's value or check it
    """
    item_type = 0x56
    header = struct.Struct('>B B H H')

    def __init__(
            self,
            sop_class_uid: uid.UID,
            app_info: bytes,
            reserved: int = 0x00
    ) -> None:
        """Initializes new sub item instance"""
        self.reserved = reserved
        self.sop_class_uid = sop_class_uid
        self.app_info = app_info

    @property
    def item_length(self) -> int:
        """Calculates item length

        :return: item length
        """
        return 2 + len(self.sop_class_uid) + len(self.app_info)

    @property
    def total_length(self) -> int:
        """Returns total item length, including the header.

        :return: total item length
        """
        return 4 + self.item_length

    def encode(self) -> bytes:
        """Encodes itself into binary form

        :return: binary representation of an item
        """
        return b''.join(
            [self.header.pack(self.item_type, self.reserved, self.item_length,
                              len(self.sop_class_uid)),
             self.sop_class_uid.encode(),
             self.app_info])

    @classmethod
    def decode(cls, stream: BytesIO) -> 'SOPClassExtendedNegotiationSubItem':
        """Factory method. Creates sub-item from binary stream.

        :param stream: binary stream that should be decoded
        :return: new sub-item
        """
        _, reserved, item_length, uid_length = cls.header.unpack(
            stream.read(6)
        )
        # Per PS3.8 D.3.3.5 the item length covers the 2-byte UID length
        # field, the UID itself and the application information. A UID
        # length that does not fit into the item length is invalid and
        # would make the read below consume the whole remaining stream.
        if item_length < uid_length + 2:
            raise exceptions.PDUProcessingError(
                'Invalid SOP class extended negotiation sub-item: item '
                f'length {item_length} does not fit UID length '
                f'{uid_length}'
            )
        sop_class_uid = uid.UID(_read_exact(stream, uid_length).decode())
        app_info_length = item_length - uid_length - 2
        app_info = _read_exact(stream, app_info_length)
        return cls(
            reserved=reserved,
            sop_class_uid=sop_class_uid,
            app_info=app_info
        )


class UserIdentityNegotiationSubItem:
    """Represents sub-item described in D.3.3.7.1 User Identity sub-item
    structure(A-ASSOCIATE-RQ).

    Passes user identification information based on login (and password) or
    kerberos service ticket

    :ivar primary_field: user name or kerberos ticket depending on
                         value of `user_identity_type`
    :ivar secondary_field: password. Used only if `user_identity_type` has
                           value of 2
    :ivar user_identity_type: type of user identification. Defaults to 2
                              which is username/password identification
    :ivar positive_response_req: 0 - no response requested,
                                 1 - positive response requested
    :ivar reserved: reserved field, defaults to 0x00. In most cases you
                    should not change it's value or check it
    """
    item_type = 0x58
    header = struct.Struct('>B B H B B H')

    def __init__(
            self,
            primary_field: Union[str, bytes],
            secondary_field: Union[str, bytes] = '',
            user_identity_type: int = 2,
            positive_response_req: int = 0,
            reserved: int = 0x00
    ) -> None:
        """Initializes new sub item instance

        Both fields accept ``str`` (encoded as UTF-8) or raw ``bytes``.
        Username/password identity types carry text; Kerberos, SAML and JWT
        types carry opaque binary credentials that must be passed as
        ``bytes``.
        """
        self.reserved = reserved  # byte
        self.user_identity_type = user_identity_type  # byte
        self.positive_response_req = positive_response_req
        if isinstance(primary_field, str):
            primary_field = primary_field.encode('utf8')
        if isinstance(secondary_field, str):
            secondary_field = secondary_field.encode('utf8')
        self._primary_field = primary_field  # bytes
        self._secondary_field = secondary_field  # bytes

    @property
    def primary_field(self) -> Union[str, bytes]:
        """Sub-item primary field value.

        Meaning of the value depends on the `user_identity_type` value

        :return: primary field value: ``str`` when the field is valid UTF-8
                 (user name), otherwise raw ``bytes`` (Kerberos ticket, SAML
                 assertion or JWT)
        """
        try:
            return self._primary_field.decode('utf8')
        except UnicodeDecodeError:
            return self._primary_field

    @property
    def secondary_field(self) -> Union[str, bytes]:
        """Sub-item secondary field value.

        Meaning of the value depends on the `user_identity_type` value

        :return: secondary field value: ``str`` when the field is valid
                 UTF-8, otherwise raw ``bytes``
        """
        try:
            return self._secondary_field.decode('utf8')
        except UnicodeDecodeError:
            return self._secondary_field

    #: User identity types that carry secret material in the primary field:
    #: 3 - Kerberos service ticket, 4 - SAML assertion, 5 - JSON Web Token.
    #: The username-based types (1, 2) do not.
    _SECRET_PRIMARY_FIELD_TYPES = frozenset((3, 4, 5))

    def __repr__(self) -> str:
        # Never leak credentials. The secondary field carries the password
        # (type 2) and the primary field carries secret tokens for the
        # Kerberos, SAML and JWT types; both are masked when populated.
        if self.user_identity_type in self._SECRET_PRIMARY_FIELD_TYPES:
            primary = '<hidden>'
        else:
            value = self.primary_field
            primary = '<hidden>' if isinstance(value, bytes) else value
        secondary = '<hidden>' if self._secondary_field else ''
        return (
            'UserIdentityNegotiationSubItem('
            f'primary_field="{primary}", '
            f'secondary_field="{secondary}", '
            f'user_identity_type={self.user_identity_type}, '
            f'positive_response_req={self.positive_response_req}, '
            f'reserved={self.reserved})'
        )

    @property
    def item_length(self) -> int:
        """Calculates item length

        :return: item length
        """
        return 6 + len(self._primary_field) + len(self._secondary_field)

    @property
    def total_length(self) -> int:
        """Returns total item length, including header.

        :return: total item length
        """
        return 4 + self.item_length

    def encode(self) -> bytes:
        """Encodes itself into binary form

        :return: binary representation of an item
        """
        return b''.join(
            [
                self.header.pack(
                    self.item_type,
                    self.reserved,
                    self.item_length,
                    self.user_identity_type,
                    self.positive_response_req,
                    len(self._primary_field)
                ),
                self._primary_field,
                struct.pack('>H', len(self._secondary_field)),
                self._secondary_field
            ]
        )

    @classmethod
    def decode(cls, stream: BytesIO) -> 'UserIdentityNegotiationSubItem':
        """Factory method. Creates sub-item from binary stream.

        :param stream: binary stream that should be decoded
        :return: new sub-item
        """
        _, reserved, _, user_identity_type, \
            positive_response_req, \
            primary_field_len = cls.header.unpack(stream.read(cls.header.size))
        primary_field = _read_exact(stream, primary_field_len)
        secondary_field_len = struct.unpack(
            '>H', _read_exact(stream, 2)
        )[0]
        secondary_field = _read_exact(stream, secondary_field_len)
        # Kerberos, SAML and JWT identity types carry opaque binary data:
        # the fields must not be forced through a UTF-8 decode.
        return cls(
            primary_field,
            secondary_field,
            user_identity_type,
            positive_response_req,
            reserved
        )


class UserIdentityNegotiationSubItemAc:
    """Represents sub-item described in D.3.3.7.2 User Identity sub-item
    structure(A-ASSOCIATE-AC).

    Server response (accept) user identification sub-item. This item is
    expected only if `positive_response_req` was set to 1 in request sub-item.

    :ivar server_response: kerberos service ticket or SAML response,
                           depending on requested user identification type
    :ivar reserved: reserved field, defaults to 0x00. In most cases you
                    should not change it's value or check it
    """
    item_type = 0x59
    header = struct.Struct('>B B H H')

    def __init__(
            self,
            server_response: Union[str, bytes],
            reserved: int = 0x00
    ) -> None:
        """Initializes new response sub-item"""
        self.reserved = reserved  # byte
        if isinstance(server_response, str):
            server_response = server_response.encode('utf8')
        self._server_response = server_response  # bytes

    @property
    def server_response(self) -> Union[str, bytes]:
        """Server response value.

        :return: server response: ``str`` when the field is valid UTF-8,
                 otherwise raw ``bytes`` (Kerberos ticket or SAML response)
        """
        try:
            return self._server_response.decode('utf8')
        except UnicodeDecodeError:
            return self._server_response

    def __repr__(self) -> str:
        response = self.server_response
        if isinstance(response, bytes):
            # Kerberos/SAML server responses are credentials; do not leak
            # them into logs.
            response = '<hidden>'
        return (
            f'UserIdentityNegotiationSubItemAc('
            f'server_response="{response}", '
            f'reserved={self.reserved})'
        )

    @property
    def item_length(self) -> int:
        """Calculates item length

        :return: item length
        """
        return 2 + len(self._server_response)

    @property
    def total_length(self) -> int:
        """Returns total item length, including header.

        :return: total item length
        """
        return 4 + self.item_length

    def encode(self) -> bytes:
        """Encodes itself into binary form

        :return: binary representation of an item
        """
        return b''.join(
            [
                self.header.pack(
                    self.item_type,
                    self.reserved,
                    self.item_length,
                    len(self._server_response)
                ),
                self._server_response
            ]
        )

    @classmethod
    def decode(cls, stream: BytesIO) -> 'UserIdentityNegotiationSubItemAc':
        """Factory method. Creates sub-item from binary stream.

        :param stream: binary stream that should be decoded
        :return: new sub-item
        """
        _, reserved, _, response_len = cls.header.unpack(
            stream.read(cls.header.size)
        )
        # Kerberos and SAML server responses are opaque binary data: the
        # field must not be forced through a UTF-8 decode.
        server_response = _read_exact(stream, response_len)
        return cls(server_response, reserved)


class GenericUserDataSubItem:
    """This class is provided only to allow user data to converted to and from
    PDUs.

    The actual data is not interpreted. This is left to the user.
    """
    header = struct.Struct('>B B H')

    def __init__(
            self,
            item_type: int,
            user_data: bytes,
            reserved: int = 0x00
    ) -> None:
        self.item_type = item_type  # unsigned byte
        self.reserved = reserved  # unsigned byte
        self.user_data = user_data  # raw string

    def __repr__(self) -> str:
        return (
            f'GenericUserDataSubItem(item_type={self.item_type}, '
            f'user_data="{str(self.user_data)}", '
            f'reserved={self.reserved})'
        )

    @property
    def item_length(self) -> int:
        """Calculates item length

        :return: item length
        """
        return len(self.user_data)

    @property
    def total_length(self) -> int:
        """Returns total item length, including header.

        :return: total item length
        """
        return 4 + self.item_length

    def encode(self) -> bytes:
        """Encodes itself into binary form

        :return: binary representation of an item
        """
        return b''.join([
            self.header.pack(
                self.item_type,
                self.reserved,
                self.item_length
            ),
            self.user_data
        ])

    @classmethod
    def decode(cls, stream: BytesIO) -> 'GenericUserDataSubItem':
        """Decodes generic data sub-item from data stream

        User data value is left in raw string format. The Application Entity
        is responsible for dealing with it.

        :param stream: raw data stream
        :return: decoded generic data sub-item
        """
        item_type, reserved, item_length = cls.header.unpack(stream.read(4))
        user_data = _read_exact(stream, item_length)
        return cls(
            item_type=item_type,
            user_data=user_data,
            reserved=reserved
        )
