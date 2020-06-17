# -*- coding: utf-8 -*-
import numpy as np
from hdmf.common.table import DynamicTable, VectorData
from ndx_spectrum import Spectrum
from ndx_survey_data.survey_definitions import nrs_survey_table, mpq_survey_table, vas_survey_table
from ndx_bipolar_scheme import BipolarSchemeTable, EcephysExt
from nwbext_ecog import CorticalSurfaces, ECoGSubject
from pynwb import NWBFile, NWBHDF5IO, get_manager, ProcessingModule
from pynwb.base import TimeSeries
from pynwb.device import Device
from pynwb.ecephys import LFP, ElectricalSeries
from pynwb.epoch import TimeIntervals
from pynwb.file import Subject, DynamicTableRegion
from pynwb.misc import DecompositionSeries
import string
import random


def id_generator(size=6, chars=string.ascii_uppercase + string.digits):
    return ''.join(random.choice(chars) for _ in range(size))


def nwb_copy_file(old_file, new_file, cp_objs={}, save_to_file=True):
    """
    Copy fields defined in 'obj', from existing NWB file to new NWB file.

    Parameters
    ----------
    old_file : str, path, nwbfile
        String or path to nwb file '/path/to/old_file.nwb'. Alternatively, the
        nwbfile object.
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
    save_to_file: Boolean
        If True, saves directly to new_file.nwb. If False, only returns nwb_new.

    Returns:
    --------
    nwb_new : nwbfile object
    """

    manager = get_manager()

    # Get from nwbfile object in memory or from file
    if isinstance(old_file, NWBFile):
        nwb_old = old_file
        io1 = False
    else:
        io1 = NWBHDF5IO(str(old_file), 'r', manager=manager, load_namespaces=True)
        nwb_old = io1.read()

    # Creates new file
    nwb_new = NWBFile(
        session_description=str(nwb_old.session_description),
        identifier=id_generator(),
        session_start_time=nwb_old.session_start_time,
    )
    with NWBHDF5IO(new_file, mode='w', manager=manager, load_namespaces=False) as io2:
        # Institution name ------------------------------------------------
        if 'institution' in cp_objs:
            nwb_new.institution = str(nwb_old.institution)

        # Lab name --------------------------------------------------------
        if 'lab' in cp_objs:
            nwb_new.lab = str(nwb_old.lab)

        # Session id ------------------------------------------------------
        if 'session' in cp_objs:
            nwb_new.session_id = nwb_old.session_id

        # Devices ---------------------------------------------------------
        if 'devices' in cp_objs:
            for aux in list(nwb_old.devices.keys()):
                dev = Device(nwb_old.devices[aux].name)
                nwb_new.add_device(dev)

        # Electrode groups ------------------------------------------------
        if 'electrode_groups' in cp_objs and nwb_old.electrode_groups is not None:
            for aux in list(nwb_old.electrode_groups.keys()):
                nwb_new.create_electrode_group(
                    name=str(nwb_old.electrode_groups[aux].name),
                    description=str(nwb_old.electrode_groups[
                        aux].description),
                    location=str(nwb_old.electrode_groups[aux].location),
                    device=nwb_new.get_device(
                        nwb_old.electrode_groups[aux].device.name)
                )

        # Electrodes ------------------------------------------------------
        if 'electrodes' in cp_objs and nwb_old.electrodes is not None:
            nElec = len(nwb_old.electrodes['x'].data[:])
            for aux in np.arange(nElec):
                nwb_new.add_electrode(
                    x=nwb_old.electrodes['x'][aux],
                    y=nwb_old.electrodes['y'][aux],
                    z=nwb_old.electrodes['z'][aux],
                    imp=nwb_old.electrodes['imp'][aux],
                    location=str(nwb_old.electrodes['location'][aux]),
                    filtering=str(nwb_old.electrodes['filtering'][aux]),
                    group=nwb_new.get_electrode_group(
                        nwb_old.electrodes['group'][aux].name),
                    group_name=str(nwb_old.electrodes['group_name'][aux])
                )
            # if there are custom variables
            new_vars = list(nwb_old.electrodes.colnames)
            default_vars = ['x', 'y', 'z', 'imp', 'location', 'filtering',
                            'group', 'group_name']
            [new_vars.remove(var) for var in default_vars]
            for var in new_vars:
                if var == 'label':
                    var_data = [str(elem) for elem in nwb_old.electrodes[var].data[:]]
                else:
                    var_data = np.array(nwb_old.electrodes[var].data[:])

                nwb_new.add_electrode_column(
                    name=str(var),
                    description=str(nwb_old.electrodes[var].description),
                    data=var_data
                )

            # If Bipolar scheme for electrodes
            for v in nwb_old.lab_meta_data.values():
                if isinstance(v, EcephysExt) and hasattr(v, 'bipolar_scheme_table'):
                    bst_old = v.bipolar_scheme_table
                    bst_new = BipolarSchemeTable(
                        name=bst_old.name,
                        description=bst_old.description
                    )
                    ecephys_ext = EcephysExt(name=v.name)
                    ecephys_ext.bipolar_scheme_table = bst_new
                    nwb_new.add_lab_meta_data(ecephys_ext)

        # Epochs ----------------------------------------------------------
        if 'epochs' in cp_objs and nwb_old.epochs is not None:
            nEpochs = len(nwb_old.epochs['start_time'].data[:])
            for i in np.arange(nEpochs):
                nwb_new.add_epoch(
                    start_time=nwb_old.epochs['start_time'].data[i],
                    stop_time=nwb_old.epochs['stop_time'].data[i])
            # if there are custom variables
            new_vars = list(nwb_old.epochs.colnames)
            default_vars = ['start_time', 'stop_time', 'tags',
                            'timeseries']
            [new_vars.remove(var) for var in default_vars if
             var in new_vars]
            for var in new_vars:
                nwb_new.add_epoch_column(
                    name=var,
                    description=nwb_old.epochs[var].description,
                    data=nwb_old.epochs[var].data[:]
                )

        # Invalid times ---------------------------------------------------
        if 'invalid_times' in cp_objs and nwb_old.invalid_times is not None:
            nInvalid = len(nwb_old.invalid_times['start_time'][:])
            for aux in np.arange(nInvalid):
                nwb_new.add_invalid_time_interval(
                    start_time=nwb_old.invalid_times['start_time'][aux],
                    stop_time=nwb_old.invalid_times['stop_time'][aux]
                )

        # Trials ----------------------------------------------------------
        if 'trials' in cp_objs and nwb_old.trials is not None:
            nTrials = len(nwb_old.trials['start_time'])
            for aux in np.arange(nTrials):
                nwb_new.add_trial(
                    start_time=nwb_old.trials['start_time'][aux],
                    stop_time=nwb_old.trials['stop_time'][aux])
            # if there are custom variables
            new_vars = list(nwb_old.trials.colnames)
            default_vars = ['start_time', 'stop_time']
            [new_vars.remove(var) for var in default_vars]
            for var in new_vars:
                nwb_new.add_trial_column(
                    name=var,
                    description=nwb_old.trials[var].description,
                    data=nwb_old.trials[var].data[:]
                )

        # Intervals -------------------------------------------------------
        if 'intervals' in cp_objs and nwb_old.intervals is not None:
            all_objs_names = list(nwb_old.intervals.keys())
            for obj_name in all_objs_names:
                obj_old = nwb_old.intervals[obj_name]
                # create and add TimeIntervals
                obj = TimeIntervals(name=obj_old.name,
                                    description=obj_old.description)
                nInt = len(obj_old['start_time'])
                for ind in np.arange(nInt):
                    obj.add_interval(start_time=obj_old['start_time'][ind],
                                     stop_time=obj_old['stop_time'][ind])
                # Add to file
                nwb_new.add_time_intervals(obj)

        # Stimulus --------------------------------------------------------
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

        # Processing modules ----------------------------------------------
        if 'ecephys' in cp_objs:
            interfaces = [nwb_old.processing['ecephys'].data_interfaces[key]
                          for key in cp_objs['ecephys']]
            # Add ecephys module to NWB file
            ecephys_module = ProcessingModule(
                name='ecephys',
                description='Extracellular electrophysiology data.'
            )
            nwb_new.add_processing_module(ecephys_module)
            for interface_old in interfaces:
                obj = copy_obj(interface_old, nwb_old, nwb_new)
                if obj is not None:
                    ecephys_module.add_data_interface(obj)

        if 'behavior' in cp_objs:
            interfaces = [nwb_old.processing['behavior'].data_interfaces[key]
                          for key in cp_objs['behavior']]
            if 'behavior' not in nwb_new.processing:
                # Add behavior module to NWB file
                behavior_module = ProcessingModule(
                    name='behavior',
                    description='behavioral data.'
                )
                nwb_new.add_processing_module(behavior_module)
            for interface_old in interfaces:
                obj = copy_obj(interface_old, nwb_old, nwb_new)
                if obj is not None:
                    behavior_module.add_data_interface(obj)

        # Acquisition -----------------------------------------------------
        # Can get raw ElecetricalSeries and Mic recording
        if 'acquisition' in cp_objs:
            for acq_name in cp_objs['acquisition']:
                obj_old = nwb_old.acquisition[acq_name]
                acq = copy_obj(obj_old, nwb_old, nwb_new)
                nwb_new.add_acquisition(acq)

        # Surveys ---------------------------------------------------------
        if 'surveys' in cp_objs and 'behavior' in nwb_old.processing:
            surveys_list = [v for v in nwb_old.processing['behavior'].data_interfaces.values()
                            if v.neurodata_type == 'SurveyTable']
            if cp_objs['surveys'] and len(surveys_list) > 0:
                if 'behavior' not in nwb_new.processing:
                    # Add behavior module to NWB file
                    behavior_module = ProcessingModule(
                        name='behavior',
                        description='behavioral data.'
                    )
                    nwb_new.add_processing_module(behavior_module)
                for obj_old in surveys_list:
                    srv = copy_obj(obj_old, nwb_old, nwb_new)
                    behavior_module.add_data_interface(srv)

        # Subject ---------------------------------------------------------
        if nwb_old.subject is not None:
            if 'subject' in cp_objs:
                try:
                    cortical_surfaces = CorticalSurfaces()
                    surfaces = nwb_old.subject.cortical_surfaces.surfaces
                    for sfc in list(surfaces.keys()):
                        cortical_surfaces.create_surface(
                            name=surfaces[sfc].name,
                            faces=surfaces[sfc].faces,
                            vertices=surfaces[sfc].vertices)
                    nwb_new.subject = ECoGSubject(
                        cortical_surfaces=cortical_surfaces,
                        subject_id=nwb_old.subject.subject_id,
                        age=nwb_old.subject.age,
                        description=nwb_old.subject.description,
                        genotype=nwb_old.subject.genotype,
                        sex=nwb_old.subject.sex,
                        species=nwb_old.subject.species,
                        weight=nwb_old.subject.weight,
                        date_of_birth=nwb_old.subject.date_of_birth)
                except:
                    nwb_new.subject = Subject(**nwb_old.subject.fields)

        # Write new file with copied fields
        if save_to_file:
            io2.write(nwb_new, link_data=False)

    # Close old file and return new nwbfile object
    if io1:
        io1.close()

    return nwb_new


