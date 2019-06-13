from __future__ import division
import numpy as np
import scipy as sp
from .resample_clone import resample as resample_func

__authors__ = "Alex Bujan"

__all__ = ['resample']


def resample(X, new_freq, old_freq, kind=1, axis=-1, same_sign=False):
    """
    Resamples the ECoG signal from the original
    sampling frequency to a new frequency.

    Parameters
    ----------
    X : array
        Input data, dimensions (n_channels, ..., n_timePoints)
    new_freq : float
        New sampling frequency
    old_freq : float
        Original sampling frequency
    axis : int (optional)
        Axis along which to resample the data

    Returns
    -------
    Xds : array
        Downsampled data, dimensions (n_channels, ..., n_timePoints_new)
    """
    ratio = float(old_freq) / new_freq
    if np.allclose(ratio, int(ratio)) and same_sign:
        ratio = int(ratio)
        if (ratio % 2) == 0:
            med = ratio + 1
        else:
            med = ratio
        meds = [1] * X.ndim
        meds[axis % X.ndim] = med
        slices = [slice(None)] * X.ndim
        slices[axis % X.ndim] = slice(None, None, ratio)
        Xds = sp.signal.medfilt(X, meds)[slices]
    else:
        time = X.shape[axis]
        new_time = int(np.ceil(time * new_freq / old_freq))
        if kind == 0:
            ratio = int(ratio)
            if (ratio % 2) == 0:
                med = ratio + 1
            else:
                med = ratio
            meds = [1] * X.ndim
            meds[axis % X.ndim] = med
            Xf = sp.signal.medfilt(X, meds)
            f = sp.interpolate.interp1d(np.linspace(0, 1, time), Xf, axis=axis)
            Xds = f(np.linspace(0, 1, new_time))
        else:
            Xds = resample_func(X, new_time, axis=axis)

    return Xds
