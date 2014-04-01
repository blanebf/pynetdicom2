# Copyright (c) 2014 Pavel 'Blane' Tuchin
# Copyright (c) 2012 Patrice Munger
# This file is part of pynetdicom, released under a modified MIT license.
#    See the file license.txt included with this distribution, also
#    available at http://pynetdicom.googlecode.com
#

"""
Implementation of DICOM Standard, PS 3.8, section 9.3
DICOM Upper Layer Protocol for TCP/IP
Data Unit Structure


Module implementing the Data Unit Structures
There are seven different PDUs, each of them corresponds to distinct class.
    A_ASSOCIATE_RQ_PDU
    A_ASSOCIATE_AC_PDU
    A_ASSOCIATE_RJ_PDU
    P_DATA_TF_PDU
    A_RELEASE_RQ_PDU
    A_RELEASE_RP_PDU
    A_ABORT_PDU


    All PDU classes implement the following methods:

      from_params(DULServiceParameterObject):  Builds a PDU from a
                                              DULServiceParameter object.
                                              Used when receiving primitives
                                              from the DULServiceUser.
      to_params()                           :  Convert the PDU into a
                                              DULServiceParameter object.
                                              Used for sending primitives to
                                              the DULServiceUser.
      encode()                     :  Returns the encoded PDU as a string,
                                      ready to be sent over the net.
      decode(string)               :  Construct PDU from "string".
                                      Used for reading PDU's from the net.

                        from_params                 encode
  |------------ -------| ------->  |------------| -------> |------------|
  | Service parameters |           |     PDU    |          |    TCP     |
  |       object       |           |   object   |          |   socket   |
  |____________________| <-------  |____________| <------- |____________|
                         to_params                  decode



In addition to PDUs, several items and sub-items classes are implemented.
These classes are:

        ApplicationContextItem
        PresentationContextItemRQ
        AbstractSyntaxSubItem
        TransferSyntaxSubItem
        UserInformationItem
        PresentationContextItemAC
        PresentationDataValueItem
"""

import struct
from cStringIO import StringIO

import netdicom2.dulparameters as dulparameters
import netdicom2.exceptions as exceptions
import netdicom2.dimseparameters as dimseparameters


class AAssociateRqPDU(object):
    """This class represents the A-ASSOCIATE-RQ PDU"""

    def __init__(self):
        self.pdu_type = 0x01  # Unsigned byte
        self.reserved1 = 0x00  # Unsigned byte
        self.pdu_length = None  # Unsigned int
        self.protocol_version = 1  # Unsigned short
        self.reserved2 = 0x00  # Unsigned short
        self.called_ae_title = None  # string of length 16
        self.calling_ae_title = None  # string of length 16
        self.reserved3 = (0, 0, 0, 0, 0, 0, 0, 0)  # 32 bytes

        # VariablesItems is a list containing the following:
        #   1 ApplicationContextItem
        #   1 or more PresentationContextItemRQ
        #   1 UserInformationItem
        self.variable_items = []

    def __repr__(self):
        tmp = ''.join(['A-ASSOCIATE-RQ PDU\n',
                       ' PDU type: 0x%02x\n' % self.pdu_type,
                       ' PDU length: %d\n' % self.pdu_length,
                       ' Called AE title: %s\n' % self.called_ae_title,
                       ' Calling AE title: %s\n' % self.calling_ae_title])
        tmp2 = ''.join([item.__repr__() for item in self.variable_items])
        return '%s%s\n' % (tmp, tmp2)

    @classmethod
    def from_params(cls, params):
        """Factory method. Create PDU from AAssociateServiceParameters instance

        :rtype : AAssociateRqPDU
        :param params: AAssociateServiceParameters instance
        :return: PDU instance
        """
        instance = cls()
        instance.calling_ae_title = params.calling_ae_title
        instance.called_ae_title = params.called_ae_title
        tmp_app_cont = ApplicationContextItem.from_params(
            params.application_context_name)
        instance.variable_items.append(tmp_app_cont)

        # Make presentation contexts
        for context in params.presentation_context_definition_list:
            tmp_pres_cont = PresentationContextItemRQ()
            tmp_pres_cont.from_params(context)
            instance.variable_items.append(tmp_pres_cont)

        # Make user information
        tmp_user_info = UserInformationItem.from_params(params.user_information)
        instance.variable_items.append(tmp_user_info)

        instance.pdu_length = 68
        for item in instance.variable_items:
            instance.pdu_length = instance.pdu_length + item.total_length()
        return instance

    def to_params(self):
        # Returns an A_ASSOCIATE_ServiceParameters object
        assoc = dulparameters.AAssociateServiceParameters()
        assoc.calling_ae_title = self.calling_ae_title
        assoc.called_ae_title = self.called_ae_title
        assoc.application_context_name = self.variable_items[
            0].application_context_name

        # Write presentation contexts
        for ii in self.variable_items[1:-1]:
            assoc.presentation_context_definition_list.append(ii.to_params())

        # Write user information
        assoc.user_information = self.variable_items[-1].to_params()
        return assoc

    def encode(self):
        tmp = ''.join([struct.pack('B', self.pdu_type),
                       struct.pack('B', self.reserved1),
                       struct.pack('>I', self.pdu_length),
                       struct.pack('>H', self.protocol_version),
                       struct.pack('>H', self.reserved2),
                       struct.pack('16s', self.called_ae_title),
                       struct.pack('16s', self.calling_ae_title),
                       struct.pack('>8I', 0, 0, 0, 0, 0, 0, 0, 0)])

        tmp2 = ''.join([item.encode() for item in self.variable_items])
        return tmp + tmp2

    @classmethod
    def decode(cls, rawstring):
        """Factory method. Decodes A-ASSOCIATE-RQ PDU instance from raw string.

        :rtype : AAssociateRqPDU
        :param rawstring: rawstring containing binary representation of the
        A-ASSOCIATE-RQ PDU
        :return: decoded PDU
        :raise RuntimeError:
        """
        stream = StringIO(rawstring)
        decoded_pdu = cls()
        decoded_pdu.pdu_type, decoded_pdu.reserved1, \
            decoded_pdu.pdu_length, decoded_pdu.protocol_version, \
            decoded_pdu.reserved2, decoded_pdu.called_ae_title, \
            decoded_pdu.calling_ae_title = struct.unpack('> B B I H H 16s 16s',
                                                         stream.read(42))
        decoded_pdu.reserved3 = struct.unpack('> 8I', stream.read(32))
        decoded_pdu.called_ae_title = decoded_pdu.called_ae_title.strip('\0')
        decoded_pdu.calling_ae_title = decoded_pdu.calling_ae_title.strip('\0')
        item_type = next_type(stream)
        while item_type:
            if item_type == 0x10:
                tmp = ApplicationContextItem.decode(stream)
            elif item_type == 0x20:
                tmp = PresentationContextItemRQ.decode(stream)
            elif item_type == 0x50:
                tmp = UserInformationItem.decode(stream)
            else:
                raise exceptions.PDUProcessingError('Invalid variable item')
            decoded_pdu.variable_items.append(tmp)
            item_type = next_type(stream)
        return decoded_pdu

    def total_length(self):
        return 6 + self.pdu_length


