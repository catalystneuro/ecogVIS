# -*- coding: utf-8 -*-
import sys
from PyQt5 import QtCore, QtGui, Qt

from PyQt5.QtCore import QCoreApplication
from PyQt5.QtWidgets import (QWidget, QLabel, QLineEdit, QMessageBox, QHBoxLayout,
    QTextEdit, QApplication, QPushButton, QVBoxLayout, QGroupBox, QFormLayout, QDialog,
    QRadioButton, QGridLayout)

import pyqtgraph as pg
from Function.subFunctions import ecogTSGUI
import os
import datetime
import numpy as np


model = None
selectBI_ = False
deleteBI_ = False
class Application(QWidget):
    keyPressed = QtCore.pyqtSignal(QtCore.QEvent)
    def __init__(self, filename, parent = None):
        global model

        # e.g.: /home/User/freesurfer_subjects/Subject_XX.nwb
        pathName = filename
        self.temp = []
        self.cursor_ = False
        self.channel_ = False
        self.error = None
        super(Application, self).__init__()
        self.keyPressed.connect(self.on_key)
        self.active_mode = 'default'
        self.init_gui()
        self.setWindowTitle('')
        self.show()
        #self.Maximized()

        '''
        run the main file
        '''
        parameters = {}
        parameters['pars'] = {'Figure': [self.win1, self.win2, self.win3]}
        parameters['editLine'] = {'qLine0': self.qline0, 'qLine1': self.qline1, 'qLine2': self.qline2, 'qLine3': self.qline3,
                  'qLine4': self.qline4}
#        '''
#        main file
#        '''
##        try:
        model = ecogTSGUI(self, pathName, parameters)
