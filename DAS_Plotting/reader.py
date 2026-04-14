"""
Module for reading DAS data from HDF5 files
Date: 2026-04-13
"""

import h5py
import numpy as np
from typing import Tuple, Dict, Optional

class DASReader:
    """
    Class for reading DAS data from HDF5 files.

    Attributes
    ----------
    filepath : str
        Path to the HDF5 file
    fs : float
        Sampling frequency (PulseRate) in Hz
    dx : float
        Spatial sampling interval in meters
    num_locs : int
        Number of channels (loci)
    data : np.ndarray
        Raw DAS data (channels x time samples)
    """

    def __init__(self, filepath: str):
        """
        Initialize DASReader with filepath.

        Parameters
        ----------
        filepath : str
            Path to HDF5 file
        """
        self.filepath = filepath
        self.fs = None
        self.dx = None
        self.num_locs = None
        self.data = None
        self.metadata = {}

    def read_h5_file(self) -> Tuple[np.ndarray, float, float, int]:
        """
        Reads HDF5 file and extracts metadata and data.

        Returns
        -------
        X : np.ndarray
            DAS data array (channels x time samples)
        fs : float
            Sampling frequency in Hz
        dx : float
            Spatial sampling interval in meters
        num_locs : int
            Number of channels

        Raises
        ------
        RuntimeError
            If file cannot be read or required attributes are missing
        """
        print('Reading file metadata...')

        try:
            with h5py.File(self.filepath, 'r') as f:
                # Read metadata
                self.fs = f['/Acquisition'].attrs['PulseRate']
                self.dx = f['/Acquisition'].attrs['SpatialSamplingInterval']
                self.num_locs = f['/Acquisition'].attrs['NumberOfLoci']

                # Read main data - shape: (num_locs, num_tr) channels x time
                self.data = f['/Acquisition/Raw[0]/RawData'][:]
                self.data = self.data.astype(np.float64)

            print('Metadata read successfully:')
            print(f' -> fs = {self.fs:.1f} Hz')
            print(f' -> dx = {self.dx:.3f} m')
            print(f' -> num_locs = {self.num_locs} channels')

            return self.data, self.fs, self.dx, self.num_locs

        except KeyError as e:
            raise RuntimeError(f'Missing required dataset/attribute in HDF5 file: {str(e)}')
        except Exception as e:
            raise RuntimeError(f'Error reading the file: {str(e)}')

    def get_data_info(self) -> Dict:
        """Get basic information about the loaded data."""
        if self.data is None:
            return {'status': 'No data loaded'}

        return {
            'shape': self.data.shape,
            'dtype': str(self.data.dtype),
            'min_value': float(self.data.min()),
            'max_value': float(self.data.max()),
            'mean_value': float(self.data.mean()),
            'std_value': float(self.data.std()),
            'fs_hz': self.fs,
            'dx_m': self.dx,
            'duration_s': self.data.shape[1] / self.fs if self.fs else None,
            'length_m': self.data.shape[0] * self.dx if self.dx else None
        }


