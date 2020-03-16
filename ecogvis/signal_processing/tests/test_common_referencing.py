from ecogvis.signal_processing.common_referencing import subtract_CAR,subtract_common_median_reference

def test_subtract_common_median_reference():
    X = np.random.randn(1000, 96, 500)
    Xp = subtract_common_median_reference(X, channel_axis=-2)
    assert Xp.shape == X.shape
    
def test_subtract_CAR():
    X = np.random.randn(167, 500)
    Xs = subtract_CAR(X)
    assert Xs.shape == X.shape
    
