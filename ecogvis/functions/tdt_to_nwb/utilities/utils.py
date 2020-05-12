# -*- coding: utf-8 -*-
"""
Utility functions for creating and parsing information for NWB files.
"""

import re

import numpy as np


def get_block_number(string_input, template=None):
    """Finds the block number in a string
    Parameters
    ----------
    string_input : str
        The string containing the block number
    template : str
        A template string, e.g.  '_B1', 'B_1'
        (Both of these examples can be handled by the default)

    Returns
    -------
    block: int
    """

    if template is None:
        pattern = '_?B_?([0-9]+)'
    else:
        pattern = re.sub('[0-9]+', '([0-9]+)', template)

    match = re.search(pattern, string_input)
    if match:
        return int(match.group(1))
    else:
        raise RuntimeError(
            'No match for pattern {} in string {}'.format(pattern,
                                                          string_input))


################################################################
### potentially outdated functions, used in chang2nwb script ###
########## Author: Ben Dichter #################################
################################################################

def find_discontinuities(tt, factor=10000):
    """
    Find discontinuities in a timeseries. Returns the indices before each
    discontinuity.
    """
    dt = np.diff(tt)
    before_jumps = np.where(dt > np.median(dt) * factor)[0]

    if len(before_jumps):
        out = np.array([tt[0], tt[before_jumps[0]]])
        for i, j in zip(before_jumps, before_jumps[1:]):
            out = np.vstack((out, [tt[i + 1], tt[j]]))
        out = np.vstack((out, [tt[before_jumps[-1] + 1], tt[-1]]))
        return out
    else:
        return np.array([[tt[0], tt[-1]]])


def isin_single_interval(tt, tbound, inclusive_left, inclusive_right):
    if inclusive_left:
        left_condition = (tt >= tbound[0])
    else:
        left_condition = (tt > tbound[0])

    if inclusive_right:
        right_condition = (tt <= tbound[1])
    else:
        right_condition = (tt < tbound[1])

    return left_condition & right_condition


def isin_time_windows(tt, tbounds, inclusive_left=True, inclusive_right=False):
    """
    util: Is time inside time window(s)?
    :param tt:      n,    np.array   time counter
    :param tbounds: k, 2  np.array   time windows
    :param inclusive_left:  bool
    :param inclusive_right: bool
    :return:        n, bool          logical indicating if time is in any of
    the windows
    """
    # check if tbounds in np.array and if not fix it
    tbounds = np.array(tbounds)
    tt = np.array(tt)

    tf = np.zeros(tt.shape, dtype='bool')

    if len(tbounds.shape) is 1:
        tf = isin_single_interval(tt, tbounds, inclusive_left, inclusive_right)
    else:
        for tbound in tbounds:
            tf = tf | isin_single_interval(tt, tbound, inclusive_left,
                                           inclusive_right)
    return tf.astype(bool)


def check_equal(iterator):
    iterator = iter(iterator)
    try:
        first = next(iterator)
    except StopIteration:
        return True
    return all(first == rest for rest in iterator)


def remove_duplicates(li):
    """Removes duplicates of a list but preserves list order
    Parameters
    ----------
    li: list
    Returns
    -------
    res: list
    """
    res = []
    for e in li:
        if e not in res:
            res.append(e)
    return res


def natural_key(text):
    # Key used for natural ordering: orders files correctly even if numbers
    # are not zero-padded
    return [int(c) if c.isdigit() else c for c in re.split('(\d+)', text)]


def check_module(nwbfile, name, description=None):
    """Check if processing module exists. If not, create it. Then return module
    Parameters
    ----------
    nwbfile: pynwb.NWBFile
    name: str
    description: str | None (optional)
    Returns
    -------
    pynwb.module
    """

    if name in nwbfile.modules:
        return nwbfile.modules[name]
    else:
        if description is None:
            description = name
    return nwbfile.create_processing_module(name, description)
