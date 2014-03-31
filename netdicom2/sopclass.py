#
# Copyright (c) 2012 Patrice Munger
# This file is part of pynetdicom, released under a modified MIT license.
#    See the file license.txt included with this distribution, also
#    available at http://pynetdicom.googlecode.com
#
import time
import logging

import dsutils
import netdicom2.exceptions as exceptions
from netdicom2 import dimseparameters


logger = logging.getLogger(__name__)


class Status(object):
    def __init__(self, type_, description, code_range):
        self.type_ = type_
        self.description = description
        self.code_range = code_range

    def __int__(self):
        return self.code_range[0]

    def __repr__(self):
        return self.type_ + ' ' + self.description


Success = Status('Success', 'Sub-operations Complete - No Failure or Warnings',
                 xrange(0x0000, 0x0000 + 1))

Pending = Status('Pending', 'Sub-operations are continuing',
                 xrange(0xFF00, 0xFF00 + 1))
PendingWarning = Status('Pending',
                        'Matches are continuing - Warning that one or more'
                        ' optional keys were not supported for existence '
                        'and/or matching for this identifier',
                        xrange(0xFF01, 0xFF01 + 1))

Cancel = Status('Cancel', 'Sub-operations terminated due to Cancel indication',
                xrange(0xFE00, 0xFE00 + 1))
MatchingTerminatedDueToCancelRequest = Status('Cancel',
                                              'Matching terminated due to '
                                              'Cancel request',
                                              xrange(0xFE00, 0xFE00 + 1))

Warning_ = Status('Warning',
                  'Sub-operations Complete - One or more Failures or Warnings',
                  xrange(0xB000, 0xB000 + 1))
CoercionOfDataElements = Status('Warning', 'Coercion of Data Elements',
                                xrange(0xB000, 0xB000 + 1))
ElementDiscarded = Status('Warning', 'Element Discarded',
                          xrange(0xB006, 0xB006 + 1))
DataSetDoesNotMatchSOPClassWarning = Status('Warning',
                                            'Data Set does not match SOP Class',
                                            xrange(0xB007, 0xB007 + 1))

OutOfResources = Status('Failure', 'Refused: Out of resources',
                        xrange(0xA700, 0xA7FF + 1))
DataSetDoesNotMatchSOPClassFailure = Status('Failure',
                                            'Error: Data Set does not '
                                            'match SOP Class',
                                            xrange(0xA900, 0xA9FF + 1))
CannotUnderstand = Status('Failure', 'Error: Cannot understand',
                          xrange(0xC000, 0xCFFF + 1))
IdentifierDoesNotMatchSOPClass = Status('Failure',
                                        'Identifier does not match SOP Class',
                                        xrange(0xA900, 0xA900 + 1))
UnableToProcess = Status('Failure', 'Unable to process',
                         xrange(0xC000, 0xCFFF + 1))
OutOfResourcesNumberOfMatches = Status('Failure',
                                       'Refused: Out of resources - '
                                       'Unable to calcultate number of matches',
                                       xrange(0xA701, 0xA701 + 1))
OutOfResourcesUnableToPerform = Status('Failure',
                                       'Refused: Out of resources - '
                                       'Unable to perform sub-operations',
                                       xrange(0xA702, 0xA702 + 1))
MoveDestinationUnknown = Status('Failure', 'Refused: Move destination unknown',
                                xrange(0xA801, 0xA801 + 1))


# VERIFICATION SOP CLASSES
VerificationSOPClass = '1.2.840.10008.1.1'

