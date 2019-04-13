# -*- coding: utf-8 -*-
"""
Created on Fri Aug  3 11:41:15 2018

@author: lenovo_i5
"""

def getEcog(pathName, newfs):
    
    if ('newfs' not in locals()) | (len(newfs) == 0):
        newfs = 400
        
    
    
#    wavs = dir(fullfile(pathName,'RawHTK','Wav*.htk'));
#    nchan = length(wavs);
#    
#    recordingblocksize = 64;
#    nrecordingblocks = ceil(nchan/recordingblocksize);
#    
#    %determine size of handles.ecogDS.data (could probably be done better)
#    path = fullfile(pathName,'RawHTK','Wav11.htk');
#    [RawECOG, fs] = readhtk(path);
#    
#    if fs == 3051.7578
#        d = resample(RawECOG, 2^11, 5^6*400/newfs);
#    elseif fs == 8138.021
#        keyboard
#        temp = strsplit(num2str(fs),'.');
#        precision = length(temp{2});
#        
#        %d = resample(RawECOG, newfs*10^precision, round(fs*10^precision));
#        d1 = resample(RawECOG, 10^precision, fs*10^precision/23);
#    end
#    
#    %load, downsample, and store
#    disp('Loading, downsampling, and storing...')
#    data = NaN(nchan,length(d)); % malloc
#    i = 0;
#    fprintf('\nLoading channel (/256)...\n');
#    done = 0;
#    for n=1:nrecordingblocks %4 for humans
#        for k = 1:recordingblocksize %64 for humans
#            i = i+1;
#            path = fullfile(pathName,'RawHTK',['Wav' num2str(n) num2str(k) '.htk']);
#            if ~exist(path)
#                warning(['loading stopped at Wav' num2str(n) num2str(k) '.htk'])
#                done = 1;
#                break
#            end
#            RawECOG = readhtk(path)*1e6;
#            if all(~RawECOG)
#                warning(['loading stopped at Wav' num2str(n) num2str(k) '.htk'])
#                done = 1;
#                break
#            end
#            
#            if fs == 3051.7578
#                data(i,:) = resample(RawECOG, 2^11, 5^6*400/newfs);
#            else
#                temp = strsplit(num2str(fs),'.');
#                precision = length(temp{2});
#                
#                d(i,:) = resample(RawECOG, round(fs*10^precision), newfs*10^precision);
#            end
#            fprintf('%d.',i);
#        end
#        fprintf('\n');
#        if done; break; end
#    end
#    fprintf('\n');