class AAssociateAcPDU(object):
    """This class represents the A-ASSOCIATE-AC PDU"""

    def __init__(self):
        self.pdu_type = 0x02  # Unsigned byte
        self.reserved1 = 0x00  # Unsigned byte
        self.pdu_length = None  # Unsigned int
        self.protocol_version = 1  # Unsigned short
        self.reserved2 = 0x00  # Unsigned short
        self.reserved3 = None  # string of length 16
        self.reserved4 = None  # string of length 16
        self.reserved5 = (0x0000, 0x0000, 0x0000, 0x0000)  # 32 bytes

        # VariablesItems is a list containing the following:
        #   1 ApplicationContextItem
        #   1 or more PresentationContextItemAC
        #   1 UserInformationItem
        self.variable_items = []

    def __repr__(self):
        tmp = ''.join(['A-ASSOCIATE-AC PDU\n',
                       ' PDU type: 0x%02x\n' % self.pdu_type,
                       ' PDU length: %d\n' % self.pdu_length,
                       ' Called AE title: %s\n' % self.reserved3,
                       ' Calling AE title: %s\n' % self.reserved4])
        tmp2 = ''.join([item.__repr__() for item in self.variable_items])
        return '%s%s\n' % (tmp, tmp2)

    @classmethod
    def from_params(cls, params):
        """Factory method. Create PDU from AAssociateServiceParameters instance

        :rtype : AAssociateAcPDU
        :param params: AAssociateServiceParameters instance
        :return: PDU instance
        """
        instance = cls()
        instance.reserved3 = params.called_ae_title
        instance.reserved4 = params.calling_ae_title
        # Make application context
        tmp_app_cont = ApplicationContextItem.from_params(
            params.application_context_name)
        instance.variable_items.append(tmp_app_cont)
        # Make presentation contexts
        for context in params.presentation_context_definition_result_list:
            tmp_pres_cont = PresentationContextItemAC.from_params(context)
            instance.variable_items.append(tmp_pres_cont)
        # Make user information
        tmp_user_info = UserInformationItem.from_params(params.user_information)
        instance.variable_items.append(tmp_user_info)
        # Compute PDU length
        instance.pdu_length = 68
        for item in instance.variable_items:
            instance.pdu_length = instance.pdu_length + item.total_length()
        return instance

    def to_params(self):
        assoc = dulparameters.AAssociateServiceParameters()
        assoc.called_ae_title = self.reserved3
        assoc.calling_ae_title = self.reserved4
        assoc.application_context_name = self.variable_items[0].to_params()

        # Write presentation context
        for ii in self.variable_items[1:-1]:
            assoc.presentation_context_definition_result_list.append(
                ii.to_params())

        # Write user information
        assoc.user_information = self.variable_items[-1].to_params()
        assoc.result = 'Accepted'
        return assoc

    def encode(self):
        tmp = ''.join([struct.pack('B', self.pdu_type),
                       struct.pack('B', self.reserved1),
                       struct.pack('>I', self.pdu_length),
                       struct.pack('>H', self.protocol_version),
                       struct.pack('>H', self.reserved2),
                       struct.pack('16s', self.reserved3),
                       struct.pack('16s', self.reserved4),
                       struct.pack('>8I', 0, 0, 0, 0, 0, 0, 0, 0)])

        # variable item elements
        tmp2 = ''.join([item.encode() for item in self.variable_items])
        return tmp + tmp2

    @classmethod
    def decode(cls, rawstring):
        """Factory method. Decodes A-ASSOCIATE-AC PDU instance from raw string.

        :rtype : AAssociateAcPDU
        :param rawstring: rawstring containing binary representation of the
        A-ASSOCIATE-AC PDU
        :return: decoded PDU
        :raise RuntimeError:
        """
        stream = StringIO(rawstring)
        decoded_pdu = cls()
        decoded_pdu.pdu_type, decoded_pdu.reserved1, decoded_pdu.pdu_length, \
            decoded_pdu.protocol_version, decoded_pdu.reserved2, \
            decoded_pdu.reserved3, \
            decoded_pdu.reserved4 = struct.unpack('> B B I H H 16s 16s',
                                                  stream.read(42))
        decoded_pdu.reserved5 = struct.unpack('>8I', stream.read(32))
        item_type = next_type(stream)
        while item_type:
            if item_type == 0x10:
                tmp = ApplicationContextItem.decode(stream)
            elif item_type == 0x21:
                tmp = PresentationContextItemAC.decode(stream)
            elif item_type == 0x50:
                tmp = UserInformationItem.decode(stream)
            else:
                raise exceptions.PDUProcessingError('Invalid variable item')
            decoded_pdu.variable_items.append(tmp)
            item_type = next_type(stream)
        return decoded_pdu

    def total_length(self):
        return 6 + self.pdu_length


