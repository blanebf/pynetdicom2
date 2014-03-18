#
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
from StringIO import StringIO
import dulparameters
import dimseparameters


class PDUBase(object):
    """Base class for PDUs."""
    def __init__(self):
        pass

    def __eq__(self, other):
        """Equality of tho PDUs"""
        for k, v in self.__dict__.iteritems():
            if v != other.__dict__[k]:
                return False
        return True


class AAssociateRqPDU(PDUBase):

    """This class represents the A-ASSOCIATE-RQ PDU"""

    def __init__(self):
        super(AAssociateRqPDU, self).__init__()

        self.pdu_type = 0x01                        # Unsigned byte
        self.reserved1 = 0x00                      # Unsigned byte
        self.pdu_length = None                      # Unsigned int
        self.protocol_version = 1                   # Unsigned short
        self.reserved2 = 0x00                      # Unsigned short
        self.called_ae_title = None                # string of length 16
        self.calling_ae_title = None               # string of length 16
        self.reserved3 = (0, 0, 0, 0, 0, 0, 0, 0)  # 32 bytes

        # VariablesItems is a list containing the following:
        #   1 ApplicationContextItem
        #   1 or more PresentationContextItemRQ
        #   1 UserInformationItem
        self.variable_items = []

    def __repr__(self):
        tmp = ''.join(['A-ASSOCIATE-RQ PDU\n', ' PDU type: 0x%02x\n' % self.pdu_type,
                       ' PDU length: %d\n' % self.pdu_length, ' Called AE title: %s\n' % self.called_ae_title,
                       ' Calling AE title: %s\n' % self.calling_ae_title])
        tmp2 = ''.join([item.__repr__() for item in self.variable_items])
        return '%s%s\n' % (tmp, tmp2)

    def from_params(self, params):
        # Params is an A_ASSOCIATE_ServiceParameters object
        self.calling_ae_title = params.calling_ae_title
        self.called_ae_title = params.called_ae_title
        tmp_app_cont = ApplicationContextItem()
        tmp_app_cont.from_params(params.application_context_name)
        self.variable_items.append(tmp_app_cont)

        # Make presentation contexts
        for ii in params.presentation_context_definition_list:
            tmp_pres_cont = PresentationContextItemRQ()
            tmp_pres_cont.from_params(ii)
            self.variable_items.append(tmp_pres_cont)

        # Make user information
        tmp_user_info = UserInformationItem()
        tmp_user_info.from_params(params.user_information)
        self.variable_items.append(tmp_user_info)

        self.pdu_length = 68
        for ii in self.variable_items:
            self.pdu_length = self.pdu_length + ii.total_length()

    def to_params(self):
        # Returns an A_ASSOCIATE_ServiceParameters object
        assoc = dulparameters.AAssociateServiceParameters()
        assoc.calling_ae_title = self.calling_ae_title
        assoc.called_ae_title = self.called_ae_title
        assoc.application_context_name = self.variable_items[0].application_context_name

        # Write presentation contexts
        for ii in self.variable_items[1:-1]:
            assoc.presentation_context_definition_list.append(ii.to_params())

        # Write user information
        assoc.user_information = self.variable_items[-1].to_params()
        return assoc

    def encode(self):
        tmp = ''.join([struct.pack('B', self.pdu_type), struct.pack('B', self.reserved1),
                       struct.pack('>I', self.pdu_length), struct.pack('>H', self.protocol_version),
                       struct.pack('>H',  self.reserved2), struct.pack('16s', self.called_ae_title),
                       struct.pack('16s', self.calling_ae_title), struct.pack('>8I', 0, 0, 0, 0, 0, 0, 0, 0)])

        tmp2 = ''.join([item.encode() for item in self.variable_items])
        return tmp + tmp2

    def decode(self, rawstring):
        stream = StringIO(rawstring)
        self.pdu_type, self.reserved1, self.pdu_length, self.protocol_version, self.reserved2, \
            self.called_ae_title, self.calling_ae_title = struct.unpack('> B B I H H 16s 16s', stream.read(42))
        self.reserved3 = struct.unpack('> 8I', stream.read(32))
        while 1:
            type_ = next_type(stream)
            if type_ == 0x10:
                tmp = ApplicationContextItem()
            elif type_ == 0x20:
                tmp = PresentationContextItemRQ()
            elif type_ == 0x50:
                tmp = UserInformationItem()
            elif type_ is None:
                break
            else:
                raise RuntimeError('InvalidVariableItem')
            tmp.decode(stream)
            self.variable_items.append(tmp)

    def total_length(self):
        return 6 + self.pdu_length


