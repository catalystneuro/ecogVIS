# -*- coding: utf-8 -*-
"""
Convert ECoG to NWB.

:Author: Ben Dichter, Jessie R. Liu
Modified by Luiz Tauffer on May 30, 2020
"""
from __future__ import print_function
import os
from datetime import datetime
from os import path
from pathlib import Path

import numpy as np
import pandas as pd
from hdmf.backends.hdf5 import H5DataIO
from nwbext_ecog import ECoGSubject
from pynwb import NWBFile, TimeSeries, get_manager, NWBHDF5IO
from pynwb.ecephys import ElectricalSeries, LFP
import scipy.io as sio
from scipy.io.wavfile import read as wavread
from tqdm import tqdm

from ecogvis.functions.htk_to_nwb.HTK import readHTK


# get_manager must come after dynamic imports
manager = get_manager()


def get_analog(anin_path, num=1):
    """
    Load analog data. Try:
    1) analog[num].wav
    2) ANIN[num].htk

    Parameters
    ----------
    blockpath: str
    num: int

    Returns
    -------
    fs, data
    """
    wav_path = path.join(anin_path, 'analog' + str(num) + '.wav')
    if os.path.isfile(wav_path):
        rate, data = wavread(wav_path)
        return float(rate), np.array(data, dtype=float)
    htk_path = path.join(anin_path, 'ANIN' + str(num) + '.htk')
    if os.path.isfile(htk_path):
        htk_out = readHTK(htk_path, scale_s_rate=True)
        return htk_out['sampling_rate'], htk_out['data'].ravel()
    print('no analog path found for ' + str(num))
    return None, None


def readhtks(htk_path, elecs=None, use_tqdm=True):
    # First fix the order of htk files
    all_files = np.array([f for f in Path(htk_path).glob('*.htk')])
    numbers = [f.name.split('.')[0].split('Wav')[1] for f in Path(htk_path).glob('*.htk')]
    new_numbers = [n[0] + '0' + n[1] if len(n) == 2 else n for n in numbers]
    sorted_index = np.argsort(new_numbers)
    sorted_files = all_files[sorted_index]
    # Load data from files in correct order
    data = []
    if use_tqdm:
        this_iter = tqdm(sorted_files, desc='reading electrodes')
    else:
        this_iter = sorted_files
    for i in this_iter:
        htk = readHTK(i, scale_s_rate=True)
        data.append(htk['data'])
    data = np.stack(data)
    if len(data.shape) == 3:
        data = data.transpose([2, 0, 1])

    rate = htk['sampling_rate']

    return rate, data.squeeze()


def get_bad_elecs(blockpath):
    bad_channels_file = os.path.join(blockpath, 'Artifacts', 'badChannels.txt')

    # I think bad channels is 1-indexed but I'm not sure
    if os.path.isfile(bad_channels_file) and os.stat(
            bad_channels_file).st_size:
        dat = pd.read_csv(bad_channels_file, header=None, delimiter=' ',
                          engine='python')
        bad_elecs_inds = dat.values.ravel() - 1
        bad_elecs_inds = bad_elecs_inds[np.isfinite(bad_elecs_inds)]
    else:
        bad_elecs_inds = []

    return bad_elecs_inds


