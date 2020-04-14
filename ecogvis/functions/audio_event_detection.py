from PyQt5 import QtGui, QtCore
from PyQt5.QtWidgets import (QGridLayout, QGroupBox, QLineEdit, QLabel, QComboBox,
                             QPushButton, QVBoxLayout, QHBoxLayout)
import pyqtgraph as pg
from ecogvis.signal_processing.detect_events import detect_events

from pynwb import NWBHDF5IO
from pynwb.epoch import TimeIntervals
import numpy as np


# Creates Audio Event Detection window -----------------------------------------
class AudioEventDetection(QtGui.QDialog):
    def __init__(self, parent):
        super().__init__()
        self.parent = parent
        self.value = -1

        # Left panel - Plot Preview ---------------------------------------------
        self.push0_0 = QPushButton('Draw')
        self.push0_0.clicked.connect(self.reset_draw)
        labelSpeaker = QLabel('Speaker:')
        self.combo0 = QComboBox()
        self.combo0.activated.connect(self.reset_draw)
        labelMic = QLabel('Mic:')
        self.combo1 = QComboBox()
        self.combo1.activated.connect(self.reset_draw)
        labelStart = QLabel('Start [sec]:')
        self.qline1 = QLineEdit('0')
        self.qline1.returnPressed.connect(self.reset_draw)
        labelStop = QLabel('Stop [sec]:')
        self.qline2 = QLineEdit('20')
        self.qline2.returnPressed.connect(self.reset_draw)

        grid0 = QGridLayout()
        grid0.addWidget(self.push0_0, 0, 0, 1, 6)
        grid0.addWidget(labelSpeaker, 1, 0, 1, 3)
        grid0.addWidget(self.combo0, 1, 3, 1, 3)
        grid0.addWidget(labelMic, 2, 0, 1, 3)
        grid0.addWidget(self.combo1, 2, 3, 1, 3)
        grid0.addWidget(labelStart, 3, 0, 1, 4)
        grid0.addWidget(self.qline1, 3, 4, 1, 2)
        grid0.addWidget(labelStop, 4, 0, 1, 4)
        grid0.addWidget(self.qline2, 4, 4, 1, 2)
        grid0.setAlignment(QtCore.Qt.AlignTop)
        panel0 = QGroupBox('Plot')
        panel0.setFixedWidth(200)
        panel0.setLayout(grid0)

        # Left panel - Detection ------------------------------------------------
        labelDown = QLabel('Downsample:')
        self.qline3 = QLineEdit('800')
        labelDown.setToolTip('Downsample rate of raw signal.\n'
                             'Typical values: 500~900 Hz')
        labelWidth = QLabel('Width:')
        self.qline4 = QLineEdit('.4')
        labelWidth.setToolTip('This will affect the width of \n'
                              'the smoothing filter.\n'
                              'Typical values: .1 ~ 1')
        labelThresh = QLabel('Threshold:')
        self.qline5 = QLineEdit('.05')
        labelThresh.setToolTip('This will affect the sensitivity to variation.\n'
                               'Typical values: .02 ~ .1')
        self.push1_0 = QPushButton('Run Test')
        self.push1_0.clicked.connect(self.run_test)

        grid1 = QGridLayout()
        grid1.addWidget(labelDown, 0, 0, 1, 4)
        grid1.addWidget(self.qline3, 0, 4, 1, 2)
        grid1.addWidget(labelWidth, 1, 0, 1, 4)
        grid1.addWidget(self.qline4, 1, 4, 1, 2)
        grid1.addWidget(labelThresh, 2, 0, 1, 4)
        grid1.addWidget(self.qline5, 2, 4, 1, 2)
        grid1.addWidget(self.push1_0, 3, 0, 1, 6)
        grid1.setAlignment(QtCore.Qt.AlignTop)
        panel1 = QGroupBox('Detection Parameters')
        panel1.setFixedWidth(200)
        panel1.setLayout(grid1)

        self.push2_0 = QPushButton('Run Detection')
        self.push2_0.clicked.connect(self.run_detection)
        grid2 = QGridLayout()
        grid2.addWidget(self.push2_0)
        panel2 = QGroupBox('Run for whole signal')
        panel2.setFixedWidth(200)
        panel2.setLayout(grid2)

        self.leftbox = QVBoxLayout()
        self.leftbox.addWidget(panel0)
        self.leftbox.addWidget(panel1)
        self.leftbox.addWidget(panel2)
        self.leftbox.addStretch()

        # Right panel -----------------------------------------------------------
        self.win = pg.PlotWidget()
        self.win.resize(1000, 300)
        background_color = self.palette().color(QtGui.QPalette.Background)
        self.win.setBackground(background_color)

        self.rightbox = QVBoxLayout()
        self.plotTitle = QLabel('Preview detection results:')
        self.rightbox.addWidget(self.plotTitle)
        self.rightbox.addWidget(self.win)

        self.hbox = QHBoxLayout()
        self.hbox.addLayout(self.leftbox)    # add panels in the left
        self.hbox.addLayout(self.rightbox)   # add plot on the right

        self.setLayout(self.hbox)
        self.setWindowTitle('Audio Event Detection')
        self.resize(1100, 300)
        self.find_signals()
        self.reset_draw()
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
            if resp == 'microphone':
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
        # Response variables
        resp = self.combo1.currentText()
        self.source_resp = self.responses[resp]
        self.signal_resp = self.source_resp.data
        self.respTimes = []  # clears any previous resp times
        # Common to both stim and resp
        self.fs = self.source_stim.rate
        self.nTotalBins = self.signal_stim.shape[0]
        self.maxTime = self.nTotalBins / self.fs
        self.draw_scene()

    def set_interval(self):
        """Sets new interval."""
        # Control for invalid values and ranges
        self.startTime = np.clip(float(self.qline1.text()), 0, self.maxTime - 1.1)
        self.stopTime = np.clip(float(self.qline2.text()), 1.1, self.maxTime)
        if (self.stopTime - self.startTime) < 1:
            self.stopTime = self.startTime + 1
        self.qline1.setText(str(np.round(self.startTime, 1)))
        self.qline2.setText(str(np.round(self.stopTime, 1)))
        # Calculate correspondent bins
        self.startBin = int(self.startTime * self.fs)
        self.stopBin = int(self.stopTime * self.fs)
        self.plotBins = np.arange(self.startBin, self.stopBin)
        self.plotBins = np.clip(self.plotBins, 0, self.nTotalBins - 1).astype('int')
        self.x = self.plotBins / self.fs

    def draw_scene(self):
        """Draws signal and detection points."""
        self.set_interval()
        self.win.clear()
        # self.win.addLegend()
        # Plot stimuli
        y0 = self.signal_stim[self.plotBins[0]:self.plotBins[-1] + 1].astype(float)
        y0 /= np.max(np.abs(y0))
        self.win.plot(self.x, y0 + 2, pen=pg.mkPen((0, 0, 200), width=1.), name='Speaker')
        # Plot responses
        y1 = self.signal_resp[self.plotBins[0]:self.plotBins[-1] + 1].astype(float)
        y1 /= np.max(np.abs(y1))
        self.win.plot(self.x, y1 + 1, pen=pg.mkPen((200, 0, 0), width=1.), name='Mic')
        # Axes parameters
        self.win.setXRange(self.startTime, self.stopTime)
        self.win.setYRange(0, 3)
        self.win.getAxis('left').setStyle(showValues=False)
        self.win.getAxis('left').setTicks([])
        self.win.getAxis('left').setPen(pg.mkPen(color=(50, 50, 50)))
        self.win.setLabel('bottom', 'Time', units='sec')
        self.win.getAxis('bottom').setPen(pg.mkPen(color=(50, 50, 50)))

    def run_test(self):
        speakerDS, speakerEventDS, micDS, micEventDS = detect_events(
            speaker_data=self.source_stim,
            mic_data=self.source_resp,
            interval=[self.plotBins[0], self.plotBins[-1] + 1],
            dfact=self.fs / float(self.qline3.text()),
            smooth_width=float(self.qline4.text()),
            threshold=float(self.qline5.text())
        )
        self.stimTimes = speakerEventDS + self.startTime
        self.respTimes = micEventDS + self.startTime
        # self.draw_scene()
        self.xx = self.startTime + np.arange(len(speakerDS)) / float(self.qline3.text())
        self.win.clear()
        # self.win.addLegend()
        # Plot speaker
        y0 = speakerDS
        y0 /= np.max(np.abs(y0))
        self.win.plot(self.xx, y0 + 2, pen=pg.mkPen((0, 0, 200), width=1.), name='Speaker')
        for st in self.stimTimes:
            self.win.plot([st, st], [0, 3], pen=pg.mkPen((0, 0, 200), width=2.))
        # Plot responses
        y1 = micDS
        y1 /= np.max(np.abs(y1))
        self.win.plot(self.xx, y1 + 1, pen=pg.mkPen((200, 0, 0), width=1.), name='Mic')
        for rt in self.respTimes:
            self.win.plot([rt, rt], [0, 3], pen=pg.mkPen((200, 0, 0), width=2.))
        # Axes parameters
        self.win.setXRange(self.startTime, self.stopTime)
        self.win.setYRange(0, 3)
        self.win.getAxis('left').setStyle(showValues=False)
        self.win.getAxis('left').setTicks([])
        self.win.getAxis('left').setPen(pg.mkPen(color=(50, 50, 50)))
        self.win.setLabel('bottom', 'Time', units='sec')
        self.win.getAxis('bottom').setPen(pg.mkPen(color=(50, 50, 50)))

    def run_detection(self):
        self.disable_all()
        self.plotTitle.setText('Running event detection. Please wait...')
        self.thread = EventDetectionFunction(
            speaker_data=self.source_stim,
            mic_data=self.source_resp,
            dfact=self.fs / float(self.qline3.text()),
            smooth_width=float(self.qline4.text()),
            threshold=float(self.qline5.text())
        )
        self.thread.finished.connect(lambda: self.out_close(1))
        self.thread.start()

    def disable_all(self):
        self.win.clear()
        self.push0_0.setEnabled(False)
        self.combo0.setEnabled(False)
        self.combo1.setEnabled(False)
        self.qline1.setEnabled(False)
        self.qline2.setEnabled(False)
        self.qline3.setEnabled(False)
        self.qline4.setEnabled(False)
        self.qline5.setEnabled(False)
        self.push1_0.setEnabled(False)
        self.push2_0.setEnabled(False)

    def out_close(self, val):
        self.value = val
        if val == 1:  # finished auto-detection of events
            self.stimTimes = self.thread.stimTimes
            self.respTimes = self.thread.respTimes
            fname = self.parent.model.fullpath
            with NWBHDF5IO(fname, 'r+', load_namespaces=True) as io:
                nwb = io.read()
                # Speaker stimuli times
                ti_stim = TimeIntervals(name='TimeIntervals_speaker')
                times = self.stimTimes.reshape((-1, 2)).astype('float')
                for start, stop in times:
                    ti_stim.add_interval(start, stop)
                # Microphone responses times
                ti_resp = TimeIntervals(name='TimeIntervals_mic')
                times = self.respTimes.reshape((-1, 2)).astype('float')
                for start, stop in times:
                    ti_resp.add_interval(start, stop)
                # Add both to file
                nwb.add_time_intervals(ti_stim)
                nwb.add_time_intervals(ti_resp)
                # Write file
                io.write(nwb)
        self.accept()


# Runs 'detect_events' function, useful to wait for thread ---------------------
class EventDetectionFunction(QtCore.QThread):
    def __init__(self, speaker_data, mic_data, dfact, smooth_width, threshold):
        super().__init__()
        self.source_stim = speaker_data
        self.source_resp = mic_data
        self.dfact = dfact
        self.smooth_width = smooth_width
        self.threshold = threshold

    def run(self):
        speakerDS, speakerEventDS, micDS, micEventDS = detect_events(
            speaker_data=self.source_stim,
            mic_data=self.source_resp,
            interval=None,
            dfact=self.dfact,
            smooth_width=self.smooth_width,
            threshold=self.threshold,
            direction='both'
        )
        self.stimTimes = speakerEventDS
        self.respTimes = micEventDS
