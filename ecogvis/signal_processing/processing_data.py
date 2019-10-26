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
from ecogvis.functions.nwb_copy_file import nwb_copy_file


def processing_data(path, subject, blocks, mode=None, config=None, new_file=''):
    for block in blocks:
        block_path = os.path.join(path, '{}_B{}.nwb'.format(subject, block))
        if new_file != '':
            make_new_nwb(old_file=block_path, new_file=new_file)

        if mode == 'preprocess':
            preprocess_raw_data(block_path, config=config)
        elif mode == 'decomposition':
            spectral_decomposition(block_path, bands_vals=config)
        elif mode == 'high_gamma':
            high_gamma_estimation(block_path, bands_vals=config, new_file=new_file)


def make_new_nwb(old_file, new_file, cp_objs=None):
    """
    Copy all fields, as defined by cp_objs, from current NWB file to new NWB
    file.

    Parameters
    ----------
    old_file : str, path
        String such as '/path/to/old_file.nwb'.
    new_file : str, path
        String such as '/path/to/new_file.nwb'.
    cp_objs : dictionary
        Dictionary of objectives to copy from the current NWB file to the
        new NWB file. If not given, the defaults will be set (defined
        below). For 'acquisition', 'stimulus', and 'ecephys' fields, if the
        value is defined as 'default', the default fields from those fields
        will be copied. Otherwise, if specified as a list of strings,
        those specific fields will be copied. If something is not to be
        copied, it should be left out of the cp_objs dictionary.
    """

    # Dictionary for copy_nwb
    if cp_objs is None:
        cp_objs = {
            'institution': True,
            'lab': True,
            'session': True,
            'devices': True,
            'electrode_groups': True,
            'electrodes': True,
            'intervals': True,
            'stimulus': True,
            'subject': True,
            'acquisition': 'default'
        }

    # Open original signal file
    with NWBHDF5IO(old_file, 'r', load_namespaces=True) as io:
        nwb_old = io.read()

        if ('acquisition' in cp_objs) and \
                (cp_objs['acquisition'] == 'default'):
            # If 'acquisition' variables are in cp_objs but not defined,
            # default: Exclude raw signals, keep other acquisition
            acq_vars = list(nwb_old.acquisition.keys())
            if 'ElectricalSeries' in acq_vars:
                acq_vars.remove('ElectricalSeries')
            cp_objs['acquisition'] = acq_vars

        if ('ecephys' in cp_objs) and \
                (cp_objs['ecephys'] == 'default'):
            # If 'ecephys' variables are in cp_objs but not defined, default:
            # Exclude existing high_gamma, keep other processing modules
            ece_vars = list(nwb_old.processing['ecephys'].data_interfaces.keys())
            if 'high_gamma' in ece_vars:
                ece_vars.remove('high_gamma')
            cp_objs['ecephys'] = ece_vars

    nwb_copy_file(old_file, new_file, cp_objs=cp_objs)


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
        'referencing' - tuple specifying electrode referencing (type, options)
            ('CAR', N_channels_per_group)
            ('CMR', N_channels_per_group)
            ('bipolar', INCLUDE_OBLIQUE_NBHD)
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

    with NWBHDF5IO(block_path, 'r+', load_namespaces=True) as io:
        nwb = io.read()

        # Storage of processed signals on NWB file ----------------------------
        if 'ecephys' in nwb.processing:
            ecephys_module = nwb.processing['ecephys']
        else:   # creates ecephys ProcessingModule
            ecephys_module = ProcessingModule(
                name='ecephys',
                description='Extracellular electrophysiology data.'
            )
            # Add module to NWB file
            nwb.add_processing_module(ecephys_module)
            print('Created ecephys')

        # LFP: Downsampled and power line signal removed ----------------------
        if 'LFP' in nwb.processing['ecephys'].data_interfaces:
            ######
            # What's the point of this?  Nothing is done with these vars...
            lfp = nwb.processing['ecephys'].data_interfaces['LFP']
            lfp_ts = nwb.processing['ecephys'].data_interfaces[
                'LFP'].electrical_series['preprocessed']
            ######
        else:  # creates LFP data interface container
            lfp = LFP()

            # Data source
            source_list = [acq for acq in nwb.acquisition.values()
                           if type(acq) == ElectricalSeries]
            assert len(source_list) == 1, (
                'Not precisely one ElectricalSeries in acquisition!')
            source = source_list[0]
            nChannels = source.data.shape[1]

            # Downsampling
            if config['Downsample'] is not None:
                print("Downsampling signals to "+str(config['Downsample'])+" Hz.")
                print("Please wait, this might take around 30 minutes.")
                start = time.time()
                # zeros to pad to make signal length a power of 2
                nBins = source.data.shape[0]
                extraBins0 = 2**(np.ceil(np.log2(nBins)).astype('int')) - nBins
                extraZeros = np.zeros(extraBins0)
                rate = config['Downsample']

                # malloc
                T = int(np.ceil((nBins + extraBins0)*rate/source.rate))
                X = np.zeros((source.data.shape[1], T))

                # One channel at a time, to improve memory usage for long signals
                for ch in np.arange(nChannels):
                    # 1e6 scaling helps with numerical accuracy
                    Xch = source.data[:, ch]*1e6
                    # Make length a power of 2, improves performance
                    Xch = np.append(Xch, extraZeros)
                    X[ch, :] = resample(Xch, rate, source.rate)
                print('Downsampling finished in {} seconds'.format(
                    time.time()-start))
            else:  # No downsample
                extraBins0 = 0
                rate = source.rate
                X = source.data[()].T*1e6

            # re-reference the (scaled by 1e6!) data
            electrodes = source.electrodes
            if config['referencing'] is not None:
                if config['referencing'][0] == 'CAR':
                    print("Computing and subtracting Common Average Reference in "
                          + str(config['referencing'][1])+" channel blocks.")
                    start = time.time()
                    X = subtract_CAR(X, b_size=config['referencing'][1])
                    print('CAR subtract time for {}: {} seconds'.format(
                        block_name, time.time()-start))
                elif config['referencing'][0] == 'bipolar':
                    X, bipolarTable, electrodes = get_bipolar_referenced_electrodes(
                        X, electrodes, rate, grid_step=1)

                    # add data interface for the metadata for saving
                    ecephys_module.add_data_interface(bipolarTable)
                    print('bipolarElectrodes stored for saving in '+block_path)
                else:
                    print('UNRECOGNIZED REFERENCING SCHEME; ', end='')
                    print('SKIPPING REFERENCING!')

            # Apply Notch filters
            if config['Notch'] is not None:
                print("Applying notch filtering of "+str(config['Notch'])+" Hz")
                # zeros to pad to make signal lenght a power of 2
                nBins = X.shape[1]
                extraBins1 = 2**(np.ceil(np.log2(nBins)).astype('int')) - nBins
                extraZeros = np.zeros(extraBins1)
                start = time.time()
                for ch in np.arange(nChannels):
                    Xch = np.append(X[ch, :], extraZeros).reshape(1, -1)
                    Xch = linenoise_notch(Xch, rate, notch_freq=config['Notch'])
                    if ch == 0:
                        X2 = Xch.reshape(1, -1)
                    else:
                        X2 = np.append(X2, Xch.reshape(1, -1), axis=0)
                print('Notch filter time for {}: {} seconds'.format(
                    block_name, time.time()-start))

                X = np.copy(X2)
                del X2
            else:
                extraBins1 = 0

            # Remove excess bins (because of zero padding on previous steps)
            excessBins = int(np.ceil(extraBins0*rate/source.rate) + extraBins1)
            X = X[:, 0:-excessBins]
            X = X.astype('float32')     # signal (nChannels,nSamples)
            X /= 1e6                    # Scales signals back to volts

            # Add preprocessed downsampled signals as an electrical_series
            referencing = 'None' if config['referencing'] is None else config[
                'referencing'][0]
            notch = 'None' if config['Notch'] is None else str(config['Notch'])
            downs = 'No' if config['Downsample'] is None else 'Yes'
            config_comment = (
                'referencing:' + referencing
                + ',Notch:' + notch
                + ', Downsampled:' + downs
            )

            # create an electrical series for the LFP and store it in lfp
            lfp_ts = lfp.create_electrical_series(
                name='preprocessed',
                data=X.T,
                electrodes=electrodes,
                rate=rate,
                description='',
                comments=config_comment
            )
            ecephys_module.add_data_interface(lfp)

            # Write LFP to NWB file
            io.write(nwb)
            print('LFP saved in '+block_path)


