import numpy as np
from datetime import datetime
from dateutil.tz import tzlocal
from pynwb import NWBFile
from pynwb import NWBHDF5IO
from pynwb.ecephys import ElectricalSeries
from pynwb.ecephys import LFP
from ecogvis.signal_processing.periodogram import psd_estimate
import unittest


class periodogramTestCase(unittest.TestCase):

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

        self.electrode_table_region = self.nwbfile.create_electrode_table_region([0, 2], 'the first and third electrodes')

        self.rate = 5.0
        np.random.seed(1234)
        data_len = 50
        self.ephys_data = np.array([[0.76711663, 0.70811536],
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
        self.ephys_timestamps = np.arange(data_len) / self.rate

        

    def test_psd_estimate_raw(self):

        ephys_ts = ElectricalSeries('ElectricalSeries',
                                    self.ephys_data,
                                    self.electrode_table_region,
                                    starting_time=self.ephys_timestamps[0],
                                    rate=self.rate,
                                    resolution=0.001,
                                    comments="This data was randomly generated with numpy, using 1234 as the seed",
                                    description="Random numbers generated with numpy.random.rand")

        self.nwbfile.add_acquisition(ephys_ts)

        with NWBHDF5IO('ecephys_example.nwb', 'w') as io:
            io.write(self.nwbfile)

        psd_estimate('ecephys_example.nwb', 'raw')
        
        io = NWBHDF5IO('ecephys_example.nwb', 'r')
        nwbfile_in = io.read()
        
        Spectrum_fft_raw = nwbfile_in.processing['ecephys'].data_interfaces['Spectrum_fft_raw'].power[:]
        
        Spectrum_fft_raw_expected = np.array([[0.00000000e+00, 9.32150093e-33],
                                               [2.52788013e-02, 5.31733673e-02],
                                               [1.82396499e-02, 5.84488782e-03],
                                               [3.92897929e-02, 4.55653034e-02],
                                               [1.15060643e-01, 4.42044537e-02],
                                               [3.68706901e-04, 9.75174687e-05],
                                               [4.93647789e-02, 8.59638829e-02],
                                               [2.23976068e-02, 2.39712748e-02],
                                               [1.64736034e-03, 1.49408444e-02],
                                               [2.19939585e-02, 4.97337198e-02],
                                               [5.61308661e-02, 2.91244157e-02],
                                               [3.42469507e-02, 4.16667268e-02],
                                               [7.46670216e-02, 3.22025200e-02],
                                               [4.68794398e-02, 3.16590784e-02],
                                               [1.21172905e-01, 5.61342631e-02],
                                               [1.80178113e-02, 1.55382607e-02],
                                               [3.81391501e-02, 3.53454269e-03]])


        np.testing.assert_almost_equal(Spectrum_fft_raw,Spectrum_fft_raw_expected)
        
        Spectrum_welch_raw = nwbfile_in.processing['ecephys'].data_interfaces['Spectrum_welch_raw'].power[:]
        Spectrum_welch_raw_expected = np.array([[0.00213913, 0.00044904],
                                               [0.03040964, 0.08910539],
                                               [0.0476898 , 0.09236207],
                                               [0.01177005, 0.00949409],
                                               [0.00643496, 0.01212059],
                                               [0.00140033, 0.05965447],
                                               [0.06733389, 0.05905316],
                                               [0.04684629, 0.01423956],
                                               [0.00444179, 0.02149517],
                                               [0.0255754 , 0.03897136],
                                               [0.00133956, 0.02147899],
                                               [0.0002621 , 0.02569019],
                                               [0.01063481, 0.02097604],
                                               [0.02362226, 0.02488475],
                                               [0.06889825, 0.03086559],
                                               [0.09727786, 0.01151824],
                                               [0.06526025, 0.05238111],
                                               [0.01927571, 0.04279204],
                                               [0.03504444, 0.00742166],
                                               [0.08368458, 0.0106964 ],
                                               [0.05205703, 0.00381934],
                                               [0.04645789, 0.06377106],
                                               [0.13058409, 0.05153322],
                                               [0.07301973, 0.01396382],
                                               [0.05203894, 0.01870544],
                                               [0.04057161, 0.00124306]])

        np.testing.assert_almost_equal(Spectrum_welch_raw,Spectrum_welch_raw_expected)


    def test_psd_estimate_preprocessed(self):

        ephys_ts = ElectricalSeries('preprocessed',
                                    self.ephys_data,
                                    self.electrode_table_region,
                                    starting_time=self.ephys_timestamps[0],
                                    rate=self.rate,
                                    resolution=0.001,
                                    comments="This data was randomly generated with numpy, using 1234 as the seed",
                                    description="Random numbers generated with numpy.random.rand")

        lfp = LFP(ephys_ts)

        ecephys_module = self.nwbfile.create_processing_module(name='ecephys',
                                                       description='preprocessed ecephys data')

        self.nwbfile.processing['ecephys'].add(lfp)

        with NWBHDF5IO('ecephys_example.nwb', 'w') as io:
            io.write(self.nwbfile)

        psd_estimate('ecephys_example.nwb', 'preprocessed')
