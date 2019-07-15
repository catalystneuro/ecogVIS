from __future__ import print_function, division

import argparse, h5py, time, os
import numpy as np

import nwbext_ecog
from pynwb import NWBHDF5IO, ProcessingModule
from pynwb.ecephys import LFP, ElectricalSeries
from pynwb.core import DynamicTable, DynamicTableRegion, VectorData
from pynwb.misc import DecompositionSeries
from pynwb.base import TimeSeries
from pynwb.file import Subject

from ecogvis.signal_processing.hilbert_transform import *
from ecogvis.signal_processing.resample import *
from ecogvis.signal_processing.linenoise_notch import *
from ecogvis.signal_processing.common_referencing import *
from ecogvis.signal_processing.bands import *


def processing_data(path, subject, blocks, mode=None , config=None, new_file=''):
    for block in blocks:
        block_path = os.path.join(path, '{}_B{}.nwb'.format(subject, block))
        if new_file!='':
            make_new_nwb(old_file=block_path, new_file=new_file)

        if mode=='preprocess':
            preprocess_raw_data(block_path, config=config)
        elif mode=='decomposition':
            spectral_decomposition(block_path, bands_vals=config)
        elif mode=='high_gamma':
            high_gamma_estimation(block_path, bands_vals=config, new_file=new_file)


def make_new_nwb(old_file, new_file):
    """
    Copy all fields, except 'acquisition', from current NWB file to new NWB file.

    Parameters
    ----------
    old_file : str, path
        String such as '/path/to/old_file.nwb'.
    new_file : str, path
        String such as '/path/to/new_file.nwb'.
    """
    from datetime import datetime
    from dateutil.tz import tzlocal
    from pynwb import NWBFile, NWBHDF5IO, get_manager
    from pynwb.device import Device
    from nwbext_ecog import CorticalSurfaces, ECoGSubject

    manager = get_manager()

    # Open original signal file
    with NWBHDF5IO(old_file, 'r', manager=manager) as io1:
        nwb = io1.read()
        # Creates new file
        nwb_new = NWBFile(session_description=str(nwb.session_description),
                          identifier='high gamma data',
                          session_start_time=datetime.now(tzlocal()))
        with NWBHDF5IO(new_file, mode='w', manager=manager) as io2:
            # Copy relevant fields, except Acquisition and DecompositionSeries
            #Devices
            if nwb.devices is not None:
                for aux in list(nwb.devices.keys()):
                    dev = Device(nwb.devices[aux].name)
                    nwb_new.add_device(dev)
            #Electrode groups
            if nwb.electrode_groups is not None:
                for aux in list(nwb.electrode_groups.keys()):
                    nwb_new.create_electrode_group(name=nwb.electrode_groups[aux].name,
                                                   description=nwb.electrode_groups[aux].description,
                                                   location=nwb.electrode_groups[aux].location,
                                                   device=nwb_new.get_device(nwb.electrode_groups[aux].description))
            #Electrodes
            if nwb.electrodes is not None:
                nElec = len(nwb.electrodes['x'].data[:])
                for aux in np.arange(nElec):
                    nwb_new.add_electrode(x=nwb.electrodes['x'][aux],
                                          y=nwb.electrodes['y'][aux],
                                          z=nwb.electrodes['z'][aux],
                                          imp=nwb.electrodes['imp'][aux],
                                          location=nwb.electrodes['location'][aux],
                                          filtering=nwb.electrodes['filtering'][aux],
                                          group=nwb_new.get_electrode_group(nwb.electrodes['group'][aux].name),
                                          group_name=nwb.electrodes['group_name'][aux])
                # if there are custom variables
                new_vars = list(nwb.electrodes.colnames)
                default_vars = ['x', 'y', 'z', 'imp', 'location', 'filtering', 'group', 'group_name']
                [new_vars.remove(var) for var in default_vars]
                for var in new_vars:
                    nwb_new.add_electrode_column(name=var,
                                                 description=nwb.electrodes[var].description,
                                                 data=nwb.electrodes[var].data[:])
            #Epochs
            if nwb.epochs is not None:
                nEpochs = len(nwb.epochs['start_time'].data[:])
                for i in np.arange(nEpochs):
                    nwb_new.add_epoch(start_time=nwb.epochs['start_time'].data[i],
                                      stop_time=nwb.epochs['stop_time'].data[i])
            #Institution and Lab names
            nwb_new.institution = str(nwb.institution)
            nwb_new.lab = str(nwb.lab)
            #Invalid times
            if nwb.invalid_times is not None:
                nInvalid = len(nwb.invalid_times['start_time'][:])
                for aux in np.arange(nInvalid):
                    nwb_new.add_invalid_time_interval(start_time=nwb.invalid_times['start_time'][aux],
                                                      stop_time=nwb.invalid_times['stop_time'][aux])
            #Trials
            if nwb.trials is not None:
                nTrials = len(nwb.trials['start_time'])
                for aux in np.arange(nTrials):
                    nwb_new.add_trial(start_time=nwb.trials['start_time'][aux],
                                      stop_time=nwb.trials['stop_time'][aux])
            #Session id
            if nwb.session_id is not None:
                nwb_new.session_id = nwb.session_id
            #Stimulus
            if nwb.stimulus is not None:
                for stim_name in list(nwb.stimulus.keys()):
                    stim = nwb.stimulus[stim_name]
                    ts = TimeSeries(name=stim.name,
                                    description=stim.description,
                                    data=stim.data[:],
                                    rate=stim.rate,
                                    resolution=stim.resolution,
                                    conversion=stim.conversion,
                                    starting_time=stim.starting_time,
                                    unit=stim.unit)
                    nwb_new.add_stimulus(ts)
            #Subject
            # if nwb.subject is not None:
            #     try:
            #         cortical_surfaces = CorticalSurfaces()
            #         surfaces = nwb.subject.cortical_surfaces.surfaces
            #         for sfc in list(surfaces.keys()):
            #             cortical_surfaces.create_surface(name=surfaces[sfc].name,
            #                                              faces=surfaces[sfc].faces,
            #                                              vertices=surfaces[sfc].vertices)
            #         nwb_new.subject = ECoGSubject(cortical_surfaces=cortical_surfaces,
            #                                       subject_id=nwb.subject.subject_id,
            #                                       age=nwb.subject.age,
            #                                       description=nwb.subject.description,
            #                                       genotype=nwb.subject.genotype,
            #                                       sex=nwb.subject.sex,
            #                                       species=nwb.subject.species,
            #                                       weight=nwb.subject.weight,
            #                                       date_of_birth=nwb.subject.date_of_birth)
            #     except:
            #         nwb_new.subject = Subject(age=nwb.subject.age,
            #                                   description=nwb.subject.description,
            #                                   genotype=nwb.subject.genotype,
            #                                   sex=nwb.subject.sex,
            #                                   species=nwb.subject.species,
            #                                   subject_id=nwb.subject.subject_id,
            #                                   weight=nwb.subject.weight,
            #                                   date_of_birth=nwb.subject.date_of_birth)

            #Write new file with copied fields
            io2.write(nwb_new, link_data=False)


