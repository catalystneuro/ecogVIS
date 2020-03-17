import numpy as np
from datetime import datetime
from dateutil.tz import tzlocal
from pynwb import NWBFile
from pynwb import NWBHDF5IO
from pynwb.ecephys import ElectricalSeries
from pynwb.ecephys import LFP
from ecogvis.signal_processing.processing_data import high_gamma_estimation,spectral_decomposition,preprocess_raw_data
import unittest


class ProcessingDataTestCase(unittest.TestCase):

    def setUp(self):
        
        start_time = datetime(2017, 4, 3, 11, tzinfo=tzlocal())
        create_date = datetime(2017, 4, 15, 12, tzinfo=tzlocal())
        
        nwbfile = NWBFile('my first synthetic recording', 'EXAMPLE_ID', datetime.now(tzlocal()),
                          experimenter='Dr. Bilbo Baggins',
                          lab='Bag End Laboratory',
                          institution='University of Middle Earth at the Shire',
                          experiment_description='I went on an adventure with thirteen dwarves to reclaim vast treasures.',
                          session_id='LONELYMTN')

        device = nwbfile.create_device(name='trodes_rig123')

        electrode_name = 'tetrode1'
        description = "an example tetrode"
        location = "somewhere in the hippocampus"

        electrode_group = nwbfile.create_electrode_group(electrode_name,
                                                         description=description,
                                                         location=location,
                                                         device=device)

        for idx in [1, 2, 3, 4]:
            nwbfile.add_electrode(id=idx,
                                  x=1.0, y=2.0, z=3.0,
                                  imp=float(-idx),
                                  location='CA1', filtering='none',
                                  group=electrode_group)

        electrode_table_region = nwbfile.create_electrode_table_region([0, 2], 'the first and third electrodes')

        rate = 10.0
        np.random.seed(1234)
        data_len = 1000
        ephys_data = np.random.rand(data_len * 2).reshape((data_len, 2))
        ephys_timestamps = np.arange(data_len) / rate

        ephys_ts = ElectricalSeries('preprocessed',
                                    ephys_data,
                                    electrode_table_region,
                                    starting_time=ephys_timestamps[0],
                                    rate=rate,
                                    resolution=0.001,
                                    comments="This data was randomly generated with numpy, using 1234 as the seed",
                                    description="Random numbers generated with numpy.random.rand")
        
         lfp = LFP(ephys_ts)

        ecephys_module = nwbfile.create_processing_module(name='ecephys',
                                                       description='preprocessed ecephys data')

        nwbfile.processing['ecephys'].add(lfp)

        with NWBHDF5IO('ecephys_example.nwb', 'w') as io:
            io.write(nwbfile)
        
    def test_high_gamma_estimation(self):

        bands_vals=np.random.rand(2,10)*80+70
        high_gamma_estimation('ecephys_example.nwb', bands_vals)

    def test_spectral_decomposition(self):

        bands_vals=np.random.rand(2,10)*80+70
        spectral_decomposition('ecephys_example.nwb', bands_vals)

    def test_preprocess_raw_data(self):
 
        config = {'CAR':16,'Notch':60,'Downsample':400}
        preprocess_raw_data('ecephys_example.nwb', config)