def elecs_to_electrode_table(nwbfile, elecspath):
    """
    Takes an NWB file and the elecs .mat file path, loads the anatomical and
    location information for each electrode,
    and writes this information to the NWB file.

    Parameters:
    -----------
    nwbfile : object
        An NWB file object.
    elecspath : str
        Path to the TDT_elecs_all.mat file for this subject. First, second,
        and third columns of the key 'elecmatrix'
        should be x, y, and z coordinates, respectively. For the 'anatomy'
        field, second column should be the full electrode label and the
        fourth column should be the anatomical location name.

    Returns:
    --------
    nwb_file : object
        The edited NWB file with the added electrode information.
    """

    # Get anatomical and location information for electrodes.
    elec_mat = sio.loadmat(elecspath)
    labels = elec_mat['anatomy'][:, 1]
    location = elec_mat['anatomy'][:, 3]
    x = elec_mat['elecmatrix'][:, 0]
    y = elec_mat['elecmatrix'][:, 1]
    z = elec_mat['elecmatrix'][:, 2]

    # Get MNI warped electrode coordinates.
    if Path(elecspath.as_posix().split('.')[0] + '_warped.mat').is_file():
        elec_mat_warped = sio.loadmat(elecspath.split('.')[0] + '_warped.mat')
        x_warped = elec_mat_warped['elecmatrix'][:, 0]
        y_warped = elec_mat_warped['elecmatrix'][:, 1]
        z_warped = elec_mat_warped['elecmatrix'][:, 2]
    else:
        print('No warped electrode information found...filling with zeros.')
        x_warped = np.zeros_like(x)
        y_warped = np.zeros_like(y)
        z_warped = np.zeros_like(z)

    # Define electrode device label names.
    group_labels = []
    for current_group in labels:
        name = current_group[0].rstrip('0123456789')
        # Replace 'NaN' for 'null'
        if name == 'NaN':
            name = 'null'
        group_labels.append(name)

    # Get the list of unique electrode device label names
    unique_group_indexes = np.unique(group_labels, return_index=True)[1]
    unique_group_labels = [group_labels[f] for f in sorted(unique_group_indexes)]

    # Add additional columns to the electodes table.
    nwbfile.add_electrode_column('label', 'label of electrode')
    nwbfile.add_electrode_column('bad', 'electrode identified as too noisy')
    nwbfile.add_electrode_column('x_warped', 'x warped onto cvs_avg35_inMNI152')
    nwbfile.add_electrode_column('y_warped', 'y warped onto cvs_avg35_inMNI152')
    nwbfile.add_electrode_column('z_warped', 'z warped onto cvs_avg35_inMNI152')
    nwbfile.add_electrode_column('null', 'if not connected to real electrode')

    for group_label in unique_group_labels:
        # Get region name and device label for the group.
        if 'Depth' in group_label:
            brain_area = group_label.split('Depth')[0]
        elif 'Strip' in group_label:
            brain_area = group_label.split('Strip')[0]
        elif 'Grid' in group_label:
            brain_area = group_label.split('Grid')[0]
        elif 'Pole' in group_label:
            brain_area = group_label.split('Pole')[0]
        elif 'HeschlsGyrus' in group_label:
            brain_area = 'HeschlsGyrus'
        elif 'null' in group_label:
            brain_area = 'null'
        else:
            brain_area = 'other'

        # Create electrode device (same as the group).
        device = nwbfile.create_device(group_label)

        # Create electrode group with name, description, device object,
        # and general location.
        electrode_group = nwbfile.create_electrode_group(
            name='{} electrodes'.format(group_label),
            description='{}'.format(group_label),
            device=device,
            location=str(brain_area)
        )

        # Loop through the number of electrodes in this electrode group
        elec_nums = np.where(np.array(group_labels) == group_label)[0]
        for elec_num in elec_nums:
            # Add the electrode information to the table.
            elec_location = location[elec_num]
            if len(elec_location) == 0:
                # If no label is recorded for this electrode, set it to null
                elec_location = 'null'
                is_null = True
            else:
                elec_location = elec_location[0]
                is_null = False

            nwbfile.add_electrode(
                id=elec_num,
                x=x[elec_num],
                y=y[elec_num],
                z=z[elec_num],
                imp=np.nan,
                x_warped=x_warped[elec_num],
                y_warped=y_warped[elec_num],
                z_warped=z_warped[elec_num],
                location=str(elec_location),
                filtering='filtering',
                group=electrode_group,
                label=str(labels[elec_num][0]),
                bad=False,
                null=is_null,
            )

    return nwbfile


