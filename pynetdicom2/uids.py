# Copyright (c) 2021 Pavel 'Blane' Tuchin
# This file is part of pynetdicom2, released under a modified MIT license.
#    See the file license.txt included with this distribution.
"""
This module provides some useful constants for SOP Class UIDs and
Transfer Syntax UIDs.
Storage-related SOP Classes are grouped under STORAGE_SOP_CLASSES
constant.
"""
__author__ = 'Blane'

from pydicom import uid

# Transfer syntax

# pylint: disable=line-too-long
#: Deflated Explicit VR Little Endian
DEFLATED_EXPLICIT_VR_LITTLE_ENDIAN = uid.DeflatedExplicitVRLittleEndian
#: JPEG Baseline (Process 1)
JPEG_BASELINE_PROCESS_1 = uid.JPEGBaseline8Bit
#: JPEG Extended (Process 2 and 4)
JPEG_EXTENDED_PROCESS_2_AND_4 = uid.JPEGExtended12Bit
#: JPEG Lossless, Non-Hierarchical (Process 14)
JPEG_LOSSLESS_NON_HIERARCHICAL_PROCESS_14 = uid.UID('1.2.840.10008.1.2.4.57')

JPEG_LOSSLESS_NON_HIERARCHICAL_FIRST_ORDER_PREDICTION_PROCESS_14_SELECTION_VALUE_1 = uid.JPEGLosslessSV1  # noqa: E501
"""
JPEG Lossless, Non-Hierarchical, First-Order Prediction (Process 14
[Selection Value 1]).
"""

#: JPEG-LS Lossless Image Compression
JPEG_LS_LOSSLESS_IMAGE_COMPRESSION = uid.JPEGLSLossless
#: JPEG-LS Lossy (Near-Lossless) Image Compression
JPEG_LS_LOSSY_NEAR_LOSSLESS_IMAGE_COMPRESSION = uid.JPEGLSNearLossless
#: JPEG 2000 Image Compression (Lossless Only)
JPEG_2000_IMAGE_COMPRESSION_LOSSLESS_ONLY = uid.JPEG2000Lossless
#: JPEG 2000 Image Compression
JPEG_2000_IMAGE_COMPRESSION = uid.JPEG2000
#: JPEG 2000 Part 2 Multi-component Image Compression (Lossless Only)
JPEG_2000_PART_2_MULTI_COMPONENT_IMAGE_COMPRESSION_LOSSLESS_ONLY = uid.JPEG2000MCLossless  # noqa: E501
#: JPEG 2000 Part 2 Multi-component Image Compression
JPEG_2000_PART_2_MULTI_COMPONENT_IMAGE_COMPRESSION = uid.JPEG2000MC
#: JPIP Referenced
JPIP_REFERENCED = uid.UID('1.2.840.10008.1.2.4.94')
#: JPIP Referenced Deflate
JPIP_REFERENCED_DEFLATE = uid.UID('1.2.840.10008.1.2.4.95')
#: MPEG2 Main Profile / Main Level
MPEG2_MAIN_PROFILE_MAIN_LEVEL = uid.MPEG2MPML
#: MPEG2 Main Profile / High Level
MPEG2_MAIN_PROFILE_HIGH_LEVEL = uid.MPEG2MPHL
#: MPEG-4 AVC/H.264 High Profile / Level 4.1
MPEG_4_AVC_H_264_HIGH_PROFILE_LEVEL_4_1 = uid.MPEG4HP41
#: MPEG-4 AVC/H.264 BD-compatible High Profile / Level 4.1
MPEG_4_AVC_H_264_BD_COMPATIBLE_HIGH_PROFILE_LEVEL_4_1 = uid.MPEG4HP41BD
#: MPEG-4 AVC/H.264 High Profile / Level 4.2 For 2D Video
MPEG_4_AVC_H_264_HIGH_PROFILE_LEVEL_4_2_FOR_2D_VIDEO = uid.MPEG4HP422D
#: MPEG-4 AVC/H.264 High Profile / Level 4.2 For 3D Video
MPEG_4_AVC_H_264_HIGH_PROFILE_LEVEL_4_2_FOR_3D_VIDEO = uid.MPEG4HP423D
#: MPEG-4 AVC/H.264 Stereo High Profile / Level 4.2
MPEG_4_AVC_H_264_STEREO_HIGH_PROFILE_LEVEL_4_2 = uid.MPEG4HP42STEREO
#: HEVC/H.265 Main Profile / Level 5.1
HEVC_H_265_MAIN_PROFILE_LEVEL_5_1 = uid.HEVCMP51
#: HEVC/H.265 Main 10 Profile / Level 5.1
HEVC_H_265_MAIN_10_PROFILE_LEVEL_5_1 = uid.HEVCM10P51
#: RLE Lossless
RLE_LOSSLESS = uid.RLELossless
#: RFC 2557 MIME encapsulation
RFC_2557_MIME_ENCAPSULATION = uid.UID('1.2.840.10008.1.2.6.1')
#: XML Encoding
XML_ENCODING = uid.UID('1.2.840.10008.1.2.6.2')


