import numpy as np

from numpy.fft import rfftfreq, fftfreq

try:
    from mkl_fft._numpy_fft import rfft, irfft, fft, ifft
except ImportError:
    try:
        from pyfftw.interfaces.numpy_fft import rfft, irfft, fft, ifft
    except ImportError:
        from numpy.fft import rfft, irfft, fft, ifft