class AAssociateRjPDU(object):
    """This class represents the A-ASSOCIATE-RJ PDU"""

    def __init__(self):
        self.pdu_type = 0x03  # Unsigned byte
        self.reserved1 = 0x00  # Unsigned byte
        self.pdu_length = 0x00000004  # Unsigned int
        self.reserved2 = 0x00  # Unsigned byte
        self.result = None  # Unsigned byte
        self.source = None  # Unsigned byte
        self.reason_diag = None  # Unsigned byte

    def __repr__(self):
        return ''.join(['A-ASSOCIATE-RJ PDU\n',
                        ' PDU type: 0x%02x\n' % self.pdu_type,
                        ' PDU length: %d\n' % self.pdu_length,
                        ' Result: %d\n' % self.result,
                        ' Source: %s\n' % str(self.source),
                        ' Reason/Diagnostic: %s\n' % str(self.reason_diag),
                        '\n'])

    @classmethod
    def from_params(cls, params):
        """Factory method. Create PDU from AAssociateServiceParameters instance

        :rtype : AAssociateRjPDU
        :param params: AAssociateServiceParameters instance
        :return: PDU instance
        """
        instance = cls()
        instance.result = params.result
        instance.source = params.result_source
        instance.reason_diag = params.diagnostic
        return instance

    def to_params(self):
        tmp = dulparameters.AAssociateServiceParameters()
        tmp.result = self.result
        tmp.result_source = self.source
        tmp.diagnostic = self.reason_diag
        return tmp

    def encode(self):
        return ''.join([struct.pack('B', self.pdu_type),
                        struct.pack('B', self.reserved1),
                        struct.pack('>I', self.pdu_length),
                        struct.pack('B', self.reserved2),
                        struct.pack('B', self.result),
                        struct.pack('B', self.source),
                        struct.pack('B', self.reason_diag)])

    @classmethod
    def decode(cls, rawstring):
        """Factory method. Decodes A-ASSOCIATE-RJ PDU instance from raw string.

        :rtype : AAssociateRjPDU
        :param rawstring: rawstring containing binary representation of the
        A-ASSOCIATE-RJ PDU
        :return: decoded PDU
        """
        stream = StringIO(rawstring)
        decoded_pdu = cls()
        decoded_pdu.pdu_type, decoded_pdu.reserved1, decoded_pdu.pdu_length, \
            decoded_pdu.reserved2, decoded_pdu.result, decoded_pdu.source, \
            decoded_pdu.reason_diag = struct.unpack('> B B I B B B B',
                                                    stream.read(10))
        return decoded_pdu

    def total_length(self):
        return 10


class PDataTfPDU(object):
    """This class represents the P-DATA-TF PDU"""

    def __init__(self):
        self.pdu_type = 0x04  # Unsigned byte
        self.reserved = 0x00  # Unsigned byte
        self.pdu_length = None  # Unsigned int

        # List of one of more PresentationDataValueItem
        self.presentation_data_value_items = []

    def __repr__(self):
        tmp = ''.join(['P-DATA-TF PDU\n', ' PDU type: 0x%02x\n' % self.pdu_type,
                       ' PDU length: %d\n' % self.pdu_length])
        tmp2 = ''.join(item.__repr__()
                       for item in self.presentation_data_value_items)
        return '%s%s\n' % (tmp, tmp2)

    @classmethod
    def from_params(cls, params):
        """Factory method. Create PDU from PDataServiceParameters instance

        :rtype : PDataTfPDU
        :param params: PDataServiceParameters instance
        :return: PDU instance
        """
        instance = cls()
        for value in params.presentation_data_value_list:
            tmp = PresentationDataValueItem.from_params(value)
            instance.presentation_data_value_items.append(tmp)
        instance.pdu_length = 0
        for item in instance.presentation_data_value_items:
            instance.pdu_length = instance.pdu_length + item.total_length()

    def to_params(self):
        tmp = dulparameters.PDataServiceParameters()
        tmp.presentation_data_value_list = [[i.presentation_context_id,
                                             i.presentation_data_value]
                                            for i in
                                            self.presentation_data_value_items]
        return tmp

    def encode(self):
        tmp = ''.join([struct.pack('B', self.pdu_type),
                       struct.pack('B', self.reserved),
                       struct.pack('>I', self.pdu_length)])
        tmp2 = ''.join([item.encode()
                        for item in self.presentation_data_value_items])
        return tmp + tmp2

    @classmethod
    def decode(cls, rawstring):
        """Factory method. Decodes P-DATA-TF PDU instance from raw string.

        :rtype : PDataTfPDU
        :param rawstring: rawstring containing binary representation of the
        P-DATA-TF PDU
        :return: decoded PDU
        """
        stream = StringIO(rawstring)
        decoded_pdu = cls()
        decoded_pdu.pdu_type, decoded_pdu.reserved, \
            decoded_pdu.pdu_length = struct.unpack('> B B I', stream.read(6))
        length_read = 0
        while length_read != decoded_pdu.pdu_length:
            tmp = PresentationDataValueItem.decode(stream)
            length_read += tmp.total_length()
            decoded_pdu.presentation_data_value_items.append(tmp)
        return decoded_pdu

    def total_length(self):
        return 6 + self.pdu_length


