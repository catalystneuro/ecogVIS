import numpy as np
from pynwb import TimeSeries
from ecogvis.signal_processing.detect_events import detect_events, threshcross
from scipy.io import wavfile
import os


def test_detect_events():
    here_path = os.path.dirname(os.path.abspath(__file__))
    fs1, data1 = wavfile.read(os.path.join(here_path, 'example_speaker.wav'))
    fs2, data2 = wavfile.read(os.path.join(here_path, 'example_microphone.wav'))

    # microphone recorded signal starts before, it gets aligned with speaker with [92000:, 0]
    speaker_data = TimeSeries(name='speaker_data', data=data1[:, 0].astype('float'), unit='m', starting_time=0.0, rate=float(fs1))
    mic_data = TimeSeries(name='mic_data', data=data2[92000:, 0].astype('float'), unit='m', starting_time=0.0, rate=float(fs2))

    speakerDS, speakerEventDS, speakerFilt, micDS, micEventDS, micFilt = detect_events(
        speaker_data,
        mic_data,
        interval=[0, 450000],
        dfact=30,
        speaker_threshold=0.01,
        mic_threshold=0.01
    )

    speakerEventDS_expected = np.array([1.24875, 1.60875, 4.000625, 4.44625, 6.98, 7.214375])
    micEventDS_expected = np.array([2.314375, 2.7, 5.413125, 5.841875, 8.55, 8.7475])

    np.testing.assert_array_almost_equal(speakerEventDS, speakerEventDS_expected)
    np.testing.assert_array_almost_equal(micEventDS, micEventDS_expected)


def test_threshcross():
    data = np.array([-0.00923858, -0.46818037, 0.97913552, 1.44891143, 0.52656067,
                     -0.13614786, -1.15257763, 0.19372024, -0.27798147, 0.3749529,
                     -1.34686999, 0.65927353, -1.20584738, -1.26425261, 2.1550186,
                     0.25529244, 0.86569944, 0.08566919, 1.60049703, -0.77054931,
                     -0.16126592, -0.149841, -0.42771099, 0.34550433, -1.36395812,
                     0.8393572, -0.21272933, 0.90493892, 1.8125925, -0.45761982,
                     -0.69935143, 1.26503883, -0.00657156, 1.20480859, 1.44862601,
                     0.79878701, -0.27143059, -1.54836016, -0.00322803, -0.29347789,
                     0.76488881, 0.93952847, 1.99928338, -1.09587945, -0.52881138,
                     0.31639658, 1.32548262, 0.60921676, -1.32819148, 0.46352056])
    out = threshcross(data, threshold=0.08)
    out_expected = np.array([2, 7, 9, 11, 14, 23, 25, 27, 31, 33, 40, 45, 49])
    np.testing.assert_equal(out, out_expected)
