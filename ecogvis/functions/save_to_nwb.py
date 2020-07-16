from PyQt5 import QtGui
from PyQt5.QtWidgets import (QGridLayout, QGroupBox, QLabel, QPushButton,
                             QVBoxLayout, QHBoxLayout, QCheckBox, QLineEdit,
                             QStyle, QFileDialog)
import pynwb


# Save to NWB file dialog ------------------------------------------------------
class SaveToNWBDialog(QtGui.QDialog):
    def __init__(self, parent):
        super().__init__()
        self.parent = parent
        self.curr_nwbfile = self.parent.model.nwb
        self.value = False

        # New file path
        self.newfile = ''
        self.btn_newfile = QPushButton('Save to')
        self.btn_newfile.setIcon(self.style().standardIcon(QStyle.SP_DriveFDIcon))
        self.btn_newfile.clicked.connect(self.newfile_path)
        self.lin_newfile = QLineEdit('')
        self.lin_newfile.setEnabled(False)

        self.panel_0 = QGridLayout()
        self.panel_0.addWidget(self.btn_newfile, 0, 0)
        self.panel_0.addWidget(self.lin_newfile, 0, 1)

        # Include raw data
        self.chk_raw = QCheckBox('Raw data')
        self.chk_raw.setChecked(False)
        self.chk_raw.setEnabled(False)
        for v in self.curr_nwbfile.acquisition.values():
            if v.__class__ is pynwb.ecephys.ElectricalSeries:
                self.chk_raw.setEnabled(True)
                self.chk_raw.setChecked(True)
                self.raw_name = v.name
        self.form_1 = QVBoxLayout()
        self.form_1.addWidget(self.chk_raw)

        # Include processing 'ecephys'
        self.checks_processing_ecephys = []
        if 'ecephys' in self.curr_nwbfile.processing:
            for k, v in self.curr_nwbfile.processing['ecephys'].data_interfaces.items():
                chk = QCheckBox(k)
                chk.setChecked(True)
                self.checks_processing_ecephys.append(chk)
                self.form_1.addWidget(chk)

        # Include processing 'behavior'
        self.checks_processing_behavior = []
        if 'behavior' in self.curr_nwbfile.processing:
            for k, v in self.curr_nwbfile.processing['behavior'].data_interfaces.items():
                if v.neurodata_type != 'SurveyTable':
                    chk = QCheckBox(k)
                    chk.setChecked(True)
                    self.checks_processing_behavior.append(chk)
                    self.form_1.addWidget(chk)
        self.panel_1 = QGroupBox('Include data:')
        self.panel_1.setLayout(self.form_1)

        # Include mic recording
        self.form_2 = QVBoxLayout()
        self.checks_mic = []
        for k, v in self.curr_nwbfile.acquisition.items():
            if v.__class__ is pynwb.ecephys.TimeSeries:
                chk = QCheckBox(k)
                chk.setChecked(True)
                self.checks_mic.append(chk)
                self.form_2.addWidget(chk)
        self.panel_2 = QGroupBox('Include microphone:')
        self.panel_2.setLayout(self.form_2)

        # Speaker stimuli
        self.form_3 = QVBoxLayout()
        self.checks_stimuli = []
        for k, v in self.curr_nwbfile.stimulus.items():
            chk = QCheckBox(k)
            chk.setChecked(True)
            self.checks_stimuli.append(chk)
            self.form_3.addWidget(chk)
        self.panel_3 = QGroupBox('Include stimuli:')
        self.panel_3.setLayout(self.form_3)

        self.form_4 = QVBoxLayout()

        # Surveys tables
        self.chk_surveys = QCheckBox('Surveys')
        self.chk_surveys.setChecked(False)
        if 'behavior' in self.curr_nwbfile.processing:
            if any([v for v in self.curr_nwbfile.processing['behavior'].data_interfaces.values()
                    if v.neurodata_type == 'SurveyTable']):
                self.form_4.addWidget(self.chk_surveys)
                self.chk_surveys.setChecked(True)

        # Include user-edited information
        self.chk_intervals = QCheckBox('Intervals')
        self.chk_intervals.setChecked(False)
        self.chk_annotations = QCheckBox('Annotations')
        self.chk_annotations.setChecked(False)
        self.form_4.addWidget(self.chk_intervals)
        self.form_4.addWidget(self.chk_annotations)

        self.panel_4 = QGroupBox('Include info:')
        self.panel_4.setLayout(self.form_4)

        # Buttons
        self.btn_save = QPushButton("Save")
        self.btn_save.clicked.connect(self.save)
        self.btn_cancel = QPushButton("Cancel")
        self.btn_cancel.clicked.connect(self.cancel)

        self.hbox_1 = QHBoxLayout()
        self.hbox_1.addWidget(self.btn_save)
        self.hbox_1.addWidget(self.btn_cancel)

        # Main Layout
        self.vbox_1 = QVBoxLayout()
        self.text0 = QLabel('New nwb file:')
        self.vbox_1.addWidget(self.text0)
        self.vbox_1.addLayout(self.panel_0)
        self.vbox_1.addWidget(QLabel(''))
        self.text1 = QLabel('Select what should be included in the new NWB file:')
        self.vbox_1.addWidget(self.text1)
        self.vbox_1.addWidget(self.panel_1)
        self.vbox_1.addWidget(self.panel_2)
        self.vbox_1.addWidget(self.panel_3)
        self.vbox_1.addWidget(self.panel_4)
        self.vbox_1.addLayout(self.hbox_1)

        self.setLayout(self.vbox_1)
        self.setWindowTitle('Save to NWB file')
        self.exec_()

    def newfile_path(self):
        filename, _ = QFileDialog.getSaveFileName(None, 'Save to file', '', "(*.nwb)")
        if filename:
            self.newfile = filename
            self.lin_newfile.setText(filename)

    def save(self):
        self.value = True
        self.make_cp_objs()
        self.accept()

    def cancel(self):
        self.value = False
        self.accept()

    def make_cp_objs(self):
        """Make dictionary of chosen objects to be passed to new file"""
        self.cp_objs = {
            'institution': True,
            'lab': True,
            'session': True,
            'devices': True,
            'electrode_groups': True,
            'electrodes': True,
            'epochs': True,
            'trials': True,
            'subject': True,
            'acquisition': [],
            'stimulus': [],
            'ecephys': [],
            'behavior': [],
            'surveys': False,
        }
        # Raw data
        if self.chk_raw.isChecked():
            self.cp_objs['acquisition'].append(self.raw_name)
        # Processed data
        for chk in self.checks_processing_ecephys:
            if chk.isChecked():
                self.cp_objs['ecephys'].append(chk.text())
        for chk in self.checks_processing_behavior:
            if chk.isChecked():
                self.cp_objs['behavior'].append(chk.text())
        # Mic recording
        for chk in self.checks_mic:
            if chk.isChecked():
                self.cp_objs['acquisition'].append(chk.text())
        # Speaker stimuli
        for chk in self.checks_stimuli:
            if chk.isChecked():
                self.cp_objs['stimulus'].append(chk.text())
        # Surveys
        if self.chk_surveys.isChecked():
            self.cp_objs.update({'surveys': True})
        # User-defined info
        if self.chk_intervals.isChecked():
            self.cp_objs.update({'intervals': True})
