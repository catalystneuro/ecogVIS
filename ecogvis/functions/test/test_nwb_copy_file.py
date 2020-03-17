import numpy as np
from datetime import datetime
from dateutil.tz import tzlocal
from pynwb import NWBFile
from pynwb import NWBHDF5IO
from pynwb.ecephys import ElectricalSeries
from pynwb.ecephys import LFP
from ecogvis.functions.nwb_copy_file import nwb_copy_file
import unittest

class FunctionCopyTestCase(unittest.TestCase):

    def setUp(self):
        
        start_time = datetime(2017, 4, 3, 11, tzinfo=tzlocal())
        create_date = datetime(2017, 4, 15, 12, tzinfo=tzlocal())
        
        self.nwbfile = NWBFile('my first synthetic recording', 'EXAMPLE_ID', datetime.now(tzlocal()),
                          experimenter='Dr. Bilbo Baggins',
                          lab='Bag End Laboratory',
                          institution='University of Middle Earth at the Shire',
                          experiment_description='I went on an adventure with thirteen dwarves to reclaim vast treasures.',
                          session_id='LONELYMTN')

        device = self.nwbfile.create_device(name='trodes_rig123')

        electrode_name = 'tetrode1'
        description = "an example tetrode"
        location = "somewhere in the hippocampus"

        electrode_group = self.nwbfile.create_electrode_group(electrode_name,
                                                         description=description,
                                                         location=location,
                                                         device=device)

        for idx in [1, 2, 3, 4]:
            self.nwbfile.add_electrode(id=idx,
                                  x=1.0, y=2.0, z=3.0,
                                  imp=float(-idx),
                                  location='CA1', filtering='none',
                                  group=electrode_group)

        electrode_table_region = self.nwbfile.create_electrode_table_region([0, 2], 'the first and third electrodes')

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
        
        self.lfp = LFP(ephys_ts)

        ecephys_module = self.nwbfile.create_processing_module(name='ecephys',
                                                       description='preprocessed ecephys data')

        self.nwbfile.processing['ecephys'].add(self.lfp)

        with NWBHDF5IO('ecephys_example.nwb', 'w') as io:
            io.write(self.nwbfile)
        

        nwbfile_new = NWBFile('my first synthetic recording', 'EXAMPLE_ID', datetime.now(tzlocal()),
                          experimenter='Dr. Bilbo Baggins',
                          lab='Bag End Laboratory',
                          institution='University of Middle Earth at the Shire',
                          experiment_description='I went on an adventure with thirteen dwarves to reclaim vast treasures.',
                          session_id='LONELYMTN')

        with NWBHDF5IO('new_ecephys_example.nwb', 'w') as io:
                io.write(self.nwbfile_new)
        
    def test_nwb_copy_file(self):
         
        cp_objs = {
        'institution': True,
        'lab': True,
        'session':True,
        'devices':True,
        'electrode_groups':True,
        'electrodes':True,
        'intervals':True,
        'stimulus':True}
         nwb_copy_file('ecephys_example.nwb','new_ecephys_example.nwb',cp_objs=cp_objs)
         
    def test_copy_obj(self):
        
        copy_obj(self.lfp,1,self.nwbfile)
