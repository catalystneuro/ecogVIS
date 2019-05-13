# ecogVIS
Timeseries visualizer for ECoG signals stored in [NWB](https://neurodatawithoutborders.github.io/) files. 

## Installation
To clone the repository and set up a conda environment, do:
```
$ git clone https://github.com/luiztauffer/ecogVIS
$ conda env create -f ecogVIS/make_env.yml
$ source activate ecog_vis
```
After activating the ecog_vis environment, there are two ways of starting the application. You can do it from the command line prompt:
```
$ cd ~/path_to/ecogVIS
$ python ecog_vis.py                       <--- if left undefined, you'll be prompted to choose a file 
$ python ecog_vis.py '/path_to/file.nwb'   <--- you can include the file path directly, as a string
```

You can also import ecog_vis and run it from a python instance:
```python
from ecog_vis import main
import os

fpath = os.path.join('path_to','file.nwb')
main(fpath)
```

## Examples
work in progress
