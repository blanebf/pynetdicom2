# Copyright (c) 2021 Pavel 'Blane' Tuchin
# This file is part of pynetdicom2, released under a modified MIT license.
#    See the file license.txt included with this distribution.
"""
This module contains User Data sub-item helper classes.
Each sub-item class provides means for serialization and deserialization
to and from binary formats as specified in PS 3.7 of DICOM standard.
"""

import struct

from pydicom import uid


class MaximumLengthSubItem(object):
    """Represents sub-item described in PS 3.8 D.1 Maximum Length Negotiation

    Note that item is used in both A-ASSOCIATE-RQ and A-ASSOCIATE-AC PDUs.

    :ivar reserved: this reserved field shall be sent with a value 00H but not
                    tested to this value when received.
    :ivar item_length: item length, in the case of this item it's fixed to 0x0004
    :ivar maximum_length_received: P-DATA-TF PDUs size limit
    """
    item_type = 0x51
    item_format = struct.Struct('>B B H I')

    def __init__(self, maximum_length_received, reserved=0x00,
                 item_length=0x0004):
        # type: (int,int,int) -> None
        self.reserved = reserved  # unsigned byte
        self.item_length = item_length  # unsigned short
        self.maximum_length_received = maximum_length_received  # unsigned int

    def __repr__(self):
        return 'MaximumLengthSubItem(' \
               'maximum_length_received={self.maximum_length_received}, ' \
               'reserved={self.reserved}, ' \
               'item_length={self.item_length})'.format(self=self)

    @property
    def total_length(self):
        """Returns item total length.

        This item has a fixed length of 8, so method always returns 8 regardless
        of specific instance
        :rtype int
        :return item total length
        """
        return 0x08

    def encode(self):
        """Encodes itself into binary form

        :return: binary representation of an item
        """
        return self.item_format.pack(self.item_type, self.reserved, self.item_length,
                                     self.maximum_length_received)

    @classmethod
    def decode(cls, stream):
        """Decodes maximum length sub-item from data stream

        :rtype MaximumLengthSubItem
        :param stream: raw data stream
        :return decoded maximum length sub-item
        """
        _, reserved, item_length, maximum_length_received = cls.item_format.unpack(stream.read(8))
        return cls(reserved=reserved, item_length=item_length,
                   maximum_length_received=maximum_length_received)


class ImplementationClassUIDSubItem(object):
    """Represents sub-item described in PS 3.8 D.3.3.2 Implementation Identification Notification

    Note that item is used in both A-ASSOCIATE-RQ and A-ASSOCIATE-AC PDUs.

    :ivar reserved: this reserved field shall be sent with a value 00H but not
                    tested to this value when received.
    :ivar implementation_class_uid: This variable field shall contain the Implementation-class-uid
    """
    item_type = 0x52
    header = struct.Struct('>B B H')

    def __init__(self, implementation_class_uid, reserved=0x00):
        # type: (uid.UID,int) -> None
        self.reserved = reserved  # unsigned byte
        self.implementation_class_uid = implementation_class_uid  # string

    def __repr__(self):
        return 'ImplementationClassUIDSubItem(' \
               'implementation_class_uid="{self.implementation_class_uid}", ' \
               'reserved={self.reserved})'.format(self=self)

    @property
    def item_length(self):
        """Calculates item length

        :return: item length
        """
        return len(self.implementation_class_uid)

    @property
    def total_length(self):
        """Returns total item length, including header.

        :return: total item length
        """
        return 4 + self.item_length

    def encode(self):
        """Encodes itself into binary form

        :return: binary representation of an item
        """
        return b''.join([self.header.pack(self.item_type, self.reserved, self.item_length),
                         self.implementation_class_uid.encode()])

    @classmethod
    def decode(cls, stream):
        """Decodes Implementation Class UID sub-item from data stream

        :rtype ImplementationClassUIDSubItem
        :param stream: raw data stream
        :return decoded maximum length sub-item
        """
        _, reserved, item_length = cls.header.unpack(stream.read(4))
        implementation_class_uid = uid.UID(stream.read(item_length).decode())
        return cls(reserved=reserved, implementation_class_uid=implementation_class_uid)


