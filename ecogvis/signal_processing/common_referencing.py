from __future__ import division
import numpy as np


__all__ = ['subtract_common_median_reference']

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
