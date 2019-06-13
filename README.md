# ecogVIS
Timeseries visualizer for Electrocorticography (ECoG) signals stored in [NWB](https://neurodatawithoutborders.github.io/) files. 

## Installation
To clone the repository and set up a conda environment, do:
```
$ git clone https://github.com/bendichter/ecogVIS.git
$ conda env create -f ecogVIS/make_env.yml
$ source activate ecog_vis
```

Alternatively, to install **ecogvis** directly in an existing environment:
```
$ pip install git+https://github.com/bendichter/ecogVIS.git
```

After activating the correct environment, there are two ways of starting the application. You can do it from the command line prompt:
```
$ cd ~/path_to/ecogVIS
$ python ecogvis.py                       <--- if left undefined, you'll be prompted to choose a file 
$ python ecogvis.py '/path_to/file.nwb'   <--- you can include the file path directly, as a string
```

You can also import ecog_vis and run it from a python instance. If the file does not exist (or if you provide an empty string ''), you'll be prompted to choose a file from a dialog.
```python
from ecogvis.ecogvis import main
import os

fpath = os.path.join('path_to','file.nwb')
main(fpath)
```

## Features
**ecogVIS** makes it intuitive and simple to viualize ECoG signals. It currently features:
- Select electrodes from specific brain areas
- Annotation tool
- Intervals marking

![screenshot1](media/screenshot_1.png)


## Examples
work in progress
