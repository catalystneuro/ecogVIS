from PyQt5 import QtGui, QtCore, uic
from PyQt5.QtWidgets import (QTableWidgetItem, QGridLayout, QGroupBox, QLineEdit,
                             QWidget, QLabel, QPushButton, QVBoxLayout, QHBoxLayout,
                             QComboBox, QScrollArea, QFileDialog, QHeaderView,
                             QMainWindow, QCheckBox)
import pyqtgraph as pg
import pyqtgraph.opengl as gl
from PyQt5 import QtGui, QtCore, uic
from PyQt5.QtWidgets import (QTableWidgetItem, QGridLayout, QGroupBox,
                             QLineEdit,
                             QWidget, QLabel, QPushButton, QVBoxLayout,
                             QHBoxLayout, QComboBox, QScrollArea,
                             QFileDialog, QHeaderView, QMainWindow, QCheckBox)
from ecogvis.signal_processing import bands as default_bands
from ecogvis.signal_processing.processing_data import processing_data
from ecogvis.signal_processing.periodogram import psd_estimate
from .FS_colorLUT import get_lut

import numpy as np
import os


# Path where UI files are
ui_path = os.path.join(os.path.dirname(__file__), '..', 'ui')


# Creates custom interval type -------------------------------------------------
Ui_CustomInterval, _ = uic.loadUiType(os.path.join(ui_path, "intervals_gui.ui"))
class CustomIntervalDialog(QtGui.QDialog, Ui_CustomInterval):
    def __init__(self):
        super().__init__()
        self.setupUi(self)

    def getResults(self):
        if self.exec_() == QtGui.QDialog.Accepted:
            # get all values
            int_type = str(self.lineEdit_1.text())
            color = str(self.comboBox.currentText())
            return int_type, color
        else:
            return '', ''


# Warning of no High gamma data in the NWB file ------------ -----------------
class NoHighGammaDialog(QtGui.QDialog):
    def __init__(self):
        super().__init__()
        self.text = QLabel("There is no high gamma data in the current NWB file.\n"
                           "To calculate high gamma power traces, use button:\n"
                           "High Gamma")
        self.okButton = QtGui.QPushButton("OK")
        self.okButton.clicked.connect(self.onAccepted)
        vbox = QtGui.QVBoxLayout()
        vbox.addWidget(self.text)
        vbox.addWidget(self.okButton)
        self.setLayout(vbox)
        self.setWindowTitle('No high gama data')
        self.exec_()

    def onAccepted(self):
        self.accept()


# Warning of no High gamma data in the NWB file ------------------------------
class NoPreprocessedDialog(QtGui.QDialog):
    def __init__(self):
        super().__init__()
        self.text = QLabel("There is no preprocessed data in the current NWB file.\n"
                           "To generate preprocessed voltage traces, use button:\n"
                           "Preprocess")
        self.okButton = QtGui.QPushButton("OK")
        self.okButton.clicked.connect(self.onAccepted)
        vbox = QtGui.QVBoxLayout()
        vbox.addWidget(self.text)
        vbox.addWidget(self.okButton)
        self.setLayout(vbox)
        self.setWindowTitle('No preprocessed data')
        self.exec_()

    def onAccepted(self):
        self.accept()


# Warning of no Raw data in the NWB file --------------------------------
class NoRawDialog(QtGui.QDialog):
    def __init__(self):
        super().__init__()
        self.text = QLabel("There is no raw data in the current NWB file.")
        self.okButton = QtGui.QPushButton("OK")
        self.okButton.clicked.connect(self.onAccepted)
        vbox = QtGui.QVBoxLayout()
        vbox.addWidget(self.text)
        vbox.addWidget(self.okButton)
        self.setLayout(vbox)
        self.setWindowTitle('No raw data')
        self.exec_()

    def onAccepted(self):
        self.accept()


# Warning of no Trials data in the NWB file ----------------------------------
class NoTrialsDialog(QtGui.QDialog):
    def __init__(self):
        super().__init__()
        self.text = QLabel("There is no trials data in the current NWB file.\n"
                           "Trial times are needed to generate ERP.")
        self.okButton = QtGui.QPushButton("OK")
        self.okButton.clicked.connect(self.onAccepted)
        vbox = QtGui.QVBoxLayout()
        vbox.addWidget(self.text)
        vbox.addWidget(self.okButton)
        self.setLayout(vbox)
        self.setWindowTitle('No trial data')
        self.exec_()

    def onAccepted(self):
        self.accept()


# Warning that Trials data already exists in the NWB file --------------------
class ExistIntervalsDialog(QtGui.QDialog):
    def __init__(self):
        super().__init__()
        self.text = QLabel("Speaker intervals data already exists in the current NWB file.\n"
                           "It is not possible to substitute it.")
        self.okButton = QtGui.QPushButton("OK")
        self.okButton.clicked.connect(self.onAccepted)
        vbox = QtGui.QVBoxLayout()
        vbox.addWidget(self.text)
        vbox.addWidget(self.okButton)
        self.setLayout(vbox)
        self.setWindowTitle('Speaker intervals already exist')
        self.exec_()

    def onAccepted(self):
        self.accept()


# Warning of no Audio data in the NWB file -----------------------------------
class NoAudioDialog(QtGui.QDialog):
    def __init__(self):
        super().__init__()
        self.text = QLabel("There is no audio data in the current NWB file.")
        self.okButton = QtGui.QPushButton("OK")
        self.okButton.clicked.connect(self.onAccepted)
        vbox = QtGui.QVBoxLayout()
        vbox.addWidget(self.text)
        vbox.addWidget(self.okButton)
        self.setLayout(vbox)
        self.setWindowTitle('No audio data')
        self.exec_()

    def onAccepted(self):
        self.accept()


# Warning of no Spectrum data in the NWB file --------------------------------
class NoSpectrumDialog(QtGui.QDialog):
    def __init__(self, parent, type):
        super().__init__()
        self.parent = parent
        self.type = type
        self.val = -1
        self.text = QLabel("There is no Spectrum data for " + self.type + " data in the current NWB file.\n"
                           "To calculate the Power Spectral Density, click Calculate.")
        self.cancelButton = QtGui.QPushButton("Cancel")
        self.cancelButton.clicked.connect(lambda: self.out_close(val=-1))
        self.calculateButton = QtGui.QPushButton("Calculate")
        self.calculateButton.clicked.connect(self.run_estimation)
        hbox = QtGui.QHBoxLayout()
        hbox.addWidget(self.cancelButton)
        hbox.addWidget(self.calculateButton)
        vbox = QtGui.QVBoxLayout()
        vbox.addWidget(self.text)
        vbox.addLayout(hbox)
        self.setLayout(vbox)
        self.setWindowTitle('No Spectrum data')
        self.exec_()

    def run_estimation(self):
        self.text.setText("Calculating the Power Spectral Density for " + self.type + " data.\n"
                          "Please wait, this might take around 5 minutes.")
        self.cancelButton.setEnabled(False)
        self.calculateButton.setEnabled(False)
        self.thread = PSDCalcFunction(self)
        self.thread.finished.connect(lambda: self.out_close(val=1))
        self.thread.start()

    def out_close(self, val):
        self.val = val
        self.accept()


# Runs 'psd_estimate' function, useful to wait for thread -------------------
class PSDCalcFunction(QtCore.QThread):
    def __init__(self, parent):
        super().__init__()
        self.parent = parent
        self.data = parent.parent.model.source
        self.src_file = parent.parent.file
        self.type = parent.type   # 'raw' or 'preprocessed'

    def run(self):
        psd_estimate(src_file=self.src_file,
                     type=self.type)


