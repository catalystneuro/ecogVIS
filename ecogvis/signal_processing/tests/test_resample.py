import numpy as np

from ecog.signal_processing import resample

def test_resample_shape():
    X = np.random.randn(32, 2000)

    Xp = resample(X, 100, 200)
    assert Xp.shape == (32, 1000)


def test_resample_ones():
    chs = [2, 32, 100]

    ts = [50, 1001, 5077]
    for ch in chs:
        for t in ts:
            X = np.ones((32, 2000))

            Xp = resample(X, 100, 200)
            assert np.allclose(Xp, 1.)
