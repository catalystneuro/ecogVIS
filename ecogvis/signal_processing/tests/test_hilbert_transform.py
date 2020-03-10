import numpy as np
from ecogvis.signal_processing.hilbert_transform import (hilbert_transform,
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


def test_gaussian():
    X = np.random.randn(32, 1000)
    rate = 200
    center = 100
    sd = 5
    Xg = gaussian(X, rate, center, sd)
    assert Xg.shape[0] == X.shape[1]
    assert Xg.dtype == 'float64'


def test_hamming():
    X = np.random.randn(32, 1000)
    rate = 200
    min_freq = 60
    max_freq = 70
    Xham = hamming(X, rate, min_freq, max_freq)
    assert Xham.shape[0] == X.shape[1]
    assert Xham.dtype == 'float64'
    
