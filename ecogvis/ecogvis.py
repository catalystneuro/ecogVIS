# ecogVIS
# Timeseries visualizer for Electrocorticography (ECoG) signals stored in NWB files.
# Developed by:
# Luiz Tauffer, Ben Dichter
# https://github.com/bendichter/ecogVIS
#
import sys
import os
import numpy as np
import datetime
import glob

from PyQt5 import QtCore, QtGui, Qt
from PyQt5.QtCore import QCoreApplication
from PyQt5.QtWidgets import (QWidget, QLabel, QLineEdit, QMessageBox, QHBoxLayout,
    QApplication, QPushButton, QVBoxLayout, QGroupBox, QGridLayout, QComboBox,
    QInputDialog, QFileDialog, QMainWindow, QAction, QStackedLayout)
import pyqtgraph as pg

from ecogvis.functions.subFunctions import TimeSeriesPlotter
from ecogvis.functions.subDialogs import (CustomIntervalDialog, SelectChannelsDialog,
    SpectralChoiceDialog, NoHighGammaDialog, NoPreprocessedDialog, NoTrialsDialog,
    ExitDialog, ERPDialog, HighGammaDialog, PeriodogramGridDialog, AudioEventDetection,
    PreprocessingDialog, NoRawDialog, NoSpectrumDialog, NoAudioDialog, ExistIntervalsDialog)

annotationAdd_ = False
annotationDel_ = False
annotationColor_ = 'red'
intervalAdd_ = False
intervalDel_ = False
intervalType_ = 'invalid'
intervalsDict_ = {'invalid': {'type': 'invalid',
                              'session': '',
                              'color': 'red',
                              'counts': 0}}


