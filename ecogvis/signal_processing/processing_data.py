from __future__ import print_function, division

import argparse, h5py, time, os
import numpy as np

import nwbext_ecog
from pynwb import NWBHDF5IO, ProcessingModule
from pynwb.ecephys import LFP
from pynwb.core import DynamicTable, DynamicTableRegion, VectorData
from pynwb.misc import DecompositionSeries
from pynwb.base import TimeSeries

from ecogvis.signal_processing.hilbert_transform import *
from ecogvis.signal_processing.resample import *
from ecogvis.signal_processing.linenoise_notch import *
from ecogvis.signal_processing.common_referencing import *
from ecogvis.signal_processing.bands import *


def processing_data(path, subject, blocks, mode=None , config=None):
    for block in blocks:
        block_path = os.path.join(path, '{}_B{}.nwb'.format(subject, block))
        if mode=='preprocess':
            preprocess_raw_data(block_path, config=config)
        elif mode=='decomposition':
            spectral_decomposition(block_path, bands_vals=config)
        elif mode=='high_gamma':
            high_gamma_estimation(block_path, bands_vals=config)


def preprocess_raw_data(block_path, config=None):
    """
    Takes raw data and runs:
    1) CAR
    2) notch filters
    3) Downsampling

    Parameters
    ----------
    block_path : str
        subject file path
    config : dictionary
        'CAR' - boolean, whether to run CAR or not (default=True)
        'Notch' - Main frequency (Hz) for notch filters (default=60)
        'Downsample' - Downsampling frequency (Hz, default= 400)

    Returns
    -------
    Saves preprocessed signals (LFP) in the current NWB file.
    Only if containers for these data do not exist in the current file.
    """
    subj_path, block_name = os.path.split(block_path)
    block_name = os.path.splitext(block_path)[0]
    start = time.time()

    with NWBHDF5IO(block_path, 'r+') as io:
        nwb = io.read()

        # Storage of processed signals on NWB file -----------------------------
        try:      # if ecephys module already exists
            ecephys_module = nwb.modules['ecephys']
        except:   # creates ecephys ProcessingModule
            ecephys_module = ProcessingModule(name='ecephys',
                                              description='Extracellular electrophysiology data.')
            # Add module to NWB file
            nwb.add_processing_module(ecephys_module)

        # LFP: Downsampled and power line signal removed -----------------------
        if 'LFP' in nwb.modules['ecephys'].data_interfaces:    # if LFP already exists
            lfp = nwb.modules['ecephys'].data_interfaces['LFP']
            lfp_ts = nwb.modules['ecephys'].data_interfaces['LFP'].electrical_series['preprocessed']
        else: # creates LFP data interface container
            lfp = LFP()

            # Downsampling
            fs = nwb.acquisition['ECoG'].rate
            if config['Downsample'] is not None:
                rate = config['Downsample']
            else:
                rate = fs
            nChannels = nwb.acquisition['ECoG'].data.shape[1]
            for ch in np.arange(nChannels):     #One channel at a time, to improve memory usage for large files
                Xch = nwb.acquisition['ECoG'].data[:,ch]*1e6  # 1e6 scaling helps with numerical accuracy
                if config['Downsample'] is not None:  # Downsample
                    if not np.allclose(rate, fs):
                        assert rate < fs
                        Xch = resample(Xch, rate, fs)
                    if ch==0:
                        X = Xch.reshape(1,-1)
                    else:
                        X = np.append(X, Xch.reshape(1,-1), axis=0)

            # Subtract CAR
            if config['CAR']:
                print("Computing and subtracting Common Average Reference in 16 channel blocks.")
                start = time.time()
                X = subtract_CAR(X)
                print('CAR subtract time for {}: {} seconds'.format(block_name,
                                                                    time.time()-start))

            # Apply Notch filters
            if config['Notch'] is not None:
                print("Applying Notch filtering of "+str(config['Notch'])+" Hz")
                start = time.time()
                X = linenoise_notch(X, rate, notch_freq=config['Notch'])
                print('Notch filter time for {}: {} seconds'.format(block_name,
                                                                    time.time()-start))

            X = X.astype('float32')     # signal (nChannels,nSamples)
            X /= 1e6                    # Scales signals back to Volt

            # Add preprocessed downsampled signals as an electrical_series
            elecs_region = nwb.electrodes.create_region(name='electrodes',
                                                        region=np.arange(nChannels).tolist(),
                                                        description='')
            lfp_ts = lfp.create_electrical_series(name='preprocessed',
                                                  data=X.T,
                                                  electrodes=elecs_region,
                                                  rate=rate,
                                                  description='')
            ecephys_module.add_data_interface(lfp)

            # Write LFP to NWB file
            io.write(nwb)


