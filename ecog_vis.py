# -*- coding: utf-8 -*-
import sys
import os
import time
import numpy as np

from PyQt5 import QtCore, QtGui, Qt
from PyQt5.QtCore import QCoreApplication
from PyQt5.QtWidgets import (QWidget, QLabel, QLineEdit, QMessageBox, QHBoxLayout,
    QTextEdit, QApplication, QPushButton, QVBoxLayout, QGroupBox, QFormLayout, QDialog,
    QRadioButton, QGridLayout, QComboBox, QInputDialog, QFileDialog, QMainWindow,
    QAction, QStackedLayout)
import pyqtgraph as pg
from pyqtgraph.widgets.MatplotlibWidget import MatplotlibWidget
from Function.subFunctions import ecogVIS
from Function.subDialogs import (CustomIntervalDialog, SelectChannelsDialog,
    SpectralChoiceDialog, PeriodogramDialog)


model = None
intervalAdd_ = False
intervalDel_ = False
intervalType_ = 'invalid'
intervalsDict_ = {'invalid':{'name':'invalid',
                             'color':'red',
                             'counts':0}}
annotationAdd_ = False
annotationDel_ = False
annotationColor_ = 'red'
periodogram_ = False

class Application(QMainWindow):
    keyPressed = QtCore.pyqtSignal(QtCore.QEvent)
    def __init__(self, filename, parent = None):
        super().__init__()
        global model

        self.centralwidget = QWidget()
        self.setCentralWidget(self.centralwidget)
        self.resize(800, 600)
        self.setWindowTitle('ecogVIS')

        # e.g.: /home/User/freesurfer_subjects/Subject_XX.nwb
        if not os.path.isfile(filename):
            filename = self.open_file()

        self.error = None
        self.keyPressed.connect(self.on_key)
        self.active_mode = 'default'

        self.init_gui()
        self.show()
        #self.showMaximized()

        # Run the main function
        parameters = {}
        parameters['pars'] = {'Figure': [self.win1, self.win2, self.win3]}
        parameters['editLine'] = {'qLine0': self.qline0, 'qLine1': self.qline1,
                                  'qLine2': self.qline2, 'qLine3': self.qline3,
                                  'qLine4': self.qline4}

        model = ecogVIS(self, filename, parameters)



    def log_error(self, error):
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
        if event.key() == QtCore.Qt.Key_Up:
            model.channel_Scroll_Up('page')
        elif event.key() == QtCore.Qt.Key_PageUp:
            model.channel_Scroll_Up('page')
        elif event.key() == QtCore.Qt.Key_Down:
            model.channel_Scroll_Down('page')
        elif event.key() == QtCore.Qt.Key_PageDown:
            model.channel_Scroll_Down('page')
        elif event.key() == QtCore.Qt.Key_Left:
            model.time_scroll(scroll=-1/3)
        elif event.key() == QtCore.Qt.Key_Right:
            model.time_scroll(scroll=1/3)
        event.accept()


    def init_gui(self):
        mainMenu = self.menuBar()
        # File menu
        fileMenu = mainMenu.addMenu('File')
        # Adding actions to file menu
        action_open_file = QAction('Open Another File', self)
        fileMenu.addAction(action_open_file)
        action_open_file.triggered.connect(self.open_file)
        action_save_file = QAction('Save to NWB', self)
        fileMenu.addAction(action_save_file)
        action_save_file.triggered.connect(self.save_file)

        editMenu = mainMenu.addMenu('Edit')

        toolsMenu = mainMenu.addMenu('Tools')
        action_load_annotations = QAction('Load Annotations', self)
        toolsMenu.addAction(action_load_annotations)
        action_load_annotations.triggered.connect(self.load_annotations)
        action_load_intervals = QAction('Load Intervals', self)
        toolsMenu.addAction(action_load_intervals)
        action_load_intervals.triggered.connect(self.load_intervals)
        channels_tools_menu = toolsMenu.addMenu('Channels')
        action_add_badchannel = QAction('Add Bad Channel', self)
        channels_tools_menu.addAction(action_add_badchannel)
        action_add_badchannel.triggered.connect(self.add_badchannel)
        action_del_badchannel = QAction('Del Bad Channel', self)
        channels_tools_menu.addAction(action_del_badchannel)
        action_del_badchannel.triggered.connect(self.del_badchannel)
        action_save_badchannel = QAction('Save Bad Channels', self)
        channels_tools_menu.addAction(action_save_badchannel)
        action_save_badchannel.triggered.connect(self.save_badchannel)
        analysis_tools_menu = toolsMenu.addMenu('Analysis')
        action_spectral_analysis = QAction('Spectral Analysis', self)
        analysis_tools_menu.addAction(action_spectral_analysis)
        action_spectral_analysis.triggered.connect(self.spectral_analysis)

        helpMenu = mainMenu.addMenu('Help')
        action_about = QAction('About', self)
        helpMenu.addAction(action_about)
        action_about.triggered.connect(self.about)


        '''
        Buttons and controls vertical box layout
        '''
        panel1 = QGroupBox('Panel')
        panel1.setFixedWidth(200)
        panel1.setFixedHeight(200)

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

        # Get channel buttons
        qlabelChannels = QLabel('Channels:')
        self.push3_0 = QPushButton('Select')
        self.push3_0.clicked.connect(self.ChannelSelect)

        self.push4_0 = QPushButton('Periodogram')
        self.push4_0.setCheckable(True)
        self.push4_0.clicked.connect(self.PeriodogramSelect)

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
        grid1.addWidget(qlabelChannels, 4, 0, 1, 3)
        grid1.addWidget(self.push3_0, 4, 3, 1, 3)
        grid1.addWidget(self.push4_0, 5, 0, 1, 6)
        panel1.setLayout(grid1)

        # Traces panel ---------------------------------------------------------
        panel2 = QGroupBox('Traces')
        panel2.setFixedWidth(200)
        panel2.setFixedHeight(100)
        self.rbtn1 = QRadioButton('Voltage')
        self.rbtn1.setChecked(True)
        self.rbtn1.clicked.connect(self.voltage_time_series)
        self.combo3 = QComboBox()
        self.combo3.addItem('raw')
        self.combo3.addItem('preprocessed')
        self.combo3.activated.connect(self.voltage_time_series)
        self.rbtn2 = QRadioButton('High gamma')
        self.rbtn2.setChecked(False)
        self.rbtn2.clicked.connect(self.power_time_series)
        grid2 = QGridLayout()
        grid2.addWidget(self.rbtn1, 0, 0, 1, 1)
        grid2.addWidget(self.combo3, 0, 1, 1, 1)
        grid2.addWidget(self.rbtn2, 1, 0, 1, 2)
        panel2.setLayout(grid2)

        # Plot controls panel --------------------------------------------------
        panel3 = QGroupBox('Plot Controls')
        panel3.setFixedWidth(200)
        self.enableButton = QPushButton('Enable')
        self.enableButton.setFixedWidth(100)
        self.enableButton.clicked.connect(self.enable)
        qlabel1 = QLabel('Top')
        qlabel2 = QLabel('Bottom')
        qlabel3 = QLabel('Interval \nstart(s)')
        qlabel4 = QLabel('Time \nspan')
        qlabel5 = QLabel('Vertical\nScale')
        self.qline0 = QLineEdit('16')
        self.qline0.setEnabled(False)
        self.qline1 = QLineEdit('1')
        self.qline1.setEnabled(False)
        self.qline2 = QLineEdit('0.01')
        self.qline2.setEnabled(False)
        self.qline3 = QLineEdit('2')
        self.qline3.setEnabled(False)
        self.qline4 = QLineEdit('1')
        self.qline4.setEnabled(False)

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
        form_2.addWidget(self.enableButton, 0, 1)
        form_2.addWidget(qlabel1, 1, 0)
        form_2.addWidget(self.qline0, 1, 1)
        form_2.addWidget(self.pushbtn1_1, 1, 2)
        form_2.addWidget(self.pushbtn1_2, 1, 3)
        form_2.addWidget(qlabel2, 2, 0)
        form_2.addWidget(self.qline1, 2, 1)
        form_2.addWidget(self.pushbtn2_1, 2, 2)
        form_2.addWidget(self.pushbtn2_2, 2, 3)

        form_2.addWidget(qlabel3, 4, 0, 1, 2)
        form_2.addWidget(self.qline2, 4, 2, 1, 2)
        form_2.addWidget(self.pushbtn3, 5, 0)
        form_2.addWidget(self.pushbtn4, 5, 1)
        form_2.addWidget(self.pushbtn6, 5, 2)
        form_2.addWidget(self.pushbtn5, 5, 3)
        form_2.addWidget(qlabel4, 6, 0)
        form_2.addWidget(self.qline3, 6, 1)
        form_2.addWidget(self.pushbtn7, 6, 2)
        form_2.addWidget(self.pushbtn8, 6, 3)
        form_2.addWidget(qlabel5, 7, 0)
        form_2.addWidget(self.qline4, 7, 1)
        form_2.addWidget(self.pushbtn9, 7, 2)
        form_2.addWidget(self.pushbtn10, 7, 3)
        form_2.addWidget(QLabel(), 8, 0)
        panel3.setLayout(form_2)

        self.vbox1 = QVBoxLayout()
        self.vbox1.addWidget(panel1)
        self.vbox1.addWidget(panel2)
        self.vbox1.addWidget(panel3)


        '''
        Time series plots Vertical Box
        '''
        vb = CustomViewBox()
        self.win1 = pg.PlotWidget(viewBox = vb)   #middle signals plot
        self.win2 = pg.PlotWidget(border = 'k')   #upper horizontal bar
        self.win3 = pg.PlotWidget()               #lower audio plot
        self.win1.setBackground('w')
        self.win2.setBackground('w')
        self.win3.setBackground('w')
        self.win1.setMouseEnabled(x = False, y = False)
        self.win2.setMouseEnabled(x = False, y = False)
        self.win3.setMouseEnabled(x = False, y = False)

        self.win2.hideAxis('left')
        self.win2.hideAxis('bottom')
        self.win3.hideAxis('left')
        self.win3.hideAxis('bottom')

        form_3 = QGridLayout() #QVBoxLayout()
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


        '''
        Create a horizontal box layout and populate it with panels
        '''
        self.hbox = QHBoxLayout(self.centralwidget)
        self.hbox.addLayout(self.vbox1)    #add panels first
        self.hbox.addLayout(self.vbox2)    #add plots second



    def open_file(self):
        filename, _ = QFileDialog.getOpenFileName(None, 'Open file', '', "(*.nwb)")
        return filename

    def save_file(self):
        print('Save file to NWB - to be implemented')

    def load_annotations(self):
        # opens annotations file dialog, calls function to paint them
        fname = QFileDialog.getOpenFileName(self, 'Open file', '', "(*.csv)")
        model.AnnotationLoad(fname=fname[0])

    def load_intervals(self):
        # opens intervals file dialog, calls function to paint them
        fname = QFileDialog.getOpenFileName(self, 'Open file', '', "(*.csv)")
        model.IntervalLoad(fname=fname[0])

    def add_badchannel(self):
        # opens dialog for user input
        text, ok = QInputDialog.getText(None, 'Add as bad channel', 'Channel number:')
        ch = int(text)-1
        model.BadChannelAdd(ch=ch)

    def del_badchannel(self):
        # opens dialog for user input
        text, ok = QInputDialog.getText(None, 'Delete bad channel', 'Channel number:')
        ch = int(text)-1
        model.BadChannelDel(ch=ch)

    def save_badchannel(self):
        model.BadChannelSave()


    def spectral_analysis(self):
        w = SpectralChoiceDialog(nwb=model.nwb, fpath=model.pathName,
                                 fname=model.fileName)
        model.refresh_file()        # re-opens the file, now with new data
        self.power_time_series()    # refresh plot graphs


    def about(self):
        msg = QMessageBox()
        msg.setWindowTitle("About ecogVIS")
        msg.setIcon(QMessageBox.Information)
        msg.setText("Version: 1.0.0 \n"+
                    "Timeseries visualizer for ECoG signals stored in NWB files.\n ")
        msg.setInformativeText("<a href='https://github.com/luiztauffer/ecogVIS/'>ecogVIS Github page</a>")
        msg.setStandardButtons(QMessageBox.Ok)
        msg.exec_()


    def reset_buttons(self):
        global intervalAdd_
        global intervalDel_
        global annotationAdd_
        global annotationDel_
        global periodogram_

        #self.active_mode = 'default', 'intervalAdd', 'intervalDel', 'periodogram'
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

        if self.active_mode != 'periodogram':
            self.push4_0.setChecked(False)
            periodogram_ = False


    ## Annotation functions ----------------------------------------------------
    def AnnotationColor(self):
        global annotationColor_
        annotationColor_ = str(self.combo1.currentText())


    def AnnotationAdd(self):
        global annotationAdd_
        if self.push1_1.isChecked():  #if button is pressed down
            self.active_mode = 'annotationAdd'
            self.reset_buttons()
            annotationAdd_ = True
        else:
            self.active_mode = 'default'
            self.reset_buttons()


    def AnnotationDel(self):
        global annotationDel_
        if self.push1_2.isChecked():  #if button is pressed down
            self.active_mode = 'annotationDel'
            self.reset_buttons()
            annotationDel_ = True
        else:
            self.active_mode = 'default'
            self.reset_buttons()


    def AnnotationSave(self):
        self.active_mode = 'default'
        self.reset_buttons()
        try:
            model.AnnotationSave()
        except Exception as ex:
            self.log_error(str(ex))


    ## Interval functions ------------------------------------------------------
    def IntervalType(self):
        global intervalType_
        global intervalsDict_

        item = str(self.combo2.currentText())
        if item == 'add custom':
            w = CustomIntervalDialog()
            text, color = w.getResults()
            if len(text)>0:    # If user chose a valid name for the new interval type
                curr_ind = self.combo2.currentIndex()
                self.combo2.setItemText(curr_ind, text)
                self.combo2.addItem('add custom')
                intervalType_ = text
                intervalsDict_[intervalType_] = {'name':intervalType_,
                                                 'color':color,
                                                 'counts':0}
                self.combo2.setCurrentIndex(curr_ind)
            else:
                self.combo2.setCurrentIndex(0)
        else:
            intervalType_ = item


    def IntervalAdd(self):
        global intervalAdd_
        if self.push2_1.isChecked():  #if button is pressed down
            self.active_mode = 'intervalAdd'
            self.reset_buttons()
            intervalAdd_ = True
        else:
            self.active_mode = 'default'
            self.reset_buttons()


    def IntervalDel(self):
        global intervalDel_
        if self.push2_2.isChecked():  #if button is pressed down
            self.active_mode = 'intervalDel'
            self.reset_buttons()
            intervalDel_ = True
        else:
            self.active_mode = 'default'
            self.reset_buttons()


    def IntervalSave(self):
        self.active_mode = 'default'
        self.reset_buttons()
        try:
            model.IntervalSave()
        except Exception as ex:
            self.log_error(str(ex))



    ## Channel functions -------------------------------------------------------
    def ChannelSelect(self):
        self.active_mode = 'default'
        self.reset_buttons()
        # Dialog to choose channels from specific brain regions
        w = SelectChannelsDialog(model.all_regions, model.regions_mask)
        all_locs = model.ecog.electrodes.table['location'][:]
        model.channels_mask = np.zeros(len(all_locs))
        for loc in w.choices:
            model.channels_mask += all_locs==loc
        #Indices of channels from chosen regions
        model.channels_mask_ind = np.where(model.channels_mask)[0]
        model.nChTotal = len(model.channels_mask_ind)
        # Reset channels span control
        model.lastCh = np.minimum(16, model.nChTotal)
        model.firstCh = 1
        model.nChToShow = model.lastCh - model.firstCh + 1
        self.qline0.setText(str(model.lastCh))
        self.qline1.setText(str(model.firstCh))
        # Update signals plot
        model.selectedChannels = model.channels_mask_ind[model.firstCh-1:model.lastCh]
        model.refreshScreen()



    # Select channel for Periodogram display -----------------------------------
    def PeriodogramSelect(self):
        global periodogram_
        if self.push4_0.isChecked():  #if button is pressed down
            self.active_mode = 'periodogram'
            self.reset_buttons()
            periodogram_ = True
        else:
            self.active_mode = 'default'
            self.reset_buttons()


    #def get_channel(self, event):
    #    mousePoint = self.win1.plotItem.vb.mapSceneToView(event.scenePos())
    #    model.getChannel(mousePoint)



    ## Change Signals plot panel -----------------------------------------------
    def voltage_time_series(self):
        self.rbtn1.setChecked(True)
        if self.combo3.currentText()=='raw':
            model.plot_panel = 'voltage_raw'
            model.plotData = model.ecog.data
            model.nBins = model.plotData.shape[0]     #total number of bins
            model.fs_signal = model.ecog.rate     #sampling frequency [Hz]
            model.tbin_signal = 1/model.fs_signal #time bin duration [seconds]
        elif self.combo3.currentText()=='preprocessed':
            try:   #if preprocessed signals already exist on NWB file
                model.plotData = model.nwb.modules['ecephys'].data_interfaces['LFP'].electrical_series['preprocessed'].data
                model.plot_panel = 'voltage_preprocessed'
            except:
                self.spectral_analysis()
                model.plot_panel = 'voltage_preprocessed'
                model.plotData = model.nwb.modules['ecephys'].data_interfaces['LFP'].electrical_series['preprocessed'].data
            #total number of bins
            model.nBins = model.nwb.modules['ecephys'].data_interfaces['LFP'].electrical_series['preprocessed'].data.shape[0]
            #sampling frequency [Hz]
            model.fs_signal = model.nwb.modules['ecephys'].data_interfaces['LFP'].electrical_series['preprocessed'].rate
            #time bin duration [seconds]
            model.tbin_signal = 1/model.fs_signal
        model.getCurAxisParameters()    #updates time points
        model.refreshScreen()


    def power_time_series(self):
        try:     #if decomposition already exists on NWB file
            model.plotData = model.nwb.modules['ecephys'].data_interfaces['high_gamma'].data
        except:  #if not, opens dialog for user choice
            self.spectral_analysis()
            model.plotData = model.nwb.modules['ecephys'].data_interfaces['high_gamma'].data
        model.plot_panel = 'spectral_power'
        #total number of bins
        model.nBins = model.plotData.shape[0]
        #sampling frequency [Hz]
        model.fs_signal = model.nwb.modules['ecephys'].data_interfaces['Bandpower_default'].rate
        #time bin duration [seconds]
        model.tbin_signal = 1/model.fs_signal
        model.getCurAxisParameters()    #updates time points
        model.refreshScreen()




    ## Plot control buttons ----------------------------------------------------
    def enable(self):
        if self.enableButton.text() == 'Enable':
            self.enableButton.setText('Disable')
            self.qline0.setEnabled(True)
            self.qline1.setEnabled(True)
            self.qline2.setEnabled(True)
            self.qline3.setEnabled(True)
            self.qline4.setEnabled(True)
        else:
            self.enableButton.setText('Enable')
            self.qline0.setEnabled(False)
            self.qline1.setEnabled(False)
            self.qline2.setEnabled(False)
            self.qline3.setEnabled(False)
            self.qline4.setEnabled(False)

    def scroll_up(self):
        model.channel_Scroll_Up('unit')

    def scroll_up_page(self):
        model.channel_Scroll_Up('page')

    def scroll_down(self):
        model.channel_Scroll_Down('unit')

    def scroll_down_page(self):
        model.channel_Scroll_Down('page')

    def page_backward(self):
        model.time_scroll(scroll=-1)

    def scroll_backward(self):
        model.time_scroll(scroll=-1/3)

    def page_forward(self):
        model.time_scroll(scroll=1)

    def scroll_forward(self):
        model.time_scroll(scroll=1/3)

    def verticalScale(self):
        model.refreshScreen()

    def horizontalScaleIncrease(self):
        model.horizontalScaleIncrease()

    def horizontalScaleDecrease(self):
        model.horizontalScaleDecrease()

    def verticalScaleIncrease(self):
        model.verticalScaleIncrease()

    def verticalScaleDecrease(self):
        model.verticalScaleDecrease()

    def time_window_size(self):
        model.updateCurXAxisPosition()

    def time_window_enlarge(self):
        model.time_window_resize(2.)

    def time_window_reduce(self):
        model.time_window_resize(0.5)

    def interval_start(self):
        model.updateCurXAxisPosition()

    def channelDisplayed(self):
        model.nChannels_Displayed()



