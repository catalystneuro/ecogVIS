from ecogvis.signal_processing.detect_events import detect_events,threshcross

def test_detect_events():
    
    
def test_threshcross():
    data = np.random.randn(500)
    out = threshcross(data,threshold=0.08)
    assert out.shape[0]<=data.shape[0]
