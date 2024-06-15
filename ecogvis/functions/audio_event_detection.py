from PyQt5 import QtGui, QtCore, QtWidgets
from PyQt5.QtWidgets import (QGridLayout, QGroupBox, QLineEdit, QLabel, QComboBox,
                             QPushButton, QVBoxLayout, QHBoxLayout)
import pyqtgraph as pg
from ecogvis.signal_processing.detect_events import detect_events

from pynwb import NWBHDF5IO
from pynwb.epoch import TimeIntervals
import numpy as np


# Creates Audio Event Detection window -----------------------------------------
class AudioEventDetection(QtWidgets.QDialog):
    def __init__(self, parent):
        super().__init__()
        self.parent = parent
        self.value = -1

        # Plotting default values
        self.speaker_offset = 3.3
        self.mic_offset = 1
        self.ylim = [-0.1, 4.3]
        self.blue = (40, 116, 166)
        self.blue_light = (40, 116, 166, 80)
        self.red = (176, 58, 46)
        self.red_light = (176, 58, 46, 80)
        self.gray = (33, 47, 61)

        # Left panel - Plot Preview ------------------------------------------
        labelSpeaker = QLabel('Speaker:')
        self.combo0 = QComboBox()
        self.combo0.activated.connect(self.reset_draw)
        labelMic = QLabel('Mic:')
        self.combo1 = QComboBox()
        self.combo1.activated.connect(self.reset_draw)
        labelStart = QLabel('Interval Start (s):')
        self.qline1 = QLineEdit('0')
        self.qline1.returnPressed.connect(self.draw_scene)
        labelStop = QLabel('Plot window (s):')
        self.qline2 = QLineEdit('20')
        self.qline2.returnPressed.connect(self.draw_scene)

        self.push0_0 = QPushButton('<<')
        self.push0_0.clicked.connect(self.page_backward)
        self.push0_1 = QPushButton('refresh')
        self.push0_1.clicked.connect(self.draw_scene)
        self.push0_2 = QPushButton('>>')
        self.push0_2.clicked.connect(self.page_forward)

        grid0 = QGridLayout()
        grid0.addWidget(labelSpeaker, 1, 0, 1, 3)
        grid0.addWidget(self.combo0, 1, 3, 1, 4)
        grid0.addWidget(labelMic, 2, 0, 1, 3)
        grid0.addWidget(self.combo1, 2, 3, 1, 4)
        grid0.addWidget(labelStart, 3, 0, 1, 5)
        grid0.addWidget(self.qline1, 3, 5, 1, 2)
        grid0.addWidget(labelStop, 4, 0, 1, 5)
        grid0.addWidget(self.qline2, 4, 5, 1, 2)
        grid0.addWidget(self.push0_0, 5, 0, 1, 2)
        grid0.addWidget(self.push0_1, 5, 2, 1, 3)
        grid0.addWidget(self.push0_2, 5, 5, 1, 2)
        grid0.setAlignment(QtCore.Qt.AlignTop)
        panel0 = QGroupBox('Plot')
        panel0.setFixedWidth(200)
        panel0.setLayout(grid0)

        # Left panel - Detection Settings -----------------------------------
        labelDetectStart = QLabel('Start (s):')
        self.qline7 = QLineEdit('0')
        labelDetectStop = QLabel('Stop (s):')
        self.qline8 = QLineEdit('end')

        labelDown = QLabel('Downsample\nFactor:')
        self.qline3 = QLineEdit('800')
        labelDown.setToolTip('Downsample rate of raw signal.\n'
                             'Typical values: 500~900 Hz')
        labelWidth = QLabel('Smoothing Filter\nWidth:')
        self.qline4 = QLineEdit('0.4')
        labelWidth.setToolTip('This will affect the width of \n'
                              'the smoothing filter (seconds).\n'
                              'Typical values: .1 ~ 1')
        labelSpeakerThresh = QLabel('Speaker Threshold:')
        self.qline5 = QLineEdit('0.05')
        labelSpeakerThresh.setToolTip(
            'Threshold on the smoothed signal (standard deviations from the '
            'mean).\n'
            'Typical values: .02 ~ .1')
        labelMicThresh = QLabel('Mic Threshold:')
        self.qline6 = QLineEdit('0.1')
        labelMicThresh.setToolTip(
            'Threshold on the smoothed signal (standard deviations from the '
            'mean).\n'
            'Typical values: .05 ~ .5')

        labelRunTest = QLabel('Preview detection with\nthese settings.')
        self.push1_0 = QPushButton('Run Test')
        self.push1_0.clicked.connect(self.run_test)

        grid1 = QGridLayout()
        grid1.addWidget(labelDetectStart, 0, 0, 1, 3)
        grid1.addWidget(self.qline7, 0, 3, 1, 3)
        grid1.addWidget(labelDetectStop, 1, 0, 1, 3)
        grid1.addWidget(self.qline8, 1, 3, 1, 3)
        grid1.addWidget(labelDown, 2, 0, 1, 4)
        grid1.addWidget(self.qline3, 2, 4, 1, 2)
        grid1.addWidget(labelWidth, 3, 0, 1, 4)
        grid1.addWidget(self.qline4, 3, 4, 1, 2)
        grid1.addWidget(labelSpeakerThresh, 4, 0, 1, 4)
        grid1.addWidget(self.qline5, 4, 4, 1, 2)
        grid1.addWidget(labelMicThresh, 5, 0, 1, 4)
        grid1.addWidget(self.qline6, 5, 4, 1, 2)
        grid1.addWidget(labelRunTest, 6, 0, 1, 6)
        grid1.addWidget(self.push1_0, 7, 0, 1, 6)

        grid1.setAlignment(QtCore.Qt.AlignTop)
        panel1 = QGroupBox('Detection - Settings')
        panel1.setFixedWidth(200)
        panel1.setLayout(grid1)

        # Left panel - Detection Full --------------------------------------

        labelRunDetection = QLabel('Run and save detection\nwith these '
                                   'settings.')
        self.push2_0 = QPushButton('Run Detection')
        self.push2_0.clicked.connect(self.run_detection)

        grid2 = QGridLayout()
        grid2.addWidget(labelRunDetection, 0, 0, 1, 6)
        grid2.addWidget(self.push2_0, 1, 0, 1, 6)

        grid2.setAlignment(QtCore.Qt.AlignTop)
        panel2 = QGroupBox('Detection - Run')
        panel2.setFixedWidth(200)
        panel2.setLayout(grid2)

        self.leftbox = QVBoxLayout()
        self.leftbox.addWidget(panel0)
        self.leftbox.addWidget(panel1)
        self.leftbox.addWidget(panel2)
        self.leftbox.addStretch()

        # Right panel --------------------------------------------------------
        self.win = pg.PlotWidget()
        self.win.resize(1000, 300)
        background_color = self.palette().color(QtGui.QPalette.Background)
        self.win.setBackground(background_color)

        self.rightbox = QVBoxLayout()
        self.plotTitle = QLabel('Preview detection results:')
        self.rightbox.addWidget(self.plotTitle)
        self.rightbox.addWidget(self.win)

        self.hbox = QHBoxLayout()
        self.hbox.addLayout(self.leftbox)  # add panels in the left
        self.hbox.addLayout(self.rightbox)  # add plot on the right

        self.setLayout(self.hbox)
        self.setWindowTitle('Audio Event Detection')
        self.resize(1100, 300)
        self.find_signals()
        self.reset_draw()
        self.set_detect_interval()
        self.exec_()

    def find_signals(self):
        # Find speaker signals
        self.stimuli = {}  # Dictionary {'stimName':stim.source}
        for stim in list(self.parent.model.nwb.stimulus.keys()):
            self.combo0.addItem(stim)
            self.stimuli[stim] = self.parent.model.nwb.stimulus[stim]
        self.combo0.setCurrentIndex(0)
        # Find microphone signals
        self.responses = {}  # Dictionary {'respName':resp.source}
        for resp in list(self.parent.model.nwb.acquisition.keys()):
            # if type(self.parent.model.nwb.acquisition[resp]).__name__ == 'TimeSeries':
            if resp in ['microphone', 'anin4']:
                self.combo1.addItem(resp)
                self.responses[resp] = self.parent.model.nwb.acquisition[resp]
        self.combo1.setCurrentIndex(0)

    def reset_draw(self):
        """Reset draw."""
        # Stimuli variables
        stim = self.combo0.currentText()
        self.source_stim = self.stimuli[stim]
        self.signal_stim = self.source_stim.data
        self.stimTimes = []  # clears any previous stim times
        self.signal_stim_filt = None  # clears any previous smoothed speaker

        # Response variables
        resp = self.combo1.currentText()
        self.source_resp = None
        self.signal_resp = None
        self.signal_resp_filt = None
        self.respTimes = []  # clears any previous resp times
        if resp in self.responses:
            self.source_resp = self.responses[resp]
            self.signal_resp = self.source_resp.data

        # Common to both stim and resp
        self.fs = self.source_stim.rate
        self.nTotalBins = self.signal_stim.shape[0]
        self.timeaxis = np.arange(self.nTotalBins) / self.fs
        self.maxTime = self.timeaxis[-1]
        self.draw_scene()

    def set_plot_interval(self):
        """Sets new interval."""
        # Control for invalid values and ranges
        interval = float(self.qline2.text())
        self.startTime = np.clip(float(self.qline1.text()), 0,
                                 np.max([self.maxTime - interval,0]))
        self.stopTime = np.clip(self.startTime + interval, 1.1,
                                self.maxTime)
        if (self.stopTime - self.startTime) < 1:
            self.stopTime = self.startTime + 1
        self.qline1.setText(str(np.round(self.startTime, 1)))
        self.qline2.setText(str(np.round(self.stopTime-self.startTime, 1)))

    def page_forward(self):
        start = float(self.qline1.text())
        interval = float(self.qline2.text())
        self.qline1.setText(str(start + interval))
        self.set_plot_interval()
        self.draw_scene()

    def page_backward(self):
        start = float(self.qline1.text())
        interval = float(self.qline2.text())
        self.qline1.setText(str(start - interval))
        self.set_plot_interval()
        self.draw_scene()

    def set_detect_interval(self):
        """Sets new detect interval"""
        # Control for invalid values and ranges
        if self.qline8.text() == 'end':
            self.qline8.setText(str(np.round(self.maxTime, 1)))
        self.detectStartTime = np.clip(float(self.qline7.text()), 0,
                                       self.maxTime - 1.1)
        self.detectStopTime = np.clip(float(self.qline8.text()), 1.1,
                                      self.maxTime)
        if (self.detectStopTime - self.detectStartTime) < 1:
            self.detectStopTime = self.detectStartTime + 1
        self.qline7.setText(str(np.round(self.detectStartTime, 1)))
        self.qline8.setText(str(np.round(self.detectStopTime, 1)))

        # Calculate correspondent bins
        self.detectStartBin = int(self.detectStartTime * self.fs)
        self.detectStopBin = int(self.detectStopTime * self.fs)

    def draw_scene(self):
        """Draws signal and detection points."""
        self.set_plot_interval()
        self.win.clear()
        # self.win.addLegend()

        # Plot stimuli
        plotBins = np.logical_and(self.timeaxis >= self.startTime, self.timeaxis <= self.stopTime)
        x = self.timeaxis[plotBins]
        y0 = self.signal_stim[plotBins].astype(float)
        y0 /= np.max(np.abs(y0))
        self.win.plot(x, y0 + self.speaker_offset,
                      pen=pg.mkPen(self.blue_light, width=1.),
                      name='Speaker')

        # Plot responses
        if self.signal_resp is not None:
            y1 = self.signal_resp[plotBins].astype(float)
            y1 /= np.max(np.abs(y1))
            self.win.plot(x, y1 + self.mic_offset, pen=pg.mkPen(self.red_light, width=1.), name='Mic')

        if self.signal_stim_filt is not None:
            plotBinsFilt = np.logical_and(self.timeaxis_filt >= self.startTime,
                                          self.timeaxis_filt <= self.stopTime)
            x_filt = self.timeaxis_filt[plotBinsFilt]

            # Plot filtered stimulus and threshold
            y0 = [self.signal_stim_filt[plotBinsFilt],
                  np.ones(np.sum(plotBinsFilt)) * self.speakerThresh]
            y0_names = ['SpeakerFilt', 'SpeakerThresh']
            y0_kargs = [
                {'color': self.gray, 'width': 2.},
                {'color': self.blue, 'width': 1.5, 'style': QtCore.Qt.DashLine}
            ]
            for name, kargs, column in zip(y0_names, y0_kargs, y0):
                self.win.plot(x_filt, column + self.speaker_offset,
                              pen=pg.mkPen(**kargs), name=name)

            for st in self.stimTimes:
                if st > self.startTime and st <= self.stopTime:
                    self.win.plot([st, st], self.ylim,
                                  pen=pg.mkPen(self.blue, width=2.))

        if self.signal_resp_filt is not None:
            # Plot filtered response and threshold
            if self.signal_resp_filt is not None:
                y1 = [self.signal_resp_filt[plotBinsFilt], np.ones(np.sum(plotBinsFilt)) * self.micThresh]
                y1_names = ['MicFilt', 'MicThresh']
                y1_kargs = [
                    {'color': self.gray, 'width': 2.},
                    {'color': self.red, 'width': 1.5, 'style': QtCore.Qt.DashLine}
                ]
                for name, kargs, column in zip(y1_names, y1_kargs, y1):
                    self.win.plot(x_filt, column + self.mic_offset,
                                  pen=pg.mkPen(**kargs), name=name)

            for rt in self.respTimes:
                if rt > self.startTime and rt <= self.stopTime:
                    self.win.plot([rt, rt], self.ylim, pen=pg.mkPen(self.red, width=2.))

        # Axes parameters
        self.win.setXRange(self.startTime, self.stopTime)
        self.win.setYRange(self.ylim[0], self.ylim[1])
        self.win.getAxis('left').setStyle(showValues=False)
        self.win.getAxis('left').setTicks([])
        self.win.getAxis('left').setPen(pg.mkPen(color=(50, 50, 50)))
        self.win.setLabel('bottom', 'Time', units='sec')
        self.win.getAxis('bottom').setPen(pg.mkPen(color=(50, 50, 50)))

    def run_test(self):

        # Assign the threshold values.
        self.speakerThresh = float(self.qline5.text())
        self.micThresh = float(self.qline6.text())

        # Use the full signal based on the interval specified (different
        # from the interval plotted.
        self.set_detect_interval()

        speakerDS, speakerEventDS, speakerFilt, micDS, micEventDS, micFilt = detect_events(
            speaker_data=self.source_stim,
            mic_data=self.source_resp,
            interval=[self.detectStartBin, self.detectStopBin + 1],
            dfact=self.fs / float(self.qline3.text()),
            smooth_width=float(self.qline4.text()),
            speaker_threshold=self.speakerThresh,
            mic_threshold=self.micThresh
        )

        self.stimTimes = speakerEventDS
        self.respTimes = micEventDS
        self.timeaxis_filt = self.detectStartTime + np.arange(len(speakerDS)) / float(
            self.qline3.text())
        self.signal_stim_filt = speakerFilt
        self.signal_resp_filt = micFilt

        self.draw_scene()

    def run_detection(self):
        self.set_detect_interval()
        self.disable_all()
        self.plotTitle.setText(
            f'Running event detection {self.detectStartTime}-'
            f'{self.detectStopTime}s. Please wait...')
        self.thread = EventDetectionFunction(
            speaker_data=self.source_stim,
            mic_data=self.source_resp,
            interval=[self.detectStartBin, self.detectStopBin + 1],
            dfact=self.fs / float(self.qline3.text()),
            smooth_width=float(self.qline4.text()),
            speaker_threshold=float(self.qline5.text()),
            mic_threshold=float(self.qline6.text())
        )
        self.thread.finished.connect(lambda: self.out_close(1))
        self.thread.start()

    def disable_all(self):
        self.win.clear()
        self.push0_0.setEnabled(False)
        self.push0_1.setEnabled(False)
        self.push0_2.setEnabled(False)
        self.combo0.setEnabled(False)
        self.combo1.setEnabled(False)
        self.qline1.setEnabled(False)
        self.qline2.setEnabled(False)
        self.qline3.setEnabled(False)
        self.qline4.setEnabled(False)
        self.qline5.setEnabled(False)
        self.qline6.setEnabled(False)
        self.qline7.setEnabled(False)
        self.qline8.setEnabled(False)
        self.push1_0.setEnabled(False)
        self.push2_0.setEnabled(False)

    def out_close(self, val):
        self.value = val
        if val == 1:  # finished auto-detection of events
            self.stimTimes = self.thread.stimTimes
            self.respTimes = self.thread.respTimes

            # Speaker stimuli times
            ti_stim = TimeIntervals(name='TimeIntervals_speaker')
            times = self.stimTimes.reshape((-1, 2)).astype('float')
            for start, stop in times:
                ti_stim.add_interval(start, stop)
            self.parent.model.nwb.add_time_intervals(ti_stim)

            # Microphone responses times
            if self.respTimes is not None:
                ti_resp = TimeIntervals(name='TimeIntervals_mic')
                times = self.respTimes.reshape((-1, 2)).astype('float')
                for start, stop in times:
                    ti_resp.add_interval(start, stop)
                self.parent.model.nwb.add_time_intervals(ti_resp)

            # Write file
            self.parent.model.io.write(self.parent.model.nwb)

            self.parent.model.refresh_file()
            self.parent.model.SpeakerAndMicIntervalAdd()
            self.parent.model.refreshScreen()
        self.accept()


# Runs 'detect_events' function, useful to wait for thread ---------------------
class EventDetectionFunction(QtCore.QThread):
    def __init__(self, speaker_data, mic_data, interval, dfact,
                 smooth_width,
                 speaker_threshold, mic_threshold):
        super().__init__()
        self.source_stim = speaker_data
        self.source_resp = mic_data
        self.interval = interval
        self.dfact = dfact
        self.smooth_width = smooth_width
        self.stim_threshold = speaker_threshold
        self.resp_threshold = mic_threshold

    def run(self):
        speakerDS, speakerEventDS, _, micDS, micEventDS, _ = detect_events(
            speaker_data=self.source_stim,
            mic_data=self.source_resp,
            interval=self.interval,
            dfact=self.dfact,
            smooth_width=self.smooth_width,
            speaker_threshold=self.stim_threshold,
            mic_threshold=self.resp_threshold,
            direction='both'
        )
        self.stimTimes = speakerEventDS
        self.respTimes = micEventDS
