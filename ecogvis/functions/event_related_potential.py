from PyQt5 import QtGui, QtCore
from PyQt5.QtWidgets import (QGridLayout, QGroupBox, QLineEdit, QHBoxLayout,
                             QWidget, QLabel, QPushButton, QVBoxLayout,
                             QComboBox, QScrollArea, QMainWindow)
import pyqtgraph as pg
from ecogvis.functions.misc_dialogs import SelectChannelsDialog
from .FS_colorLUT import get_lut
import numpy as np


# Creates Event-Related Potential dialog ---------------------------------------
class ERPDialog(QMainWindow):
    def __init__(self, parent):
        super().__init__()
        self.setWindowTitle('Event-Related Potentials')
        self.resize(1300, 600)

        self.parent = parent
        self.nCols = 16
        self.alignment = 'start_time'
        self.interval_type = 'speaker'
        self.grid_order = np.arange(256)
        self.transparent = []
        self.Y_start_speaker_mean = {}
        self.Y_start_speaker_sem = {}
        self.Y_stop_speaker_mean = {}
        self.Y_stop_speaker_sem = {}
        self.Y_start_mic_mean = {}
        self.Y_start_mic_sem = {}
        self.Y_stop_mic_mean = {}
        self.Y_stop_mic_sem = {}
        self.X = []
        self.Yscale = {}

        self.source = self.parent.model.nwb.processing['ecephys'].data_interfaces['high_gamma'].data
        self.fs = self.parent.model.nwb.processing['ecephys'].data_interfaces['high_gamma'].rate
        self.electrodes = self.parent.model.nwb.processing['ecephys'].data_interfaces['high_gamma'].electrodes
        self.speaker_start_times = self.parent.model.nwb.intervals['TimeIntervals_speaker']['start_time'].data[:]
        self.speaker_stop_times = self.parent.model.nwb.intervals['TimeIntervals_speaker']['stop_time'].data[:]
        self.mic_start_times = self.parent.model.nwb.intervals['TimeIntervals_mic']['start_time'].data[:]
        self.mic_stop_times = self.parent.model.nwb.intervals['TimeIntervals_mic']['stop_time'].data[:]
        # Get only reference times smaller than the main signal duration
        self.maxTime = self.source.shape[0] / self.fs
        self.speaker_start_times = self.speaker_start_times[self.speaker_start_times < self.maxTime]
        self.speaker_stop_times = self.speaker_stop_times[self.speaker_stop_times < self.maxTime]
        self.mic_start_times = self.mic_start_times[self.mic_start_times < self.maxTime]
        self.mic_stop_times = self.mic_stop_times[self.mic_stop_times < self.maxTime]

        # Left panel
        self.push0_0 = QPushButton('Draw ERP')
        self.push0_0.clicked.connect(self.set_elec_group)
        label0 = QLabel('Group:')
        self.combo0 = QComboBox()
        self.find_groups()
        self.combo0.activated.connect(self.set_elec_group)
        label1 = QLabel('Alignment:')
        self.push1_0 = QPushButton('Onset')
        self.push1_0.setCheckable(True)
        self.push1_0.setChecked(True)
        self.push1_0.clicked.connect(self.set_onset)
        self.push1_1 = QPushButton('Offset')
        self.push1_1.setCheckable(True)
        self.push1_1.setChecked(False)
        self.push1_1.clicked.connect(self.set_offset)
        self.push1_2 = QPushButton('Stimulus')
        self.push1_2.setCheckable(True)
        self.push1_2.setChecked(True)
        self.push1_2.clicked.connect(self.set_stim)
        self.push1_3 = QPushButton('Response')
        self.push1_3.setCheckable(True)
        self.push1_3.setChecked(False)
        self.push1_3.clicked.connect(self.set_resp)
        label2 = QLabel('Width (sec):')
        self.qline2 = QLineEdit('2')
        self.qline2.returnPressed.connect(self.set_width)
        label3 = QLabel('Y scale:')
        self.combo1 = QComboBox()
        self.combo1.addItem('individual')
        self.combo1.addItem('global max')
        self.combo1.addItem('global std')
        self.combo1.activated.connect(self.scale_plots)
        self.push2_0 = QPushButton('Significant')
        self.push2_0.setCheckable(True)
        self.push2_0.setChecked(False)
        self.push3_0 = QPushButton('Brain areas')
        self.push3_0.clicked.connect(self.areas_select)
        self.push4_0 = QPushButton('Save image')
        self.push4_0.clicked.connect(self.save_image)
        label4 = QLabel('Rotate grid:')
        self.push5_0 = QPushButton('90°')
        self.push5_0.clicked.connect(lambda: self.rearrange_grid(90))
        self.push5_0.setToolTip('Counter-clockwise')
        self.push5_1 = QPushButton('-90°')
        self.push5_1.clicked.connect(lambda: self.rearrange_grid(-90))
        self.push5_1.setToolTip('Clockwise')
        self.push5_2 = QPushButton('T')
        self.push5_2.clicked.connect(lambda: self.rearrange_grid('T'))
        self.push5_2.setToolTip('Transpose')
        label5 = QLabel('Rearrange grid:')
        self.push5_3 = QPushButton('L-R')
        self.push5_3.clicked.connect(lambda: self.rearrange_grid('FLR'))
        self.push5_3.setToolTip('Flip Left-Right')
        self.push5_4 = QPushButton('U-D')
        self.push5_4.clicked.connect(lambda: self.rearrange_grid('FUD'))
        self.push5_4.setToolTip('Flip Up-Down')
        self.push5_5 = QPushButton('2FL')
        self.push5_5.clicked.connect(lambda: self.rearrange_grid('2FL'))
        self.push5_5.setToolTip('Double flip')

        self.push1_0.setEnabled(False)
        self.push1_1.setEnabled(False)
        self.push1_2.setEnabled(False)
        self.push1_3.setEnabled(False)
        self.qline2.setEnabled(False)
        self.combo1.setEnabled(False)
        self.push2_0.setEnabled(False)
        self.push3_0.setEnabled(False)
        self.push4_0.setEnabled(False)
        self.push5_0.setEnabled(False)
        self.push5_1.setEnabled(False)
        self.push5_2.setEnabled(False)
        self.push5_3.setEnabled(False)
        self.push5_4.setEnabled(False)
        self.push5_5.setEnabled(False)

        grid0 = QGridLayout()
        grid0.addWidget(label0, 0, 0, 1, 2)
        grid0.addWidget(self.combo0, 0, 2, 1, 4)
        grid0.addWidget(label1, 1, 0, 1, 6)
        grid0.addWidget(self.push1_0, 2, 0, 1, 3)
        grid0.addWidget(self.push1_1, 2, 3, 1, 3)
        grid0.addWidget(self.push1_2, 3, 0, 1, 3)
        grid0.addWidget(self.push1_3, 3, 3, 1, 3)
        grid0.addWidget(QHLine(), 4, 0, 1, 6)
        grid0.addWidget(label2, 5, 0, 1, 6)
        grid0.addWidget(self.qline2, 6, 0, 1, 6)
        grid0.addWidget(QHLine(), 7, 0, 1, 6)
        grid0.addWidget(label3, 8, 0, 1, 6)
        grid0.addWidget(self.combo1, 9, 0, 1, 6)
        grid0.addWidget(QHLine(), 10, 0, 1, 6)
        grid0.addWidget(self.push2_0, 11, 0, 1, 6)
        grid0.addWidget(self.push3_0, 12, 0, 1, 6)
        grid0.addWidget(self.push4_0, 13, 0, 1, 6)
        grid0.addWidget(QHLine(), 14, 0, 1, 6)
        grid0.addWidget(label4, 15, 0, 1, 6)
        grid0.addWidget(self.push5_0, 16, 0, 1, 2)
        grid0.addWidget(self.push5_1, 16, 2, 1, 2)
        grid0.addWidget(self.push5_2, 16, 4, 1, 2)
        grid0.addWidget(label5, 17, 0, 1, 6)
        grid0.addWidget(self.push5_3, 18, 0, 1, 2)
        grid0.addWidget(self.push5_4, 18, 2, 1, 2)
        grid0.addWidget(self.push5_5, 18, 4, 1, 2)
        grid0.setAlignment(QtCore.Qt.AlignTop)

        panel0 = QGroupBox('Controls:')
        panel0.setFixedWidth(180)
        panel0.setLayout(grid0)

        self.leftbox = QVBoxLayout()
        self.leftbox.addWidget(self.push0_0)
        self.leftbox.addWidget(panel0)

        # Right panel
        self.win = pg.GraphicsLayoutWidget()
        self.win.resize(1020, 1020)
        background_color = self.palette().color(QtGui.QPalette.Background)
        self.win.setBackground(background_color)
        # this is to avoid the error:
        # RuntimeError: wrapped C/C++ object of type GraphicsScene has been deleted
        vb = CustomViewBox(self, 0)
        p = self.win.addPlot(0, 0, viewBox=vb)
        p.hideAxis('left')
        p.hideAxis('bottom')
        # Scroll Area Properties
        self.scroll = QScrollArea()
        self.scroll.setVerticalScrollBarPolicy(QtCore.Qt.ScrollBarAsNeeded)
        self.scroll.setHorizontalScrollBarPolicy(QtCore.Qt.ScrollBarAsNeeded)
        self.scroll.setWidgetResizable(False)
        self.scroll.setWidget(self.win)

        self.centralwidget = QWidget()
        self.setCentralWidget(self.centralwidget)
        self.hbox = QHBoxLayout(self.centralwidget)
        self.hbox.addLayout(self.leftbox)    # add panels first
        self.hbox.addWidget(self.scroll)
        self.show()

    def find_groups(self):
        """Find electrodes groups present in current file."""
        elec_groups = list(self.parent.model.nwb.electrode_groups.keys())
        for grp in elec_groups:
            self.combo0.addItem(grp)

    def set_elec_group(self):
        """Sets electrodes group to be plotted, resizes plot grid."""
        self.elec_group = self.combo0.currentText()
        self.grid_order = np.where(self.electrodes.table['group_name'].data[:] == self.elec_group)[0]
        self.nElecs = len(self.grid_order)
        self.nCols = 16
        self.nRows = int(self.nElecs / self.nCols)
        self.set_grid()
        self.draw_erp()

    def set_grid(self):
        # remove previous items
        for i in np.arange(16):
            for j in np.arange(16):
                it = self.win.getItem(i, j)
                if it is not None:
                    self.win.removeItem(it)
        for j in np.arange(self.nCols):
            self.win.ci.layout.setColumnFixedWidth(j, 60)
            self.win.ci.layout.setColumnSpacing(j, 3)
        for i in np.arange(self.nRows):
            self.win.ci.layout.setRowFixedHeight(i, 60)
            self.win.ci.layout.setRowSpacing(i, 3)

    def set_onset(self):
        self.alignment = 'start_time'
        self.push1_1.setChecked(False)
        self.draw_erp()

    def set_offset(self):
        self.alignment = 'stop_time'
        self.push1_0.setChecked(False)
        self.draw_erp()

    def set_stim(self):
        self.interval_type = 'speaker'
        self.push1_3.setChecked(False)
        self.draw_erp()

    def set_resp(self):
        self.interval_type = 'mic'
        self.push1_2.setChecked(False)
        self.draw_erp()

    def set_width(self):
        self.Y_start_speaker_mean = {}
        self.Y_start_speaker_sem = {}
        self.Y_stop_speaker_mean = {}
        self.Y_stop_speaker_sem = {}
        self.Y_start_mic_mean = {}
        self.Y_start_mic_sem = {}
        self.Y_stop_mic_mean = {}
        self.Y_stop_mic_sem = {}
        self.X = []
        self.draw_erp()

    def rearrange_grid(self, angle):
        grid = self.grid_order.reshape(-1, self.nCols)  # re-arranges as 2D array
        # 90 degrees clockwise
        if angle == -90:
            grid = np.rot90(grid, axes=(1, 0))
            if self.nRows != self.nCols:
                aux = np.copy(self.nRows)
                self.nRows = np.copy(self.nCols)
                self.nCols = aux
        # 90 degrees conter-clockwise
        elif angle == 90:
            grid = np.rot90(grid, axes=(0, 1))
            if self.nRows != self.nCols:
                aux = np.copy(self.nRows)
                self.nRows = np.copy(self.nCols)
                self.nCols = aux
        # Transpose
        elif angle == 'T':
            grid = grid.T
            if self.nRows != self.nCols:
                aux = np.copy(self.nRows)
                self.nRows = np.copy(self.nCols)
                self.nCols = aux
        # Flip left-right
        elif angle == 'FLR':
            grid = np.flip(grid, 1)
        # Flip up-down
        elif angle == 'FUD':
            grid = np.flip(grid, 0)
        # Double flip
        elif angle == '2FL':
            grid = np.flip(grid, 1)
            grid = np.flip(grid, 0)
        self.grid_order = grid.flatten()    # re-arranges as 1D array
        self.draw_erp()

    def save_image(self):
        p = self.win.getItem(row=0, col=0)
        self.win.sceneObj.contextMenuItem = p
        self.win.sceneObj.showExportDialog()

    def scale_plots(self):
        for ind, ch in enumerate(self.grid_order):
            row = np.floor(ind / self.nCols)
            col = ind % self.nCols
            p = self.win.getItem(row=row, col=col)
            if p is None:
                return
            else:
                curr_txt = self.combo1.currentText()
                if curr_txt != 'individual':
                    p.setYRange(self.Yscale[curr_txt][0], self.Yscale[curr_txt][1])
                else:
                    if (self.alignment == 'start_time') and (self.interval_type == 'speaker'):
                        yrng = max(abs(self.Y_start_speaker_mean[str(ch)]))
                    elif (self.alignment == 'start_time') and (self.interval_type == 'mic'):
                        yrng = max(abs(self.Y_start_mic_mean[str(ch)]))
                    elif (self.alignment == 'stop_time') and (self.interval_type == 'speaker'):
                        yrng = max(abs(self.Y_stop_speaker_mean[str(ch)]))
                    elif (self.alignment == 'stop_time') and (self.interval_type == 'mic'):
                        yrng = max(abs(self.Y_stop_mic_mean[str(ch)]))
                    p.setYRange(-yrng, yrng)

    def get_erp(self, ch):
        if (self.alignment == 'start_time') and (self.interval_type == 'speaker'):
            if str(ch) in self.Y_start_speaker_mean:   # If it was calculated already
                return self.Y_start_speaker_mean[str(ch)], self.Y_start_speaker_sem[str(ch)], self.X
            else:                              # If it isn't calculated yet
                Y_mean, Y_sem, X = self.calc_erp(ch=ch)
                self.Y_start_speaker_mean[str(ch)] = Y_mean
                self.Y_start_speaker_sem[str(ch)] = Y_sem
                self.X = X
                return self.Y_start_speaker_mean[str(ch)], self.Y_start_speaker_sem[str(ch)], self.X
        if (self.alignment == 'start_time') and (self.interval_type == 'mic'):
            if str(ch) in self.Y_start_mic_mean:   # If it was calculated already
                return self.Y_start_mic_mean[str(ch)], self.Y_start_mic_sem[str(ch)], self.X
            else:                              # If it isn't calculated yet
                Y_mean, Y_sem, X = self.calc_erp(ch=ch)
                self.Y_start_mic_mean[str(ch)] = Y_mean
                self.Y_start_mic_sem[str(ch)] = Y_sem
                self.X = X
                return self.Y_start_mic_mean[str(ch)], self.Y_start_mic_sem[str(ch)], self.X
        if (self.alignment == 'stop_time') and (self.interval_type == 'speaker'):
            if str(ch) in self.Y_stop_speaker_mean:  # If it was calculated already
                return self.Y_stop_speaker_mean[str(ch)], self.Y_stop_speaker_sem[str(ch)], self.X
            else:                               # If it isn't calculated yet
                Y_mean, Y_sem, X = self.calc_erp(ch=ch)
                self.Y_stop_speaker_mean[str(ch)] = Y_mean
                self.Y_stop_speaker_sem[str(ch)] = Y_sem
                self.X = X
                return self.Y_stop_speaker_mean[str(ch)], self.Y_stop_speaker_sem[str(ch)], self.X
        if (self.alignment == 'stop_time') and (self.interval_type == 'mic'):
            if str(ch) in self.Y_stop_mic_mean:  # If it was calculated already
                return self.Y_stop_mic_mean[str(ch)], self.Y_stop_mic_sem[str(ch)], self.X
            else:                               # If it isn't calculated yet
                Y_mean, Y_sem, X = self.calc_erp(ch=ch)
                self.Y_stop_mic_mean[str(ch)] = Y_mean
                self.Y_stop_mic_sem[str(ch)] = Y_sem
                self.X = X
                return self.Y_stop_mic_mean[str(ch)], self.Y_stop_mic_sem[str(ch)], self.X

    def calc_erp(self, ch):
        if (self.alignment == 'start_time') and (self.interval_type == 'speaker'):
            ref_times = self.speaker_start_times
        if (self.alignment == 'stop_time') and (self.interval_type == 'speaker'):
            ref_times = self.speaker_stop_times
        if (self.alignment == 'start_time') and (self.interval_type == 'mic'):
            ref_times = self.mic_start_times
        if (self.alignment == 'stop_time') and (self.interval_type == 'mic'):
            ref_times = self.mic_stop_times
        ref_bins = (ref_times * self.fs).astype('int')
        nBinsTr = int(float(self.qline2.text()) * self.fs / 2)
        start_bins = ref_bins - nBinsTr
        stop_bins = ref_bins + nBinsTr
        nTrials = len(ref_times)
        Y = np.zeros((nTrials, 2 * nBinsTr)) + np.nan
        for tr in np.arange(nTrials):
            Y[tr, :] = self.source[start_bins[tr]:stop_bins[tr], ch]
        Y_mean = np.nanmean(Y, 0)
        Y_sem = np.nanstd(Y, 0) / np.sqrt(Y.shape[0])
        X = np.arange(0, 2 * nBinsTr) / self.fs
        return Y_mean, Y_sem, X

    def draw_erp(self):
        self.push1_0.setEnabled(True)
        self.push1_1.setEnabled(True)
        self.push1_2.setEnabled(True)
        self.push1_3.setEnabled(True)
        self.qline2.setEnabled(True)
        self.combo1.setEnabled(True)
        self.push3_0.setEnabled(True)
        self.push4_0.setEnabled(True)
        self.push5_0.setEnabled(True)
        self.push5_1.setEnabled(True)
        self.push5_2.setEnabled(True)
        self.push5_3.setEnabled(True)
        self.push5_4.setEnabled(True)
        self.push5_5.setEnabled(True)
        self.combo1.setCurrentIndex(self.combo1.findText('individual'))
        self.set_grid()
        cmap = get_lut()
        ymin, ymax = 0, 0
        ystd = 0
        for ind, ch in enumerate(self.grid_order):
            if ch in self.transparent:  # if it should be made transparent
                elem_alpha = 30
            else:
                elem_alpha = 255
            Y_mean, Y_sem, X = self.get_erp(ch=ch)
            dc = np.mean(Y_mean)
            Y_mean -= dc
            ymax = max(max(Y_mean), ymax)
            ymin = min(min(Y_mean), ymin)
            ystd = max(np.std(Y_mean), ystd)
            # Include items
            row = np.floor(ind / self.nCols).astype('int')
            col = int(ind % self.nCols)
            p = self.win.getItem(row=row, col=col)
            if p is None:
                vb = CustomViewBox(self, ch)
                p = self.win.addPlot(row=row, col=col, viewBox=vb)
            p.hideAxis('left')
            p.hideAxis('bottom')
            p.clear()
            p.setMouseEnabled(x=False, y=False)
            p.setToolTip('Ch ' + str(ch + 1) + '\n' + str(self.parent.model.nwb.electrodes['location'][ch]))
            # Background
            loc = 'ctx-lh-' + self.parent.model.nwb.electrodes['location'][ch]
            vb = p.getViewBox()
            color = tuple(cmap[loc])
            vb.setBackgroundColor((*color, min(elem_alpha, 70)))  # append alpha to color tuple
            # Main plots
            mean = p.plot(x=X, y=Y_mean, pen=pg.mkPen((50, 50, 50, min(elem_alpha, 255)), width=1.))
            semp = p.plot(x=X, y=Y_mean + Y_sem, pen=pg.mkPen((100, 100, 100, min(elem_alpha, 100)), width=.1))
            semm = p.plot(x=X, y=Y_mean - Y_sem, pen=pg.mkPen((100, 100, 100, min(elem_alpha, 100)), width=.1))
            fill = pg.FillBetweenItem(semm, semp, pg.mkBrush(100, 100, 100, min(elem_alpha, 100)))
            p.addItem(fill)
            p.hideButtons()
            p.setXRange(X[0], X[-1])
            yrng = max(abs(Y_mean))
            p.setYRange(-yrng, yrng)
            xref = [X[int(len(X) / 2)], X[int(len(X) / 2)]]
            yref = [-1000 * yrng, 1000 * yrng]
            p.plot(x=xref, y=yref, pen=(0, 0, 0, min(elem_alpha, 255)))    # reference mark
            p.plot(x=X, y=np.zeros(len(X)), pen=(0, 0, 0, min(elem_alpha, 255)))  # Zero line
            # Axis control
            left = p.getAxis('left')
            left.setStyle(showValues=False)
            left.setTicks([])
            bottom = p.getAxis('bottom')
            bottom.setStyle(showValues=False)
            bottom.setTicks([])
        # store scale limits
        self.Yscale['global max'] = [ymin, ymax]
        self.Yscale['global std'] = [-ystd, ystd]

    def areas_select(self):
        # Dialog to choose channels from specific brain regions
        w = SelectChannelsDialog(self.parent.model.all_regions, self.parent.model.regions_mask)
        self.transparent = []
        for ind, ch in enumerate(self.grid_order):
            loc = self.parent.model.nwb.electrodes['location'][ch]
            if loc not in w.choices:
                self.transparent.append(ch)
        self.draw_erp()


