import numpy as np

from ecog.signal_processing import (hilbert_transform,
        gaussian, hamming)

def test_hilbert_return():
    """
    Test the return shape and dtype.
    """
    X = np.random.randn(32, 1000)
    rate = 200
    filters = [gaussian(X, rate, 100, 5),
               hamming(X, rate, 60, 70)]
    Xh = hilbert_transform(X, rate, filters)
    assert Xh.shape == (len(filters), X.shape[0], X.shape[1])
    assert Xh.dtype == np.complex

    Xh = hilbert_transform(X, rate)
    assert Xh.shape == X.shape
    assert Xh.dtype == np.complex
