#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Created on Fri Jul 13 21:32:20 2018

@author: lenovo_i5
"""
import os
import scipy.io
import numpy as np
import pandas as pd
import h5py
from ast import literal_eval as make_tuple
from PyQt5.QtWidgets import QInputDialog, QLineEdit, QFileDialog, QMessageBox
import datetime
#import Function.BadTimesConverterGUI as f
import pyqtgraph as pg
from PyQt5 import QtGui

import pynwb
import nwbext_ecog

class ecogTSGUI:
    def __init__(self, par, pathName, parameters):
        self.parent = par
        self.pathName = os.path.split(os.path.abspath(pathName))[0] #path
        self.fileName = os.path.split(os.path.abspath(pathName))[1] #file
        self.axesParams = parameters

        nwb = pynwb.NWBHDF5IO(pathName,'r').read()      #reads NWB file
        self.ecog = nwb.acquisition['ECoG']             #ecog

        self.h = []
        self.text = []
        self.AnnotationsList = []
        self.AnnotationsPosAV = np.array([])    #(x, y_va, y_off)

        self.nBins = self.ecog.data.shape[0]     #total number of bins
        self.nChTotal = self.ecog.data.shape[1]     #total number of channels
        self.allChannels = np.arange(0, self.nChTotal)  #array with all channels
        # Channels to show
        self.firstCh = int(self.axesParams['editLine']['qLine1'].text())
        self.lastCh = int(self.axesParams['editLine']['qLine0'].text())
        self.nChToShow = self.lastCh - self.firstCh + 1
        self.selectedChannels = np.arange(self.firstCh, self.lastCh + 1)

        self.rawecog = self.ecog.data       #ecog signals
        self.fs_signal = self.ecog.rate     #sampling frequency [Hz]
        self.tbin_signal = 1/self.fs_signal #time bin duration [seconds]

        self.current_rect = []
        self.badChannels = np.where( nwb.electrodes['bad'][:] )

        # Bad intervals
        if nwb.invalid_times == None:
            self.badIntervals = np.array([])
        else:
            self.nBI = nwb.invalid_times.columns[0][:].shape[0] #number of BI
            self.badIntervals = np.empty([self.nBI,2])
            for ii in np.arange(self.nBI):
                # start of bad interval
                self.badIntervals[ii,0] = nwb.invalid_times.columns[0][ii]
                # end of bad interval
                self.badIntervals[ii,1] = nwb.invalid_times.columns[1][ii]

        # menu('load audio?','yes','no') == 1
        if os.path.exists(os.path.join(pathName, 'Analog', 'ANIN4.htk')):
            self.disp_audio = 1
            self.audio = readHTK(os.path.join(pathName, 'Analog', 'ANIN4.htk'))

            self.downsampled = self.downsample(10)
            self.audio['sampling_rate'] = self.audio['sampling_rate']/10000
            self.fs_audio = self.audio['sampling_rate']/10
            self.taudio = np.arange(1, np.shape(self.downsampled)[0])/self.fs_audio
        else:
            self.disp_audio = 0

        total_dur = np.shape(self.ecog.data)[0]/self.fs_signal
        self.axesParams['pars']['Figure'][1].plot([0, total_dur], [0.5, 0.5], pen = 'k', width = 0.5)

        # plot bad time segments
        BIs = self.badIntervals
        self.BIRects1 = np.array([], dtype = 'object')   #red rectangles at upper bar plot
        self.BIRects2 = np.array([], dtype = 'object')   #red rectangles at middle signal plot
        for i in range(self.nBI):
            # on timeline
            c = pg.QtGui.QGraphicsRectItem(BIs[i][0], 0, max([BIs[i][1] - BIs[i][0], 0.01]), 1)
            self.BIRects1 = np.append(self.BIRects1, c)
            c.setPen(pg.mkPen(color = 'r'))
            c.setBrush(QtGui.QColor(255, 0, 0, 250))
            a = self.axesParams['pars']['Figure'][1]
            a.addItem(c)
            # on signals plot
            c = pg.QtGui.QGraphicsRectItem(BIs[i][0], 0, max([BIs[i][1] - BIs[i][0], 0.01]), 1)
            self.BIRects2 = np.append(self.BIRects2, c)
            c.setPen(pg.mkPen(color = 'r'))
            c.setBrush(QtGui.QColor(255, 0, 0, 120))
            a = self.axesParams['pars']['Figure'][0]
            a.addItem(c)


        # Initiate interval to show
        self.getCurAxisParameters()

        self.refreshScreen()


    def refreshScreen(self):
        self.AR_plotter()


    def AR_plotter(self):
        #self.getCurAxisParameters()
        startSamp = self.intervalStartSamples
        endSamp = self.intervalEndSamples
        timebaseGuiUnits = np.arange(startSamp - 1, endSamp) * (self.intervalStartGuiUnits/self.intervalStartSamples)

        # Use the same scaling factor for all channels, to keep things comparable
        self.verticalScaleFactor = float(self.axesParams['editLine']['qLine4'].text())
        scaleFac = 2*np.std(self.ecog.data[startSamp:endSamp, self.selectedChannels-1], axis=0)/self.verticalScaleFactor

        # Scale variance_units, offset for each channel
        scale_va = np.max(scaleFac)
        self.scaleVec = np.arange(1, self.nChToShow + 1) * scale_va

        scaleV = np.zeros([len(self.scaleVec), 1])
        scaleV[:, 0] = self.scaleVec

        # constrains the plotData to the chosen interval (and transpose matix)
        # plotData dims=[self.nChToShow, plotInterval]
        try:
            data = self.ecog.data[startSamp - 1 : endSamp, self.selectedChannels-1].T
            plotData = data + np.tile(scaleV, (1, endSamp - startSamp + 1)) # data + offset
        except:  #if time segment shorter than window.
            data = self.ecog.data[:, self.selectedChannels-1].T
            plotData = data + np.tile(scaleV, (1, endSamp - startSamp + 1)) # data + offset
        self.plotData = []
        self.plotData = plotData

        ## Rectangle Plot
        x = float(self.axesParams['editLine']['qLine2'].text())
        w = float(self.axesParams['editLine']['qLine3'].text())

        # Upper horizontal bar
        plt2 = self.axesParams['pars']['Figure'][1]
        if self.current_rect != []:
            plt2.removeItem(self.current_rect)

        self.current_rect = pg.QtGui.QGraphicsRectItem(x, 0, w, 1)
        self.current_rect.setPen(pg.mkPen(color = 'k'))
        self.current_rect.setBrush(QtGui.QColor(0, 255, 0, 200))
        plt2.addItem(self.current_rect)

        for i in range(len(self.BIRects1)):
            plt2.removeItem(self.BIRects1[i])
        for i in range(len(self.BIRects1)):
            plt2.addItem(self.BIRects1[i])


        # Middle signals plot
        # A line indicating reference for every channel
        x = np.tile([timebaseGuiUnits[0], timebaseGuiUnits[-1]], (len(self.scaleVec), 1))
        y = np.hstack((scaleV, scaleV))
        plt = self.axesParams['pars']['Figure'][0]   #middle signal plot
        # Clear plot
        plt.clear()
        for l in range(np.shape(x)[0]):
            plt.plot(x[l], y[l], pen = 'k')
        plt.setLabel('bottom', 'Time', units = 'sec')
        plt.setLabel('left', 'Channel #')

        labels = [str(ch) for ch in self.selectedChannels]
        ticks = list(zip(y[:, 0], labels))

        plt.getAxis('left').setTicks([ticks])

        # Find bad and valid channels from self.selectedChannels
        badCh = np.intersect1d(self.selectedChannels, self.badChannels)
        validCh = np.setdiff1d(self.selectedChannels, self.badChannels)
        nrows, ncols = np.shape(plotData)

        # Iterate over chosen channels, plot one at a time
        for i in range(nrows):
            if i in badCh:
                plt.plot(timebaseGuiUnits, plotData[i], pen = 'r', width = 1)
            else:
                c = 'g'
                if i%2 == 0:
                    c = 'b'
                #plt.plot(timebaseGuiUnits, plotData[i], pen = pg.mkPen(c, width = 1))
                plt.plot(timebaseGuiUnits, plotData[i], pen = c, width = 1)


        plt.setXRange(timebaseGuiUnits[0], timebaseGuiUnits[-1], padding = 0.003)
        plt.setYRange(y[0, 0], y[-1, 0], padding = 0.06)

        # Make red box around bad time segments
        for i in range(len(self.BIRects2)):
            plt.removeItem(self.BIRects2[i])
        for i in range(len(self.BIRects2)):
            plt.addItem(self.BIRects2[i])

        # Show Annotations
        for i in range(len(self.AnnotationsList)):
            plt.removeItem(self.AnnotationsList[i])
        for i in range(len(self.AnnotationsList)):
            aux = self.AnnotationsList[i]
            x = self.AnnotationsPosAV[i,0]
            # Y to plot = (Y_va + Channel offset)*scale_variance
            y_va = self.AnnotationsPosAV[i,1]
            y = (y_va + self.AnnotationsPosAV[i,2] - self.firstCh) * scale_va
            aux.setPos(x,y)
            plt.addItem(aux)


        # yaxis = plt.getAxis('left').range
        # ymin, ymax = yaxis[0], yaxis[1]
        # xaxis = plt.getAxis('bottom').range
        # xmin, xmax = xaxis[0], xaxis[1]
        # for i in range(self.nBI):
        #     BI = self.badIntervals[i]
        #     x1, y1, w, h = BI[0], ymin, BI[1] - BI[0], ymax
        #     c = pg.QtGui.QGraphicsRectItem(x1, y1, w, h)
        #     c.setPen(pg.mkPen(color = (255, 255, 200)))
        #     c.setBrush(QtGui.QColor(255, 0, 0, 200))
        #     plt.addItem(c)
        #     self.text1 = pg.TextItem(str(round(BI[0], 3)), color = 'k')
        #     self.text1.setPos(BI[0], ymax)
        #     plt.addItem(self.text1)
        #     self.text2 = pg.TextItem(str(round(BI[1], 3)), color = 'k')
        #     self.text2.setPos(BI[1], ymax)
        #     plt.addItem(self.text2)


        # Plot audio
        if self.disp_audio:
            begin = self.intervalStartGuiUnits
            stop = self.intervalStartGuiUnits + self.intervalLengthGuiUnits
            plt1 = self.axesParams['pars']['Figure'][2]
            plt1.clear()
            ind_disp = np.where((self.taudio > begin) & (self.taudio < stop))
            x_axis = np.linspace(xmin, xmax, len(self.downsampled[ind_disp]))
            plt1.plot(x_axis, self.downsampled[ind_disp], pen = 'r', width = 2)
            plt1.setXLink(plt)
            # plt2.setXLink(plt)




    def getCurAxisParameters(self):
        self.updateCurXAxisPosition()


    # Updates the time interval selected from the user forms,
    # with checks for allowed values
    def updateCurXAxisPosition(self):
        # Read from user forms
        self.intervalStartGuiUnits = float(self.axesParams['editLine']['qLine2'].text())
        self.intervalLengthGuiUnits = float(self.axesParams['editLine']['qLine3'].text())

        max_dur = self.nBins * self.tbin_signal  # Max duration in seconds
        min_len = 1000*self.tbin_signal          # Min accepted length

        # Check for max and min allowed values: START
        if  self.intervalStartGuiUnits < 0.001:
            self.intervalStartGuiUnits = 0.001
        elif self.intervalStartGuiUnits > max_dur-min_len:
            self.intervalStartGuiUnits = max_dur-min_len

        # Check for max and min allowed values: LENGTH
        if self.intervalLengthGuiUnits + self.intervalStartGuiUnits > max_dur:
            self.intervalLengthGuiUnits = max_dur - self.intervalStartGuiUnits
        elif self.intervalLengthGuiUnits < min_len:
            self.intervalLengthGuiUnits = min_len

        # Updates form values (round to miliseconds for display)
        self.intervalStartGuiUnits = np.round(self.intervalStartGuiUnits,3)
        self.intervalLengthGuiUnits = np.round(self.intervalLengthGuiUnits,3)
        self.axesParams['editLine']['qLine2'].setText(str(self.intervalStartGuiUnits))
        self.axesParams['editLine']['qLine3'].setText(str(self.intervalLengthGuiUnits))

        # Updates times in samples
        self.intervalLengthSamples = int(np.floor(self.intervalLengthGuiUnits / self.tbin_signal))
        self.intervalStartSamples = int(np.floor(self.intervalStartGuiUnits / self.tbin_signal))
        self.intervalEndSamples = self.intervalStartSamples + self.intervalLengthSamples

        self.refreshScreen()


    # Updates the plotting time interval range
    def time_window_resize(self, wscale):
        self.intervalLengthGuiUnits = float(self.axesParams['editLine']['qLine3'].text())
        self.intervalLengthGuiUnits = self.intervalLengthGuiUnits * wscale
        self.axesParams['editLine']['qLine3'].setText(str(self.intervalLengthGuiUnits))
        self.updateCurXAxisPosition()


    # Updates the plotting time interval for scrolling
    # Buttons: >>, >, <<, <
    def time_scroll(self, scroll=0):
        #new interval start
        self.intervalStartSamples = self.intervalStartSamples \
                                    + int(scroll * self.intervalLengthSamples)

        #if the last sample of the new interval is beyond is the available data
        # set start such that intserval is in a valid range
        if self.intervalStartSamples + self.intervalLengthSamples > self.nBins:
            self.intervalStartSamples = self.nBins - self.intervalLengthSamples
        elif self.intervalStartSamples < 1:
            self.intervalStartSamples = 1

        #new interval end
        self.intervalEndSamples = self.intervalStartSamples + self.intervalLengthSamples

        # Updates start time in seconds (first avoid <0.001 values)
        self.intervalStartGuiUnits = max(self.intervalStartSamples*self.tbin_signal,0.001)
        # Round to miliseconds for display
        self.intervalStartGuiUnits = np.round(self.intervalStartGuiUnits,3)
        self.intervalEndGuiUnits = self.intervalEndSamples*self.tbin_signal
        self.axesParams['editLine']['qLine2'].setText(str(self.intervalStartGuiUnits))

        self.refreshScreen()


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


    def channel_Scroll_Up(self, opt='unit'): # Buttons: ^, ^^
        # Test upper limit
        if self.lastCh < self.nChTotal:
            if opt=='unit':
                step = 1
            elif opt=='page':
                step = np.minimum(self.nChToShow, self.nChTotal-self.lastCh)
            # Add +1 to first and last channels
            self.firstCh += step
            self.lastCh += step
            self.axesParams['editLine']['qLine0'].setText(str(self.lastCh))
            self.axesParams['editLine']['qLine1'].setText(str(self.firstCh))
            self.nChToShow = self.lastCh - self.firstCh + 1
            self.selectedChannels = np.arange(self.firstCh, self.lastCh + 1)

        self.refreshScreen()


    def channel_Scroll_Down(self, opt='unit'): # Buttons: v, vv
        # Test lower limit
        if self.firstCh > 1:
            if opt=='unit':
                step = 1
            elif opt=='page':
                step = np.minimum(self.nChToShow, self.firstCh-1)
            # Subtract from first and last channels
            self.firstCh -= step
            self.lastCh -= step
            self.axesParams['editLine']['qLine0'].setText(str(self.lastCh))
            self.axesParams['editLine']['qLine1'].setText(str(self.firstCh))
            self.nChToShow = self.lastCh - self.firstCh + 1
            self.selectedChannels = np.arange(self.firstCh, self.lastCh + 1)

        self.refreshScreen()


    def verticalScaleIncrease(self):
        scaleFac = float(self.axesParams['editLine']['qLine4'].text())
        self.axesParams['editLine']['qLine4'].setText(str(scaleFac * 2))
        self.refreshScreen()


    def verticalScaleDecrease(self):
        scaleFac = float(self.axesParams['editLine']['qLine4'].text())
        self.axesParams['editLine']['qLine4'].setText(str(scaleFac/2.0))
        self.refreshScreen()


    def time_window_size(self):
        plotIntervalGuiUnits = float(self.axesParams['editLine']['qLine3'].text())
        n = self.ecog.data.shape[0]

        # Minimum time interval
        if plotIntervalGuiUnits < self.tbin_signal:
            plotIntervalGuiUnits = self.tbin_signal
            self.axesParams['editLine']['qLine3'].setText(str(plotIntervalGuiUnits))
        elif plotIntervalGuiUnits/self.tbin_signal > n:
            plotIntervalGuiUnits = (n - 1) * self.tbin_signal
            self.axesParams['editLine']['qLine3'].setText(str(plotIntervalGuiUnits))
        self.refreshScreen()


    def interval_start(self):
        self.updateCurXAxisPosition()

        # Interval at least one sample long
        if self.intervalStartSamples < self.tbin_signal:
            self.intervalStartSamples = 1   #set to the first sample
            self.setXAxisPositionSamples()

        # Maximum interval size
        if self.intervalStartSamples + self.intervalLengthSamples - 1 > self.nBins:
            self.intervalStartSamples = self.nBins - self.intervalLengthSamples + 1
            self.setXAxisPositionSamples()

        self.refreshScreen()


    def nChannels_Displayed(self):
        # Update channels to show
        self.firstCh = int(self.axesParams['editLine']['qLine1'].text())
        self.lastCh = int(self.axesParams['editLine']['qLine0'].text())

        # Make sure indices are in a valid range
        if self.firstCh < 1:
            self.firstCh = 1

        if self.firstCh > self.nChTotal:
            self.firstCh = self.nChTotal
            self.lastCh = self.nChTotal

        if self.lastCh < 1:
            self.lastCh = self.firstCh

        if self.lastCh > self.nChTotal:
            self.lastCh = self.nChTotal

        if self.lastCh - self.firstCh < 1:
            self.lastCh = self.firstCh

        #Update variables and values displayed on forms
        self.nChToShow = self.lastCh - self.firstCh + 1
        self.selectedChannels = np.arange(self.firstCh, self.lastCh + 1)
        self.axesParams['editLine']['qLine0'].setText(str(self.lastCh))
        self.axesParams['editLine']['qLine1'].setText(str(self.firstCh))
        self.refreshScreen()


    def AnnotationLoad(self, fname=''):
        df = pd.read_csv(fname)
        all_x = df['x'].values
        all_y_va = df['y_va'].values
        all_y_off = df['y_off'].values
        texts = df['text'].values.tolist()
        colors_rgb = df['color'].tolist()
        for i, txt in enumerate(texts):    # Add loaded annotations to graph
            rgb = make_tuple(colors_rgb[i])
            bgcolor = pg.mkBrush(rgb[0], rgb[1], rgb[2], rgb[3])
            c = pg.TextItem(anchor=(.5,.5), border=pg.mkPen(100, 100, 100), fill=bgcolor)
            c.setText(text=txt, color=(0,0,0))
            # Y coordinate transformed to variance_units (for plot control)
            y_va = all_y_va[i]
            x = all_x[i]
            c.setPos(x,y_va)
            self.AnnotationsList = np.append(self.AnnotationsList, c)
            if len(self.AnnotationsPosAV) > 0:
                self.AnnotationsPosAV = np.concatenate((self.AnnotationsPosAV,
                                                        np.array([x, y_va, all_y_off[i]]).reshape(1,3)))
            else:
                self.AnnotationsPosAV = np.array([x, y_va, all_y_off[i]]).reshape(1,3)

        self.refreshScreen()


    def AnnotationAdd(self, x, y, color='yellow', text='Event'):
        if color=='yellow':
            bgcolor = pg.mkBrush(250, 250, 150, 200)
        elif color=='red':
            bgcolor = pg.mkBrush(250, 0, 0, 200)
        elif color=='green':
            bgcolor = pg.mkBrush(0, 255, 0, 200)
        elif color=='blue':
            bgcolor = pg.mkBrush(0, 0, 255, 200)
        c = pg.TextItem(anchor=(.5,.5), border=pg.mkPen(100, 100, 100), fill=bgcolor)
        c.setText(text=text, color=(0,0,0))
        # Y coordinate transformed to variance_units (for plot control)
        y_va = y/self.scaleVec[0]
        c.setPos(x,y_va)
        self.AnnotationsList = np.append(self.AnnotationsList, c)
        if len(self.AnnotationsPosAV) > 0:
            self.AnnotationsPosAV = np.concatenate((self.AnnotationsPosAV,
                                                    np.array([x, y_va, self.firstCh]).reshape(1,3)))
        else:
            self.AnnotationsPosAV = np.array([x, y_va, self.firstCh]).reshape(1,3)
        self.refreshScreen()


    def AnnotationDel(self, x, y):
        x_ann = self.AnnotationsPosAV[:,0]
        y_ann = (self.AnnotationsPosAV[:,1] + self.AnnotationsPosAV[:,2] - self.firstCh)*self.scaleVec[0]
        # Calculates euclidian distance from click
        euclid_dist = np.sqrt( (x_ann-x)**2 + (y_ann-y)**2 )
        indmin = np.argmin(euclid_dist)
        # Checks if user intends to delete annotation
        text = self.AnnotationsList[indmin].textItem.toPlainText()
        buttonReply = QMessageBox.question(None,
                                           'Delete Annotation', "Delete the annotation: \n\n"+text+' ?',
                                           QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
        if buttonReply == QMessageBox.Yes:
            self.AnnotationsList = np.delete(self.AnnotationsList, indmin, axis=0)
            self.AnnotationsPosAV = np.delete(self.AnnotationsPosAV, indmin, axis=0)
            self.refreshScreen()


    def AnnotationSave(self):
        buttonReply = QMessageBox.question(None, ' ', 'Save annotations on external file?',
                                           QMessageBox.Yes | QMessageBox.No)
        if buttonReply == QMessageBox.Yes:
            c0 = self.AnnotationsPosAV[:,0]     # x
            c1 = self.AnnotationsPosAV[:,1]     # y_va
            c2 = self.AnnotationsPosAV[:,2]     # y_off
            # colors
            c3 = [self.AnnotationsList[i].fill.color().getRgb() for i in range(len(self.AnnotationsList))]
            # texts
            c4 = [self.AnnotationsList[i].textItem.toPlainText() for i in range(len(self.AnnotationsList))]
            d = {'x':c0, 'y_va':c1, 'y_off':c2, 'color':c3, 'text':c4}
            df = pd.DataFrame(data=d)
            fullfile = os.path.join(self.pathName, self.fileName[:-4] + '_annotations_' +
                                    datetime.datetime.today().strftime('%Y-%m-%d')+
                                    '.csv')
            df.to_csv(fullfile, header=True, index=True)



    def addBadTimeSeg(self, BadInterval):
        #axes(handles.timeline_axes);
        x = BadInterval[0]
        y = 0
        w = np.diff(np.array(BadInterval))[0]
        h = 1
        # add rectangle to upper plot
        c = pg.QtGui.QGraphicsRectItem(x, y, w, h)
        c.setPen(pg.mkPen(color = 'r'))
        c.setBrush(QtGui.QColor(255, 0, 0, 255))
        self.BIRects1 = np.append(self.BIRects1, [c])
        # add rectangle to middle signal plot
        c = pg.QtGui.QGraphicsRectItem(x, y, w, h)
        c.setPen(pg.mkPen(color = 'r'))
        c.setBrush(QtGui.QColor(255, 0, 0, 120))
        self.BIRects2 = np.append(self.BIRects2, [c])
        if np.size(self.badIntervals) == 0:
            self.badIntervals = np.array([BadInterval])
        else:
            self.badIntervals = np.vstack((self.badIntervals, np.array(BadInterval)))
        self.nBI = len(self.badIntervals)


    def deleteInterval(self, x):
        BIs = self.badIntervals
        di = np.where((x >= BIs[:, 0]) & (x <= BIs[:, 1]))   #interval of the click
        if np.size(di) > 0:
            self.axesParams['pars']['Figure'][1].removeItem(self.BIRects1[di[0][0]])
            self.BIRects1 = np.delete(self.BIRects1, di[0][0], axis = 0)
            self.axesParams['pars']['Figure'][0].removeItem(self.BIRects2[di[0][0]])
            self.BIRects2 = np.delete(self.BIRects2, di[0][0], axis = 0)
            self.badIntervals = np.delete(self.badIntervals, di, axis = 0)
            self.nBI = len(self.badIntervals)

            self.refreshScreen()


    def pushSave(self):
        fullfile = os.path.join(self.pathName, 'bad_intervals_'+
                                datetime.datetime.today().strftime('%Y-%m-%d')+
                                '.csv')
        pd.DataFrame(self.badIntervals).to_csv(fullfile, header=False, index=False)
        ## TO DO
        ## SAVE BAD INTERVALS IN HDF5 file
        ## use method  add_invalid_time_interval() in loop for all chosen intervals



    def getChannel(self, mousePoint):
        x = mousePoint.x()
        y = mousePoint.y()
        print('x: ',x,'     y: ',y)

        if (x == []):
            pass
        else:
            start_ = float(self.axesParams['editLine']['qLine2'].text())
            end_ = float(self.axesParams['editLine']['qLine3'].text())
            points = np.round(np.linspace(start_, end_, np.shape(self.plotData)[1]), 2)

            index = np.where(points == round(x, 2))

            DataIndex = index[0][0]
            #print(index)
            y_points = self.plotData[:, DataIndex]
            diff_ = abs(np.array(y_points) - y)
            index = np.argmin(diff_)
            chanel = self.selectedChannels
            channel = chanel[index]

            plt = self.axesParams['pars']['Figure'][0]
            yaxis = plt.getAxis('left').range
            ymin, ymax = yaxis[0], yaxis[1]

            #plt.setTitle('Selected Channel:' + str(channel))
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



    def DrawMarkTime(self, position):
        plt = self.axesParams['pars']['Figure'][0]     #middle signal plot
        self.current_mark = pg.QtGui.QGraphicsRectItem(position, 0, 0, 1)
        self.current_mark.setPen(pg.mkPen(color = 'k'))
        self.current_mark.setBrush(QtGui.QColor(150, 150, 150, 100))
        plt.addItem(self.current_mark)


    def RemoveMarkTime(self):
        plt = self.axesParams['pars']['Figure'][0]     #middle signal plot
        plt.removeItem(self.current_mark)