def chang2nwb(blockpath, out_file_path=None, save_to_file=False, htk_config=None):
    """
    Parameters
    ----------
    blockpath: str
    out_file_path: None | str
        if None, output = [blockpath]/[blockname].nwb
    save_to_file : bool
        If True, saves to file. If False, just returns nwbfile object
    htk_config : dict
        Dictionary cotaining HTK conversion paths and options. Example:
        {
            ecephys_path: 'path_to/ecephys_htk_files',
            ecephys_type: 'raw', 'preprocessed' or 'high_gamma',
            analog_path: 'path_to/analog_htk_files',
            anin1: {present: True, name: 'microphone', type: 'acquisition'},
            anin2: {present: True, name: 'speaker1', type: 'stimulus'},
            anin3: {present: False, name: 'speaker2', type: 'stimulus'},
            anin4: {present: False, name: 'custom', type: 'acquisition'},
            metadata: metadata,
            electrodes_file: electrodes_file
        }

    Returns
    -------
    """

    metadata = {}

    if htk_config is None:
        blockpath = Path(blockpath)
    else:
        blockpath = Path(htk_config['ecephys_path'])
        metadata = htk_config['metadata']
    blockname = blockpath.parent.name
    subject_id = blockpath.parent.parent.name[2:]

    if out_file_path is None:
        out_file_path = blockpath.resolve().parent / ''.join(['EC', subject_id, '_', blockname, '.nwb'])

    # file paths
    ecog_path = blockpath
    anin_path = htk_config['analog_path']
    bad_time_file = path.join(blockpath, 'Artifacts', 'badTimeSegments.mat')

    # Create the NWB file object
    nwbfile_dict = {
        'session_description': blockname,
        'identifier': blockname,
        'session_start_time': datetime.now().astimezone(),
        'institution': 'University of California, San Francisco',
        'lab': 'Chang Lab'
    }
    if 'NWBFile' in metadata:
        nwbfile_dict.update(metadata['NWBFile'])
    nwbfile = NWBFile(**nwbfile_dict)

    # Read electrophysiology data from HTK files
    print('reading htk acquisition...', flush=True)
    ecog_rate, data = readhtks(ecog_path)
    data = data.squeeze()
    print('done', flush=True)

    # Get electrodes info from mat file
    if htk_config['electrodes_file'] is not None:
        nwbfile = elecs_to_electrode_table(
            nwbfile=nwbfile,
            elecspath=htk_config['electrodes_file'],
        )
        n_electrodes = nwbfile.electrodes[:].shape[0]
        all_elecs = list(range(n_electrodes))
        elecs_region = nwbfile.create_electrode_table_region(
            all_elecs,
            'ECoG electrodes on brain'
        )
    else:  # Get electrodes info from metadata file
        ecephys_dict = {
            'Device': [{'name': 'auto_device'}],
            'ElectricalSeries': [{'name': 'ECoG', 'description': 'description'}],
            'ElectrodeGroup': [{'name': 'auto_group', 'description': 'auto_group',
                                'location': 'location', 'device': 'auto_device'}]
        }
        if 'Ecephys' in metadata:
            ecephys_dict.update(metadata['Ecephys'])

        # Create devices
        for dev in ecephys_dict['Device']:
            device = nwbfile.create_device(dev['name'])

        # Electrode groups
        for el_grp in ecephys_dict['ElectrodeGroup']:
            device = nwbfile.devices[el_grp['device']]
            electrode_group = nwbfile.create_electrode_group(
                name=el_grp['name'],
                description=el_grp['description'],
                location=el_grp['location'],
                device=device
            )

        # Electrodes table
        n_electrodes = data.shape[1]
        nwbfile.add_electrode_column('label', 'label of electrode')
        nwbfile.add_electrode_column('bad', 'electrode identified as too noisy')
        nwbfile.add_electrode_column('x_warped', 'x warped onto cvs_avg35_inMNI152')
        nwbfile.add_electrode_column('y_warped', 'y warped onto cvs_avg35_inMNI152')
        nwbfile.add_electrode_column('z_warped', 'z warped onto cvs_avg35_inMNI152')
        nwbfile.add_electrode_column('null', 'if not connected to real electrode')
        bad_elecs_inds = get_bad_elecs(blockpath)
        for elec_counter in range(n_electrodes):
            bad = elec_counter in bad_elecs_inds
            nwbfile.add_electrode(
                id=elec_counter + 1,
                x=np.nan,
                y=np.nan,
                z=np.nan,
                imp=np.nan,
                x_warped=np.nan,
                y_warped=np.nan,
                z_warped=np.nan,
                location='',
                filtering='none',
                group=electrode_group,
                label='',
                bad=bad,
                null=False,
            )

        all_elecs = list(range(n_electrodes))
        elecs_region = nwbfile.create_electrode_table_region(
            all_elecs,
            'ECoG electrodes on brain'
        )

    # Stores HTK electrophysiology data as raw, preprocessed or high gamma
    if htk_config['ecephys_type'] == 'raw':
        ecog_es = ElectricalSeries(name='ECoG',
                                   data=H5DataIO(data[:, 0:n_electrodes], compression='gzip'),
                                   electrodes=elecs_region,
                                   rate=ecog_rate,
                                   description='all Wav data')
        nwbfile.add_acquisition(ecog_es)
    elif htk_config['ecephys_type'] == 'preprocessed':
        lfp = LFP()
        ecog_es = ElectricalSeries(name='preprocessed',
                                   data=H5DataIO(data[:, 0:n_electrodes], compression='gzip'),
                                   electrodes=elecs_region,
                                   rate=ecog_rate,
                                   description='all Wav data')
        lfp.add_electrical_series(ecog_es)
        # Creates the ecephys processing module
        ecephys_module = nwbfile.create_processing_module(
            name='ecephys',
            description='preprocessed electrophysiology data'
        )
        ecephys_module.add_data_interface(lfp)
    elif htk_config['ecephys_type'] == 'high_gamma':
        ecog_es = ElectricalSeries(name='high_gamma',
                                   data=H5DataIO(data[:, 0:n_electrodes], compression='gzip'),
                                   electrodes=elecs_region,
                                   rate=ecog_rate,
                                   description='all Wav data')
        # Creates the ecephys processing module
        ecephys_module = nwbfile.create_processing_module(
            name='ecephys',
            description='preprocessed electrophysiology data'
        )
        ecephys_module.add_data_interface(ecog_es)

    # Add ANIN 1
    if htk_config['anin1']['present']:
        fs, data = get_analog(anin_path, 1)
        ts = TimeSeries(
            name=htk_config['anin1']['name'],
            data=data,
            unit='NA',
            rate=fs,
        )
        if htk_config['anin1']['type'] == 'acquisition':
            nwbfile.add_acquisition(ts)
        else:
            nwbfile.add_stimulus(ts)
        print('ANIN1 saved with name "', htk_config['anin1']['name'], '" in ',
              htk_config['anin1']['type'])

    # Add ANIN 2
    if htk_config['anin2']['present']:
        fs, data = get_analog(anin_path, 2)
        ts = TimeSeries(
            name=htk_config['anin2']['name'],
            data=data,
            unit='NA',
            rate=fs,
        )
        if htk_config['anin2']['type'] == 'acquisition':
            nwbfile.add_acquisition(ts)
        else:
            nwbfile.add_stimulus(ts)
        print('ANIN2 saved with name "', htk_config['anin2']['name'], '" in ',
              htk_config['anin2']['type'])

    # Add ANIN 3
    if htk_config['anin3']['present']:
        fs, data = get_analog(anin_path, 3)
        ts = TimeSeries(
            name=htk_config['anin3']['name'],
            data=data,
            unit='NA',
            rate=fs,
        )
        if htk_config['anin3']['type'] == 'acquisition':
            nwbfile.add_acquisition(ts)
        else:
            nwbfile.add_stimulus(ts)
        print('ANIN3 saved with name "', htk_config['anin3']['name'], '" in ',
              htk_config['anin3']['type'])

    # Add ANIN 4
    if htk_config['anin4']['present']:
        fs, data = get_analog(anin_path, 4)
        ts = TimeSeries(
            name=htk_config['anin4']['name'],
            data=data,
            unit='NA',
            rate=fs,
        )
        if htk_config['anin4']['type'] == 'acquisition':
            nwbfile.add_acquisition(ts)
        else:
            nwbfile.add_stimulus(ts)
        print('ANIN4 saved with name "', htk_config['anin4']['name'], '" in ',
              htk_config['anin4']['type'])

    # Add bad time segments
    if os.path.exists(bad_time_file) and os.stat(bad_time_file).st_size:
        bad_time = sio.loadmat(bad_time_file)['badTimeSegments']
        for row in bad_time:
            nwbfile.add_invalid_time_interval(start_time=row[0],
                                              stop_time=row[1],
                                              tags=('ECoG artifact',),
                                              timeseries=ecog_es)

    # Subject
    subject_dict = {'subject_id': subject_id}
    if 'Subject' in metadata:
        subject_dict.update(metadata['Subject'])
    subject = ECoGSubject(**subject_dict)
    nwbfile.subject = subject

    if save_to_file:
        print('Saving HTK content to NWB file...')
        # Export the NWB file
        with NWBHDF5IO(str(out_file_path), manager=manager, mode='w') as io:
            io.write(nwbfile)

        # read check
        with NWBHDF5IO(str(out_file_path), manager=manager, mode='r') as io:
            io.read()
        print('NWB file saved: ', str(out_file_path))

    return nwbfile, out_file_path, subject_id, blockname