class Application(QMainWindow):
    keyPressed = QtCore.pyqtSignal(QtCore.QEvent)

    def __init__(self, filename, parent=None):
        super().__init__()
        # Enable anti-aliasing for prettier plots
        pg.setConfigOptions(antialias=True)

        self.centralwidget = QWidget()
        self.setCentralWidget(self.centralwidget)
        self.resize(1000, 600)
        self.setWindowTitle('ecogVIS')

        # e.g.: /home/User/freesurfer_subjects/Subject_XX.nwb
        if not os.path.isfile(filename):
            filename = self.open_file()
        self.file = filename

        self.error = None
        self.keyPressed.connect(self.on_key)
        self.active_mode = 'default'

        self.init_gui()
        self.show()

        # opens dialog for session name
        text = 'Enter session name:\n(e.g. your_name)'
        uinp, ok = QInputDialog.getText(None, 'Choose session', text)
        if ok:
            self.current_session = uinp
        else:
            self.current_session = 'default'

        # Run the main function
        self.model = TimeSeriesPlotter(self)

    def closeEvent(self, event):
        """Before exiting, checks if there are any unsaved changes and inform the user."""
        w = ExitDialog(self)
        if w.value == -1:  # just exit
            event.accept()
        elif w.value == 1:  # save and exit
            self.AnnotationSave()
            self.IntervalSave()
            event.accept()
        elif w.value == 0:  # ignore
            event.ignore()

    def log_error(self, error):
        """Error logging"""
        pwd = os.getcwd()
        folder = os.path.join(pwd, 'error_log')
        if not os.path.exists(folder):
            os.mkdir(folder)
        with open(os.path.join(folder, 'error.log'), 'a') as file:
            file.write(datetime.datetime.today().strftime('%Y-%m-%d  %H:%M:%S') + ' ' + error + '\n')
        file.close()

    def keyPressEvent(self, event):
        super(Application, self).keyPressEvent(event)
        self.keyPressed.emit(event)

    def on_key(self, event):
        """Actions to be taken when user presses keys."""
        if event.key() == QtCore.Qt.Key_Up:
            self.model.channel_Scroll_Up('page')
        elif event.key() == QtCore.Qt.Key_PageUp:
            self.model.channel_Scroll_Up('page')
        elif event.key() == QtCore.Qt.Key_Down:
            self.model.channel_Scroll_Down('page')
        elif event.key() == QtCore.Qt.Key_PageDown:
            self.model.channel_Scroll_Down('page')
        elif event.key() == QtCore.Qt.Key_Left:
            self.model.time_scroll(scroll=-1/3)
        elif event.key() == QtCore.Qt.Key_Right:
            self.model.time_scroll(scroll=1/3)
        event.accept()

    def init_gui(self):
        """Initiates GUI elements."""
        mainMenu = self.menuBar()
        # File menu
        fileMenu = mainMenu.addMenu('File')
        # Adding actions to file menu
        change_session_file = QAction('Change Session', self)
        fileMenu.addAction(change_session_file)
        change_session_file.triggered.connect(self.change_session)
        action_open_file = QAction('Open Another File', self)
        fileMenu.addAction(action_open_file)
        action_open_file.triggered.connect(lambda: self.open_another_file(None))
        #action_save_file = QAction('Save to NWB', self)
        #fileMenu.addAction(action_save_file)
        #action_save_file.triggered.connect(self.save_file)

        toolsMenu = mainMenu.addMenu('Tools')
        action_load_annotations = QAction('Load Annotations', self)
        toolsMenu.addAction(action_load_annotations)
        action_load_annotations.triggered.connect(self.load_annotations)
        action_load_intervals = QAction('Load Intervals', self)
        toolsMenu.addAction(action_load_intervals)
        action_load_intervals.triggered.connect(self.load_intervals)
        channels_tools_menu = toolsMenu.addMenu('Bad Channels')
        action_add_badchannel = QAction('Add Bad Channel', self)
        channels_tools_menu.addAction(action_add_badchannel)
        action_add_badchannel.triggered.connect(self.add_badchannel)
        action_del_badchannel = QAction('Del Bad Channel', self)
        channels_tools_menu.addAction(action_del_badchannel)
        action_del_badchannel.triggered.connect(self.del_badchannel)
        action_save_badchannel = QAction('Save Bad Channels', self)
        channels_tools_menu.addAction(action_save_badchannel)
        action_save_badchannel.triggered.connect(self.save_badchannel)
        action_spectral_decomposition = QAction('Spectral Decomposition', self)
        toolsMenu.addAction(action_spectral_decomposition)
        action_spectral_decomposition.triggered.connect(self.spectral_decomposition)
        action_erp = QAction('ERP', self)
        toolsMenu.addAction(action_erp)
        action_erp.triggered.connect(self.event_related_potential)
        action_event_detection = QAction('CV Event Detection', self)
        toolsMenu.addAction(action_event_detection)
        action_event_detection.triggered.connect(self.audio_event_detection)

        helpMenu = mainMenu.addMenu('Help')
        action_about = QAction('About', self)
        helpMenu.addAction(action_about)
        action_about.triggered.connect(self.about)

        # Buttons and controls vertical box layout -----------------------------
        #Block change buttons
        self.qlabelBlocks = QLabel('Move Block')
        self.pushBlock_0 = QPushButton('<')
        self.pushBlock_0.clicked.connect(lambda: self.change_block(-1))
        self.pushBlock_1 = QPushButton('>')
        self.pushBlock_1.clicked.connect(lambda: self.change_block(1))
        grid0 = QGridLayout()
        grid0.addWidget(self.pushBlock_0, 0, 0, 1, 1)
        grid0.addWidget(self.qlabelBlocks, 0, 1, 1, 3)
        grid0.addWidget(self.pushBlock_1, 0, 4, 1, 1)

        panel1 = QGroupBox('Panel')
        panel1.setFixedWidth(250)

        # Annotation buttons
        qlabelAnnotations = QLabel('Annotation:')
        self.combo1 = QComboBox()
        self.combo1.addItem('red')
        self.combo1.addItem('green')
        self.combo1.addItem('blue')
        self.combo1.addItem('yellow')
        self.combo1.activated.connect(self.AnnotationColor)
        self.push1_1 = QPushButton('Add')
        self.push1_1.clicked.connect(self.AnnotationAdd)
        self.push1_1.setCheckable(True)
        self.push1_2 = QPushButton('Del')
        self.push1_2.clicked.connect(self.AnnotationDel)
        self.push1_2.setCheckable(True)
        self.push1_3 = QPushButton('Save')
        self.push1_3.clicked.connect(self.AnnotationSave)

        # Custom intervals buttons
        qlabelIntervals = QLabel('Intervals:')
        self.combo2 = QComboBox()
        self.combo2.addItem('invalid')
        self.combo2.addItem('add custom')
        self.combo2.activated.connect(self.IntervalType)
        self.push2_1 = QPushButton('Add')
        self.push2_1.clicked.connect(self.IntervalAdd)
        self.push2_1.setCheckable(True)
        self.push2_2 = QPushButton('Del')
        self.push2_2.clicked.connect(self.IntervalDel)
        self.push2_2.setCheckable(True)
        self.push2_3 = QPushButton('Save')
        self.push2_3.clicked.connect(self.IntervalSave)

        #Bad channels buttons
        qlabelBadChannels = QLabel('Bad channels:')
        self.push3_1 = QPushButton('Add')
        self.push3_1.clicked.connect(self.add_badchannel)
        self.push3_2 = QPushButton('Del')
        self.push3_2.clicked.connect(self.del_badchannel)
        self.push3_3 = QPushButton('Save')
        self.push3_3.clicked.connect(self.save_badchannel)

        # Get channel by brain region
        self.push4_0 = QPushButton('Select regions')
        self.push4_0.clicked.connect(self.ChannelSelect)
        #Periodogram
        self.push5_0 = QPushButton('Periodogram')
        self.push5_0.clicked.connect(self.PeriodogramSelect)
        # One-click preprocess signals
        self.push6_0 = QPushButton('Preprocess')
        self.push6_0.setCheckable(False)
        self.push6_0.clicked.connect(self.Preprocess)
        # One-click calculate High Gamma
        self.push7_0 = QPushButton('High Gamma')
        self.push7_0.setCheckable(False)
        self.push7_0.clicked.connect(self.CalcHighGamma)

        # Buttons layout
        grid1 = QGridLayout()
        grid1.addWidget(qlabelAnnotations, 0, 0, 1, 3)
        grid1.addWidget(self.combo1, 0, 3, 1, 3)
        grid1.addWidget(self.push1_1, 1, 0, 1, 2)
        grid1.addWidget(self.push1_2, 1, 2, 1, 2)
        grid1.addWidget(self.push1_3, 1, 4, 1, 2)
        grid1.addWidget(qlabelIntervals, 2, 0, 1, 3)
        grid1.addWidget(self.combo2, 2, 3, 1, 3)
        grid1.addWidget(self.push2_1, 3, 0, 1, 2)
        grid1.addWidget(self.push2_2, 3, 2, 1, 2)
        grid1.addWidget(self.push2_3, 3, 4, 1, 2)
        grid1.addWidget(qlabelBadChannels, 4, 0, 1, 6)
        grid1.addWidget(self.push3_1, 5, 0, 1, 2)
        grid1.addWidget(self.push3_2, 5, 2, 1, 2)
        grid1.addWidget(self.push3_3, 5, 4, 1, 2)
        grid1.addWidget(self.push4_0, 6, 0, 1, 3)
        grid1.addWidget(self.push5_0, 6, 3, 1, 3)
        grid1.addWidget(self.push6_0, 7, 0, 1, 3)
        grid1.addWidget(self.push7_0, 7, 3, 1, 3)
        panel1.setLayout(grid1)


        # Traces panel ---------------------------------------------------------
        panel2 = QGroupBox('Traces')
        panel2.setFixedWidth(250)
        qlabelSignal = QLabel('Signal:')
        self.combo3 = QComboBox()
        self.combo3.addItem('raw')
        self.combo3.addItem('preprocessed')
        self.combo3.addItem('high gamma')
        self.combo3.activated.connect(self.voltage_time_series)
        qlabelStimuli = QLabel('Stimuli:')
        self.combo4 = QComboBox()
        self.combo4.activated.connect(self.choose_stim)

        grid2 = QGridLayout()
        grid2.addWidget(qlabelSignal, 0, 0, 1, 1)
        grid2.addWidget(self.combo3, 0, 1, 1, 1)
        grid2.addWidget(qlabelStimuli, 1, 0, 1, 1)
        grid2.addWidget(self.combo4, 1, 1, 1, 1)
        grid2.setAlignment(QtCore.Qt.AlignTop)
        panel2.setLayout(grid2)


        # Plot controls panel --------------------------------------------------
        qlabel1 = QLabel('Top')
        qlabel2 = QLabel('Bottom')
        qlabel3 = QLabel('Interval \nstart(s)')
        qlabel4 = QLabel('Time \nspan')
        qlabel5 = QLabel('Vertical\nScale')
        self.qline0 = QLineEdit('16')
        self.qline1 = QLineEdit('1')
        self.qline2 = QLineEdit('0.01')
        self.qline3 = QLineEdit('2')
        self.qline4 = QLineEdit('1')

        self.qline0.returnPressed.connect(self.channelDisplayed)
        self.qline1.returnPressed.connect(self.channelDisplayed)
        self.qline2.returnPressed.connect(self.interval_start)
        self.qline3.returnPressed.connect(self.time_window_size)
        self.qline4.returnPressed.connect(self.verticalScale)

        self.pushbtn1_1 = QPushButton('^')
        self.pushbtn1_1.clicked.connect(self.scroll_up)
        self.pushbtn1_2 = QPushButton('^^')
        self.pushbtn1_2.clicked.connect(self.scroll_up_page)
        self.pushbtn2_1 = QPushButton('v')
        self.pushbtn2_1.clicked.connect(self.scroll_down)
        self.pushbtn2_2 = QPushButton('vv')
        self.pushbtn2_2.clicked.connect(self.scroll_down_page)

        self.pushbtn3 = QPushButton('<<')
        self.pushbtn3.clicked.connect(self.page_backward)
        self.pushbtn4 = QPushButton('<')
        self.pushbtn4.clicked.connect(self.scroll_backward)
        self.pushbtn5 = QPushButton('>>')
        self.pushbtn5.clicked.connect(self.page_forward)
        self.pushbtn6 = QPushButton('>')
        self.pushbtn6.clicked.connect(self.scroll_forward)
        self.pushbtn7 = QPushButton('*2')
        self.pushbtn7.clicked.connect(self.time_window_enlarge)
        self.pushbtn8 = QPushButton('/2')
        self.pushbtn8.clicked.connect(self.time_window_reduce)
        self.pushbtn9 = QPushButton('*2')
        self.pushbtn9.clicked.connect(self.verticalScaleIncrease)
        self.pushbtn10 = QPushButton('/2')
        self.pushbtn10.clicked.connect(self.verticalScaleDecrease)

        form_2 = QGridLayout()
        form_2.addWidget(qlabel1, 0, 0)
        form_2.addWidget(self.qline0, 0, 1)
        form_2.addWidget(self.pushbtn1_1, 0, 2)
        form_2.addWidget(self.pushbtn1_2, 0, 3)
        form_2.addWidget(qlabel2, 1, 0)
        form_2.addWidget(self.qline1, 1, 1)
        form_2.addWidget(self.pushbtn2_1, 1, 2)
        form_2.addWidget(self.pushbtn2_2, 1, 3)

        form_2.addWidget(qlabel3, 2, 0, 1, 2)
        form_2.addWidget(self.qline2, 2, 2, 1, 2)
        form_2.addWidget(self.pushbtn3, 3, 0)
        form_2.addWidget(self.pushbtn4, 3, 1)
        form_2.addWidget(self.pushbtn6, 3, 2)
        form_2.addWidget(self.pushbtn5, 3, 3)
        form_2.addWidget(qlabel4, 4, 0)
        form_2.addWidget(self.qline3, 4, 1)
        form_2.addWidget(self.pushbtn7, 4, 2)
        form_2.addWidget(self.pushbtn8, 4, 3)
        form_2.addWidget(qlabel5, 5, 0)
        form_2.addWidget(self.qline4, 5, 1)
        form_2.addWidget(self.pushbtn9, 5, 2)
        form_2.addWidget(self.pushbtn10, 5, 3)

        panel3 = QGroupBox('Plot Controls')
        panel3.setFixedWidth(250)
        panel3.setLayout(form_2)

        self.vbox1 = QVBoxLayout()
        self.vbox1.addLayout(grid0)
        self.vbox1.addWidget(panel1)
        self.vbox1.addWidget(panel2)
        self.vbox1.addWidget(panel3)
        self.vbox1.addStretch()


        # Time series plots Vertical Box ---------------------------------------
        vb = CustomViewBox(self)
        self.win1 = pg.PlotWidget(viewBox = vb)   #middle signals plot
        self.win2 = pg.PlotWidget()               #upper horizontal bar
        self.win3 = pg.PlotWidget()               #lower audio plot
        self.win1.setBackground(self.palette().color(QtGui.QPalette.Background))
        self.win2.setBackground(self.palette().color(QtGui.QPalette.Background))
        self.win3.setBackground(self.palette().color(QtGui.QPalette.Background))
        self.win1.setMouseEnabled(x = False, y = False)
        self.win2.setMouseEnabled(x = False, y = False)
        self.win3.setMouseEnabled(x = False, y = False)
        self.win1.hideButtons()
        self.win2.hideButtons()
        self.win3.hideButtons()
        #self.win2.hideAxis('left')
        self.win2.hideAxis('bottom')
        #self.win3.hideAxis('left')
        self.win3.hideAxis('bottom')

        form_3 = QGridLayout()
        form_3.setSpacing(0.0)
        form_3.setRowStretch(0, 1)
        form_3.setRowStretch(1, 8)
        form_3.setRowStretch(2, 1)
        form_3.addWidget(self.win2)
        form_3.addWidget(self.win1)
        form_3.addWidget(self.win3)

        self.groupbox1 = QGroupBox('Signals')
        self.groupbox1.setLayout(form_3)

        self.vbox2 = QStackedLayout()
        self.vbox2.addWidget(self.groupbox1)
        self.vbox2.setCurrentIndex(0)

        # Creates a horizontal box layout and populate it with panels ----------
        self.hbox = QHBoxLayout(self.centralwidget)
        self.hbox.addLayout(self.vbox1)    #add panels first
        self.hbox.addLayout(self.vbox2)    #add plots second


    def change_block(self, move):
        """Move between Block files for the same subject."""
        fpath = os.path.split(os.path.abspath(self.file))[0] #file directory
        fname = os.path.split(os.path.abspath(self.file))[1] #current file
        pre, _ = fname.split('_B')
        flist = glob.glob(fpath+'/'+pre+'_B*.nwb')
        curr_ind = flist.index(self.file)
        if curr_ind+move == len(flist):
            new_file = flist[0]
        else:
            new_file = flist[curr_ind+move]
        self.open_another_file(filename=new_file)


    def open_file(self):
        """Opens initial file."""
        filename, _ = QFileDialog.getOpenFileName(None, 'Open file', '', "(*.nwb)")
        return filename


    def open_another_file(self, filename=None):
        """Opens another NWB file."""
        if filename is None: # Opens new file dialog
            filename, _ = QFileDialog.getOpenFileName(None, 'Open file', '', "(*.nwb)")
        if os.path.isfile(filename):
            self.file = filename
            # Reset file specific variables on GUI
            self.combo3.setCurrentIndex(self.combo3.findText('raw'))
            self.combo4.clear()
            self.qline0.setText('16')
            self.qline1.setText('1')
            self.qline2.setText('0.01')
            self.qline3.setText('2')
            self.qline4.setText('1')
            self.win1.clear()
            self.win2.clear()
            self.win3.clear()
            # Rebuild the model
            self.model = TimeSeriesPlotter(self)


    def save_file(self):
        """Saves latest alterations to NWB file. TO BE IMPLEMENTED."""
        print('Save file to NWB - to be implemented')


    def change_session(self):
        """Changes session name."""
        text = 'Current session is: '+self.current_session+'\nEnter new session name:'
        uinp, ok = QInputDialog.getText(None, 'Change session', text)
        if ok:
            self.current_session = uinp
            fname = os.path.split(os.path.abspath(self.file))[1] #file
            self.setWindowTitle('ecogVIS - '+fname+' - '+self.current_session)


    def load_annotations(self):
        """Loads annotations from file, calls function to paint them."""
        fname, aux = QFileDialog.getOpenFileName(self, 'Open file', '', "(*.csv)")
        if fname!='':
            self.model.AnnotationLoad(fname=fname)


    def load_intervals(self):
        """Loads intervals from file, calls function to paint them."""
        fname, aux = QFileDialog.getOpenFileName(self, 'Open file', '', "(*.csv)")
        if fname!='':
            self.model.IntervalLoad(fname=fname)


    def add_badchannel(self):
        """Opens dialog for user input of channels to mark as bad."""
        text = 'Channel number: \n(e.g.: 3, 5, 8-12)'
        uinp, ok = QInputDialog.getText(None, 'Add as bad channel', text)
        if ok:
            uinp = uinp.replace(' ','')  #removes blank spaces
            ch_str = uinp.split(',')     #splits csv
            try:
                ch_list = []
                for elem in ch_str:
                    if '-' in elem:   #if given a range e.g. 7-12
                        elem_lims = elem.split('-')
                        seq = range(int(elem_lims[0])-1,int(elem_lims[1]))
                        ch_list.extend(seq)
                    else:             #if given a single value
                        ch_list.append(int(elem)-1)
                self.model.BadChannelAdd(ch_list=ch_list)
            except Exception as ex:
                print(str(ex))


    def del_badchannel(self):
        """Opens dialog for user input of channels to unmark as bad."""
        text = 'Channel number: \n(e.g.: 3, 5, 8-12)'
        uinp, ok = QInputDialog.getText(None, 'Delete bad channel', text)
        if ok:
            uinp = uinp.replace(' ','')  #removes blank spaces
            ch_str = uinp.split(',')     #splits csv
            try:
                ch_list = []
                for elem in ch_str:
                    if '-' in elem:   #if given a range e.g. 7-12
                        elem_lims = elem.split('-')
                        seq = range(int(elem_lims[0])-1,int(elem_lims[1]))
                        ch_list.extend(seq)
                    else:             #if given a single value
                        ch_list.append(int(elem)-1)
                self.model.BadChannelDel(ch_list=ch_list)
            except Exception as ex:
                print(str(ex))


    def save_badchannel(self):
        """Saves bad channels to file."""
        self.model.BadChannelSave()


    def spectral_decomposition(self):
        """Opens Spectral decomposition dialog."""
        w = SpectralChoiceDialog(self)
        if w.value==1:       # If new data was created
            self.model.refresh_file()


    def event_related_potential(self):
        """Opens ERP window."""
        open_dialog = True
        try: #Checks if file contains proper intervals information
            speaker_start_times = self.model.nwb.intervals['TimeIntervals_speaker']['start_time'].data
            speaker_stop_times = self.model.nwb.intervals['TimeIntervals_speaker']['stop_time'].data
            mic_start_times = self.model.nwb.intervals['TimeIntervals_mic']['start_time'].data
            mic_stop_times = self.model.nwb.intervals['TimeIntervals_mic']['stop_time'].data
        except: #if it fails, raises a no intervals data message
            NoTrialsDialog()
            open_dialog = False
        try:  #Tries to load High Gamma and intervals data
            hg = self.model.nwb.processing['ecephys'].data_interfaces['high_gamma']
        except: #if it fails, raises a no high gamma message
            NoHighGammaDialog()
            open_dialog = False
        #If all tries passed, open ERP
        if open_dialog:
            w = ERPDialog(parent=self)


    def audio_event_detection(self):
        """Opens Audio Event Detection window."""
         #Test if trials already exist
        if 'TimeIntervals_speaker' not in self.model.nwb.intervals:
            #Test if file contains audio signals
            if ('microphone' in self.model.nwb.acquisition) and ('speaker1' in self.model.nwb.stimulus):
                w = AudioEventDetection(parent=self)
                if w.value == 1:  #Trial times were detected
                    self.model.refresh_file()  # re-opens the file, now with new data
            else:
                NoAudioDialog()
        else:
            ExistIntervalsDialog()


    def about(self):
        """About dialog."""
        msg = QMessageBox()
        msg.setWindowTitle("About ecogVIS")
        msg.setIcon(QMessageBox.Information)
        msg.setText("Version: 1.0.0 \n"+
                    "Timeseries visualizer for ECoG signals stored in NWB files.\n ")
        msg.setInformativeText("<a href='https://github.com/luiztauffer/ecogVIS/'>ecogVIS Github page</a>")
        msg.setStandardButtons(QMessageBox.Ok)
        msg.exec_()


    def reset_buttons(self):
        """Controls appearance and active state of panel buttons."""
        global intervalAdd_
        global intervalDel_
        global annotationAdd_
        global annotationDel_

        #self.active_mode = 'default', 'intervalAdd', 'intervalDel'
        if self.active_mode != 'intervalAdd':
            self.push2_1.setChecked(False)
            intervalAdd_ = False

        if self.active_mode != 'intervalDel':
            self.push2_2.setChecked(False)
            intervalDel_ = False

        if self.active_mode != 'annotationAdd':
            self.push1_1.setChecked(False)
            annotationAdd_ = False

        if self.active_mode != 'annotationDel':
            self.push1_2.setChecked(False)
            annotationDel_ = False


    ## Annotation functions ----------------------------------------------------
    def AnnotationColor(self):
        """Selects annotation color."""
        global annotationColor_
        annotationColor_ = str(self.combo1.currentText())

    def AnnotationAdd(self):
        """Add new annotation at point selected with mouse right-click."""
        global annotationAdd_
        if self.push1_1.isChecked():  #if button is pressed down
            self.active_mode = 'annotationAdd'
            self.reset_buttons()
            annotationAdd_ = True
        else:
            self.active_mode = 'default'
            self.reset_buttons()

    def AnnotationDel(self):
        """Deletes annotations chosen with mouse right-click."""
        global annotationDel_
        if self.push1_2.isChecked():  #if button is pressed down
            self.active_mode = 'annotationDel'
            self.reset_buttons()
            annotationDel_ = True
        else:
            self.active_mode = 'default'
            self.reset_buttons()

    def AnnotationSave(self):
        """Saves current set of annotations to file."""
        self.active_mode = 'default'
        self.reset_buttons()
        try:
            self.model.AnnotationSave()
        except Exception as ex:
            self.log_error(str(ex))


    ## Interval functions ------------------------------------------------------
    def IntervalType(self):
        """Add new interval type."""
        global intervalType_
        global intervalsDict_

        item = str(self.combo2.currentText())
        if item == 'add custom':
            w = CustomIntervalDialog()
            int_type, color = w.getResults()
            if len(int_type)>0:    # If user chose a valid name for the new interval type
                curr_ind = self.combo2.currentIndex()
                self.combo2.setItemText(curr_ind, int_type)
                self.combo2.addItem('add custom')
                intervalType_ = int_type
                intervalsDict_[intervalType_] = {'type':intervalType_,
                                                 'session':self.current_session,
                                                 'color':color,
                                                 'counts':0}
                self.combo2.setCurrentIndex(curr_ind)
            else:
                self.combo2.setCurrentIndex(0)
        else:
            intervalType_ = item


    def IntervalAdd(self):
        """Adds intervals with mouse click-and-drag at time series plot."""
        global intervalAdd_
        if self.push2_1.isChecked():  #if button is pressed down
            self.active_mode = 'intervalAdd'
            self.reset_buttons()
            intervalAdd_ = True
        else:
            self.active_mode = 'default'
            self.reset_buttons()


    def IntervalDel(self):
        """Deletes intervals chosen with mouse right-click."""
        global intervalDel_
        if self.push2_2.isChecked():  #if button is pressed down
            self.active_mode = 'intervalDel'
            self.reset_buttons()
            intervalDel_ = True
        else:
            self.active_mode = 'default'
            self.reset_buttons()


    def IntervalSave(self):
        """Saves current set of intervals to file."""
        self.active_mode = 'default'
        self.reset_buttons()
        try:
            self.model.IntervalSave()
        except Exception as ex:
            self.log_error(str(ex))


    def ChannelSelect(self):
        """Opens dialog to select channels from specific brain regions."""
        self.active_mode = 'default'
        self.reset_buttons()
        # Dialog to choose channels from specific brain regions
        w = SelectChannelsDialog(self.model.all_regions, self.model.regions_mask)
        all_locs = self.model.nwb.electrodes['location'][:]
        self.model.channels_mask = np.zeros(len(all_locs))
        for loc in w.choices:
            self.model.channels_mask += all_locs==loc
        #Indices of channels from chosen regions
        self.model.channels_mask_ind = np.where(self.model.channels_mask)[0]
        self.model.nChTotal = len(self.model.channels_mask_ind)
        # Reset channels span control
        self.model.lastCh = np.minimum(16, self.model.nChTotal)
        self.model.firstCh = 1
        self.model.nChToShow = self.model.lastCh - self.model.firstCh + 1
        self.qline0.setText(str(self.model.lastCh))
        self.qline1.setText(str(self.model.firstCh))
        # Update signals plot
        self.model.selectedChannels = self.model.channels_mask_ind[self.model.firstCh-1:self.model.lastCh]
        self.model.refreshScreen()


    def PeriodogramSelect(self):
        """Opens Periodogram grid window. Checks if PSD data is present on file
        and, if not, asks the user if it should be calculated."""
        if self.combo3.currentText()=='raw':
            try:  # tries to read fft and welch spectral data
                psd_fft = self.model.nwb.modules['ecephys'].data_interfaces['Spectrum_fft_raw']
                psd_welch = self.model.nwb.modules['ecephys'].data_interfaces['Spectrum_welch_raw']
                PeriodogramGridDialog(self)
            except:
                w = NoSpectrumDialog(self, 'raw')
                if w.val == 1:  # PSD was calculated
                    self.model.refresh_file()  # re-opens the file, now with new data
                    self.combo3.setCurrentIndex(self.combo3.findText('raw'))
                    psd_fft = self.model.nwb.modules['ecephys'].data_interfaces['Spectrum_fft_raw']
                    psd_welch = self.model.nwb.modules['ecephys'].data_interfaces['Spectrum_welch_raw']
                    PeriodogramGridDialog(self)
        elif self.combo3.currentText()=='preprocessed':
            try:  #tries to read fft and welch spectral data
                psd_fft = self.model.nwb.modules['ecephys'].data_interfaces['Spectrum_fft_preprocessed']
                psd_welch = self.model.nwb.modules['ecephys'].data_interfaces['Spectrum_welch_preprocessed']
                PeriodogramGridDialog(self)
            except:
                w = NoSpectrumDialog(self, 'preprocessed')
                if w.val == 1:  #PSD was calculated
                    self.model.refresh_file()  # re-opens the file, now with new data
                    self.combo3.setCurrentIndex(self.combo3.findText('preprocessed'))
                    psd_fft = self.model.nwb.modules['ecephys'].data_interfaces['Spectrum_fft_preprocessed']
                    psd_welch = self.model.nwb.modules['ecephys'].data_interfaces['Spectrum_welch_preprocessed']
                    PeriodogramGridDialog(self)


    def Preprocess(self):
        """Opens Preprocessing dialog."""
        w = PreprocessingDialog(self)
        if w.value==1:       # If new data was created
            self.model.refresh_file()        # re-opens the file, now with new data
            self.combo3.setCurrentIndex(self.combo3.findText('preprocessed'))
            self.voltage_time_series()

    def CalcHighGamma(self):
        """Opens calculate High Gamma dialog."""
        w = HighGammaDialog(self)
        if w.value==1:       # If new data was created
            self.open_another_file(filename=w.new_fname)

    def voltage_time_series(self):
        """
        Selects the time series data to be ploted on main window. The options are:
        - 'voltage_raw': Raw voltage traces, stored in nwb.acquisition['ElectricalSeries']
        - 'preprocessed': Preprocessed voltage traces, stored in nwb.processing['ecephys'].data_interfaces['LFP'].electrical_series['preprocessed']
        - 'high gamma': High Gamma estimation traces, stored in nwb.processing['ecephys'].data_interfaces['high_gamma']
        """
        if self.combo3.currentText()=='raw':
            lis = list(self.model.nwb.acquisition.keys())
            there_is_raw = False
            for i in lis:  # Check if there is ElectricalSeries in acquisition group
                if type(self.model.nwb.acquisition[i]).__name__ == 'ElectricalSeries':
                    self.model.source = self.model.nwb.acquisition[i]
                    there_is_raw = True
            if there_is_raw:
                self.model.plot_panel = 'voltage_raw'
                self.model.plotData = self.model.source.data
                self.model.nBins = self.model.plotData.shape[0]     #total number of bins
                self.model.fs_signal = self.model.source.rate     #sampling frequency [Hz]
                self.model.tbin_signal = 1/self.model.fs_signal #time bin duration [seconds]
                self.push5_0.setEnabled(True)
                self.push6_0.setEnabled(True)
                self.push7_0.setEnabled(False)
            else:
                self.combo3.setCurrentIndex(self.combo3.findText('high gamma'))
                self.voltage_time_series()
                NoRawDialog()
        elif self.combo3.currentText()=='preprocessed':
            try:   #if preprocessed signals already exist on NWB file
                self.model.source = self.model.nwb.processing['ecephys'].data_interfaces['LFP'].electrical_series['preprocessed']
                self.model.plotData = self.model.source.data
                self.model.plot_panel = 'voltage_preprocessed'
                self.model.nBins = self.model.source.data.shape[0]
                self.model.fs_signal = self.model.source.rate
                self.model.tbin_signal = 1/self.model.fs_signal
                self.push5_0.setEnabled(True)
                self.push6_0.setEnabled(False)
                self.push7_0.setEnabled(True)
            except:
                self.combo3.setCurrentIndex(self.combo3.findText('raw'))
                self.voltage_time_series()
                NoPreprocessedDialog()
        elif self.combo3.currentText()=='high gamma':
            try:     #if high gamma already exists on NWB file
                self.model.source = self.model.nwb.processing['ecephys'].data_interfaces['high_gamma']
                self.model.plotData = self.model.source.data
                self.model.plot_panel = 'spectral_power'
                self.model.nBins = self.model.source.data.shape[0]
                self.model.fs_signal = self.model.source.rate
                self.model.tbin_signal = 1/self.model.fs_signal
                self.push5_0.setEnabled(False)
                self.push6_0.setEnabled(False)
                self.push7_0.setEnabled(False)
            except:  #if not, opens warning dialog
                self.combo3.setCurrentIndex(self.combo3.findText('preprocessed'))
                self.voltage_time_series()
                NoHighGammaDialog()
        self.model.updateCurXAxisPosition()    #updates time points
        self.model.refreshScreen()


    def choose_stim(self):
        """Choose stimulus."""
        stimName = self.combo4.currentText()
        if stimName != '':
            self.model.refreshScreen()


    ## Plot control buttons ----------------------------------------------------
    def scroll_up(self):
        self.model.channel_Scroll_Up('unit')

    def scroll_up_page(self):
        self.model.channel_Scroll_Up('page')

    def scroll_down(self):
        self.model.channel_Scroll_Down('unit')

    def scroll_down_page(self):
        self.model.channel_Scroll_Down('page')

    def page_backward(self):
        self.model.time_scroll(scroll=-1)

    def scroll_backward(self):
        self.model.time_scroll(scroll=-1/3)

    def page_forward(self):
        self.model.time_scroll(scroll=1)

    def scroll_forward(self):
        self.model.time_scroll(scroll=1/3)

    def horizontalScaleIncrease(self):
        self.model.horizontalScaleIncrease()

    def horizontalScaleDecrease(self):
        self.model.horizontalScaleDecrease()

    def verticalScale(self):
        """Updates vertical scale and refreshes plot."""
        self.model.refreshScreen()

    def verticalScaleIncrease(self):
        """Increases vertical scale by a factor of 2."""
        scaleFac = float(self.qline4.text())
        self.qline4.setText(str(scaleFac * 2))
        self.model.refreshScreen()

    def verticalScaleDecrease(self):
        """Decreases vertical scale by a factor of 2."""
        scaleFac = float(self.qline4.text())
        self.qline4.setText(str(scaleFac / 2))
        self.model.refreshScreen()

    def time_window_size(self):
        self.model.updateCurXAxisPosition()

    def time_window_enlarge(self):
        self.model.time_window_resize(2.)

    def time_window_reduce(self):
        self.model.time_window_resize(0.5)

    def interval_start(self):
        self.model.updateCurXAxisPosition()

    def channelDisplayed(self):
        self.model.nChannels_Displayed()