def spectral_decomposition(block_path, bands_vals):
    """
    Takes preprocessed LFP data and does the standard Hilbert transform on
    different bands. Takes about 20 minutes to run on 1 10-min block.

    Parameters
    ----------
    block_path : str
        subject file path
    bands_vals : [2,nBands] numpy array with Gaussian filter parameters, where:
        bands_vals[0,:] = filter centers [Hz]
        bands_vals[1,:] = filter sigmas [Hz]

    Returns
    -------
    Saves spectral power (DecompositionSeries) in the current NWB file.
    Only if container for this data do not exist in the file.
    """

    # Get filter parameters
    band_param_0 = bands_vals[0,:]
    band_param_1 = bands_vals[1,:]

    with NWBHDF5IO(block_path, 'r+') as io:
        nwb = io.read()
        lfp = nwb.modules['ecephys'].data_interfaces['LFP'].electrical_series['preprocessed']
        rate = lfp.rate

        nBands = len(band_param_0)
        nSamples = lfp.data.shape[0]
        nChannels = lfp.data.shape[1]
        Xp = np.zeros((nBands, nChannels, nSamples))  #power (nBands,nChannels,nSamples)

        # Apply Hilbert transform
        X = lfp.data[:].T*1e6       # 1e6 scaling helps with numerical accuracy
        X = X.astype('float32')     # signal (nChannels,nSamples)
        X_fft_h = None
        for ii, (bp0, bp1) in enumerate(zip(band_param_0, band_param_1)):
            kernel = gaussian(X, rate, bp0, bp1)
            X_analytic, X_fft_h = hilbert_transform(X, rate, kernel, phase=None, X_fft_h=X_fft_h)
            Xp[ii] = abs(X_analytic).astype('float32')

        # data: (ndarray) dims: num_times * num_channels * num_bands
        Xp = np.swapaxes(Xp,0,2)

        # Spectral band power
        # bands: (DynamicTable) frequency bands that signal was decomposed into
        band_param_0V = VectorData(name='filter_param_0',
                          description='frequencies for bandpass filters',
                          data=band_param_0)
        band_param_1V = VectorData(name='filter_param_1',
                          description='frequencies for bandpass filters',
                          data=band_param_1)
        bandsTable = DynamicTable(name='bands',
                                  description='Series of filters used for Hilbert transform.',
                                  columns=[band_param_0V,band_param_1V],
                                  colnames=['filter_param_0','filter_param_1'])
        decs = DecompositionSeries(name='Bandpower',
                                    data=Xp,
                                    description='Band power estimated with Hilbert transform.',
                                    metric='power',
                                    unit='V**2/Hz',
                                    bands=bandsTable,
                                    rate=rate,
                                    source_timeseries=lfp)

        # Storage of spectral decomposition on NWB file ------------------------
        ecephys_module = nwb.modules['ecephys']
        ecephys_module.add_data_interface(decs)
        io.write(nwb)