def copy_obj(obj_old, nwb_old, nwb_new):
    """ Creates a copy of obj_old. """

    # ElectricalSeries --------------------------------------------------------
    if type(obj_old) is ElectricalSeries:
        # If reference electrodes table is bipolar scheme
        if isinstance(obj_old.electrodes.table, BipolarSchemeTable):
            bst_old = obj_old.electrodes.table
            bst_old_df = bst_old.to_dataframe()
            bst_new = nwb_new.lab_meta_data['ecephys_ext'].bipolar_scheme_table

            for id, row in bst_old_df.iterrows():
                index_anodes = row['anodes'].index.tolist()
                index_cathodes = row['cathodes'].index.tolist()
                bst_new.add_row(anodes=index_anodes, cathodes=index_cathodes)
            bst_new.anodes.table = nwb_new.electrodes
            bst_new.cathodes.table = nwb_new.electrodes

            # if there are custom columns
            new_cols = list(bst_old_df.columns)
            default_cols = ['anodes', 'cathodes']
            [new_cols.remove(col) for col in default_cols]
            for col in new_cols:
                col_data = list(bst_old[col].data[:])
                bst_new.add_column(
                    name=str(col),
                    description=str(bst_old[col].description),
                    data=col_data
                )

            elecs_region = DynamicTableRegion(
                name='electrodes',
                data=bst_old_df.index.tolist(),
                description='desc',
                table=bst_new
            )
        else:
            region = np.array(obj_old.electrodes.table.id[:])[obj_old.electrodes.data[:]].tolist()
            elecs_region = nwb_new.create_electrode_table_region(
                name='electrodes',
                region=region,
                description=''
            )
        els = ElectricalSeries(
            name=obj_old.name,
            data=obj_old.data[:],
            electrodes=elecs_region,
            rate=obj_old.rate,
            description=obj_old.description
        )
        return els

    # DynamicTable ------------------------------------------------------------
    if type(obj_old) is DynamicTable:
        return DynamicTable(
            name=obj_old.name,
            description=obj_old.description,
            colnames=obj_old.colnames,
            columns=obj_old.columns,
        )

    # LFP ---------------------------------------------------------------------
    if type(obj_old) is LFP:
        obj = LFP(name=obj_old.name)
        assert len(obj_old.electrical_series) == 1, (
            'Expected precisely one electrical series, got %i!' %
            len(obj_old.electrical_series))
        els = list(obj_old.electrical_series.values())[0]

        ####
        # first check for a table among the new file's data_interfaces
        if els.electrodes.table.name in nwb_new.processing['ecephys'].data_interfaces:
            LFP_dynamic_table = nwb_new.processing['ecephys'].data_interfaces[els.electrodes.table.name]
        else:
            # othewise use the electrodes as the table
            LFP_dynamic_table = nwb_new.electrodes
        ####

        region = np.array(els.electrodes.table.id[:])[els.electrodes.data[:]].tolist()
        elecs_region = LFP_dynamic_table.create_region(
            name='electrodes',
            region=region,
            description=els.electrodes.description
        )

        obj.create_electrical_series(
            name=els.name,
            comments=els.comments,
            conversion=els.conversion,
            data=els.data[:],
            description=els.description,
            electrodes=elecs_region,
            rate=els.rate,
            resolution=els.resolution,
            starting_time=els.starting_time
        )

        return obj

    # TimeSeries --------------------------------------------------------------
    if type(obj_old) is TimeSeries:
        return TimeSeries(
            name=obj_old.name,
            description=obj_old.description,
            data=obj_old.data[:],
            rate=obj_old.rate,
            resolution=obj_old.resolution,
            conversion=obj_old.conversion,
            starting_time=obj_old.starting_time,
            unit=obj_old.unit
        )

    # DecompositionSeries -----------------------------------------------------
    if type(obj_old) is DecompositionSeries:
        list_columns = []
        for item in obj_old.bands.columns:
            bp = VectorData(name=item.name,
                            description=item.description,
                            data=item.data[:])
            list_columns.append(bp)
        bandsTable = DynamicTable(
            name=obj_old.bands.name,
            description=obj_old.bands.description,
            columns=list_columns,
            colnames=obj_old.bands.colnames
        )
        return DecompositionSeries(
            name=obj_old.name,
            data=obj_old.data[:],
            description=obj_old.description,
            metric=obj_old.metric,
            unit=obj_old.unit,
            rate=obj_old.rate,
            # source_timeseries=lfp,
            bands=bandsTable,
        )

    # Spectrum ----------------------------------------------------------------
    if type(obj_old) is Spectrum:
        file_elecs = nwb_new.electrodes
        nChannels = len(file_elecs['x'].data[:])
        elecs_region = file_elecs.create_region(
            name='electrodes',
            region=np.arange(nChannels).tolist(),
            description=''
        )
        return Spectrum(
            name=obj_old.name,
            frequencies=obj_old.frequencies[:],
            power=obj_old.power,
            electrodes=elecs_region
        )

    # Survey tables ------------------------------------------------------------
    if obj_old.neurodata_type == 'SurveyTable':
        if obj_old.name == 'nrs_survey_table':
            n_rows = len(obj_old['nrs_pain_intensity_rating'].data)
            for i in range(n_rows):
                nrs_survey_table.add_row(**{c: obj_old[c][i] for c in obj_old.colnames})
            return nrs_survey_table

        elif obj_old.name == 'vas_survey_table':
            n_rows = len(obj_old['vas_pain_intensity_rating'].data)
            for i in range(n_rows):
                vas_survey_table.add_row(**{c: obj_old[c][i] for c in obj_old.colnames})
            return vas_survey_table

        elif obj_old.name == 'mpq_survey_table':
            n_rows = len(obj_old['throbbing'].data)
            for i in range(n_rows):
                mpq_survey_table.add_row(**{c: obj_old[c][i] for c in obj_old.colnames})
            return mpq_survey_table
