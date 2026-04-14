"""
Module for DAS data preprocessing
Date: 2026-04-13
"""

import numpy as np
from scipy.signal import butter, sosfiltfilt

class DASPreprocessor:
    """
    Class for preprocessing DAS data.

    Methods include:
    - Temporal trimming
    - DC mean removal
    - Bandpass filtering
    """
    def __init__(self):
        self.processing_history = []
    def temporal_cut(self, X, t, t_start_cut, t_end_cut):
        print('Applying temporal cut...')
        t_original_end = t[-1]
        num_tr_original = X.shape[1]
        condition = (t >= t_start_cut) & (t <= t_end_cut)
        valid_indices = np.where(condition)[0]
        if len(valid_indices) == 0:
            print(f"Error: No data in range {t_start_cut}s to {t_end_cut}s")
            return X, t
        idx_start = valid_indices[0]
        idx_end = valid_indices[-1]
        X_cut = X[:, idx_start:idx_end + 1]
        t_cut = t[idx_start:idx_end + 1]

        print('Temporal cut completed.')
        print(f' -> Original time: {t[0]:.2f} s to {t_original_end:.2f} s ({num_tr_original} samples)')
        print(f' -> New time:      {t_cut[0]:.2f} s to {t_cut[-1]:.2f} s ({len(t_cut)} samples)')

        self.processing_history.append({
            'operation': 'temporal_cut',
            't_start': t_start_cut,
            't_end': t_end_cut,
            'original_shape': X.shape,
            'new_shape': X_cut.shape
        })

        return X_cut, t_cut
    def bandpass_filter(self, X, fs,
                        hp_cut, lp_cut,
                        order: int = 4):
        print(f'Applying band-pass filter from {hp_cut} to {lp_cut} Hz...')
        nyquist = fs / 2
        Wn = [hp_cut / nyquist, lp_cut / nyquist]
        sos = butter(order, Wn, btype='bandpass', output='sos')
        for channel_idx in range(X.shape[0]):
            X[channel_idx, :] = sosfiltfilt(sos, X[channel_idx, :])
        print('Filtering completed.')
        self.processing_history.append({
            'operation': 'bandpass_filter',
            'hp_cut': hp_cut,
            'lp_cut': lp_cut,
            'order': order
        })
        return X

    def process_full_pipeline(self, filePath, t_start_cut, t_end_cut,
                              hp_cut, lp_cut, remove_dc=True):
        from DAS_Plotting.reader import DASReader
        print("\n1. Reading Data...")
        try:
            reader = DASReader(filePath)
            X, fs, dx, num_locs = reader.read_h5_file()
        except Exception as e:
            raise RuntimeError(f"Error reading file: {e}")
        num_tr = X.shape[0]
        t = np.arange(num_tr) / fs
        y = np.arange(num_locs).reshape(-1, 1) * dx
        X = X.T

        print(f'Dimensional Matrix: {num_locs} Channels × {num_tr} Samples ({t[-1]:.2f} Seconds)')
        print(f'After transpose: {X.shape} (time × channels)')

        try:
            X, t = self.temporal_cut(X, t, t_start_cut, t_end_cut)
            num_locs, num_tr = X.shape
        except ValueError as e:
            print(f"Error en recorte temporal: {e}")
            print("Usando rango completo de datos")

        if remove_dc:
            print('Removing DC mean from each channel...')
            X = X - np.mean(X, axis=1, keepdims=True)
        try:
            X = self.bandpass_filter(X, fs, hp_cut, lp_cut)
        except ValueError as e:
            print(f"Filter Error: {e}")
            print("Skip Filtering")

        print("Processing completed.")
        print(f"Shape of the data: {X.shape} (time × channels)")
        return X, t, y, fs, dx, num_locs