# Exit confirmation ------------------------------------------------------------
Ui_Exit, _ = uic.loadUiType(os.path.join(ui_path, "exit_gui.ui"))
class ExitDialog(QtGui.QDialog, Ui_Exit):
    def __init__(self, parent):
        super().__init__()
        self.setupUi(self)

        self.pushButton_1.setEnabled(False)
        self.pushButton_1.clicked.connect(self.save)
        self.pushButton_2.clicked.connect(self.cancel)
        self.pushButton_3.clicked.connect(self.exit)

        if parent.model.unsaved_changes_annotation or parent.model.unsaved_changes_interval:
            text = "There are unsaved changes in this session.\n" + \
                   "Do you want to save them before exit?"
            self.label.setText(text)
            self.pushButton_1.setEnabled(True)

        self.setWindowTitle('Exit ecogVIS')
        self.exec_()

    def save(self):
        self.value = 1
        self.accept()

    def cancel(self):
        self.value = 0
        self.accept()

    def exit(self):
        self.value = -1
        self.accept()


# Selects channels from specific brain regions to be plotted -----------------
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
        # vbox.addStretch(1)
        vbox.addLayout(hbox)

        self.setLayout(vbox)
        # self.setLayout(layout)
        self.setWindowTitle('Select Regions:')

        self.okButton.clicked.connect(self.onAccepted)
        self.selectButton.clicked.connect(self.select_all)
        self.unselectButton.clicked.connect(self.unselect_all)

        self.select_all()
        self.choices = [self.model.item(i).text() for i in range(self.model.rowCount())
                        if self.model.item(i).checkState() == QtCore.Qt.Checked]
        self.exec_()

    def onAccepted(self):
        self.choices = [self.model.item(i).text() for i in range(self.model.rowCount())
                        if self.model.item(i).checkState() == QtCore.Qt.Checked]
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
Ui_SpectralChoice, _ = uic.loadUiType(os.path.join(ui_path, "spectral_choice_gui.ui"))
class SpectralChoiceDialog(QtGui.QDialog, Ui_SpectralChoice):
    def __init__(self, parent):
        super().__init__()
        self.setupUi(self)
        self.nwb = parent.model.nwb
        self.fpath = parent.model.pathName
        self.fname = parent.model.fileName
        self.chosen_bands = None    # Values for custom filter bands (user input)
        self.value = -1             # Reference value for user pressed exit button
        self.radioButton_1.clicked.connect(self.choice_default)
        self.radioButton_2.clicked.connect(self.choice_custom)
        self.pushButton_1.clicked.connect(self.add_band)
        self.pushButton_2.clicked.connect(self.del_band)
        self.runButton.clicked.connect(self.run_decomposition)
        self.cancelButton.clicked.connect(lambda: self.out_close(val=-1))

        if 'ecephys' in parent.model.nwb.processing:
            # If there's no preprocessed data in NWB file
            if 'LFP' not in parent.model.nwb.processing[
                'ecephys'].data_interfaces:
                self.disable_all()
                text = "There's no preprocessed data in the current file.\n" \
                       "Run 'Preprocess' to generate it."
                self.label_1.setText(text)
                self.cancelButton.setEnabled(True)
            # If there's already Bandpower data in NWB file
            if 'DecompositionSeries' in self.nwb.processing[
                'ecephys'].data_interfaces:
                self.disable_all()
                text = "Frequency decomposition data already exists in " \
                       "current file."
                self.label_1.setText(text)
                self.cancelButton.setEnabled(True)
        else:
            self.disable_all()
            text = "There's no preprocessed data in the current file.\n" \
                   "Run 'Preprocess' to generate it."
            self.label_1.setText(text)
            self.cancelButton.setEnabled(True)

        self.setWindowTitle('Spectral decomposition')
        self.exec_()

    def choice_default(self):  # default chosen
        self.pushButton_1.setEnabled(False)
        self.pushButton_2.setEnabled(False)
        self.tableWidget.setEditTriggers(
            QtGui.QAbstractItemView.NoEditTriggers)
        text = "Spectral decomposition data does not exist in current " \
               "file.\n" \
               "It can be created from the bands shown in the table. " \
               "The results will be saved in the current NWB file.\nDo you " \
               "want to create it?"
        self.label_1.setText(text)
        self.runButton.setEnabled(True)
        # Populate table with values
        self.tableWidget.setHorizontalHeaderLabels(['center [Hz]', 'sigma [Hz]'])
        p0 = default_bands.chang_lab['cfs']
        p1 = default_bands.chang_lab['sds']
        self.tableWidget.setRowCount(len(p0))
        for i in np.arange(len(p0)):
            self.tableWidget.setItem(i, 0, QTableWidgetItem(str(round(p0[i], 1))))
            self.tableWidget.setItem(i, 1, QTableWidgetItem(str(round(p1[i], 1))))

    def choice_custom(self):  # default chosen
        text = "Spectral decomposition data does not exist in current " \
               "file.\n" \
               "To create it, add the bands of interest to the table. " \
               "The results will be saved in the current NWB file.\nDo you " \
               "want to create it?"
        self.label_1.setText(text)
        self.runButton.setEnabled(True)
        # Allows user to populate table with values
        self.tableWidget.setRowCount(1)
        self.tableWidget.setHorizontalHeaderLabels(['center [Hz]', 'sigma [Hz]'])
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
        self.tableWidget.removeRow(nRows - 1)

    def run_decomposition(self):
        self.disable_all()
        nRows = self.tableWidget.rowCount()
        self.chosen_bands = np.zeros((2, nRows))
        for i in np.arange(nRows):   # read bands from table
            self.chosen_bands[0, i] = float(self.tableWidget.item(i, 0).text())
            self.chosen_bands[1, i] = float(self.tableWidget.item(i, 1).text())
        self.label_1.setText('Processing spectral decomposition.\nPlease wait...')
        subj, aux = self.fname.split('_')
        block = [aux.split('.')[0][1:]]
        self.thread = ProcessingDataFunction(
            path=self.fpath,
            subject=subj,
            blocks=block,
            mode='decomposition',
            config=self.chosen_bands
        )
        self.thread.finished.connect(lambda: self.out_close(val=1))
        self.thread.start()

    def disable_all(self):
        self.pushButton_1.setEnabled(False)
        self.pushButton_2.setEnabled(False)
        self.tableWidget.setEnabled(False)
        self.groupBox.setEnabled(False)
        self.runButton.setEnabled(False)
        self.cancelButton.setEnabled(False)

    def out_close(self, val):
        self.value = val
        self.accept()


# Runs 'processing_data' function, useful to wait for thread -------------------
class ProcessingDataFunction(QtCore.QThread):
    def __init__(self, path, subject, blocks, mode, config, new_file=''):
        super().__init__()
        self.fpath = path
        self.subject = subject
        self.blocks = blocks
        self.mode = mode
        self.config = config
        self.new_fname = new_file

    def run(self):
        processing_data(path=self.fpath,
                        subject=self.subject,
                        blocks=self.blocks,
                        mode=self.mode,
                        config=self.config,
                        new_file=self.new_fname)


