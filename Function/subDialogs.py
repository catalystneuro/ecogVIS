from PyQt5 import QtGui, QtCore, uic
from PyQt5.QtWidgets import (QTableWidgetItem, QGridLayout, QGroupBox, QVBoxLayout,
    QWidget)
import pyqtgraph as pg
from ecog.utils import bands as default_bands
from ecog.signal_processing.preprocess_data import preprocess_data
from threading import Event, Thread
import numpy as np
import os
import time

path = os.path.dirname(__file__)

# Creates custom interval type -------------------------------------------------
Ui_CustomInterval, _ = uic.loadUiType(os.path.join(path,"intervals_gui.ui"))
class CustomIntervalDialog(QtGui.QDialog, Ui_CustomInterval):
    def __init__(self):
        super().__init__()
        self.setupUi(self)

    def getResults(self):
        if self.exec_() == QtGui.QDialog.Accepted:
            # get all values
            text = str(self.lineEdit.text())
            color = str(self.comboBox.currentText())
            return text, color
        else:
            return '', ''


# Selects channels from specific brain regions to be plotted -------------------
class SelectChannelsDialog(QtGui.QDialog):
    def __init__(self, stringlist, checked):
        super().__init__()

        self.model = QtGui.QStandardItemModel()
        for i, string in enumerate(stringlist):
            item = QtGui.QStandardItem(string)
            item.setCheckable(True)
            check = (QtCore.Qt.Checked if checked[i] else QtCore.Qt.Unchecked)
            item.setCheckState(check)
            self.model.appendRow(item)

        self.listView = QtGui.QListView()
        self.listView.setModel(self.model)

        self.okButton = QtGui.QPushButton("OK")
        self.selectButton = QtGui.QPushButton("Select All")
        self.unselectButton = QtGui.QPushButton("Unselect All")

        hbox = QtGui.QHBoxLayout()
        hbox.addStretch(1)
        hbox.addWidget(self.okButton)
        hbox.addWidget(self.selectButton)
        hbox.addWidget(self.unselectButton)

        vbox = QtGui.QVBoxLayout()
        vbox.addWidget(self.listView)
        #vbox.addStretch(1)
        vbox.addLayout(hbox)

        self.setLayout(vbox)
        #self.setLayout(layout)
        self.setWindowTitle('Select Regions:')

        self.okButton.clicked.connect(self.onAccepted)
        self.selectButton.clicked.connect(self.select_all)
        self.unselectButton.clicked.connect(self.unselect_all)

        self.select_all()
        self.choices = [self.model.item(i).text() for i in
                        range(self.model.rowCount())
                        if self.model.item(i).checkState()
                        == QtCore.Qt.Checked]
        self.exec_()

    def onAccepted(self):
        self.choices = [self.model.item(i).text() for i in
                        range(self.model.rowCount())
                        if self.model.item(i).checkState()
                        == QtCore.Qt.Checked]
        self.accept()

    def select_all(self):
        for i in range(self.model.rowCount()):
            item = self.model.item(i)
            item.setCheckState(QtCore.Qt.Checked)

    def unselect_all(self):
        for i in range(self.model.rowCount()):
            item = self.model.item(i)
            item.setCheckState(QtCore.Qt.Unchecked)



