import numpy as np

from scipy.signal import resample as sp_resample
from ecog.signal_processing.resample_clone import resample as cl_resample

def test_resample_clone():
    rng = np.random.RandomState(20161029)
    channels = [2, 5, 32]
    times = [100, 1001, 5777]
    new_times = [59, 256, 3000]

    for ch in channels:
        for t in times:
            for nt in new_times:
                x = rng.randn(ch, t)
                sp_xf = sp_resample(x, nt, axis=-1)
                cl_xf = cl_resample(x, nt, axis=-1)
                assert np.allclose(sp_xf, cl_xf)