## Viewbox for signal plots ----------------------------------------------------
class CustomViewBox(pg.ViewBox):
    def __init__(self):
        pg.ViewBox.__init__(self)
        #super().__init__(self)

    def mouseClickEvent(self, ev):
        global intervalDel_
        global annotationAdd_
        global annotationDel_
        global annotationColor_
        global periodogram_

        if intervalDel_:
            mousePoint = self.mapSceneToView(ev.scenePos())
            x = mousePoint.x()
            try:
                model.IntervalDel(round(x, 3))
            except Exception as ex:
                print(str(ex))

        if annotationAdd_:
            mousePoint = self.mapSceneToView(ev.scenePos())
            x = mousePoint.x()
            y = mousePoint.y()
            try:
                text, ok = QInputDialog.getText(None, 'Annotations', 'Enter your annotation:')
                model.AnnotationAdd(x=x, y=y, color=annotationColor_, text=text)
            except Exception as ex:
                print(str(ex))

        if annotationDel_:
            mousePoint = self.mapSceneToView(ev.scenePos())
            x = mousePoint.x()
            y = mousePoint.y()
            try:
                model.AnnotationDel(x=x, y=y)
            except Exception as ex:
                print(str(ex))

        if periodogram_:
            mousePoint = self.mapSceneToView(ev.scenePos())
            x = mousePoint.x()
            y = mousePoint.y()
            try:
                PeriodogramDialog(model=model, x=x, y=y)
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
                    model.DrawMarkTime(self.pos1)     #temporary line on x mark
                elif ev.isFinish():  #release from dragging
                    model.RemoveMarkTime()   #remove line on x mark
                    a = self.mapSceneToView(ev.scenePos())
                    self.pos2 = a.x()              #final x mark
                    if self.pos1 is not None:
                        if self.pos2 < self.pos1:     #marking from right to left
                            interval = [round(self.pos2, 3), round(self.pos1, 3)]
                        else:               #marking from left to right
                            interval = [round(self.pos1, 3), round(self.pos2, 3)]
                        color = intervalsDict_[intervalType_]['color']
                        intervalsDict_[intervalType_]['counts'] += 1
                        model.IntervalAdd(interval, intervalType_, color)
                        model.refreshScreen()



## Main file definitions -------------------------------------------------------
# If it was imported as a module
def main(filename):
    app = QCoreApplication.instance()
    if app is None:
        app = QApplication(sys.argv)  #instantiate a QtGui (holder for the app)
    ex = Application(filename)
    sys.exit(app.exec_())

# If called from a command line, e.g.: $ python ecog_ts_gui.py
if __name__ == '__main__':
    app = QApplication(sys.argv)  #instantiate a QtGui (holder for the app)
    if len(sys.argv)==1:
        fname = ''
    else:
        fname = sys.argv[1]
    ex = Application(filename=fname)
    sys.exit(app.exec_())
