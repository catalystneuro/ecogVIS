from __future__ import division
from process_nwb.wavelet_transform import gaussian,hamming
import numpy as np

from process_nwb.fft import fftfreq, fft, ifft
try:
    from accelerate.mkl.fftpack import fft, ifft
except ImportError:
    try:
        from pyfftw.interfaces.numpy_fft import fft, ifft
    except ImportError:
        from numpy.fft import fft, ifft


__authors__ = "Alex Bujan, Jesse Livezey"
__all__ = ['hilbert_transform']


def hilbert_transform(X, rate, filters=None, phase=None, X_fft_h=None):
    """
    Apply bandpass filtering with Hilbert transform using
    a prespecified set of filters.

    Parameters
    ----------
    X : ndarray (n_channels, n_time)
        Input data, dimensions
    rate : float
        Number of samples per second.
    filters : filter or list of filters (optional)
        One or more bandpass filters

    Returns
    -------
    Xh : ndarray, complex
        Bandpassed analytic signal
    """
    if not isinstance(filters, list):
        filters = [filters]
    time = X.shape[-1]
    freq = fftfreq(time, 1. / rate)

    Xh = np.zeros((len(filters),) + X.shape, dtype=np.complex)
    if X_fft_h is None:
        # Heavyside filter
        h = np.zeros(len(freq))
        h[freq > 0] = 2.
        h[0] = 1.
        h = h[np.newaxis, :]
        X_fft_h = fft(X) * h
        if phase is not None:
            X_fft_h *= phase
    for ii, f in enumerate(filters):
        if f is None:
            Xh[ii] = ifft(X_fft_h)
        else:
            f = f / np.linalg.norm(f)
            Xh[ii] = ifft(X_fft_h * f)
    if Xh.shape[0] == 1:
        return Xh[0], X_fft_h

    return Xh, X_fft_h