class AAssociateAcPDU(PDUBase):

    """This class represents the A-ASSOCIATE-AC PDU"""

    def __init__(self):
        super(AAssociateAcPDU, self).__init__()

        self.pdu_type = 0x02       # Unsigned byte
        self.reserved1 = 0x00      # Unsigned byte
        self.pdu_length = None     # Unsigned int
        self.protocol_version = 1  # Unsigned short
        self.reserved2 = 0x00      # Unsigned short
        self.reserved3 = None      # string of length 16
        self.reserved4 = None      # string of length 16
        self.reserved5 = (0x0000, 0x0000, 0x0000, 0x0000)  # 32 bytes

        # VariablesItems is a list containing the following:
        #   1 ApplicationContextItem
        #   1 or more PresentationContextItemAC
        #   1 UserInformationItem
        self.variable_items = []

    def __repr__(self):
        tmp = ''.join(["A-ASSOCIATE-AC PDU\n", " PDU type: 0x%02x\n" % self.pdu_type,
                       " PDU length: %d\n" % self.pdu_length, " Called AE title: %s\n" % self.reserved3,
                       " Calling AE title: %s\n" % self.reserved4])
        tmp2 = ''.join([item.__repr__() for item in self.variable_items])
        return '%s%s\n' % (tmp, tmp2)

    def from_params(self, params):
        # Params is an A_ASSOCIATE_ServiceParameters object
        self.reserved3 = params.called_ae_title
        self.reserved4 = params.calling_ae_title
        # Make application context
        tmp_app_cont = ApplicationContextItem()
        tmp_app_cont.from_params(params.application_context_name)
        self.variable_items.append(tmp_app_cont)
        # Make presentation contexts
        for ii in params.presentation_context_definition_result_list:
            tmp_pres_cont = PresentationContextItemAC()
            tmp_pres_cont.from_params(ii)
            self.variable_items.append(tmp_pres_cont)
        # Make user information
        tmp_user_info = UserInformationItem()
        tmp_user_info.from_params(params.user_information)
        self.variable_items.append(tmp_user_info)
        # Compute PDU length
        self.pdu_length = 68
        for ii in self.variable_items:
            self.pdu_length = self.pdu_length + ii.total_length()

    def to_params(self):
        assoc = dulparameters.AAssociateServiceParameters()
        assoc.called_ae_title = self.reserved3
        assoc.calling_ae_title = self.reserved4
        assoc.application_context_name = self.variable_items[0].to_params()

        # Write presentation context
        for ii in self.variable_items[1:-1]:
            assoc.presentation_context_definition_result_list.append(ii.to_params())

        # Write user information
        assoc.user_information = self.variable_items[-1].to_params()
        assoc.result = 'Accepted'
        return assoc

    def encode(self):
        tmp = ''.join([struct.pack('B', self.pdu_type), struct.pack('B', self.reserved1),
                       struct.pack('>I', self.pdu_length), struct.pack('>H', self.protocol_version),
                       struct.pack('>H',  self.reserved2), struct.pack('16s', self.reserved3),
                       struct.pack('16s', self.reserved4), struct.pack('>8I', 0, 0, 0, 0, 0, 0, 0, 0)])

        # variable item elements
        tmp2 = ''.join([item.encode() for item in self.variable_items])
        return tmp + tmp2

    def decode(self, rawstring):
        stream = StringIO(rawstring)
        self.pdu_type, self.reserved1, self.pdu_length, self.protocol_version, self.reserved2, \
            self.reserved3, self.reserved4 = struct.unpack('> B B I H H 16s 16s', stream.read(42))
        self.reserved5 = struct.unpack('>8I', stream.read(32))
        while 1:
            type_ = next_type(stream)
            if type_ == 0x10:
                tmp = ApplicationContextItem()
            elif type_ == 0x21:
                tmp = PresentationContextItemAC()
            elif type_ == 0x50:
                tmp = UserInformationItem()
            elif type_ is None:
                break
            else:
                raise RuntimeError('InvalidVariableItem')
            tmp.decode(stream)
            self.variable_items.append(tmp)

    def total_length(self):
        return 6 + self.pdu_length


