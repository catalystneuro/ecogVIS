from ndx_survey_data import SurveyTable
from scipy.io import loadmat
import math


def map_to_words(data, col_name):
    """Map data to words"""
    # Map nan to 'no answer'
    data = ['no answer' if math.isnan(a) else int(a) for a in data]

    # Map integers to words for McGill Pain Questionnaire
    if ('mpq' in col_name) and ('total' not in col_name):
        words = ['mild', 'moderate', 'severe']
        data = [words[a - 1] if not isinstance(a, str) else a for a in data]

    return data


def add_survey_data(nwbfile, path_survey_file):
    """
    Add survey data to nwb file

    Parameters:
    -----------
    nwbfile: nwbfile
    path_survey_fila: path
        Path to .mat file containing survey data
    """
    survey_dict = loadmat(path_survey_file)
    survey_data = survey_dict['redcap_painscores']
    survey_dt = survey_dict['redcap_datetimes'][:, 0]

    # Create Survey table
    survey_table = SurveyTable(name='daily_pain_survey', description='desc')

    # Add unix timestamps
    for d_t in survey_dt:
        survey_table.add_row(unix_timestamp=d_t)

    # Add columns
    question_name = [q[0] for q in survey_dict['column_questionName'][0, :]]
    question_category = [q[0] for q in survey_dict['column_taskCategory'][0, :]]
    for i, (q, c) in enumerate(zip(question_name, question_category)):
        # Join question name and category to form column name
        col_name = q.lower().replace(' ', '_') + '_' + c.lower()

        # Process data
        data = map_to_words(data=survey_data[:, i], col_name=col_name)

        # Add column
        survey_table.add_column(
            name=col_name,
            description='desc',
            data=data
        )

    # Create behavioral processing module, if not existent
    if 'behavior' not in nwbfile.processing:
        nwbfile.create_processing_module(
            name='behavior',
            description='behavioral data'
        )

    # Add survey table to behavioral processing module
    nwbfile.processing['behavior'].add(survey_table)

    print('Survey data added successfully!')
