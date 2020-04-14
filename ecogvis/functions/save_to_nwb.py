from PyQt5 import QtGui
from PyQt5.QtWidgets import (QGridLayout, QGroupBox, QLabel, QPushButton,
                             QVBoxLayout, QHBoxLayout, QCheckBox)


# Save to NWB file dialog ------------------------------------------------------
class SaveToNWBDialog(QtGui.QDialog):
    def __init__(self, parent):
        super().__init__()
        self.parent = parent
        self.value = False

        # Include data
        self.chk_raw = QCheckBox('Raw data')
        self.chk_raw.setChecked(False)
        self.chk_processed = QCheckBox('Preprocessed data')
        self.chk_processed.setChecked(False)
        self.chk_gamma = QCheckBox('High gamma')
        self.chk_gamma.setChecked(False)

        self.form_1 = QGridLayout()
        self.form_1.addWidget(self.chk_raw, 0, 0)
        self.form_1.addWidget(self.chk_processed, 1, 0)
        self.form_1.addWidget(self.chk_gamma, 2, 0)

        self.panel_1 = QGroupBox('Include data:')
        self.panel_1.setLayout(self.form_1)

        # Include Stimuli
        self.chk_stim1 = QCheckBox('Stimulus 1')
        self.chk_stim1.setChecked(False)
        self.chk_stim2 = QCheckBox('Stimulus 2')
        self.chk_stim2.setChecked(False)

        self.form_2 = QGridLayout()
        self.form_2.addWidget(self.chk_stim1, 0, 0)
        self.form_2.addWidget(self.chk_stim2, 1, 0)

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