#: Every available transfer syntax that can encode a DICOM Data Set.
#:
#: Excludes pseudo transfer syntaxes such as RFC 2557 MIME encapsulation and
#: XML encoding, which do not encode Data Sets and so are not valid for
#: negotiation on storage presentation contexts. Tuples are used so the
#: collections cannot be modified by accident.
ALL_TS = (
    uid.ExplicitVRLittleEndian,
    uid.ImplicitVRLittleEndian,
    uid.ExplicitVRBigEndian,
    DEFLATED_EXPLICIT_VR_LITTLE_ENDIAN,
    JPEG_BASELINE_PROCESS_1,
    JPEG_EXTENDED_PROCESS_2_AND_4,
    JPEG_LOSSLESS_NON_HIERARCHICAL_PROCESS_14,
    JPEG_LOSSLESS_NON_HIERARCHICAL_FIRST_ORDER_PREDICTION_PROCESS_14_SELECTION_VALUE_1,  # noqa: E501
    JPEG_LS_LOSSLESS_IMAGE_COMPRESSION,
    JPEG_LS_LOSSY_NEAR_LOSSLESS_IMAGE_COMPRESSION,
    JPEG_2000_IMAGE_COMPRESSION_LOSSLESS_ONLY,
    JPEG_2000_IMAGE_COMPRESSION,
    JPEG_2000_PART_2_MULTI_COMPONENT_IMAGE_COMPRESSION_LOSSLESS_ONLY,
    JPEG_2000_PART_2_MULTI_COMPONENT_IMAGE_COMPRESSION,
    JPIP_REFERENCED,
    JPIP_REFERENCED_DEFLATE,
    MPEG2_MAIN_PROFILE_MAIN_LEVEL,
    MPEG2_MAIN_PROFILE_HIGH_LEVEL,
    MPEG_4_AVC_H_264_HIGH_PROFILE_LEVEL_4_1,
    MPEG_4_AVC_H_264_BD_COMPATIBLE_HIGH_PROFILE_LEVEL_4_1,
    MPEG_4_AVC_H_264_HIGH_PROFILE_LEVEL_4_2_FOR_2D_VIDEO,
    MPEG_4_AVC_H_264_HIGH_PROFILE_LEVEL_4_2_FOR_3D_VIDEO,
    MPEG_4_AVC_H_264_STEREO_HIGH_PROFILE_LEVEL_4_2,
    HEVC_H_265_MAIN_PROFILE_LEVEL_5_1,
    HEVC_H_265_MAIN_10_PROFILE_LEVEL_5_1,
    RLE_LOSSLESS,
)


# VERIFICATION SOP CLASSES
#: Verification SOP Class
VERIFICATION_SOP_CLASS = uid.UID('1.2.840.10008.1.1')

# STORAGE SOP CLASSES