def preprocess_raw_data(block_path, config):
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
        'CAR' - Number of channels to use in CAR (default=16)
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
            print('Created ecephys')

        # LFP: Downsampled and power line signal removed -----------------------
        if 'LFP' in nwb.modules['ecephys'].data_interfaces:    # if LFP already exists
            lfp = nwb.modules['ecephys'].data_interfaces['LFP']
            lfp_ts = nwb.modules['ecephys'].data_interfaces['LFP'].electrical_series['preprocessed']
        else: # creates LFP data interface container
            lfp = LFP()

            # Data source
            lis = list(nwb.acquisition.keys())
            for i in lis:  # Check if there is ElectricalSeries in acquisition group
                if type(nwb.acquisition[i]).__name__ == 'ElectricalSeries':
                    source = nwb.acquisition[i]
            nChannels = source.data.shape[1]

            # Downsampling
            extraBins0 = 0
            fs = source.rate
            if config['Downsample'] is not None:
                print("Downsampling signals to "+str(config['Downsample'])+" Hz.")
                print("Please wait, this might take around 30 minutes.")
                start = time.time()
                #zeros to pad to make signal lenght a power of 2
                nBins = source.data.shape[0]
                extraBins0 = 2**(np.ceil(np.log2(nBins)).astype('int')) - nBins
                extraZeros = np.zeros(extraBins0)
                rate = config['Downsample']
                #One channel at a time, to improve memory usage for long signals
                for ch in np.arange(nChannels):
                    #1e6 scaling helps with numerical accuracy
                    Xch = source.data[:,ch]*1e6
                    #Make lenght a power of 2, improves performance
                    Xch = np.append(Xch,extraZeros)
                    Xch = resample(Xch, rate, fs)
                    if ch==0:
                        X = Xch.reshape(1,-1)
                    else:
                        X = np.append(X, Xch.reshape(1,-1), axis=0)
                print('Downsampling finished in {} seconds'.format(time.time()-start))
            else:  # No downsample
                rate = fs
                X = source.data[:,:].T*1e6

            # Subtract CAR
            if config['CAR'] is not None:
                print("Computing and subtracting Common Average Reference in "+str(config['CAR'])+" channel blocks.")
                start = time.time()
                X = subtract_CAR(X, b_size=config['CAR'])
                print('CAR subtract time for {}: {} seconds'.format(block_name, time.time()-start))

            # Apply Notch filters
            if config['Notch'] is not None:
                print("Applying Notch filtering of "+str(config['Notch'])+" Hz")
                #zeros to pad to make signal lenght a power of 2
                nBins = X.shape[1]
                extraBins1 = 2**(np.ceil(np.log2(nBins)).astype('int')) - nBins
                extraZeros = np.zeros(extraBins1)
                start = time.time()
                for ch in np.arange(nChannels):
                    Xch = np.append(X[ch,:],extraZeros).reshape(1,-1)
                    Xch = linenoise_notch(Xch, rate, notch_freq=config['Notch'])
                    if ch==0:
                        X2 = Xch.reshape(1,-1)
                    else:
                        X2 = np.append(X2, Xch.reshape(1,-1), axis=0)
                print('Notch filter time for {}: {} seconds'.format(block_name, time.time()-start))

            X = np.copy(X2)
            del X2
            #Remove excess bins (because of zero padding on previous steps)
            excessBins = int(np.ceil(extraBins0*rate/fs) + extraBins1)
            X = X[:, 0:-excessBins]
            X = X.astype('float32')     # signal (nChannels,nSamples)
            X /= 1e6                    # Scales signals back to Volt

            # Add preprocessed downsampled signals as an electrical_series
            elecs_region = nwb.electrodes.create_region(name='electrodes',
                                                        region=np.arange(nChannels).tolist(),
                                                        description='')
            if config['CAR'] is None:
                car = 'None'
            else: car = str(config['CAR'])
            if config['Notch'] is None:
                notch = 'None'
            else: notch = str(config['Notch'])
            if config['Downsample'] is None:
                downs = 'No'
            else: downs = 'Yes'
            config_comment = 'CAR:'+car+', Notch:'+notch+', Downsampled:'+downs
            lfp_ts = lfp.create_electrical_series(name='preprocessed',
                                                  data=X.T,
                                                  #electrodes=elecs_region,
                                                  electrodes=source.electrodes,
                                                  rate=rate,
                                                  description='',
                                                  comments=config_comment)
            ecephys_module.add_data_interface(lfp)

            # Write LFP to NWB file
            io.write(nwb)
            print('LFP saved in '+block_path)


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

        # Apply Hilbert transform ----------------------------------------------
        print('Running Spectral Decomposition...')
        start = time.time()
        for ch in np.arange(nChannels):
            Xch = lfp.data[:,ch]*1e6       # 1e6 scaling helps with numerical accuracy
            Xch = Xch.reshape(1,-1)
            Xch = Xch.astype('float32')     # signal (nChannels,nSamples)
            X_fft_h = None
            for ii, (bp0, bp1) in enumerate(zip(band_param_0, band_param_1)):
                kernel = gaussian(Xch, rate, bp0, bp1)
                X_analytic, X_fft_h = hilbert_transform(Xch, rate, kernel, phase=None, X_fft_h=X_fft_h)
                Xp[ii, ch, :] = abs(X_analytic).astype('float32')
        print('Spectral Decomposition finished in {} seconds'.format(time.time()-start))

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
        print('Spectral decomposition saved in '+block_path)


