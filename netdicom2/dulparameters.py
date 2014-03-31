# DUL Service Parameters
# 3.8 Section 7


class ServiceParam(object):
    def __init__(self):
        pass

    def __repr__(self):
        return ''.join(['%s %s\n' % (str(k), str(v))
                        for k, v in self.__dict__.iteritems()
                        if not callable(v)])


class AAssociateServiceParameters(ServiceParam):

    def __init__(self):
        super(AAssociateServiceParameters, self).__init__()

        self.mode = 'normal'
        self.application_context_name = None                    # String
        self.calling_ae_title = None                            # String
        self.called_ae_title = None                             # String
        self.responding_ae_title = None                         # String
        self.user_information = None                            # List of raw strings
        self.result = None                                      # Int in (0,1,2)
        self.result_source = None                               # Int in (0,1,2)
        self.diagnostic = None                                  # Int
        self.calling_presentation_address = None                # String
        self.called_presentation_address = None                 # String
        self.responding_presentation_address = None             # String
        self.presentation_context_definition_list = []          # List of [ID, AbsName, [TrNames]]
        self.presentation_context_definition_result_list = []   # List of [ID, result, TrName]
        self.presentation_requirements = 'Presentation Kernel'
        self.session_requirements = ''


class AReleaseServiceParameters(object):

    def __init__(self):
        self.reason = None
        self.result = None   # Must be None for Request and Indication
                             # Must be "affirmative" for Response and
                             # Confirmation


class AAbortServiceParameters(object):
    def __init__(self):
        self.abort_source = None
        self.user_information = None


class APAbortServiceParameters(object):
    def __init__(self):
        self.provider_reason = None


class PDataServiceParameters(object):
    def __init__(self):
        # should be of the form [ [ID, pdv], [ID, pdv] ... ]
        self.presentation_data_value_list = None


A_ASSOCIATE_ResultValues = (
    'accepted',
    'rejected (permanent)',
    'rejected (transient)')
A_ASSOCIATE_ResultSourceValues = (
    'UL service-user',
    'UL service provider (ACSE)',
    'UL service provider (Presentation)')
A_ASSOCIATE_DiagnosticValues = (
    # if result_source == 0
    ('no-reason given', 'application-context-name not supported',
     'calling-AE-title not recognized',
     'called-AE-title not recognized',
     'calling-AE-qualifier not recognized',
     'calling-AP-invocation-identifier not recognized',
     'calling-AE-invocation-identifier not recognized',
     'called-AE-qualifier not recognized',
     'called-AP-invocation-identifier not recognized',
     'called-AE-invocation-identifier not recognized'),
    # if reseult_source == 1
    ('no-reason-given',
     'no-common-UL version'),
    # if result_source == 2
    ('no-reason-given',
     'temporary-congestion',
     'local-limit-exceeded',
     'called-(Presentation)-address-unknown',
     'Presentation-protocol version not supported',
     'no-(Presentation) Service Access Point (SAP) available'))