class AAssociateRjPDU(PDUBase):

    """This class represents the A-ASSOCIATE-RJ PDU"""

    def __init__(self):
        super(AAssociateRjPDU, self).__init__()

        self.pdu_type = 0x03          # Unsigned byte
        self.reserved1 = 0x00         # Unsigned byte
        self.pdu_length = 0x00000004  # Unsigned int
        self.reserved2 = 0x00         # Unsigned byte
        self.result = None            # Unsigned byte
        self.source = None            # Unsigned byte
        self.reason_diag = None       # Unsigned byte

    def __repr__(self):
        return ''.join(['A-ASSOCIATE-RJ PDU\n', ' PDU type: 0x%02x\n' % self.pdu_type,
                        ' PDU length: %d\n' % self.pdu_length, ' Result: %d\n' % self.result,
                        ' Source: %s\n' % str(self.source), ' Reason/Diagnostic: %s\n' % str(self.reason_diag), "\n"])

    def from_params(self, params):
        # Params is an A_ASSOCIATE_ServiceParameters object
        self.result = params.result
        self.source = params.result_source
        self.reason_diag = params.diagnostic

    def to_params(self):
        tmp = dulparameters.AAssociateServiceParameters()
        tmp.result = self.result
        tmp.result_source = self.source
        tmp.diagnostic = self.reason_diag
        return tmp

    def encode(self):
        return ''.join([struct.pack('B', self.pdu_type), struct.pack('B', self.reserved1),
                        struct.pack('>I', self.pdu_length), struct.pack('B', self.reserved2),
                        struct.pack('B', self.result), struct.pack('B', self.source),
                        struct.pack('B', self.reason_diag)])

    def decode(self, rawstring):
        stream = StringIO(rawstring)
        self.pdu_type, self.reserved1, self.pdu_length, self.reserved2, self.result, self.source, \
            self.reason_diag = struct.unpack('> B B I B B B B', stream.read(10))

    def total_length(self):
        return 10


class PDataTfPDU(PDUBase):

    """This class represents the P-DATA-TF PDU"""

    def __init__(self):
        super(PDataTfPDU, self).__init__()

        self.pdu_type = 0x04    # Unsigned byte
        self.reserved = 0x00   # Unsigned byte
        self.pdu_length = None  # Unsigned int

        # List of one of more PresentationDataValueItem
        self.presentation_data_value_items = []

    def __repr__(self):
        tmp = ''.join(['P-DATA-TF PDU\n', ' PDU type: 0x%02x\n' % self.pdu_type, ' PDU length: %d\n' % self.pdu_length])
        tmp2 = ''.join(item.__repr__() for item in self.presentation_data_value_items)
        return '%s%s\n' % (tmp, tmp2)

    def from_params(self, params):
        # Params is an P_DATA_ServiceParameters object
        for ii in params.presentation_data_value_list:
            tmp = PresentationDataValueItem()
            tmp.from_params(ii)
            self.presentation_data_value_items.append(tmp)
        self.pdu_length = 0
        for ii in self.presentation_data_value_items:
            self.pdu_length = self.pdu_length + ii.total_length()

    def to_params(self):
        tmp = dulparameters.PDataServiceParameters()
        tmp.presentation_data_value_list = []
        for ii in self.presentation_data_value_items:
            tmp.presentation_data_value_list.append([ii.presentation_context_id, ii.presentation_data_value])
        return tmp

    def encode(self):
        tmp = ''.join([struct.pack('B', self.pdu_type), struct.pack('B', self.reserved),
                       struct.pack('>I', self.pdu_length)])
        tmp2 = ''.join([item.encode() for item in self.presentation_data_value_items])
        return tmp + tmp2

    def decode(self, rawstring):
        stream = StringIO(rawstring)
        self.pdu_type, self.reserved, self.pdu_length = struct.unpack('> B B I', stream.read(6))
        length_read = 0
        while length_read != self.pdu_length:
            tmp = PresentationDataValueItem()
            tmp.decode(stream)
            length_read += tmp.total_length()
            self.presentation_data_value_items.append(tmp)

    def total_length(self):
        return 6 + self.pdu_length