#: Computed Radiography Image Storage
CR_IMAGE_STORAGE = uid.ComputedRadiographyImageStorage
#: Digital X-Ray Image Storage - For Presentation
DX_IMAGE_STORAGE_FOR_PRESENTATION = uid.DigitalXRayImageStorageForPresentation
#: Digital X-Ray Image Storage - For Processing
DX_IMAGE_STORAGE_FOR_PROCESSING = uid.DigitalXRayImageStorageForProcessing
#: Digital Mammography X-Ray Image Storage - For Presentation
MG_IMAGE_STORAGE_FOR_PRESENTATION = uid.DigitalMammographyXRayImageStorageForPresentation  # noqa: E501
#: Digital Mammography X-Ray Image Storage - For Processing
MG_IMAGE_STORAGE_FOR_PROCESSING = uid.DigitalMammographyXRayImageStorageForProcessing  # noqa: E501
#: Digital Intra-Oral X-Ray Image Storage - For Presentation
IO_IMAGE_STORAGE_FOR_PRESENTATION = uid.DigitalIntraOralXRayImageStorageForPresentation  # noqa: E501
#: Digital Intra-Oral X-Ray Image Storage - For Processing
IO_IMAGE_STORAGE_FOR_PROCESSING = uid.DigitalIntraOralXRayImageStorageForProcessing  # noqa: E501
#: CT Image Storage
CT_IMAGE_STORAGE = uid.CTImageStorage
#: Enhanced CT Image Storage
ENHANCED_CT_IMAGE_STORAGE = uid.EnhancedCTImageStorage
#: Legacy Converted Enhanced CT Image Storage
LEGACY_ENHANCED_CT_IMAGE_STORAGE = uid.LegacyConvertedEnhancedCTImageStorage
#: Ultrasound Multi-frame Image Storage
ULTRASOUND_MULTI_FRAME_IMAGE = uid.UltrasoundMultiFrameImageStorage
#: MR Image Storage
MR_IMAGE_STORAGE = uid.MRImageStorage
#: Enhanced MR Image Storage
ENHANCED_MR_IMAGE = uid.EnhancedMRImageStorage
#: MR Spectroscopy Storage
MR_SPECTROSCOPY_STORAGE = uid.MRSpectroscopyStorage
#: Enhanced MR Color Image Storage
ENHANCED_MR_COLOR_IMAGE_STORAGE = uid.EnhancedMRColorImageStorage
#: Legacy Converted Enhanced MR Image Storage
LEGACY_CONVERTED_ENHANCED_MR_IMAGE_STORAGE = uid.LegacyConvertedEnhancedMRImageStorage  # noqa: E501
#: Ultrasound Image Storage
ULTRASOUND_IMAGE_STORAGE = uid.UltrasoundImageStorage
#: Enhanced US Volume Storage
ENHANCED_US_VOLUME_STORAGE = uid.EnhancedUSVolumeStorage
#: Secondary Capture Image Storage
SC_IMAGE_STORAGE = uid.SecondaryCaptureImageStorage
#: Multi-frame Single Bit Secondary Capture Image Storage
MULTI_FRAME_SINGLE_BIT_SC_IMAGE_STORAGE = uid.MultiFrameSingleBitSecondaryCaptureImageStorage  # noqa: E501
#: Multi-frame Grayscale Byte Secondary Capture Image Storage
MULTI_FRAME_GRAYSCALE_BYTE_SC_IMAGE_STORAGE = uid.MultiFrameGrayscaleByteSecondaryCaptureImageStorage  # noqa: E501
#: Multi-frame Grayscale Word Secondary Capture Image Storage
MULTI_FRAME_GRAYSCALE_WORD_SC_IMAGE_STORAGE = uid.MultiFrameGrayscaleWordSecondaryCaptureImageStorage  # noqa: E501
#: Multi-frame True Color Secondary Capture Image Storage
MULTI_FRAME_TRUE_COLOR_SC_IMAGE_STORAGE = uid.MultiFrameTrueColorSecondaryCaptureImageStorage  # noqa: E501
#: 12-lead ECG Waveform Storage
TWELVE_LEAD_ECG_WAVEFORM_STORAGE = uid.TwelveLeadECGWaveformStorage
#: General ECG Waveform Storage
GENERAL_ECG_WAVEFORM_STORAGE = uid.GeneralECGWaveformStorage
#: Ambulatory ECG Waveform Storage
AMBULATORY_ECG_WAVEFORM_STORAGE = uid.AmbulatoryECGWaveformStorage
#: Hemodynamic Waveform Storage
HEMODYNAMIC_WAVEFORM_STORAGE = uid.HemodynamicWaveformStorage
#: Cardiac Electrophysiology Waveform Storage
CARDIAC_ELECTROPHYSIOLOGY_WAVEFORM_STORAGE = uid.CardiacElectrophysiologyWaveformStorage  # noqa: E501
#: Basic Voice Audio Waveform Storage
BASIC_VOICE_AUDIO_WAVEFORM_STORAGE = uid.BasicVoiceAudioWaveformStorage
#: General Audio Waveform Storage
GENERAL_AUDIO_WAVEFORM_STORAGE = uid.GeneralAudioWaveformStorage
#: Arterial Pulse Waveform Storage
ARTERIAL_PULSE_WAVEFORM_STORAGE = uid.ArterialPulseWaveformStorage
#: Respiratory Waveform Storage
RESPIRATORY_WAVEFORM_STORAGE = uid.RespiratoryWaveformStorage
#: Grayscale Softcopy Presentation State Storage
GRAYSCALE_SOFTCOPY_PRESENTATION_STATE_STORAGE = uid.GrayscaleSoftcopyPresentationStateStorage  # noqa: E501
#: Color Softcopy Presentation State Storage
COLOR_SOFTCOPY_PRESENTATION_STATE_STORAGE = uid.ColorSoftcopyPresentationStateStorage  # noqa: E501
#: Pseudo-Color Softcopy Presentation State Storage
PSEUDO_COLOR_SOFTCOPY_PRESENTATION_STATE_STORAGE = uid.PseudoColorSoftcopyPresentationStateStorage  # noqa: E501
#: Blending Softcopy Presentation State Storage
BLENDING_SOFTCOPY_PRESENTATION_STATE_STORAGE = uid.BlendingSoftcopyPresentationStateStorage  # noqa: E501
#: XA/XRF Grayscale Softcopy Presentation State Storage
XA_XRF_GRAYSCALE_SOFTCOPY_PRESENTATION_STATE_STORAGE = uid.XAXRFGrayscaleSoftcopyPresentationStateStorage  # noqa: E501
#: Grayscale Planar MPR Volumetric Presentation State Storage
GRAYSCALE_PLANAR_MPR_VOLUMETRIC_PRESENTATION_STATE_STORAGE = uid.GrayscalePlanarMPRVolumetricPresentationStateStorage  # noqa: E501
#: Compositing Planar MPR Volumetric Presentation State Storage
COMPOSITING_PLANAR_MPR_VOLUMETRIC_PRESENTATION_STATE_STORAGE = uid.CompositingPlanarMPRVolumetricPresentationStateStorage  # noqa: E501
#: Advanced Blending Presentation State Storage
ADVANCED_BLENDING_PRESENTATION_STATE_STORAGE = uid.AdvancedBlendingPresentationStateStorage  # noqa: E501
#: Volume Rendering Volumetric Presentation State Storage
VOLUME_RENDERING_VOLUMETRIC_PRESENTATION_STATE_STORAGE = uid.VolumeRenderingVolumetricPresentationStateStorage  # noqa: E501
#: Segmented Volume Rendering Volumetric Presentation State Storage
SEGMENTED_VOLUME_RENDERING_VOLUMETRIC_PRESENTATION_STATE_STORAGE = uid.SegmentedVolumeRenderingVolumetricPresentationStateStorage  # noqa: E501
#: Multiple Volume Rendering Volumetric Presentation State Storage
MULTIPLE_VOLUME_RENDERING_VOLUMETRIC_PRESENTATION_STATE_STORAGE = uid.MultipleVolumeRenderingVolumetricPresentationStateStorage  # noqa: E501
#: X-Ray Angiographic Image Storage
XA_IMAGE_STORAGE = uid.XRayAngiographicImageStorage
#: Enhanced XA Image Storage
ENHANCED_XA_IMAGE_STORAGE = uid.EnhancedXAImageStorage
#: X-Ray Radiofluoroscopic Image Storage
RF_IMAGE_STORAGE = uid.XRayRadiofluoroscopicImageStorage
#: Enhanced XRF Image Storage
ENHANCED_RF_IMAGE_STORAGE = uid.EnhancedXRFImageStorage
#: X-Ray 3D Angiographic Image Storage
X_RAY_3D_ANGIOGRAPHIC_IMAGE_STORAGE = uid.XRay3DAngiographicImageStorage
#: X-Ray 3D Craniofacial Image Storage
X_RAY_3D_CRANIOFACIAL_IMAGE_STORAGE = uid.XRay3DCraniofacialImageStorage
#: Breast Tomosynthesis Image Storage
BREAST_TOMOSYNTHESIS_IMAGE_STORAGE = uid.BreastTomosynthesisImageStorage
#: Breast Projection X-Ray Image Storage - For Presentation
BREAST_PROJECTION_X_RAY_IMAGE_STORAGE_FOR_PRESENTATION = uid.BreastProjectionXRayImageStorageForPresentation  # noqa: E501
#: Breast Projection X-Ray Image Storage - For Processing
BREAST_PROJECTION_X_RAY_IMAGE_STORAGE_FOR_PROCESSING = uid.BreastProjectionXRayImageStorageForProcessing  # noqa: E501
#: Intravascular Optical Coherence Tomography Image Storage - For Presentation
INTRAVASCULAR_OPTICAL_COHERENCE_TOMOGRAPHY_IMAGE_STORAGE_FOR_PRESENTATION = uid.IntravascularOpticalCoherenceTomographyImageStorageForPresentation  # noqa: E501
#: Intravascular Optical Coherence Tomography Image Storage - For Processing
INTRAVASCULAR_OPTICAL_COHERENCE_TOMOGRAPHY_IMAGE_STORAGE_FOR_PROCESSING = uid.IntravascularOpticalCoherenceTomographyImageStorageForProcessing  # noqa: E501
#: Nuclear Medicine Image Storage
NM_IMAGE_STORAGE = uid.NuclearMedicineImageStorage
#: Parametric Map Storage
PARAMETRIC_MAP_STORAGE = uid.ParametricMapStorage
#: Raw Data Storage
RAW_DATA_STORAGE = uid.RawDataStorage
#: Spatial Registration Storage
SPATIAL_REGISTRATION = uid.SpatialRegistrationStorage
#: Spatial Fiducials Storage
SPATIAL_FIDUCIALS_STORAGE = uid.SpatialFiducialsStorage
#: Deformable Spatial Registration Storage
DEFORMABLE_SPATIAL_REGISTRATION_STORAGE = uid.DeformableSpatialRegistrationStorage  # noqa: E501
#: Segmentation Storage
SEGMENTATION_STORAGE = uid.SegmentationStorage
#: Surface Segmentation Storage
SURFACE_SEGMENTATION_STORAGE = uid.SurfaceSegmentationStorage
#: Tractography Results Storage
TRACTOGRAPHY_RESULTS_STORAGE = uid.TractographyResultsStorage
#: Real World Value Mapping Storage
REAL_WORLD_VALUE_MAPPING_STORAGE = uid.RealWorldValueMappingStorage
#: Surface Scan Mesh Storage
SURFACE_SCAN_MESH_STORAGE = uid.SurfaceScanMeshStorage
#: Surface Scan Point Cloud Storage
SURFACE_SCAN_POINT_CLOUD_STORAGE = uid.SurfaceScanPointCloudStorage
#: VL Endoscopic Image Storage
VL_ENDOSCOPIC_IMAGE_STORAGE = uid.VLEndoscopicImageStorage
#: Video Endoscopic Image Storage
VIDEO_ENDOSCOPIC_IMAGE_STORAGE = uid.VideoEndoscopicImageStorage
#: VL Microscopic Image Storage
VL_MICROSCOPIC_IMAGE_STORAGE = uid.VLMicroscopicImageStorage
#: Video Microscopic Image Storage
VIDEO_MICROSCOPIC_IMAGE_STORAGE = uid.VideoMicroscopicImageStorage
#: VL Slide-Coordinates Microscopic Image Storage
VL_SLIDE_COORDINATES_MICROSCOPIC_IMAGE_STORAGE = uid.VLSlideCoordinatesMicroscopicImageStorage  # noqa: E501
#: VL Photographic Image Storage
VL_PHOTOGRAPHIC_IMAGE_STORAGE = uid.VLPhotographicImageStorage
#: Video Photographic Image Storage
VIDEO_PHOTOGRAPHIC_IMAGE_STORAGE = uid.VideoPhotographicImageStorage
#: Ophthalmic Photography 8 Bit Image Storage
OPHTHALMIC_PHOTOGRAPHY_8_BIT_IMAGE_STORAGE = uid.OphthalmicPhotography8BitImageStorage  # noqa: E501
#: Ophthalmic Photography 16 Bit Image Storage
OPHTHALMIC_PHOTOGRAPHY_16_BIT_IMAGE_STORAGE = uid.OphthalmicPhotography16BitImageStorage  # noqa: E501
#: Stereometric Relationship Storage
STEREOMETRIC_RELATIONSHIP_STORAGE = uid.StereometricRelationshipStorage
#: Ophthalmic Tomography Image Storage
OPHTHALMIC_TOMOGRAPHY_IMAGE_STORAGE = uid.OphthalmicTomographyImageStorage
#: Wide Field Ophthalmic Photography Stereographic Projection Image Storage
WIDE_FIELD_OPHTHALMIC_PHOTOGRAPHY_STEREOGRAPHIC_PROJECTION_IMAGE_STORAGE = uid.WideFieldOphthalmicPhotographyStereographicProjectionImageStorage  # noqa: E501
#: Wide Field Ophthalmic Photography 3D Coordinates Image Storage
WIDE_FIELD_OPHTHALMIC_PHOTOGRAPHY_3D_COORDINATES_IMAGE_STORAGE = uid.WideFieldOphthalmicPhotography3DCoordinatesImageStorage  # noqa: E501
#: Ophthalmic Optical Coherence Tomography En Face Image Storage
OPHTHALMIC_OPTICAL_COHERENCE_TOMOGRAPHY_EN_FACE_IMAGE_STORAGE = uid.OphthalmicOpticalCoherenceTomographyEnFaceImageStorage  # noqa: E501
#: Ophthalmic Optical Coherence Tomography B-scan Volume Analysis Storage
OPHTHALMIC_OPTICAL_COHERENCE_TOMOGRAPHY_B_SCAN_VOLUME_ANALYSIS_STORAGE = uid.OphthalmicOpticalCoherenceTomographyBscanVolumeAnalysisStorage  # noqa: E501
#: VL Whole Slide Microscopy Image Storage
VL_WHOLE_SLIDE_MICROSCOPY_IMAGE_STORAGE = uid.VLWholeSlideMicroscopyImageStorage  # noqa: E501
#: Lensometry Measurements Storage
LENSOMETRY_MEASUREMENTS_STORAGE = uid.LensometryMeasurementsStorage
#: Autorefraction Measurements Storage
AUTOREFRACTION_MEASUREMENTS_STORAGE = uid.AutorefractionMeasurementsStorage
#: Keratometry Measurements Storage
KERATOMETRY_MEASUREMENTS_STORAGE = uid.KeratometryMeasurementsStorage
#: Subjective Refraction Measurements Storage
SUBJECTIVE_REFRACTION_MEASUREMENTS_STORAGE = uid.SubjectiveRefractionMeasurementsStorage  # noqa: E501
#: Visual Acuity Measurements Storage
VISUAL_ACUITY_MEASUREMENTS_STORAGE = uid.VisualAcuityMeasurementsStorage
#: Spectacle Prescription Report Storage
SPECTACLE_PRESCRIPTION_REPORT_STORAGE = uid.SpectaclePrescriptionReportStorage
#: Ophthalmic Axial Measurements Storage
OPHTHALMIC_AXIAL_MEASUREMENTS_STORAGE = uid.OphthalmicAxialMeasurementsStorage
#: Intraocular Lens Calculations Storage
INTRAOCULAR_LENS_CALCULATIONS_STORAGE = uid.IntraocularLensCalculationsStorage
#: Macular Grid Thickness and Volume Report Storage
MACULAR_GRID_THICKNESS_AND_VOLUME_REPORT_STORAGE = uid.MacularGridThicknessAndVolumeReportStorage  # noqa: E501
#: Ophthalmic Visual Field Static Perimetry Measurements Storage
OPHTHALMIC_VISUAL_FIELD_STATIC_PERIMETRY_MEASUREMENTS_STORAGE = uid.OphthalmicVisualFieldStaticPerimetryMeasurementsStorage  # noqa: E501
#: Ophthalmic Thickness Map Storage
OPHTHALMIC_THICKNESS_MAP_STORAGE = uid.OphthalmicThicknessMapStorage
#: Corneal Topography Map Storage
CORNEAL_TOPOGRAPHY_MAP_STORAGE = uid.CornealTopographyMapStorage
#: Basic Text SR Storage
BASIC_TEXT_SR_STORAGE = uid.BasicTextSRStorage
#: Enhanced SR Storage
ENHANCED_SR_STORAGE = uid.EnhancedSRStorage
#: Comprehensive SR Storage
COMPREHENSIVE_SR_STORAGE = uid.ComprehensiveSRStorage
#: Comprehensive 3D SR Storage
COMPREHENSIVE_3D_SR_STORAGE = uid.Comprehensive3DSRStorage
#: Extensible SR Storage
EXTENSIBLE_SR_STORAGE = uid.ExtensibleSRStorage
#: Procedure Log Storage
PROCEDURE_LOG_STORAGE = uid.ProcedureLogStorage
#: Mammography CAD SR Storage
MAMMOGRAPHY_CAD_SR_STORAGE = uid.MammographyCADSRStorage
#: Key Object Selection Document Storage
KEY_OBJECT_SELECTION_DOCUMENT_STORAGE = uid.KeyObjectSelectionDocumentStorage
#: Chest CAD SR Storage
CHEST_CAD_SR_STORAGE = uid.ChestCADSRStorage
#: X-Ray Radiation Dose SR Storage
XRAY_RADIATION_DOSE_SR_STORAGE = uid.XRayRadiationDoseSRStorage
#: Radiopharmaceutical Radiation Dose SR Storage
RADIOPHARMACEUTICAL_RADIATION_DOSE_SR_STORAGE = uid.RadiopharmaceuticalRadiationDoseSRStorage  # noqa: E501
#: Colon CAD SR Storage
COLON_CAD_SR_STORAGE = uid.ColonCADSRStorage
#: Implantation Plan SR Storage
IMPLANTATION_PLAN_SR_STORAGE = uid.ImplantationPlanSRStorage
#: Acquisition Context SR Storage
ACQUISITION_CONTEXT_SR_STORAGE = uid.AcquisitionContextSRStorage
#: Simplified Adult Echo SR Storage
SIMPLIFIED_ADULT_ECHO_SR_STORAGE = uid.SimplifiedAdultEchoSRStorage
#: Patient Radiation Dose SR Storage
PATIENT_RADIATION_DOSE_SR_STORAGE = uid.PatientRadiationDoseSRStorage
#: Content Assessment Results Storage
CONTENT_ASSESSMENT_RESULTS_STORAGE = uid.ContentAssessmentResultsStorage
#: Encapsulated PDF Storage
ENCAPSULATED_PDF_STORAGE = uid.EncapsulatedPDFStorage
#: Encapsulated CDA Storage
ENCAPSULATED_CDA_STORAGE = uid.EncapsulatedCDAStorage
#: Positron Emission Tomography Image Storage
PET_IMAGE_STORAGE = uid.PositronEmissionTomographyImageStorage
#: Legacy Converted Enhanced PET Image Storage
LEGACY_CONVERTED_ENHANCED_PET_IMAGE_STORAGE = uid.LegacyConvertedEnhancedPETImageStorage  # noqa: E501
#: Standalone PET Curve Storage
STANDALONE_PET_CURVE_STORAGE = uid.UID('1.2.840.10008.5.1.4.1.1.129')
#: Enhanced PET Image Storage
ENHANCED_PET_IMAGE_STORAGE = uid.EnhancedPETImageStorage
#: Basic Structured Display Storage
BASIC_STRUCTURED_DISPLAY_STORAGE = uid.BasicStructuredDisplayStorage
#: CT Defined Procedure Protocol Storage
CT_DEFINED_PROCEDURE_PROTOCOL_STORAGE = uid.CTDefinedProcedureProtocolStorage
#: CT Performed Procedure Protocol Storage
CT_PERFORMED_PROCEDURE_PROTOCOL_STORAGE = uid.CTPerformedProcedureProtocolStorage  # noqa: E501
#: Protocol Approval Storage
PROTOCOL_APPROVAL_STORAGE = uid.ProtocolApprovalStorage
#: RT Image Storage
RT_IMAGE_STORAGE = uid.RTImageStorage
#: RT Dose Storage
RT_DOSE_STORAGE = uid.RTDoseStorage
#: RT Structure Set Storage
RT_STRUCTURE_SET_STORAGE = uid.RTStructureSetStorage
#: RT Beams Treatment Record Storage
RT_BEAMS_TREATMENT_RECORD_STORAGE = uid.RTBeamsTreatmentRecordStorage
#: RT Plan Storage
RT_PLAN_STORAGE = uid.RTPlanStorage
#: RT Brachy Treatment Record Storage
RT_BRACHY_TREATMENT_RECORD_STORAGE = uid.RTBrachyTreatmentRecordStorage
#: RT Treatment Summary Record Storage
RT_TREATMENT_SUMMARY_RECORD_STORAGE = uid.RTTreatmentSummaryRecordStorage
#: RT Ion Plan Storage
RT_ION_PLAN_STORAGE = uid.RTIonPlanStorage
#: RT Ion Beams Treatment Record Storage
RT_ION_BEAMS_TREATMENT_RECORD_STORAGE = uid.RTIonBeamsTreatmentRecordStorage
#: DICOS CT Image Storage
DICOS_CT_IMAGE_STORAGE = uid.DICOSCTImageStorage
#: DICOS Digital X-Ray Image Storage - For Presentation
DICOS_DIGITAL_X_RAY_IMAGE_STORAGE_FOR_PRESENTATION = uid.DICOSDigitalXRayImageStorageForPresentation  # noqa: E501
#: DICOS Digital X-Ray Image Storage - For Processing
DICOS_DIGITAL_X_RAY_IMAGE_STORAGE_FOR_PROCESSING = uid.DICOSDigitalXRayImageStorageForProcessing  # noqa: E501
#: DICOS Threat Detection Report Storage
DICOS_THREAT_DETECTION_REPORT_STORAGE = uid.DICOSThreatDetectionReportStorage
#: DICOS 2D AIT Storage
DICOS_2D_AIT_STORAGE = uid.DICOS2DAITStorage
#: DICOS 3D AIT Storage
DICOS_3D_AIT_STORAGE = uid.DICOS3DAITStorage
#: DICOS Quadrupole Resonance (QR) Storage
DICOS_QR_STORAGE = uid.DICOSQuadrupoleResonanceStorage
#: Eddy Current Image Storage
EDDY_CURRENT_IMAGE_STORAGE = uid.EddyCurrentImageStorage
#: Eddy Current Multi-frame Image Storage
EDDY_CURRENT_MULTI_FRAME_IMAGE_STORAGE = uid.EddyCurrentMultiFrameImageStorage
# pylint: enable=line-too-long


