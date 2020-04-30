from ecogvis.functions.nwb_copy_file import nwb_copy_file
from datetime import datetime
from dateutil.tz import tzlocal
import pynwb
import numpy as np
from numpy.testing import assert_array_equal
import os


def test_nwb_copy_file():
    # Create a nwb file to be copied
    path_here = os.path.dirname(os.path.abspath(__file__))
    path_old_file = os.path.join(path_here, 'old_file.nwb')
    nwbfile_old = create_random_nwbfile()
    with pynwb.NWBHDF5IO(path_old_file, 'w') as io:
        io.write(nwbfile_old)

    path_new_file = os.path.join(path_here, 'new_file.nwb')

    cp_objs = {
        'institution': True,
        'lab': True,
        'session': True,
        'devices': True,
        'electrode_groups': True,
        'electrodes': True,
        'epochs': True,
        'trials': True,
        'subject': True,
        'acquisition': ['raw_data', 'mic'],
        'stimulus': ['stim1', 'stim2'],
        'ecephys': ['LFP', 'high_gamma']
    }
    nwb_copy_file(
        old_file=path_old_file,
        new_file=path_new_file,
        cp_objs=cp_objs,
        save_to_file=True,
    )

    with pynwb.NWBHDF5IO(path_new_file, 'r') as io:
        nwbfile_new = io.read()

        assert nwbfile_new.institution == nwbfile_old.institution
        assert nwbfile_new.session_start_time == nwbfile_old.session_start_time
        assert nwbfile_new.devices is not None
        assert_array_equal(nwbfile_new.electrodes.columns[0][:], nwbfile_old.electrodes.columns[0][:])
        assert nwbfile_new.electrode_groups.keys() == nwbfile_old.electrode_groups.keys()
        for (v1, v2) in zip(nwbfile_new.stimulus.values(), nwbfile_old.stimulus.values()):
            assert_array_equal(v1.data, v2.data)
        for k in nwbfile_new.acquisition.keys():
            assert_array_equal(nwbfile_new.acquisition[k].data, nwbfile_old.acquisition[k].data)

    # Remove test nwb files
    os.remove(path_old_file)
    os.remove(path_new_file)


def create_random_nwbfile(add_processing=True, add_high_gamma=True):
    """
    Creates a NWB file with fields used by the Chang lab, with random fake data.

    Parameters
    ----------
    add_processing : boolean
        Whether to add processing (LFP) data or not.
    add_high_gamma : boolean
        Whether to add high_gamma (DecompositionSeries) data or not.

    Returns
    -------
    nwbfile : nwbfile object
    """
    # Create NWBFile
    start_time = datetime(2017, 4, 3, 11, tzinfo=tzlocal())
    nwbfile = pynwb.NWBFile(session_description='fake data', identifier='NWB123', session_start_time=start_time)

    # Basic fields
    nwbfile.institution = 'My institution'
    nwbfile.lab = 'My lab'
    nwbfile.subject = pynwb.file.Subject(age='5 months', description='description')

    # Add device and electrodes
    device = nwbfile.create_device(name='device')
    electrode_group = nwbfile.create_electrode_group(name='electrode_group0',
                                                     description="an electrode group",
                                                     location="somewhere in the hippocampus",
                                                     device=device)
    n_electrodes = 4
    for idx in np.arange(n_electrodes):
        nwbfile.add_electrode(id=idx,
                              x=1.0, y=2.0, z=3.0,
                              imp=float(-idx),
                              location='CA1', filtering='none',
                              group=electrode_group)

    # Add noise signal as raw data
    electrode_table_region = nwbfile.create_electrode_table_region(list(np.arange(n_electrodes)), 'electrodes_table_region')
    raw_len = 1000
    ephys_data = np.random.rand(raw_len * 4).reshape((raw_len, 4))
    ephys_ts = pynwb.ecephys.ElectricalSeries(
        name='raw_data',
        data=ephys_data,
        electrodes=electrode_table_region,
        starting_time=0.,
        rate=100.
    )
    nwbfile.add_acquisition(ephys_ts)

    # Add noise signal as processing data
    if add_processing:
        ecephys_module = nwbfile.create_processing_module(name='ecephys', description='preprocessed data')
        lfp_len = 100
        lfp_data = np.random.rand(lfp_len * 4).reshape((lfp_len, 4))
        lfp = pynwb.ecephys.LFP(name='LFP')
        lfp.create_electrical_series(
            name='processed_electrical_series',
            data=lfp_data,
            electrodes=electrode_table_region,
            rate=10.,
            starting_time=0.
        )
        ecephys_module.add_data_interface(lfp)

    # Add noise signal as decomposition series
    if add_processing and add_high_gamma:
        n_bands = 2
        hg_data = np.random.rand(lfp_len * n_electrodes * n_bands).reshape((lfp_len, n_electrodes, n_bands))
        decomp = pynwb.misc.DecompositionSeries(
            name='high_gamma',
            data=hg_data,
            metric='power',
            unit=' V**2/Hz',
            rate=10.,
        )
        ecephys_module.add_data_interface(decomp)

    # Add noise signals as speaker stimuli and mic recording acquisition
    stim1 = pynwb.TimeSeries(name='stim1', data=np.random.rand(raw_len), starting_time=0.0, rate=100., unit='')
    stim2 = pynwb.TimeSeries(name='stim2', data=np.random.rand(raw_len), starting_time=0.0, rate=100., unit='')
    nwbfile.add_stimulus(stim1)
    nwbfile.add_stimulus(stim2)

    mic = pynwb.TimeSeries(name='mic', data=np.random.rand(raw_len), starting_time=0.0, rate=100., unit='')
    nwbfile.add_acquisition(mic)

    return nwbfile