#
#        except Exception as ex:
#            self.log_error(str(ex))


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
            model.channel_Scroll_Up()
        elif event.key() == QtCore.Qt.Key_Down:
            model.channel_Scroll_Down()
        elif event.key() == QtCore.Qt.Key_Left:
            model.time_scroll(scroll=-1/3)
        elif event.key() == QtCore.Qt.Key_Right:
            model.time_scroll(scroll=1/3)

        event.accept()


    def init_gui(self):
        '''
        create a horizontal box layout
        '''
        hbox = QHBoxLayout()
        vbox = QVBoxLayout()

        groupbox1 = QGroupBox('Channels Plot')
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

        self.figure1 = self.win1.plot(x = [], y = [])

        self.win2.hideAxis('left')
        self.win2.hideAxis('bottom')
        self.win3.hideAxis('left')
        self.win3.hideAxis('bottom')

        form5layout = QGridLayout() #QVBoxLayout()
        form5layout.setSpacing(0.0)
        form5layout.setRowStretch(0, 1)
        form5layout.setRowStretch(1, 8)
        form5layout.setRowStretch(2, 1)
        form5layout.addWidget(self.win2)
        form5layout.addWidget(self.win1)
        form5layout.addWidget(self.win3)

        groupbox1.setLayout(form5layout)

        vbox.addWidget(groupbox1)


        '''
        Another vertical box layout
        '''
        vbox1 = QVBoxLayout()
        panel1 = QGroupBox('Panel')
        panel1.setFixedWidth(200)
        panel1.setFixedHeight(200)
        form1 = QFormLayout()
        self.push1 = QPushButton('Data Cursor On')
        self.push1.setFixedWidth(150)
        self.push1.clicked.connect(self.Data_Cursor)
        self.push2 = QPushButton('Get Channel')
        self.push2.clicked.connect(self.GetChannel)
        self.push2.setFixedWidth(150)
        self.push3 = QPushButton('Save Bad Intervals')
        self.push3.clicked.connect(self.SaveBadIntervals)
        self.push3.setFixedWidth(150)
        self.push4 = QPushButton('Select Bad Intervals')
        self.push4.clicked.connect(self.SelectBadInterval)
        self.push4.setFixedWidth(150)
        self.push4.setCheckable(True)
        self.push5 = QPushButton('Delete Bad Intervals')
        self.push5.clicked.connect(self.DeleteBadInterval)
        self.push5.setFixedWidth(150)
        self.push5.setCheckable(True)

        form1.addWidget(self.push1)
        form1.addWidget(self.push2)

        form1.addWidget(self.push4)
        form1.addWidget(self.push5)
        form1.addWidget(self.push3)
        panel1.setLayout(form1)

        panel2 = QGroupBox('Signal Type')
        panel2.setFixedWidth(200)
        panel2.setFixedHeight(100)
        form2 = QFormLayout()
        self.rbtn1 = QRadioButton('raw ECoG')
        self.rbtn1.setChecked(True)
        self.rbtn2 = QRadioButton('High Gamma')
        self.rbtn2.setChecked(False)
        form2.addWidget(self.rbtn1)
        form2.addWidget(self.rbtn2)
        panel2.setLayout(form2)

        panel3 = QGroupBox('Plot Controls')
        panel3.setFixedWidth(200)
        form3 = QGridLayout()
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
        self.pushbtn1_2 = QPushButton('Up')
        self.pushbtn1_2.clicked.connect(self.scroll_up)
        self.pushbtn2_1 = QPushButton('v')
        self.pushbtn2_1.clicked.connect(self.scroll_down)
        self.pushbtn2_2 = QPushButton('Down')
        self.pushbtn2_2.clicked.connect(self.scroll_down)

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

        form3.addWidget(self.enableButton, 0, 1)
        form3.addWidget(qlabel1, 1, 0)
        form3.addWidget(self.qline0, 1, 1)
        form3.addWidget(self.pushbtn1_1, 1, 2)
        form3.addWidget(self.pushbtn1_2, 1, 3)
        form3.addWidget(qlabel2, 2, 0)
        form3.addWidget(self.qline1, 2, 1)
        form3.addWidget(self.pushbtn2_1, 2, 2)
        form3.addWidget(self.pushbtn2_2, 2, 3)

        form3.addWidget(qlabel3, 4, 0, 1, 2)
        form3.addWidget(self.qline2, 4, 2, 1, 2)
        form3.addWidget(self.pushbtn3, 5, 0)
        form3.addWidget(self.pushbtn4, 5, 1)
        form3.addWidget(self.pushbtn6, 5, 2)
        form3.addWidget(self.pushbtn5, 5, 3)
        form3.addWidget(qlabel4, 6, 0)
        form3.addWidget(self.qline3, 6, 1)
        form3.addWidget(self.pushbtn7, 6, 2)
        form3.addWidget(self.pushbtn8, 6, 3)
        form3.addWidget(qlabel5, 7, 0)
        form3.addWidget(self.qline4, 7, 1)
        form3.addWidget(self.pushbtn9, 7, 2)
        form3.addWidget(self.pushbtn10, 7, 3)
        form3.addWidget(QLabel(), 8, 0)
        panel3.setLayout(form3)
        vbox1.addWidget(panel1)
        vbox1.addWidget(panel2)
        vbox1.addWidget(panel3)

        hbox.addLayout(vbox1)   #add panels first
        hbox.addLayout(vbox)    #add plots second
        self.setLayout(hbox)


    def check_status(self):
        global selectBI_
        global deleteBI_

        #self.active_mode = 'default', 'selectBI', 'deleteBI'
        if self.active_mode != 'selectBI':
            self.push4.setChecked(False)
            selectBI_ = False

        if self.active_mode != 'deleteBI':
            self.push5.setChecked(False)
            deleteBI_ = False

        if self.channel_:
            self.channel_ = False

        if self.cursor_:
            self.cursor_ = False


    def SaveBadIntervals(self):
        self.active_mode = 'default'
        self.check_status()
        try:
            model.pushSave()
        except Exception as ex:
            self.log_error(str(ex))


    def SelectBadInterval(self):
        global selectBI_

        #if self.temp != []:
        #    self.win1.removeItem(self.temp)

        if self.push4.isChecked():  #if button is pressed down
            self.active_mode = 'selectBI'
            self.check_status()
            selectBI_ = True
        else:
            self.active_mode = 'default'
            self.check_status()


    def DeleteBadInterval(self):
        global deleteBI_

        if self.push5.isChecked():  #if button is pressed down
            self.active_mode = 'deleteBI'
            self.check_status()
            deleteBI_ = True
            #self.win1.scene().sigMouseClicked.connect(self.DeleteBadInterval_coordinates)
        else:
            self.active_mode = 'default'
            self.check_status()


    # def DeleteBadInterval_coordinates(self, event):
    #     mousePoint = self.win1.plotItem.vb.mapSceneToView(event.scenePos())
    #     x = mousePoint.x()
    #     try:
    #         model.deleteInterval(round(x, 3))
    #     except Exception as ex:
    #         self.log_error(str(ex))


    def GetChannel(self):
        self.check_status()
        self.channel = self.win1.scene().sigMouseClicked.connect(self.get_channel)
        self.channel_ = True

    def get_channel(self, event):
        mousePoint = self.win1.plotItem.vb.mapSceneToView(event.scenePos())
        x = mousePoint.x()
        y = mousePoint.y()
        model.x_cur = x
        model.y_cur = y

        model.getChannel()



    def Data_Cursor(self):
        #self.check_status()
        if self.push1.text() == 'Data Cursor On':
            self.push1.setText('Data Cursor Off')
            self.p = self.win1.scene().sigMouseClicked.connect(self.get_cursor_position)
            self.cursor_ = True

        elif self.push1.text() == 'Data Cursor Off':
            self.win1.removeItem(self.p)
            self.push1.setText('Data Cursor On')
            self.cursor_ = False
            if self.temp != []:
                self.win1.removeItem(self.temp)
                self.temp = []

    def get_cursor_position(self, event):
