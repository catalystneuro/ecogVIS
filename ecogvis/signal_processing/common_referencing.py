from __future__ import division
import numpy as np


__all__ = ['subtract_CAR',
           'subtract_common_median_reference']

def subtract_CAR(X, b_size=16):
    """
    Compute and subtract common average reference in 16 channel blocks.
    """

    channels, time_points = X.shape
    s = channels // b_size
    r = channels % b_size

    X_1 = X[:channels-r].copy()

    X_1 = X_1.reshape((s, b_size, time_points))
    X_1 -= np.nanmean(X_1, axis=1, keepdims=True)
    if r > 0:
        X_2 = X[channels-r:].copy()
        X_2 -= np.nanmean(X_2, axis=0, keepdims=True)
        X = np.vstack([X_1.reshape((s*b_size, time_points)), X_2])
        return X
    else:
        return X_1.reshape((s*b_size, time_points))


def subtract_common_median_reference(X, channel_axis=-2):
    """
    Compute and subtract common median reference
    for the entire grid.

    Parameters
    ----------
    X : ndarray (..., n_channels, n_time)
        Data to common median reference.

    Returns
    -------
    Xp : ndarray (..., n_channels, n_time)
        Common median referenced data.
    """

    median = np.nanmedian(X, axis=channel_axis, keepdims=True)
    Xp = X - median

    return Xp
