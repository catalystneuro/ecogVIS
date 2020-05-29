# -*- coding: utf-8 -*-
"""
Convert ECoG to NWB.

:Author: Ben Dichter, Jessie R. Liu
Modified by Luiz Tauffer on May 12, 2020
"""
from __future__ import print_function

import argparse
import glob
import json
import os
from datetime import datetime
from os import path
from pathlib import Path

import numpy as np
import pandas as pd
from h5py import File
from hdmf.backends.hdf5 import H5DataIO
from hdmf.data_utils import DataChunkIterator
from nwbext_ecog import CorticalSurfaces, ECoGSubject
from pynwb import NWBFile, TimeSeries, get_manager, NWBHDF5IO
from pynwb.base import Images
from pynwb.behavior import BehavioralTimeSeries
from pynwb.ecephys import ElectricalSeries, LFP
from pynwb.image import RGBImage, RGBAImage, GrayscaleImage
from pynwb.misc import DecompositionSeries
from pytz import timezone
import scipy.io as sio
from scipy.io import loadmat
from scipy.io.wavfile import read as wavread
# from scipy.misc import imread # this function is deprecated
# from imageio import imread
from tqdm import tqdm

from ecogvis.functions.tdt_to_nwb.utilities.HTK import readHTK
# from changlab_to_nwb.tdt_matread import load_wavs, load_anin
# from changlab_to_nwb.transcripts import parse, make_df, create_transcription_ndx
# from changlab_to_nwb.utils import remove_duplicates

# get_manager must come after dynamic imports
manager = get_manager()

# Load base paths from config file.
# with open('{}/.config/NWBconf.json'.format(os.path.expanduser('~')), 'r') as f:
#     base_paths = json.load(f)
#
# raw_htk_paths = [base_paths['processed_data_directory'],
#                  base_paths['older_processed_data_directory']]
# IMAGING_PATH = base_paths['imaging_directory']
#
# hilb_dir = '/path/to/hilb'
# transcript_path = '/path/to/transcripts'


def find_ekg_elecs(elec_metadata_file):
    elec_grp_df, coord = read_electrodes(elec_metadata_file)
    return np.where(elec_grp_df['device'] == 'EKG')[0]


def add_ekg(nwbfile, ecog_path, ekg_elecs):
    if os.path.split(ecog_path)[1] == 'RawHTK':
        rate, data = readhtks(ecog_path, ekg_elecs)
    elif os.path.split(ecog_path)[1] == 'ecog.mat':
        with File(ecog_path, 'r') as f:
            data = f['ecogDS']['data'][:, ekg_elecs]
            rate = f['ecogDS']['sampFreq'][:].ravel()[0]
    elif os.path.split(ecog_path)[1] == 'raw.mat':
        rate, data = load_wavs(ecog_path, ekg_elecs)

    ekg_ts = TimeSeries('EKG', H5DataIO(data, compression='gzip'), unit='V',
                        rate=rate, conversion=.001,
                        description='electrotorticography')
    nwbfile.add_acquisition(ekg_ts)


def add_images_to_subject(subject, subject_image_list):
    images = Images(name='images', description="images of subject's brain")
    for image_path in subject_image_list:
        image_name = os.path.split(image_path)[1]
        image_name = os.path.splitext(image_name)[0]
        image_data = imread(image_path)
        kwargs = {'data': image_data, 'name': image_name}
        if len(image_data.shape) == 2:
            image = GrayscaleImage(**kwargs)
        elif image_data.shape[2] == 3:
            image = RGBImage(**kwargs)
        elif image_data.shape[2] == 4:
            image = RGBAImage(**kwargs)

        images.add_image(image)
    subject.images = images
    return subject


def load_pitch(blockpath):
    blockname = os.path.split(blockpath)[1]
    pitch_path = os.path.join(blockpath, 'pitch_' + blockname + '.mat')
    matin = loadmat(pitch_path)
    data = matin['pitch'].ravel()
    fs = 1 / matin['dt'][0, 0]
    return fs, data


def load_intensity(blockpath):
    blockname = os.path.split(blockpath)[1]
    pitch_path = os.path.join(blockpath, 'intensity_' + blockname + '.mat')
    matin = loadmat(pitch_path)
    data = matin['intensity'].ravel()
    fs = 1 / matin['dt'][0, 0]
    return fs, data