#        pos = self.win1.plotItem.vb.mapSceneToView(event.scenePos())
        mousePoint = self.win1.plotItem.vb.mapSceneToView(event.scenePos())
        x = mousePoint.x()
        y = mousePoint.y()
        model.x_cur = x
        model.y_cur = y
        text = 'x:' + str(round(x, 2)) + '\n' + 'y:' + str(round(y, 2))

        t = pg.TextItem(text, color = pg.mkColor(70, 70, 70), border = pg.mkPen(200, 200, 200), fill = pg.mkBrush(250, 250, 150, 180))
        t.setPos(x, y)
        self.win1.addItem(t)
        if self.temp == []:
            self.temp = t
        else:
            try:
                self.win1.removeItem(self.temp)
                self.temp = t
            except Exception as ex:
                self.log_error(str(ex))
#        self.figure1.canvas.draw()


    ## Lower-Left buttons
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
        model.channel_Scroll_Up()

    def scroll_down(self):
        model.channel_Scroll_Down()

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



class CustomViewBox(pg.ViewBox):
    def __init__(self):
        pg.ViewBox.__init__(self)


    def mouseClickEvent(self, ev):
        global deleteBI_
        if deleteBI_:
            mousePoint = self.mapSceneToView(ev.scenePos())
            x = mousePoint.x()
            try:
                model.deleteInterval(round(x, 3))
            except Exception as ex:
                print(str(ex))
                #self.log_error(str(ex))



    def mouseDragEvent(self, ev):
        global selectBI_
        if selectBI_:
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
                            BadInterval = [round(self.pos2, 3), round(self.pos1, 3)]
                        else:               #marking from left to right
                            BadInterval = [round(self.pos1, 3), round(self.pos2, 3)]
                        model.addBadTimeSeg(BadInterval)
                        model.refreshScreen()



def main(filename):
    app = QCoreApplication.instance()
    if app is None:
        app = QApplication(sys.argv)
    ex = Application(filename)

    sys.exit(app.exec_())
