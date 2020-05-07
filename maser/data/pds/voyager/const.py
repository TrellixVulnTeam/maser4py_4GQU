import numpy
from astropy.units import Unit

from .pra import PDSPPIVoyagerPRAHighRateDataTimeSeriesDataFromLabel, PDSPPIVoyagerPRARDRLowBand6SecDataFromLabel, \
    PDSPPIVoyagerPRARDRLowBand48SecDataFromLabel

__all__ = ['PDS_OBJECT_CLASSES', 'VOYAGER_PRA_FREQUENCY_LOWBAND']

PDS_OBJECT_CLASSES = {
    'VG1-J-PRA-3-RDR-LOWBAND-6SEC-V1.0': PDSPPIVoyagerPRARDRLowBand6SecDataFromLabel,
    'VG1-S-PRA-3-RDR-LOWBAND-6SEC-V1.0': PDSPPIVoyagerPRARDRLowBand6SecDataFromLabel,
    'VG2-J-PRA-3-RDR-LOWBAND-6SEC-V1.0': PDSPPIVoyagerPRARDRLowBand6SecDataFromLabel,
    'VG2-S-PRA-3-RDR-LOWBAND-6SEC-V1.0': PDSPPIVoyagerPRARDRLowBand6SecDataFromLabel,
    'VG2-N-PRA-3-RDR-LOWBAND-6SEC-V1.0': PDSPPIVoyagerPRARDRLowBand6SecDataFromLabel,
    'VG2-U-PRA-3-RDR-LOWBAND-6SEC-V1.0': PDSPPIVoyagerPRARDRLowBand6SecDataFromLabel,
    'VG1-J-PRA-4-SUMM-BROWSE-48SEC-V1.0': PDSPPIVoyagerPRARDRLowBand48SecDataFromLabel,
    'VG2-J-PRA-4-SUMM-BROWSE-48SEC-V1.0': PDSPPIVoyagerPRARDRLowBand48SecDataFromLabel,
    'VG2-N-PRA-4-SUMM-BROWSE-48SEC-V1.0': PDSPPIVoyagerPRARDRLowBand48SecDataFromLabel,
    'VG2-U-PRA-4-SUMM-BROWSE-48SEC-V1.0': PDSPPIVoyagerPRARDRLowBand48SecDataFromLabel,
    'VG2-N-PRA-2-RDR-HIGHRATE-60MS-V1.0': PDSPPIVoyagerPRAHighRateDataTimeSeriesDataFromLabel,
    'VG2-U-PRA-2-RDR-HIGHRATE-60MS-V1.0': PDSPPIVoyagerPRAHighRateDataTimeSeriesDataFromLabel,
}

VOYAGER_PRA_FREQUENCY_LOWBAND = numpy.arange(1326, -18, -19.2) * Unit('kHz')