# -*- coding: utf-8 -*-
import numpy as np
import math

def BadTimesConverterGUI(badtimes, filename):    
    if np.size(badtimes) > 0:
        index = np.argsort(badtimes[:, 0])
        badtimes = badtimes[index, :]
        fid = open(filename, 'w')
        first = 0
        for cnt1 in range(np.shape(badtimes)[0]):
            fid.write(str(math.floor(first * 1e7)) + ' ' + str(math.floor(badtimes[cnt1, 0] * 1e7)) + ' b ' + \
                      str(badtimes[cnt1][2]) + '\n')
            fid.write(str(math.floor(badtimes[cnt1][0] * 1e7)) + ' ' + str(math.floor(badtimes[cnt1, 1] * 1e7)) + ' e ' + \
                      str(badtimes[cnt1][2]) + '\n')            
            first = badtimes[cnt1][1]
        
        fid.close()
    else: 
        fid = open(filename, 'w')
        fid.write(' ')
        fid.close()
    
    