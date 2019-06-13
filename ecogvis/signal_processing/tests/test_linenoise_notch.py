import numpy as np

from ecog.signal_processing import linenoise_notch

def test_linenoise_notch_return():
    """
    Test the return shape.
    """
    X = np.random.randn(32, 1000)
    rate = 200
    Xh = linenoise_notch(X, rate)
    assert Xh.shape == X.shape
