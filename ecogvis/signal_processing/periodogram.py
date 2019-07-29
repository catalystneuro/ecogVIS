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
    with NWBHDF5IO(src_file, mode='r+', load_namespaces=True) as io:
        nwb = io.read()

        #Source ElectricalSeries
        if type=='raw':
            data_obj = nwb.acquisition['ElectricalSeries']
        elif type=='preprocessed':
            data_obj = nwb.processing['ecephys'].data_interfaces['LFP'].electrical_series['preprocessed']

        nChannels = data_obj.data.shape[1]
        nSamples = data_obj.data.shape[0]
        fs = data_obj.rate
        #Welch - window length as power of 2 and keeps dF~0.05 Hz
        dF = .05            #Frequency bin size
        win_len_welch = 2**(np.ceil(np.log2(fs/dF)).astype('int'))   #dF = fs/nfft
        #FFT - using a power of 2 number of samples improves performance
        nfft = int(2**(np.floor(np.log2(nSamples)).astype('int')))
        fx_lim = 200.
        for ch in np.arange(nChannels):  # Iterate over channels
            trace = data_obj.data[:, ch]
            fx_w, py_w = sgn.welch(trace, fs=fs, nperseg=win_len_welch)
            fx_f, py_f = sgn.periodogram(trace, fs=fs, nfft=nfft)
            #saves PSD up to 200 Hz
            py_w = py_w[fx_w < fx_lim]
            fx_w = fx_w[fx_w < fx_lim]
            py_f = py_f[fx_f < fx_lim]
            fx_f = fx_f[fx_f < fx_lim]
            if ch==0:
                PY_welch = py_w.reshape(-1,1)
                PY_fft = py_f.reshape(-1,1)
            else:
                PY_welch = np.append(PY_welch, py_w.reshape(-1,1), axis=1)
                PY_fft = np.append(PY_fft, py_f.reshape(-1,1), axis=1)

        #Electrodes
        elecs_region = nwb.electrodes.create_region(name='electrodes',
                                                    region=np.arange(nChannels).tolist(),
                                                    description='all electrodes')

        #PSD shape: ('frequency', 'channel')
        spectrum_module_welch = Spectrum(name='Spectrum_welch_'+type,
                                         frequencies=fx_w,
                                         power=PY_welch,
                                         source_timeseries=data_obj,
                                         electrodes=elecs_region)

        spectrum_module_fft = Spectrum(name='Spectrum_fft_'+type,
                                       frequencies=fx_f,
                                       power=PY_fft,
                                       source_timeseries=data_obj,
                                       electrodes=elecs_region)
                                       
        # Processing module
        try:      # if ecephys module already exists
            ecephys_module = nwb.processing['ecephys']
        except:   # creates ecephys ProcessingModule
            ecephys_module = ProcessingModule(name='ecephys',
                                              description='Extracellular electrophysiology data.')
            # Add module to NWB file
            nwb.add_processing_module(ecephys_module)
            print('Created ecephys')
        ecephys_module.add_data_interface(spectrum_module_welch)
        ecephys_module.add_data_interface(spectrum_module_fft)

        io.write(nwb)
        print('Spectrum_welch_'+type+' added to file.')
        print('Spectrum_fft_'+type+' added to file.')
