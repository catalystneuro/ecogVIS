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
- Seamless visual navigation through long signals from large arrays of electrodes 
- Select electrodes from specific brain areas
- Signal preprocessing: resampling and filtering
- Spectral Decomposition
- High Gamma power estimation
- Annotations and Intervals creation tool
- Event-Related Potential analysis
- Periodogram analysis

![screenshot1](media/screenshot_1.png)


## Examples
work in progress