# Creates High Gamma dialog ----------------------------------------------------
Ui_HighGamma, _ = uic.loadUiType(os.path.join(ui_path, "high_gamma_gui.ui"))
class HighGammaDialog(QtGui.QDialog, Ui_HighGamma):
    def __init__(self, parent):
        super().__init__()
        self.setupUi(self)
        self.parent = parent
        self.nwb = parent.model.nwb
        self.fpath = parent.model.pathName
        self.fname = parent.model.fileName
        self.chosen_bands = None    # Values for custom filter bands (user input)
        self.value = -1             # Reference value for user pressed exit button'
        self.new_fname = ''

        self.radioButton_1.setChecked(True)
        self.radioButton_3.setChecked(True)
        self.lineEdit.setEnabled(False)
        self.radioButton_1.clicked.connect(self.choice_default)
        self.radioButton_2.clicked.connect(self.choice_custom)
        self.radioButton_3.clicked.connect(lambda: self.choose_file(0))
        self.radioButton_4.clicked.connect(lambda: self.choose_file(1))
        self.pushButton_1.clicked.connect(self.add_band)
        self.pushButton_2.clicked.connect(self.del_band)
        self.runButton.clicked.connect(self.run)
        self.cancelButton.clicked.connect(lambda: self.out_close(val=-1))

        self.check_hg_exists()
        self.setWindowTitle('High Gamma power estimation')
        self.exec_()

    def check_hg_exists(self):
        if 'ecephys' in self.parent.model.nwb.processing:
            # If there's no preprocessed data in NWB file
            if 'LFP' not in self.parent.model.nwb.processing[
                'ecephys'].data_interfaces:
                self.disable_all()
                text = "There's no preprocessed data in the current file.\n" \
                       "Run 'Preprocess' to generate it."
                self.label_1.setText(text)
                self.radioButton_4.setEnabled(False)
                self.cancelButton.setEnabled(True)
            # If there's already Bandpower data in NWB file
            elif 'high_gamma' in self.nwb.processing[
                'ecephys'].data_interfaces:
                self.disable_all()
                text = "High Gamma data already exists in current file."
                self.label_1.setText(text)
                self.cancelButton.setEnabled(True)
            # If preprocessed data exists and Bandpower data does nt exist
            else:
                self.radioButton_1.setChecked(True)
                self.choice_default()
        else:
            self.disable_all()
            text = "There's no preprocessed data in the current file.\n" \
                   "Run 'Preprocess' to generate it."
            self.label_1.setText(text)
            self.radioButton_4.setEnabled(False)
            self.cancelButton.setEnabled(True)

    def choose_file(self, flag):
        if flag == 0:  # save in current NWB file
            self.nwb = self.parent.model.nwb
            self.lineEdit.setEnabled(False)
            self.new_fname = ''
            self.check_hg_exists()
        elif flag == 1:  # save in new NWB file
            part0, part1 = self.fname.split('.')
            default_path_name = os.path.join(self.fpath, part0 + '_hg.' + part1)
            filename, _ = QFileDialog.getSaveFileName(self, 'New file', default_path_name, "(*.nwb)")
            self.lineEdit.setEnabled(True)
            self.lineEdit.setText(filename)
            self.new_fname = filename
            self.enable_all()
            self.radioButton_1.setChecked(True)
            self.choice_default()

    def disable_all(self):
        self.lineEdit.setEnabled(False)
        self.groupBox_1.setEnabled(False)
        self.tableWidget.setEnabled(False)
        self.pushButton_1.setEnabled(False)
        self.pushButton_2.setEnabled(False)
        self.runButton.setEnabled(False)

    def enable_all(self):
        self.lineEdit.setEnabled(True)
        self.groupBox_1.setEnabled(True)
        self.tableWidget.setEnabled(True)
        self.pushButton_1.setEnabled(True)
        self.pushButton_2.setEnabled(True)
        self.runButton.setEnabled(True)

    def choice_default(self):  # default chosen
        self.pushButton_1.setEnabled(False)
        self.pushButton_2.setEnabled(False)
        self.tableWidget.setEditTriggers(
            QtGui.QAbstractItemView.NoEditTriggers)
        text = "'High gamma' power data can be created from the averaged " \
               "power " \
               "of the bands shown in the table. " \
               "The results will be saved in the chosen NWB file.\nDo you " \
               "want to create it?"
        self.label_1.setText(text)
        self.runButton.setEnabled(True)
        # Populate table with values
        self.tableWidget.setHorizontalHeaderLabels(['', 'center [Hz]', 'sigma [Hz]'])
        self.tableWidget.setColumnWidth(0, 14)
        self.tableWidget.horizontalHeader().setSectionResizeMode(0,
                                                                 QHeaderView.ResizeToContents)
        self.tableWidget.setFocusPolicy(QtCore.Qt.NoFocus)
        self.tableWidget.setSelectionMode(QtGui.QAbstractItemView.NoSelection)
        p0 = default_bands.chang_lab['cfs'][29:]
        p1 = default_bands.chang_lab['sds'][29:]
        self.tableWidget.setRowCount(len(p0))
        for i in np.arange(len(p0)):
            cell_widget = QWidget()
            chk_bx = QtGui.QCheckBox()
            chk_bx.setMaximumWidth(14)
            if i < 8:
                chk_bx.setChecked(True)
            else:
                chk_bx.setChecked(False)
            self.tableWidget.setCellWidget(i, 0, chk_bx)
            self.tableWidget.setItem(i, 1, QTableWidgetItem(str(round(p0[i], 1))))
            self.tableWidget.setItem(i, 2, QTableWidgetItem(str(round(p1[i], 1))))
            self.tableWidget.item(i, 1).setTextAlignment(QtCore.Qt.AlignRight | QtCore.Qt.AlignVCenter)
            self.tableWidget.item(i, 2).setTextAlignment(QtCore.Qt.AlignRight | QtCore.Qt.AlignVCenter)

    def choice_custom(self):  # default chosen
        self.pushButton_1.setEnabled(False)
        self.pushButton_2.setEnabled(False)
        self.tableWidget.setEditTriggers(
            QtGui.QAbstractItemView.NoEditTriggers)
        text = "'High gamma' power data can be created from the averaged " \
               "power " \
               "of the bands shown in the table. " \
               "The results will be saved in the chosen NWB file.\nDo you " \
               "want to create it?"
        self.label_1.setText(text)
        self.runButton.setEnabled(True)
        # Populate table with values
        self.tableWidget.setHorizontalHeaderLabels(['', 'center [Hz]', 'sigma [Hz]'])
        self.tableWidget.setColumnWidth(0, 14)
        self.tableWidget.horizontalHeader().setSectionResizeMode(0,
                                                                 QHeaderView.ResizeToContents)
        self.tableWidget.setFocusPolicy(QtCore.Qt.NoFocus)
        self.tableWidget.setSelectionMode(QtGui.QAbstractItemView.NoSelection)
        p0 = default_bands.chang_lab['cfs'][29:]
        p1 = default_bands.chang_lab['sds'][29:]
        self.tableWidget.setRowCount(len(p0))
        for i in np.arange(len(p0)):
            cell_widget = QWidget()
            chk_bx = QtGui.QCheckBox()
            chk_bx.setChecked(True)
            chk_bx.setMaximumWidth(14)
            self.tableWidget.setCellWidget(i, 0, chk_bx)
            self.tableWidget.setItem(i, 1, QTableWidgetItem(str(round(p0[i], 1))))
            self.tableWidget.setItem(i, 2, QTableWidgetItem(str(round(p1[i], 1))))
            self.tableWidget.item(i, 1).setTextAlignment(QtCore.Qt.AlignRight | QtCore.Qt.AlignVCenter)
            self.tableWidget.item(i, 2).setTextAlignment(QtCore.Qt.AlignRight | QtCore.Qt.AlignVCenter)
        # Allows user to populate table with values
        self.tableWidget.setEditTriggers(QtGui.QAbstractItemView.DoubleClicked)
        self.pushButton_1.setEnabled(True)
        self.pushButton_2.setEnabled(True)

    def add_band(self):
        nRows = self.tableWidget.rowCount()
        self.tableWidget.insertRow(nRows)
        cell_widget = QWidget()
        chk_bx = QtGui.QCheckBox()
        chk_bx.setChecked(True)
        chk_bx.setMaximumWidth(14)
        self.tableWidget.setCellWidget(nRows, 0, chk_bx)
        self.tableWidget.setItem(nRows, 1, QTableWidgetItem(str(0)))
        self.tableWidget.setItem(nRows, 2, QTableWidgetItem(str(0)))
        self.tableWidget.item(nRows, 1).setTextAlignment(
            QtCore.Qt.AlignRight | QtCore.Qt.AlignVCenter)
        self.tableWidget.item(nRows, 2).setTextAlignment(
            QtCore.Qt.AlignRight | QtCore.Qt.AlignVCenter)

    def del_band(self):
        nRows = self.tableWidget.rowCount()
        self.tableWidget.removeRow(nRows - 1)

    def run(self):
        self.chosen_bands = np.zeros((2, 0))
        nRows = self.tableWidget.rowCount()
        for i in np.arange(nRows):
            if self.tableWidget.cellWidget(i, 0).isChecked():
                val0 = float(self.tableWidget.item(i, 1).text())
                val1 = float(self.tableWidget.item(i, 2).text())
                self.chosen_bands = np.append(self.chosen_bands, np.array([[val0], [val1]]), axis=1)
        # If Decomposition data does not exist in NWB file and user decides to create it
        self.label_1.setText('Processing High Gamma power estimation. \nPlease wait...')
        self.pushButton_1.setEnabled(False)
        self.pushButton_2.setEnabled(False)
        self.tableWidget.setEnabled(False)
        self.groupBox_1.setEnabled(False)
        self.groupBox_2.setEnabled(False)
        self.runButton.setEnabled(False)
        self.cancelButton.setEnabled(False)
        subj, aux = self.fname.split('_')
        block = [aux.split('.')[0][1:]]
        self.thread = ProcessingDataFunction(
            path=self.fpath,
            subject=subj,
            blocks=block,
            mode='high_gamma',
            config=self.chosen_bands,
            new_file=self.new_fname
        )
        self.thread.finished.connect(lambda: self.out_close(1))
        self.thread.start()

    def out_close(self, val):
        """When out of this function, the current file will be refreshed or the
        newly created will be opened"""
        self.value = val
        if self.new_fname == '':
            self.new_fname = os.path.join(self.fpath, self.fname)
        self.accept()


