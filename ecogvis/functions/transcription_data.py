from ndx_hierarchical_behavioral_data.transcription_io import timitsounds_df, timitsounds_converter
from ndx_hierarchical_behavioral_data.mocha_io import mocha_df, mocha_re_df, mocha_converter


def add_transcription_data(nwbfile, path_transcription, type, subject_id=None,
                           session_id=None):
    """
    Add transcription data to nwb file

    Parameters:
    -----------
    nwbfile : nwbfile
    path_transcription : path
    type : str
        Transcriptions data type: timitsounds, textgrid or mocha
    subject_id : str
        Used for Mocha
    session_id : str
        Used for Mocha
    """

    if type == 'timitsounds':
        phonemes, syllables, words, sentences = get_timitsounds(path_transcription=path_transcription)
    elif type == 'mocha':
        phonemes, syllables, words, sentences = get_mocha(
            path_transcription=path_transcription,
            subject_id=subject_id,
            session_id=session_id
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


def get_mocha(path_transcription, subject_id, session_id):
    """Get data from Mocha directory"""
    phoneme_data, syllable_data, word_data, sentences_data = mocha_df(path_to_files=path_transcription)
    re_phoneme_data, re_syllable_data, re_word_data, re_sentence_data = mocha_re_df(
        phoneme_data=phoneme_data,
        syllable_data=syllable_data,
        word_data=word_data,
        sentences_data=sentences_data,
        subject_id=subject_id,  # 'EC118'
        session_id=session_id,  # 'B6'
        trial_id='...'
    )
    phonemes, syllables, words, sentences = mocha_converter(
        re_phoneme_data=re_phoneme_data,
        re_syllable_data=re_syllable_data,
        re_word_data=re_word_data,
        re_sentence_data=re_sentence_data
    )
    return phonemes, syllables, words, sentences


def get_timitsounds(path_transcription):
    """Get data from TimitSounds directory"""
    phonemes_data, syllables_data, words_data, sentences_data, pitch_data, formant_data, intensity_data = timitsounds_df(path_to_files=path_transcription)
    phonemes, syllables, words, sentences, pitch_ts, formant_ts, intensity_ts = timitsounds_converter(
        phonemes_data=phonemes_data,
        syllables_data=syllables_data,
        words_data=words_data,
        sentences_data=sentences_data,
        pitch_data=pitch_data,
        formant_data=formant_data,
        intensity_data=intensity_data
    )
    return phonemes, syllables, words, sentences
