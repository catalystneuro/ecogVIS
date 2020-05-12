# -*- coding: utf-8 -*-
"""
Configuration variables for various processing. This may include system
settings that are relevant for metadata. This is NOT meant to hold path names.
Those should still be stored in a separate configuration JSON.

:Author: Jessie R. Liu
"""

config = {
    "TDT": {
        "PZ5M-512": {
            "dynamic_range": [-0.5, 0.5],
            "bit_resolution": 28
        },
        "RZ2": {
            "dynamic_range": [-10, 10],
            "bit_resolution": 16
        }
    }
}