class ImplementationVersionNameSubItem(object):
    """Represents sub-item described in PS 3.8 D.3.3.2 Implementation Identification Notification

    Note that item is used in both A-ASSOCIATE-RQ and A-ASSOCIATE-AC PDUs.

    :ivar reserved: this reserved field shall be sent with a value 00H but not
                    tested to this value when received.
    :ivar implementation_version_name: This variable field shall contain the
                                       Implementation-version-name
    """
    item_type = 0x55
    header = struct.Struct('> B B H')

    def __init__(self, implementation_version_name, reserved=0x00):
        # type: (str,int) -> None
        self.reserved = reserved  # unsigned byte
        self.implementation_version_name = implementation_version_name  # string

    def __repr__(self):
        return 'ImplementationVersionNameSubItem(' \
               'implementation_version_name=' \
               '"{self.implementation_version_name}", ' \
               'reserved={self.reserved})'.format(self=self)

    @property
    def item_length(self):
        """Calculates item length

        :return: item length
        """
        return len(self.implementation_version_name)

    @property
    def total_length(self):
        """Returns total item length, including header.

        :return: total item length
        """
        return 4 + self.item_length

    def encode(self):
        """Encodes itself into binary form

        :return: binary representation of an item
        """
        return b''.join([self.header.pack(self.item_type, self.reserved, self.item_length),
                         self.implementation_version_name.encode()])

    @classmethod
    def decode(cls, stream):
        """Decodes Implementation Version Name sub-item from data stream

        :rtype ImplementationVersionNameSubItem
        :param stream: raw data stream
        :return decoded Implementation Version Name sub-item
        """
        _, reserved, item_length = cls.header.unpack(stream.read(4))
        implementation_version_name = stream.read(item_length).decode()
        return cls(implementation_version_name=implementation_version_name,
                   reserved=reserved)


class AsynchronousOperationsWindowSubItem(object):
    """Represents sub-item described in PS 3.8 D.3.3.3 Asynchronous Operations (And Sub-Operations)
    Window Negotiation

    Note that item is used in both A-ASSOCIATE-RQ and A-ASSOCIATE-AC PDUs.

    :ivar reserved: this reserved field shall be sent with a value 00H but not
                    tested to this value when received.
    :ivar item_length: item length, in the case of this item it's fixed to 0x0004
    :ivar max_num_ops_invoked: This field shall contain the Maximum-number-operations-invoked
    :ivar max_num_ops_performed: This field shall contain the Maximum-number-operations-performed
    """
    item_type = 0x53
    item_format = struct.Struct('>B B H H H')

    def __init__(self, max_num_ops_invoked, max_num_ops_performed,
                 reserved=0x00, item_length=0x0004):
        # type: (int,int,int,int) -> None
        self.reserved = reserved  # unsigned byte
        self.item_length = item_length  # unsigned short
        self.max_num_ops_invoked = max_num_ops_invoked  # unsigned short
        self.max_num_ops_performed = max_num_ops_performed  # unsigned short

    def __repr__(self):
        return 'AsynchronousOperationsWindowSubItem(' \
               'max_num_ops_invoked={self.max_num_ops_invoked}, ' \
               'max_num_ops_performed={self.max_num_ops_performed}, ' \
               'reserved={self.reserved}, ' \
               'item_length={self.item_length})'.format(self=self)

    @property
    def total_length(self):
        """Returns total item length, including header.

        :return: total item length
        """
        return 4 + self.item_length

    def encode(self):
        """Encodes itself into binary form

        :return: binary representation of an item
        """
        return self.item_format.pack(self.item_type, self.reserved,
                                     self.item_length, self.max_num_ops_invoked,
                                     self.max_num_ops_performed)

    @classmethod
    def decode(cls, stream):
        """Decodes Asynchronous Operations Window sub-item from data stream

        :rtype AsynchronousOperationsWindowSubItem
        :param stream: raw data stream
        :return decoded Asynchronous Operations Window sub-item
        """
        _, reserved, item_length, max_num_ops_invoked, \
            max_num_ops_performed = cls.item_format.unpack(stream.read(8))
        return cls(reserved=reserved, item_length=item_length,
                   max_num_ops_invoked=max_num_ops_invoked,
                   max_num_ops_performed=max_num_ops_performed)


