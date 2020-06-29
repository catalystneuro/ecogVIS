import numpy as np
from datetime import datetime
from dateutil.tz import tzlocal
from pynwb import NWBFile
from pynwb import NWBHDF5IO
from pynwb.ecephys import ElectricalSeries
from pynwb.ecephys import LFP
from ecogvis.signal_processing.processing_data import high_gamma_estimation, spectral_decomposition, preprocess_raw_data, make_new_nwb
import unittest
import os

class ProcessingDataTestCase(unittest.TestCase):

    def setUp(self):
        here_path = os.path.dirname(os.path.abspath(__file__))

        # processed and raw example data
        self.processed_name = os.path.join(here_path,'example_ecephys.nwb')

        # temporary files
        self.test_name = 'ecephys_exmpl_test.nwb'
        self.copy_name = 'ecephys_exmpl_copy.nwb'

        # Pull out processing parameters
        with NWBHDF5IO(self.processed_name, 'r') as io:
            nwbfile = io.read()

            rate = nwbfile.processing['ecephys'].data_interfaces['LFP'].electrical_series['preprocessed'].rate
            self.config = {
                'referencing': ('CAR', 16),
                'Notch': 60,
                'Downsample': rate
            }

            bands = nwbfile.processing['ecephys'].data_interfaces['DecompositionSeries'].bands
            self.bands_vals = bands.to_dataframe().to_numpy().T
            # Note: assumes that high gamma was generated with the same bands

    def test_processing(self):
        # Test copying
        try:
            self.step1_make_new_nwb()
        except Exception as e:
            self.fail("{} failed ({}: {})".format('step1_make_new_nwb', type(e), e))

        # Make a copy of the processed nwb that only has raw data
        # Note: assumes that copying works
        cp_objs = {
            'institution': True,
            'lab': True,
            'session': True,
            'devices': True,
            'electrode_groups': True,
            'electrodes': True,
            'acquisition':['raw']
        }
        make_new_nwb(self.processed_name, self.test_name, cp_objs=cp_objs)

        # Test preprocessing
        try:
            self.step2_preprocess_raw_data()
        except Exception as e:
            self.fail("{} failed ({}: {})".format('step2_preprocess_raw_data', type(e), e))

        # Test Spectral decomposition
        # Note: assumes that preprocessing ran correctly on the test file
        try:
            self.step3_spectral_decomposition()
        except Exception as e:
            self.fail("{} failed ({}: {})".format('step3_spectral_decomposition', type(e), e))

        # Test High Gamma estimation
        # Note: assumes that preprocessing ran correctly on the test file
        try:
            self.step4_high_gamma_estimation()
        except Exception as e:
            self.fail("{} failed ({}: {})".format('step4_high_gamma_estimation', type(e), e))

        # Remove the testing nwb file
        os.remove(self.test_name)

    def tearDown(self):
        # If there wasn't an error, these files will have been removed already
        try:
            os.remove(self.test_name)
        except FileNotFoundError as e:
            pass
        try:
            os.remove(self.copy_name)
        except FileNotFoundError as e:
            pass

    def step1_make_new_nwb(self):
        cp_objs = {
            'institution': True,
            'lab': True,
            'session': True,
            'devices': True,
            'electrode_groups': True,
            'electrodes': True,
            'intervals': True,
            'stimulus': True,
            'acquisition': 'default',
            'ecephys': 'default'
        }
        make_new_nwb(self.processed_name, self.copy_name, cp_objs=cp_objs)

        with NWBHDF5IO(self.processed_name, 'r') as io1:
            nwbfile_in = io1.read()
            with NWBHDF5IO(self.copy_name, 'r') as io2:
                new_nwbfile_in = io2.read()
                # Check that they have the same elements (symmetric set difference is empty)
                assert not ((set(cp_objs.keys()) & set(new_nwbfile_in.fields.keys())) ^ \
                        (set(cp_objs.keys()) & set(nwbfile_in.fields.keys())))

                # (May want to add deeper checks here)

        os.remove(self.copy_name)

    def step2_preprocess_raw_data(self):
        # Make sure there is no existing preprocessed data in the test file
        with NWBHDF5IO(self.test_name, 'r') as io:
            nwbfile_test = io.read()
            assert not(nwbfile_test.processing)

        # Run preprocessing
        preprocess_raw_data(self.test_name, self.config)

        # Check that it matches the processed file
        with NWBHDF5IO(self.test_name, 'r') as io:
            nwbfile_test = io.read()
            lfp_data = nwbfile_test.processing['ecephys'].data_interfaces['LFP'].electrical_series['preprocessed'].data[:]

        with NWBHDF5IO(self.processed_name, 'r') as io:
            nwbfile_correct = io.read()
            lfp_data_expected = nwbfile_correct.processing['ecephys'].data_interfaces['LFP'].electrical_series['preprocessed'].data[:]

        np.testing.assert_almost_equal(lfp_data, lfp_data_expected)

    def step3_spectral_decomposition(self):
        # Make sure there is no Decomposition data in the test file
        with NWBHDF5IO(self.test_name, 'r') as io:
            nwbfile_test = io.read()
            assert 'DecompositionSeries' not in nwbfile_test.processing['ecephys'].data_interfaces

        # Run decomposition
        spectral_decomposition(self.test_name, self.bands_vals)

        # Check that it matches the processed file
        with NWBHDF5IO(self.test_name, 'r') as io:
            nwbfile_test = io.read()
            decomposition_data = nwbfile_test.processing['ecephys'].data_interfaces['DecompositionSeries'].data[:]

        with NWBHDF5IO(self.processed_name, 'r') as io:
            nwbfile_correct = io.read()
            decomposition_data_expected = nwbfile_correct.processing['ecephys'].data_interfaces['DecompositionSeries'].data[:]

        np.testing.assert_almost_equal(decomposition_data, decomposition_data_expected)

    def step4_high_gamma_estimation(self):
        # Make sure there is no High Gamma data in the test file
        with NWBHDF5IO(self.test_name, 'r') as io:
            nwbfile_test = io.read()
            assert 'high_gamma' not in nwbfile_test.processing['ecephys'].data_interfaces

        # Run high gamma
        high_gamma_estimation(self.test_name, self.bands_vals)

        # Check that it matches the processed file
        with NWBHDF5IO(self.test_name, 'r') as io:
            nwbfile_test = io.read()
            high_gamma_data = nwbfile_test.processing['ecephys'].data_interfaces['high_gamma'].data[:]

        with NWBHDF5IO(self.processed_name, 'r') as io:
            nwbfile_correct = io.read()
            high_gamma_data_expected = nwbfile_correct.processing['ecephys'].data_interfaces['high_gamma'].data[:]

        np.testing.assert_almost_equal(high_gamma_data, high_gamma_data_expected)


