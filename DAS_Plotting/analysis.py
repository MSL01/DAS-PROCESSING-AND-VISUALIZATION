"""
Module for DAS data analysis (spectrogram and FFT)
Date: 2026-04-13
"""

import numpy as np
import time
from scipy import signal
from scipy.fft import fft2, fftshift


def integrated_band_spectrogram(X, fs, freq_band, window_time=0.5, overlap_perc=0.75):
    """
    Computes a temporal PSD map integrated over a frequency band.

    Parameters
    ----------
    X : np.ndarray
        DAS data array (channels x time samples)
    fs : float
        Sampling frequency in Hz
    freq_band : list or tuple
        [low_freq, high_freq] frequency band in Hz
    window_time : float, default=0.5
        Window length in seconds
    overlap_perc : float, default=0.75
        Overlap percentage (0-1)

    Returns
    -------
    PSD_map_temporal : np.ndarray
        2D array of integrated band power (channels x time_windows)
    t_spec : np.ndarray
        Time vector for spectrogram
    """
    print('Computing spectrogram with integrated band...')

    if X.ndim == 1:
        X = X.reshape(1, -1)
    n_window = int(window_time * fs)
    n_overlap = int(overlap_perc * n_window)

    f_spec, t_spec, Sref = signal.spectrogram(X[0, :], fs=fs,
                                              window='hamming',
                                              nperseg=n_window,
                                              noverlap=n_overlap)
    num_time_windows = len(t_spec)
    num_locs = X.shape[0]
    PSD_map_temporal = np.zeros((num_locs, num_time_windows))
    t0 = time.time()
    for k in range(num_locs):
        f_spec, t_k, Sxx = signal.spectrogram(
            X[k, :],
            fs=fs,
            window='hamming',
            nperseg=n_window,
            noverlap=n_overlap)
        psd = np.abs(Sxx) ** 2 / (fs * np.sum(np.hamming(n_window) ** 2))
        idx_band = np.where((f_spec >= freq_band[0]) & (f_spec <= freq_band[1]))[0]
        if len(idx_band) > 0:
            band_power = np.trapezoid(psd[idx_band, :], f_spec[idx_band], axis=0)
            PSD_map_temporal[k, :] = band_power
    print(f'Computation completed in {time.time() - t0:.2f} seconds')
    return PSD_map_temporal, t_spec


def fft_2d_analysis(X_roi, fs, dx, scale_factor=0.02292):
    """
    Performs 2D FFT (k-f) analysis on a region of interest.

    Parameters
    ----------
    X_roi : np.ndarray
        ROI data array (channels x time samples)
    fs : float
        Sampling frequency in Hz
    dx : float
        Channel spacing in meters
    scale_factor : float, default=0.02292
        Scaling factor for wavenumber (1 inch = 0.02292? adjust as needed)

    Returns
    -------
    F_dB : np.ndarray
        2D FFT magnitude in dB (wavenumber x frequency)
    f_vec : np.ndarray
        Frequency vector in Hz
    k_vec_scaled : np.ndarray
        Wavenumber vector in cycles/m
    """
    Ny, Nt = X_roi.shape
    win_y = np.hanning(Ny)
    win_t = np.hanning(Nt)
    win_2d = np.outer(win_y, win_t)
    X_win = X_roi * win_2d
    F = fftshift(fft2(X_win))
    F_dB = 20 * np.log10(np.abs(F) + 1e-10)
    f_vec = np.fft.fftshift(np.fft.fftfreq(Nt, 1 / fs))
    dx_scaled = dx * scale_factor
    k_vec_scaled = np.fft.fftshift(np.fft.fftfreq(Ny, dx_scaled))
    return F_dB, f_vec, k_vec_scaled