# Creates preprocessing dialog -------------------------------------------------
Ui_Preprocessing, _ = uic.loadUiType(os.path.join(ui_path, "preprocessing_gui.ui"))
class PreprocessingDialog(QtGui.QDialog, Ui_Preprocessing):
    def __init__(self, parent):
        super().__init__()
        self.setupUi(self)
        self.value = -1

        self.checkBox_1.setChecked(True)
        self.checkBox_2.setChecked(True)
        self.checkBox_3.setChecked(True)
        self.lineEdit_1.setText('16')
        self.lineEdit_2.setText('60')
        self.lineEdit_3.setText('400')
        self.pushButton_1.clicked.connect(lambda: self.out_close(-1))
        self.pushButton_2.clicked.connect(self.ok)
        self.fname = parent.model.fileName
        self.fpath = parent.model.pathName
        # if preprocessed signals already exist on NWB file
        if 'ecephys' in parent.model.nwb.processing:
            if 'LFP' in parent.model.nwb.processing['ecephys'].data_interfaces:
                self.disable_all()
                aux = parent.model.nwb.processing['ecephys'].data_interfaces[
                    'LFP'].electrical_series['preprocessed']
                car, notch, downs = aux.comments.split(',')
                _, car = car.split(':')
                _, notch = notch.split(':')
                _, downs = downs.split(':')
                if car == 'None':
                    self.checkBox_1.setChecked(False)
                self.lineEdit_1.setText(car)
                if notch == 'None':
                    self.checkBox_2.setChecked(False)
                self.lineEdit_2.setText(notch)
                if downs == 'No':
                    self.checkBox_3.setChecked(False)
                self.lineEdit_3.setText(str(aux.rate))
                self.pushButton_1.setEnabled(True)
                self.label_2.setText('Preprocessed data already exists in file,'
                                     ' with the parameters shown above.')

        self.setWindowTitle('Preprocessing ')
        self.exec_()

    def ok(self):
        self.disable_all()
        self.label_2.setText('Preprocessing ECoG signals.\nPlease wait...')
        config = {}
        if self.checkBox_1.isChecked():
            config['referencing'] = ('CAR', int(self.lineEdit_1.text()))
        else:
            config['referencing'] = None
        if self.checkBox_2.isChecked():
            config['Notch'] = float(self.lineEdit_2.text())
        else:
            config['Notch'] = None
        if self.checkBox_3.isChecked():
            config['Downsample'] = float(self.lineEdit_3.text())
        else:
            config['Downsample'] = None
        subj, aux = self.fname.split('_')
        block = [aux.split('.')[0][1:]]
        self.thread = ProcessingDataFunction(
            path=self.fpath,
            subject=subj,
            blocks=block,
            mode='preprocess',
            config=config
        )
        self.thread.finished.connect(lambda: self.out_close(1))
        self.thread.start()

    def out_close(self, val):
        self.value = val
        self.accept()

    def disable_all(self):
        self.label_1.setEnabled(False)
        self.checkBox_1.setEnabled(False)
        self.checkBox_2.setEnabled(False)
        self.checkBox_3.setEnabled(False)
        self.lineEdit_1.setEnabled(False)
        self.lineEdit_2.setEnabled(False)
        self.lineEdit_3.setEnabled(False)
        self.pushButton_1.setEnabled(False)
        self.pushButton_2.setEnabled(False)


