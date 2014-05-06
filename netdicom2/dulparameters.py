# Copyright (c) 2014 Pavel 'Blane' Tuchin
# Copyright (c) 2012 Patrice Munger
# This file is part of pynetdicom, released under a modified MIT license.
#    See the file license.txt included with this distribution, also
#    available at http://pynetdicom.googlecode.com
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