# Viewbox for ERP plots --------------------------------------------------------
class CustomViewBox(pg.ViewBox):
    def __init__(self, parent, ch):
        pg.ViewBox.__init__(self)
        self.parent = parent
        self.ch = ch

    def mouseDoubleClickEvent(self, ev):
        IndividualERPDialog(self)


# Individual Event-Related Potential dialog ------------------------------------
class IndividualERPDialog(QtGui.QDialog):
    def __init__(self, parent):
        super().__init__()
        # Enable antialiasing for prettier plots
        pg.setConfigOptions(antialias=True)

        self.parent = parent
        self.ch = parent.ch
        self.alignment = 'start_time'
        self.interval_type = 'speaker'
        self.source = self.parent.parent.source
        self.fs = self.parent.parent.fs
        self.speaker_start_times = self.parent.parent.speaker_start_times
        self.speaker_stop_times = self.parent.parent.speaker_stop_times
        self.mic_start_times = self.parent.parent.mic_start_times
        self.mic_stop_times = self.parent.parent.mic_stop_times

        # Left panel
        label1 = QLabel('Alignment:')
        self.push1_0 = QPushButton('Onset')
        self.push1_0.setCheckable(True)
        self.push1_0.setChecked(True)
        self.push1_0.clicked.connect(self.set_onset)
        self.push1_1 = QPushButton('Offset')
        self.push1_1.setCheckable(True)
        self.push1_1.setChecked(False)
        self.push1_1.clicked.connect(self.set_offset)
        self.push1_2 = QPushButton('Stimulus')
        self.push1_2.setCheckable(True)
        self.push1_2.setChecked(True)
        self.push1_2.clicked.connect(self.set_stim)
        self.push1_3 = QPushButton('Response')
        self.push1_3.setCheckable(True)
        self.push1_3.setChecked(False)
        self.push1_3.clicked.connect(self.set_resp)
        label2 = QLabel('Width (sec):')
        self.qline2 = QLineEdit('2')
        self.qline2.returnPressed.connect(self.draw_erp)

        grid0 = QGridLayout()
        grid0.addWidget(label1, 0, 0, 1, 2)
        grid0.addWidget(self.push1_0, 1, 0, 1, 1)
        grid0.addWidget(self.push1_1, 1, 1, 1, 1)
        grid0.addWidget(self.push1_2, 2, 0, 1, 1)
        grid0.addWidget(self.push1_3, 2, 1, 1, 1)
        grid0.addWidget(label2, 3, 0, 1, 1)
        grid0.addWidget(self.qline2, 3, 1, 1, 1)
        grid0.setAlignment(QtCore.Qt.AlignTop)
        panel0 = QGroupBox('Controls:')
        panel0.setFixedWidth(180)
        panel0.setLayout(grid0)
        self.leftbox = QVBoxLayout()
        self.leftbox.addWidget(panel0)

        # Right panel
        self.win = pg.GraphicsLayoutWidget()
        self.win.resize(900, 600)
        self.win.setBackground('w')
        self.hbox = QHBoxLayout()
        # self.hbox.addWidget(panel0)
        self.hbox.addLayout(self.leftbox)
        self.hbox.addWidget(self.win)
        self.setLayout(self.hbox)
        self.setWindowTitle('Individual Event-Related Potential - Ch ' + str(self.ch + 1))
        self.resize(900, 600)

        self.draw_erp()
        self.exec_()

    def set_onset(self):
        self.alignment = 'start_time'
        self.push1_1.setChecked(False)
        self.draw_erp()

    def set_offset(self):
        self.alignment = 'stop_time'
        self.push1_0.setChecked(False)
        self.draw_erp()

    def set_stim(self):
        self.interval_type = 'speaker'
        self.push1_3.setChecked(False)
        self.draw_erp()

    def set_resp(self):
        self.interval_type = 'mic'
        self.push1_2.setChecked(False)
        self.draw_erp()

    def calc_erp(self, ch):
        if (self.alignment == 'start_time') and (self.interval_type == 'speaker'):
            ref_times = self.speaker_start_times
        if (self.alignment == 'stop_time') and (self.interval_type == 'speaker'):
            ref_times = self.speaker_stop_times
        if (self.alignment == 'start_time') and (self.interval_type == 'mic'):
            ref_times = self.mic_start_times
        if (self.alignment == 'stop_time') and (self.interval_type == 'mic'):
            ref_times = self.mic_stop_times
        ref_bins = (ref_times * self.fs).astype('int')
        nBinsTr = int(float(self.qline2.text()) * self.fs / 2)
        start_bins = ref_bins - nBinsTr
        stop_bins = ref_bins + nBinsTr
        nTrials = len(ref_times)
        Y = np.zeros((nTrials, 2 * nBinsTr)) + np.nan
        for tr in np.arange(nTrials):
            Y[tr, :] = self.source[start_bins[tr]:stop_bins[tr], ch]
        Y_mean = np.nanmean(Y, 0)
        Y_sem = np.nanstd(Y, 0) / np.sqrt(Y.shape[0])
        X = np.arange(0, 2 * nBinsTr) / self.fs
        X -= X[-1] / 2
        return Y_mean, Y_sem, X

    def draw_erp(self):
        cmap = get_lut()
        Y_mean, Y_sem, X = self.calc_erp(ch=self.ch)
        dc = np.mean(Y_mean)
        Y_mean -= dc
        p = self.win.getItem(row=0, col=0)
        if p is None:
            p = self.win.addPlot(row=0, col=0)
        p.clear()
        p.setMouseEnabled(x=False, y=True)
        # Background color
        loc = 'ctx-lh-' + self.parent.parent.parent.model.nwb.electrodes['location'][self.ch]
        vb = p.getViewBox()
        color = tuple(cmap[loc])
        vb.setBackgroundColor((*color, 70))  # append alpha to color tuple
        vb.border = pg.mkPen(color='w')
        # Main plots
        mean = p.plot(x=X, y=Y_mean, pen=pg.mkPen((60, 60, 60), width=2.))
        semp = p.plot(x=X, y=Y_mean + Y_sem, pen=pg.mkPen((100, 100, 100, 100), width=.1))
        semm = p.plot(x=X, y=Y_mean - Y_sem, pen=pg.mkPen((100, 100, 100, 100), width=.1))
        fill = pg.FillBetweenItem(semm, semp, pg.mkBrush(100, 100, 100, 100))
        p.addItem(fill)
        p.hideButtons()
        p.setXRange(X[0], X[-1])
        p.setYRange(min(Y_mean), max(Y_mean))
        xref = [X[int(len(X) / 2)], X[int(len(X) / 2)]]
        yref = [-1000, 1000]
        p.plot(x=xref, y=yref, pen=(0, 0, 0))    # reference mark
        p.plot(x=X, y=np.zeros(len(X)), pen=(0, 0, 0))  # Zero line
        # Axis control
        left = p.getAxis('left')
        left.setStyle(showValues=False)
        left.setTicks([])
        bottom = p.getAxis('bottom')
        bottom.setStyle(showValues=True)
        p.setLabel('bottom', 'Time', units='sec')


# Gray line for visual separation of buttons -----------------------------------
class QHLine(QtGui.QFrame):
    def __init__(self):
        super().__init__()
        self.setFrameShape(QtGui.QFrame.HLine)
        self.setFrameShadow(QtGui.QFrame.Sunken)