# Creates Periodogram Grid window --------------------------------------------
class PeriodogramGridDialog(QMainWindow):
    def __init__(self, parent):
        super().__init__()
        self.setWindowTitle('Periodograms')
        self.resize(1250, 500)

        self.parent = parent
        self.nCols = 16
        self.grid_order = np.arange(256)
        self.parent = parent
        self.freqMax = 200.
        self.transparent = []
        self.Ymax = {}

        # Left panel
        self.push0_0 = QPushButton('Draw')
        self.push0_0.clicked.connect(self.set_elec_group)
        qlabelSignal = QLabel('Signal:')
        self.combo0 = QComboBox()
        self.initiate_sources()
        self.combo0.activated.connect(self.change_source)
        qlabelGroup = QLabel('Group:')
        self.combo1 = QComboBox()
        self.find_groups()
        self.combo1.activated.connect(self.set_elec_group)
        qlabelMethod = QLabel('Method:')
        self.b1 = QCheckBox("FFT")
        self.b1.setChecked(True)
        self.b2 = QCheckBox("Welch")
        self.b2.setChecked(True)
        qlabelYscale = QLabel('Y scale:')
        self.qline1 = QLineEdit('1')
        self.qline1.returnPressed.connect(self.scale_plots)
        qlabelXrng = QLabel('X range:')
        self.qline2_0 = QLineEdit('0')
        self.qline2_0.returnPressed.connect(self.set_xrange)
        self.qline2_1 = QLineEdit('200')
        self.qline2_1.returnPressed.connect(self.set_xrange)
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

        grid0 = QGridLayout()
        grid0.addWidget(qlabelSignal, 0, 0, 1, 2)
        grid0.addWidget(self.combo0, 0, 2, 1, 4)
        grid0.addWidget(qlabelGroup, 1, 0, 1, 2)
        grid0.addWidget(self.combo1, 1, 2, 1, 4)
        grid0.addWidget(qlabelMethod, 2, 0, 1, 2)
        grid0.addWidget(self.b1, 2, 2, 1, 4)
        grid0.addWidget(QLabel(' '), 3, 0, 1, 2)
        grid0.addWidget(self.b2, 3, 2, 1, 4)
        grid0.addWidget(qlabelYscale, 4, 0, 1, 2)
        grid0.addWidget(self.qline1, 4, 2, 1, 2)
        grid0.addWidget(qlabelXrng, 5, 0, 1, 2)
        grid0.addWidget(self.qline2_0, 5, 2, 1, 2)
        grid0.addWidget(self.qline2_1, 5, 4, 1, 2)
        grid0.addWidget(QHLine(), 13, 0, 1, 6)
        grid0.addWidget(label4, 14, 0, 1, 6)
        grid0.addWidget(self.push5_0, 15, 0, 1, 2)
        grid0.addWidget(self.push5_1, 15, 2, 1, 2)
        grid0.addWidget(self.push5_2, 15, 4, 1, 2)
        grid0.addWidget(label5, 16, 0, 1, 6)
        grid0.addWidget(self.push5_3, 17, 0, 1, 2)
        grid0.addWidget(self.push5_4, 17, 2, 1, 2)
        grid0.addWidget(self.push5_5, 17, 4, 1, 2)
        grid0.addWidget(QHLine(), 18, 0, 1, 6)
        grid0.addWidget(self.push3_0, 19, 0, 1, 6)
        grid0.addWidget(self.push4_0, 20, 0, 1, 6)
        grid0.setAlignment(QtCore.Qt.AlignTop)

        panel0 = QGroupBox('Controls:')
        panel0.setFixedWidth(180)
        panel0.setLayout(grid0)

        self.leftbox = QVBoxLayout()
        self.leftbox.addWidget(self.push0_0)
        self.leftbox.addWidget(panel0)

        self.push3_0.setEnabled(False)
        self.push4_0.setEnabled(False)
        self.push5_0.setEnabled(False)
        self.push5_1.setEnabled(False)
        self.push5_2.setEnabled(False)
        self.push5_0.setEnabled(False)
        self.push5_1.setEnabled(False)
        self.push5_2.setEnabled(False)

        # Right panel
        self.win = pg.GraphicsLayoutWidget()
        item_width = 80
        self.win.resize(item_width * 16 + 60, item_width * 16 + 60)
        background_color = self.palette().color(QtGui.QPalette.Background)
        self.win.setBackground(background_color)
        # this is to avoid the error:
        # RuntimeError: wrapped C/C++ object of type GraphicsScene has been deleted
        vb = CustomViewBoxPeriodogram(self, 0)
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

    def initiate_sources(self):
        """Check sources available on file, 'raw' and 'preprocessed'."""
        # Populate combo box
        if 'Spectrum_fft_raw' in self.parent.model.nwb.modules['ecephys'].data_interfaces:
            self.combo0.addItem('raw')
        if 'Spectrum_fft_preprocessed' in self.parent.model.nwb.modules[
            'ecephys'].data_interfaces:
            self.combo0.addItem('preprocessed')
        self.change_source()

    def change_source(self):
        if self.combo0.currentText() == 'raw':
            # PSD shape: ('frequency', 'channel')
            self.psd_fft = self.parent.model.nwb.processing['ecephys'].data_interfaces['Spectrum_fft_raw'].power
            self.xf_fft = self.parent.model.nwb.processing['ecephys'].data_interfaces['Spectrum_fft_raw'].frequencies[:]
            self.psd_welch = self.parent.model.nwb.processing['ecephys'].data_interfaces['Spectrum_welch_raw'].power
            self.xf_welch = self.parent.model.nwb.processing['ecephys'].data_interfaces['Spectrum_welch_raw'].frequencies[:]
            self.electrodes = self.parent.model.nwb.processing['ecephys'].data_interfaces['Spectrum_fft_raw'].electrodes
        elif self.combo0.currentText() == 'preprocessed':
            # PSD shape: ('frequency', 'channel')
            self.psd_fft = self.parent.model.nwb.processing['ecephys'].data_interfaces['Spectrum_fft_preprocessed'].power
            self.xf_fft = self.parent.model.nwb.processing['ecephys'].data_interfaces['Spectrum_fft_preprocessed'].frequencies[:]
            self.psd_welch = self.parent.model.nwb.processing['ecephys'].data_interfaces['Spectrum_welch_preprocessed'].power
            self.xf_welch = self.parent.model.nwb.processing['ecephys'].data_interfaces['Spectrum_welch_preprocessed'].frequencies[:]
            self.electrodes = self.parent.model.nwb.processing['ecephys'].data_interfaces['Spectrum_fft_preprocessed'].electrodes

    def find_groups(self):
        """Find electrodes groups present in current file."""
        elec_groups = list(self.parent.model.nwb.electrode_groups.keys())
        for grp in elec_groups:
            self.combo1.addItem(grp)

    def set_elec_group(self):
        """Sets electrodes group to be plotted, resizes plot grid."""
        self.elec_group = self.combo1.currentText()
        self.grid_order = np.where(self.electrodes.table['group_name'].data[:] == self.elec_group)[0]
        self.nElecs = len(self.grid_order)
        self.nCols = 16
        self.nRows = int(self.nElecs / self.nCols)
        self.set_grid()
        self.draw_periodograms()

    def set_grid(self):
        # remove previous items
        for i in np.arange(16):
            for j in np.arange(16):
                it = self.win.getItem(i, j)
                if it is not None:
                    self.win.removeItem(it)
        for j in np.arange(self.nCols):
            self.win.ci.layout.setColumnFixedWidth(j, 80)
            self.win.ci.layout.setColumnSpacing(j, 3)
        for i in np.arange(self.nRows):
            self.win.ci.layout.setRowFixedHeight(i, 80)
            self.win.ci.layout.setRowSpacing(i, 3)

    def scale_plots(self):
        scale = float(self.qline1.text())
        for ind, ch in enumerate(self.grid_order):
            row = np.floor(ind / self.nCols)
            col = ind % self.nCols
            p = self.win.getItem(row=row, col=col)
            if p is None:
                return
            else:
                xrng, yrng = p.viewRange()   # list: [[xmin, xmax], [ymin, ymax]]
                ylim = scale * yrng[1]
                p.setYRange(0, ylim)

    def set_xrange(self):
        x0 = np.abs(float(self.qline2_0.text()))
        x0 = min(max(x0, 0), 200)  # hard limits
        x1 = np.abs(float(self.qline2_1.text()))
        x1 = min(max(x1, 0), 200)  # hard limits
        for ind, ch in enumerate(self.grid_order):
            row = np.floor(ind / self.nCols)
            col = ind % self.nCols
            p = self.win.getItem(row=row, col=col)
            if p is None:
                return
            else:
                p.setXRange(x0, x1)
                tks = np.linspace(x0, x1, 3).astype('int')
                ticks = list(zip(tks, [str(tks[0]), str(tks[1]), str(tks[2])]))
                bottom = p.getAxis('bottom')
                bottom.setTicks([ticks])

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
        self.grid_order = grid.flatten()  # re-arranges as 1D array
        self.draw_periodograms()

    def areas_select(self):
        # Dialog to choose channels from specific brain regions
        w = SelectChannelsDialog(self.parent.model.all_regions,
                                 self.parent.model.regions_mask)
        self.transparent = []
        for ind, ch in enumerate(self.grid_order):
            loc = self.parent.model.nwb.electrodes['location'][ch]
            if loc not in w.choices:
                self.transparent.append(ch)
        self.draw_periodograms()

    def save_image(self):
        p = self.win.getItem(row=0, col=0)
        self.win.sceneObj.contextMenuItem = p
        self.win.sceneObj.showExportDialog()

    def draw_periodograms(self):
        self.push3_0.setEnabled(True)
        self.push4_0.setEnabled(True)
        self.push5_0.setEnabled(True)
        self.push5_1.setEnabled(True)
        self.push5_2.setEnabled(True)
        self.push5_3.setEnabled(True)
        self.push5_4.setEnabled(True)
        self.push5_5.setEnabled(True)
        cmap = get_lut()
        self.set_grid()
        # X limits and ticks
        x0 = np.abs(float(self.qline2_0.text()))
        x0 = min(max(x0, 0), 200)  # hard limits
        x1 = np.abs(float(self.qline2_1.text()))
        x1 = min(max(x1, 0), 200)  # hard limits
        tks = np.linspace(x0, x1, 3).astype('int')
        ticks = list(zip(tks, [str(tks[0]), str(tks[1]), str(tks[2])]))
        for ind, ch in enumerate(self.grid_order):
            if ch in self.transparent:  # if it should be made transparent
                elem_alpha = 30
            else:
                elem_alpha = 255
            row = np.floor(ind / self.nCols)
            col = ind % self.nCols
            p = self.win.getItem(row=row, col=col)
            if p is None:
                vb = CustomViewBoxPeriodogram(self, ch)
                p = self.win.addPlot(row=row, col=col, viewBox=vb)
            p.showAxis('left', False)
            p.showAxis('bottom', True)
            # p.hideAxis('left')
            # p.hideAxis('bottom')
            p.clear()
            p.setMouseEnabled(x=False, y=False)
            p.setToolTip('Ch ' + str(ch + 1) + '\n' + str(self.parent.model.nwb.electrodes['location'][ch]))
            # Background
            loc = 'ctx-lh-' + self.parent.model.nwb.electrodes['location'][ch]
            vb = p.getViewBox()
            color = tuple(cmap[loc])
            vb.setBackgroundColor((*color, min(elem_alpha, 70)))  # append alpha to color tuple
            # Main plots
            if self.b1.isChecked():
                Yp_fft = self.psd_fft[:, ch]
                mean_fft = p.plot(x=self.xf_fft, y=Yp_fft, pen=pg.mkPen((50, 50, 50, min(elem_alpha, 255)), width=1.))
            if self.b2.isChecked():
                Yp_welch = self.psd_welch[:, ch]
                mean_welch = p.plot(x=self.xf_welch, y=Yp_welch, pen=pg.mkPen((17, 102, 0, min(elem_alpha, 255)), width=1.))
            p.hideButtons()
            # Axis control
            left = p.getAxis('left')
            left.setStyle(showValues=False)
            left.setTicks([])
            p.setXRange(x0, x1)
            bottom = p.getAxis('bottom')
            bottom.setStyle(showValues=True)
            bottom.setTicks([ticks])


