import numpy as np
import scipy.signal as sgn
from process_nwb.resample import resample

def detect_events(speaker_data, mic_data=None, interval=None, dfact=30,
                  smooth_width=0.4, threshold=0.05, direction='both'):
    """
    Automatically detects events in audio signals.

    Parameters
    ----------
    speaker_data : 'pynwb.base.TimeSeries' object
        Object containing speaker data.
    mic_data : 'pynwb.base.TimeSeries' object
        Object containing microphone data.
    interval : list of floats
        Interval to be used [Start_bin, End_bin]. If 'None', the whole signal is used.
    dfact : float
        Downsampling factor. Default 30.
    smooth_width: float
        Width scale for median smoothing filter (default = .4, decent for CVs).
    threshold : float
        Sets threshold level.
    direction : str
        'Up' detects events start times. 'Down' detects events stop times. 'Both'
        detects both start and stop times.

    Returns
    -------
    speakerDS : 1D array of floats
        Downsampled speaker signal.
    speakerEventDS : 1D array of floats
        Event times for speaker signal.
    micDS : 1D array of floats
        Downsampled microphone signal.
    micEventDS : 1D array of floats
        Event times for microphone signal.
    """

    # Downsampling Speaker -----------------------------------------------------
    speakerDS, speakerEventDS = None, None
    if speaker_data is not None:
        if interval is None:
            X = speaker_data.data[:]
        else:
            X = speaker_data.data[interval[0]:interval[1]]
        fs = speaker_data.rate    #sampling rate
        ds = fs/dfact
        #Pad zeros to make signal lenght a power of 2, improves performance
        nBins = X.shape[0]
        extraBins = 2**(np.ceil(np.log2(nBins)).astype('int')) - nBins
        extraZeros = np.zeros(extraBins)
        X = np.append(X, extraZeros)
        speakerDS = resample(X, ds, fs)
        #Remove excess bins (because of zero padding on previous step)
        excessBins = int(np.ceil(extraBins*ds/fs))
        speakerDS = speakerDS[0:-excessBins]

        #kernel size must be an odd number
        speaker_filt = sgn.medfilt(volume=np.diff(np.append(speakerDS,speakerDS[-1]))**2,
                                   kernel_size=int((smooth_width*ds//2)*2+1))
        speaker_thresh = np.std(speaker_filt)*threshold
        #Find threshold crossing times
        stimBinsDS = threshcross(speaker_filt, speaker_thresh, direction)
        #Remove detections too close in time (< 100 miliseconds)
        rem_ind = np.where(np.diff(stimBinsDS/ds)<.1)[0] + 1
        stimBinsDS = np.delete(stimBinsDS, rem_ind)
        #Transform bins to time
        speakerEventDS = stimBinsDS/ds

    # Downsampling Mic ---------------------------------------------------------
    micDS, micEventDS = None, None
    if mic_data is not None:
        if interval is None:
            X = mic_data.data[:]
        else:
            X = mic_data.data[interval[0]:interval[1]]
        fs = mic_data.rate    #sampling rate
        ds = fs/dfact
        #Pad zeros to make signal lenght a power of 2, improves performance
        nBins = X.shape[0]
        extraBins = 2**(np.ceil(np.log2(nBins)).astype('int')) - nBins
        extraZeros = np.zeros(extraBins)
        X = np.append(X, extraZeros)
        micDS = resample(X, ds, fs)
        #Remove excess bins (because of zero padding on previous step)
        excessBins = int(np.ceil(extraBins*ds/fs))
        micDS = micDS[0:-excessBins]

        # Remove mic response to speaker
        micDS[np.where(speaker_filt > speaker_thresh)[0]] = 0
        mic_filt = sgn.medfilt(volume=np.diff(np.append(micDS,micDS[-1]))**2,
                               kernel_size=int((smooth_width*ds//2)*2+1))
        mic_thresh = np.std(mic_filt)*threshold #2e-4
        #Find threshold crossing times
        micBinsDS = threshcross(mic_filt, mic_thresh, direction)
        #Remove detections too close in time (< 100 miliseconds)
        rem_ind = np.where(np.diff(micBinsDS/ds)<.1)[0] + 1
        micBinsDS = np.delete(micBinsDS, rem_ind)
        #Transform bins to time
        micEventDS = micBinsDS/ds

    return speakerDS, speakerEventDS, micDS, micEventDS


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

    Returns
    -------
    out : array
        Array with indices where data crossed threshold.
    """

    # Find crosses
    over = (data >= threshold).astype('int')
    cross = np.append(False,np.diff(over))

    if direction == 'up':
        out = np.where(cross==1)[0]
    elif direction == 'down':
        out = np.where(cross==-1)[0]
    elif direction == 'both':
        out = np.where(cross!=0)[0]

    return out