# QUERY RETRIEVE SOP Classes
PATIENT_ROOT_FIND_SOP_CLASS = uid.UID('1.2.840.10008.5.1.4.1.2.1.1')
PATIENT_ROOT_MOVE_SOP_CLASS = uid.UID('1.2.840.10008.5.1.4.1.2.1.2')
PATIENT_ROOT_GET_SOP_CLASS = uid.UID('1.2.840.10008.5.1.4.1.2.1.3')
STUDY_ROOT_FIND_SOP_CLASS = uid.UID('1.2.840.10008.5.1.4.1.2.2.1')
STUDY_ROOT_MOVE_SOP_CLASS = uid.UID('1.2.840.10008.5.1.4.1.2.2.2')
STUDY_ROOT_GET_SOP_CLASS = uid.UID('1.2.840.10008.5.1.4.1.2.2.3')
PATIENT_STUDY_ONLY_FIND_SOP_CLASS = uid.UID('1.2.840.10008.5.1.4.1.2.3.1')
PATIENT_STUDY_ONLY_MOVE_SOP_CLASS = uid.UID('1.2.840.10008.5.1.4.1.2.3.2')
PATIENT_STUDY_ONLY_GET_SOP_CLASS = uid.UID('1.2.840.10008.5.1.4.1.2.3.3')

