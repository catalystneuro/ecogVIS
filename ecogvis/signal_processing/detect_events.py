# -*- coding: utf-8 -*-
"""
Detect CV (consonant-vowel) pair events in speaker and microphone channels.
"""

# Third party libraries
import numpy as np
import scipy.signal as sgn
from process_nwb.resample import resample

def detect_events(speaker_data, mic_data=None, interval=None, dfact=30,
                  smooth_width=0.4, speaker_threshold=0.05, mic_threshold=0.05,
                  direction='both'):
    """
    Automatically detects events in audio signals.

    Parameters
    ----------
    speaker_data : 'pynwb.base.TimeSeries' object
        Object containing speaker data.
    mic_data : 'pynwb.base.TimeSeries' object
        Object containing microphone data.
    interval : list of floats
        Interval to be used [Start_bin, End_bin]. If 'None', the whole
        signal is used.
    dfact : float
        Downsampling factor. Default 30.
    smooth_width: float
        Width scale for median smoothing filter (default = .4, decent for CVs).
    speaker_threshold : float
        Sets threshold level for speaker.
    mic_threshold : float
        Sets threshold level for mic.
    direction : str
        'Up' detects events start times. 'Down' detects events stop times.
        'Both'
        detects both start and stop times.

    Returns
    -------
    speakerDS : 1D array of floats
        Downsampled speaker signal.
    speakerEventDS : 1D array of floats
        Event times for speaker signal.
    speakerFilt : 1D array of floats
        Filtered speaker signal.
    micDS : 1D array of floats
        Downsampled microphone signal.
    micEventDS : 1D array of floats
        Event times for microphone signal.
    micFilt : 1D array of floats
        Filtered microphone signal.
    """

    # Downsampling Speaker ---------------------------------------------------

    speakerDS, speakerEventDS, speakerFilt = None, None, None

    if speaker_data is not None:
        if interval is None:
            X = speaker_data.data[:]
        else:
            X = speaker_data.data[interval[0]:interval[1]]
        fs = speaker_data.rate  # sampling rate
        ds = fs / dfact

        # Pad zeros to make signal length a power of 2, improves performance
        nBins = X.shape[0]
        extraBins = 2 ** (np.ceil(np.log2(nBins)).astype('int')) - nBins
        extraZeros = np.zeros(extraBins)
        X = np.append(X, extraZeros)
        speakerDS = resample(X, ds, fs)

        # Remove excess bins (because of zero padding on previous step)
        excessBins = int(np.ceil(extraBins * ds / fs))
        speakerDS = speakerDS[0:-excessBins]

        # Kernel size must be an odd number
        speakerFilt = sgn.medfilt(
            volume=np.diff(np.append(speakerDS, speakerDS[-1])) ** 2,
            kernel_size=int((smooth_width * ds // 2) * 2 + 1))

        # Normalize the filtered signal.
        speakerFilt /= np.max(np.abs(speakerFilt))

        # Find threshold crossing times
        stimBinsDS = threshcross(speakerFilt, speaker_threshold, direction)

        # Remove events that have a duration less than 0.1 s.
        speaker_events = stimBinsDS.reshape((-1, 2))
        rem_ind = np.where((speaker_events[:, 1] - speaker_events[:, 0]) < ds * 0.1)[0]
        speaker_events = np.delete(speaker_events, rem_ind, axis=0)
        stimBinsDS = speaker_events.reshape((-1))

        # Transform bins to time
        speakerEventDS = (stimBinsDS  / ds) + (interval[0] / fs)

    # Downsampling Mic -------------------------------------------------------

    micDS, micEventDS, micFilt = None, None, None

    if mic_data is not None:

        if interval is None:
            X = mic_data.data[:]
        else:
            X = mic_data.data[interval[0]:interval[1]]
        fs = mic_data.rate  # sampling rate
        ds = fs / dfact

        # Pad zeros to make signal length a power of 2, improves performance
        nBins = X.shape[0]
        extraBins = 2 ** (np.ceil(np.log2(nBins)).astype('int')) - nBins
        extraZeros = np.zeros(extraBins)
        X = np.append(X, extraZeros)
        micDS = resample(X, ds, fs)

        # Remove excess bins (because of zero padding on previous step)
        excessBins = int(np.ceil(extraBins * ds / fs))
        micDS = micDS[0:-excessBins]

        # Remove mic response to speaker
        micDS[np.where(speakerFilt > speaker_threshold)[0]] = 0
        micFilt = sgn.medfilt(volume=np.diff(np.append(micDS, micDS[-1])) ** 2,
                              kernel_size=int(
                                  (smooth_width * ds // 2) * 2 + 1))

        # Normalize the filtered signal.
        micFilt /= np.max(np.abs(micFilt))

        # Find threshold crossing times
        micBinsDS = threshcross(micFilt, mic_threshold, direction)

        # Remove events that have a duration less than 0.1 s.
        mic_events = micBinsDS.reshape((-1, 2))
        rem_ind = np.where((mic_events[:, 1] - mic_events[:, 0]) < ds * 0.1)[0]
        mic_events = np.delete(mic_events, rem_ind, axis=0)
        micBinsDS = mic_events.reshape((-1))

        # Transform bins to time
        micEventDS = (micBinsDS / ds) + (interval[0] / fs)

    return speakerDS, speakerEventDS, speakerFilt, micDS, micEventDS, micFilt


def threshcross(data, threshold=0, direction='up'):
    """
    Outputs the indices where the signal crossed the threshold.

    Parameters
    ----------
    data : array of floats
        Numpy array of floats, containing signal.
    threshold : float
        Value of threshold.
    direction : str
        Defines the direction of cross detected: 'up', 'down', or 'both'.
        With 'both', it will check to make sure that up and down crosses are
        detected. In other words,

    Returns
    -------
    out : array
        Array with indices where data crossed threshold.
    """

    # Find crosses
    over = (data >= threshold).astype('int')
    cross = np.append(False, np.diff(over))

    if direction == 'up':
        out = np.where(cross == 1)[0]
    elif direction == 'down':
        out = np.where(cross == -1)[0]
    elif direction == 'both':
        cross_nonzero = np.where(cross != 0)[0]

        events = []
        for i in range(len(cross_nonzero) - 1):

            # Skip to the next ind if this one was already recorded.
            if cross_nonzero[i] in events:
                continue

            if (cross[cross_nonzero[i]] == 1) and (
                    cross[cross_nonzero[i + 1]] == -1):
                events.append(cross_nonzero[i])
                events.append(cross_nonzero[i + 1])

        out = np.array(events)

    return out