class ScpScuRoleSelectionSubItem(object):
    """Represents sub-item described in PS 3.8 D.3.3.4 SCP/SCU Role Selection Negotiation

    Note that item is used in both A-ASSOCIATE-RQ and A-ASSOCIATE-AC PDUs.

    :ivar reserved: this reserved field shall be sent with a value 00H but not
                    tested to this value when received.
    :ivar sop_class_uid: SOP Class UID or Meta SOP Class UID
    :ivar scu_role: 0 - non support of the SCU role, 1 - support of the SCU role
    :ivar scp_role: 0 - non support of the SCP role, 1 - support of the SCP role.
    """
    item_type = 0x54
    header = struct.Struct('>B B H H')

    def __init__(self, sop_class_uid, scu_role, scp_role, reserved=0x00):
        # type: (uid.UID,int,int,int) -> None
        self.reserved = reserved  # unsigned byte 0x00
        self.sop_class_uid = sop_class_uid  # string
        self.scu_role = scu_role  # unsigned byte
        self.scp_role = scp_role  # unsigned byte

    def __repr__(self):
        return 'ScpScuRoleSelectionSubItem(' \
               'sop_class_uid="{self.sop_class_uid}", ' \
               'scu_role={self.scu_role}, scp_role={self.scp_role}, ' \
               'reserved={self.reserved})'.format(self=self)

    @property
    def item_length(self):
        """Calculates item length

        :return: item length
        """
        return 4 + len(self.sop_class_uid)

    @property
    def total_length(self):
        """Returns total item length, including header.

        :return: total item length
        """
        return 4 + self.item_length

    def encode(self):
        """Encodes itself into binary form

        :return: binary representation of an item
        """
        return b''.join(
            [self.header.pack(self.item_type, self.reserved, self.item_length,
                              len(self.sop_class_uid)),
             self.sop_class_uid.encode(),
             struct.pack('B B', self.scu_role, self.scp_role)])

    @classmethod
    def decode(cls, stream):
        """Decodes SCP/SCU Role Selection sub-item from data stream

        :rtype ScpScuRoleSelectionSubItem
        :param stream: raw data stream
        :return decoded SCP/SCU Role Selection sub-item
        """
        _, reserved, _, uid_length = cls.header.unpack(stream.read(6))
        sop_class_uid = uid.UID(stream.read(uid_length).decode())
        scu_role, scp_role = struct.unpack('B B', stream.read(2))
        return cls(reserved=reserved, sop_class_uid=sop_class_uid,
                   scu_role=scu_role, scp_role=scp_role)


class SOPClassExtendedNegotiationSubItem(object):
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

    def __init__(self, sop_class_uid, app_info, reserved=0x00):
        # type: (uid.UID,bytes,int) -> None
        """Initializes new sub item instance"""
        self.reserved = reserved
        self.sop_class_uid = sop_class_uid
        self.app_info = app_info

    @property
    def item_length(self):
        """Calculates item length

        :return: item length
        """
        return 2 + len(self.sop_class_uid) + len(self.app_info)

    @property
    def total_length(self):
        """Returns total item length, including the header.

        :return: total item length
        """
        return 4 + self.item_length

    def encode(self):
        """Encodes itself into binary form

        :return: binary representation of an item
        """
        return b''.join(
            [self.header.pack(self.item_type, self.reserved, self.item_length,
                              len(self.sop_class_uid)),
             self.sop_class_uid.encode(),
             self.app_info])

    @classmethod
    def decode(cls, stream):
        """Factory method. Creates sub-item from binary stream.

        :param stream: binary stream that should be decoded
        :return: new sub-item
        """
        _, reserved, item_length, uid_length = cls.header.unpack(stream.read(6))
        sop_class_uid = uid.UID(stream.read(uid_length).decode())
        app_info_length = item_length - uid_length
        app_info = stream.read(app_info_length)
        return cls(reserved=reserved, sop_class_uid=sop_class_uid, app_info=app_info)