def high_gamma_estimation(block_path, bands_vals, new_file=''):
    """
    Takes preprocessed LFP data and calculates High-Gamma power from the
    averaged power of standard Hilbert transform on 70~150 Hz bands.

    Parameters
    ----------
    block_path : str
        subject file path
    bands_vals : [2,nBands] numpy array with Gaussian filter parameters, where:
        bands_vals[0,:] = filter centers [Hz]
        bands_vals[1,:] = filter sigmas [Hz]
    new_file : str
        if this argument is of form 'path/to/new_file.nwb', High Gamma power
        will be saved in a new file. If it is an empty string, '', High Gamma
        power will be saved in the current NWB file.

    Returns
    -------
    Saves High Gamma power (TimeSeries) in the current or new NWB file.
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

        # Apply Hilbert transform ----------------------------------------------
        print('Running High Gamma estimation...')
        start = time.time()
        for ch in np.arange(nChannels):
            Xch = lfp.data[:,ch]*1e6       # 1e6 scaling helps with numerical accuracy
            Xch = Xch.reshape(1,-1)
            Xch = Xch.astype('float32')     # signal (nChannels,nSamples)
            X_fft_h = None
            for ii, (bp0, bp1) in enumerate(zip(band_param_0, band_param_1)):
                kernel = gaussian(Xch, rate, bp0, bp1)
                X_analytic, X_fft_h = hilbert_transform(Xch, rate, kernel, phase=None, X_fft_h=X_fft_h)
                Xp[ii, ch, :] = abs(X_analytic).astype('float32')
        print('High Gamma estimation finished in {} seconds'.format(time.time()-start))

        # data: (ndarray) dims: num_times * num_channels * num_bands
        Xp = np.swapaxes(Xp,0,2)
        HG = np.mean(Xp, 2)   #average of high gamma bands

        hg = TimeSeries(name='high_gamma',
                        data=HG,
                        rate=rate,
                        unit='V**2/Hz',
                        description='')

        # Storage of High Gamma on NWB file -----------------------------
        if new_file=='':  #on current file
            ecephys_module = nwb.modules['ecephys']
            ecephys_module.add_data_interface(hg)
            io.write(nwb)
            print('High Gamma power saved in '+block_path)
        else:           #on new file
            with NWBHDF5IO(new_file, 'r+') as io_new:
                nwb_new = io_new.read()
                # creates ecephys ProcessingModule
                ecephys_module = ProcessingModule(name='ecephys',
                                                  description='Extracellular electrophysiology data.')
                # Add module to NWB file
                nwb_new.add_processing_module(ecephys_module)
                ecephys_module.add_data_interface(hg)
                io_new.write(nwb_new)
                print('High Gamma power saved in '+new_file)