def get_analog(anin_path, num=1):
    """
    Load analog data. Try:
    1) analog[num].wav
    2) ANIN[num].htk
    3) Extracting from raw.mat
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
    # blockname = os.path.split(blockpath)[1]
    # subject_id = get_subject_id(blockname)
    # raw_fpath = os.path.join(raw_htk_paths[0], subject_id, blockname,
    #                          'raw.mat')
    # if os.path.isfile(raw_fpath):
    #     return load_anin(raw_fpath, num)
    print('no analog path found for ' + str(num))
    return None, None


def get_subject_id(blockname):
    return blockname[:blockname.find('_')]


def gen_htk_num(i, n=64):
    """Input 0-indexed channel number, output htk filename.
    Parameters
    ----------
    i: int
        zero-indexed channel number
    n: int
        number of channels per wav
    Returns
    -------
    str
    """
    return str(i // n + 1) + str(np.mod(i, n) + 1)


def auto_ecog(blockpath, ecog_elecs, verbose=False):
    basepath, blockname = os.path.split(blockpath)
    subject_id = get_subject_id(blockname)
    for htk_blockpath in [blockpath] + [os.path.join(x, subject_id, blockname)
                                        for x in raw_htk_paths]:
        htk_path = os.path.join(htk_blockpath, 'RawHTK')
        if os.path.exists(htk_path):
            if verbose:
                print('reading htk acquisition...', flush=True)
            fs, data = readhtks(htk_path, ecog_elecs)
            data = data.squeeze()
            if verbose:
                print('done', flush=True)
            return fs, data, htk_path
        raw_fpath = os.path.join(htk_blockpath, 'raw.mat')
        if os.path.exists(raw_fpath):
            fs, data = load_wavs(raw_fpath)
            return fs, data, raw_fpath


def create_cortical_surfaces(pial_files, subject_id):
    if not len(pial_files):
        return None

    names = []
    cortical_surfaces = CorticalSurfaces()
    for pial_file in pial_files:
        matin = loadmat(pial_file)
        if 'cortex' in matin:
            x = 'cortex'
        elif 'mesh' in matin:
            x = 'mesh'
        else:
            Warning('Unknown structure of ' + pial_file + '.')
            continue

        tri = matin[x]['tri'][0][0] - 1
        vert = matin[x]['vert'][0][0]
        name = os.path.split(pial_file)[1][len(subject_id) + 1:-4]
        names.append(name)
        cortical_surfaces.create_surface(faces=tri.astype('uint'),
                                         vertices=vert, name=name)
    return cortical_surfaces


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


def read_electrodes(elec_metadata_file):
    """Read metadata for all electrodes
    Parameters
    ----------
    elec_metadata_file: str
    Returns
    -------
    elec_grp_df, coord
    """
    elecs_metadata = sio.loadmat(elec_metadata_file)
    elec_grp_xyz_coord = elecs_metadata['elecmatrix']
    anatomy = elecs_metadata['anatomy']
    elec_grp_loc = [str(x[3][0]) if len(x[3]) else "" for x in anatomy]
    elec_grp_type = [str(x[2][0]) for x in anatomy]
    elec_grp_long_name = [str(x[1][0]) for x in anatomy]

    if 'Electrode' in elec_grp_long_name[0]:
        elec_grp_device = [x[:x.find('Electrode')] for x in elec_grp_long_name]
    else:
        elec_grp_device = [''.join(filter(lambda y: not str.isdigit(y), x))
                           for x in elec_grp_long_name]

    elec_grp_short_name = [str(x[0][0]) for x in anatomy]

    anatomy = {
        'loc': elec_grp_loc, 'type': elec_grp_type,
        'long_name': elec_grp_long_name, 'short_name': elec_grp_short_name,
        'device': elec_grp_device
    }
    elec_grp_df = pd.DataFrame(anatomy)

    n = len(elec_grp_long_name)
    if n < len(elec_grp_xyz_coord):
        coord = elec_grp_xyz_coord[:n]
    elif n == len(elec_grp_xyz_coord):
        coord = elec_grp_xyz_coord
    else:
        coord = elec_grp_xyz_coord
        for i in range(n - len(elec_grp_xyz_coord)):
            coord.append([np.nan, np.nan, np.nan])

    return elec_grp_df, coord


def write_electrodes(nwbfile, elec_grp_df, coord, bad_elecs_inds,
                     warped_coord=None):
    ignore_devices = ('NaN', 'Right', 'EKG', 'Na')

    elec_grp_df['bad'] = np.zeros((len(elec_grp_df),), dtype=bool)
    elec_grp_df.loc[bad_elecs_inds, 'bad'] = True

    devices = remove_duplicates(elec_grp_df['device'])
    devices = [x for x in devices if x not in ignore_devices]

    if warped_coord is not None:
        nwbfile.add_electrode_column('x_warped',
                                     'x warped onto cvs_avg35_inMNI152')
        nwbfile.add_electrode_column('y_warped',
                                     'x warped onto cvs_avg35_inMNI152')
        nwbfile.add_electrode_column('z_warped',
                                     'x warped onto cvs_avg35_inMNI152')

    for device_name in devices:
        device_data = elec_grp_df[elec_grp_df['device'] == device_name]
        # Create devices
        device = nwbfile.create_device(device_name)

        # Create electrode groups
        electrode_group = nwbfile.create_electrode_group(
            name=device_name + ' electrodes',
            description=device_name,
            location=device_data['type'].iloc[0],
            device=device
        )

        for idx, elec_data in device_data.iterrows():
            kwargs = {}
            kwargs.update(x=float(coord[idx, 0]),
                          y=float(coord[idx, 1]),
                          z=float(coord[idx, 2]),
                          imp=np.nan,
                          location=elec_data['loc'],
                          filtering='none',
                          group=electrode_group,
                          bad=elec_data['bad'])
            if warped_coord is not None:
                kwargs.update(x_warped=float(warped_coord[idx, 0]),
                              y_warped=float(warped_coord[idx, 1]),
                              z_warped=float(warped_coord[idx, 2]))
            nwbfile.add_electrode(**kwargs)


def add_electrodes(nwbfile, elec_metadata_file, bad_elecs_inds,
                   load_warped=True):
    elec_grp_df, coord = read_electrodes(elec_metadata_file)

    if load_warped:
        warped_elec_metadata_file = elec_metadata_file[:-4] + '_warped.mat'
        warped_coord = read_electrodes(warped_elec_metadata_file)[1]

    write_electrodes(nwbfile, elec_grp_df, coord, bad_elecs_inds,
                     warped_coord=warped_coord)


def transpose_iter(aa):
    for i in range(aa.shape[-1]):
        yield aa[..., i].T


def parse_interview(blockpath, blockname):
    try:
        tg_path = '{}/{}_interview.TextGrid'.format(blockpath, blockname)

        with open(tg_path, 'r') as tg:
            content = tg.readlines()

        value_tabs = '\t\t\t\t'
        name_tabs = '\t\t\t'

    except FileNotFoundError:
        tg_path = '{}/{}.TextGrid'.format(blockpath, blockname)

        with open(tg_path, 'r') as tg:
            content = tg.readlines()

        value_tabs = '            '
        name_tabs = '        '

    speaker_starts = []
    speaker_names = []

    for i, line in enumerate(content):
        if line.strip(name_tabs)[:4] == 'name':
            speaker_starts.append(i)

            speaker_name = line.split('"')[1]
            speaker_names.append(speaker_name)

    speaker_starts.append(len(content))

    text_dict_list = []

    for i, speaker in enumerate(speaker_names):

        if speaker != 'Proper':

            speaker_content = content[
                              speaker_starts[i] + 4:speaker_starts[i + 1]]

            if speaker in ['1', '2']:
                label_type = 'phrases'

                if speaker == '1':
                    speaker_label = 'interviewer'
                else:
                    speaker_label = 'subject'

            else:
                if speaker.split(' ')[-1] in ['Words', 'Phones']:
                    label_type = speaker.split(' ')[-1].lower()
                    speaker_label = speaker.split(' ')[0]
                else:
                    label_type = 'phrases'
                    speaker_label = speaker.lower()

            tmin = []
            tmax = []
            ttext = []
            for line in speaker_content:

                line_prcsd = line.replace(' ', '').strip('\n').strip(
                    value_tabs)
                line_type = line_prcsd.split('=')[0]

                if line_type == 'xmin':
                    tmin.append(float(line_prcsd.split('=')[1]))
                elif line_type == 'xmax':
                    tmax.append(float(line_prcsd.split('=')[1]))
                elif line_type == 'text':
                    ttext.append(line.split('"')[1].lower())

            for t, token in enumerate(ttext):
                if token not in ['', 'sp']:
                    text_dict = {
                        'speaker': speaker_label.lower(),
                        'start_time': tmin[t],
                        'stop_time': tmax[t],
                        'label_type': label_type,
                        'label': token
                    }
                    text_dict_list.append(text_dict)

    return text_dict_list


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
    nwbfile.add_electrode_column('is_null', 'if not connected to real electrode')

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
                is_null=is_null,
            )

    return nwbfile


def chang2nwb(blockpath, out_file_path=None, save_to_file=False, htk_config=None,
              session_start_time=None, session_description=None,
              identifier=None, anin4=False, include_intensity=False,
              ecog_format='htk', external_subject=False, include_pitch=False,
              hilb=False, verbose=False, imaging_path=None, parse_transcript=False,
              parse_percept_transcript=False, include_cortical_surfaces=False,
              include_ekg=False, subject_image_list=None, rest_period=None):
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
    session_start_time: datetime.datetime
        default: datetime(1900, 1, 1)
    session_description: str
        default: blockname
    identifier: str
        default: blockname
    anin4: False | str
        Whether or not to convert ANIN4. ANIN4 is used as an extra channel for
        things like button presses, and is usually unused. If a string is
        supplied, that is used as the name of the timeseries.
    ecog_format: str
        ({'htk'}, 'mat', 'raw')
    external_subject: bool (optional)
        True: (default) cortical mesh is saved in an external file and a
        link is
            provided to that file. This is useful if you have multiple
            sessions for a single subject.
        False: cortical mesh is saved normally
    include_pitch: bool (optional)
        add pitch data. Default: False
    include_intensity: bool (optional)
        add intensity data. Default: False
    hilb: bool
        include Hilbert Transform data. Default: False
    verbose: bool (optional)
    imaging_path: str (optional)
        None: use IMAGING_DIR
        'local': use subject_dir/Imaging/
        else: use supplied string
    parse_transcript: str (optional)
    parse_percept_transcript: str (optional)
    include_cortical_surfaces: bool (optional)
    include_ekg: bool (optional)
    subject_image_list: list (optional)
        List of paths of images to include
    rest_period: None | array-like

    Returns
    -------
    """

    behav_module = None
    metadata = {}

    if htk_config is None:
        blockpath = Path(blockpath)
    else:
        blockpath = Path(htk_config['ecephys_path'])
        metadata = htk_config['metadata']
    blockname = blockpath.parent.name
    subject_id = blockpath.parent.parent.name[2:]
    if identifier is None:
        identifier = blockname

    if session_description is None:
        session_description = blockname

    if out_file_path is None:
        out_file_path = blockpath.resolve().parent / ''.join(['EC', subject_id, '_', blockname, '.nwb'])
    out_base_path = os.path.split(out_file_path)[0]

    if session_start_time is None:
        # session_start_time = datetime(1900, 1, 1).astimezone(timezone('UTC'))
        session_start_time = datetime.now().astimezone()

    # if imaging_path is None:
    #     subj_imaging_path = path.join(IMAGING_PATH, subject_id)
    # elif imaging_path == 'local':
    #     subj_imaging_path = path.join(basepath, 'imaging')
    # else:
    #     subj_imaging_path = os.path.join(imaging_path, subject_id)

    # file paths
    ecog_path = blockpath
    anin_path = htk_config['analog_path']
    bad_time_file = path.join(blockpath, 'Artifacts', 'badTimeSegments.mat')
    # ecog400_path = path.join(blockpath, 'ecog400', 'ecog.mat')
    # mesh_path = path.join(subj_imaging_path, 'Meshes')
    # pial_files = glob.glob(path.join(mesh_path, '*pial.mat'))

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
    if ecog_format == 'htk':
        if verbose:
            print('reading htk acquisition...', flush=True)
        ecog_rate, data = readhtks(ecog_path)
        data = data.squeeze()
        if verbose:
            print('done', flush=True)
    elif ecog_format == 'auto':
        raise NotImplementedError(f'Not implemented format {ecog_format}')
        # ecog_rate, data, ecog_path = auto_ecog(blockpath, ecog_elecs, verbose=False)
    elif ecog_format == 'mat':
        raise NotImplementedError(f'Not implemented format {ecog_format}')
        # with File(ecog400_path, 'r') as f:
        #     data = f['ecogDS']['data'][:, ecog_elecs]
        #     ecog_rate = f['ecogDS']['sampFreq'][:].ravel()[0]
        # ecog_path = ecog400_path
    elif ecog_format == 'raw':
        raise NotImplementedError(f'Not implemented format {ecog_format}')
        # ecog_path = os.path.join(raw_htk_paths[0], subject_id, blockname, 'raw.mat')
        # ecog_rate, data = load_wavs(ecog_path)
    else:
        raise ValueError('unrecognized argument: ecog_format')

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
        nwbfile.add_electrode_column('is_null', 'if not connected to real electrode')
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
                is_null=False,
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

    # if include_ekg:
    #     ekg_elecs = find_ekg_elecs(elec_metadata_file)
    #     if len(ekg_elecs):
    #         add_ekg(nwbfile, ecog_path, ekg_elecs)
    #
    # if rest_period is not None:
    #     nwbfile.add_epoch(start_time=rest_period[0], stop_time=rest_period[1])
    #
    # if hilb:
    #     block_hilb_path = os.path.join(hilb_dir, subject_id, blockname,
    #                                    blockname + '_AA.h5')
    #     file = File(block_hilb_path, 'r')
    #
    #     data = transpose_iter(
    #         file['X'])  # transposes data during iterative write
    #     filter_center = file['filter_center'][:]
    #     filter_sigma = file['filter_sigma'][:]
    #
    #     data = H5DataIO(
    #         DataChunkIterator(
    #             tqdm(data, desc='writing hilbert data'),
    #             buffer_size=400 * 20), compression='gzip')
    #
    #     decomp_series = DecompositionSeries(
    #         name='LFPDecompositionSeries',
    #         description='Gaussian band Hilbert transform',
    #         data=data, rate=400.,
    #         source_timeseries=ecog_es, metric='amplitude')
    #
    #     for band_mean, band_stdev in zip(filter_center, filter_sigma):
    #         decomp_series.add_band(band_mean=band_mean, band_stdev=band_stdev)
    #
    #     hilb_mod = nwbfile.create_processing_module(
    #         name='ecephys', description='holds hilbert analysis results')
    #     hilb_mod.add_container(decomp_series)
    #
    # if include_cortical_surfaces:
    #     subject.cortical_surfaces = create_cortical_surfaces(pial_files,
    #                                                          subject_id)
    #
    # if subject_image_list is not None:
    #     subject = add_images_to_subject(subject, subject_image_list)
    #
    # if external_subject:
    #     subj_fpath = path.join(out_base_path, subject_id + '.nwb')
    #     if not os.path.isfile(subj_fpath):
    #         subj_nwbfile = NWBFile(
    #             session_description=subject_id, identifier=subject_id,
    #             subject=subject,
    #             session_start_time=datetime.now().astimezone()
    #         )
    #         with NWBHDF5IO(subj_fpath, manager=manager, mode='w') as subj_io:
    #             subj_io.write(subj_nwbfile)
    #     subj_read_io = NWBHDF5IO(subj_fpath, manager=manager, mode='r')
    #     subj_nwbfile = subj_read_io.read()
    #     subject = subj_nwbfile.subject
    #
    # if parse_percept_transcript:
    #     nwbfile.add_trial_column('word', 'presented word stimulus')
    #     nwbfile.add_trial_column('phoneme', 'phoneme transcription')
    #     nwbfile.add_trial_column('trial', 'trial number')
    #
    #     stim_info = loadmat(path.join(basepath, '{}_stimInfo.mat'.format(
    #         blockname.split('_')[0])))
    #
    #     words = stim_info['stimInfo']['word'][0, 0].squeeze()
    #     words = np.array([w[0] for w in words])
    #     phoneme_trans = stim_info['stimInfo']['phn'][0, 0].squeeze()
    #     phoneme_times = stim_info['stimInfo']['phnTimes_corrected'][
    #         0, 0].squeeze()
    #
    #     with File(path.join(blockpath, 'Analog/evnt.mat'), 'r') as f:
    #         events = f['evnt']
    #         num_trials = len(events['trial'])
    #
    #         for i_trial in range(num_trials):
    #             start_time = \
    #                 np.array(events[events['StartTime'][i_trial][0]])[0][0]
    #             # stop_time = np.array(events[events['StopTime'][i_trial][
    #             # 0]])[0][0]
    #             trial_num = int(
    #                 np.array(events[events['trial'][i_trial][0]])[0][0])
    #             trial_word = np.array(
    #                 events[events['name'][i_trial][0]]).squeeze()
    #             trial_word = ''.join(map(chr, trial_word))
    #
    #             trial_ind = np.where(words == trial_word)[0][0]
    #             trial_phoneme_trans = phoneme_trans[trial_ind].squeeze()
    #             trial_phoneme_times = start_time + phoneme_times[trial_ind]
    #
    #             for i_phone in range(trial_phoneme_times.shape[0]):
    #                 nwbfile.add_trial(
    #                     start_time=trial_phoneme_times[i_phone, 0],
    #                     stop_time=trial_phoneme_times[i_phone, 1],
    #                     word=trial_word,
    #                     phoneme=trial_phoneme_trans[i_phone][0],
    #                     trial=trial_num)
    #
    # if parse_transcript:
    #     if parse_transcript == 'interview':
    #         parseout = parse_interview(blockpath, blockname)
    #
    #         nwbfile.add_trial_column('speaker',
    #                                  'whether interviewer or interviewee is '
    #                                  'speaking')
    #         nwbfile.add_trial_column('label_type',
    #                                  'which type of transcription')
    #         nwbfile.add_trial_column('label', 'label for transcription type')
    #
    #         for entry in parseout:
    #             nwbfile.add_trial(start_time=entry['start_time'],
    #                               stop_time=entry['stop_time'],
    #                               speaker=entry['speaker'],
    #                               label_type=entry['label_type'],
    #                               label=entry['label'])
    #
    #     else:
    #         parseout = parse(blockpath, blockname)
    #         if parse_transcript == 'CV':
    #             df = make_df(parseout, 0, subject_id, align_pos=1)
    #             nwbfile.add_trial_column(
    #                 'cv_transition_time', 'time of CV transition in seconds')
    #             nwbfile.add_trial_column(
    #                 'speak',
    #                 'if True, subject is speaking. If False, subject is '
    #                 'listening')
    #             nwbfile.add_trial_column('condition', 'syllable spoken')
    #             for _, row in df.iterrows():
    #                 nwbfile.add_trial(
    #                     start_time=row['start'], stop_time=row['stop'],
    #                     cv_transition_time=row['align'],
    #                     speak=row['mode'] == 'speak', condition=row['label'])
    #         elif parse_transcript == 'singing':
    #             df = make_df(parseout, 0, subject_id, align_pos=0)
    #             if not len(df):
    #                 df = pd.DataFrame(parseout)
    #                 df['mode'] = 'speak'
    #
    #             df = df.loc[df['label'].astype('bool'),
    #                  :]  # handle empty labels
    #             nwbfile.add_trial_column(
    #                 'speak',
    #                 'if True, subject is speaking. If False, subject is '
    #                 'listening')
    #             nwbfile.add_trial_column('condition', 'syllable spoken')
    #             for _, row in df.iterrows():
    #                 nwbfile.add_trial(
    #                     start_time=row['start'], stop_time=row['stop'],
    #                     speak=row['mode'] == 'speak', condition=row['label'])
    #         elif parse_transcript == 'emphasis':
    #             try:
    #                 df = make_df(parseout, 0, subject_id, align_pos=0)
    #             except:
    #                 df = pd.DataFrame(parseout)
    #             if not len(df):
    #                 df = pd.DataFrame(parseout)
    #             df = df.loc[df['label'].astype('bool'),
    #                  :]  # handle empty labels
    #             nwbfile.add_trial_column('condition', 'word emphasized')
    #             nwbfile.add_trial_column(
    #                 'speak',
    #                 'if True, subject is speaking. If False, subject is '
    #                 'listening')
    #             for _, row in df.iterrows():
    #                 nwbfile.add_trial(
    #                     start_time=row['start'], stop_time=row['stop'],
    #                     speak=True, condition=row['label'])
    #         elif parse_transcript == 'MOCHA':
    #             if behav_module is None:
    #                 behav_module = nwbfile.create_processing_module('behavior',
    #                                                                 'processing about behavior')
    #             transcript = create_transcription_ndx(transcript_path,
    #                                                   blockname)
    #             behav_module.add_data_interface(transcript)
    #
    # # behavior
    # if include_pitch:
    #     if behav_module is None:
    #         behav_module = nwbfile.create_processing_module('behavior',
    #                                                         'processing '
    #                                                         'about behavior')
    #     if os.path.isfile(
    #             os.path.join(blockpath, 'pitch_' + blockname + '.mat')):
    #         fs, data = load_pitch(blockpath)
    #         pitch_ts = TimeSeries(data=data, rate=fs, unit='Hz', name='pitch',
    #                               description='Pitch as extracted from '
    #                                           'Praat. NaNs mark unvoiced '
    #                                           'regions.')
    #         behav_module.add_container(
    #             BehavioralTimeSeries(name='pitch', time_series=pitch_ts))
    #     else:
    #         print('No pitch file for ' + blockname)
    #
    # if include_intensity:
    #     if behav_module is None:
    #         behav_module = nwbfile.create_processing_module('behavior',
    #                                                         'processing '
    #                                                         'about behavior')
    #     if os.path.isfile(
    #             os.path.join(blockpath, 'intensity_' + blockname + '.mat')):
    #         fs, data = load_pitch(blockpath)
    #         intensity_ts = TimeSeries(data=data, rate=fs, unit='dB',
    #                                   name='intensity',
    #                                   description='Intensity of speech in dB '
    #                                               'extracted from Praat.')
    #         behav_module.add_container(BehavioralTimeSeries(name='intensity',
    #                                                         time_series=intensity_ts))
    #     else:
    #         print('No intensity file for ' + blockname)

    if save_to_file:
        print('Saving HTK content to NWB file...')
        # Export the NWB file
        with NWBHDF5IO(str(out_file_path), manager=manager, mode='w') as io:
            io.write(nwbfile)

        # read check
        with NWBHDF5IO(str(out_file_path), manager=manager, mode='r') as io:
            io.read()
        print('NWB file saved: ', str(out_file_path))

    # if external_subject:
    #     subj_read_io.close()
    #
    # if hilb:
    #     file.close()

    return nwbfile, out_file_path, subject_id, blockname