# Creates Spectral Analysis choice dialog --------------------------------------
Ui_SpectralChoice, _ = uic.loadUiType(os.path.join(path,"spectral_choice_gui.ui"))
class SpectralChoiceDialog(QtGui.QDialog, Ui_SpectralChoice):
    def __init__(self, nwb, fpath, fname):
        super().__init__()
        self.setupUi(self)
        self.nwb = nwb
        self.fpath = fpath
        self.fname = fname

        self.data_exists = False    #Indicates if data already exists or will be created
        self.decomp_type = None     #Indicates the chosen decomposition type
        self.custom_bands = None    #Values for custom filter bands (user input)

        self.radioButton_1.clicked.connect(self.choice_default)
        self.radioButton_2.clicked.connect(self.choice_custom)
        self.pushButton_1.clicked.connect(self.add_band)
        self.pushButton_2.clicked.connect(self.del_band)

        self.runButton.clicked.connect(self.out_accepted)
        self.cancelButton.clicked.connect(self.out_cancel)

        self.exec_()

    def choice_default(self):  # default chosen
        self.decomp_type = 'default'
        self.custom_bands = None
        self.pushButton_1.setEnabled(False)
        self.pushButton_2.setEnabled(False)
        self.tableWidget.setEditTriggers(QtGui.QAbstractItemView.NoEditTriggers)
        try:    # if data already exists in file
            decomp = self.nwb.modules['ecephys'].data_interfaces['Bandpower_default']
            text = "'Default' frequency decomposition data exists in current file.\n" \
                   "The bands are shown in the table."
            self.label_1.setText(text)
            self.data_exists = True
            # Populate table with values
            self.tableWidget.setHorizontalHeaderLabels(['center','sigma'])
            p0 = decomp.bands['filter_param_0']
            p1 = decomp.bands['filter_param_1']
            self.tableWidget.setRowCount(len(p0))
            for i in np.arange(len(p0)):
                self.tableWidget.setItem(i, 0, QTableWidgetItem(str(round(p0[i],1))))
                self.tableWidget.setItem(i, 1, QTableWidgetItem(str(round(p1[i],1))))
        except:   # if data does not exist in file
            text = "'Default' frequency decomposition data does not exist in current file.\n" \
                   "Do you want to generate it? The bands are shown in the table."
            self.label_1.setText(text)
            self.data_exists = False
            # Populate table with values
            self.tableWidget.setHorizontalHeaderLabels(['center [Hz]','sigma [Hz]'])
            p0 = default_bands.chang_lab['cfs']
            p1 = default_bands.chang_lab['sds']
            self.tableWidget.setRowCount(len(p0))
            for i in np.arange(len(p0)):
                self.tableWidget.setItem(i, 0, QTableWidgetItem(str(round(p0[i],1))))
                self.tableWidget.setItem(i, 1, QTableWidgetItem(str(round(p1[i],1))))



    def choice_custom(self):  # default chosen
        self.decomp_type = 'custom'
        self.custom_bands = None
        try:    # if data already exists in file
            decomp = self.nwb.modules['ecephys'].data_interfaces['Bandpower_custom']
            text = "'Custom' frequency decomposition data exists in current file.\n" \
                   "The bands are shown in the table."
            self.label_1.setText(text)
            self.data_exists = True
            # Populate table with values
            self.tableWidget.setHorizontalHeaderLabels(['center','sigma'])
            p0 = decomp.bands['filter_param_0']
            p1 = decomp.bands['filter_param_1']
            self.tableWidget.setRowCount(len(p0))
            self.custom_bands = np.zeros((2,len(p0)))
            for i in np.arange(len(p0)):
                self.tableWidget.setItem(i, 0, QTableWidgetItem(str(round(p0[i],1))))
                self.tableWidget.setItem(i, 1, QTableWidgetItem(str(round(p1[i],1))))
                self.custom_bands[i,0] = round(p0[i],1)
                self.custom_bands[i,1] = round(p1[i],1)
        except:  # if data does not exist in file
            text = "'Custom' frequency decomposition data does not exist in current file.\n" \
                   "Do you want to generate it? Select the bands in the table."
            self.label_1.setText(text)
            self.data_exists = False
            # Allows user to populate table with values
            self.tableWidget.setRowCount(1)
            self.tableWidget.setHorizontalHeaderLabels(['center','sigma'])
            self.tableWidget.setItem(0, 0, QTableWidgetItem(str(0)))
            self.tableWidget.setItem(0, 1, QTableWidgetItem(str(0)))
            self.tableWidget.setEditTriggers(QtGui.QAbstractItemView.DoubleClicked)
            self.pushButton_1.setEnabled(True)
            self.pushButton_2.setEnabled(True)

    def add_band(self):
        nRows = self.tableWidget.rowCount()
        self.tableWidget.insertRow(nRows)
        self.tableWidget.setItem(nRows, 0, QTableWidgetItem(str(0)))
        self.tableWidget.setItem(nRows, 1, QTableWidgetItem(str(0)))

    def del_band(self):
        nRows = self.tableWidget.rowCount()
        self.tableWidget.removeRow(nRows-1)

    def out_accepted(self):
        if self.decomp_type=='custom':
            nRows = self.tableWidget.rowCount()
            self.custom_bands = np.zeros((2,nRows))
            for i in np.arange(nRows):
                self.custom_bands[0,i] = float(self.tableWidget.item(i, 0).text())
                self.custom_bands[1,0] = float(self.tableWidget.item(i, 1).text())
        # If Decomposition data does not exist in NWB file and user decides to create it
        # NOT WORKING 100%, IT SHOULD FREEZE DIALOG WHILE PROCESSING HAPPENS
        self.label_2.setText('Processing signals. Please wait...')
        self.pushButton_1.setEnabled(False)
        self.pushButton_2.setEnabled(False)
        self.tableWidget.setEnabled(False)
        self.groupBox.setEnabled(False)
        self.runButton.setEnabled(False)
        self.cancelButton.setEnabled(False)
        #-----------------------------------------------------------------------
        if not self.data_exists:
            subj, aux = self.fname.split('_')
            block = [ aux.split('.')[0][1:] ]
            ready = Event()
            program = ChildProgram(ready=ready, path=self.fpath, subject=subj,
                                   blocks=block, filter=self.decomp_type,
                                   bands_vals=self.custom_bands)
            # configure & start thread
            thread = Thread(target=program.run)
            thread.start()
            # block until ready
            ready.wait()

        self.accept()

    def out_cancel(self):
        self.data_exists = False
        self.decomp_type = None
        self.custom_bands = None
        self.close()