class AReleaseRqPDU(PDUBase):

    """This class represents the A-ASSOCIATE-RQ PDU"""

    def __init__(self):
        super(AReleaseRqPDU, self).__init__()

        self.pdu_type = 0x05          # Unsigned byte
        self.reserved1 = 0x00         # Unsigned byte
        self.pdu_length = 0x00000004  # Unsigned int
        self.reserved2 = 0x00000000   # Unsigned int

    def __repr__(self):
        return ''.join(['A-RELEASE-RQ PDU\n', ' PDU type: 0x%02x\n' % self.pdu_type,
                        ' PDU length: %d\n' % self.pdu_length, '\n'])

    def from_params(self, params=None):
        # Params is an A_RELEASE_ServiceParameters object. It is optional.
        pass

    def to_params(self):
        tmp = dulparameters.AReleaseServiceParameters()
        tmp.reason = 'normal'
        tmp.result = 'affirmative'
        return tmp

    def encode(self):
        return ''.join([struct.pack('B', self.pdu_type), struct.pack('B', self.reserved1),
                        struct.pack('>I', self.pdu_length),struct.pack('>I', self.reserved2)])

    def decode(self, rawstring):
        stream = StringIO(rawstring)
        self.pdu_type, self.reserved1, self.pdu_length, self.reserved2 = struct.unpack('> B B I I', stream.read(10))

    def total_length(self):
        return 10


class AReleaseRpPDU(PDUBase):

    """This class represents the A-RELEASE-RP PDU"""

    def __init__(self):
        super(AReleaseRpPDU, self).__init__()

        self.pdu_type = 0x06          # Unsigned byte
        self.reserved1 = 0x00         # Unsigned byte
        self.pdu_length = 0x00000004  # Unsigned int
        self.reserved2 = 0x00000000   # Unsigned int

    def __repr__(self):
        return ''.join(['A-RELEASE-RP PDU\n', ' PDU type: 0x%02x\n' % self.pdu_type,
                        ' PDU length: %d\n' % self.pdu_length + '\n'])

    def from_params(self, params=None):
        # Params is an A_RELEASE_ServiceParameters object. It is optional.
        pass

    def to_params(self):
        tmp = dulparameters.AReleaseServiceParameters()
        tmp.reason = 'normal'
        tmp.result = 'affirmative'
        return tmp

    def encode(self):
        return ''.join([struct.pack('B', self.pdu_type), struct.pack('B', self.reserved1),
                        struct.pack('>I', self.pdu_length), struct.pack('>I', self.reserved2)])

    def decode(self, rawstring):
        stream = StringIO(rawstring)
        self.pdu_type, self.reserved1, self.pdu_length, self.reserved2 = struct.unpack('> B B I I', stream.read(10))

    def total_length(self):
        return 10


class AAbortPDU(PDUBase):

    """This class represents the A-ABORT PDU"""

    def __init__(self):
        super(AAbortPDU, self).__init__()

        self.pdu_type = 0x07          # Unsigned byte
        self.reserved1 = 0x00         # Unsigned byte
        self.pdu_length = 0x00000004  # Unsigned int
        self.reserved2 = 0x00         # Unsigned byte
        self.reserved3 = 0x00         # Unsigned byte
        self.abort_source = None      # Unsigned byte
        self.reason_diag = None       # Unsigned byte

    def __repr__(self):
        return ''.join(['A-ABORT PDU\n', ' PDU type: 0x%02x\n' % self.pdu_type, ' PDU length: %d\n' % self.pdu_length,
                        ' Abort Source: %d\n' % self.abort_source, ' Reason/Diagnostic: %d\n' % self.reason_diag, '\n'])

    def from_params(self, params):
        # Params can be an AAbortServiceParameters or APAbortServiceParameters object.
        if isinstance(params, dulparameters.AAbortServiceParameters):  # User initiated abort
            self.reason_diag = 0
            self.abort_source = params.abort_source
        elif isinstance(params, dulparameters.APAbortServiceParameters):  # User provider initiated abort
            self.abort_source = params.abort_source
            self.reason_diag = None

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
        return ''.join([struct.pack('B', self.pdu_type), struct.pack('B', self.reserved1),
                        struct.pack('>I', self.pdu_length), struct.pack('B', self.reserved2),
                        struct.pack('B', self.reserved3), struct.pack('B', self.abort_source),
                        struct.pack('B', self.reason_diag)])

    def decode(self, rawstring):
        stream = StringIO(rawstring)
        (self.pdu_type, self.reserved1, self.pdu_length, self.reserved2,
         self.reserved3, self.abort_source, self.reason_diag) = struct.unpack('> B B I B B B B', stream.read(10))

    def total_length(self):
        return 10