def get_bipolar_referenced_electrodes(
    X, electrodes, rate, grid_size=None, grid_step=1
):
    '''
    Bipolar referencing of electrodes according to the scheme of Dr. John Burke

    Each electrode (with obvious exceptions at the edges) yields two bipolar-
    referenced channels, one for the "right" and one for the "below" neighbors.
    These are returned as an ElectricalSeries.

    Input arguments:
    --------
    X:
        numpy array containing (raw) electrode traces (Nelectrodes x T)
    electrodes:
        DynamicTableRegion containing the metadata for the electrodes whose
        traces are in X
    rate:
        sampling rate of X; for storage in ElectricalSeries
    grid_size:
        numpy array with the two dimensions of the grid (2, )

    Returns:
    --------
    bipolarElectrodes:
        ElectricalSeries containing the bipolar-referenced (pseudo) electrodes
        and associated metadata.  (NB that a, e.g., 16x16 grid yields 960 of
        these pseudo-electrodes.)
    '''

    # set mutable default argument(s)
    if grid_size is None:
        grid_size = np.array([16, 16])

    # malloc
    elec_layout = np.arange(np.prod(grid_size)-1, -1, -1).reshape(grid_size).T
    elec_layout = elec_layout[::grid_step, ::grid_step]
    grid_size = elec_layout.T.shape  # in case grid_step > 1
    Nchannels = 2*np.prod(grid_size) - np.sum(grid_size)
    XX = np.zeros((Nchannels, X.shape[1]))

    # create a new dynamic table to hold the metadata
    column_names = ['x', 'y', 'z', 'imp', 'location', 'label', 'bad']
    columns = [
        VectorData(
            name=name,
            description=electrodes.table[name].description)
        for name in column_names
    ]
    bipolarTable = DynamicTable(
        name='bipolar-referenced metadata',
        description=('pseudo-channels derived via John Burke style'
                     ' bipolar referencing'),
        colnames=column_names,
        columns=columns,
    )

    # compute bipolar-ref'd channel and add a new row of metadata to table
    def add_new_channel(iChannel, iElectrode, jElectrode):
        jElectrode = int(jElectrode)

        # "bipolar referencing": the difference of neighboring electrodes
        XX[iChannel, :] = X[iElectrode, :] - X[jElectrode, :]

        # add a row to the table for this new pseudo-electrode
        bipolarTable.add_row(
            {
                'location': '_'.join({
                    electrodes.table['location'][iElectrode],
                    electrodes.table['location'][jElectrode]
                }),
                'label': '-'.join([
                    electrodes.table['label'][iElectrode],
                    electrodes.table['label'][jElectrode]
                ]),
                'bad': (
                    electrodes.table['bad'][iElectrode] or
                    electrodes.table['bad'][jElectrode]
                ),
                **{name: electrodes.table[name][iElectrode]
                   for name in ['x', 'y', 'z', 'imp']},
            }
        )
        return iChannel+1

    iChannel = 0

    # loop across columns and rows (remembering that grid is transposed)
    for i in range(grid_size[1]):
        for j in range(grid_size[0]):
            if j < grid_size[0]-1:
                iChannel = add_new_channel(
                    iChannel, elec_layout[i, j], elec_layout[i, j+1])
            if i < grid_size[1]-1:
                iChannel = add_new_channel(
                    iChannel, elec_layout[i, j], elec_layout[i+1, j])

    # create one big region for the entire table
    bipolarTableRegion = bipolarTable.create_region(
        'electrodes', [i for i in range(Nchannels)], 'all bipolar electrodes')

    return XX, bipolarTable, bipolarTableRegion


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
    band_param_0 = bands_vals[0, :]
    band_param_1 = bands_vals[1, :]

    with NWBHDF5IO(block_path, 'r+', load_namespaces=True) as io:
        nwb = io.read()
        lfp = nwb.processing['ecephys'].data_interfaces['LFP'].electrical_series['preprocessed']
        rate = lfp.rate

        nBands = len(band_param_0)
        nSamples = lfp.data.shape[0]
        nChannels = lfp.data.shape[1]
        Xp = np.zeros((nBands, nChannels, nSamples))  #power (nBands,nChannels,nSamples)

        # Apply Hilbert transform ---------------------------------------------
        print('Running Spectral Decomposition...')
        start = time.time()
        for ch in np.arange(nChannels):
            Xch = lfp.data[:, ch]*1e6       # 1e6 scaling helps with numerical accuracy
            Xch = Xch.reshape(1, -1)
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
        band_param_0V = VectorData(
            name='filter_param_0',
            description='frequencies for bandpass filters',
            data=band_param_0
        )
        band_param_1V = VectorData(
            name='filter_param_1',
            description='frequencies for bandpass filters',
            data=band_param_1
        )
        bandsTable = DynamicTable(
            name='bands',
            description='Series of filters used for Hilbert transform.',
            columns=[band_param_0V, band_param_1V],
            colnames=['filter_param_0', 'filter_param_1']
        )
        decs = DecompositionSeries(
            name='DecompositionSeries',
            data=Xp,
            description='Analytic amplitude estimated with Hilbert transform.',
            metric='amplitude',
            unit='V',
            bands=bandsTable,
            rate=rate,
            source_timeseries=lfp
        )

        # Storage of spectral decomposition on NWB file ------------------------
        ecephys_module = nwb.processing['ecephys']
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
    band_param_0 = bands_vals[0, :]
    band_param_1 = bands_vals[1, :]

    with NWBHDF5IO(block_path, 'r+', load_namespaces=True) as io:
        nwb = io.read()
        lfp = nwb.processing['ecephys'].data_interfaces[
            'LFP'].electrical_series['preprocessed']
        rate = lfp.rate

        nBands = len(band_param_0)
        nSamples = lfp.data.shape[0]
        nChannels = lfp.data.shape[1]
        Xp = np.zeros((nBands, nChannels, nSamples))  #power (nBands,nChannels,nSamples)

        # Apply Hilbert transform ---------------------------------------------
        print('Running High Gamma estimation...')
        start = time.time()
        for ch in np.arange(nChannels):
            Xch = lfp.data[:, ch]*1e6       # 1e6 scaling helps with numerical accuracy
            Xch = Xch.reshape(1, -1)
            Xch = Xch.astype('float32')     # signal (nChannels,nSamples)
            X_fft_h = None
            for ii, (bp0, bp1) in enumerate(zip(band_param_0, band_param_1)):
                kernel = gaussian(Xch, rate, bp0, bp1)
                X_analytic, X_fft_h = hilbert_transform(
                    Xch, rate, kernel, phase=None, X_fft_h=X_fft_h)
                Xp[ii, ch, :] = abs(X_analytic).astype('float32')
        print('High Gamma estimation finished in {} seconds'.format(
            time.time()-start))

        # data: (ndarray) dims: num_times * num_channels * num_bands
        Xp = np.swapaxes(Xp, 0, 2)
        HG = np.mean(Xp, 2)   # average of high gamma bands

        # Storage of High Gamma on NWB file -----------------------------
        if new_file == '' or new_file is None:  # on current file
            # make electrodes table
            nElecs = HG.shape[1]
            ecephys_module = nwb.processing['ecephys']

            # first check for a table among the file's data_interfaces
            ####
            if lfp.electrodes.table.name in ecephys_module.data_interfaces:
                LFP_dynamic_table = ecephys_module.data_interfaces[
                    lfp.electrodes.table.name]
            else:
                # othewise use the electrodes as the table
                LFP_dynamic_table = nwb.electrodes
            ####
            elecs_region = LFP_dynamic_table.create_region(
                name='electrodes',
                region=[i for i in range(nChannels)],
                description='all electrodes'
            )
            hg = ElectricalSeries(
                name='high_gamma',
                data=HG,
                electrodes=elecs_region,
                rate=rate,
                description=''
            )

            ecephys_module.add_data_interface(hg)
            io.write(nwb)
            print('High Gamma power saved in '+block_path)
        else:  # on new file
            with NWBHDF5IO(new_file, 'r+', load_namespaces=True) as io_new:
                nwb_new = io_new.read()
                # make electrodes table
                nElecs = HG.shape[1]
                elecs_region = nwb_new.electrodes.create_region(
                    name='electrodes',
                    region=np.arange(nElecs).tolist(),
                    description='all electrodes'
                )
                hg = ElectricalSeries(
                    name='high_gamma',
                    data=HG,
                    electrodes=elecs_region,
                    rate=rate,
                    description=''
                )

                try:      # if ecephys module already exists
                    ecephys_module = nwb_new.processing['ecephys']
                except:   # creates ecephys ProcessingModule
                    ecephys_module = ProcessingModule(name='ecephys',
                                                      description='Extracellular electrophysiology data.')
                    nwb_new.add_processing_module(ecephys_module)

                ecephys_module.add_data_interface(hg)
                io_new.write(nwb_new)
                print('High Gamma power saved in '+new_file)