def gen_external_subject(subject_id, basepath=None, imaging_path=None,
                         outpath=None, subject_image_list=None):
    subject = ECoGSubject(subject_id=subject_id)

    if subject_image_list is not None:
        subject = add_images_to_subject(subject, subject_image_list)

    if imaging_path is None:
        subj_imaging_path = path.join(IMAGING_PATH, subject_id)
    elif imaging_path == 'local':
        subj_imaging_path = path.join(basepath, 'imaging')
    else:
        subj_imaging_path = os.path.join(imaging_path, subject_id)

    mesh_path = path.join(subj_imaging_path, 'Meshes')
    pial_files = glob.glob(path.join(mesh_path, subject_id + '*pial.mat'))

    subject.cortical_surfaces = create_cortical_surfaces(pial_files,
                                                         subject_id)

    out_base_path = os.path.split(outpath)[0]
    subj_fpath = path.join(out_base_path, subject_id + '.nwb')
    subj_nwbfile = NWBFile(
        session_description=subject_id, identifier=subject_id, subject=subject,
        session_start_time=datetime(1900, 1, 1).astimezone(timezone('UTC')))
    with NWBHDF5IO(subj_fpath, manager=manager, mode='w') as subj_io:
        subj_io.write(subj_nwbfile)


def main():
    # Establish the assumptions about file paths
    raw = "RawHTK"
    analog = "Analog"
    artifacts = "Artifacts"
    meshes = "Meshes"
    desc = 'convert Raw ECoG data (in HTK) to NWB'
    epi = 'The following directories must be present: %s, %s, %s, and %s' % \
          (raw, analog, artifacts, meshes)

    parser = argparse.ArgumentParser(usage='%(prog)s data_dir out.nwb',
                                     description=desc, epilog=epi)
    parser.add_argument('blockpath', type=str,
                        help='the directory containing Raw ECoG data files')

    parser.add_argument('outfile', type=str,
                        help='the path to the NWB file to write to')

    parser.add_argument('-s', '--scale', action='store_true', default=False,
                        help='specifies whether or not to scale sampling rate')

    args = parser.parse_args()

    chang2nwb(**args)


if __name__ == '__main__':
    main()