class CustomViewBox(pg.ViewBox):
    """Customized ViewBox to add/del Annotations and Intervals."""
    def __init__(self, parent):
        pg.ViewBox.__init__(self)
        self.parent = parent

    def mouseClickEvent(self, ev):
        global intervalDel_
        global annotationAdd_
        global annotationDel_
        global annotationColor_

        if intervalDel_:
            mousePoint = self.mapSceneToView(ev.scenePos())
            x = mousePoint.x()
            try:
                self.parent.model.IntervalDel(round(x, 3))
            except Exception as ex:
                print(str(ex))

        if annotationAdd_:
            mousePoint = self.mapSceneToView(ev.scenePos())
            x = mousePoint.x()
            y = mousePoint.y()
            try:
                text, ok = QInputDialog.getText(None, 'Annotations', 'Enter your annotation:')
                self.parent.model.AnnotationAdd(x=x, y=y, color=annotationColor_, text=text)
            except Exception as ex:
                print(str(ex))

        if annotationDel_:
            mousePoint = self.mapSceneToView(ev.scenePos())
            x = mousePoint.x()
            y = mousePoint.y()
            try:
                self.parent.model.AnnotationDel(x=x, y=y)
            except Exception as ex:
                print(str(ex))

    def mouseDragEvent(self, ev):
        global intervalType_
        global intervalAdd_
        global intervalsDict_

        if intervalAdd_:
            if ev.button() == QtCore.Qt.RightButton:
                ev.ignore()
            else:
                pg.ViewBox.mouseDragEvent(self, ev)
                if ev.isStart():    #first click before dragging
                    a = self.mapSceneToView(ev.scenePos())
                    self.pos1 = a.x()              #initial x mark
                    self.parent.model.DrawMarkTime(self.pos1)     #temporary line on x mark
                elif ev.isFinish():  #release from dragging
                    self.parent.model.RemoveMarkTime()   #remove line on x mark
                    a = self.mapSceneToView(ev.scenePos())
                    self.pos2 = a.x()              #final x mark
                    if self.pos1 is not None:
                        if self.pos2 < self.pos1:     #marking from right to left
                            interval = [round(self.pos2, 3), round(self.pos1, 3)]
                        else:               #marking from left to right
                            interval = [round(self.pos1, 3), round(self.pos2, 3)]
                        color = intervalsDict_[intervalType_]['color']
                        session = self.parent.current_session
                        intervalsDict_[intervalType_]['counts'] += 1
                        self.parent.model.IntervalAdd(interval, intervalType_, color, session)
                        self.parent.model.refreshScreen()


def main(filename):  # If it was imported as a module
    """Sets up QT application."""
    app = QCoreApplication.instance()
    if app is None:
        app = QApplication(sys.argv)  # instantiate a QtGui (holder for the app)
    ex = Application(filename=filename)
    sys.exit(app.exec_())


if __name__ == '__main__':
    main(sys.argv[0])