# Items and sub-items classes


class ApplicationContextItem(PDUBase):

    def __init__(self):
        super(ApplicationContextItem, self).__init__()

        self.item_type = 0x10                 # Unsigned byte
        self.reserved = 0x00                  # Unsigned byte
        self.item_length = None               # Unsigned short
        self.application_context_name = None  # String

    def __repr__(self):
        return ''.join([' Application context item\n', '  Item type: 0x%02x\n' % self.item_type,
                       '  Item length: %d\n' % self.item_length,
                       '  Presentation context ID: %s\n' % self.application_context_name])

    def from_params(self, params):
        # Params is a string
        self.application_context_name = params
        self.item_length = len(self.application_context_name)

    def to_params(self):
        # Returns the application context name
        return self.application_context_name

    def encode(self):
        return ''.join([struct.pack('B', self.item_type), struct.pack('B', self.reserved),
                        struct.pack('>H', self.item_length), self.application_context_name])

    def decode(self, stream):
        self.item_type, self.reserved, self.item_length = struct.unpack('> B B H', stream.read(4))
        self.application_context_name = stream.read(self.item_length)

    def total_length(self):
        return 4 + self.item_length


class PresentationContextItemRQ(PDUBase):

    def __init__(self):
        super(PresentationContextItemRQ, self).__init__()

        self.item_type = 0x20                # Unsigned byte
        self.reserved1 = 0x00                # Unsigned byte
        self.item_length = None              # Unsigned short
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
        tmp = ''.join([" Presentation context RQ item\n", "  Item type: 0x%02x\n" % self.item_type,
                       "  Item length: %d\n" % self.item_length,
                       "  Presentation context ID: %d\n" % self.presentation_context_id])
        tmp2 = ''.join([item.__repr__() for item in self.abstract_transfer_syntax_sub_items])
        return tmp + tmp2

    def from_params(self, params):
        # Params is a list of the form [ID, AbstractSyntaxName,
        # [TransferSyntaxNames]]
        self.presentation_context_id = params[0]
        tmp_abs_syn = AbstractSyntaxSubItem()
        tmp_abs_syn.from_params(params[1])
        self.abstract_transfer_syntax_sub_items.append(tmp_abs_syn)
        for ii in params[2]:
            tmp_tr_syn = TransferSyntaxSubItem()
            tmp_tr_syn.from_params(ii)
            self.abstract_transfer_syntax_sub_items.append(tmp_tr_syn)
        self.item_length = 4
        for ii in self.abstract_transfer_syntax_sub_items:
            self.item_length = self.item_length + ii.total_length()

    def to_params(self):
        # Returns a list of the form [ID, AbstractSyntaxName, [TransferSyntaxNames]]
        return [self.presentation_context_id, self.abstract_transfer_syntax_sub_items[0].to_params(),
                [item.to_params() for item in self.abstract_transfer_syntax_sub_items[1:]]]

    def encode(self):
        tmp = ''.join([struct.pack('B', self.item_type), struct.pack('B', self.reserved1),
                       struct.pack('>H', self.item_length), struct.pack('B', self.presentation_context_id),
                       struct.pack('B', self.reserved2), struct.pack('B', self.reserved3),
                       struct.pack('B', self.reserved4)])
        tmp2 = ''.join([item.encode() for item in self.abstract_transfer_syntax_sub_items])
        return tmp + tmp2

    def decode(self, stream):
        self.item_type, self.reserved1, self.item_length, self.presentation_context_id, self.reserved2, \
            self.reserved3, self.reserved4 = struct.unpack('> B B H B B B B', stream.read(8))
        tmp = AbstractSyntaxSubItem()
        tmp.decode(stream)
        self.abstract_transfer_syntax_sub_items.append(tmp)
        next_item_type = next_type(stream)
        while next_item_type == 0x40:
            tmp = TransferSyntaxSubItem()
            tmp.decode(stream)
            self.abstract_transfer_syntax_sub_items.append(tmp)
            next_item_type = next_type(stream)

    def total_length(self):
        return 4 + self.item_length


