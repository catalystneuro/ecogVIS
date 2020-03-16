import numpy as np
from pynwb import TimeSeries
from ecogvis.signal_processing.detect_events import detect_events,threshcross

def test_detect_events():
    speaker_data = TimeSeries(name='speaker_data', data=np.random.rand(160,), unit='m', starting_time=0.0, rate=1.0)
    mic_data = TimeSeries(name='mic_data', data=np.random.rand(160,), unit='m', starting_time=0.0, rate=1.0)
    detect_events(speaker_data, mic_data)
    
    
def test_threshcross():
    data = np.random.randn(500)
    out = threshcross(data,threshold=0.08)
    assert out.shape[0]<=data.shape[0]