# Viewbox for Periodogram plots ----------------------------------------------
class CustomViewBoxPeriodogram(pg.ViewBox):
    def __init__(self, parent, ch):
        pg.ViewBox.__init__(self)
        self.parent = parent
        self.ch = ch

    def mouseDoubleClickEvent(self, ev):
        IndividualPeriodogramDialog(self)


# Individual Event-Related Potential dialog ----------------------------------
class IndividualPeriodogramDialog(QtGui.QDialog):
    def __init__(self, parent):
        super().__init__()
        # Enable antialiasing for prettier plots
        pg.setConfigOptions(antialias=True)
        self.parent = parent
        self.ancestor = parent.parent.parent
        self.ch = parent.ch
        self.psd_fft = parent.parent.psd_fft
        self.xf_fft = parent.parent.xf_fft
        self.psd_welch = parent.parent.psd_welch
        self.xf_welch = parent.parent.xf_welch

        # Left panel
        qlabelSignal = QLabel('Signal:')
        self.combo0 = QComboBox()
        self.combo0.activated.connect(self.change_source)
        qlabelMethod = QLabel('Method:')
        self.b1 = QCheckBox("FFT")
        self.b1.setChecked(True)
        self.b1.stateChanged.connect(self.draw_periodograms)
        self.b2 = QCheckBox("Welch")
        self.b2.setChecked(True)
        self.b2.stateChanged.connect(self.draw_periodograms)

        grid0 = QGridLayout()
        grid0.addWidget(qlabelSignal, 0, 0, 1, 2)
        grid0.addWidget(self.combo0, 0, 2, 1, 4)
        grid0.addWidget(qlabelMethod, 1, 0, 1, 2)
        grid0.addWidget(self.b1, 1, 2, 1, 4)
        grid0.addWidget(QLabel(' '), 2, 0, 1, 2)
        grid0.addWidget(self.b2, 2, 2, 1, 4)
        grid0.setAlignment(QtCore.Qt.AlignTop)

        panel0 = QGroupBox('Controls:')
        panel0.setFixedWidth(180)
        panel0.setLayout(grid0)

        self.leftbox = QVBoxLayout()
        self.leftbox.addWidget(panel0)

        # Right panel
        self.win = pg.GraphicsLayoutWidget()
        self.win.resize(900, 600)
        background_color = self.palette().color(QtGui.QPalette.Background)
        self.win.setBackground(background_color)

        self.hbox = QHBoxLayout()
        # self.hbox.addWidget(panel0)
        self.hbox.addLayout(self.leftbox)
        self.hbox.addWidget(self.win)
        self.setLayout(self.hbox)
        self.setWindowTitle('Individual Periodogram - Ch ' + str(self.ch + 1))
        self.resize(900, 600)

        self.initiate_sources()
        self.draw_periodograms()
        self.exec_()

    def initiate_sources(self):
        """Check sources available on file, 'raw' and 'preprocessed'."""
        # Populate combo box
        if 'Spectrum_fft_raw' in self.ancestor.model.nwb.modules['ecephys'].data_interfaces:
            self.combo0.addItem('raw')
        if 'Spectrum_fft_preprocessed' in self.ancestor.model.nwb.modules[
            'ecephys'].data_interfaces:
            self.combo0.addItem('preprocessed')
        self.change_source()

    def change_source(self):
        if self.combo0.currentText() == 'raw':
            # PSD shape: ('frequency', 'channel')
            self.psd_fft = self.ancestor.model.nwb.modules['ecephys'].data_interfaces['Spectrum_fft_raw'].power
            self.xf_fft = self.ancestor.model.nwb.modules['ecephys'].data_interfaces['Spectrum_fft_raw'].frequencies[:]
            self.psd_welch = self.ancestor.model.nwb.modules['ecephys'].data_interfaces['Spectrum_welch_raw'].power
            self.xf_welch = self.ancestor.model.nwb.modules['ecephys'].data_interfaces['Spectrum_welch_raw'].frequencies[:]
        elif self.combo0.currentText() == 'preprocessed':
            # PSD shape: ('frequency', 'channel')
            self.psd_fft = self.ancestor.model.nwb.modules['ecephys'].data_interfaces['Spectrum_fft_preprocessed'].power
            self.xf_fft = self.ancestor.model.nwb.modules['ecephys'].data_interfaces['Spectrum_fft_preprocessed'].frequencies[:]
            self.psd_welch = self.ancestor.model.nwb.modules['ecephys'].data_interfaces['Spectrum_welch_preprocessed'].power
            self.xf_welch = self.ancestor.model.nwb.modules['ecephys'].data_interfaces['Spectrum_welch_preprocessed'].frequencies[:]
        self.draw_periodograms()

    def draw_periodograms(self):
        cmap = get_lut()
        p = self.win.getItem(row=0, col=0)
        if p is None:
            p = self.win.addPlot(row=0, col=0)
        p.hideAxis('left')
        # p.hideAxis('bottom')
        p.clear()
        # p.setMouseEnabled(x=False, y=False)
        # Background
        loc = 'ctx-lh-' + self.ancestor.model.nwb.electrodes['location'][self.ch]
        vb = p.getViewBox()
        color = tuple(cmap.get(loc, cmap['Unknown']))
        vb.setBackgroundColor((*color, 70))  # append alpha to color tuple
        # Main plots
        if self.b1.isChecked() == True:
            Yp_fft = self.psd_fft[:, self.ch]
            mean_fft = p.plot(x=self.xf_fft, y=Yp_fft,
                              pen=pg.mkPen((50, 50, 50, 255), width=1.))
        if self.b2.isChecked() == True:
            Yp_welch = self.psd_welch[:, self.ch]
            mean_welch = p.plot(x=self.xf_welch, y=Yp_welch,
                                pen=pg.mkPen((17, 112, 0, 255), width=1.))
        # p.hideButtons()
        # Axis control
        left = p.getAxis('left')
        left.setStyle(showValues=False)
        left.setTicks([])
        bottom = p.getAxis('bottom')
        bottom.setStyle(showValues=True)
        p.setLabel('bottom', 'Frequency', units='Hz')
        # ticks = list(zip([0, 100, 200], ['0', '100', '200']))
        # bottom.setTicks([ticks])
        p.setLimits(xMin=0)
        p.setLimits(xMax=200)
        # p.setLimits(yMin=0)


