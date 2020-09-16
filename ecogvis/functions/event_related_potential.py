from PyQt5 import QtGui, QtCore
from PyQt5.QtWidgets import (QGridLayout, QGroupBox, QLineEdit, QHBoxLayout,
                             QWidget, QLabel, QPushButton, QVBoxLayout,
                             QComboBox, QScrollArea, QMainWindow)
import pyqtgraph as pg
from ecogvis.functions.misc_dialogs import SelectChannelsDialog
from .FS_colorLUT import get_lut
import numpy as np

default_interval = 'TimeIntervals_speaker'
default_alignment = 'start_time'


# Creates Event-Related Potential dialog ---------------------------------------
class ERPDialog(QMainWindow):
    def __init__(self, parent):
        super().__init__()
        self.setWindowTitle('Event-Related Potentials')
        self.resize(1300, 600)

        self.parent = parent
        self.grid_order = np.arange(256)
        self.transparent = []
        self.Yscale = {}

        self.all_regions = np.unique(self.parent.model.all_regions)
        self.regions_mask = np.ones(len(self.all_regions))

        self.source = self.parent.model.nwb.processing['ecephys'].data_interfaces['high_gamma'].data
        self.fs = self.parent.model.nwb.processing['ecephys'].data_interfaces['high_gamma'].rate
        self.electrodes = self.parent.model.nwb.processing['ecephys'].data_interfaces['high_gamma'].electrodes
        self.maxTime = self.source.shape[0] / self.fs

        # Make intervals dictionary, e.g. self.intervals['TimeIntervals_speaker']['start_time']['times'] = data[:]
        self.intervals = {}
        for interval_type, interval_obj in self.parent.model.nwb.intervals.items():
            self.intervals[interval_type] = {}
            for alignment_type, obj in zip(interval_obj.colnames, interval_obj.columns):
                times = obj.data[:]
                # Get only reference times smaller than the main signal duration
                times = times[times < self.maxTime]
                self.intervals[interval_type][alignment_type] = {}
                self.intervals[interval_type][alignment_type]['times'] = times
                self.intervals[interval_type][alignment_type]['Y_mean'] = {}
                self.intervals[interval_type][alignment_type]['Y_sem'] = {}
        self.X = []

        self.interval_sel = default_interval
        self.alignment_sel = default_alignment

        # Left panel
        self.push0_0 = QPushButton('Draw ERP')
        self.push0_0.clicked.connect(self.set_elec_group)
        label0 = QLabel('Group:')
        self.combo0 = QComboBox()
        self.find_groups()
        self.combo0.activated.connect(self.set_elec_group)
        label1 = QLabel('Alignment:')
        self.combo_interval = QComboBox()
        self.combo_interval.activated.connect(self.set_interval)
        self.combo_alignment = QComboBox()
        self.combo_alignment.activated.connect(self.set_alignment)
        self.find_intervals()
        label_ncols = QLabel('Columns:')
        self.qline_ncols = QLineEdit()
        label_nrows = QLabel('Rows:')
        self.qline_nrows = QLineEdit() # will never be enabled (must be nElecs/nCols)
        self.qline_ncols.returnPressed.connect(self.set_grid)

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

        self.qline_nrows.setEnabled(False)
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
        grid0.addWidget(self.combo_interval, 2, 0, 1, 6)
        grid0.addWidget(self.combo_alignment, 3, 0, 1, 6)
        grid0.addWidget(label_ncols, 4, 0, 1, 3)
        grid0.addWidget(label_nrows, 4, 3, 1, 3)
        grid0.addWidget(self.qline_ncols, 5, 0, 1, 3)
        grid0.addWidget(self.qline_nrows, 5, 3, 1, 3)
        grid0.addWidget(QHLine(), 6, 0, 1, 6)
        grid0.addWidget(label2, 7, 0, 1, 6)
        grid0.addWidget(self.qline2, 8, 0, 1, 6)
        grid0.addWidget(QHLine(), 9, 0, 1, 6)
        grid0.addWidget(label3, 10, 0, 1, 6)
        grid0.addWidget(self.combo1, 11, 0, 1, 6)
        grid0.addWidget(QHLine(), 12, 0, 1, 6)
        grid0.addWidget(self.push2_0, 13, 0, 1, 6)
        grid0.addWidget(self.push3_0, 14, 0, 1, 6)
        grid0.addWidget(self.push4_0, 15, 0, 1, 6)
        grid0.addWidget(QHLine(), 16, 0, 1, 6)
        grid0.addWidget(label4, 17, 0, 1, 6)
        grid0.addWidget(self.push5_0, 18, 0, 1, 2)
        grid0.addWidget(self.push5_1, 18, 2, 1, 2)
        grid0.addWidget(self.push5_2, 18, 4, 1, 2)
        grid0.addWidget(label5, 19, 0, 1, 6)
        grid0.addWidget(self.push5_3, 20, 0, 1, 2)
        grid0.addWidget(self.push5_4, 20, 2, 1, 2)
        grid0.addWidget(self.push5_5, 20, 4, 1, 2)
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

        self.set_elec_group()
        self.set_interval(sel=self.interval_sel)

    def find_groups(self):
        """Find electrodes groups present in current file."""
        elec_groups = list(self.parent.model.nwb.electrode_groups.keys())
        for grp in elec_groups:
            self.combo0.addItem(grp)

    def find_intervals(self):
        intervals = list(self.intervals.keys())
        for ivl in intervals:
            self.combo_interval.addItem(ivl)

    def find_alignments(self, starting_sel=default_alignment):
        """Find alignment types for current interval type"""
        self.combo_alignment.clear()
        ivl = self.combo_interval.currentText()
        alignments = list(self.intervals[ivl].keys())
        for aln in alignments:
            self.combo_alignment.addItem(aln)

        self.set_alignment(sel=starting_sel)

    def set_elec_group(self):
        """Sets electrodes group to be plotted, resizes plot grid."""
        self.elec_group = self.combo0.currentText()
        self.grid_order = np.where(self.electrodes.table['group_name'].data[:] == self.elec_group)[0]
        self.nElecs = len(self.grid_order)
        self.qline_ncols.setText(str(self.guess_ncols()))
        self.qline_ncols.setEnabled(True)
        self.set_grid()

    def guess_ncols(self):
        if self.nElecs == 64:
            return 8
        elif self.nElecs in [128,256]:
            return 16
        else: # depths, strips
            return min(self.nElecs, 16)

    def set_interval(self, sel=None):
        if isinstance(sel, int):
            sel = self.combo_interval.itemText(sel)
        if sel is not None:
            index = self.combo_interval.findText(sel, QtCore.Qt.MatchFixedString)
            if index >= 0:
                self.combo_interval.setCurrentIndex(index)

        sel = self.combo_interval.currentText()
        self.interval_sel = sel
        self.find_alignments(starting_sel=self.alignment_sel)

    def set_alignment(self, sel=None):
        if isinstance(sel, int):
            sel = self.combo_alignment.itemText(sel)
        if sel is not None:
            index = self.combo_alignment.findText(sel, QtCore.Qt.MatchFixedString)
            if index >= 0:
                self.combo_alignment.setCurrentIndex(index)

        sel = self.combo_alignment.currentText()
        self.alignment_sel = sel
        self.draw_erp()

    def set_grid(self):
        # remove previous items
        for it in self.win.items():
            if isinstance(it,pg.graphicsItems.PlotItem.PlotItem):
                self.win.removeItem(it)

        # Update grid parameters
        try:
            self.nCols = int(self.qline_ncols.text())
        except x:
            self.nCols = self.guess_ncols()
            self.qline_ncols.setText(str(self.nCols))
        self.nRows = int(np.ceil(self.nElecs / self.nCols))
        self.qline_nrows.setText(str(self.nRows))
        self.qline_ncols.repaint()
        self.qline_nrows.repaint()

        # add new items
        for j in np.arange(self.nCols):
            self.win.ci.layout.setColumnFixedWidth(j, 60)
            self.win.ci.layout.setColumnSpacing(j, 3)
        for i in np.arange(self.nRows):
            self.win.ci.layout.setRowFixedHeight(i, 60)
            self.win.ci.layout.setRowSpacing(i, 3)

        self.draw_erp()

    def set_width(self):
        for interval_type, interval_dict in self.intervals.items():
            for alignment_type, alignment_dict in interval_dict.items():
                alignment_dict['Y_mean'] = {}
                alignment_dict['Y_sem'] = {}
        self.X = []
        self.draw_erp()

    def rearrange_grid(self, angle):
        grid = self.grid_order.reshape(-1, self.nCols)  # re-arranges as 2D array
        # 90 degrees clockwise
        if angle == -90:
            grid = np.rot90(grid, axes=(1, 0))
            if self.nRows != self.nCols:
                self.qline_ncols.setText(str(self.nRows))
        # 90 degrees conter-clockwise
        elif angle == 90:
            grid = np.rot90(grid, axes=(0, 1))
            if self.nRows != self.nCols:
                self.qline_ncols.setText(str(self.nRows))
        # Transpose
        elif angle == 'T':
            grid = grid.T
            if self.nRows != self.nCols:
                self.qline_ncols.setText(str(self.nRows))
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
        self.qline_ncols.setEnabled(False) # User should set ncols before doing any transposing
        self.set_grid()

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
                    yrng = max(abs(self.intervals[self.interval_sel][self.alignment_sel]['Y_mean'][str(ch)]))
                    p.setYRange(-yrng, yrng)

    def get_erp(self, ch):
        try:
            return self.intervals[self.interval_sel][self.alignment_sel]['Y_mean'][str(ch)], \
                   self.intervals[self.interval_sel][self.alignment_sel]['Y_sem'][str(ch)], \
                   self.X
        except:
            Y_mean, Y_sem, X = self.calc_erp(ch=ch)
            self.intervals[self.interval_sel][self.alignment_sel]['Y_mean'][str(ch)] = Y_mean
            self.intervals[self.interval_sel][self.alignment_sel]['Y_sem'][str(ch)] = Y_sem
            self.X = X
            return self.intervals[self.interval_sel][self.alignment_sel]['Y_mean'][str(ch)], \
                   self.intervals[self.interval_sel][self.alignment_sel]['Y_sem'][str(ch)], \
                   self.X

    def calc_erp(self, ch):
        ref_times = self.intervals[self.interval_sel][self.alignment_sel]['times']
        ref_bins = (ref_times * self.fs).astype('int')
        nBinsTr = int(float(self.qline2.text()) * self.fs / 2)
        start_bins = ref_bins - nBinsTr
        stop_bins = ref_bins + nBinsTr
        nTrials = len(ref_times)
        Y = np.zeros((nTrials, 2 * nBinsTr)) + np.nan
        for tr in np.arange(nTrials):
            # Get only trials with enough data points
            if self.source[start_bins[tr]:stop_bins[tr], ch].shape[0] == Y.shape[1]:
                Y[tr, :] = self.source[start_bins[tr]:stop_bins[tr], ch]
        Y_mean = np.nanmean(Y, 0)
        Y_sem = np.nanstd(Y, 0) / np.sqrt(Y.shape[0])
        X = np.arange(0, 2 * nBinsTr) / self.fs
        return Y_mean, Y_sem, X

    def draw_erp(self):
        self.qline2.setEnabled(True)
        self.combo1.setEnabled(True)
        self.push3_0.setEnabled(True)
        self.push4_0.setEnabled(True)
        if self.nElecs % 16 == 0:
            self.push5_0.setEnabled(True)
            self.push5_1.setEnabled(True)
            self.push5_2.setEnabled(True)
            self.push5_3.setEnabled(True)
            self.push5_4.setEnabled(True)
            self.push5_5.setEnabled(True)
        else:
            self.push5_0.setEnabled(False)
            self.push5_1.setEnabled(False)
            self.push5_2.setEnabled(False)
            self.push5_3.setEnabled(False)
            self.push5_4.setEnabled(False)
            self.push5_5.setEnabled(False)
        self.combo1.setCurrentIndex(self.combo1.findText('individual'))
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
            color = tuple(cmap.get(loc, cmap['Unknown']))
            vb.setBackgroundColor(
                (*color, min(elem_alpha, 70)))  # append alpha to color tuple
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
        w = SelectChannelsDialog(self.all_regions, self.regions_mask)
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
        self.intervals = self.parent.parent.intervals

        self.interval_sel = self.parent.parent.interval_sel
        self.alignment_sel = self.parent.parent.alignment_sel

        # Left panel
        label1 = QLabel('Alignment:')
        self.combo_interval = QComboBox()
        self.combo_interval.activated.connect(self.set_interval)
        self.combo_alignment = QComboBox()
        self.combo_alignment.activated.connect(self.set_alignment)
        self.find_intervals()

        label2 = QLabel('Width (sec):')
        self.qline2 = QLineEdit('2')
        self.qline2.returnPressed.connect(self.draw_erp)

        grid0 = QGridLayout()
        grid0.addWidget(label1, 0, 0, 1, 2)
        grid0.addWidget(self.combo_interval, 1, 0, 1, 6)
        grid0.addWidget(self.combo_alignment, 2, 0, 1, 6)
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

        self.set_interval(sel=self.interval_sel)

        self.draw_erp()
        self.exec_()

    def find_intervals(self):
        intervals = list(self.intervals.keys())
        for ivl in intervals:
            self.combo_interval.addItem(ivl)

    def find_alignments(self, starting_sel=default_alignment):
        """Find alignment types for current interval type"""
        self.combo_alignment.clear()
        ivl = self.combo_interval.currentText()
        alignments = list(self.intervals[ivl].keys())
        for aln in alignments:
            self.combo_alignment.addItem(aln)
        self.set_alignment(sel=starting_sel)

    def set_interval(self, sel=None):
        if isinstance(sel, int):
            sel = self.combo_interval.itemText(sel)
        if sel is not None:
            index = self.combo_interval.findText(sel, QtCore.Qt.MatchFixedString)
            if index >= 0:
                self.combo_interval.setCurrentIndex(index)
        sel = self.combo_interval.currentText()
        self.interval_sel = sel
        self.find_alignments(starting_sel=self.alignment_sel)

    def set_alignment(self, sel=None):
        if isinstance(sel, int):
            sel = self.combo_alignment.itemText(sel)
        if sel is not None:
            index = self.combo_alignment.findText(sel, QtCore.Qt.MatchFixedString)
            if index >= 0:
                self.combo_alignment.setCurrentIndex(index)
        sel = self.combo_alignment.currentText()
        self.alignment_sel = sel
        self.draw_erp()

    def get_erp(self, ch):
        try:
            return self.intervals[self.interval_sel][self.alignment_sel]['Y_mean'][str(ch)], \
                   self.intervals[self.interval_sel][self.alignment_sel]['Y_sem'][str(ch)], \
                   self.X
        except:
            Y_mean, Y_sem, X = self.calc_erp(ch=ch)
            self.intervals[self.interval_sel][self.alignment_sel]['Y_mean'][str(ch)] = Y_mean
            self.intervals[self.interval_sel][self.alignment_sel]['Y_sem'][str(ch)] = Y_sem
            self.X = X
            return self.intervals[self.interval_sel][self.alignment_sel]['Y_mean'][str(ch)], \
                   self.intervals[self.interval_sel][self.alignment_sel]['Y_sem'][str(ch)], \
                   self.X

    def calc_erp(self, ch):
        ref_times = self.intervals[self.interval_sel][self.alignment_sel]['times']
        ref_bins = (ref_times * self.fs).astype('int')
        nBinsTr = int(float(self.qline2.text()) * self.fs / 2)
        start_bins = ref_bins - nBinsTr
        stop_bins = ref_bins + nBinsTr
        nTrials = len(ref_times)
        Y = np.zeros((nTrials, 2 * nBinsTr)) + np.nan
        for tr in np.arange(nTrials):
            # Get only trials with enough data points
            if self.source[start_bins[tr]:stop_bins[tr], ch].shape[0] == Y.shape[1]:
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
        color = tuple(cmap.get(loc, cmap['Unknown']))
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