class AReleaseRqPDU(object):
    """This class represents the A-RELEASE-RQ PDU"""

    def __init__(self):
        self.pdu_type = 0x05  # Unsigned byte
        self.reserved1 = 0x00  # Unsigned byte
        self.pdu_length = 0x00000004  # Unsigned int
        self.reserved2 = 0x00000000  # Unsigned int

    def __repr__(self):
        return ''.join(['A-RELEASE-RQ PDU\n',
                        ' PDU type: 0x%02x\n' % self.pdu_type,
                        ' PDU length: %d\n' % self.pdu_length, '\n'])

    def to_params(self):
        tmp = dulparameters.AReleaseServiceParameters()
        tmp.reason = 'normal'
        tmp.result = 'affirmative'
        return tmp

    def encode(self):
        return ''.join([struct.pack('B', self.pdu_type),
                        struct.pack('B', self.reserved1),
                        struct.pack('>I', self.pdu_length),
                        struct.pack('>I', self.reserved2)])

    @classmethod
    def decode(cls, rawstring):
        """Factory method. Decodes A-RELEASE-RQ PDU instance from raw string.

        :rtype : AReleaseRqPDU
        :param rawstring: rawstring containing binary representation of the
        A-RELEASE-RQ PDU
        :return: decoded PDU
        """
        stream = StringIO(rawstring)
        decoded_pdu = cls()
        decoded_pdu.pdu_type, decoded_pdu.reserved1, decoded_pdu.pdu_length, \
            decoded_pdu.reserved2 = struct.unpack('> B B I I', stream.read(10))
        return decoded_pdu

    def total_length(self):
        return 10


class AReleaseRpPDU(object):
    """This class represents the A-RELEASE-RP PDU"""

    def __init__(self):
        self.pdu_type = 0x06  # Unsigned byte
        self.reserved1 = 0x00  # Unsigned byte
        self.pdu_length = 0x00000004  # Unsigned int
        self.reserved2 = 0x00000000  # Unsigned int

    def __repr__(self):
        return ''.join(['A-RELEASE-RP PDU\n',
                        ' PDU type: 0x%02x\n' % self.pdu_type,
                        ' PDU length: %d\n' % self.pdu_length + '\n'])

    def to_params(self):
        tmp = dulparameters.AReleaseServiceParameters()
        tmp.reason = 'normal'
        tmp.result = 'affirmative'
        return tmp

    def encode(self):
        return ''.join([struct.pack('B', self.pdu_type),
                        struct.pack('B', self.reserved1),
                        struct.pack('>I', self.pdu_length),
                        struct.pack('>I', self.reserved2)])

    @classmethod
    def decode(cls, rawstring):
        """Factory method. Decodes A-RELEASE-RP PDU instance from raw string.

        :rtype : AReleaseRpPDU
        :param rawstring: rawstring containing binary representation of the
        A-RELEASE-RP PDU
        :return: decoded PDU
        """
        stream = StringIO(rawstring)
        decoded_pdu = cls()
        decoded_pdu.pdu_type, decoded_pdu.reserved1, decoded_pdu.pdu_length, \
            decoded_pdu.reserved2 = struct.unpack('> B B I I', stream.read(10))
        return decoded_pdu

    def total_length(self):
        return 10