class PresentationContextItemAC(PDUBase):

    def __init__(self):
        super(PresentationContextItemAC, self).__init__()

        self.item_type = 0x21                 # Unsigned byte
        self.reserved1 = 0x00                 # Unsigned byte
        self.item_length = None               # Unsigned short
        self.presentation_context_id = None   # Unsigned byte
        self.reserved2 = 0x00                 # Unsigned byte
        self.result_reason = None             # Unsigned byte
        self.reserved3 = 0x00                 # Unsigned byte
        self.transfer_syntax_sub_item = None  # TransferSyntaxSubItem object

    def __repr__(self):
        return ''.join([' Presentation context AC item\n', '  Item type: 0x%02x\n' % self.item_type,
                        '  Item length: %d\n' % self.item_length,
                        '  Presentation context ID: %d\n' % self.presentation_context_id,
                        '  Result/Reason: %d\n' % self.result_reason, self.transfer_syntax_sub_item.__repr__()])

    def from_params(self, params):
        # Params is a list of the form [ID, Response, TransferSyntax].
        self.presentation_context_id = params[0]
        self.result_reason = params[1]
        self.transfer_syntax_sub_item = TransferSyntaxSubItem()
        self.transfer_syntax_sub_item.from_params(params[2])
        self.item_length = 4 + self.transfer_syntax_sub_item.total_length()

    def to_params(self):
        # Returns a list of the form [ID, Response, TransferSyntax].
        return [self.presentation_context_id, self.result_reason, self.transfer_syntax_sub_item.to_params()]

    def encode(self):
        return ''.join([struct.pack('B', self.item_type), struct.pack('B', self.reserved1),
                        struct.pack('>H', self.item_length), struct.pack('B', self.presentation_context_id),
                        struct.pack('B', self.reserved2), struct.pack('B', self.result_reason),
                        struct.pack('B', self.reserved3), self.transfer_syntax_sub_item.encode()])

    def decode(self, stream):
        self.item_type, self.reserved1, self.item_length, self.presentation_context_id,\
            self.reserved2, self.result_reason, self.reserved3 = struct.unpack('> B B H B B B B', stream.read(8))
        self.transfer_syntax_sub_item = TransferSyntaxSubItem()
        self.transfer_syntax_sub_item.decode(stream)

    def total_length(self):
        return 4 + self.item_length


class AbstractSyntaxSubItem(PDUBase):

    def __init__(self):
        super(AbstractSyntaxSubItem, self).__init__()

        self.reserved = 0x00              # Unsigned byte
        self.item_type = 0x30             # Unsigned byte
        self.item_length = None           # Unsigned short
        self.abstract_syntax_name = None  # String

    def __repr__(self):
        return ''.join(['  Abstract syntax sub item\n', '   Item type: 0x%02x\n' % self.item_type,
                        '   Item length: %d\n' % self.item_length,
                        '   Abstract syntax name: %s\n' % self.abstract_syntax_name])

    def from_params(self, params):
        # Params is a string
        self.abstract_syntax_name = params
        self.item_length = len(self.abstract_syntax_name)

    def to_params(self):
        # Returns the abstract syntax name
        return self.abstract_syntax_name

    def encode(self):
        return ''.join([struct.pack('B', self.item_type), struct.pack('B', self.reserved),
                        struct.pack('>H', self.item_length), self.abstract_syntax_name])

    def decode(self, stream):
        self.item_type, self.reserved, self.item_length = struct.unpack('> B B H', stream.read(4))
        self.abstract_syntax_name = stream.read(self.item_length)

    def total_length(self):
        return 4 + self.item_length


class TransferSyntaxSubItem(PDUBase):

    def __init__(self):
        super(TransferSyntaxSubItem, self).__init__()

        self.item_type = 0x40             # Unsigned byte
        self.reserved = 0x00              # Unsigned byte
        self.item_length = None           # Unsigned short
        self.transfer_syntax_name = None  # String

    def __repr__(self):
        return ''.join(['  Transfer syntax sub item\n', '   Item type: 0x%02x\n' % self.item_type,
                        '   Item length: %d\n' % self.item_length,
                        '   Transfer syntax name: %s\n' % self.transfer_syntax_name])

    def from_params(self, params):
        # Params is a string.
        self.transfer_syntax_name = params
        self.item_length = len(self.transfer_syntax_name)

    def to_params(self):
        # Returns the transfer syntax name
        return self.transfer_syntax_name

    def encode(self):
        return ''.join([struct.pack('B', self.item_type), struct.pack('B', self.reserved),
                        struct.pack('>H', self.item_length), self.transfer_syntax_name])

    def decode(self, stream):
        self.item_type, self.reserved, self.item_length = struct.unpack('> B B H', stream.read(4))
        self.transfer_syntax_name = stream.read(self.item_length)

    def total_length(self):
        return 4 + self.item_length


