import numpy as np
from ecogvis.signal_processing.linenoise_notch import linenoise_notch,apply_notches
import unittest

class LineNoiseNotchTestCase(unittest.TestCase):

    def setUp(self):
        self.X = np.random.randn(32, 1000)
        self.rate = 200

    def test_linenoise_notch_return(self):
        """
        Test the return shape.
        """
        Xh = linenoise_notch(self.X, self.rate)
        assert Xh.shape == self.X.shape

    def test_apply_notches(self):
        notches = np.arange(60, 100, 60)
        Xan = apply_notches(self.X, notches, self.rate)
        assert Xan.shape == self.X.shape
