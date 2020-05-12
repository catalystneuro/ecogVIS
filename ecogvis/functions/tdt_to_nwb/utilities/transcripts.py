# -*- coding: utf-8 -*-
"""
:Authors: David Conant, Jesse Livezey, Ben Dichter
"""

from __future__ import division

import os
import re

import numpy as np
import pandas as pd
from pynwb.epoch import TimeIntervals

lab_time_conversion = 1e7


def parse(blockpath, blockname):
    """
    Find and parse transcript for block.
    Parameters
    ----------
    blockpath : str
        Path to block folder.
    blockname : str
        Block transcript file prefix.
    Returns
    -------
    parseout : dict
        With keys:
        label : an array of strings identifying each event according to the
        utterance
        start : an array of the start times for each event
        stop : an array of the stop times for each event
        tier : an array specifying the tier (phoneme or word) for each event
        contains : an array specifying the phonemes contained within each event
        contained_by : an array specifying the words contiaining each event
        position : the position of each phoneme within the word
    """
    textgrid_path = os.path.join(blockpath,
                                 blockname + '_transcription_final.TextGrid')
    lab_path = os.path.join(blockpath, blockname + '_transcription_final.lab')
    if os.path.isfile(textgrid_path):
        parseout = parse_TextGrid(textgrid_path)
    elif os.path.isfile(lab_path):
        parseout = parse_Lab(lab_path)
    else:
        raise ValueError("Transcription not found at: "
                         + str(textgrid_path) + " or: "
                         + str(lab_path))
    return parseout


def parse_TextGrid(fname):
    """
    Reads in a TextGrid (used by Praat) and returns a dictionary with the
    events
    contained within, as well as their times, labels, and hierarchy.
    Assumes a 2 tier textgrid corresponding to words and phonemes
    Parameters:
    fname: filename of the TextGrid
    Returns
    -------
    events : dict
        With keys:
        label : an array of strings identifying each event according to the
        utterance
        start : an array of the start times for each event
        stop : an array of the stop times for each event
        tier : an array specifying the tier (phoneme or word) for each event
        contains : an array specifying the phonemes contained within each event
        contained_by : an array specifying the words containing each event
        position : the position of each phoneme within the word
    """

    with open(fname) as tg:
        content = tg.readlines()

    label = []
    start = []
    stop = []
    tier = []

    if any(['item [' in c for c in content]):
        # Normal formatting
        for ii, line in enumerate(content):
            if 'item [1]:' in line:
                t = 'phoneme'
            elif 'item [2]:' in line:
                t = 'word'
            elif 'item [3]:' in line:
                t = 'phrase'
            elif 'text =' in line and t != 'phrase':
                if '"sp"' in line or '""' in line:
                    continue

                token = ''.join(re.findall('[a-zA-Z]', line.split(' ')[-2]))
                if t == 'word':
                    mode = re.findall('[0-9]', line.split(' ')[-2])
                    if len(mode) == 1:
                        token += mode[0]
                    else:
                        token += '2'
                label.append(token)
                start.append(float(content[ii - 2].split(' ')[-2]))
                stop.append(float(content[ii - 1].split(' ')[-2]))
                tier.append(t)
    else:
        # Truncated formatting
        content = content[7:]
        for ii, line in enumerate(content):
            if 'IntervalTier' in line:
                continue
            elif 'phone' in line:
                t = 'phoneme'
                continue
            elif 'word' in line:
                t = 'word'
                continue
            elif 'sp' in line:
                continue
            else:
                try:
                    float(line)
                except ValueError:
                    label.append(line[1:-1])
                    start.append(float(content[ii - 2]))
                    stop.append(float(content[ii - 1]))
                    tier.append(t)

    return format_events(label, start, stop, tier)


