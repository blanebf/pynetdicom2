# adapted from pydicom source code

import __version__

__version_info__ = __version__.__version__.split('.')

# some imports
import applicationentity
import sopclass


def _setup_request(search_level, search_params, addr, port, aet,
                   transfer_syntax=None):
    import dicom.UID
    import dicom.dataset
    import dicom.datadict

    if not transfer_syntax:
        transfer_syntax = [dicom.UID.ExplicitVRLittleEndian,
                           dicom.UID.ImplicitVRLittleEndian,
                           dicom.UID.ExplicitVRBigEndian]

    remote_ae = {'Address': addr, 'Port': port, 'AET': aet}
    ds = dicom.dataset.Dataset()
    ds.QueryRetrieveLevel = search_level.upper()
    for k, v in search_params.iteritems():
        vr, _, _, _, _ = dicom.datadict.get_entry(k)
        ds.add_new(k, vr, v)
    return remote_ae, ds, transfer_syntax


def c_find(search_level, search_params, addr, port, aet, loc_aet, loc_port,
           transfer_syntax=None):
    remote_ae, ds, transfer_syntax = _setup_request(search_level, search_params,
                                                    addr, port, aet,
                                                    transfer_syntax)
    ae = applicationentity.AE(loc_aet, loc_port,
                              sopclass.QueryRetrieveFindSOPClass.sop_classes,
                              [],
                              transfer_syntax)
    try:
        ae.start()
        assoc = ae.request_association(remote_ae)

        if not assoc:
            # TODO: Replace this exception
            raise Exception('Association request failed')
        for result in assoc.get_scu(sopclass.PATIENT_ROOT_FIND_SOP_CLASS).scu(ds,
                                                                          1):
            yield result[1]
    finally:
        ae.quit()


def c_get(search_level, search_params, addr, port, aet, loc_aet, loc_port,
          transfer_syntax=None):
    remote_ae, ds, transfer_syntax = _setup_request(search_level, search_params,
                                                    addr, port, aet,
                                                    transfer_syntax)
    ae = applicationentity.AE(loc_aet, loc_port,
                              sopclass.QueryRetrieveGetSOPClass.sop_classes, [],
                              transfer_syntax)
    try:
        ae.start()
        assoc = ae.request_association(remote_ae)
        if not assoc:
            # TODO: Replace this exception
            raise Exception('Association request failed')
        for result in assoc.get_scu(sopclass.PATIENT_ROOT_GET_SOP_CLASS).scu(ds, 1):
            yield result[1]
    finally:
        ae.quit()

# Set up logging system for the whole package.  In each module, set
# logger=logging.getLogger('pynetdicom') and the same instance will be
# used by all At command line, turn on debugging for all pynetdicom
# functions with: import netdicom netdicom.debug(). Turn off debugging
# with netdicom.debug(False)
import logging

# pynetdicom defines a logger with a NullHandler only.
# Client code have the responsability to configure
# this logger.
logger = logging.getLogger('netdicom')
logger.addHandler(logging.NullHandler())

# helper functions to configure the logger. This should be
# called by the client code.


def logger_setup():
    logger = logging.getLogger('netdicom')
    handler = logging.StreamHandler()
    logger.setLevel(logging.WARNING)
    formatter = logging.Formatter("%(name)s %(message)s")
    handler.setFormatter(formatter)
    logger.addHandler(handler)
    # logging.getLogger('netdicom.FSM').setLevel(logging.CRITICAL)
    logging.getLogger('netdicom.DUL').setLevel(logging.CRITICAL)


def debug(debug_on=True):
    """Turn debugging of DICOM network operations on or off."""
    logger = logging.getLogger('netdicom')
    logger.setLevel(logging.DEBUG)