class AAbortPDU(object):
    """This class represents the A-ABORT PDU"""

    def __init__(self):
        self.pdu_type = 0x07  # Unsigned byte
        self.reserved1 = 0x00  # Unsigned byte
        self.pdu_length = 0x00000004  # Unsigned int
        self.reserved2 = 0x00  # Unsigned byte
        self.reserved3 = 0x00  # Unsigned byte
        self.abort_source = None  # Unsigned byte
        self.reason_diag = None  # Unsigned byte

    def __repr__(self):
        return ''.join(['A-ABORT PDU\n', ' PDU type: 0x%02x\n' % self.pdu_type,
                        ' PDU length: %d\n' % self.pdu_length,
                        ' Abort Source: %d\n' % self.abort_source,
                        ' Reason/Diagnostic: %d\n' % self.reason_diag, '\n'])

    @classmethod
    def from_params(cls, params):
        instance = cls()
        # params can be an AAbortServiceParameters or
        # APAbortServiceParameters object.
        try:  # User initiated abort
            instance.abort_source = params.abort_source
            instance.reason_diag = 0
        except AttributeError:  # User provider initiated abort
            instance.abort_source = 0
            instance.reason_diag = params.provider_reason
        return instance

    def to_params(self):
        # Returns either a A-ABORT of an A-P-ABORT
        if self.abort_source is not None:
            tmp = dulparameters.AAbortServiceParameters()
            tmp.abort_source = self.abort_source
        elif self.reason_diag is not None:
            tmp = dulparameters.APAbortServiceParameters()
            tmp.provider_reason = self.reason_diag
        else:
            raise RuntimeError('Unknown abort source')
        return tmp

    def encode(self):
        return ''.join([struct.pack('B', self.pdu_type),
                        struct.pack('B', self.reserved1),
                        struct.pack('>I', self.pdu_length),
                        struct.pack('B', self.reserved2),
                        struct.pack('B', self.reserved3),
                        struct.pack('B', self.abort_source),
                        struct.pack('B', self.reason_diag)])

    @classmethod
    def decode(cls, rawstring):
        """Factory method. Decodes A-ABORT PDU instance from raw string.

        :rtype : AAbortPDU
        :param rawstring: rawstring containing binary representation of
        the A-ABORT PDU
        :return: decoded PDU
        """
        stream = StringIO(rawstring)
        decoded_pdu = cls()
        decoded_pdu.pdu_type, decoded_pdu.reserved1, \
            decoded_pdu.pdu_length, decoded_pdu.reserved2, \
            decoded_pdu.reserved3, decoded_pdu.abort_source, \
            decoded_pdu.reason_diag = struct.unpack('> B B I B B B B',
                                                    stream.read(10))
        return decoded_pdu

    def total_length(self):
        return 10


# Items and sub-items classes


class ApplicationContextItem(object):
    def __init__(self):
        self.item_type = 0x10  # Unsigned byte
        self.reserved = 0x00  # Unsigned byte
        self.item_length = None  # Unsigned short
        self.application_context_name = None  # String

    def __repr__(self):
        return ''.join([' Application context item\n',
                        '  Item type: 0x%02x\n' % self.item_type,
                        '  Item length: %d\n' % self.item_length,
                        '  Presentation context ID: %s\n' %
                        self.application_context_name])

    @classmethod
    def from_params(cls, params):
        # Params is a string
        instance = cls()
        instance.application_context_name = params
        instance.item_length = len(instance.application_context_name)
        return instance

    def to_params(self):
        # Returns the application context name
        return self.application_context_name

    def encode(self):
        return ''.join([struct.pack('B', self.item_type),
                        struct.pack('B', self.reserved),
                        struct.pack('>H', self.item_length),
                        self.application_context_name])

    @classmethod
    def decode(cls, stream):
        """Decodes application context item from data stream

        :rtype : ApplicationContextItem
        :param stream: raw data stream
        :return decoded item
        """
        decoded_obj = cls()
        decoded_obj.item_type, decoded_obj.reserved, \
            decoded_obj.item_length = struct.unpack('> B B H', stream.read(4))
        decoded_obj.application_context_name = stream.read(
            decoded_obj.item_length)
        return decoded_obj

    def total_length(self):
        return 4 + self.item_length


class PresentationContextItemRQ(object):
    def __init__(self):
        self.item_type = 0x20  # Unsigned byte
        self.reserved1 = 0x00  # Unsigned byte
        self.item_length = None  # Unsigned short
        self.presentation_context_id = None  # Unsigned byte

        self.reserved2 = 0x00  # Unsigned byte
        self.reserved3 = 0x00  # Unsigned byte
        self.reserved4 = 0x00  # Unsigned byte
        # abstract_transfer_syntax_sub_items is a list
        # containing the following elements:
        #         One AbstractSyntaxSubItem
        #     One of more TransferSyntaxSubItem
        self.abstract_transfer_syntax_sub_items = []

    def __repr__(self):
        tmp = ''.join([" Presentation context RQ item\n",
                       "  Item type: 0x%02x\n" % self.item_type,
                       "  Item length: %d\n" % self.item_length,
                       "  Presentation context ID: %d\n" %
                       self.presentation_context_id])
        tmp2 = ''.join([item.__repr__()
                        for item in self.abstract_transfer_syntax_sub_items])
        return tmp + tmp2

    @classmethod
    def from_params(cls, params):
        # params is a list of the form
        # [ID, AbstractSyntaxName, [TransferSyntaxNames]]
        instance = cls()
        instance.presentation_context_id = params[0]
        tmp_abs_syn = AbstractSyntaxSubItem.from_params(params[1])
        instance.abstract_transfer_syntax_sub_items.append(tmp_abs_syn)
        for item in params[2]:
            tmp_tr_syn = TransferSyntaxSubItem.from_params(item)
            instance.abstract_transfer_syntax_sub_items.append(tmp_tr_syn)
        instance.item_length = 4
        for item in instance.abstract_transfer_syntax_sub_items:
            instance.item_length = instance.item_length + item.total_length()
        return instance

    def to_params(self):
        # Returns a list of the form
        # [ID, AbstractSyntaxName, [TransferSyntaxNames]]
        return [self.presentation_context_id,
                self.abstract_transfer_syntax_sub_items[0].to_params(),
                [item.to_params()
                 for item in self.abstract_transfer_syntax_sub_items[1:]]]

    def encode(self):
        tmp = ''.join([struct.pack('B', self.item_type),
                       struct.pack('B', self.reserved1),
                       struct.pack('>H', self.item_length),
                       struct.pack('B', self.presentation_context_id),
                       struct.pack('B', self.reserved2),
                       struct.pack('B', self.reserved3),
                       struct.pack('B', self.reserved4)])
        tmp2 = ''.join([item.encode()
                        for item in self.abstract_transfer_syntax_sub_items])
        return tmp + tmp2

    @classmethod
    def decode(cls, stream):
        """Decodes presentation context item 'request' from data stream

        :rtype : PresentationContextItemRQ
        :param stream: raw data stream
        :return: decoded context item
        """
        decoded_item = cls()
        decoded_item.item_type, decoded_item.reserved1, \
            decoded_item.item_length, \
            decoded_item.presentation_context_id, \
            decoded_item.reserved2, decoded_item.reserved3, \
            decoded_item.reserved4 = struct.unpack('> B B H B B B B',
                                                   stream.read(8))
        tmp = AbstractSyntaxSubItem.decode(stream)
        decoded_item.abstract_transfer_syntax_sub_items.append(tmp)
        next_item_type = next_type(stream)
        while next_item_type == 0x40:
            tmp = TransferSyntaxSubItem.decode(stream)
            decoded_item.abstract_transfer_syntax_sub_items.append(tmp)
            next_item_type = next_type(stream)
        return decoded_item

    def total_length(self):
        return 4 + self.item_length