class UserIdentityNegotiationSubItem(object):
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

    def __init__(self, primary_field, secondary_field='', user_identity_type=2,
                 positive_response_req=0, reserved=0x00):
        # type: (str,str,int,int,int) -> None
        """Initializes new sub item instance"""
        self.reserved = reserved  # byte
        self.user_identity_type = user_identity_type  # byte
        self.positive_response_req = positive_response_req
        self._primary_field = primary_field.encode('utf8')  # string
        self._secondary_field = secondary_field.encode('utf8')  # string

    @property
    def primary_field(self):
        """Sub-item primary field value.

        Meaning of the value depends on the `user_identity_type` value

        :return: primary field value
        :rtype: str
        """
        return self._primary_field.decode('utf8')

    @property
    def secondary_field(self):
        """Sub-item secondary field value.

        Meaning of the value depends on the `user_identity_type` value

        :return: secondary field value
        :rtype: str
        """
        return self._secondary_field.decode('utf8')

    def __repr__(self):
        return 'UserIdentityNegotiationSubItem(' \
               'primary_field="{self.primary_field}", ' \
               'secondary_field="{self.secondary_field}", ' \
               'user_identity_type={self.user_identity_type}, ' \
               'positive_response_req={self.positive_response_req}, ' \
               'reserved={self.reserved})'.format(self=self)

    @property
    def item_length(self):
        """Calculates item length

        :return: item length
        """
        return 6 + len(self._primary_field) + len(self._secondary_field)

    @property
    def total_length(self):
        """Returns total item length, including header.

        :return: total item length
        """
        return 4 + self.item_length

    def encode(self):
        """Encodes itself into binary form

        :return: binary representation of an item
        """
        return b''.join(
            [self.header.pack(self.item_type, self.reserved, self.item_length,
                              self.user_identity_type,
                              self.positive_response_req,
                              len(self._primary_field)),
             self._primary_field, struct.pack('>H', len(self._secondary_field)),
             self._secondary_field])

    @classmethod
    def decode(cls, stream):
        """Factory method. Creates sub-item from binary stream.

        :param stream: binary stream that should be decoded
        :return: new sub-item
        """
        _, reserved, _, user_identity_type, \
            positive_response_req, \
            primary_field_len = cls.header.unpack(stream.read(cls.header.size))
        primary_field = stream.read(primary_field_len)
        secondary_field_len = struct.unpack('>H', stream.read(2))[0]
        secondary_field = stream.read(secondary_field_len)
        return cls(primary_field.decode('utf8'), secondary_field.decode('utf8'), user_identity_type,
                   positive_response_req, reserved)


class UserIdentityNegotiationSubItemAc(object):
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

    def __init__(self, server_response, reserved=0x00):
        # type: (str,int) -> None
        """Initializes new response sub-item"""
        self.reserved = reserved  # byte
        self.server_response = server_response  # string

    def __repr__(self):
        return 'UserIdentityNegotiationSubItemAc(' \
               'server_response="{self.server_response}", ' \
               'reserved={self.reserved})'.format(self=self)

    @property
    def item_length(self):
        """Calculates item length

        :return: item length
        """
        return 2 + len(self.server_response)

    @property
    def total_length(self):
        """Returns total item length, including header.

        :return: total item length
        """
        return 4 + self.item_length

    def encode(self):
        """Encodes itself into binary form

        :return: binary representation of an item
        """
        server_response = self.server_response.encode()
        return b''.join(
            [self.header.pack(self.item_type, self.reserved, self.item_length,
                              len(server_response)),
             server_response])

    @classmethod
    def decode(cls, stream):
        """Factory method. Creates sub-item from binary stream.

        :param stream: binary stream that should be decoded
        :return: new sub-item
        """
        _, reserved, _, response_len = cls.header.unpack(stream.read(cls.header.size))
        server_response = stream.read(response_len).decode()
        return cls(server_response, reserved)


class GenericUserDataSubItem(object):
    """This class is provided only to allow user data to converted to and from
    PDUs.

    The actual data is not interpreted. This is left to the user.
    """
    header = struct.Struct('>B B H')

    def __init__(self, item_type, user_data, reserved=0x00):
        # type: (int,bytes,int) -> None
        self.item_type = item_type  # unsigned byte
        self.reserved = reserved  # unsigned byte
        self.user_data = user_data  # raw string

    def __repr__(self):
        return 'GenericUserDataSubItem(item_type={self.item_type}, ' \
               'user_data="{self.user_data}", ' \
               'reserved={self.reserved})'.format(self=self)

    @property
    def item_length(self):
        """Calculates item length

        :return: item length
        """
        return len(self.user_data)

    @property
    def total_length(self):
        """Returns total item length, including header.

        :return: total item length
        """
        return 4 + self.item_length

    def encode(self):
        """Encodes itself into binary form

        :return: binary representation of an item
        """
        return b''.join([self.header.pack(self.item_type, self.reserved, self.item_length),
                         self.user_data])

    @classmethod
    def decode(cls, stream):
        """Decodes generic data sub-item from data stream

        User data value is left in raw string format. The Application Entity
        is responsible for dealing with it.

        :param stream: raw data stream
        :return: decoded generic data sub-item
        """
        item_type, reserved, item_length = cls.header.unpack(stream.read(4))
        user_data = stream.read(int(item_length))
        return cls(item_type=item_type, user_data=user_data, reserved=reserved)