class ChildProgram:
    def __init__(self, ready, path, subject, blocks, filter, bands_vals):
        self.ready = ready
        self.fpath = path
        self.subject = subject
        self.blocks = blocks
        self.filter = filter
        self.bands_vals = bands_vals

    def run(self):
        preprocess_data(path=self.fpath,
                      subject=self.subject,
                      blocks=self.blocks,
                      filter=self.filter,
                      bands_vals=self.bands_vals)
        # then fire the ready event
        self.ready.set()



# Creates Periodogram dialog ---------------------------------------------------
class PeriodogramDialog(QtGui.QDialog):
    def __init__(self, model, x, y):
        super().__init__()

        self.model = model
        self.x = x
        self.y = y
        self.relative_index = np.argmin(np.abs(self.model.scaleVec-self.y))
        self.chosen_channel = model.selectedChannels[self.relative_index]
        self.BIs = model.IntRects2

        self.fig1 = pg.PlotWidget()               #uppper periodogram plot
        self.fig2 = pg.PlotWidget()               #lower voltage plot
        self.fig1.setBackground('w')
        self.fig2.setBackground('w')

        grid = QGridLayout() #QVBoxLayout()
        grid.setSpacing(0.0)
        grid.setRowStretch(0, 2)
        grid.setRowStretch(1, 1)
        grid.addWidget(self.fig1)
        grid.addWidget(self.fig2)

        self.setLayout(grid)
        self.setWindowTitle('Periodogram')

        # Draw plots -----------------------------------------------------------
        startSamp = self.model.intervalStartSamples
        endSamp = self.model.intervalEndSamples

        # Upper Panel: Periodogram plot ----------------------------------------
        spectrogram = model.nwb.modules['ecephys'].data_interfaces['Bandpower_default'].data
        periodogram = np.mean(spectrogram[startSamp - 1 : endSamp, self.chosen_channel, :], 0)
        bands_centers = model.nwb.modules['ecephys'].data_interfaces['Bandpower_default'].bands['filter_param_0'][:]
        plt1 = self.fig1   # Lower voltage plot
        plt1.clear()       # Clear plot
        plt1.setLabel('bottom', 'Band center', units = 'Hz')
        plt1.setLabel('left', 'Average power', units = 'V**2/Hz')
        plt1.setTitle('Channel #'+str(self.chosen_channel+1))
        plt1.plot(bands_centers, periodogram, pen='k', width=1)

        # Lower Panel: Voltage time series plot --------------------------------
        try:
            plotVoltage = self.model.plotData[startSamp - 1 : endSamp, self.chosen_channel]
        except:  #if time segment shorter than window.
            plotVoltage = self.model.plotData[:, self.chosen_channel]

        timebaseGuiUnits = np.arange(startSamp - 1, endSamp) * (self.model.intervalStartGuiUnits/self.model.intervalStartSamples)
        plt2 = self.fig2   # Lower voltage plot
        plt2.clear()       # Clear plot
        plt2.setLabel('bottom', 'Time', units='sec')
        plt2.setLabel('left', 'Signal', units='Volts')
        plt2.plot(timebaseGuiUnits, np.zeros(len(timebaseGuiUnits)), pen='k', width=.8)
        if self.chosen_channel in self.model.badChannels:
            plt2.plot(timebaseGuiUnits, plotVoltage, pen='r', width=.8, alpha=.3)
        else:
            plt2.plot(timebaseGuiUnits, plotVoltage, pen='b', width=1)
        plt2.setXRange(timebaseGuiUnits[0], timebaseGuiUnits[-1], padding=0.003)
        yrange = 3*np.std(plotVoltage)
        plt2.setYRange(-yrange, yrange, padding = 0.06)

        # Make red box around bad time segments
        for i in model.IntRects2:
            x = i.rect().left()
            w = i.rect().width()
            c = pg.QtGui.QGraphicsRectItem(x, -1, w, 2)
            bc = [250, 0, 0, 100]
            c.setPen(pg.mkPen(color=QtGui.QColor(bc[0], bc[1], bc[2], 255)))
            c.setBrush(QtGui.QColor(bc[0], bc[1], bc[2], bc[3]))
            plt2.addItem(c)

        self.exec_()