# Creates 3D Periodograms window --------------------------------------------
class Periodograms3D(QtGui.QDialog):
    def __init__(self, parent, psd):
        super().__init__()
        self.parent = parent
        self.psd = psd  # Power Spectral Density data
        self.nChannels = parent.model.nChTotal
        self.freqMax = 200.
        self.freqTickRes = 20
        self.chTickGrid = 5
        self.chTickSpace = self.nChannels / (self.chTickGrid - 1)
        self.transparent = []

        # Left panel
        self.push0_0 = QPushButton('Draw')
        self.push0_0.clicked.connect(self.draw_periodograms)
        self.push1_0 = QPushButton('Brain areas')
        self.push1_0.clicked.connect(self.areas_select)
        label2 = QLabel('Freq bin [Hz]:')
        self.qline2 = QLineEdit('20')
        self.qline2.returnPressed.connect(self.set_freq_bin)
        label3 = QLabel('Ch grid [#]:')
        self.qline3 = QLineEdit('5')
        self.qline3.returnPressed.connect(self.set_ch_grid)

        self.push4_0 = QPushButton('Save image')
        self.push4_0.clicked.connect(self.save_image)

        grid0 = QGridLayout()
        grid0.addWidget(label2, 0, 0, 1, 4)
        grid0.addWidget(self.qline2, 0, 4, 1, 2)
        grid0.addWidget(label3, 1, 0, 1, 4)
        grid0.addWidget(self.qline3, 1, 4, 1, 2)
        grid0.addWidget(QHLine(), 2, 0, 1, 6)
        grid0.addWidget(self.push1_0, 3, 0, 1, 6)
        grid0.addWidget(self.push4_0, 4, 0, 1, 6)
        grid0.setAlignment(QtCore.Qt.AlignTop)

        panel0 = QGroupBox('Controls:')
        panel0.setFixedWidth(180)
        panel0.setLayout(grid0)

        self.leftbox = QVBoxLayout()
        self.leftbox.addWidget(self.push0_0)
        self.leftbox.addWidget(panel0)

        # Right panel --------------------------------------------------------
        self.fig1 = CustomGLWidget(self)  # gl.GLViewWidget()
        background_color = self.palette().color(QtGui.QPalette.Background)
        self.fig1.setBackgroundColor(background_color)
        self.fig1.setToolTip('Tooltip')

        self.rightbox = QGridLayout()  # QVBoxLayout()
        self.rightbox.setSpacing(0.0)
        self.rightbox.setRowStretch(0, 2)
        # self.rightbox.setRowStretch(1, 1)
        self.rightbox.addWidget(self.fig1)

        self.hbox = QHBoxLayout()
        self.hbox.addLayout(self.leftbox)  # add panels in the left
        self.hbox.addLayout(self.rightbox)  # add plot on the right

        self.setLayout(self.hbox)
        self.setWindowTitle('Periodogram')
        self.resize(1100, 600)
        self.exec_()

    def set_freq_bin(self):
        self.freqTickRes = float(self.qline2.text())
        self.draw_periodograms()

    def set_ch_grid(self):
        self.chTickGrid = float(self.qline3.text())
        self.chTickSpace = self.nChannels / (self.chTickGrid - 1)
        self.draw_periodograms()

    def save_image(self):
        """Export image. For 3D scenes, this is still a bit limited."""
        default_path_name = self.parent.model.pathName
        filename, _ = QFileDialog.getSaveFileName(self, 'Export image',
                                                  default_path_name, "(*.png)")
        print(filename)
        self.fig1.grabFrameBuffer().save(filename + '.png')

    def areas_select(self):
        """Dialog to choose channels from specific brain regions."""
        w = SelectChannelsDialog(self.parent.model.all_regions,
                                 self.parent.model.regions_mask)
        self.transparent = []
        for ch in np.arange(self.nChannels):
            loc = self.parent.model.nwb.electrodes['location'][ch]
            if loc not in w.choices:
                self.transparent.append(ch)
        self.draw_periodograms()

    def draw_periodograms(self):
        """Draw periodograms."""
        # Cleans scene
        for it in self.fig1.items[:]:
            self.fig1.removeItem(it)
        # nBins = 400
        # y = np.linspace(0,self.nChannels,self.nChannels)
        # x = np.linspace(0,self.freqMax,nBins)
        # maxz = 0
        # Yscale = self.freqMax/2  #Scale Z for better visualization
        # for ch in range(self.nChannels):
        #     if ch in self.transparent: #if it should be made transparent
        #         elem_alpha = .1
        #     else:
        #         elem_alpha = 1
        #     yi = np.array([y[ch]]*nBins)
        #     z = Yscale*(np.exp(-x/70) + np.random.randn(len(x))*np.exp(
        #     -x/70)/5)
        #     maxz = max(maxz,max(z))
        #     pts = np.vstack([x,yi,z]).transpose()
        #     plt = gl.GLLinePlotItem(pos=pts, color=(0,0,0,elem_alpha),
        #     width=1., antialias=True)
        #     self.fig1.addItem(plt)
        idx = self.psd.frequencies[:] <= self.freqMax
        idx[0] = False
        x = self.psd.frequencies[idx]
        nX = np.sum(idx)
        nY = self.nChannels
        y = np.linspace(0, nY, nY)
        for ch in range(nY):
            zch = self.psd.power[idx, ch]
            if ch == 0:
                z = zch
            else:
                z = np.vstack((z, zch))
        z = z.T  # z.shape (nBinsFreq,nChannels)
        zmax = z.max()
        zmin = z.min()
        zpercs = np.percentile(z, [10, 90])
        # Manually specified colors
        csize = 101
        cmap = np.hstack((np.linspace(0, 1, csize).reshape(-1, 1),
                          np.zeros(csize).reshape(-1, 1) + .4,
                          np.linspace(1, 0, csize).reshape(-1, 1)))
        colors = np.zeros((nX, nY, 4))
        # Finds color for each point in surface
        for f in range(nX):
            for ch in range(nY):
                # rel = (z[f,ch]-zmin)/(zmax-zmin)
                # relative position to choose color
                rel = np.clip((z[f, ch] - zpercs[0]) / (zpercs[1] - zpercs[0]), 0, 1)
                relc = int(rel * (csize - 1))
                colors[f, ch, 0] = cmap[relc, 0]  # red
                colors[f, ch, 1] = cmap[relc, 1]  # green
                colors[f, ch, 2] = cmap[relc, 2]  # blue
        # Surface plot
        p3 = gl.GLSurfacePlotItem(x=x, y=y, z=z, colors=colors.reshape(nX * nY, 4),
                                  shader='shaded', smooth=False)
        zscale = 200 / zmax
        p3.scale(1, 1, zscale)
        self.fig1.addItem(p3)
        # Axes
        axis = Custom3DAxis(self.fig1)
        axis.setSize(x=self.freqMax, y=self.nChannels, z=zmax * zscale)
        axis.add_labels(labels=['Frequency [Hz]', 'Channel #', 'PSD [V**2/Hz]'])
        xticks = np.arange(0, self.freqMax + 0.01, self.freqTickRes, dtype='int')
        yticks = np.linspace(1, self.nChannels, self.chTickGrid, dtype='int')
        zticks = np.round(np.linspace(0, zmax * zscale, 4), 1)
        axis.add_tick_values(xticks=xticks, yticks=yticks, zticks=zticks)
        self.fig1.addItem(axis)
        # Camera initial position
        self.fig1.setCameraPosition(distance=497, elevation=22, azimuth=-83)
        self.fig1.opts['center'] = QtGui.QVector3D(95.6, 195.4, 0)
        # Reference grids
        # gx = CustomGLGrid(self)#gl.GLGridItem()
        # gx.rotate(90, 0, 1, 0)
        # gx.setSize(x=zmax*zscale, y=self.nChannels)
        # gx.translate(dx=0, dy=self.nChannels/2, dz=zmax*zscale/2.)
        # gx.setSpacing(x=np.diff(zticks)[0], y=self.chTickSpace)
        # self.fig1.addItem(gx)
        # gy = CustomGLGrid(self)#gl.GLGridItem()
        # gy.rotate(90, 1, 0, 0)
        # gy.setSize(x=self.freqMax, y=zmax*zscale)
        # gy.translate(dx=self.freqMax/2, dy=self.nChannels, dz=zmax*zscale/2)
        # gy.setSpacing(x=np.diff(xticks)[0], y=np.diff(zticks)[0])
        # self.fig1.addItem(gy)
        # gz = CustomGLGrid(self)#gl.GLGridItem()
        # gz.setSize(x=self.freqMax, y=self.nChannels)
        # gz.translate(dx=self.freqMax/2, dy=self.nChannels/2, dz=0)
        # gz.setSpacing(x=np.diff(xticks)[0], y=self.chTickSpace)
        # self.fig1.addItem(gz)