def parse_Lab(fname):
    """
    Reads a 'lab' transcript and returns a dictionary with the events
    contained within, as well as their times, labels, and hierarchy.
    Parameters
    ----------
    fname: filename of the 'lab' transcript
    Returns
    -------
    events : dict
        With keys:
        label : an array of strings identifying each event according to the
        utterance
        start : an array of the start times for each event
        stop : an array of the stop times for each event
        tier : an array specifying the tier (phoneme or word) for each event
        contains : an array specifying the phonemes contained within each event
        contained_by : an array specifying the words contiaining each event
        position : the position of each phoneme within the word
    """

    def clean_tokens(token):
        if token == 'ra':
            return 'raa'
        return token

    def split_token(token):
        m = re.search('\d', token)
        if m:
            m = m.start()
            token_text = token[:m]
            token_num = token[m]
        else:
            token_text = token[:-1]
            token_num = None

        token_text = clean_tokens(token_text)
        token_consonant = token_text[:-2]
        token_vowel = token_text[-2:]
        return token_text, token_consonant, token_vowel, token_num

    start = []
    stop = []
    tier = []
    label = []
    with open(fname) as lab:
        content = lab.readlines()

    for ii, line in enumerate(content):
        _, time, token = line.split(' ')
        token_text, token_consonant, token_vowel, token_num = split_token(
            token)

        isplosive = token_consonant in ['d', 't', 'b', 'p', 'g', 'k', 'gh']
        if (isplosive and '4' == token_num) or (
                not isplosive and '3' == token_num):
            _, start_time, start_token = content[ii - 1].split(' ')
            _, stop_time, stop_token = content[ii + 1].split(' ')
            # First phoneme
            tier.append('phoneme')
            start.append(float(start_time) / lab_time_conversion)
            stop.append(float(time) / lab_time_conversion)
            label.append(token_consonant)
            # Second phoneme
            tier.append('phoneme')
            start.append(float(time) / lab_time_conversion)
            stop.append(float(stop_time) / lab_time_conversion)
            label.append(token_vowel)
            # Word
            tier.append('word')
            start.append(float(start_time) / lab_time_conversion)
            stop.append(float(stop_time) / lab_time_conversion)
            label.append(token_text + '2')

    return format_events(label, start, stop, tier)


def standardize_token(token):
    """
    Standardizations to make to tokens.
    Parameters
    ----------
    token : str
        Token to be standarized.
    Returns
    -------
    token : str
        Standardized token.
    """
    token = token.lower()
    token = token.replace('uu', 'oo')
    token = token.replace('ue', 'oo')
    token = token.replace('gh', 'g')
    token = token.replace('who', 'hoo')
    token = token.replace('aw', 'aa')

    return token


def format_events(label, start, stop, tier):
    """
    Add position information to events.
    Parameters
    ----------
    label : list
        List of event labels.
    start : list
        List of event start times.
    stop : list
        List of event stop times.
    tier : list
        Event tier.
    Returns
    -------
    events : dict
        With keys:
        label : an array of strings identifying each event according to the
        utterance
        start : an array of the start times for each event
        stop : an array of the stop times for each event
        tier : an array specifying the tier (phoneme or word) for each event
        contains : an array specifying the phonemes contained within each event
        contained_by : an array specifying the words contiaining each event
        position : the position of each phoneme within the word
    """

    label = np.array([standardize_token(l) for l in label])
    start = np.array(start)
    stop = np.array(stop)
    tier = np.array(tier)

    phones, = np.where(tier == 'phoneme')
    words, = np.where(tier == 'word')

    contained_by = [-1] * label.size
    contains = [-1] * label.size
    position = -1 * np.ones(label.size)

    # Determine hierarchy of events
    for ind in words:
        position[ind] = 0
        contained_by[ind] = -1;

        # Find contained phonemes
        tol = abs(start[ind] - stop[ind]) / 10.
        lower = start[ind] - tol
        upper = stop[ind] + tol
        startCandidates = np.where(start >= lower)[0]
        stopCandidates = np.where(stop <= upper)[0]
        intersect = np.intersect1d(startCandidates, stopCandidates)
        cont = list(intersect)
        cont.remove(ind)
        contains[ind] = cont
        for i in cont:
            contained_by[i] = ind

    for ind in phones:
        # Find phonemes in the same word, position is order in list
        same_word = np.where(np.asarray(contained_by) == contained_by[ind])[0]
        position[ind] = np.where(same_word == ind)[0]

    contains = np.asarray(contains, dtype=object)
    contained_by = np.asarray(contained_by, dtype=object)

    events = {
        'label': label, 'start': start, 'stop': stop,
        'tier': tier, 'contains': contains,
        'contained_by': contained_by, 'position': position
    }

    return events


