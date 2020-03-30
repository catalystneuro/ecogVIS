import numpy as np
from datetime import datetime
from dateutil.tz import tzlocal
from pynwb import NWBFile
from pynwb import NWBHDF5IO
from pynwb.ecephys import ElectricalSeries
from pynwb.ecephys import LFP
from ecogvis.signal_processing.processing_data import high_gamma_estimation,spectral_decomposition,preprocess_raw_data,make_new_nwb
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

        rate = 5.0
        np.random.seed(1234)
        data_len = 50
        ephys_data = np.array([[0.76711663, 0.70811536],
                               [0.79686718, 0.55776083],
                               [0.96583653, 0.1471569 ],
                               [0.029647  , 0.59389349],
                               [0.1140657 , 0.95080985],
                               [0.32570741, 0.19361869],
                               [0.45781165, 0.92040257],
                               [0.87906916, 0.25261576],
                               [0.34800879, 0.18258873],
                               [0.90179605, 0.70652816],
                               [0.72665846, 0.90008784],
                               [0.7791638 , 0.59915478],
                               [0.29112524, 0.15139526],
                               [0.33517466, 0.65755178],
                               [0.07334254, 0.0550064 ],
                               [0.32319481, 0.5904818 ],
                               [0.85389857, 0.28706243],
                               [0.17306723, 0.13402121],
                               [0.99465383, 0.17949787],
                               [0.31754682, 0.5682914 ],
                               [0.00934857, 0.90064862],
                               [0.97724143, 0.55689468],
                               [0.08477384, 0.33300247],
                               [0.72842868, 0.14243537],
                               [0.55246894, 0.27304326],
                               [0.97449514, 0.66778691],
                               [0.25565329, 0.10831149],
                               [0.77618072, 0.78247799],
                               [0.76160391, 0.91440311],
                               [0.65862278, 0.56836758],
                               [0.20175569, 0.69829638],
                               [0.95219541, 0.88996329],
                               [0.99356736, 0.81870351],
                               [0.54512217, 0.45125405],
                               [0.89055719, 0.97326479],
                               [0.59341133, 0.3660745 ],
                               [0.32309469, 0.87142326],
                               [0.21563406, 0.73494519],
                               [0.36561909, 0.8016026 ],
                               [0.78273559, 0.70135538],
                               [0.62277659, 0.49368265],
                               [0.8405377 , 0.71209699],
                               [0.44390898, 0.03103486],
                               [0.36323976, 0.73072179],
                               [0.47556657, 0.34441697],
                               [0.64088043, 0.12620532],
                               [0.17146526, 0.73708649],
                               [0.12702939, 0.36964987],
                               [0.604334  , 0.10310444],
                               [0.80237418, 0.94555324]])
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

        with NWBHDF5IO('ecephys_exmpl.nwb', 'w') as io:
            io.write(nwbfile)
        

        nwbfile_new = NWBFile('my first synthetic recording', 'EXAMPLE_ID', datetime.now(tzlocal()),
                          experimenter='Dr. Bilbo Baggins',
                          lab='Bag End Laboratory',
                          institution='University of Middle Earth at the Shire',
                          experiment_description='I went on an adventure with thirteen dwarves to reclaim vast treasures.',
                          session_id='LONELYMTN')

        with NWBHDF5IO('new_ecephys_example.nwb', 'w') as io:
                io.write(nwbfile_new)
        
        
    def test_high_gamma_estimation(self):

        bands_vals=np.random.rand(2,10)*80+70
        high_gamma_estimation('ecephys_exmpl.nwb', bands_vals)

    def test_spectral_decomposition(self):

        bands_vals=np.random.rand(2,10)*80+70
        spectral_decomposition('ecephys_exmpl.nwb', bands_vals)

    def test_preprocess_raw_data(self):
 
        config = {'CAR':16,'Notch':60,'Downsample':400}
        preprocess_raw_data('ecephys_exmpl.nwb', config)
        
    def test_make_new_nwb(self):
         
        cp_objs = {
        'institution': True,
        'lab': True,
        'session':True,
        'devices':True,
        'electrode_groups':True,
        'electrodes':True,
        'intervals':True,
        'stimulus':True,
        'acquisition':'default',
        'ecephys':'default'}
         make_new_nwb('ecephys_exmpl.nwb','new_ecephys_example.nwb',cp_objs=cp_objs)
