#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Created on Fri Jul 13 21:32:20 2018

@author: lenovo_i5
"""
import os
import scipy.io
import numpy as np
import h5py
from Function.read_HTK import readHTK
import math
from PyQt5.QtWidgets import QInputDialog, QLineEdit, QFileDialog
import datetime
import Function.BadTimesConverterGUI as f
import pyqtgraph as pg
from PyQt5 import QtGui

class ecogTSGUI:
    def __init__(self, par, pathName, parameters):
        
        self.parent = par
        self.pathName = pathName
        self.axesParams = parameters        
        out = self.loadBlock()
        self.ecog = out['ecogDS']
        self.x_cur = []
        self.y_cur = []
        self.h = []
        self.text = []
        n_ch = np.shape(self.ecog['data'])[1]
        self.channelScrollDown = np.arange(0, int(self.axesParams['editLine']['qLine0'].text()))
        self.indexToSelectedChannels = np.arange(0, int(self.axesParams['editLine']['qLine0'].text()))
        self.selectedChannels = np.arange(0, n_ch)
        self.channelSelector = np.arange(0, n_ch)
        self.rawecog = out['ecogDS']
        self.badIntervals = out['badTimeSegments']
        self.t1 = 0
        self.current_rect = []
        self.badChannels = out['badChannels']        
        if os.path.exists(os.path.join(pathName, 'Analog', 'ANIN4.htk')):#menu('load audio?','yes','no') == 1
            self.disp_audio = 1
            self.audio = readHTK(os.path.join(pathName, 'Analog', 'ANIN4.htk'))    
            
            self.downsampled = self.downsample(10)
            self.audio['sampling_rate'] = self.audio['sampling_rate']/10000
            self.fs_audio = self.audio['sampling_rate']/10            
            self.taudio = np.arange(1, np.shape(self.downsampled)[0])/self.fs_audio
            
        else:
            self.disp_audio = 0
         
        total_dur = len(self.ecog['data'])/self.ecog['sampFreq'][0][0]
        self.axesParams['pars']['Figure'][1].plot([0, total_dur], [0.5, 0.5], pen = 'k', width = 0.5)

#        %plot bad time segments on timeline
        BIs = self.badIntervals
        self.BIRects = np.array([], dtype = 'object')
        for i in range(np.shape(BIs)[0]):
            c = pg.QtGui.QGraphicsRectItem(BIs[i][0], 0, max([BIs[i][1] - BIs[i][0], 0.01]), 1)
            a = self.axesParams['pars']['Figure'][1]
            c.setPen(pg.mkPen(color = 'r'))
            c.setBrush(QtGui.QColor(255, 0, 0, 255))
            a.addItem(c)
            self.BIRects = np.append(self.BIRects, c)

        
        
        
        
#        BIs(all(~BIs,2),:) = []; % fix row of all zeros
#        for i=1:size(BIs,1)
#            handles.BIRects(i) = rectangle('Position',[BIs(i,1),0,max(BIs(i,2)-BIs(i,1),.01),1],'FaceColor','r');
#        end
        
        self.refreshScreen()
       
    def refreshScreen(self):
        self.AR_plotter()
        
    def AR_plotter(self):        
        self.getCurAxisParameters()
        startSamp = int(math.ceil(self.intervalStartSamples))      
        endSamp = int(math.floor(self.intervalEndSamples))       
        
        channelsToShow = self.selectedChannels[self.indexToSelectedChannels]
        self.verticalScaleFactor = float(self.axesParams['editLine']['qLine4'].text())
        scaleFac = np.var(self.ecog['data'][: (endSamp - startSamp), :], axis = 0)/self.verticalScaleFactor #We use on fixed interval for the scaling factor to keep things comparable
       
        scaleVec = np.arange(1, len(channelsToShow) + 1) * max(scaleFac) * 1/50 #The multiplier is arbitrary. Find a better solution
        
        timebaseGuiUnits = np.arange(startSamp - 1, endSamp) * (self.intervalStartGuiUnits/self.intervalStartSamples) 

        scaleV = np.zeros([len(scaleVec), 1])
        scaleV[:, 0] = scaleVec
        try:            
            data = self.ecog['data'][startSamp - 1 : endSamp, channelsToShow].T
            plotData = data + np.tile(scaleV, (1, endSamp - startSamp + 1)) #data + offset        
        except:
#            #if time segment shorter than window.
            data = self.ecog['data'][:, channelsToShow].T
            plotData = data + np.tile(scaleV, (1, endSamp - startSamp + 1)) # %data + offset
         
###### Rectangle Plot
        x = float(self.axesParams['editLine']['qLine2'].text())
        w = float(self.axesParams['editLine']['qLine3'].text())
        
        plt2 = self.axesParams['pars']['Figure'][1]
        if self.current_rect != []:                       
            plt2.removeItem(self.current_rect)
        
        self.current_rect = pg.QtGui.QGraphicsRectItem(x, 0, w, 1)
        self.current_rect.setPen(pg.mkPen(color = 'k'))
        self.current_rect.setBrush(QtGui.QColor(0, 255, 0, 200))
        plt2.addItem(self.current_rect)

        
        for i in range(len(self.BIRects)):
            plt2.removeItem(self.BIRects[i])
        for i in range(len(self.BIRects)):   
            plt2.addItem(self.BIRects[i])

        
######       Rectangle Plot
        
#        %bad_t=handles.ecog.bad_t;
#        %A line indicating zero for every channel        
        x = np.tile([timebaseGuiUnits[0], timebaseGuiUnits[-1]], (len(scaleVec), 1))
        y = np.hstack((scaleV, scaleV))
        plt = self.axesParams['pars']['Figure'][0]
        plt.clear()                                                             #clear plot
        for l in range(np.shape(x)[0]):
            plt.plot(x[l], y[l], pen = 'r')
        plt.setLabel('bottom', 'Time', units = 'sec')
        plt.setLabel('left', 'Channel #')
        
        labels = [str(ch + 1) for ch in channelsToShow]
        ticks = list(zip(y[:, 0], labels))
        
        plt.getAxis('left').setTicks([ticks])       
        
        
        badch = np.array([])    
        nrows, ncols = np.shape(plotData)
        for channels in enumerate(channelsToShow):
            if np.any(str(channels) in self.badChannels):
                np.append(badch, channels)
        if not np.empty(badch):            
            if len(np.where(self.badChannels == 999)) > 0:                
                for i in range(nrows):
                    c = 'g'
                    if i%2 == 0:
                        c = 'b'                    
                    plt.plot(timebaseGuiUnits, plotData[i], pen = pg.mkPen(c, width = 1))
                    if i in badch:
                        plt.plot(timebaseGuiUnits, plotData[i], pen = 'r', width = 1)
            else:
                plotData[badch, :] = np.nan
                ph = plt.plot(timebaseGuiUnits, plotData.T)      
            
        else:
            #PLOT CHANNELS 
            for i in range(nrows):
                c = 'g'
                if i%2 == 0:
                    c = 'b'                    
                plt.plot(timebaseGuiUnits, plotData[i], pen = c, width = 1)
            
        plt.setXRange(timebaseGuiUnits[0], timebaseGuiUnits[-1], padding = 0.003) 
        plt.setYRange(y[0, 0], y[-1, 0], padding = 0.06)
#        %MAKE TRANSPARENT BOX AROUND BAD TIME SEGMENTS
        self.plotData = []
        self.plotData = plotData
        self.showChan = channelsToShow   
        yaxis = plt.getAxis('left').range
        ymin, ymax = yaxis[0], yaxis[1]
        xaxis = plt.getAxis('bottom').range
        xmin, xmax = xaxis[0], xaxis[1]
        
        for i in range(np.shape(self.badIntervals)[0]):
            BI = self.badIntervals[i]            
            x1, y1, w, h = BI[0], ymin, BI[1] - BI[0], ymax            
            c = pg.QtGui.QGraphicsRectItem(x1, y1, w, h)
            c.setPen(pg.mkPen(color = (255, 255, 200)))
            c.setBrush(QtGui.QColor(255, 255, 200, 150))
            plt.addItem(c)
            self.text1 = pg.TextItem(str(round(BI[0], 4)), color = 'r')
            self.text1.setPos(BI[0], ymax)
            plt.addItem(self.text1)
            self.text2 = pg.TextItem(str(round(BI[1], 4)), color = 'r')
            self.text2.setPos(BI[1], ymax)
            plt.addItem(self.text2)          

        
        if self.disp_audio:#    % PLOT AUDIO            
            begin = self.intervalStartGuiUnits            
            stop = self.intervalStartGuiUnits + self.intervalLengthGuiUnits  
            plt1 = self.axesParams['pars']['Figure'][2]
            plt1.clear()
            ind_disp = np.where((self.taudio > begin) & (self.taudio < stop))
            x_axis = np.linspace(xmin, xmax, len(self.downsampled[ind_disp]))            
            plt1.plot(x_axis, self.downsampled[ind_disp], pen = 'r', width = 2)
            plt1.setXLink(plt)
#        plt2.setXLink(plt)

            

            
        
    def getCurAxisParameters(self):        
        self.getCurXAxisPosition()
        
    def getCurXAxisPosition(self):
        self.intervalStartGuiUnits = float(self.axesParams['editLine']['qLine2'].text())
        
        self.intervalLengthGuiUnits = float(self.axesParams['editLine']['qLine3'].text())
        
        
        total_dur = np.shape(self.ecog['data'])[0] * self.ecog['sampDur'][0][0]/1000        
        if self.intervalLengthGuiUnits > total_dur:
            self.intervalLengthGuiUnits = total_dur
        
        self.intervalLengthSamples = self.intervalLengthGuiUnits * (1000/self.ecog['sampDur'][0][0])
        
        self.intervalStartSamples = self.intervalStartGuiUnits * (1000/self.ecog['sampDur'][0][0]) # assumes seconds in GUI and milliseconds in  ecog.sampDur
        self.intervalEndSamples = self.intervalStartSamples + self.intervalLengthSamples - 1 #We assume that the intervall length is specified in samples
        #%should always work because plausibility has been checked when channels were entered (
        self.indexToSelectedChannels = self.channelScrollDown
        
    def downsample(self, n):
        L = self.audio['num_samples']
        block = round(L/n)
        n_zeros = block * n + n - L       
        self.downsampled = np.append(self.audio['data'], np.zeros([int(n_zeros)]))
        re_shape = np.reshape(self.downsampled, [int((block * n + n)/n), n])[:, 0]
        return re_shape
            
    
    def loadBadTimes(self):
        
        filename = os.path.join(self.pathName, 'Artifacts', 'badTimeSegments.mat')
        
        if os.path.exists(filename):
            loadmatfile = scipy.io.loadmat(filename)
            badTimeSegments = loadmatfile['badTimeSegments']
#            print '{} bad time segments loaded '.format(np.shape(loadmatfile['badTimeSegments'])[1])
        else:
            if not os.path.exists(os.path.join(self.pathName, 'Artifacts')):
                os.mkdir(os.path.join(self.pathName, 'Artifacts'))
                
            badTimeSegments = []
            scipy.io.savemat(filename, mdict = {'badTimeSegments': badTimeSegments})
    
        return badTimeSegments
    
    def loadBadCh(self):
        filename = os.path.join(self.pathName, 'Artifacts', 'badChannels.txt')
        if os.path.exists(filename):
            with open(filename)  as f:
                badChannels = f.read()
#                print 'Bad Channels : {}'.format(badChannels)
        else:
            os.mkdir(os.path.join(self.pathName, 'Artifcats'))
            with open(filename, 'w') as f:
                f.write('')
                f.close()
            badChannels = []
        return badChannels
    
    
    def fileParts(self):
        parts = self.pathName.split('\\')
        return parts[-1]

#def getEcog(pathName, newfs):
    
    def loadBlock(self, *argv):
        
        try:
            saveopt = argv[0]  
            
        except:
            saveopt = 0
            
            
        try:
            newfs = argv[1]
        except:
            newfs = 400
            
        if saveopt:
            auto = 1
        else:
            auto = 0
        
            
        if not os.path.exists(self.pathName):
            self.pathName = QFileDialog().getExistingDirectory(self.parent, 'Open File')
    
   
    
        if os.path.exists(os.path.join(self.pathName, 'RawHTK')) and \
            os.path.exists(os.path.join(self.pathName, 'ecog400')) and \
            os.path.exists(os.path.join(self.pathName, 'ecog600')) and \
            os.path.exists(os.path.join(self.pathName, 'ecog1000')) and \
            os.path.exists(os.path.join(self.pathName, 'ecog2000')):
            
                print('Please choose a block folder that contains the RawHTK, ecog400 or ecog600 folder, e.g. EC34_B5')
                
        
    
    
        blockName = self.fileParts()
#        print blockName
    
    #automatically load bad time segments
    
        badTimeSegments = self.loadBadTimes()
        badChannels = self.loadBadCh()
        
    #load data
    
    #try to find downsampled data
        file_ = os.path.join(self.pathName, 'ecog' + str(newfs), 'ecog.mat')
        out = dict()
        if os.path.exists(file_):
#            print 'Loading downsampled ecog....'
            loadmatfile = h5py.File(file_)
#            print 'done'
            
        elif os.path.exists(os.path.join(self.pathName, 'RawHTK')):
#            print 'Loading downsampled ecog...'
            loadmatfile = h5py.File(file_)
#            print 'done'
            ## LEFT to be implemented
        
            
        out['badTimeSegments'] = badTimeSegments
        out['badChannels'] = badChannels
        out['blockName'] = blockName
        out['ecogDS'] = loadmatfile['ecogDS']
        
        return out

    def channel_Scroll_Up(self):
        blockIndices = self.channelScrollDown        
        self.nChannelsDisplayed = int(self.axesParams['editLine']['qLine0'].text())
        nChanToShow = self.nChannelsDisplayed        
        chanToShow = self.channelSelector        
        blockIndices  = blockIndices + nChanToShow        
        if blockIndices[-1] > len(chanToShow):
            blockIndices = np.arange(len(chanToShow) - len(blockIndices) + 1, len(chanToShow))
#        print blockIndices
        self.channelScrollDown = blockIndices        
        self.refreshScreen()
        
    def channel_Scroll_Down(self):
        blockIndices = self.channelScrollDown        
        nChanToShow = int(self.axesParams['editLine']['qLine0'].text())
        blockIndices = blockIndices - nChanToShow
        if blockIndices[0] <= 0:
            blockIndices = np.arange(0, nChanToShow) #first possible block
            
        self.channelScrollDown = blockIndices
        self.refreshScreen()
        
    def page_forward(self):
        n, m = np.shape(self.ecog['data'])       
        self.getCurXAxisPosition()
        # check if inteval length is appropriate        
        if self.intervalLengthSamples > n:
            #set interval length to available data
            self.intervalLengthSamples = n        
        #new interval start
        
        self.intervalStartSamples = self.intervalStartSamples \
        + self.intervalLengthSamples        
       
        #if the last sample of the new interval is beyond is the available data
        # set start such that intserval is in a valid range
        if self.intervalStartSamples + self.intervalLengthSamples > n:
            self.intervalStartSamples = n - self.intervalLengthSamples + 1
        
        
        self.setXAxisPositionSamples()
        self.refreshScreen()
        
    def setXAxisPositionSamples(self):
        t = 1000/self.ecog['sampDur'][0][0]
        self.axesParams['editLine']['qLine2'].setText(str(self.intervalStartSamples/t))
        self.axesParams['editLine']['qLine3'].setText(str(self.intervalLengthSamples/t))
        
    def page_back(self):
        n, m = np.shape(self.ecog['data'])
        self.getCurXAxisPosition()
        #new interval start
        self.intervalStartSamples = self.intervalStartSamples - self.intervalLengthSamples
        
        # if the last sample of the new interval is beyond is the available data
        # set start such that intserval is in a valid range
        if self.intervalStartSamples < 1:
            self.intervalStartSamples = 1
        
        self.setXAxisPositionSamples()
        self.refreshScreen()
        
    def scroll_back(self):
        n, m = np.shape(self.ecog['data'])
        self.getCurXAxisPosition()
        #new interval start
        self.intervalStartSamples = self.intervalStartSamples - self.intervalLengthSamples/3
        
        # if the last sample of the new interval is beyond is the available data
        # set start such that intserval is in a valid range
        if self.intervalStartSamples < 1:
            self.intervalStartSamples = 1
        
        self.setXAxisPositionSamples()
        self.refreshScreen()

    def scroll_forward(self):
        n, m = np.shape(self.ecog['data'])       
        self.getCurXAxisPosition()
        # check if inteval length is appropriate        
        if self.intervalLengthSamples > n:
            #set interval length to available data
            self.intervalLengthSamples = n        
        #new interval start
        
        self.intervalStartSamples = self.intervalStartSamples \
        + self.intervalLengthSamples/3        
       
        #if the last sample of the new interval is beyond is the available data
        # set start such that intserval is in a valid range
        if self.intervalStartSamples + self.intervalLengthSamples > n:
            self.intervalStartSamples = n - self.intervalLengthSamples + 1
        
        self.setXAxisPositionSamples()
        self.refreshScreen()

    def verticalScaleIncrease(self):
        scaleFac = float(self.axesParams['editLine']['qLine4'].text())
        self.axesParams['editLine']['qLine4'].setText(str(scaleFac * 2))        
        self.refreshScreen()
        
    def verticalScaleDecrease(self):
        scaleFac = float(self.axesParams['editLine']['qLine4'].text())
        self.axesParams['editLine']['qLine4'].setText(str(scaleFac/2.0))        
        self.refreshScreen()
        
    def plot_interval(self):
        plotIntervalGuiUnits = float(self.axesParams['editLine']['qLine3'].text())
        sam = self.ecog['sampDur'][0][0]
        n = np.shape(self.ecog['data'])[0]
        
        if plotIntervalGuiUnits * 1000 < sam:
            plotIntervalGuiUnits = self.ecog['sampDur'][0][0]/1000
            self.axesParams['editLine']['qLine3'].setText(str(plotIntervalGuiUnits))
        elif plotIntervalGuiUnits * 1000/sam > n:
            plotIntervalGuiUnits = (n - 1) * sam/1000
            self.axesParams['editLine']['qLine3'].setText(str(plotIntervalGuiUnits))
        self.refreshScreen()        
        
    def start_location(self):
        self.getCurXAxisPosition()
        #interval at least one sample long
        if self.intervalStartSamples < self.ecog['sampDur'][0][0]:
            self.intervalStartSamples = 1 #set to the first sample
            self.setXAxisPositionSamples()       
        
        if self.intervalStartSamples + self.intervalLengthSamples - 1 > \
        np.shape(self.ecog['data'])[0]:
            self.intervalStartSamples = np.shape(self.ecog['data'])[0] - \
            self.intervalLengthSamples + 1
            self.setXAxisPositionSamples()
        
        self.refreshScreen()
        
    def nChannels_Displayed(self):
        nChanToShow = int(self.axesParams['editLine']['qLine0'].text())        
#        nChanToShow = nChanToShow(1)# %make sure we have a scalar
#         make we have sure indices will be in a valid range
        chanToShow = self.channelSelector        
        if nChanToShow < 1:
            nChanToShow = 1
        elif nChanToShow > len(chanToShow):
            nChanToShow = len(chanToShow)
        self.axesParams['editLine']['qLine0'].setText(str(nChanToShow))
        
        self.channelScrollDown = np.arange(0, nChanToShow)        
        self.refreshScreen()
        
    def addBadTimeSeg(self, BadInterval):
#        axes(handles.timeline_axes);        
        x = BadInterval[0]    
        y = 0
        w = np.diff(np.array(BadInterval))[0] 
        h = 1
        c = pg.QtGui.QGraphicsRectItem(x, y, w, h)
        c.setPen(pg.mkPen(color = 'r'))
        c.setBrush(QtGui.QColor(255, 0, 0, 255))        
        self.BIRects = np.append(self.BIRects, [c])        
        if np.size(self.badIntervals) == 0:
            self.badIntervals = np.array([BadInterval])
        else:
            self.badIntervals = np.vstack((self.badIntervals, np.array(BadInterval)))
                  
        
    def deleteInterval(self, x):
        BIs = self.badIntervals       
        di = np.where((x >= BIs[:, 0]) & (x <= BIs[:, 1]))       
        if np.size(di) > 0:
            self.axesParams['pars']['Figure'][1].removeItem(self.BIRects[di[0][0]])
            self.BIRects = np.delete(self.BIRects, di[0][0], axis = 0)    
            self.badIntervals = np.delete(self.badIntervals, di, axis = 0)            
            badTimeSegments = self.badIntervals
            file_name = os.path.join(self.pathName, 'Artifacts', 'badTimeSegments')
            scipy.io.savemat(file_name, {'badTimeSegments': badTimeSegments})            
            self.refreshScreen()
            
            
    def pushSave(self):
        BAD_INTERVALS = self.badIntervals
        fullfile = os.path.join(self.pathName, 'Artifacts', 'bad_time_segments.lab')
        n_size = np.shape(BAD_INTERVALS)[0]
        one = np.ones((n_size, 1))
        variable = np.hstack((BAD_INTERVALS, one))
        f.BadTimesConverterGUI(variable, fullfile)        
        badTimeSegments = BAD_INTERVALS
        file_name = os.path.join(self.pathName, 'Artifacts', 'badTimeSegments')
        scipy.io.savemat(file_name, {'badTimeSegments': badTimeSegments})
        my_file = os.path.join(self.pathName, 'Artifacts', 'info.txt')
        if not os.path.exists(my_file):
            username, okPressed = QInputDialog.getText(self, 'Enter Text', 'Who is this:', QLineEdit.Normal, '')
            if okPressed and username != '':
                fileid = open(os.path.join(self.pathName, 'Artifacts', 'info.txt'), 'w')
                fileid.write(username + ' ' + datetime.datetime.today().strftime('%Y-%m-%d'))
                fileid.close()
        else:
            fileid = open(os.path.join(self.pathName, 'Artifacts', 'info.txt'), 'a')
            fileid.write(' ' + datetime.datetime.today().strftime('%Y-%m-%d'))
            fileid.close()

    def getChannel(self):
        x = self.x_cur
        y = self.y_cur
    
        if (x == []):
            pass
        else:
            start_ = float(self.axesParams['editLine']['qLine2'].text())
            end_ = float(self.axesParams['editLine']['qLine3'].text())
            points = np.round(np.linspace(start_, end_, np.shape(self.plotData)[1]), 2)
            
            index = np.where(points == round(x, 2))
            
            DataIndex = index[0][0]
#            print(index)
            y_points = self.plotData[:, DataIndex]
            diff_ = abs(np.array(y_points) - y)
            index = np.argmin(diff_)
            chanel = self.showChan + 1
            channel = chanel[index]

                
                
            plt = self.axesParams['pars']['Figure'][0]  
            yaxis = plt.getAxis('left').range
            ymin, ymax = yaxis[0], yaxis[1]    
           
#            plt.setTitle('Selected Channel:' + str(channel))
            if self.h != []:
                plt.removeItem(self.h)
            text_ = 'x:' + str(round(x, 2)) + '\n' + 'y:' + str(round(y, 2))      
            self.h = pg.TextItem(text_, color = pg.mkColor(70, 70, 70), border = pg.mkPen(200, 200, 200), 
                            fill = pg.mkBrush(250, 250, 150, 180))
            
            self.h.setPos(x, y)
            plt.addItem(self.h)
            
            if self.text != []:
                plt.removeItem(self.text)
            self.text = pg.TextItem('Selected Channel:' + str(channel), color = 'r', border = pg.mkPen(200, 200, 200))
            self.text.setPos(end_/2 - 2, ymax + 10)
            self.text.setFont(QtGui.QFont('SansSerif', 10))
            plt.addItem(self.text)

            
            
            
        
