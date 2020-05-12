# -*- coding: utf-8 -*-
"""
Convert raw TDT tanks of ECoG data to NWB files. Adapted from
https://github.com/bendichter/to_nwb/blob/master/to_nwb/chang/TDT2NWB.m.
Converts a single TDT block of raw data and outputs a single NWB file with
only the raw data. Utilizes base paths that should be in a config file
located at the user's home directory under ~/.config/NWBconf.json.

:Author: Jessie R. Liu
"""

# Standard libraries.
import json
import os
from glob import glob

# Third party libraries.
import numpy as np
import pytz
import scipy.io as sio
import tdt
from datetime import datetime
from nwbext_ecog import CorticalSurfaces, ECoGSubject
from pynwb import NWBFile, TimeSeries, NWBHDF5IO, get_manager
from pynwb.ecephys import ElectricalSeries

from changlab_to_nwb.utilities.config import config

manager = get_manager()


def elecs_to_electrode_table(nwb_file, elecspath):
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
    ecog_channels : 1d array of ints
        Indices of electrodes channels that were not labeled NaN.
    all_table_region : DynamicTable
        Table with electrode information.
    """

    # Get anatomical and location information for electrodes.
    elec_mat = sio.loadmat(elecspath)
    labels = elec_mat['anatomy'][:, 1]
    location = elec_mat['anatomy'][:, 3]
    x = elec_mat['elecmatrix'][:, 0]
    y = elec_mat['elecmatrix'][:, 1]
    z = elec_mat['elecmatrix'][:, 2]

    # Get MNI warped electrode coordinates.
    try:
        elec_mat_warped = sio.loadmat(elecspath.split('.')[0] + '_warped.mat')
        x_warped = elec_mat_warped['elecmatrix'][:, 0]
        y_warped = elec_mat_warped['elecmatrix'][:, 1]
        z_warped = elec_mat_warped['elecmatrix'][:, 2]
    except FileNotFoundError:
        print('No warped electrode information found...filling with zeros.')
        x_warped = np.zeros_like(x)
        y_warped = np.zeros_like(y)
        z_warped = np.zeros_like(z)

    # Define electrode device label names.
    group_labels = []
    for current_group in labels:
        group_labels.append(current_group[0].rstrip('0123456789'))

    # Get the list of unique electrode device label names
    unique_group_indexes = np.unique(group_labels, return_index=True)[1]
    unique_group_labels = [group_labels[f] for f in
                           sorted(unique_group_indexes)]

    # Add additional columns to the electodes table.
    nwb_file.add_electrode_column('label', 'label of electrode')
    nwb_file.add_electrode_column('bad', 'electrode identified as too noisy')
    nwb_file.add_electrode_column('x_warped',
                                  'x warped onto cvs_avg35_inMNI152')
    nwb_file.add_electrode_column('y_warped',
                                  'y warped onto cvs_avg35_inMNI152')
    nwb_file.add_electrode_column('z_warped',
                                  'z warped onto cvs_avg35_inMNI152')

    for group_label in unique_group_labels:

        if group_label != 'NaN':

            # Get region name and device label for the group.
            if 'Depth' in group_label:
                group_label_split = group_label.split('Depth')
            elif 'Strip' in group_label:
                group_label_split = group_label.split('Strip')
            elif 'Grid' in group_label:
                group_label_split = group_label.split('Grid')
            elif 'Pole' in group_label:
                group_label_split = group_label.split('Pole')

            # Get general group region
            brain_area = group_label_split[0]

            # Create electrode device (same as the group).
            device = nwb_file.create_device(group_label)

            # Create electrode group with name, description, device object,
            # and general location.
            electrode_group = nwb_file.create_electrode_group(
                name='{} electrodes'.format(group_label),
                description='{}'.format(group_label),
                device=device,
                location=str(brain_area))

            # Loop through the number of electrodes in this electrode group
            elec_nums = np.where(np.array(group_labels) == group_label)[0]
            for elec_num in elec_nums:

                # Add the electrode information to the table.
                elec_location = location[elec_num]
                if len(elec_location) == 0:
                    # If no label is recorded for this electrode, set it to
                    # nan.
                    elec_location = 'nan'
                else:
                    elec_location = elec_location[0]

                nwb_file.add_electrode(
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
                    bad=False)

    # Get the electrodes that were recorded into the file.
    ecog_channels = np.where(np.array(group_labels) != 'NaN')[0]

    # # Create electrode table region that includes all the recorded
    # electrodes.
    # all_table_region = nwb_file.create_electrode_table_region(
    #     list(range(len(ecog_channels))), 'all electrodes')

    return nwb_file, ecog_channels


def calculate_resolution(machine=None, system='TDT'):
    """
    Calculates the resolution of the machine that recorded the channels of
    the acquisition. That is, the smallest meaningful difference between
    values in data. This differs with different recording systems and
    recording circuits.

    Resolution is calculated by the dynamic range / encodable storage.

    For the TDT system, neural channels are recorded through the PZ5M-512
    while analog channels go through the RZ2.
    #TODO: microphone channel technically goes through an amplifier before
    going into the RZ2.

    Parameters
    ----------
    machine : str, default None
        The machine of the system. For example, for neural channels,
        the machine that affects the resolution is the amplifier (PZ5M-512
        by default).
    system : str, default 'TDT'
        The recording system/manufacturer. Default is Tucker-Davis
        Technologies (TDT).

    Returns
    -------
    res : float
        The resolution of the recording in volts.
    """
    # Get the bit resolution and dynamic range of the machine.
    bit_res = config[system][machine]['bit_resolution']
    dr = config[system][machine]['dynamic_range']

    # Calculate the resolution.
    res = (dr[1] - dr[0]) / float(2 ** bit_res)
    return res


def TDTtoNWB(subject, block, external_subject=False,
             include_cortical_surfaces=False, out_directory=None,
             anin_labels=None, elec_path_prefix='TDT_elecs_all',
             tanks_directory=None, tanks_block_folder_name=None,
             neural_machine='PZ5M-512',
             analog_machine='RZ2', daq_system='TDT', recording_software=None):
    """
    Loads raw data from a single TDT tank block and converts to NWB format.

    Parameters
    ----------
    subject : int or str
        The number of the subject, to be concatenated with 'EC'.
    block : int
        The block number to process.
    external_subject : bool, default False
        Whether or not to create a separate NWB file for the subject,
        which would then be linked via external links to the block file.
    include_cortical_surfaces : bool, default False
        Whether or not to include cortical surfaces information (i.e.
        meshes).
    out_directory : str or None
        Path specifying where to save the resulting NWB files. If
        unspecified (that is, it is the default None), the usual processed
        data location is used.
    anin_labels : dict
        Dictionary of labels for the analog channels, where the keys are the
        string labels and the values are whether the channel was an
        acquisition (subject data/input) or a stimulus. These should be in
        the order of the analog channels they refer to. For example,
        the defaults are:
            {'microphone': 'acquisition',
             'speaker1': 'stimulus',
             'speaker2': 'stimulus',
             'anin4': 'acquisition'}
        Acquisitions will be stored under nwbfile.acquisition while stimuli
        will be stored under nwbfile.stimulus.
    elec_path_prefix : str
        The prefix for the .mat elecs file, usually TDT_elecs_all,
        but occasionally has other names.
    tanks_directory : str
        The directory with the tanks. If not specified, the server location
        will be used by default.
    tanks_block_folder_name : str
        The folder name for the block data. If not specified, will use
        'EC{subject}_B{block}
    neural_machine : str
        The machine (processor or amplifier) used to record the neural data.
        Default is the 'PZ5M-512' from TDT (TDT would be specified in
        daq_system).
    analog_machine : str
        The machine (processor or amplifier) used to record the analog
        channels. Default is the 'RZ2' from TDT (TDT would be specified in
        daq_system).
    daq_system : str
        The Data Acquisition System (DAQ) that was used for recording.
        Default is 'TDT'.
    recording_software : str
        The recording software used on the daq_system. For TDT and
        pre-EC212, 'openex' was used. EC212 and forward, 'synapse' was used.

    Returns
    -------
        Nothing. File saving is done within this function.
    """
    # Load base paths from config file, which should reside in the user's
    # home directory under .config
    with open('{}/.config/NWBconf.json'.format(os.path.expanduser('~')),
              'r') as f:
        base_paths = json.load(f)

    # Get base paths. For now, assume this is on the server.
    imaging_directory = base_paths['imaging_directory']

    if tanks_directory is None:
        tanks_directory = base_paths['server_tanks_directory']

    # Define EC subject name and block name.
    subject_id = 'EC{}'.format(subject)
    out_block_name = 'EC{}_B{}'.format(subject, block)

    # Define relevant paths.
    subject_path = os.path.join(tanks_directory, subject_id)
    imaging_path = os.path.join(imaging_directory, subject_id, 'Meshes')
    elecs_path = os.path.join(imaging_directory, subject_id,
                              'elecs/{}.mat'.format(elec_path_prefix))

    if tanks_block_folder_name is None:
        tanks_block_folder_name = out_block_name
    block_path = os.path.join(subject_path, tanks_block_folder_name)

    if not os.path.isdir(block_path):
        raise NotADirectoryError('Directory not found {}. Consider specifying '
                                 'the folder name using the block_folder_name '
                                 'parameter'.format(block_path))

    # If an out_path is not specified, default to the usual processed data
    # directory from the config file.
    if out_directory is None:
        out_directory = base_paths['processed_data_directory']
        out_directory = os.path.join(out_directory, subject_id)

    # Create the subject output folder if it doesn't already exist.
    try:
        os.mkdir(out_directory)
        print('Subject output folder does not exist, creating.')
    except FileExistsError:
        print('Subject output folder exists.')

    # Define NWB file name for this block
    nwb_path = os.path.join(out_directory, '{}.nwb'.format(out_block_name))

    # Calculate the recording resolution for neural and analog channels.
    neural_resolution = calculate_resolution(
        machine=neural_machine,
        system=daq_system
    )
    analog_resolution = calculate_resolution(
        machine=analog_machine,
        system=daq_system
    )

    # Read in TDT tank data.
    data = tdt.read_block(block_path)
    print('Successfully loaded TDT block...', flush=True)

    # Get session start time.
    session_start_time = data.info.start_date

    # Assign timezone the data was saved with.
    session_start_time = session_start_time.replace(
        tzinfo=pytz.timezone('UTC'))

    # Replace timezone with local (PST).
    pacific = pytz.timezone('US/Pacific')
    session_start_time = session_start_time.astimezone(pacific)

    # Create NWB file.
    file = NWBFile('NWB File', out_block_name, session_start_time,
                   institution='University of California, San Francisco',
                   lab='Chang Lab')

    # Assign electrode anatomical and location information to the NWB file.
    file, ecog_channels = elecs_to_electrode_table(file, elecs_path)
    print('Assigned electrode information...', flush=True)

    # Define the prefix for the data streams.
    if daq_system == 'TDT':
        if recording_software == 'openex':
            stream_prefix = 'Wav'
        elif recording_software == 'synapse':
            stream_prefix = 'Raw'
        else:
            raise ValueError('Recording software not defined so cannnot '
                             'define the data stream prefix.')
    else:
        stream_prefix = 'Wav'

    # Get the data streams and sort the stream names by Wav.
    stream_names = list(data.streams.keys())
    ecog_streams_names = sorted([key for key in stream_names if stream_prefix
                                 in key])

    # Extract raw ECoG from TDT data stream.
    ecog_data = []
    for stream_key in ecog_streams_names:
        stream = data.streams[stream_key]
        ecog_data.append(stream.data.T)

    # Concatenate the data streams.
    try:
        ecog_data = np.concatenate(ecog_data, axis=-1)
    except ValueError:
        # There is a mismatch in the number of timepoints in each stream.
        # Cutoff longer streams based on the shortest stream recorded.
        array_shapes = [s.shape[0] for s in ecog_data]
        time_cutoff = np.min(array_shapes)
        ecog_data = [s[:time_cutoff, :] for s in ecog_data]
        ecog_data = np.concatenate(ecog_data, axis=-1)

    # Get sampling rate from TDT streams
    sampling_rate = stream.fs

    # Get only appropriate ECoG channels
    if len(ecog_channels) > ecog_data.shape[-1]:
        print('Not all electrodes were recorded during this block. Assuming '
              'that they correspond to the first {} electrodes.'.format(
                ecog_data.shape[-1]))
    else:
        ecog_data = ecog_data[:, ecog_channels]

    # Going on the assumption that the relevant electrodes are the first in
    # the table, assign the electrode table accordingly.
    # TODO: need a more elegant solution to this. How do we know what
    #  electrodes were recorded?
    elec_table_region = file.create_electrode_table_region(
        list(range(ecog_data.shape[-1])), 'electrodes')

    # Define ElectricalSeries acquisition for ECoG data
    es = ElectricalSeries('ElectricalSeries',
                          ecog_data,
                          elec_table_region,
                          conversion=1.0,
                          rate=sampling_rate,
                          resolution=neural_resolution,
                          starting_time=0.0,
                          description='all Wav data')

    # Set ECoG as acquisition
    file.add_acquisition(es)

    # Get analog channels and define names
    anin_stream = data.streams['ANIN']

    # If analog labels are not specified, set the defaults.
    if anin_labels is None:
        anin_labels = {
            'microphone': 'acquisition',
            'speaker1': 'stimulus',
            'speaker2': 'stimulus',
            'anin4': 'acquisition'
        }

    # Add each analog channel as a separate TimeSeries.
    for cur_anin, (anin_label, anin_type) in enumerate(anin_labels.items()):
        ts = TimeSeries(anin_label,
                        anin_stream.data[cur_anin, :].T,
                        unit='amplitude',
                        rate=anin_stream.fs,
                        conversion=1.0,
                        resolution=analog_resolution,
                        starting_time=0.0,
                        description='{}'.format(anin_label))

        if anin_type == 'stimulus':
            # Add stimulus type anin streams.
            file.add_stimulus(ts)

        elif anin_type == 'acquisition':
            # Add acquisition type anin streams.
            file.add_acquisition(ts)

    print('Added all TDT stream data...', flush=True)

    # Create ECoGSubject object.
    nwbfile_subject = ECoGSubject(subject_id=subject_id)

    if include_cortical_surfaces:
        # If including cortical surfaces, get the mesh file names.
        mesh_file_list = glob(os.path.join(imaging_path, '*_pial.mat'))
        mesh_file_names = [f.split('/')[-1].split('.')[0] for f in
                           mesh_file_list]

        # Create cortical surfaces object.
        cortical_surfaces = CorticalSurfaces()

        # Add each surface to the CorticalSurfaces object
        for i_mesh, mesh_file in enumerate(mesh_file_list):
            surface_load = sio.loadmat(mesh_file)

            if 'mesh' in surface_load.keys():

                # Faces stored as 0-indexed in nwbext_ecog
                faces = surface_load['mesh'][0][0][0] - 1
                vertices = surface_load['mesh'][0][0][1]

            elif 'cortex' in surface_load.keys():

                # Faces stored as 0-indexed in nwbext_ecog
                faces = surface_load['cortex'][0][0][0] - 1
                vertices = surface_load['cortex'][0][0][1]

            cortical_surfaces.create_surface(name=mesh_file_names[i_mesh],
                                             faces=faces, vertices=vertices)

        # Assign the cortical surfaces to the NWB file.
        nwbfile_subject.cortical_surfaces = cortical_surfaces
        print('Added cortical surface information to subject information...',
              flush=True)

    if external_subject:
        # If saving an external file with all the subject information,
        # define new subject NWB file.
        subj_fpath = os.path.join(out_directory, '{}.nwb'.format(subject_id))

        # Check if subject NWB file already exists.
        if not os.path.isfile(subj_fpath):
            # If the file does not exist, create it.
            subj_nwbfile = NWBFile(
                session_description=str(subject),
                identifier=str(subject),
                subject=nwbfile_subject,
                session_start_time=datetime(1900, 1, 1).astimezone(
                    pytz.timezone('UTC')))

            # Write the new subject NWB file.
            with NWBHDF5IO(subj_fpath, manager=manager, mode='w') as subj_io:
                subj_io.write(subj_nwbfile)
        else:
            # Subject file already exists, use as is.
            print('External subject file already exists, using as is...',
                  flush=True)

        # Load and read the previously defined or newly written subject NWB
        # file.
        subj_read_io = NWBHDF5IO(subj_fpath, manager=manager, mode='r')
        subj_nwbfile = subj_read_io.read()

        # Get the subject object from the subject NWB file.
        nwbfile_subject = subj_nwbfile.subject

    # Set the subject object information for the current NWB file.
    file.subject = nwbfile_subject
    print('Added subject information to file...', flush=True)

    # Write the current NWB file.
    with NWBHDF5IO(nwb_path, manager=manager, mode='w') as f:
        f.write(file)

    # Close any open NWB files.
    if external_subject:
        subj_read_io.close()

    # Set the permissions.
    os.system('chmod 774 {}'.format(nwb_path))
    os.system('chgrp ecog_grp {}'.format(nwb_path))

    print('Successfully saved NWB file with raw ECoG.', flush=True)
