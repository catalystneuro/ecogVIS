import numpy as np
from ecogvis.signal_processing.resample import resample

def test_resample_same_sign_true():
    X = np.random.randn(32, 2000)
    Xp = resample(X, 100, 200, same_sign=True)
    assert Xp.shape == (32, 1000)


def test_resample_same_sign_false_kind_zero():
    X = np.random.randn(32, 2000)
    Xp = resample(X, 100, 200, kind=0)
    assert Xp.shape == (32, 1000)



