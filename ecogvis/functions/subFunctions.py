#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Created on Fri Jul 13 21:32:20 2018

@author: lenovo_i5
"""
import os
import scipy.io
from scipy import signal
import numpy as np
import pandas as pd
import h5py
from ast import literal_eval as make_tuple
from PyQt5.QtWidgets import QInputDialog, QLineEdit, QFileDialog, QMessageBox
from PyQt5 import QtGui, QtCore
import pyqtgraph as pg
import datetime
import pynwb
import nwbext_ecog

class ecogVIS:
    def __init__(self, par, parameters):
        self.parent = par
        self.fullpath = par.file
        self.pathName = os.path.split(os.path.abspath(par.file))[0] #path
        self.fileName = os.path.split(os.path.abspath(par.file))[1] #file
        self.axesParams = parameters
        self.parent.setWindowTitle('ecogVIS - ' + self.fileName)

        self.io = pynwb.NWBHDF5IO(self.fullpath,'r+')
        self.nwb = self.io.read()      #reads NWB file
        self.ecog = self.nwb.acquisition['ECoG']              #ecog
        self.plotData = self.ecog.data
        # Get Brain regions present in current file
        self.all_regions = list(set(self.nwb.electrodes['location'][:].tolist()))
        self.all_regions.sort()
        self.regions_mask = [True]*len(self.all_regions)

        self.channels_mask = np.ones(len(self.nwb.electrodes['location'][:]))
        self.channels_mask_ind = np.where(self.channels_mask)[0]

        self.h = []
        self.text = []
        self.AnnotationsList = []
        self.AnnotationsPosAV = np.array([])    #(x, y_va, y_off)
        self.unsaved_changes_annotation = False
        self.unsaved_changes_interval = False

        self.fs_signal = self.ecog.rate     #sampling frequency [Hz]
        self.tbin_signal = 1/self.fs_signal #time bin duration [seconds]
        self.nBins = self.ecog.data.shape[0]     #total number of bins
        self.nChTotal = self.ecog.data.shape[1]     #total number of channels
        self.allChannels = np.arange(0, self.nChTotal)  #array with all channels
        # Channels to show
        self.firstCh = int(self.axesParams['editLine']['qLine1'].text())
        self.lastCh = int(self.axesParams['editLine']['qLine0'].text())
        self.nChToShow = self.lastCh - self.firstCh + 1
        self.selectedChannels = np.arange(self.firstCh-1, self.lastCh)

        self.current_rect = []
        self.badChannels = np.where( self.nwb.electrodes['bad'][:] )[0].tolist()

        # Load invalid intervals from NWB file
        self.allIntervals = []
        if self.nwb.invalid_times is not None:
            self.nBI = self.nwb.invalid_times.columns[0][:].shape[0] #number of BI
            for ii in np.arange(self.nBI):
                # create new interval
                obj = CustomInterval()
                obj.start = self.nwb.invalid_times.columns[0][ii]
                obj.stop = self.nwb.invalid_times.columns[1][ii]
                obj.type = 'invalid'
                obj.color = 'red'
                obj.user = ''
                self.allIntervals.append(obj)

        # Plot interval rectangles at upper and middle pannels
        self.IntRects1 = np.array([], dtype = 'object')
        self.IntRects2 = np.array([], dtype = 'object')
        for i, obj in enumerate(self.allIntervals):
            start = obj.start
            stop = obj.stop
            # on timeline
            c = pg.QtGui.QGraphicsRectItem(start, -1, max(stop-start, 0.01), 2)
            self.IntRects1 = np.append(self.IntRects1, c)
            c.setPen(pg.mkPen(color = 'r'))
            c.setBrush(QtGui.QColor(255, 0, 0, 250))
            a = self.axesParams['pars']['Figure'][1]
            a.addItem(c)
            # on signals plot
            c = pg.QtGui.QGraphicsRectItem(start, -1, max(stop-start, 0.01), 2)
            self.IntRects2 = np.append(self.IntRects2, c)
            c.setPen(pg.mkPen(color = 'r'))
            c.setBrush(QtGui.QColor(255, 0, 0, 120))
            a = self.axesParams['pars']['Figure'][0]
            a.addItem(c)


        # Load stimulus signal (audio)
        self.nStim = len(self.nwb.stimulus)
        self.stimList = list(self.nwb.stimulus.keys())
        self.stimY = {}
        for stim in self.stimList:
            self.parent.combo4.addItem(stim)   #add stimulus name to dropdown button
            dt_stim = 1./self.nwb.stimulus[stim].rate
            nb_stim = self.nwb.stimulus[stim].data.shape[0]
            self.stimX = np.linspace(dt_stim, nb_stim*dt_stim, nb_stim)
            self.stimY[stim] = self.nwb.stimulus[stim].data

            #nb_stim = self.nwb.stimulus[stim].data.shape[0]
            #output = self.stimResample(self.nwb.stimulus[stim], int(nb_stim/100))
            #self.stimY[stim] = output[0]
            #self.stimX = output[1]

            #self.downsampled = self.audio_resample(10)
            #self.audio['sampling_rate'] = self.audio['sampling_rate']/10000
            #self.fs_audio = self.audio['sampling_rate']/10
            #self.taudio = np.arange(1, np.shape(self.downsampled)[0])/self.fs_audio
        else:
            self.disp_audio = 0


        # Initiate plots
        self.getCurAxisParameters()
        self.refreshScreen()


    # Re-opens the file, for when new data is included
    def refresh_file(self):
        self.io.close()   #closes current NWB file
        self.io = pynwb.NWBHDF5IO(self.fullpath,'r+')
        self.nwb = self.io.read()      #reads NWB file
        self.ecog = self.nwb.acquisition['ECoG']    #ecog
        self.plotData = self.ecog.data
        self.fs_signal = self.ecog.rate     #sampling frequency [Hz]
        self.tbin_signal = 1/self.fs_signal #time bin duration [seconds]
        self.nBins = self.ecog.data.shape[0]     #total number of bins
        self.updateCurXAxisPosition()


    # Re-draws all plots
    def refreshScreen(self):
        self.TimeSeries_plotter()


    # Plots time series signals ------------------------------------------------
    def TimeSeries_plotter(self):
        startSamp = self.intervalStartSamples
        endSamp = self.intervalEndSamples

        # Use the same scaling factor for all channels, to keep things comparable
        self.verticalScaleFactor = float(self.axesParams['editLine']['qLine4'].text())
        scaleFac = 2*np.std(self.plotData[startSamp:endSamp, self.selectedChannels-1], axis=0)/self.verticalScaleFactor

        # Scale variance_units, offset for each channel
        scale_va = np.max(scaleFac)
        self.scaleVec = np.arange(1, self.nChToShow + 1) * scale_va

        scaleV = np.zeros([len(self.scaleVec), 1])
        scaleV[:, 0] = self.scaleVec

        # constrains the plotData to the chosen interval (and transpose matix)
        # plotData dims=[self.nChToShow, plotInterval]
        try:
            data = self.plotData[startSamp - 1 : endSamp, self.selectedChannels-1].T
            means = np.reshape(np.mean(data, 1),(-1,1))  #to align each trace around its reference trace
            plotData = data + np.tile(scaleV-means, (1, endSamp - startSamp + 1)) # data + offset
        except:  #if time segment shorter than window.
            data = self.plotData[:, self.selectedChannels-1].T
            means = np.reshape(np.mean(data, 1),(-1,1))  #to align each trace around its reference trace
            plotData = data + np.tile(scaleV-means, (1, endSamp - startSamp + 1)) # data + offset


        # Upper horizontal bar
        plt1 = self.axesParams['pars']['Figure'][1]
        plt1.clear()
        max_dur = self.nBins * self.tbin_signal
        plt1.plot([0, max_dur], [0, 0], pen=pg.mkPen('k', width=2))
        plt1.setXRange(0, max_dur)
        plt1.setYRange(-1, 1)

        if self.current_rect != []:
            plt1.removeItem(self.current_rect)

        #self.current_rect = pg.LinearRegionItem()
        #self.current_rect.setMovable(False)
        #plt1.addItem(self.current_rect)
        ## Rectangle Plot
        x = float(self.axesParams['editLine']['qLine2'].text())
        w = float(self.axesParams['editLine']['qLine3'].text())
        self.current_rect = CustomBox(self, x, -1000, w, 2000)
        self.current_rect.setPen(pg.mkPen(color=(0,0,0,50)))
        self.current_rect.setBrush(QtGui.QColor(0,0,0,50))
        self.current_rect.setFlags(QtGui.QGraphicsItem.ItemIsMovable)
        plt1.addItem(self.current_rect)
        plt1.setLabel('left', 'Span')
        plt1.getAxis('left').setWidth(w=53)
        plt1.getAxis('left').setStyle(showValues=False)
        plt1.getAxis('left').setTicks([])

        # Show Intervals
        for i in range(len(self.IntRects1)):
            plt1.removeItem(self.IntRects1[i])
        for i in range(len(self.IntRects1)):
            plt1.addItem(self.IntRects1[i])


        # Middle signals plot
        # A line indicating reference for every channel
        timebaseGuiUnits = np.arange(startSamp - 1, endSamp) * (self.intervalStartGuiUnits/self.intervalStartSamples)
        x = np.tile([timebaseGuiUnits[0], timebaseGuiUnits[-1]], (len(self.scaleVec), 1))
        y = np.hstack((scaleV, scaleV))
        plt2 = self.axesParams['pars']['Figure'][0]   #middle signal plot
        plt2.clear()
        #Channels reference lines
        for l in range(np.shape(x)[0]):
            plt2.plot(x[l], y[l], pen = 'k')

        # Iterate over chosen channels, plot one at a time
        nrows, ncols = np.shape(plotData)
        for i in range(nrows):
            if self.selectedChannels[i] in self.badChannels:
                plt2.plot(timebaseGuiUnits, plotData[i], pen=pg.mkPen((200,0,0,100), width=.8))
            else:
                c = pg.mkPen((0,120,0), width=1.2)
                if i%2 == 0:
                    c = pg.mkPen((0,0,200), width=1.2)
                plt2.plot(timebaseGuiUnits, plotData[i], pen=c)
        plt2.setLabel('bottom', 'Time', units = 'sec')
        plt2.setLabel('left', 'Channel #')
        labels = [str(ch+1) for ch in self.selectedChannels]
        ticks = list(zip(y[:, 0], labels))
        plt2.getAxis('left').setTicks([ticks])
        plt2.setXRange(timebaseGuiUnits[0], timebaseGuiUnits[-1], padding = 0.003)
        plt2.setYRange(y[0, 0], y[-1, 0], padding = 0.06)
        plt2.getAxis('left').setWidth(w=53)

        # Show Intervals
        for i in range(len(self.IntRects2)):
            plt2.removeItem(self.IntRects2[i])
        for i in range(len(self.IntRects2)):
            plt2.addItem(self.IntRects2[i])

        # Show Annotations
        for i in range(len(self.AnnotationsList)):
            plt2.removeItem(self.AnnotationsList[i])
        for i in range(len(self.AnnotationsList)):
            aux = self.AnnotationsList[i]
            x = self.AnnotationsPosAV[i,0]
            # Y to plot = (Y_va + Channel offset)*scale_variance
            y_va = self.AnnotationsPosAV[i,1]
            y = (y_va + self.AnnotationsPosAV[i,2] - self.firstCh) * scale_va
            aux.setPos(x,y)
            plt2.addItem(aux)

        # Bottom plot - Stimuli
        plt3 = self.axesParams['pars']['Figure'][2]
        plt3.clear()
        if self.parent.combo4.currentText() is not '':
            xmask = (self.stimX > timebaseGuiUnits[0]) * (self.stimX < timebaseGuiUnits[-1])
            stimName = self.parent.combo4.currentText()
            stimData = self.stimY[stimName]
            plt3.plot(self.stimX[xmask], stimData[xmask], pen='k', width=1)
            plt3.setXLink(plt2)
        plt3.setLabel('left', 'Stim')
        plt3.getAxis('left').setWidth(w=53)
        plt3.getAxis('left').setStyle(showValues=False)
        plt3.getAxis('left').setTicks([])

        #set colors
        plt1.getAxis('left').setPen(pg.mkPen(color=(50,50,50)))
        plt2.getAxis('left').setPen(pg.mkPen(color=(50,50,50)))
        plt2.getAxis('bottom').setPen(pg.mkPen(color=(50,50,50)))
        plt3.getAxis('left').setPen(pg.mkPen(color=(50,50,50)))



    def drag_window(self, dt):
        self.axesParams['editLine']['qLine2'].setText(str(self.intervalStartGuiUnits + dt))
        self.updateCurXAxisPosition()


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
        self.intervalStartSamples = int(max(np.floor(self.intervalStartGuiUnits / self.tbin_signal),1))
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


    def stimResample(self, stim, num=100):
        dt_stim = 1./stim.rate
        nb_stim = stim.data.shape[0]
        x = np.linspace(dt_stim, nb_stim*dt_stim, nb_stim)
        yrs, xrs = signal.resample(stim.data[:], num, t=x)
        return yrs, xrs



    # Updates the channels to be plotted
    # Buttons: ^, ^^
    def channel_Scroll_Up(self, opt='unit'):
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
            self.selectedChannels = self.channels_mask_ind[self.firstCh-1:self.lastCh]
        self.refreshScreen()


    # Buttons: v, vv
    def channel_Scroll_Down(self, opt='unit'):
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
            self.selectedChannels = self.channels_mask_ind[self.firstCh-1:self.lastCh]
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
        n = model.nBins
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
        self.selectedChannels = self.channels_mask_ind[self.firstCh-1:self.lastCh]
        self.axesParams['editLine']['qLine0'].setText(str(self.lastCh))
        self.axesParams['editLine']['qLine1'].setText(str(self.firstCh))
        self.refreshScreen()


    ## Annotation functions ----------------------------------------------------
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
        self.unsaved_changes_annotation = True


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
            self.unsaved_changes_annotation = True


    def AnnotationSave(self):
        buttonReply = QMessageBox.question(None, ' ', 'Save annotations on external file?',
                                           QMessageBox.No | QMessageBox.Yes)
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
            self.unsaved_changes_annotation = False


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



    ## Interval functions ------------------------------------------------------
    def IntervalAdd(self, interval, int_type, color, user):
        if color=='yellow':
            bc = [250, 250, 150, 180]
        elif color=='red':
            bc = [250, 0, 0, 100]
        elif color=='green':
            bc = [0, 255, 0, 130]
        elif color=='blue':
            bc = [0, 0, 255, 100]
        x = interval[0]
        w = np.diff(np.array(interval))[0]
        # add rectangle to upper plot
        c = pg.QtGui.QGraphicsRectItem(x, 0, w, 1)
        c.setPen(pg.mkPen(color=QtGui.QColor(bc[0], bc[1], bc[2], 255)))
        c.setBrush(QtGui.QColor(bc[0], bc[1], bc[2], 255))
        self.IntRects1 = np.append(self.IntRects1, [c])
        # add rectangle to middle signal plot
        c = pg.QtGui.QGraphicsRectItem(x, -1, w, 2)
        c.setPen(pg.mkPen(color=QtGui.QColor(bc[0], bc[1], bc[2], 255)))
        c.setBrush(QtGui.QColor(bc[0], bc[1], bc[2], bc[3]))
        self.IntRects2 = np.append(self.IntRects2, [c])
        # new Interval object
        obj = CustomInterval()
        obj.start = interval[0]
        obj.stop = interval[1]
        obj.type = int_type
        obj.color = color
        obj.user = user
        self.allIntervals.append(obj)
        self.nBI = len(self.allIntervals)
        self.unsaved_changes_interval = True


    def IntervalDel(self, x):
        for i, obj in enumerate(self.allIntervals):
            if (x >= obj.start) & (x <= obj.stop):   #interval of the click
                self.axesParams['pars']['Figure'][1].removeItem(self.IntRects1[i])
                self.IntRects1 = np.delete(self.IntRects1, i, axis = 0)
                self.axesParams['pars']['Figure'][0].removeItem(self.IntRects2[i])
                self.IntRects2 = np.delete(self.IntRects2, i, axis = 0)
                del self.allIntervals[i]
                self.nBI = len(self.allIntervals)
                self.refreshScreen()
                self.unsaved_changes_interval = True


    def IntervalSave(self):
        buttonReply = QMessageBox.question(None, ' ', 'Save intervals on external file?',
                                           QMessageBox.No | QMessageBox.Yes)
        if buttonReply == QMessageBox.Yes:
            c0, c1, c2, c3, c4 = [], [], [], [], []
            for i, obj in enumerate(self.allIntervals):
                c0.append(obj.start)     # start
                c1.append(obj.stop)      # stop
                c2.append(obj.type)      # type
                c3.append(obj.color)     # color
                c4.append(obj.user)      # user
            d = {'start':c0, 'stop':c1, 'type':c2, 'color':c3, 'user':c4}
            df = pd.DataFrame(data=d)
            fullfile = os.path.join(self.pathName, self.fileName[:-4] + '_intervals_' +
                                    datetime.datetime.today().strftime('%Y-%m-%d')+
                                    '.csv')
            df.to_csv(fullfile, header=True, index=True)
            self.unsaved_changes_interval = False


    def IntervalLoad(self, fname):
        df = pd.read_csv(fname)
        for index, row in df.iterrows():    # Add loaded intervals to graph
            interval = [row.start, row.stop]
            int_type = row.type
            color = row.color
            user = row.user
            self.IntervalAdd(interval, int_type, color, user)
            #Update dictionary of interval types
            # TO-DO
        self.refreshScreen()


    # Channels functions -------------------------------------------------------
    def BadChannelAdd(self, ch_list):  #ch is list of integers
        for ch in ch_list:
            if ch not in self.badChannels:
                self.badChannels.append(ch)
        self.refreshScreen()

    def BadChannelDel(self, ch_list):  #ch is list of integers
        for ch in ch_list:
            if ch in self.badChannels:
                self.badChannels.remove(ch)
        self.refreshScreen()

    def BadChannelSave(self):
        # opens dialog for user confirmation
        buttonReply = QMessageBox.question(None, ' ', 'Save Bad Channels on current NWB file?',
                                           QMessageBox.No | QMessageBox.Yes)
        if buttonReply == QMessageBox.Yes:
            # Modify current list of bad channels
            aux = [False]*self.nChTotal
            for ind in self.badChannels:
                aux[ind] = True
            self.nwb.electrodes['bad'].data[:] = aux



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



class CustomInterval:
    def __init__(self):
        self.start = -999
        self.stop = -999
        self.type = ''
        self.color = ''
        self.user = ''
        self.channels = []


class CustomBox(pg.QtGui.QGraphicsRectItem):
    def __init__(self, parent, x, y, w, h):
        pg.QtGui.QGraphicsRectItem.__init__(self, x, y, w, h)
        self.parent = parent
    def mouseReleaseEvent(self, event):
        dt = self.x()
        self.parent.drag_window(dt)