class PresentationContextItemAC(object):
    def __init__(self):
        self.item_type = 0x21  # Unsigned byte
        self.reserved1 = 0x00  # Unsigned byte
        self.item_length = None  # Unsigned short
        self.presentation_context_id = None  # Unsigned byte
        self.reserved2 = 0x00  # Unsigned byte
        self.result_reason = None  # Unsigned byte
        self.reserved3 = 0x00  # Unsigned byte
        self.transfer_syntax_sub_item = None  # TransferSyntaxSubItem object

    def __repr__(self):
        return ''.join([' Presentation context AC item\n',
                        '  Item type: 0x%02x\n' % self.item_type,
                        '  Item length: %d\n' % self.item_length,
                        '  Presentation context ID: %d\n' %
                        self.presentation_context_id,
                        '  Result/Reason: %d\n' % self.result_reason,
                        self.transfer_syntax_sub_item.__repr__()])

    @classmethod
    def from_params(cls, params):
        # params is a list of the form [ID, Response, TransferSyntax].
        instance = cls()
        instance.presentation_context_id = params[0]
        instance.result_reason = params[1]
        instance.transfer_syntax_sub_item = TransferSyntaxSubItem.from_params(
            params[2])
        instance.item_length = 4 + instance.transfer_syntax_sub_item.total_length()
        return instance

    def to_params(self):
        # Returns a list of the form [ID, Response, TransferSyntax].
        return [self.presentation_context_id, self.result_reason,
                self.transfer_syntax_sub_item.to_params()]

    def encode(self):
        return ''.join([struct.pack('B', self.item_type),
                        struct.pack('B', self.reserved1),
                        struct.pack('>H', self.item_length),
                        struct.pack('B', self.presentation_context_id),
                        struct.pack('B', self.reserved2),
                        struct.pack('B', self.result_reason),
                        struct.pack('B', self.reserved3),
                        self.transfer_syntax_sub_item.encode()])

    @classmethod
    def decode(cls, stream):
        """Decodes presentation context item 'accepted' from data stream

        :rtype : PresentationContextItemAC
        :param stream: raw data stream
        :return: decoded context item
        """
        decoded_item = cls()
        decoded_item.item_type, decoded_item.reserved1, \
            decoded_item.item_length, decoded_item.presentation_context_id, \
            decoded_item.reserved2, decoded_item.result_reason, \
            decoded_item.reserved3 = struct.unpack('> B B H B B B B',
                                                   stream.read(8))
        decoded_item.transfer_syntax_sub_item = TransferSyntaxSubItem.decode(
            stream)
        return decoded_item

    def total_length(self):
        return 4 + self.item_length


class AbstractSyntaxSubItem(object):
    def __init__(self):
        self.reserved = 0x00  # Unsigned byte
        self.item_type = 0x30  # Unsigned byte
        self.item_length = None  # Unsigned short
        self.abstract_syntax_name = None  # String

    def __repr__(self):
        return ''.join(['  Abstract syntax sub item\n',
                        '   Item type: 0x%02x\n' % self.item_type,
                        '   Item length: %d\n' % self.item_length,
                        '   Abstract syntax name: %s\n' %
                        self.abstract_syntax_name])

    @classmethod
    def from_params(cls, params):
        # params is a string
        instance = cls()
        instance.abstract_syntax_name = params
        instance.item_length = len(instance.abstract_syntax_name)
        return instance

    def to_params(self):
        # Returns the abstract syntax name
        return self.abstract_syntax_name

    def encode(self):
        return ''.join([struct.pack('B', self.item_type),
                        struct.pack('B', self.reserved),
                        struct.pack('>H', self.item_length),
                        self.abstract_syntax_name])

    @classmethod
    def decode(cls, stream):
        """Decodes abstract syntax sub-item from data stream

        :rtype : AbstractSyntaxSubItem
        :param stream: raw data stream
        :return: decoded abstract syntax sub-item
        """
        decoded_item = cls()
        decoded_item.item_type, decoded_item.reserved, \
            decoded_item.item_length = struct.unpack('> B B H', stream.read(4))
        decoded_item.abstract_syntax_name = stream.read(
            decoded_item.item_length)
        return decoded_item

    def total_length(self):
        return 4 + self.item_length


