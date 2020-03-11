import numpy as np
from ecogvis.signal_processing.linenoise_notch import linenoise_notch,apply_notches

def test_linenoise_notch_return():
    """
    Test the return shape.
    """
    X = np.random.randn(32, 1000)
    rate = 200
    Xh = linenoise_notch(X, rate)
    assert Xh.shape == X.shape

def test_apply_notches():
    X = np.random.randn(32, 1000)
    rate = 200
    notches = np.arange(60, 100, 60)
    Xan = apply_notches(X, notches, rate)
    assert Xan.shape == X.shape
