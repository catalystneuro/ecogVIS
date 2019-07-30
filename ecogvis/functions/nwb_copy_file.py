# -*- coding: utf-8 -*-
from datetime import datetime
from dateutil.tz import tzlocal
import numpy as np

from pynwb import NWBFile, NWBHDF5IO, get_manager, ProcessingModule
from pynwb.device import Device
from pynwb.ecephys import LFP, ElectricalSeries
from pynwb.core import DynamicTable, DynamicTableRegion, VectorData
from pynwb.epoch import TimeIntervals
from pynwb.misc import DecompositionSeries
from pynwb.base import TimeSeries
from pynwb.file import Subject
from ndx_spectrum import Spectrum
from nwbext_ecog import CorticalSurfaces, ECoGSubject


def nwb_copy_file(old_file, new_file, cp_objs={}):
    """
    Copy fields defined in 'obj', from existing NWB file to new NWB file.

    Parameters
    ----------
    old_file : str, path
        String such as '/path/to/old_file.nwb'.
    new_file : str, path
        String such as '/path/to/new_file.nwb'.
    cp_objs : dict
        Name:Value pairs (Group:Children) listing the groups and respective
        children from the current NWB file to be copied. Children can be:
        - Boolean, indicating an attribute (e.g. for institution, lab)
        - List of strings, containing several children names
        Example:
        {'institution':True,
         'lab':True,
         'acquisition':['microphone'],
         'ecephys':['LFP','DecompositionSeries']}
    """

    manager = get_manager()

    # Open original signal file
    with NWBHDF5IO(old_file, 'r', manager=manager, load_namespaces=True) as io1:
        nwb_old = io1.read()

        # Creates new file
        nwb_new = NWBFile(session_description=str(nwb_old.session_description),
                          identifier='',
                          session_start_time=datetime.now(tzlocal()))
        with NWBHDF5IO(new_file, mode='w', manager=manager, load_namespaces=False) as io2:
            #Institution name --------------------------------------------------
            if 'institution' in cp_objs:
                nwb_new.institution = str(nwb_old.institution)

            #Lab name ----------------------------------------------------------
            if 'lab' in cp_objs:
                nwb_new.lab = str(nwb_old.lab)

            #Session id --------------------------------------------------------
            if 'session' in cp_objs:
                nwb_new.session_id = nwb_old.session_id

            #Devices -----------------------------------------------------------
            if 'devices' in cp_objs:
                for aux in list(nwb_old.devices.keys()):
                    dev = Device(nwb_old.devices[aux].name)
                    nwb_new.add_device(dev)

            #Electrode groups --------------------------------------------------
            if 'electrode_groups' in cp_objs:
                for aux in list(nwb_old.electrode_groups.keys()):
                    nwb_new.create_electrode_group(name=nwb_old.electrode_groups[aux].name,
                                                   description=nwb_old.electrode_groups[aux].description,
                                                   location=nwb_old.electrode_groups[aux].location,
                                                   device=nwb_new.get_device(nwb_old.electrode_groups[aux].device.name))

            #Electrodes --------------------------------------------------------
            if 'electrodes' in cp_objs:
                nElec = len(nwb_old.electrodes['x'].data[:])
                for aux in np.arange(nElec):
                    nwb_new.add_electrode(x=nwb_old.electrodes['x'][aux],
                                          y=nwb_old.electrodes['y'][aux],
                                          z=nwb_old.electrodes['z'][aux],
                                          imp=nwb_old.electrodes['imp'][aux],
                                          location=nwb_old.electrodes['location'][aux],
                                          filtering=nwb_old.electrodes['filtering'][aux],
                                          group=nwb_new.get_electrode_group(nwb_old.electrodes['group'][aux].name),
                                          group_name=nwb_old.electrodes['group_name'][aux])
                # if there are custom variables
                new_vars = list(nwb_old.electrodes.colnames)
                default_vars = ['x', 'y', 'z', 'imp', 'location', 'filtering', 'group', 'group_name']
                [new_vars.remove(var) for var in default_vars]
                for var in new_vars:
                    nwb_new.add_electrode_column(name=var,
                                                 description=nwb_old.electrodes[var].description,
                                                 data=nwb_old.electrodes[var].data[:])

            #Epochs ------------------------------------------------------------
            if 'epochs' in cp_objs:
                nEpochs = len(nwb_old.epochs['start_time'].data[:])
                for i in np.arange(nEpochs):
                    nwb_new.add_epoch(start_time=nwb_old.epochs['start_time'].data[i],
                                      stop_time=nwb_old.epochs['stop_time'].data[i])
                # if there are custom variables
                new_vars = list(nwb_old.epochs.colnames)
                default_vars = ['start_time', 'stop_time', 'tags', 'timeseries']
                [new_vars.remove(var) for var in default_vars if var in new_vars]
                for var in new_vars:
                    nwb_new.add_epoch_column(name=var,
                                             description=nwb_old.epochs[var].description,
                                             data=nwb_old.epochs[var].data[:])

            #Invalid times -----------------------------------------------------
            if 'invalid_times' in cp_objs:
                nInvalid = len(nwb_old.invalid_times['start_time'][:])
                for aux in np.arange(nInvalid):
                    nwb_new.add_invalid_time_interval(start_time=nwb_old.invalid_times['start_time'][aux],
                                                      stop_time=nwb_old.invalid_times['stop_time'][aux])

            #Trials ------------------------------------------------------------
            if 'trials' in cp_objs:
                nTrials = len(nwb_old.trials['start_time'])
                for aux in np.arange(nTrials):
                    nwb_new.add_trial(start_time=nwb_old.trials['start_time'][aux],
                                      stop_time=nwb_old.trials['stop_time'][aux])
                # if there are custom variables
                new_vars = list(nwb_old.trials.colnames)
                default_vars = ['start_time', 'stop_time']
                [new_vars.remove(var) for var in default_vars]
                for var in new_vars:
                    nwb_new.add_trial_column(name=var,
                                             description=nwb_old.trials[var].description,
                                             data=nwb_old.trials[var].data[:])

            #Intervals ---------------------------------------------------------
            if 'intervals' in cp_objs:
                all_objs_names = list(nwb_old.intervals.keys())
                for obj_name in all_objs_names:
                    obj_old = nwb_old.intervals[obj_name]
                    #create and add TimeIntervals
                    obj = TimeIntervals(name=obj_old.name,
                                        description=obj_old.description)
                    nInt = len(obj_old['start_time'])
                    for ind in np.arange(nInt):
                        obj.add_interval(start_time=obj_old['start_time'][ind],
                                         stop_time=obj_old['stop_time'][ind])
                    #Add to file
                    nwb_new.add_time_intervals(obj)

            #Stimulus ----------------------------------------------------------
            if 'stimulus' in cp_objs:
                all_objs_names = list(nwb_old.stimulus.keys())
                for obj_name in all_objs_names:
                    obj_old = nwb_old.stimulus[obj_name]
                    obj = TimeSeries(name=obj_old.name,
                                     description=obj_old.description,
                                     data=obj_old.data[:],
                                     rate=obj_old.rate,
                                     resolution=obj_old.resolution,
                                     conversion=obj_old.conversion,
                                     starting_time=obj_old.starting_time,
                                     unit=obj_old.unit)
                    nwb_new.add_stimulus(obj)

            #Processing modules ------------------------------------------------
            if 'ecephys' in cp_objs:
                if cp_objs['ecephys'] is True:
                    all_proc_names = list(nwb_old.processing['ecephys'].data_interfaces.keys())
                else:  #list of items
                    all_proc_names = cp_objs['ecephys']
                # Add ecephys module to NWB file
                ecephys_module = ProcessingModule(name='ecephys',
                                                  description='Extracellular electrophysiology data.')
                nwb_new.add_processing_module(ecephys_module)
                for proc_name in all_proc_names:
                    obj_old = nwb_old.processing['ecephys'].data_interfaces[proc_name]
                    obj = copy_obj(obj_old, nwb_old, nwb_new)
                    if obj is not None:
                        ecephys_module.add_data_interface(obj)

            #Acquisition -------------------------------------------------------
            if 'acquisition' in cp_objs:
                if cp_objs['acquisition'] is True:
                    all_acq_names = list(nwb_old.acquisition.keys())
                else:  #list of items
                    all_acq_names = cp_objs['acquisition']
                for acq_name in all_acq_names:
                    obj_old = nwb_old.acquisition[acq_name]
                    obj = copy_obj(obj_old, nwb_old, nwb_new)
                    if obj is not None:
                        nwb_new.add_acquisition(obj)

            #Subject -----------------------------------------------------------
            if 'subject' in cp_objs:
                try:
                    cortical_surfaces = CorticalSurfaces()
                    surfaces = nwb_old.subject.cortical_surfaces.surfaces
                    for sfc in list(surfaces.keys()):
                        cortical_surfaces.create_surface(name=surfaces[sfc].name,
                                                         faces=surfaces[sfc].faces,
                                                         vertices=surfaces[sfc].vertices)
                    nwb_new.subject = ECoGSubject(cortical_surfaces=cortical_surfaces,
                                                  subject_id=nwb_old.subject.subject_id,
                                                  age=nwb_old.subject.age,
                                                  description=nwb_old.subject.description,
                                                  genotype=nwb_old.subject.genotype,
                                                  sex=nwb_old.subject.sex,
                                                  species=nwb_old.subject.species,
                                                  weight=nwb_old.subject.weight,
                                                  date_of_birth=nwb_old.subject.date_of_birth)
                except:
                    nwb_new.subject = Subject(age=nwb_old.subject.age,
                                              description=nwb_old.subject.description,
                                              genotype=nwb_old.subject.genotype,
                                              sex=nwb_old.subject.sex,
                                              species=nwb_old.subject.species,
                                              subject_id=nwb_old.subject.subject_id,
                                              weight=nwb_old.subject.weight,
                                              date_of_birth=nwb_old.subject.date_of_birth)

            #Write new file with copied fields
            io2.write(nwb_new, link_data=False)