class TransferSyntaxSubItem(object):
    def __init__(self):
        self.item_type = 0x40  # Unsigned byte
        self.reserved = 0x00  # Unsigned byte
        self.item_length = None  # Unsigned short
        self.transfer_syntax_name = None  # String

    def __repr__(self):
        return ''.join(['  Transfer syntax sub item\n',
                        '   Item type: 0x%02x\n' % self.item_type,
                        '   Item length: %d\n' % self.item_length,
                        '   Transfer syntax name: %s\n' %
                        self.transfer_syntax_name])

    @classmethod
    def from_params(cls, params):
        # params is a string.
        instance = cls()
        instance.transfer_syntax_name = params
        instance.item_length = len(instance.transfer_syntax_name)
        return instance

    def to_params(self):
        # Returns the transfer syntax name
        return self.transfer_syntax_name

    def encode(self):
        return ''.join([struct.pack('B', self.item_type),
                        struct.pack('B', self.reserved),
                        struct.pack('>H', self.item_length),
                        self.transfer_syntax_name])

    @classmethod
    def decode(cls, stream):
        """Decodes transfer syntax sub-item from data stream

        :rtype : TransferSyntaxSubItem
        :param stream: raw data stream
        :return: decoded transfer syntax sub-item
        """
        decoded_item = cls()
        decoded_item.item_type, decoded_item.reserved, \
            decoded_item.item_length = struct.unpack('> B B H', stream.read(4))
        decoded_item.transfer_syntax_name = stream.read(
            decoded_item.item_length)
        return decoded_item

    def total_length(self):
        return 4 + self.item_length


class UserInformationItem(object):
    def __init__(self):
        self.item_type = 0x50  # Unsigned byte
        self.reserved = 0x00  # Unsigned byte
        self.item_length = None  # Unsigned short

        #  user_data is a list containing the following:
        #  1 MaximumLengthItem
        #  0 or more raw strings encoding user data items
        # List of sub items
        self.user_data = []

    def __repr__(self):
        tmp = [' User information item\n',
               '  Item type: 0x%02x\n' % self.item_type,
               '  Item length: %d\n' % self.item_length, '  User Data:\n ']
        if len(self.user_data) > 1:
            tmp.append(str(self.user_data[0]))
            for ii in self.user_data[1:]:
                tmp.append('   User Data Item: ' + str(ii) + "\n")
        return ''.join(tmp)

    @classmethod
    def from_params(cls, params):
        # params is a user_data
        instance = cls()
        for param in params:
            instance.user_data.append(param.to_params())
        instance.item_length = 0
        for data in instance.user_data:
            instance.item_length = instance.item_length + data.total_length()
        return instance

    def to_params(self):
        tmp = []
        for ii in self.user_data:
            tmp.append(ii.to_params())
        return tmp

    def encode(self):
        tmp = ''.join([struct.pack('B', self.item_type),
                       struct.pack('B', self.reserved),
                       struct.pack('>H', self.item_length)])
        tmp2 = ''.join([data.encode() for data in self.user_data])
        return tmp + tmp2

    @classmethod
    def decode(cls, stream):
        """Decodes user information item from data stream

        :rtype : UserInformationItem
        :param stream: raw data stream
        :return: decoded user information item
        """
        decoded_item = cls()
        decoded_item.item_type, decoded_item.reserved, \
            decoded_item.item_length = struct.unpack('> B B H', stream.read(4))
        # read the rest of user info
        decoded_item.user_data = [sub_item for sub_item in sub_items(stream)]
        return decoded_item

    def total_length(self):
        return 4 + self.item_length


class MaximumLengthParameters(object):
    def __init__(self):
        self.maximum_length_received = None

    def __eq__(self, other):
        return self.maximum_length_received == other.maximum_length_received

    def to_params(self):
        return MaximumLengthSubItem.from_params(self)


class MaximumLengthSubItem(object):
    def __init__(self):
        self.item_type = 0x51  # Unsigned byte
        self.reserved = 0x00  # Unsigned byte
        self.item_length = 0x0004  # Unsigned short
        self.maximum_length_received = None  # Unsigned int

    def __repr__(self):
        return ''.join(['  Maximum length sub item\n',
                        '    Item type: 0x%02x\n' % self.item_type,
                        '    Item length: %d\n' % self.item_length,
                        '    Maximum Length Received: %d\n' %
                        self.maximum_length_received])

    @classmethod
    def from_params(cls, params):
        instance = cls()
        instance.maximum_length_received = params.maximum_length_received
        return instance

    def to_params(self):
        tmp = MaximumLengthParameters()
        tmp.maximum_length_received = self.maximum_length_received
        return tmp

    def encode(self):
        return ''.join([struct.pack('B', self.item_type),
                        struct.pack('B', self.reserved),
                        struct.pack('>H', self.item_length),
                        struct.pack('>I', self.maximum_length_received)])

    @classmethod
    def decode(cls, stream):
        """Decodes maximum length sub-item from data stream

        :rtype : MaximumLengthSubItem
        :param stream: raw data stream
        :return: decoded maximum length sub-item
        """
        decoded_item = cls()
        decoded_item.item_type, decoded_item.reserved, \
            decoded_item.item_length, \
            decoded_item.maximum_length_received = struct.unpack('> B B H I',
                                                                 stream.read(8))
        return decoded_item

    def total_length(self):
        return 0x08


