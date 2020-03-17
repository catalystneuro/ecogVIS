import numpy as np
from ecogvis.signal_processing.resample import resample
import unittest


class ShowPSTHTestCase(unittest.TestCase):

    def setUp(self):
        self.X = np.random.randn(32, 2000)
        
    def test_resample_same_sign_true(self):
        Xp = resample(self.X, 100, 200, same_sign=True)
        assert Xp.shape == (32, 1000)

    def test_resample_same_sign_false_kind_zero(self):
        Xp = resample(self.X, 100, 200, kind=0)
        assert Xp.shape == (32, 1000)

    def test_resample_same_sign_false_kind_nonzero(self):
        Xp = resample(self.X, 100, 200)
        assert Xp.shape == (32, 1000)