def make_df(parseout, block, subject, align_pos, tier='word'):
    """
    Organize event data.
    Parameters
    ----------
    parseout : dict
        Dictionary from parsed transcript.
    block : int
        Block ID.
    subject : str
        Subject ID.
    align_pos : int
        Sub-element in event to align to.
    tier : str
        Type of event to extract.
    """

    keys = sorted(parseout.keys())
    datamat = [parseout[key] for key in keys]
    df = pd.DataFrame(np.vstack(datamat).T, columns=keys)
    keep = (((df['tier'] == tier) &
             (df['contains'].apply(lambda x: len(x) if isinstance(x,
                                                                  list) else
             0) > align_pos)) |
            (df['tier'] != tier))
    df = df[keep]
    first_phones_per_word = df['contains'][df['tier'] == tier].apply(
        lambda x: x[align_pos])
    df_events = df[df['tier'] == tier]

    # Get rid of superfluous columns
    df_events = df_events[['label', 'start', 'stop']]
    df_events['align'] = df['start'].iloc[first_phones_per_word].astype(
        float).values
    assert np.all(df_events['align'] >= df_events['start'])
    assert np.all(df_events['align'] <= df_events['stop'])

    # Pull mode from label and get rid of number
    df_events['mode'] = ['speak' if l[-1] == '2' else 'listen' for l in
                         df_events['label']]
    df_events['label'] = df_events['label'].apply(lambda x: x[:-1])

    df_events['label'] = df_events['label'].astype('category')
    df_events['mode'] = df_events['mode'].astype('category')
    df_events['block'] = block
    df_events['subject'] = subject

    return df_events


def create_transcription_ndx(transcript_path, block):
    from ndx_speech import Transcription

    def add_blocks(df):
        df['block'] = [x[:-4] for x in df['sentence_id']]

    def reduce_df(df, block, cols=('start_time', 'stop_time', 'label')):
        return df.loc[df['block'] == block][list(cols)]

    # phoneme features
    fpath = os.path.join(transcript_path, 'phoneme_features.times')

    # not working
    df = pd.read_csv(fpath,
                     names=('label', 'sentence_id', 'start_time', 'stop_time'),
                     sep=' ')
    add_blocks(df)
    phoneme_features = TimeIntervals.from_dataframe(reduce_df(df, block),
                                                    name='phoneme_features')

    # words
    fpath = os.path.join(transcript_path, 'word.times')

    words_df = pd.read_csv(fpath, names=(
    'label', 'sentence_id', 'start_time', 'stop_time'), sep=' ')
    add_blocks(words_df)
    words = TimeIntervals.from_dataframe(reduce_df(words_df, block),
                                         name='words')

    # sentences
    fpath = os.path.join(transcript_path, 'sentence.times')
    sentence_df = pd.read_csv(fpath,
                              names=('sentence_id', 'start_time', 'stop_time'),
                              sep=' ')
    sentence_df['label'] = [
        ' '.join(words_df.loc[words_df['sentence_id'] == sentence_id]['label'])
        for sentence_id in sentence_df['sentence_id']]
    add_blocks(sentence_df)
    sentences = TimeIntervals.from_dataframe(reduce_df(sentence_df, block),
                                             name='sentences')

    # phonemes
    fpath = os.path.join(transcript_path, 'phoneme.times')

    phonemes_df = pd.read_csv(fpath, names=(
    'label', 'before', 'after', 'sentence_id', 'start_time', 'stop_time'),
                              sep=' ')
    add_blocks(phonemes_df)
    df = reduce_df(phonemes_df, block,
                   ('start_time', 'stop_time', 'label', 'before', 'after'))
    phonemes = TimeIntervals.from_dataframe(df, name='sentences')

    return Transcription(words=words, sentneces=sentences, phonemes=phonemes)