def high_gamma_estimation(block_path, config=None):
    """
    Takes preprocessed LFP data and calculates High-Gamma power from the
    averaged power of standard Hilbert transform on 70~150 Hz bands.

    Parameters
    ----------
    block_path : str
        subject file path
    config : dictionary
        'filter': str
            'default' for Chang lab default bands (70~150 Hz)
            'custom' for user defined bands
        'bands_vals': [2,nBands] numpy array with Gaussian filter parameters
            bands_vals[0,:] = filter centers [Hz]
            bands_vals[1,:] = filter sigmas [Hz]

    Returns
    -------
    Saves spectral power (DecompositionSeries) in the current NWB file.
    Only if container for this data do not exist in the file.
    """
    write_file = 1

    # Define filter parameters
    if filter=='default':
        band_param_0 = bands.chang_lab['cfs']
        band_param_1 = bands.chang_lab['sds']
    elif filter=='high_gamma':
        #band_param_0 = [ bands.neuro['min_freqs'][-1] ]  #for hamming window filter
        #band_param_1 = [ bands.neuro['max_freqs'][-1] ]
        #band_param_0 = bands.chang_lab['cfs'][29:37]      #for average of gaussian filters
        #band_param_1 = bands.chang_lab['sds'][29:37]
        band_param_0 = bands_vals[0,:]
        band_param_1 = bands_vals[1,:]
    elif filter=='custom':
        band_param_0 = bands_vals[0,:]
        band_param_1 = bands_vals[1,:]

    subj_path, block_name = os.path.split(block_path)
    block_name = os.path.splitext(block_path)[0]
    start = time.time()

    with NWBHDF5IO(block_path, 'r+') as io:
        nwb = io.read()

        fs = nwb.acquisition['ECoG'].rate
        if config['Downsample'] is not None:
            rate = config['Downsample']
        else: rate = fs

        #X = nwb.acquisition['ECoG'].data[:].T * 1e6
        nChannels = nwb.acquisition['ECoG'].data.shape[1]
        for ch in np.arange(nChannels):     #One channel at a time, to improve memory usage for large files
            Xch = nwb.acquisition['ECoG'].data[:,ch]*1e6  # 1e6 scaling helps with numerical accuracy
            if config['Downsample'] is not None:  # Downsample
                if not np.allclose(rate, fs):
                    assert rate < fs
                    Xch = resample(Xch, rate, fs)
                if ch==0:
                    X = Xch.reshape(1,-1)
                else:
                    X = np.append(X, Xch.reshape(1,-1), axis=0)


        # Apply Hilbert transform
        X = X.astype('float32')   #signal (nChannels,nSamples)
        nChannels = X.shape[0]
        nSamples = X.shape[1]
        nBands = len(band_param_0)
        Xp = np.zeros((nBands, nChannels, nSamples))  #power (nBands,nChannels,nSamples)
        X_fft_h = None
        for ii, (bp0, bp1) in enumerate(zip(band_param_0, band_param_1)):
            #if filter=='high_gamma':
            #    kernel = hamming(X, rate, bp0, bp1)
            #else:
            kernel = gaussian(X, rate, bp0, bp1)
            X_analytic, X_fft_h = hilbert_transform(X, rate, kernel, phase=None, X_fft_h=X_fft_h)
            Xp[ii] = abs(X_analytic).astype('float32')

        # Scales signals back to Volt
        X /= 1e6
        # data: (ndarray) dims: num_times * num_channels * num_bands
        Xp = np.swapaxes(Xp,0,2)

        # Storage of processed signals on NWB file -----------------------------
        try:      # if ecephys module already exists
            ecephys_module = nwb.modules['ecephys']
        except:   # creates ecephys ProcessingModule
            ecephys_module = ProcessingModule(name='ecephys',
                                              description='Extracellular electrophysiology data.')
            # Add module to NWB file
            nwb.add_processing_module(ecephys_module)


        # LFP: Downsampled and power line signal removed
        if 'LFP' in nwb.modules['ecephys'].data_interfaces:
            lfp_ts = nwb.modules['ecephys'].data_interfaces['LFP'].electrical_series['preprocessed']
            X = lfp_ts.data[:].T
            rate = lfp_ts.rate

        try:    # if LFP already exists
            lfp = nwb.modules['ecephys'].data_interfaces['LFP']
            lfp_ts = nwb.modules['ecephys'].data_interfaces['LFP'].electrical_series['preprocessed']
        except: # creates LFP data interface container
            lfp = LFP()
            # Add preprocessed downsampled signals as an electrical_series
            elecs_region = nwb.electrodes.create_region(name='electrodes',
                                                        region=np.arange(nChannels).tolist(),
                                                        description='')
            lfp_ts = lfp.create_electrical_series(name='preprocessed',
                                                  data=X.T,
                                                  electrodes=elecs_region,
                                                  rate=rate,
                                                  description='')
            ecephys_module.add_data_interface(lfp)


        # Spectral band power
        try:     # if decomposition already exists
            dec = nwb.modules['ecephys'].data_interfaces['Bandpower_'+filter]
            write_file = 0
        except:  # creates DecompositionSeries
            if filter=='high_gamma':    # High gamma bands averaged: 70~150 Hz
                HG = np.nanmean(Xp, 2)   #average of bands 70~150 Hz
                hg = TimeSeries(name='high_gamma',
                                data=HG,
                                rate=rate,
                                unit='V**2/Hz',
                                description='')
                ecephys_module.add_data_interface(hg)
            else:   #Default or custom sequence of bands
                # bands: (DynamicTable) frequency bands that signal was decomposed into
                band_param_0V = VectorData(name='filter_param_0',
                                  description='frequencies for bandpass filters',
                                  data=band_param_0)
                band_param_1V = VectorData(name='filter_param_1',
                                  description='frequencies for bandpass filters',
                                  data=band_param_1)
                bandsTable = DynamicTable(name='bands',
                                          description='Series of filters used for Hilbert transform.',
                                          columns=[band_param_0V,band_param_1V],
                                          colnames=['filter_param_0','filter_param_1'])
                decs = DecompositionSeries(name='Bandpower_'+filter,
                                            data=Xp,
                                            description='Band power estimated with Hilbert transform.',
                                            metric='power',
                                            unit='V**2/Hz',
                                            bands=bandsTable,
                                            rate=rate,
                                            source_timeseries=lfp_ts)
                ecephys_module.add_data_interface(decs)


        if write_file==1: # if new fields are created
            io.write(nwb)
