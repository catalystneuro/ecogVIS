import os
from scipy import signal
import numpy as np
import pandas as pd
from PyQt5.QtWidgets import QMessageBox
from PyQt5 import QtGui
import pyqtgraph as pg
import datetime
import pynwb
import nwbext_ecog

class TimeSeriesPlotter:
    """
    This class holds the 3 time series subplots in the main window.
    It also holds information of the currently open NWB file, as well as user
    annotations and intervals.
    """
    def __init__(self, par):
        self.parent = par
        self.fullpath = par.file
        self.pathName = os.path.split(os.path.abspath(par.file))[0] #path
        self.fileName = os.path.split(os.path.abspath(par.file))[1] #file
        self.parent.setWindowTitle('ecogVIS - '+self.fileName+' - '+self.parent.current_session)

        self.io = pynwb.NWBHDF5IO(self.fullpath, 'r+', load_namespaces=True)
        self.nwb = self.io.read()      #reads NWB file

        #Tries to load Raw data
        lis = list(self.nwb.acquisition.keys())
        there_is_raw = False
        for i in lis:  # Check if there is ElectricalSeries in acquisition group
            if type(self.nwb.acquisition[i]).__name__ == 'ElectricalSeries':
                self.source = self.nwb.acquisition[i]
                self.parent.combo3.setCurrentIndex(self.parent.combo3.findText('raw'))
                there_is_raw = True
        if not there_is_raw:
            print("No 'ElectricalSeries' object in 'acquisition' group.")
        #Tries to load preprocessed data
        try:
            self.source = self.nwb.processing['ecephys'].data_interfaces['LFP'].electrical_series['preprocessed']
            self.parent.combo3.setCurrentIndex(self.parent.combo3.findText('preprocessed'))
            self.parent.push5_0.setEnabled(True)
            self.parent.push6_0.setEnabled(False)
            self.parent.push7_0.setEnabled(True)
        except:
            print("No 'preprocessed' data in 'processing' group.")
        #Tries to load High Gamma data
        try:
            self.source = self.nwb.processing['ecephys'].data_interfaces['high_gamma']
            self.parent.combo3.setCurrentIndex(self.parent.combo3.findText('high gamma'))
            self.parent.push5_0.setEnabled(False)
            self.parent.push6_0.setEnabled(False)
            self.parent.push7_0.setEnabled(False)
        except:
            print("No 'high_gamma' data in 'processing' group.")
        self.plotData = self.source.data
        self.fs_signal = self.source.rate     #sampling frequency [Hz]
        self.tbin_signal = 1/self.fs_signal #time bin duration [seconds]
        self.nBins = self.source.data.shape[0]     #total number of bins
        self.nChTotal = self.source.data.shape[1]     #total number of channels
        self.allChannels = np.arange(0, self.nChTotal)  #array with all channels

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

        # Channels to show
        self.firstCh = int(self.parent.qline1.text())
        self.lastCh = int(self.parent.qline0.text())
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
                obj.session = ''
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
            c.setBrush(QtGui.QColor(255, 0, 0, 120))
            self.parent.win2.addItem(c)
            # on signals plot
            c = pg.QtGui.QGraphicsRectItem(start, -1, max(stop-start, 0.01), 2)
            self.IntRects2 = np.append(self.IntRects2, c)
            c.setPen(pg.mkPen(color = 'r'))
            c.setBrush(QtGui.QColor(255, 0, 0, 120))
            self.parent.win1.addItem(c)

        # Load stimuli signals (audio)
        self.load_stimuli()

        # Initiate plots
        self.updateCurXAxisPosition()
        self.refreshScreen()


    def load_stimuli(self):
        """Loads stimuli signals (speaker audio)."""
        self.nStim = len(self.nwb.stimulus)
        self.stimList = list(self.nwb.stimulus.keys())
        self.stimX = []
        self.stimY = {}
        self.parent.combo4.clear()
        for stim in self.stimList:
            self.parent.combo4.addItem(stim)   #add stimulus name to dropdown button
            dt_stim = 1./self.nwb.stimulus[stim].rate
            nb_stim = self.nwb.stimulus[stim].data.shape[0]
            self.stimX = np.linspace(dt_stim, nb_stim*dt_stim, nb_stim)
            self.stimY[stim] = self.nwb.stimulus[stim].data
        else:
            self.disp_audio = 0


    def refresh_file(self):
        """Re-opens the current file, for when new data is included"""
        self.io.close()   #closes current NWB file
        self.io = pynwb.NWBHDF5IO(self.fullpath, 'r+', load_namespaces=True)
        self.nwb = self.io.read()      #reads NWB file
        # Searches for signal source on file
        try:   #Tries to load Raw data
            lis = list(self.nwb.acquisition.keys())
            for i in lis:  # Check if there is ElectricalSeries in acquisition group
                if type(self.nwb.acquisition[i]).__name__ == 'ElectricalSeries':
                    self.source = self.nwb.acquisition[i]
                    self.parent.combo3.setCurrentIndex(self.parent.combo3.findText('raw'))
        except: None
        try:  #Tries to load preprocessed data
            self.source = self.nwb.processing['ecephys'].data_interfaces['LFP'].electrical_series['preprocessed']
            self.parent.combo3.setCurrentIndex(self.parent.combo3.findText('preprocessed'))
        except: None
        try:  #Tries to load High Gamma data
            self.source = self.nwb.processing['ecephys'].data_interfaces['high_gamma']
            self.parent.combo3.setCurrentIndex(self.parent.combo3.findText('high gamma'))
        except: None
        self.plotData = self.source.data
        self.fs_signal = self.source.rate     #sampling frequency [Hz]
        self.tbin_signal = 1/self.fs_signal #time bin duration [seconds]
        self.nBins = self.source.data.shape[0]     #total number of bins
        self.load_stimuli()  #load stimuli signals (audio)
        self.updateCurXAxisPosition()


    def refreshScreen(self):
        """Re-draws all plots"""
        self.TimeSeries_plotter()


    def TimeSeries_plotter(self):
        """Plots time series signals"""
        startSamp = self.intervalStartSamples
        endSamp = self.intervalEndSamples

        #Bins to plot - subsample for too big arrays
        maxBins = 1000
        ratio_to_max = (endSamp-startSamp)/maxBins
        if ratio_to_max > 1:
            bins_to_plot = np.linspace(startSamp, endSamp, maxBins, dtype='int')
        else:
            bins_to_plot = np.arange(startSamp, endSamp, dtype='int')

        # Use the same scaling factor for all channels, to keep things comparable
        self.verticalScaleFactor = float(self.parent.qline4.text())
        scaleFac = 2*np.std(self.plotData[startSamp:endSamp, self.selectedChannels-1], axis=0)/self.verticalScaleFactor

        # Scale variance_units, offset for each channel
        scale_va = np.max(scaleFac)
        self.scaleVec = np.arange(1, self.nChToShow + 1) * scale_va

        scaleV = np.zeros([len(self.scaleVec), 1])
        scaleV[:, 0] = self.scaleVec

        # constrains the plotData to the chosen interval (and transpose matix)
        # plotData dims=[self.nChToShow, plotInterval]
        data = self.plotData[startSamp:endSamp, self.selectedChannels-1].T
        data = data[:,bins_to_plot-startSamp-1]
        means = np.reshape(np.mean(data, 1),(-1,1))  #to align each trace around its reference trace
        plotData = data + scaleV - means  # data + offset

        # Middle signals plot
        # A line indicating reference for every channel
        timebaseGuiUnits = bins_to_plot*self.tbin_signal
        #timebaseGuiUnits = np.arange(startSamp, endSamp)*self.tbin_signal
        plt2 = self.parent.win1  #middle signal plot
        plt2.clear()
        #Channels reference lines
        for l in range(len(self.scaleVec)):
            plt2.plot([timebaseGuiUnits[0], timebaseGuiUnits[-1]],
                      [self.scaleVec[l], self.scaleVec[l]],
                      pen='k')

        # Iterate over chosen channels, plot one at a time
        nrows, ncols = np.shape(plotData)
        for i in range(nrows):
            if self.selectedChannels[i] in self.badChannels:
                plt2.plot(timebaseGuiUnits, plotData[i], pen=pg.mkPen((220,0,0), width=1.2))
            else:
                c = pg.mkPen((0,120,0), width=1.2)
                if i%2 == 0:
                    c = pg.mkPen((0,0,200), width=1.2)
                plt2.plot(timebaseGuiUnits, plotData[i], pen=c)
        plt2.setLabel('bottom', 'Time', units = 'sec')
        plt2.setLabel('left', 'Channel #')
        labels = [str(ch+1) for ch in self.selectedChannels]
        ticks = list(zip(self.scaleVec, labels))
        plt2.getAxis('left').setTicks([ticks])
        plt2.setXRange(timebaseGuiUnits[0], timebaseGuiUnits[-1], padding = 0.003)
        plt2.setYRange(self.scaleVec[0], self.scaleVec[-1], padding = 0.06)
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
            aux = self.AnnotationsList[i].pg_item
            x = self.AnnotationsPosAV[i,0]
            # Y to plot = (Y_va + Channel offset)*scale_variance
            y_va = self.AnnotationsPosAV[i,1]
            y = (y_va + self.AnnotationsPosAV[i,2] - self.firstCh) * scale_va
            aux.setPos(x,y)
            plt2.addItem(aux)

        # Upper horizontal bar
        plt1 = self.parent.win2
        plt1.clear()
        max_dur = self.nBins * self.tbin_signal
        plt1.plot([0, max_dur], [0, 0], pen=pg.mkPen('k', width=2))
        plt1.setXRange(0, max_dur)
        plt1.setYRange(-1, 1)

        if self.current_rect != []:
            plt1.removeItem(self.current_rect)

        ## Rectangle Plot
        x = float(self.parent.qline2.text())
        w = float(self.parent.qline3.text())
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

        # Bottom plot - Stimuli
        plt3 = self.parent.win3
        plt3.clear()
        if self.parent.combo4.currentText() is not '':
            try:
                xmask = (self.stimX > timebaseGuiUnits[0]) * (self.stimX < timebaseGuiUnits[-1])
                stimName = self.parent.combo4.currentText()
                stimData = self.stimY[stimName]
                plt3.plot(self.stimX[xmask], stimData[xmask], pen='k', width=1)
                plt3.setXLink(plt2)
            except:  #THIS IS MOMENTARY TO PLOT ARTIFICIAL DATA-- REMOVE LATER
                stimName = self.parent.combo4.currentText()
                stimData = self.stimY[stimName]
                plt3.plot(stimData, pen='k', width=1)
                # remove this later -------------------------------------------

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
        """Updates upper visualization window position when dragged by the user."""
        self.parent.qline2.setText(str(self.intervalStartGuiUnits + dt))
        self.updateCurXAxisPosition()


    def updateCurXAxisPosition(self):
        """Updates the time interval selected from the user forms,
           with checks for allowed values"""
        # Read from user forms
        self.intervalStartGuiUnits = float(self.parent.qline2.text())
        self.intervalLengthGuiUnits = float(self.parent.qline3.text())

        max_dur = self.nBins * self.tbin_signal  # Max duration in seconds
        min_len = 500*self.tbin_signal          # Min accepted length

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
        self.parent.qline2.setText(str(self.intervalStartGuiUnits))
        self.parent.qline3.setText(str(self.intervalLengthGuiUnits))

        # Updates times in samples
        self.intervalLengthSamples = int(np.floor(self.intervalLengthGuiUnits / self.tbin_signal))
        self.intervalStartSamples = max(np.floor(self.intervalStartGuiUnits / self.tbin_signal),0)
        self.intervalStartSamples = int(min(self.intervalStartSamples, self.nBins-501))
        self.intervalEndSamples = self.intervalStartSamples + self.intervalLengthSamples

        self.refreshScreen()


    def time_window_resize(self, wscale):
        """Updates the plotting time interval range"""
        self.intervalLengthGuiUnits = float(self.parent.qline3.text())
        self.intervalLengthGuiUnits = self.intervalLengthGuiUnits * wscale
        self.parent.qline3.setText(str(self.intervalLengthGuiUnits))
        self.updateCurXAxisPosition()


    def time_scroll(self, scroll=0):
        """Updates the plotting time interval for scrolling.
           Buttons: >>, >, <<, <"""
        #new interval start
        self.intervalStartSamples = self.intervalStartSamples \
                                    + int(scroll * self.intervalLengthSamples)
        #if the last sample of the new interval is beyond is the available data
        # set start such that intserval is in a valid range
        if self.intervalStartSamples + self.intervalLengthSamples > self.nBins:
            self.intervalStartSamples = self.nBins - self.intervalLengthSamples
        elif self.intervalStartSamples < 0:
            self.intervalStartSamples = 0

        #new interval end
        self.intervalEndSamples = self.intervalStartSamples + self.intervalLengthSamples
        # Updates start time in seconds (first avoid <0.001 values)
        self.intervalStartGuiUnits = max(self.intervalStartSamples*self.tbin_signal,0.001)
        # Round to miliseconds for display
        self.intervalStartGuiUnits = np.round(self.intervalStartGuiUnits,3)
        self.intervalEndGuiUnits = self.intervalEndSamples*self.tbin_signal
        self.parent.qline2.setText(str(self.intervalStartGuiUnits))
        self.refreshScreen()


    def channel_Scroll_Up(self, opt='unit'):
        """Updates the channels to be plotted. Buttons: ^, ^^ """
        # Test upper limit
        if self.lastCh < self.nChTotal:
            if opt=='unit':
                step = 1
            elif opt=='page':
                step = np.minimum(self.nChToShow, self.nChTotal-self.lastCh)
            # Add +1 to first and last channels
            self.firstCh += step
            self.lastCh += step
            self.parent.qline0.setText(str(self.lastCh))
            self.parent.qline1.setText(str(self.firstCh))
            self.nChToShow = self.lastCh - self.firstCh + 1
            self.selectedChannels = self.channels_mask_ind[self.firstCh-1:self.lastCh]
        self.refreshScreen()


    def channel_Scroll_Down(self, opt='unit'):
        """Updates the channels to be plotted. Buttons: v, vv """
        # Test lower limit
        if self.firstCh > 1:
            if opt=='unit':
                step = 1
            elif opt=='page':
                step = np.minimum(self.nChToShow, self.firstCh-1)
            # Subtract from first and last channels
            self.firstCh -= step
            self.lastCh -= step
            self.parent.qline0.setText(str(self.lastCh))
            self.parent.qline1.setText(str(self.firstCh))
            self.nChToShow = self.lastCh - self.firstCh + 1
            self.selectedChannels = self.channels_mask_ind[self.firstCh-1:self.lastCh]
        self.refreshScreen()


    def nChannels_Displayed(self):
        """Updates channels to be plotted."""
        self.firstCh = int(self.parent.qline1.text())
        self.lastCh = int(self.parent.qline0.text())

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
        self.parent.qline0.setText(str(self.lastCh))
        self.parent.qline1.setText(str(self.firstCh))
        self.refreshScreen()


    ## Annotation functions ----------------------------------------------------
    def AnnotationAdd(self, x, y, color='yellow', text=''):
        """
        Adds new annotation to plot scene.

        Parameters
        ----------
        x : float
            x position
        y : float
            y position
        color :
            'yellow', 'red', 'green' or 'blue'
        text : str
            Annotation text
        """
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
        y_va = np.round(y/self.scaleVec[0]).astype('int')
        c.setPos(x,y_va)
        # create annotation object and add it to the list
        obj = CustomAnnotation()
        obj.pg_item = c
        obj.x = x
        obj.y_va = y_va
        obj.y_off = self.firstCh
        obj.color = color
        obj.text = text
        obj.session = self.parent.current_session
        self.AnnotationsList = np.append(self.AnnotationsList,obj)
        # List of positions (to calculate distances)
        if len(self.AnnotationsPosAV) > 0:
            self.AnnotationsPosAV = np.concatenate((self.AnnotationsPosAV,
                                                    np.array([x, y_va, self.firstCh]).reshape(1,3)))
        else:
            self.AnnotationsPosAV = np.array([x, y_va, self.firstCh]).reshape(1,3)
        self.refreshScreen()
        self.unsaved_changes_annotation = True


    def AnnotationDel(self, x, y):
        """
        Deletes from plot scene the annotation closest to the passed position.

        Parameters
        ----------
        x : float
            x position
        y : float
            y position
        """
        x_ann = self.AnnotationsPosAV[:,0]
        y_ann = np.round((self.AnnotationsPosAV[:,1] + self.AnnotationsPosAV[:,2] - self.firstCh)*self.scaleVec[0])
        # Calculates euclidian distance from click
        euclid_dist = np.sqrt( (x_ann-x)**2 + (y_ann-y)**2 )
        indmin = np.argmin(euclid_dist)
        # Checks if user intends to delete annotation
        text = self.AnnotationsList[indmin].text
        buttonReply = QMessageBox.question(None,
                                           'Delete Annotation', "Delete the annotation: \n\n"+text+' ?',
                                           QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
        if buttonReply == QMessageBox.Yes:
            self.AnnotationsList = np.delete(self.AnnotationsList, indmin, axis=0)
            self.AnnotationsPosAV = np.delete(self.AnnotationsPosAV, indmin, axis=0)
            self.refreshScreen()
            self.unsaved_changes_annotation = True


    def AnnotationSave(self):
        """Saves annotations in an external CSV file."""
        buttonReply = QMessageBox.question(None, ' ', 'Save annotations on external file?',
                                           QMessageBox.No | QMessageBox.Yes)
        if buttonReply == QMessageBox.Yes:
            c0 = self.AnnotationsPosAV[:,0]     # x
            c1 = self.AnnotationsPosAV[:,1]     # y_va
            c2 = self.AnnotationsPosAV[:,2]     # y_off
            c3 = [self.AnnotationsList[i].color for i in range(len(self.AnnotationsList))]
            c4 = [self.AnnotationsList[i].text for i in range(len(self.AnnotationsList))]
            c5 = [self.AnnotationsList[i].session for i in range(len(self.AnnotationsList))]
            d = {'x':c0, 'y_va':c1, 'y_off':c2, 'color':c3, 'text':c4, 'session':c5}
            df = pd.DataFrame(data=d)
            fullfile = os.path.join(self.pathName, self.fileName[:-4] + '_annotations_' +
                                    datetime.datetime.today().strftime('%Y-%m-%d')+
                                    '.csv')
            df.to_csv(fullfile, header=True, index=True)
            self.unsaved_changes_annotation = False


    def AnnotationLoad(self, fname=''):
        """Loads annotations from an external CSV file."""
        df = pd.read_csv(fname)
        all_x = df['x'].values
        all_y_va = df['y_va'].values
        all_y_off = df['y_off'].values
        texts = df['text'].tolist()
        colors = df['color'].tolist()
        session = df['session'].tolist()
        for i, txt in enumerate(texts):    # Add loaded annotations to graph
            if colors[i]=='yellow':
                bgcolor = pg.mkBrush(250, 250, 150, 200)
            elif colors[i]=='red':
                bgcolor = pg.mkBrush(250, 0, 0, 200)
            elif colors[i]=='green':
                bgcolor = pg.mkBrush(0, 255, 0, 200)
            elif colors[i]=='blue':
                bgcolor = pg.mkBrush(0, 0, 255, 200)
            c = pg.TextItem(anchor=(.5,.5), border=pg.mkPen(100, 100, 100), fill=bgcolor)
            c.setText(text=txt, color=(0,0,0))
            # Y coordinate transformed to variance_units (for plot control)
            y_va = all_y_va[i]
            x = all_x[i]
            c.setPos(x,y_va)
            obj = CustomAnnotation()
            obj.pg_item = c
            obj.x = all_x[i]
            obj.y_va = all_y_va[i]
            obj.y_off = all_y_off[i]
            obj.color = colors[i]
            obj.text = txt
            obj.session = session[i]
            self.AnnotationsList.append(obj)
            if len(self.AnnotationsPosAV) > 0:
                self.AnnotationsPosAV = np.concatenate((self.AnnotationsPosAV,
                                                        np.array([x, y_va, all_y_off[i]]).reshape(1,3)))
            else:
                self.AnnotationsPosAV = np.array([x, y_va, all_y_off[i]]).reshape(1,3)
        self.refreshScreen()


    ## Interval functions ------------------------------------------------------
    def IntervalAdd(self, interval, int_type, color, session):
        """
        Adds new interval to plot scene.

        Parameters
        ----------
        interval : list of floats
            List with [x_initial, x_final] points.
        int_type : str
            Type of the interval (e.g. 'invalid').
        color :
            'yellow', 'red', 'green' or 'blue'.
        session : str
            Session name.
        """
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
        c = pg.QtGui.QGraphicsRectItem(x, -1, w, 2)
        c.setPen(pg.mkPen(color=QtGui.QColor(bc[0], bc[1], bc[2], 255)))
        c.setBrush(QtGui.QColor(bc[0], bc[1], bc[2], bc[3]))
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
        obj.session = session
        self.allIntervals.append(obj)
        self.nBI = len(self.allIntervals)
        self.unsaved_changes_interval = True


    def IntervalDel(self, x):
        """
        Deletes from plot scene the interval passing by the x position.

        Parameters
        ----------
        x : float
            x position.
        """
        for i, obj in enumerate(self.allIntervals):
            if (x >= obj.start) & (x <= obj.stop):   #interval of the click
                self.parent.win2.removeItem(self.IntRects1[i])
                self.IntRects1 = np.delete(self.IntRects1, i, axis = 0)
                self.parent.win1.removeItem(self.IntRects2[i])
                self.IntRects2 = np.delete(self.IntRects2, i, axis = 0)
                del self.allIntervals[i]
                self.nBI = len(self.allIntervals)
                self.refreshScreen()
                self.unsaved_changes_interval = True


    def IntervalSave(self):
        """Saves intervals in an external CSV file."""
        buttonReply = QMessageBox.question(None, ' ', 'Save intervals on external file?',
                                           QMessageBox.No | QMessageBox.Yes)
        if buttonReply == QMessageBox.Yes:
            c0, c1, c2, c3, c4 = [], [], [], [], []
            for i, obj in enumerate(self.allIntervals):
                c0.append(obj.start)     # start
                c1.append(obj.stop)      # stop
                c2.append(obj.type)      # type
                c3.append(obj.color)     # color
                c4.append(obj.session)   # session
            d = {'start':c0, 'stop':c1, 'type':c2, 'color':c3, 'session':c4}
            df = pd.DataFrame(data=d)
            fullfile = os.path.join(self.pathName, self.fileName[:-4] + '_intervals_' +
                                    datetime.datetime.today().strftime('%Y-%m-%d')+
                                    '.csv')
            df.to_csv(fullfile, header=True, index=True)
            self.unsaved_changes_interval = False


    def IntervalLoad(self, fname):
        """Loads intervals from an external CSV file."""
        df = pd.read_csv(fname)
        for index, row in df.iterrows():    # Add loaded intervals to graph
            interval = [row.start, row.stop]
            int_type = row.type
            color = row.color
            session = row.session
            self.IntervalAdd(interval, int_type, color, session)
            #Update dictionary of interval types
            # TO-DO
        self.refreshScreen()


    # Channels functions -------------------------------------------------------
    def BadChannelAdd(self, ch_list):
        """
        Marks specific channels as 'bad'.

        Parameters
        ----------
        ch_list : list of integers
            List of indices of channels to be marked as 'bad'.
        """
        for ch in ch_list:
            if ch not in self.badChannels:
                self.badChannels.append(ch)
        self.refreshScreen()


    def BadChannelDel(self, ch_list):
        """
        Un-marks specific channels as 'bad'.

        Parameters
        ----------
        ch_list : list of integers
            List of indices of channels to be un-marked as 'bad'.
        """
        for ch in ch_list:
            if ch in self.badChannels:
                self.badChannels.remove(ch)
        self.refreshScreen()


    def BadChannelSave(self):
        """Saves list of bad channels in current NWB file."""
        buttonReply = QMessageBox.question(None, ' ', 'Save Bad Channels on current NWB file?',
                                           QMessageBox.No | QMessageBox.Yes)
        if buttonReply == QMessageBox.Yes:
            # Modify current list of bad channels
            aux = [False]*self.nChTotal
            for ind in self.badChannels:
                aux[ind] = True
            self.nwb.electrodes['bad'].data[:] = aux


    def DrawMarkTime(self, position):
        """Marks temporary reference line when adding a new interval."""
        plt = self.parent.win1     #middle signal plot
        self.current_mark = pg.QtGui.QGraphicsRectItem(position, 0, 0, 1)
        self.current_mark.setPen(pg.mkPen(color = 'k'))
        self.current_mark.setBrush(QtGui.QColor(150, 150, 150, 100))
        plt.addItem(self.current_mark)


    def RemoveMarkTime(self):
        """Removes temporary reference line when adding a new interval."""
        plt = self.parent.win1     #middle signal plot
        plt.removeItem(self.current_mark)



class CustomInterval:
    """
    Stores information about individual Intervals.

    Parameters
    ----------
    start : float
        Start time position.
    stop : float
        Stop time position.
    type : str
        Interval type (e.g. 'invalid').
    color : str
        Interval color: 'yellow', 'red', 'green' or 'blue'.
    session: str
        Session name.
    """
    def __init__(self):
        self.start = -999
        self.stop = -999
        self.type = ''
        self.color = ''
        self.session = ''


class CustomAnnotation:
    """
    Stores information about individual Annotations.

    Parameters
    ----------
    pg_item :
        pyqtgraph TextItem object.
    x : float
        X position (time).
    y_va : int
        Y coordinate transformed to variance_units (for plot control).
    y_off : int
        Y offset, usually the bottom channel on plot when annotation is saved.
    color : str
        Interval color: 'yellow', 'red', 'green' or 'blue'.
    text : str
        Annotation text.
    session: str
        Session name.
    """
    def __init__(self):
        self.pg_item = None
        self.x = 0
        self.y_va = 0
        self.y_off = 0
        self.color = ''
        self.text = ''
        self.session = ''


class CustomBox(pg.QtGui.QGraphicsRectItem):
    """Upper visualization window rectangle that can be dragged by the user."""
    def __init__(self, parent, x, y, w, h):
        pg.QtGui.QGraphicsRectItem.__init__(self, x, y, w, h)
        self.parent = parent
    def mouseReleaseEvent(self, event):
        dt = self.x()
        self.parent.drag_window(dt)
