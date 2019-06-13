from __future__ import division
import numpy as np
from scipy.signal import firwin2, filtfilt

from .fft import rfftfreq, rfft, irfft



__all__ = ['linenoise_notch']


__authors__ = "Alex Bujan"


def apply_notches(X, notches, rate, fft=True):
    if fft:
        fs = rfftfreq(X.shape[-1], 1./rate)
        delta = 1.
        fd = rfft(X)
    else:
        nyquist = rate/2.
        n_taps = 1001
        gain = [1, 1, 0, 0, 1, 1]
    for notch in notches:
        if fft:
            window_mask = np.logical_and(fs > notch-delta, fs < notch+delta)
            window_size = window_mask.sum()
            window = np.hamming(window_size)
            fd[:, window_mask] = (fd[:, window_mask] *
                                  (1.-window)[np.newaxis, :])
        else:
            freq = np.array([0, notch-1, notch-.5,
                             notch+.5, notch+1, nyquist]) / nyquist
            filt = firwin2(n_taps, freq, gain)
            X = filtfilt(filt, np.array([1]), X)
    if fft:
        X = irfft(fd)
    return X


def linenoise_notch(X, rate):
    """
    Apply Notch filter at 60 Hz and its harmonics

    Parameters
    ----------
    X : array
        Input data, dimensions (n_channels, n_timePoints)
    rate : float
        Number of samples per second

    Returns
    -------
    X : array
        Denoised data, dimensions (n_channels, n_timePoints)
    """

    nyquist = rate / 2
    noise_hz = 60.
    notches = np.arange(noise_hz, nyquist, noise_hz)

    return apply_notches(X, notches, rate)