class UserInformationItem(PDUBase):

    def __init__(self):
        super(UserInformationItem, self).__init__()

        self.item_type = 0x50  # Unsigned byte
        self.reserved = 0x00  # Unsigned byte
        self.item_length = None  # Unsigned short

        #  user_data is a list containing the following:
        #  1 MaximumLengthItem
        #  0 or more raw strings encoding user data items
        # List of sub items
        self.user_data = []

    def __repr__(self):
        tmp = [' User information item\n', '  Item type: 0x%02x\n' % self.item_type,
               '  Item length: %d\n' % self.item_length, '  User Data:\n ']
        if len(self.user_data) > 1:
            tmp.append(str(self.user_data[0]))
            for ii in self.user_data[1:]:
                tmp.append('   User Data Item: ' + str(ii) + "\n")
        return ''.join(tmp)

    def from_params(self, params):
        # Params is a user_data
        for ii in params:
            self.user_data.append(ii.to_params())
        self.item_length = 0
        for ii in self.user_data:
            self.item_length = self.item_length + ii.total_length()

    def to_params(self):
        tmp = []
        for ii in self.user_data:
            tmp.append(ii.to_params())
        return tmp

    def encode(self):
        tmp = ''.join([struct.pack('B', self.item_type), struct.pack('B', self.reserved),
                       struct.pack('>H', self.item_length)])
        tmp2 = ''.join([data.encode() for data in self.user_data])
        return tmp + tmp2

    def decode(self, stream):
        self.item_type, self.reserved, self.item_length = struct.unpack('> B B H', stream.read(4))
        # read the rest of user info
        self.user_data = []
        while next_sub_item_type(stream) is not None:
            tmp = next_sub_item_type(stream)()
            tmp.decode(stream)
            self.user_data.append(tmp)

    def total_length(self):
        return 4 + self.item_length


class MaximumLengthParameters(PDUBase):

    def __init__(self):
        super(MaximumLengthParameters, self).__init__()
        self.maximum_length_received = None

    def __eq__(self, other):
        return self.maximum_length_received == other.maximum_length_received

    def to_params(self):
        tmp = MaximumLengthSubItem()
        tmp.from_params(self)
        return tmp


class MaximumLengthSubItem(PDUBase):

    def __init__(self):
        super(MaximumLengthSubItem, self).__init__()

        self.item_type = 0x51                # Unsigned byte
        self.reserved = 0x00                 # Unsigned byte
        self.item_length = 0x0004            # Unsigned short
        self.maximum_length_received = None  # Unsigned int

    def __repr__(self):
        return ''.join(['  Maximum length sub item\n', '    Item type: 0x%02x\n' % self.item_type,
                        '    Item length: %d\n' % self.item_length,
                        '    Maximum Length Received: %d\n' % self.maximum_length_received])

    def from_params(self, params):
        self.maximum_length_received = params.maximum_length_received

    def to_params(self):
        tmp = MaximumLengthParameters()
        tmp.maximum_length_received = self.maximum_length_received
        return tmp

    def encode(self):
        return ''.join([struct.pack('B', self.item_type), struct.pack('B', self.reserved),
                        struct.pack('>H', self.item_length), struct.pack('>I', self.maximum_length_received)])

    def decode(self, stream):
        self.item_type, self.reserved, self.item_length, \
            self.maximum_length_received = struct.unpack('> B B H I', stream.read(8))

    def total_length(self):
        return 0x08


class PresentationDataValueItem(PDUBase):

    def __init__(self):
        super(PresentationDataValueItem, self).__init__()

        self.item_length = None              # Unsigned int
        self.presentation_context_id = None  # Unsigned byte
        self.presentation_data_value = None  # String

    def __repr__(self):
        return ''.join([' Presentation value data item\n', '  Item length: %d\n' % self.item_length,
                        '  Presentation context ID: %d\n' % self.presentation_context_id,
                        '  Presentation data value: %s ...\n' % self.presentation_data_value[:20]])

    def from_params(self, params):
        # Takes a PresentationDataValue object
        self.presentation_context_id = params[0]
        self.presentation_data_value = params[1]
        self.item_length = 1 + len(self.presentation_data_value)

    def to_params(self):
        # Returns a PresentationDataValue
        tmp = PresentationDataValueItem()
        tmp.presentation_context_id = self.presentation_context_id
        tmp.presentation_data_value = self.presentation_data_value

    def encode(self):
        return ''.join([struct.pack('>I', self.item_length), struct.pack('B', self.presentation_context_id),
                        self.presentation_data_value])

    def decode(self, stream):
        self.item_length, self.presentation_context_id = struct.unpack('> I B', stream.read(5))
        # Presentation data value is left in raw string format.
        # The Application Entity is responsible for dealing with it.
        self.presentation_data_value = stream.read(int(self.item_length) - 1)

    def total_length(self):
        return 4 + self.item_length