MODALITY_WORK_LIST_INFORMATION_FIND_SOP_CLASS = uid.UID('1.2.840.10008.5.1.4.31')  # noqa: E501

STORAGE_COMMITMENT_SOP_CLASS = uid.UID('1.2.840.10008.1.20.1')

STORAGE_SOP_CLASSES = (
    CR_IMAGE_STORAGE,
    DX_IMAGE_STORAGE_FOR_PRESENTATION,
    DX_IMAGE_STORAGE_FOR_PROCESSING,
    MG_IMAGE_STORAGE_FOR_PRESENTATION,
    MG_IMAGE_STORAGE_FOR_PROCESSING,
    IO_IMAGE_STORAGE_FOR_PRESENTATION,
    IO_IMAGE_STORAGE_FOR_PROCESSING,
    CT_IMAGE_STORAGE,
    ENHANCED_CT_IMAGE_STORAGE,
    LEGACY_ENHANCED_CT_IMAGE_STORAGE,
    ULTRASOUND_MULTI_FRAME_IMAGE,
    MR_IMAGE_STORAGE,
    ENHANCED_MR_IMAGE,
    MR_SPECTROSCOPY_STORAGE,
    ENHANCED_MR_COLOR_IMAGE_STORAGE,
    LEGACY_CONVERTED_ENHANCED_MR_IMAGE_STORAGE,
    ULTRASOUND_IMAGE_STORAGE,
    ENHANCED_US_VOLUME_STORAGE,
    SC_IMAGE_STORAGE,
    MULTI_FRAME_SINGLE_BIT_SC_IMAGE_STORAGE,
    MULTI_FRAME_GRAYSCALE_BYTE_SC_IMAGE_STORAGE,
    MULTI_FRAME_GRAYSCALE_WORD_SC_IMAGE_STORAGE,
    MULTI_FRAME_TRUE_COLOR_SC_IMAGE_STORAGE,
    TWELVE_LEAD_ECG_WAVEFORM_STORAGE,
    GENERAL_ECG_WAVEFORM_STORAGE,
    AMBULATORY_ECG_WAVEFORM_STORAGE,
    HEMODYNAMIC_WAVEFORM_STORAGE,
    CARDIAC_ELECTROPHYSIOLOGY_WAVEFORM_STORAGE,
    BASIC_VOICE_AUDIO_WAVEFORM_STORAGE,
    GENERAL_AUDIO_WAVEFORM_STORAGE,
    ARTERIAL_PULSE_WAVEFORM_STORAGE,
    RESPIRATORY_WAVEFORM_STORAGE,
    GRAYSCALE_SOFTCOPY_PRESENTATION_STATE_STORAGE,
    COLOR_SOFTCOPY_PRESENTATION_STATE_STORAGE,
    PSEUDO_COLOR_SOFTCOPY_PRESENTATION_STATE_STORAGE,
    BLENDING_SOFTCOPY_PRESENTATION_STATE_STORAGE,
    XA_XRF_GRAYSCALE_SOFTCOPY_PRESENTATION_STATE_STORAGE,
    GRAYSCALE_PLANAR_MPR_VOLUMETRIC_PRESENTATION_STATE_STORAGE,
    COMPOSITING_PLANAR_MPR_VOLUMETRIC_PRESENTATION_STATE_STORAGE,
    ADVANCED_BLENDING_PRESENTATION_STATE_STORAGE,
    VOLUME_RENDERING_VOLUMETRIC_PRESENTATION_STATE_STORAGE,
    SEGMENTED_VOLUME_RENDERING_VOLUMETRIC_PRESENTATION_STATE_STORAGE,
    MULTIPLE_VOLUME_RENDERING_VOLUMETRIC_PRESENTATION_STATE_STORAGE,
    XA_IMAGE_STORAGE,
    ENHANCED_XA_IMAGE_STORAGE,
    RF_IMAGE_STORAGE,
    ENHANCED_RF_IMAGE_STORAGE,
    X_RAY_3D_ANGIOGRAPHIC_IMAGE_STORAGE,
    X_RAY_3D_CRANIOFACIAL_IMAGE_STORAGE,
    BREAST_TOMOSYNTHESIS_IMAGE_STORAGE,
    BREAST_PROJECTION_X_RAY_IMAGE_STORAGE_FOR_PRESENTATION,
    BREAST_PROJECTION_X_RAY_IMAGE_STORAGE_FOR_PROCESSING,
    INTRAVASCULAR_OPTICAL_COHERENCE_TOMOGRAPHY_IMAGE_STORAGE_FOR_PRESENTATION,
    INTRAVASCULAR_OPTICAL_COHERENCE_TOMOGRAPHY_IMAGE_STORAGE_FOR_PROCESSING,
    NM_IMAGE_STORAGE,
    PARAMETRIC_MAP_STORAGE,
    RAW_DATA_STORAGE,
    SPATIAL_REGISTRATION,
    SPATIAL_FIDUCIALS_STORAGE,
    DEFORMABLE_SPATIAL_REGISTRATION_STORAGE,
    SEGMENTATION_STORAGE,
    SURFACE_SEGMENTATION_STORAGE,
    TRACTOGRAPHY_RESULTS_STORAGE,
    REAL_WORLD_VALUE_MAPPING_STORAGE,
    SURFACE_SCAN_MESH_STORAGE,
    SURFACE_SCAN_POINT_CLOUD_STORAGE,
    VL_ENDOSCOPIC_IMAGE_STORAGE,
    VIDEO_ENDOSCOPIC_IMAGE_STORAGE,
    VL_MICROSCOPIC_IMAGE_STORAGE,
    VIDEO_MICROSCOPIC_IMAGE_STORAGE,
    VL_SLIDE_COORDINATES_MICROSCOPIC_IMAGE_STORAGE,
    VL_PHOTOGRAPHIC_IMAGE_STORAGE,
    VIDEO_PHOTOGRAPHIC_IMAGE_STORAGE,
    OPHTHALMIC_PHOTOGRAPHY_8_BIT_IMAGE_STORAGE,
    OPHTHALMIC_PHOTOGRAPHY_16_BIT_IMAGE_STORAGE,
    STEREOMETRIC_RELATIONSHIP_STORAGE,
    OPHTHALMIC_TOMOGRAPHY_IMAGE_STORAGE,
    WIDE_FIELD_OPHTHALMIC_PHOTOGRAPHY_STEREOGRAPHIC_PROJECTION_IMAGE_STORAGE,
    WIDE_FIELD_OPHTHALMIC_PHOTOGRAPHY_3D_COORDINATES_IMAGE_STORAGE,
    OPHTHALMIC_OPTICAL_COHERENCE_TOMOGRAPHY_EN_FACE_IMAGE_STORAGE,
    OPHTHALMIC_OPTICAL_COHERENCE_TOMOGRAPHY_B_SCAN_VOLUME_ANALYSIS_STORAGE,
    VL_WHOLE_SLIDE_MICROSCOPY_IMAGE_STORAGE,
    LENSOMETRY_MEASUREMENTS_STORAGE,
    AUTOREFRACTION_MEASUREMENTS_STORAGE,
    KERATOMETRY_MEASUREMENTS_STORAGE,
    SUBJECTIVE_REFRACTION_MEASUREMENTS_STORAGE,
    VISUAL_ACUITY_MEASUREMENTS_STORAGE,
    SPECTACLE_PRESCRIPTION_REPORT_STORAGE,
    OPHTHALMIC_AXIAL_MEASUREMENTS_STORAGE,
    INTRAOCULAR_LENS_CALCULATIONS_STORAGE,
    MACULAR_GRID_THICKNESS_AND_VOLUME_REPORT_STORAGE,
    OPHTHALMIC_VISUAL_FIELD_STATIC_PERIMETRY_MEASUREMENTS_STORAGE,
    OPHTHALMIC_THICKNESS_MAP_STORAGE,
    CORNEAL_TOPOGRAPHY_MAP_STORAGE,
    BASIC_TEXT_SR_STORAGE,
    ENHANCED_SR_STORAGE,
    COMPREHENSIVE_SR_STORAGE,
    COMPREHENSIVE_3D_SR_STORAGE,
    EXTENSIBLE_SR_STORAGE,
    PROCEDURE_LOG_STORAGE,
    MAMMOGRAPHY_CAD_SR_STORAGE,
    KEY_OBJECT_SELECTION_DOCUMENT_STORAGE,
    CHEST_CAD_SR_STORAGE,
    XRAY_RADIATION_DOSE_SR_STORAGE,
    RADIOPHARMACEUTICAL_RADIATION_DOSE_SR_STORAGE,
    COLON_CAD_SR_STORAGE,
    IMPLANTATION_PLAN_SR_STORAGE,
    ACQUISITION_CONTEXT_SR_STORAGE,
    SIMPLIFIED_ADULT_ECHO_SR_STORAGE,
    PATIENT_RADIATION_DOSE_SR_STORAGE,
    CONTENT_ASSESSMENT_RESULTS_STORAGE,
    ENCAPSULATED_PDF_STORAGE,
    ENCAPSULATED_CDA_STORAGE,
    PET_IMAGE_STORAGE,
    LEGACY_CONVERTED_ENHANCED_PET_IMAGE_STORAGE,
    STANDALONE_PET_CURVE_STORAGE,
    ENHANCED_PET_IMAGE_STORAGE,
    BASIC_STRUCTURED_DISPLAY_STORAGE,
    CT_DEFINED_PROCEDURE_PROTOCOL_STORAGE,
    CT_PERFORMED_PROCEDURE_PROTOCOL_STORAGE,
    PROTOCOL_APPROVAL_STORAGE,
    RT_IMAGE_STORAGE,
    RT_DOSE_STORAGE,
    RT_STRUCTURE_SET_STORAGE,
    RT_BEAMS_TREATMENT_RECORD_STORAGE,
    RT_PLAN_STORAGE,
    RT_BRACHY_TREATMENT_RECORD_STORAGE,
    RT_TREATMENT_SUMMARY_RECORD_STORAGE,
    RT_ION_PLAN_STORAGE,
    RT_ION_BEAMS_TREATMENT_RECORD_STORAGE,
    DICOS_CT_IMAGE_STORAGE,
    DICOS_DIGITAL_X_RAY_IMAGE_STORAGE_FOR_PRESENTATION,
    DICOS_DIGITAL_X_RAY_IMAGE_STORAGE_FOR_PROCESSING,
    DICOS_THREAT_DETECTION_REPORT_STORAGE,
    DICOS_2D_AIT_STORAGE,
    DICOS_3D_AIT_STORAGE,
    DICOS_QR_STORAGE,
    EDDY_CURRENT_IMAGE_STORAGE,
    EDDY_CURRENT_MULTI_FRAME_IMAGE_STORAGE
)