def copy_obj(obj_old, nwb_old, nwb_new):
    """ Creates a copy of obj_old. """

    obj = None
    obj_type = type(obj_old).__name__

    #ElectricalSeries ----------------------------------------------------------
    if obj_type=='ElectricalSeries':
        nChannels = obj_old.electrodes.table['x'].data.shape[0]
        elecs_region = nwb_new.electrodes.create_region(name='electrodes',
                                                        region=np.arange(nChannels).tolist(),
                                                        description='')
        obj = ElectricalSeries(name=obj_old.name,
                               data=obj_old.data[:],
                               electrodes=elecs_region,
                               rate=obj_old.rate,
                               description=obj_old.description)

    #LFP -----------------------------------------------------------------------
    if obj_type=='LFP':
        obj = LFP(name=obj_old.name)
        els_name = list(obj_old.electrical_series.keys())[0]
        els = obj_old.electrical_series[els_name]
        nChannels = els.data.shape[1]
        elecs_region = nwb_new.electrodes.create_region(name='electrodes',
                                                        region=np.arange(nChannels).tolist(),
                                                        description='')
        obj_ts = obj.create_electrical_series(name=els.name,
                                              comments=els.comments,
                                              conversion=els.conversion,
                                              data=els.data[:],
                                              description=els.description,
                                              electrodes=elecs_region,
                                              rate=els.rate,
                                              resolution=els.resolution,
                                              starting_time=els.starting_time)

    #TimeSeries ----------------------------------------------------------------
    elif obj_type=='TimeSeries':
        obj = TimeSeries(name=obj_old.name,
                         description=obj_old.description,
                         data=obj_old.data[:],
                         rate=obj_old.rate,
                         resolution=obj_old.resolution,
                         conversion=obj_old.conversion,
                         starting_time=obj_old.starting_time,
                         unit=obj_old.unit)

    #DecompositionSeries -------------------------------------------------------
    elif obj_type=='DecompositionSeries':
        list_columns = []
        for item in obj_old.bands.columns:
            bp = VectorData(name=item.name,
                            description=item.description,
                            data=item.data[:])
            list_columns.append(bp)
        bandsTable = DynamicTable(name=obj_old.bands.name,
                                  description=obj_old.bands.description,
                                  columns=list_columns,
                                  colnames=obj_old.bands.colnames)
        obj = DecompositionSeries(name=obj_old.name,
                                  data=obj_old.data[:],
                                  description=obj_old.description,
                                  metric=obj_old.metric,
                                  unit=obj_old.unit,
                                  rate=obj_old.rate,
                                  #source_timeseries=lfp,
                                  bands=bandsTable,)

    #Spectrum ------------------------------------------------------------------
    elif obj_type=='Spectrum':
        file_elecs = nwb_new.electrodes
        nChannels = len(file_elecs['x'].data[:])
        elecs_region = file_elecs.create_region(name='electrodes',
                                                region=np.arange(nChannels).tolist(),
                                                description='')
        obj = Spectrum(name=obj_old.name,
                       frequencies=obj_old.frequencies[:],
                       power=obj_old.power,
                       electrodes=elecs_region)




    return obj
