import numpy as np
from ecogvis.signal_processing.hilbert_transform import (hilbert_transform,
        gaussian, hamming)
import unittest

class HilbertTestCase(unittest.TestCase):

    def setUp(self):
        self.X = np.random.randn(32, 1000)
        self.rate = 200

        
    def test_hilbert_return(self):
        """
        Test the return shape and dtype.
        """
        
        filters = [gaussian(self.X, self.rate, 100, 5),
                   hamming(self.X, self.rate, 60, 70)]
        Xh = hilbert_transform(self.X, self.rate, filters)
        assert Xh.shape == (len(filters), self.X.shape[0], self.X.shape[1])
        assert Xh.dtype == np.complex

        Xh = hilbert_transform(self.X, self.rate)
        assert Xh.shape == self.X.shape
        assert Xh.dtype == np.complex


    def test_gaussian(self):
       
        center = 100
        sd = 5
        Xg = gaussian(self.X, self.rate, center, sd)
        assert Xg.shape[0] == self.X.shape[1]
        assert Xg.dtype == 'float64'


    def test_hamming(self):
        
        min_freq = 60
        max_freq = 70
        Xham = hamming(self.X, self.rate, min_freq, max_freq)
        assert Xham.shape[0] == self.X.shape[1]
        assert Xham.dtype == 'float64'

