from PyQt5 import QtGui, QtCore, uic
from PyQt5.QtWidgets import QTableWidgetItem
from ecog.utils import bands as default_bands
import numpy as np
import os

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
    def __init__(self, nwb):
        super().__init__()
        self.setupUi(self)
        self.nwb = nwb
        self.data_exists = False
        self.decomp_type = None
        self.custom_data = None

        self.radioButton_1.clicked.connect(self.choice_default)
        self.radioButton_2.clicked.connect(self.choice_highgamma)
        self.radioButton_3.clicked.connect(self.choice_custom)
        self.pushButton_1.clicked.connect(self.add_band)
        self.pushButton_2.clicked.connect(self.del_band)

        self.buttonBox.accepted.connect(self.out_accepted)
        self.buttonBox.rejected.connect(self.out_cancel)

        self.exec_()

    def choice_default(self):  # default chosen
        self.decomp_type = 'default'
        self.custom_data = None
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



    def choice_highgamma(self):  # default chosen
        self.decomp_type = 'high_gamma'
        self.custom_data = None
        self.pushButton_1.setEnabled(False)
        self.pushButton_2.setEnabled(False)
        self.tableWidget.setEditTriggers(QtGui.QAbstractItemView.NoEditTriggers)
        try:    # if data already exists in file
            decomp = self.nwb.modules['ecephys'].data_interfaces['Bandpower_high_gamma']
            text = "'High gamma' frequency decomposition data exists in current file.\n" \
                   "The bands are shown in the table."
            self.label_1.setText(text)
            self.data_exists = True
            # Populate table with values
            self.tableWidget.setHorizontalHeaderLabels(['min [Hz]','max [Hz]'])
            p0 = decomp.bands['filter_param_0']
            p1 = decomp.bands['filter_param_1']
            self.tableWidget.setRowCount(len(p0))
            for i in np.arange(len(p0)):
                self.tableWidget.setItem(i, 0, QTableWidgetItem(str(round(p0[i],1))))
                self.tableWidget.setItem(i, 1, QTableWidgetItem(str(round(p1[i],1))))
        except:  # if data does not exist in file
            text = "'High gamma' frequency decomposition data does not exist in current file.\n" \
                   "Do you want to generate it? The bands are shown in the table."
            self.label_1.setText(text)
            self.data_exists = False
            # Populate table with values
            self.tableWidget.setHorizontalHeaderLabels(['min [Hz]','max [Hz]'])
            p0 = [ default_bands.neuro['min_freqs'][-1] ]
            p1 = [ default_bands.neuro['max_freqs'][-1] ]
            self.tableWidget.setRowCount(len(p0))
            for i in np.arange(len(p0)):
                self.tableWidget.setItem(i, 0, QTableWidgetItem(str(round(p0[i],1))))
                self.tableWidget.setItem(i, 1, QTableWidgetItem(str(round(p1[i],1))))


    def choice_custom(self):  # default chosen
        self.decomp_type = 'custom'
        self.custom_data = None
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
            self.custom_data = np.zeros((2,len(p0)))
            for i in np.arange(len(p0)):
                self.tableWidget.setItem(i, 0, QTableWidgetItem(str(round(p0[i],1))))
                self.tableWidget.setItem(i, 1, QTableWidgetItem(str(round(p1[i],1))))
                self.custom_data[i,0] = round(p0[i],1)
                self.custom_data[i,1] = round(p1[i],1)
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
            self.custom_data = np.zeros((2,nRows))
            for i in np.arange(nRows):
                self.custom_data[i,0] = float(self.tableWidget.item(i, 0).text())
                self.custom_data[i,1] = float(self.tableWidget.item(i, 0).text())
        self.accept()

    def out_cancel(self):
        self.data_exists = False
        self.decomp_type = None
        self.custom_data = None
        self.close()
