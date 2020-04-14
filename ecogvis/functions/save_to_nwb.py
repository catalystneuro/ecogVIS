from PyQt5 import QtGui
from PyQt5.QtWidgets import (QGridLayout, QGroupBox, QLabel, QPushButton,
                             QVBoxLayout, QHBoxLayout, QCheckBox)


# Save to NWB file dialog ------------------------------------------------------
class SaveToNWBDialog(QtGui.QDialog):
    def __init__(self, parent):
        super().__init__()
        self.parent = parent
        self.curr_nwbfile = self.parent.model.nwb
        self.value = False

        # Include data
        self.chk_raw = QCheckBox('Raw data')
        self.chk_raw.setChecked(False)
        if 'ElectricalSeries' not in self.curr_nwbfile.acquisition:
            self.chk_raw.setEnabled(False)
        self.chk_preprocessed = QCheckBox('Preprocessed data')
        self.chk_preprocessed.setChecked(False)
        self.chk_preprocessed.setEnabled(False)
        if 'ecephys' in self.curr_nwbfile.processing:
            if 'LFP' in self.curr_nwbfile.processing['ecephys'].data_interfaces:
                if 'preprocessed' in self.curr_nwbfile.processing['ecephys'].data_interfaces['LFP'].electrical_series:
                    self.chk_preprocessed.setEnabled(True)
        self.chk_gamma = QCheckBox('High gamma')
        self.chk_gamma.setChecked(False)
        self.chk_gamma.setEnabled(False)
        if 'ecephys' in self.curr_nwbfile.processing:
            if 'high_gamma' in self.curr_nwbfile.processing['ecephys'].data_interfaces:
                self.chk_gamma.setEnabled(True)

        self.form_1 = QGridLayout()
        self.form_1.addWidget(self.chk_raw, 0, 0)
        self.form_1.addWidget(self.chk_preprocessed, 1, 0)
        self.form_1.addWidget(self.chk_gamma, 2, 0)

        self.panel_1 = QGroupBox('Include data:')
        self.panel_1.setLayout(self.form_1)

        # Include Stimuli
        self.form_2 = QVBoxLayout()
        self.checks_stimuli = []
        for k, v in self.curr_nwbfile.stimulus.items():
            chk = QCheckBox(k)
            chk.setChecked(False)
            self.checks_stimuli.append(chk)
            self.form_2.addWidget(chk)

        self.panel_2 = QGroupBox('Include stimuli:')
        self.panel_2.setLayout(self.form_2)

        # Include user-edited information
        self.chk_badchannels = QCheckBox('Bad Channels')
        self.chk_badchannels.setChecked(False)
        self.chk_intervals = QCheckBox('Intervals')
        self.chk_intervals.setChecked(False)
        self.chk_annotations = QCheckBox('Annotations')
        self.chk_annotations.setChecked(False)

        self.form_3 = QGridLayout()
        self.form_3.addWidget(self.chk_badchannels, 0, 0)
        self.form_3.addWidget(self.chk_intervals, 1, 0)
        self.form_3.addWidget(self.chk_annotations, 2, 0)

        self.panel_3 = QGroupBox('Include info:')
        self.panel_3.setLayout(self.form_3)

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
        self.text = QLabel('Select what should be included in the nwb file.')
        self.vbox_1.addWidget(self.text)
        self.vbox_1.addWidget(self.panel_1)
        self.vbox_1.addWidget(self.panel_2)
        self.vbox_1.addWidget(self.panel_3)
        self.vbox_1.addLayout(self.hbox_1)

        self.setLayout(self.vbox_1)
        self.setWindowTitle('Save to NWB file')
        self.exec_()

    def save(self):
        self.value = True
        print(self.parent.model.nwb)
        self.accept()

    def cancel(self):
        self.value = False
        self.accept()