class GenericUserDataSubItem(PDUBase):

    """
    This class is provided only to allow user data to converted to and from
    PDUs. The actual data is not interpreted. This is left to the user.
    """

    def __init__(self):
        super(GenericUserDataSubItem, self).__init__()

        self.item_type = None    # Unsigned byte
        self.reserved = 0x00     # Unsigned byte
        self.item_length = None  # Unsigned short
        self.user_data = None    # Raw string

    def __repr__(self):
        tmp = ['User data item\n', '  Item type: %d\n' % self.item_type, '  Item length: %d\n' % self.item_length]
        if len(self.user_data) > 1:
            tmp.append('  User data: %s ...\n' % self.user_data[:10])
        return ''.join(tmp)

    def from_params(self, params):
        self.item_length = len(params.user_data)
        self.user_data = params.user_data
        self.item_type = params.item_type

    def to_params(self):
        tmp = GenericUserDataSubItem()
        tmp.item_type = self.item_type
        tmp.user_data = self.user_data
        return tmp

    def encode(self):
        return ''.join([struct.pack('B', self.item_type), struct.pack('B', self.reserved),
                        struct.pack('>H', self.item_length), self.user_data])

    def decode(self, stream):
        self.item_type, self.reserved, self.item_length = struct.unpack('> B B H', stream.read(4))
        # User data value is left in raw string format. The Application Entity is responsible for dealing with it.
        self.user_data = stream.read(int(self.item_length) - 1)

    def total_length(self):
        return 4 + self.item_length


def next_type(stream):
    char = stream.read(1)
    if char == '':
        return None  # we are at the end of the file
    stream.seek(-1, 1)
    return struct.unpack('B', char)[0]


def next_pdu_type(stream):
    pdu_type = next_type(stream)
    if pdu_type == 0x01:
        return AAssociateRqPDU
    elif pdu_type == 0x02:
        return AAssociateAcPDU
    elif pdu_type == 0x03:
        return AAssociateRjPDU
    elif pdu_type == 0x04:
        return PDataTfPDU
    elif pdu_type == 0x05:
        return AReleaseRqPDU
    elif pdu_type == 0x06:
        return AReleaseRpPDU
    elif pdu_type == 0x07:
        return AAbortPDU
    elif pdu_type is None:
        return None  # end of file
    else:
        raise RuntimeError('InvalidPDU')


def next_sub_item_type(stream):
    item_type = next_type(stream)
    if item_type == 0x52:
        return dimseparameters.ImplementationClassUIDSubItem
    elif item_type == 0x51:
        return MaximumLengthSubItem
    elif item_type == 0x55:
        return dimseparameters.ImplementationVersionNameSubItem
    elif item_type == 0x53:
        return dimseparameters.AsynchronousOperationsWindowSubItem
    elif item_type == 0x54:
        return dimseparameters.ScpScuRoleSelectionSubItem
    elif item_type == 0x56:
        return SOPClassExtentedNegociationSubItem
    elif item_type is None:
        return None
    else:
        raise RuntimeError('Invalid Sub Item', "0x%X" % item_type)


def decode_pdu(rawstring):
    """Takes an encoded PDU as a string and return a PDU object"""
    char = struct.unpack('B', rawstring[0])[0]
    if char == 0x01:
        pdu = AAssociateRqPDU()
    elif char == 0x02:
        pdu = AAssociateAcPDU()
    elif char == 0x03:
        pdu = AAssociateRjPDU()
    elif char == 0x04:
        pdu = PDataTfPDU()
    elif char == 0x05:
        pdu = AReleaseRqPDU()
    elif char == 0x06:
        pdu = AReleaseRpPDU()
    elif char == 0x07:
        pdu = AAbortPDU()
    else:
        raise RuntimeError('InvalidPDUType')
    pdu.decode(rawstring)
    return pdu
