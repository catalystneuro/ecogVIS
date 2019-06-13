import os

import numpy as np

from scipy.io import loadmat

from .. import utils


__all__ = ['load_silence_time',
           'compute_baseline',
           'zscore']

def load_silence_time(nwb):
    start = nwb.epochs['start_time'][0]
    stop = nwb.epochs['stop_time'][0]
    return np.array([start, stop])


def compute_baseline(data, tt_data, baseline_time):
    data_time = utils.is_in(tt_data, baseline_time)
    return data[..., data_time]


def zscore(data, axis=-1, mode=None, sampling_freq=None, bad_times=None,
           align_window=None, event_times=None, silence_time=None):

    if mode is None:
        mode = 'silence'

    if mode == 'whole':
        baseline = data
    elif mode == 'between_data':
        tt_data = np.arange(data.shape[axis]) / sampling_freq
        data_start = event_times.min() + align_window[0]
        data_stop = event_times.max() + align_window[1]
        data_time = utils.is_in(tt_data, np.array([data_start, data_stop]))
        for bt in bad_times:
            data_time = data_time & ~utils.is_in(tt_data, bt)
        for et in event_times:
            data_time = data_time & ~utils.is_in(tt_data, et + align_window)
        baseline = data[..., data_time]
    elif mode == 'data':
        tt_data = np.arange(data.shape[-1]) / sampling_freq
        data_start = event_times.min() + align_window[0]
        data_stop = event_times.max() + align_window[1]
        data_time = utils.is_in(tt_data, np.array([data_start, data_stop]))
        for bt in bad_times:
            data_time = data_time & ~utils.is_in(tt_data, bt)
        baseline = data[..., data_time]
    elif mode == 'events':
        tt_data = np.arange(data.shape[-1]) / sampling_freq
        data_time = np.zeros_like(tt_data, dtype=bool)
        for et in event_times:
            data_time = data_time | utils.is_in(tt_data, et + align_window)
        for bt in bad_times:
            data_time = data_time & ~utils.is_in(tt_data, bt)
        baseline = data[..., data_time]
    elif mode == 'silence':
        tt_data = np.arange(data.shape[axis]) / sampling_freq
        baseline = compute_baseline(data, tt_data, silence_time)
    elif mode == 'ratio_silence':
        tt_data = np.arange(data.shape[axis]) / sampling_freq
        baseline = compute_baseline(data, tt_data, silence_time)
        means = baseline.mean(axis=axis, keepdims=True)
        stds = baseline.std(axis=axis, keepdims=True)
        data = data / means
        return data, means, stds, baseline
    elif mode == 'none':
        tt_data = np.arange(data.shape[axis]) / sampling_freq
        baseline = load_baseline(kwargs['block_path'], data, tt_data)
        means = baseline.mean(axis=axis, keepdims=True)
        stds = baseline.std(axis=axis, keepdims=True)
        return data, means, stds, baseline
    else:
        raise ValueError('zscore_mode type {} not recognized.'.format(mode))

    means = baseline.mean(axis=axis, keepdims=True)
    stds = baseline.std(axis=axis, keepdims=True)
    data = (data - means) / stds

    return data, means, stds, baseline
