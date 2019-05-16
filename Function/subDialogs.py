from PyQt5 import QtGui, QtCore, uic
import os

path = os.path.dirname(__file__)

# Creates custom interval type.
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


# Selects channels from specific brain regions to be plotted
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
        self.cancelButton = QtGui.QPushButton("Cancel")
        self.selectButton = QtGui.QPushButton("Select All")
        self.unselectButton = QtGui.QPushButton("Unselect All")

        hbox = QtGui.QHBoxLayout()
        hbox.addStretch(1)
        hbox.addWidget(self.okButton)
        hbox.addWidget(self.cancelButton)
        hbox.addWidget(self.selectButton)
        hbox.addWidget(self.unselectButton)

        vbox = QtGui.QVBoxLayout()
        vbox.addWidget(self.listView)
        vbox.addStretch(1)
        vbox.addLayout(hbox)

        self.setLayout(vbox)
        #self.setLayout(layout)
        self.setWindowTitle('Select Regions:')

        self.okButton.clicked.connect(self.onAccepted)
        self.cancelButton.clicked.connect(self.reject)
        self.selectButton.clicked.connect(self.select_all)
        self.unselectButton.clicked.connect(self.unselect_all)

        self.exec_()

    def reject(self):
        QtGui.QDialog.reject(self)

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