class PresentationDataValueItem(object):
    def __init__(self):
        self.item_length = None  # Unsigned int
        self.presentation_context_id = None  # Unsigned byte
        self.presentation_data_value = None  # String

    def __repr__(self):
        return ''.join([' Presentation value data item\n',
                        '  Item length: %d\n' % self.item_length,
                        '  Presentation context ID: %d\n' %
                        self.presentation_context_id,
                        '  Presentation data value: %s ...\n' %
                        self.presentation_data_value[:20]])

    @classmethod
    def from_params(cls, params):
        # Takes a PresentationDataValue object
        instance = cls()
        instance.presentation_context_id = params[0]
        instance.presentation_data_value = params[1]
        instance.item_length = 1 + len(instance.presentation_data_value)
        return instance

    def to_params(self):
        # Returns a PresentationDataValue
        tmp = PresentationDataValueItem()
        tmp.presentation_context_id = self.presentation_context_id
        tmp.presentation_data_value = self.presentation_data_value
        return tmp

    def encode(self):
        return ''.join([struct.pack('>I', self.item_length),
                        struct.pack('B', self.presentation_context_id),
                        self.presentation_data_value])

    @classmethod
    def decode(cls, stream):
        """Decodes presentation data value item from data stream

        :rtype : PresentationDataValueItem
        :param stream: raw data stream
        :return: decoded presentation data value item
        """
        decoded_item = cls()
        decoded_item.item_length, \
            decoded_item.presentation_context_id = struct.unpack('> I B',
                                                                 stream.read(5))
        # Presentation data value is left in raw string format.
        # The Application Entity is responsible for dealing with it.
        decoded_item.presentation_data_value = stream.read(
            int(decoded_item.item_length) - 1)
        return decoded_item

    def total_length(self):
        return 4 + self.item_length


class GenericUserDataSubItem(object):
    """
    This class is provided only to allow user data to converted to and from
    PDUs. The actual data is not interpreted. This is left to the user.
    """

    def __init__(self):
        self.item_type = None  # Unsigned byte
        self.reserved = 0x00  # Unsigned byte
        self.item_length = None  # Unsigned short
        self.user_data = None  # Raw string

    def __repr__(self):
        tmp = ['User data item\n', '  Item type: %d\n' % self.item_type,
               '  Item length: %d\n' % self.item_length]
        if len(self.user_data) > 1:
            tmp.append('  User data: %s ...\n' % self.user_data[:10])
        return ''.join(tmp)

    @classmethod
    def from_params(cls, params):
        instance = cls()
        instance.item_length = len(params.user_data)
        instance.user_data = params.user_data
        instance.item_type = params.item_type
        return instance

    def to_params(self):
        tmp = GenericUserDataSubItem()
        tmp.item_type = self.item_type
        tmp.user_data = self.user_data
        return tmp

    def encode(self):
        return ''.join([struct.pack('B', self.item_type),
                        struct.pack('B', self.reserved),
                        struct.pack('>H', self.item_length), self.user_data])

    @classmethod
    def decode(cls, stream):
        """Decodes generic data sub-item from data stream

        :rtype : GenericUserDataSubItem
        :param stream: raw data stream
        :return: decoded generic data sub-item
        """
        decoded_item = cls()
        decoded_item.item_type, decoded_item.reserved, \
            decoded_item.item_length = struct.unpack('> B B H', stream.read(4))
        # User data value is left in raw string format. The Application Entity
        # is responsible for dealing with it.
        decoded_item.user_data = stream.read(int(decoded_item.item_length) - 1)
        return decoded_item

    def total_length(self):
        return 4 + self.item_length


SUB_ITEM_TYPES = {
    0x52: dimseparameters.ImplementationClassUIDSubItem,
    0x51: MaximumLengthSubItem,
    0x55: dimseparameters.ImplementationVersionNameSubItem,
    0x53: dimseparameters.AsynchronousOperationsWindowSubItem,
    0x54: dimseparameters.ScpScuRoleSelectionSubItem,
    0x56: dimseparameters.SOPClassExtentedNegociationSubItem
}


def next_type(stream):
    char = stream.read(1)
    if char == '':
        return None  # we are at the end of the file
    stream.seek(-1, 1)
    return struct.unpack('B', char)[0]


def sub_items(stream):
    item_type = next_type(stream)
    while item_type:
        try:
            tmp = SUB_ITEM_TYPES[item_type]()
            tmp.decode(stream)
            yield tmp
            item_type = next_type(stream)
        except KeyError:
            raise exceptions.PDUProcessingError(
                'Invalid sub-item', "0x%X" % item_type)

