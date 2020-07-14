from ndx_survey_data import survey_definitions
from scipy.io import loadmat
from importlib import reload
import math


def add_survey_data(nwbfile, path_survey_file):
    """
    Add survey data to nwb file

    Parameters:
    -----------
    nwbfile: nwbfile
    path_survey_fila: path
        Path to .mat file containing survey data
    """

    # Reload definitions
    reload(survey_definitions)

    survey_dict = loadmat(path_survey_file)
    survey_data = survey_dict['redcap_painscores']
    survey_dt = survey_dict['redcap_datetimes'][:, 0]

    # Mpq data values
    def mpq_values(val):
        if math.isnan(val):
            return 'NaN'
        elif int(val) == 1:
            return 'mild'
        elif int(val) == 2:
            return 'moderate'
        elif int(val) == 3:
            return 'severe'

    # NRS and VAS data values
    def nrs_values(val):
        if math.isnan(val):
            return 'NaN'
        else:
            return str(int(val))

    # Add rows to tables
    for i, row in enumerate(survey_data):
        # NRS table
        nrs_null = all([math.isnan(v) for v in row[0:4]])
        if not nrs_null:
            survey_definitions.nrs_survey_table.add_row(
                pain_intensity_rating=nrs_values(row[0]),
                relative_pain_intensity_rating=nrs_values(row[1]),
                pain_unpleasantness=nrs_values(row[2]),
                pain_relief_rating=nrs_values(row[3]),
                unix_timestamp=survey_dt[i]
            )

        # VAS table
        vas_null = all([math.isnan(v) for v in row[4:8]])
        if not vas_null:
            survey_definitions.vas_survey_table.add_row(
                pain_intensity_rating=nrs_values(row[4]),
                pain_relief_rating=nrs_values(row[5]),
                relative_pain_intensity_rating=nrs_values(row[6]),
                pain_unpleasantness=nrs_values(row[7]),
                unix_timestamp=survey_dt[i]
            )

        # MPQ table
        mpq_null = all([math.isnan(v) for v in row[9:]])
        if not mpq_null:
            survey_definitions.mpq_survey_table.add_row(
                throbbing=mpq_values(row[9]),
                shooting=mpq_values(row[10]),
                stabbing=mpq_values(row[11]),
                sharp=mpq_values(row[12]),
                cramping=mpq_values(row[13]),
                gnawing=mpq_values(row[14]),
                hot_burning=mpq_values(row[15]),
                aching=mpq_values(row[16]),
                heavy=mpq_values(row[17]),
                tender=mpq_values(row[18]),
                splitting=mpq_values(row[19]),
                tiring_exhausting=mpq_values(row[20]),
                sickening=mpq_values(row[21]),
                fearful=mpq_values(row[22]),
                cruel_punishing=mpq_values(row[23]),
                unix_timestamp=survey_dt[i]
            )

    # Create behavioral processing module, if not existent
    if 'behavior' not in nwbfile.processing:
        nwbfile.create_processing_module(
            name='behavior',
            description='behavioral data'
        )

    # Add survey tables to behavioral processing module
    nwbfile.processing['behavior'].add(survey_definitions.nrs_survey_table)
    nwbfile.processing['behavior'].add(survey_definitions.vas_survey_table)
    nwbfile.processing['behavior'].add(survey_definitions.mpq_survey_table)

    print('Survey data added successfully!')