# STORAGE SOP CLASSES
MRImageStorageSOPClass = '1.2.840.10008.5.1.4.1.1.4'
CTImageStorageSOPClass = '1.2.840.10008.5.1.4.1.1.2'
PositronEmissionTomographyImageStorageSOPClass = '1.2.840.10008.5.1.4.1.1.128'
CRImageStorageSOPClass = '1.2.840.10008.5.1.4.1.1.1'
SCImageStorageSOPClass = '1.2.840.10008.5.1.4.1.1.7'
RTImageStorageSOPClass = '1.2.840.10008.5.1.4.1.1.481.1'
RTDoseStorageSOPClass = '1.2.840.10008.5.1.4.1.1.481.2'
RTStructureSetStorageSOPClass = '1.2.840.10008.5.1.4.1.1.481.3'
RTPlanStorageSOPClass = '1.2.840.10008.5.1.4.1.1.481.5'
SpatialRegistrationSOPClass = '1.2.840.10008.5.1.4.1.1.66.1'
EnhancedSRSOPClass = '1.2.840.10008.5.1.4.1.1.88.22'
XRayRadiationDoseSRSOPClass = '1.2.840.10008.5.1.4.1.1.88.67'
DigitalXRayImageStorageForPresentationSOPClass = '1.2.840.10008.5.1.4.1.1.1.1'
DigitalXRayImageStorageForProcessingSOPClass = '1.2.840.10008.5.1.4.1.1.1.1.1'
DigitalMammographyXRayImageStorageForPresentationSOPClass = '1.2.840.10008.5.1.4.1.1.1.2'
DigitalMammographyXRayImageStorageForProcessingSOPClass = '1.2.840.10008.5.1.4.1.1.1.2.1'
DigitalIntraOralXRayImageStorageForPresentationSOPClass = '1.2.840.10008.5.1.4.1.1.1.3'
DigitalIntraOralXRayImageStorageForProcessingSOPClass = '1.2.840.10008.5.1.4.1.1.1.3.1'
XRayAngiographicImageStorageSOPClass = '1.2.840.10008.5.1.4.1.1.12.1'
EnhancedXAImageStorageSOPClass = '1.2.840.10008.5.1.4.1.1.12.1.1'
XRayRadiofluoroscopicImageStorageSOPClass = '1.2.840.10008.5.1.4.1.1.12.2'
EnhancedXRFImageStorageSOPClass = '1.2.840.10008.5.1.4.1.1.12.2.1'
EnhancedCTImageStorageSOPClass = '1.2.840.10008.5.1.4.1.1.2.1'
NMImageStorageSOPClass = '1.2.840.10008.5.1.4.1.1.20'

# QUERY RETRIEVE SOP Classes
PatientRootFindSOPClass = '1.2.840.10008.5.1.4.1.2.1.1'
PatientRootMoveSOPClass = '1.2.840.10008.5.1.4.1.2.1.2'
PatientRootGetSOPClass = '1.2.840.10008.5.1.4.1.2.1.3'
StudyRootFindSOPClass = '1.2.840.10008.5.1.4.1.2.2.1'
StudyRootMoveSOPClass = '1.2.840.10008.5.1.4.1.2.2.2'
StudyRootGetSOPClass = '1.2.840.10008.5.1.4.1.2.2.3'
PatientStudyOnlyFindSOPClass = '1.2.840.10008.5.1.4.1.2.3.1'
PatientStudyOnlyMoveSOPClass = '1.2.840.10008.5.1.4.1.2.3.2'
PatientStudyOnlyGetSOPClass = '1.2.840.10008.5.1.4.1.2.3.3'

ModalityWorkListInformationFindSOPClass = '1.2.840.10008.5.1.4.31'

SOP_CLASSES = {}  # Initialized later


class ServiceClassMeta(type):
    def __new__(mcs, name, bases, dct):
        new_class = type.__new__(mcs, name, bases, dct)
        try:
            SOP_CLASSES.update(
                {sop_class: new_class for sop_class in dct['sop_classes']})
        except KeyError:
            pass
        finally:
            return new_class


class ServiceClass(object):
    __metaclass__ = ServiceClassMeta

    statuses = []
    sop_classes = []

    def __init__(self, ae, uid, dimse, pcid, transfer_syntax,
                 max_pdu_length=16000, asce=None):
        self.ae = ae
        self.uid = uid
        self.dimse = dimse
        self.pcid = pcid
        self.transfer_syntax = transfer_syntax
        self.max_pdu_length = max_pdu_length
        self.asce = asce

    def code_to_status(self, code):
        for status in self.statuses:
            if code in status.code_range:
                return status
        return Status('Failure', 'Unknown or unexpected status',
                      xrange(code, code))

    def check_asce(self):
        if not self.asce:
            raise Exception('Association is not specified. '
                            'Service does not support provider class')


class VerificationServiceClass(ServiceClass):
    statuses = [Success]
    sop_classes = [VerificationSOPClass]

    def scu(self, id_):
        c_echo = dimseparameters.CEchoServiceParameters()
        c_echo.message_id = id_
        c_echo.affected_sop_class_uid = self.uid

        self.dimse.send(c_echo, self.pcid, self.max_pdu_length)

        ans, id_ = self.dimse.receive(wait=True)
        return self.code_to_status(ans.status)

    def scp(self, msg):
        self.check_asce()
        rsp = dimseparameters.CEchoServiceParameters()
        rsp.message_id_being_responded_to = msg.message_id.value
        rsp.status = Success

        # send response
        try:
            self.ae.on_receive_echo(self)
        except exceptions.EventHandlingError:
            logger.error('There was an exception on OnReceiveEcho callback')
        self.dimse.send(rsp, self.pcid, self.asce.max_pdu_length)


