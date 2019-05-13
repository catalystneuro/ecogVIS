from PyQt5 import QtGui, uic
import os

path = os.path.dirname(__file__)
qtCreatorFile = "intervals_gui.ui"
Ui_Dialog, _ = uic.loadUiType(os.path.join(path,qtCreatorFile))

class CustomDialog(QtGui.QDialog, Ui_Dialog):
    '''
    Create custom interval type.
    '''
    def __init__(self):
        super(CustomDialog, self).__init__()
        self.setupUi(self)

    def getResults(self):
        if self.exec_() == QtGui.QDialog.Accepted:
            # get all values
            text = str(self.lineEdit.text())
            color = str(self.comboBox.currentText())
            return text, color
        else:
            return '', ''