class Custom3DAxis(gl.GLAxisItem):
    """Class defined to extend 'gl.GLAxisItem'."""

    def __init__(self, parent):
        gl.GLAxisItem.__init__(self)
        self.parent = parent

    def add_labels(self, labels=['X', 'Y', 'Z']):
        """Adds axes labels."""
        x, y, z = self.size()
        # X label
        self.xLabel = CustomTextItem(X=x / 2, Y=-y / 10, Z=-z / 10, text=labels[0])
        self.xLabel.setGLViewWidget(self.parent)
        self.parent.addItem(self.xLabel)
        # Y label
        self.yLabel = CustomTextItem(X=x + x / 10, Y=y / 2, Z=-z / 10, text=labels[1])
        self.yLabel.setGLViewWidget(self.parent)
        self.parent.addItem(self.yLabel)
        # Z label
        self.zLabel = CustomTextItem(X=-x / 8, Y=-y / 8, Z=z / 2, text=labels[2])
        self.zLabel.setGLViewWidget(self.parent)
        self.parent.addItem(self.zLabel)

    def add_tick_values(self, xticks=[], yticks=[], zticks=[]):
        """Adds ticks values."""
        x, y, z = self.size()
        xtpos = xticks  # np.linspace(0, x, len(xticks))
        ytpos = yticks  # np.linspace(0, y, len(yticks))
        ztpos = np.linspace(0, z, len(zticks))
        # X ticks
        for i, xt in enumerate(xticks):
            val = CustomTextItem(X=xtpos[i], Y=-y / 50, Z=-z / 50, text=str(xt))
            val.setGLViewWidget(self.parent)
            self.parent.addItem(val)
        # Y ticks
        for i, yt in enumerate(yticks):
            val = CustomTextItem(X=x + x / 50, Y=ytpos[i], Z=-z / 50, text=str(yt))
            val.setGLViewWidget(self.parent)
            self.parent.addItem(val)
        # Z ticks
        for i, zt in enumerate(zticks):
            val = CustomTextItem(X=-x / 15, Y=-y / 15, Z=ztpos[i], text=str(zt))
            val.setGLViewWidget(self.parent)
            self.parent.addItem(val)

    def paint(self):
        self.setupGLState()
        if self.antialias:
            ogl.glEnable(ogl.GL_LINE_SMOOTH)
            ogl.glHint(ogl.GL_LINE_SMOOTH_HINT, ogl.GL_NICEST)
        ogl.glBegin(ogl.GL_LINES)

        x, y, z = self.size()
        # Draw Z
        ogl.glColor4f(0, 0, 0, .6)
        ogl.glVertex3f(0, 0, 0)
        ogl.glVertex3f(0, 0, z)
        # Draw Y
        ogl.glColor4f(0, 0, 0, .6)
        ogl.glVertex3f(0, 0, 0)
        ogl.glVertex3f(0, y, 0)
        # Draw X
        ogl.glColor4f(0, 0, 0, .6)
        ogl.glVertex3f(0, 0, 0)
        ogl.glVertex3f(x, 0, 0)
        ogl.glEnd()


class CustomGLWidget(gl.GLViewWidget):
    """Class defined to extend 'gl.GLAxisItem'."""

    def __init__(self, parent):
        gl.GLViewWidget.__init__(self)
        self.parent = parent

    def mousePressEvent(self, ev):
        """Method altered to allow for mouse-click print of region."""
        self.mousePos = ev.pos()
        region = (ev.pos().x() - 5, ev.pos().y() - 5, 10, 10)
        if len(self.itemsAt(region)) > 1:
            item = self.itemsAt(region)[0]
            if type(item).__name__ == 'GLLinePlotItem':
                print(item.pos[0, 1])

    def mouseMoveEvent(self, ev):
        """Method altered to allow for mouse-driven pan."""
        diff = ev.pos() - self.mousePos
        self.mousePos = ev.pos()
        if ev.buttons() == QtCore.Qt.LeftButton:
            self.pan(diff.x(), diff.y(), 0, relative=True)
        elif ev.buttons() == QtCore.Qt.MidButton:
            if (ev.modifiers() & QtCore.Qt.ControlModifier):
                self.pan(diff.x(), 0, diff.y(), relative=True)
            else:
                self.pan(diff.x(), diff.y(), 0, relative=True)
        # print('center: ', self.parent.fig1.opts['center'])
        # print('distance: ', self.parent.fig1.opts['distance'])
        # print('elevation:', self.parent.fig1.opts['elevation'])
        # print('azimuth:', self.parent.fig1.opts['azimuth'])


class CustomGLGrid(gl.GLGridItem):
    """Class defined to extend 'gl.GLGridItem'."""

    def __init__(self, parent):
        gl.GLGridItem.__init__(self)
        self.parent = parent

    def paint(self):
        self.setupGLState()
        if self.antialias:
            ogl.glEnable(ogl.GL_LINE_SMOOTH)
            ogl.glEnable(ogl.GL_BLEND)
            ogl.glBlendFunc(ogl.GL_SRC_ALPHA, ogl.GL_ONE_MINUS_SRC_ALPHA)
            ogl.glHint(ogl.GL_LINE_SMOOTH_HINT, ogl.GL_NICEST)
        ogl.glBegin(ogl.GL_LINES)
        x, y, z = self.size()
        xs, ys, zs = self.spacing()
        xvals = np.arange(-x / 2., x / 2. + xs * 0.001, xs)
        yvals = np.arange(-y / 2., y / 2. + ys * 0.001, ys)
        ogl.glColor4f(.3, .3, .3, 1)
        st = 1.02  # scale to create ticks
        for x in xvals:
            ogl.glVertex3f(x, yvals[0] * st, 0)
            ogl.glVertex3f(x, yvals[-1] * st, 0)
        for y in yvals:
            ogl.glVertex3f(xvals[0] * st, y, 0)
            ogl.glVertex3f(xvals[-1] * st, y, 0)
        ogl.glEnd()


class CustomTextItem(gl.GLGraphicsItem.GLGraphicsItem):
    def __init__(self, X, Y, Z, text):
        gl.GLGraphicsItem.GLGraphicsItem.__init__(self)
        self.text = text
        self.X = X
        self.Y = Y
        self.Z = Z

    def setGLViewWidget(self, GLViewWidget):
        self.GLViewWidget = GLViewWidget

    def setText(self, text):
        self.text = text
        self.update()

    def setX(self, X):
        self.X = X
        self.update()

    def setY(self, Y):
        self.Y = Y
        self.update()

    def setZ(self, Z):
        self.Z = Z
        self.update()

    def paint(self):
        self.GLViewWidget.qglColor(QtCore.Qt.black)
        self.GLViewWidget.renderText(self.X, self.Y, self.Z, self.text)


# Gray line for visual separation of buttons -----------------------------------
class QHLine(QtGui.QFrame):
    def __init__(self):
        super().__init__()
        self.setFrameShape(QtGui.QFrame.HLine)
        self.setFrameShadow(QtGui.QFrame.Sunken)