class StorageServiceClass(ServiceClass):
    statuses = [OutOfResources, DataSetDoesNotMatchSOPClassFailure,
                CannotUnderstand, CoercionOfDataElements,
                DataSetDoesNotMatchSOPClassWarning, ElementDiscarded, Success]
    sop_classes = [MRImageStorageSOPClass, CTImageStorageSOPClass,
                   PositronEmissionTomographyImageStorageSOPClass,
                   CRImageStorageSOPClass, SCImageStorageSOPClass,
                   RTImageStorageSOPClass, RTDoseStorageSOPClass,
                   RTStructureSetStorageSOPClass, RTPlanStorageSOPClass,
                   SpatialRegistrationSOPClass,
                   EnhancedSRSOPClass, XRayRadiationDoseSRSOPClass,
                   DigitalXRayImageStorageForPresentationSOPClass,
                   DigitalXRayImageStorageForProcessingSOPClass,
                   DigitalMammographyXRayImageStorageForPresentationSOPClass,
                   DigitalMammographyXRayImageStorageForProcessingSOPClass,
                   DigitalIntraOralXRayImageStorageForPresentationSOPClass,
                   DigitalIntraOralXRayImageStorageForProcessingSOPClass,
                   XRayAngiographicImageStorageSOPClass,
                   EnhancedXAImageStorageSOPClass,
                   XRayRadiofluoroscopicImageStorageSOPClass,
                   EnhancedXRFImageStorageSOPClass,
                   EnhancedCTImageStorageSOPClass, NMImageStorageSOPClass]

    def scu(self, dataset, msg_id):
        # build C-STORE primitive
        c_store = dimseparameters.CStoreServiceParameters()
        c_store.message_id = msg_id
        c_store.affected_sop_class_uid = dataset.SOPClassUID
        c_store.affected_sop_instance_uid = dataset.SOPInstanceUID
        c_store.priority = 0x0002
        c_store.dataset = dsutils.encode(dataset,
                                         self.transfer_syntax.is_implicit_VR,
                                         self.transfer_syntax.is_little_endian)
        # send c_store request
        self.dimse.send(c_store, self.pcid, self.max_pdu_length)

        # wait for c-store response
        ans, id_ = self.dimse.receive(wait=True)
        return self.code_to_status(ans.status.value)

    def scp(self, msg):
        self.check_asce()
        try:
            ds = dsutils.decode(msg.dataset,
                                self.transfer_syntax.is_implicit_VR,
                                self.transfer_syntax.is_little_endian)
            status = self.ae.on_receive_store(self, ds)
        except exceptions.EventHandlingError:
            status = CannotUnderstand
        # make response
        rsp = dimseparameters.CStoreServiceParameters()
        rsp.message_id_being_responded_to = msg.message_id
        rsp.affected_sop_instance_uid = msg.affected_sop_instance_uid
        rsp.affected_sop_class_uid = msg.affected_sop_class_uid
        rsp.status = int(status)
        self.dimse.send(rsp, self.pcid, self.asce.max_pdu_length)


class QueryRetrieveServiceClass(ServiceClass):
    pass


