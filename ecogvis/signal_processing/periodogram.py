import numpy as np
from scipy import signal as sgn
from pynwb import NWBHDF5IO, ProcessingModule
from ndx_spectrum import Spectrum

def psd_estimate(src_file, type):
    """
    Estimates Power Spectral Density from signals.

    Parameters
    ----------
    src_file : str or path
        Full path to the current NWB file.
    type : str
        ElectricalSeries source. 'raw' or 'preprocessed'.
    """

    #Open file
    with NWBHDF5IO(src_file, mode='r+') as io:
        nwb = io.read()

        #Source ElectricalSeries
        if type=='raw':
            data_obj = nwb.acquisition['ElectricalSeries']
        elif type=='preprocessed':
            data_obj = nwb.processing['ecephys'].data_interfaces['LFP'].electrical_series['preprocessed']

        nChannels = data_obj.data.shape[1]
        nSamples = data_obj.data.shape[0]
        # Using a power of 2 number of samples improves performance
        nBinsToUse = 2**(np.floor(np.log2(nSamples)).astype('int'))
        fs = data_obj.rate
        dF = .8            #Frequency bin size
        #Window length as power of 2 and keeps dF~0.05 Hz
        win_len = 2**(np.ceil(np.log2(fs/dF)).astype('int'))   #dF = fs/nfft
        for ch in np.arange(nChannels):  # Iterate over channels
            trace = data_obj.data[:, ch]
            fx, py = sgn.welch(trace, fs=fs, nperseg=win_len)
            if ch==0:
                PY = py.reshape(-1,1)
            else:
                PY = np.append(PY, py.reshape(-1,1), axis=1)


        #PSD shape: ('frequency', 'channel')
        spectrum_module = Spectrum(name='Spectrum_'+type,
                                   frequencies=fx,
                                   power=PY,
                                   source_timeseries=data_obj)
        # Processing module
        try:      # if ecephys module already exists
            ecephys_module = nwb.processing['ecephys']
        except:   # creates ecephys ProcessingModule
            ecephys_module = ProcessingModule(name='ecephys',
                                              description='Extracellular electrophysiology data.')
            # Add module to NWB file
            nwb.add_processing_module(ecephys_module)
            print('Created ecephys')
        ecephys_module.add_data_interface(spectrum_module)

        io.write(nwb)
        print('Spectrum_'+type+' added to file.')
