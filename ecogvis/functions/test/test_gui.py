from ecogvis.functions.test.test_nwb_copy_file import create_random_nwbfile
from ecogvis import Application

import pynwb
from pytestqt import qtbot
import os
import time
from PyQt5 import QtCore


def test_basic_gui(qtbot):
    '''test to ensure basic functionality is working.'''

    # Create a nwb file to be copied
    path_here = os.path.dirname(os.path.abspath(__file__))
    path_file = os.path.join(path_here, 'test_file.nwb')
    nwbfile = create_random_nwbfile()
    with pynwb.NWBHDF5IO(path_file, 'w') as io:
        io.write(nwbfile)

    app = Application(filename=path_file, session='test')
    qtbot.addWidget(app)
    # qtbot.wait(5000)

    # press ok to exit
    # qtbot.mouseClick(app.exit_dialog.pushButton_3, QtCore.Qt.LeftButton)

    qtbot.keyPress(app, QtCore.Qt.Key_Return)

    # assert widget.greet_label.text() == "Hello!"
    #
    # window.fileComboBox.clear()
    # qtbot.keyClicks(window.fileComboBox, '*.avi')
    #
    # window.directoryComboBox.clear()
    # qtbot.keyClicks(window.directoryComboBox, str(tmpdir))

    # Remove test nwb files
    # time.sleep(3)
    # os.remove(path_file)