class QueryRetrieveFindSOPClass(QueryRetrieveServiceClass):
    sop_classes = [PatientRootFindSOPClass, StudyRootFindSOPClass,
                   PatientStudyOnlyFindSOPClass]
    statuses = [OutOfResources, IdentifierDoesNotMatchSOPClass, UnableToProcess,
                MatchingTerminatedDueToCancelRequest,
                Success, Pending, PendingWarning]

    def scu(self, ds, msg_id):
        # build C-FIND primitive
        c_find = dimseparameters.CFindServiceParameters()
        c_find.message_id = msg_id
        c_find.affected_sop_class_uid = self.uid
        c_find.priority = 0x0002
        c_find.identifier = dsutils.encode(ds,
                                           self.transfer_syntax.is_implicit_VR,
                                           self.transfer_syntax.is_little_endian)

        # send c-find request
        self.dimse.send(c_find, self.pcid, self.max_pdu_length)
        while 1:
            time.sleep(0.001)
            # wait for c-find responses
            ans, id_ = self.dimse.receive(wait=False)
            if not ans:
                continue
            d = dsutils.decode(ans.identifier,
                               self.transfer_syntax.is_implicit_VR,
                               self.transfer_syntax.is_little_endian)
            status = self.code_to_status(ans.status.value).type_
            yield status, d
            if status != 'Pending':
                break

    def scp(self, msg):
        self.check_asce()
        ds = dsutils.decode(msg.identifier, self.transfer_syntax.is_implicit_VR,
                            self.transfer_syntax.is_little_endian)

        # make response
        rsp = dimseparameters.CFindServiceParameters()
        rsp.message_id_being_responded_to = msg.message_id
        rsp.affected_sop_class_uid = msg.affected_sop_class_uid

        gen = self.ae.on_receive_find(self, ds)
        for identifier_ds, status in gen:
            rsp.status = int(status)
            rsp.identifier = dsutils.encode(identifier_ds,
                                            self.transfer_syntax.is_implicit_VR,
                                            self.transfer_syntax.is_little_endian)
            # send response
            self.dimse.send(rsp, self.pcid, self.asce.max_pdu_length)
            time.sleep(0.001)

        rsp = dimseparameters.CFindServiceParameters()
        rsp.message_id_being_responded_to = msg.message_id
        rsp.affected_sop_class_uid = msg.affected_sop_class_uid
        rsp.status = int(Success)
        self.dimse.send(rsp, self.pcid, self.asce.max_pdu_length)


class QueryRetrieveGetSOPClass(QueryRetrieveServiceClass):
    sop_classes = [PatientRootGetSOPClass, StudyRootGetSOPClass,
                   PatientStudyOnlyGetSOPClass]
    statuses = [OutOfResourcesNumberOfMatches, OutOfResourcesUnableToPerform,
                IdentifierDoesNotMatchSOPClass,
                UnableToProcess, Cancel, Warning_, Success, Pending]

    def scu(self, ds, msg_id):
        # build C-GET primitive
        c_get = dimseparameters.CGetServiceParameters()
        c_get.message_id = msg_id
        c_get.affected_sop_class_uid = self.uid
        c_get.priority = 0x0002
        c_get.identifier = dsutils.encode(ds,
                                          self.transfer_syntax.is_implicit_VR,
                                          self.transfer_syntax.is_little_endian)

        # send c-get primitive
        self.dimse.send(c_get, self.pcid, self.max_pdu_length)
        while 1:
            # receive c-store
            msg, id_ = self.dimse.receive(wait=True)
            if isinstance(msg, dimseparameters.CGetServiceParameters):
                if self.code_to_status(msg.status.value).type_ == 'Pending':
                    pass  # pending. intermediate C-GET response
                else:
                    break  # last answer
            elif isinstance(msg, dimseparameters.CStoreServiceParameters):
                # send c-store response
                rsp = dimseparameters.CStoreServiceParameters()
                rsp.message_id_being_responded_to = msg.message_id
                rsp.affected_sop_instance_uid = msg.affected_sop_instance_uid
                rsp.affected_sop_class_uid = msg.affected_sop_class_uid
                try:
                    d = dsutils.decode(msg.dataset,
                                       self.transfer_syntax.is_implicit_VR,
                                       self.transfer_syntax.is_little_endian)
                    sop_class = SOP_CLASSES[d.SOPClassUID]
                    status = self.ae.on_receive_store(sop_class, d)
                    yield sop_class, d
                except exceptions.EventHandlingError:
                    status = CannotUnderstand

                rsp.status = int(status)
                self.dimse.send(rsp, id_, self.max_pdu_length)


