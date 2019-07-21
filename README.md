# ecogVIS
Timeseries visualizer for Electrocorticography (ECoG) signals stored in [NWB](https://neurodatawithoutborders.github.io/) files. 

## Installation
To clone the repository and set up a conda environment, do:
```
$ git clone https://github.com/bendichter/ecogVIS.git
$ conda env create -f ecogVIS/make_env.yml
$ source activate ecog_vis
```

Alternatively, to install **ecogVIS** directly in an existing environment:
```
$ pip install git+https://github.com/bendichter/ecogVIS.git
```

After activating the correct environment, **ecogVIS** can be imported and run from python. If the file does not exist (or if you provide an empty string ''), you'll be prompted to choose a file from a dialog.
```python
from ecogvis.ecogvis import main
import os

fpath = os.path.join('path_to','file.nwb')
main(fpath)
```


## Features
**ecogVIS** makes it intuitive and simple to viualize and process ECoG signals. It currently features:

**Navigation** <br>
Seamless visual navigation through long signals from large arrays of electrodes, by mouse-dragging visualization window, control buttons, value fields and keyboard keys.

![](media/gif_time_navigation.gif)

![](media/gif_channel_navigation.gif)


**Annotations** <br>
Add, delete, save and load annotations for meaningful comments anywhere in the visualization.

![](media/gif_annotations.gif)


**Intervals** <br> 
Add, delete, save, load and create custom intervals types to mark specific points in time, with simple click-drag-release mouse movements.

![](media/gif_intervals.gif)


**Bad Channels** <br>
Mark and un-mark bad channels. Choices are saved in the `electrodes` group of the current NWB file.

![](media/gif_badchannels.gif)


**Signal preprocessing** <br>
Preprocessing of raw voltage signals, including user-defined Downsampling, CAR and Notch filtering. The resulting processed signals are stored as an [LFP](https://pynwb.readthedocs.io/en/stable/pynwb.ecephys.html#pynwb.ecephys.LFP) object, in the `processing` group of the current NWB file.

![](media/gif_preprocessing.gif)


**Event detection** <br>
Automatic detection of events in audio recordings for Consonant-Vowel tasks. The audio data should be stored in the NWB file in the following way: <br>
  Speaker audio - As a [TimeSeries](https://pynwb.readthedocs.io/en/stable/pynwb.base.html#pynwb.base.TimeSeries) object, named 'Speaker CV', in the `stimulus` group. <br>
  Microphone audio - As a [TimeSeries](https://pynwb.readthedocs.io/en/stable/pynwb.base.html#pynwb.base.TimeSeries) object, named 'Microphone CV', in the `acquisition` group. <br>

The resulting detected intervals, 'TimeIntervals_mic' and 'TimeIntervals_speaker', are saved as [TimeIntervals](https://pynwb.readthedocs.io/en/stable/pynwb.epoch.html#pynwb.epoch.TimeIntervals) objects in the `intervals` group of the current NWB file and can be used later for ERP analysis. A preview allows for testing of the detection parameters before running it for the whole duration of the audio signals. 

![](media/gif_event_detection.gif)


**Plus:**
- Select electrodes from specific brain areas
- Spectral Decomposition
- High Gamma power estimation
- Event-Related Potential analysis
- Periodogram analysis
