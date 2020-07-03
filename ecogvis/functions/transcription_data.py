from ndx_hierarchical_behavioral_data.transcription_io import timitsounds_df, timitsounds_converter


def add_transcription_data(nwbfile, path_transcription_dir):
    """
    Add transcription data to nwb file

    Parameters:
    -----------
    nwbfile: nwbfile
    path_transcription_dir: path
    """

    phonemes_data, syllables_data, words_data, sentences_data, pitch_data, formant_data, intensity_data = timitsounds_df(path_to_files=path_transcription_dir)

    phonemes, syllables, words, sentences, pitch_ts, formant_ts, intensity_ts = timitsounds_converter(
        phonemes_data=phonemes_data,
        syllables_data=syllables_data,
        words_data=words_data,
        sentences_data=sentences_data,
        pitch_data=pitch_data,
        formant_data=formant_data,
        intensity_data=intensity_data
    )

    # Create behavioral processing module, if not existent
    if 'behavior' not in nwbfile.processing:
        nwbfile.create_processing_module(
            name='behavior',
            description='behavioral data'
        )

    # Add transcription tables to behavioral processing module
    nwbfile.processing['behavior'].add(phonemes)
    nwbfile.processing['behavior'].add(syllables)
    nwbfile.processing['behavior'].add(words)
    nwbfile.processing['behavior'].add(sentences)

    print('Transcription data added successfully!')