class QueryRetrieveMoveSOPClass(QueryRetrieveServiceClass):
    sop_classes = [PatientRootMoveSOPClass, StudyRootMoveSOPClass,
                   PatientStudyOnlyMoveSOPClass]
    statuses = [OutOfResourcesNumberOfMatches, OutOfResourcesUnableToPerform,
                MoveDestinationUnknown,
                IdentifierDoesNotMatchSOPClass, UnableToProcess, Cancel,
                Warning_, Success, Pending]

    def scu(self, ds, dest_ae, msg_id):
        # build C-FIND primitive
        c_move = dimseparameters.CMoveServiceParameters()
        c_move.message_id = msg_id
        c_move.affected_sop_class_uid = self.uid
        c_move.move_destination = dest_ae
        c_move.priority = 0x0002
        c_move.identifier = dsutils.encode(ds,
                                           self.transfer_syntax.is_implicit_VR,
                                           self.transfer_syntax.is_little_endian)
        # send c-find request
        self.dimse.send(c_move, self.pcid, self.max_pdu_length)

        while 1:
            # wait for c-move responses
            time.sleep(0.001)
            ans, id_ = self.dimse.receive(wait=False)
            if not ans:
                continue
            status = self.code_to_status(ans.status.value).type_
            if status != 'Pending':
                break
            yield status

    def scp(self, msg):
        self.check_asce()
        ds = dsutils.decode(msg.identifier, self.transfer_syntax.is_implicit_VR,
                            self.transfer_syntax.is_little_endian)

        # make response
        rsp = dimseparameters.CMoveServiceParameters()
        rsp.message_id_being_responded_to = msg.message_id.value
        rsp.affected_sop_class_uid = msg.affected_sop_class_uid.value
        remote_ae, nop, gen = self.ae.on_receive_move(self, ds,
                                                      msg.MoveDestination.value)
        assoc = self.ae.request_association(remote_ae)
        failed = 0
        warning = 0
        completed = 0
        for data_set in gen:
            # request an association with destination send C-STORE
            obj = assoc.get_scu(data_set.SOPClassUID)
            status = obj.scu(data_set, completed)
            if status.type_ == 'Failed':
                failed += 1
            if status.type_ == 'Warning':
                warning += 1
            rsp.status = int(Pending)
            rsp.number_of_remaining_sub_operations = nop - completed
            rsp.number_of_complete_sub_operations = completed
            rsp.number_of_failed_sub_operations = failed
            rsp.number_of_warning_sub_operations = warning
            completed += 1

            # send response
            self.dimse.send(rsp, self.pcid, self.asce.max_pdu_length)

        rsp = dimseparameters.CMoveServiceParameters()
        rsp.message_id_being_responded_to = msg.message_id.value
        rsp.affected_sop_class_uid = msg.affected_sop_class_uid.value
        rsp.number_of_remaining_sub_operations = nop - completed
        rsp.number_of_complete_sub_operations = completed
        rsp.number_of_failed_sub_operations = failed
        rsp.number_of_warning_sub_operations = warning
        rsp.status = int(Success)
        self.dimse.send(rsp, self.pcid, self.asce.max_pdu_length)
        assoc.release(0)


class BasicWorkListServiceClass(ServiceClass):
    sop_classes = [ModalityWorkListInformationFindSOPClass]


class ModalityWorkListServiceSOPClass(BasicWorkListServiceClass):
    statuses = [OutOfResources, IdentifierDoesNotMatchSOPClass, UnableToProcess,
                MatchingTerminatedDueToCancelRequest,
                Success, Pending, PendingWarning]

    def scu(self, ds, msg_id):
        # build C-FIND primitive
        c_find = dimseparameters.CFindServiceParameters()
        c_find.message_id = msg_id
        c_find.affected_sop_class_uid = self.uid
        c_find.priority = 0x0002
        c_find.identifier = dsutils.encode(ds,
                                           self.transfer_syntax.is_implicit_VR,
                                           self.transfer_syntax.is_little_endian)

        # send c-find request
        self.dimse.send(c_find, self.pcid, self.max_pdu_length)
        while 1:
            time.sleep(0.001)
            # wait for c-find responses
            ans, id_ = self.dimse.receive(wait=False)
            if not ans:
                continue
            d = dsutils.decode(ans.identifier,
                               self.transfer_syntax.is_implicit_VR,
                               self.transfer_syntax.is_little_endian)
            status = self.code_to_status(ans.status.value).type_
            yield status, d
            if status != 'Pending':
                break

    def scp(self, msg):
        self.check_asce()
        ds = dsutils.decode(msg.identifier, self.transfer_syntax.is_implicit_VR,
                            self.transfer_syntax.is_little_endian)

        # make response
        rsp = dimseparameters.CFindServiceParameters()
        rsp.message_id_being_responded_to = msg.message_id
        rsp.affected_sop_class_uid = msg.AffectedSOPClassUID

        gen = self.ae.on_receive_find(self, ds)
        for identifier_ds, status in gen:
            rsp.status = int(status)
            rsp.identifier = dsutils.encode(identifier_ds,
                                            self.transfer_syntax.is_implicit_VR,
                                            self.transfer_syntax.is_little_endian)
            # send response
            self.dimse.send(rsp, self.pcid, self.asce.max_pdu_length)
            time.sleep(0.001)

        # send final response
        rsp = dimseparameters.CFindServiceParameters()
        rsp.message_id_being_responded_to = msg.message_id
        rsp.affected_sop_class_uid = msg.affected_sop_class_uid
        rsp.status = int(Success)
        self.dimse.send(rsp, self.pcid, self.asce.max_pdu_length)
