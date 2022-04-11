#! /usr/bin/env python
# -*- coding: utf-8 -*-
import os
import sys
import time
import tempfile

import pathlib
import subprocess
import datetime
import threading

# https://python-catalin.blogspot.com/2018/11/python-qt5-tray-icon-example.html
# https://stackoverflow.com/questions/6389580/quick-and-easy-trayicon-with-python
# https://stackoverflow.com/questions/2430877/how-to-save-a-qpixmap-object-to-a-file
# https://stackoverflow.com/questions/17087123/writing-a-text-in-a-qpixmap/17087457
# https://stackoverflow.com/questions/13350631/simple-color-fill-qicons-in-qt
# https://stackoverflow.com/questions/41387576/change-the-color-and-font-of-qstring-or-qlineedit
# https://forum.qt.io/topic/61129/qpainter-how-to-draw-text-with-different-colors/2
# https://stackoverflow.com/questions/17819698/how-to-change-fontsize-on-drawtext
# https://stackoverflow.com/questions/37573143/qml-not-using-thin-font-weight
# https://stackoverflow.com/questions/50294652/how-to-create-pyqtsignals-dynamically
from PyQt5.QtGui import QPixmap, QPainter, QFont, QIcon
from PyQt5.QtCore import Qt, QPoint, pyqtSignal, QFile, QTimer
from PyQt5.QtWidgets import QApplication, QSystemTrayIcon, QMenu, QAction

from PyQt5 import QtGui, QtCore, QtWidgets, QtMultimedia
from PyQt5.QtCore import QSize, QSettings
from PyQt5.QtWidgets import QMessageBox, QPushButton, QMainWindow, QLabel, QGridLayout, QWidget

CURRENT_DIR = os.path.dirname(os.path.realpath(__file__))

ALARM_TIMEOUT = 40
SHOW_WINDOW_INTERVAL = 1800
# ALARM_TIMEOUT = 2
# SHOW_WINDOW_INTERVAL = 2


def main():
    app = QApplication( [] )
    app.setQuitOnLastWindowClosed( False )

    global mainWin
    mainWin = MainWindow()

    global mainTray
    mainTray = QSystemTrayIconListener()

    mainWin.connectTray()
    app.exec_()


class TemporaryFileContent:
    def __init__(self, content, suffix='.vbs'):
        self.file = tempfile.NamedTemporaryFile(mode='w', delete=False, suffix=suffix)
        with self.file as f:
            f.write(content)
            f.flush()

    @property
    def filename(self):
        return pathlib.Path(self.file.name)

    def __enter__(self):
        return self.filename

    def __exit__(self, type, value, traceback):
        # os.unlink(self.filename)
        pass


def speak(text):
    with TemporaryFileContent(f"""
Set speech = CreateObject("sapi.spvoice")
Set speech.Voice = speech.GetVoices.Item(0)

' Speech speed from -10 to 10
speech.Rate = -2
speech.Volume = 100

speech.Speak "{text}"
    """) as filename:
        subprocess.Popen(f'wscript "{filename}"')
        threading.Timer( 10, os.unlink, args=(filename) )


# Copied python implementation to Start it as a daemon to not block qt from exiting!
class Timer(threading.Thread):
    """Call a function after a specified number of seconds:
            t = Timer(30.0, f, args=None, kwargs=None)
            t.start()
            t.cancel()     # stop the timer's action if it's still waiting
    """
    def __init__(self, interval, function, args=None, kwargs=None):
        threading.Thread.__init__(self, daemon=True)
        self.interval = interval
        self.function = function
        self.args = args if args is not None else []
        self.kwargs = kwargs if kwargs is not None else {}
        self.finished = threading.Event()

    def cancel(self):
        """Stop the timer if it hasn't finished yet."""
        self.finished.set()

    def run(self):
        self.finished.wait(self.interval)
        if not self.finished.is_set():
            self.function(*self.args, **self.kwargs)
        self.finished.set()


class MainWindow(QMainWindow):
    runEyeRestLoop = pyqtSignal( [] )

    def __init__(self):
        QMainWindow.__init__(self)
        name = "Eye resting stopwatch"
        author = "Eye strain user"
        self.setWindowTitle(name)
        self.setMinimumSize(QSize(300, 200))

        self.setWindowIcon(QtGui.QIcon(os.path.join(CURRENT_DIR, 'login.png')))
        self.setGeometry(100, 100, 400, 500)
        # pybutton = QPushButton('Show messagebox', self)
        # pybutton.clicked.connect(self.clickMethod)
        # pybutton.resize(200,64)
        # pybutton.move(50, 50)

        self.settings = QSettings( author, name) 
        self.resize(self.settings.value("size", QSize(400, 500)))
        self.move(self.settings.value("pos", QPoint(50, 50)))

        self.eyeRestCounterSetup()

    def eyeRestCounterSetup(self):
        # https://www.geeksforgeeks.org/pyqt5-digital-stopwatch/
        self.eyeRestCounterValue = 0
        self.incrementEyeRestCounter = False

        self.eyeRestCounterLabel = QLabel(self)
        self.eyeRestCounterLabel.setGeometry(75, 100, 250, 70)
        self.eyeRestCounterLabel.setStyleSheet("border : 4px solid black;")
        self.eyeRestCounterLabel.setText(str(self.eyeRestCounterValue))
        self.eyeRestCounterLabel.setFont(QFont('Arial', 25))
        self.eyeRestCounterLabel.setAlignment(Qt.AlignCenter)

        startEyeRestButton = QPushButton("Start Eye Rest", self)
        startEyeRestButton.setGeometry(125, 250, 150, 40)
        startEyeRestButton.pressed.connect(self.startEyeRest)

        pauseEyeRestButton = QPushButton("Pause Eye Rest", self)
        pauseEyeRestButton.setGeometry(125, 300, 150, 40)
        pauseEyeRestButton.pressed.connect(self.pauseEyeRest)

        resetEyeRestButton = QPushButton("Reset Eye Rest", self)
        resetEyeRestButton.setGeometry(125, 350, 150, 40)
        resetEyeRestButton.pressed.connect(self.resetEyeRest)

        timerEyeRest = QTimer(self)
        timerEyeRest.timeout.connect(self.updateTime)
        timerEyeRest.start(1000)
        self.isEyeRestPlaying = False

    def connectTray(self):
        self.runEyeRestLoop.connect( mainTray.nextEyeRestLoop )
        self.runEyeRestLoop.emit()

    def clickMethod(self):
        QMessageBox.about(self, "Title", "Message")

    def closeEvent(self, event):
        self.runEyeRestLoop.emit()
        event.accept()

    def keyPressEvent(self, event):
        if event.key() == QtCore.Qt.Key_Escape:
            self.close()
        if event.key() in ( QtCore.Qt.Key_Return, QtCore.Qt.Key_Enter):
            self.resetEyeRest()

    def showUp(self):
        self.show()
        self.raise_()
        self.activateWindow()

    def exitApplication(self):
        self.settings.setValue("size", self.size())
        self.settings.setValue("pos", self.pos())
        exit()

    def updateTime(self):
        seconds = self.eyeRestCounterValue
        if self.incrementEyeRestCounter:
            self.eyeRestCounterValue+= 1
            if seconds > ALARM_TIMEOUT and not self.isEyeRestPlaying:
                self.isEyeRestPlaying = True
                filename = os.path.join(CURRENT_DIR, "Alarm06.wav")
                QtMultimedia.QSound.play(filename)
            if seconds == 10:
                speak(f"{seconds} seconds")
            if seconds == 20:
                speak(f"{seconds} seconds")
            if seconds == 30:
                speak(f"{seconds} seconds")
            self.eyeRestCounterLabel.setText(str(seconds))

    def startEyeRest(self):
        self.incrementEyeRestCounter = True
        self.eyeRestCounterLabel.setStyleSheet("background-color:lightgreen")

    def pauseEyeRest(self):
        self.incrementEyeRestCounter = False
        self.eyeRestCounterLabel.setStyleSheet("background-color:lightblue")

    def resetEyeRest(self):
        self.isEyeRestPlaying = False
        self.eyeRestCounterValue = 0
        self.eyeRestCounterLabel.setText(str(self.eyeRestCounterValue))

        if self.incrementEyeRestCounter:
            self.eyeRestCounterLabel.setStyleSheet("background-color:lightgreen")
        else:
            self.eyeRestCounterLabel.setStyleSheet("background-color:")


class QSystemTrayIconListener(QSystemTrayIcon):
    updateTrayIconText = pyqtSignal( [] )
    showMainWindow = pyqtSignal( [] )

    def __init__(self, *args, **kwargs):
        self.trayIconPixmap = None
        self.trayIconFont = None
        self.trayIconPainter = None
        self.trayIcon = None
        super(QSystemTrayIconListener, self).__init__( *args, **kwargs )

        self.eyeRestTimer = None
        self.createTrayMenu()
        self.setTrayText()

        self.updateTrayIconText.connect( self.setTrayText )
        self.showMainWindow.connect( mainWin.show )

        threading.Thread( target=self.continuallyUpdateTrayIcon, daemon=True ).start()

    def nextEyeRestLoop(self):
        if self.eyeRestTimer:
            self.eyeRestTimer.cancel()

        self.eyeRestTimer = Timer( SHOW_WINDOW_INTERVAL, self.showMainWindow.emit )
        self.eyeRestTimer.start()
        # last_show_up = datetime.datetime.now().date()
        # while True:
        #     now = datetime.datetime.now().date()
        #     if now - last_show_up > datetime.timedelta(minutes=30):
        #         last_show_up = now
        #         self.showMainWindow.emit()

    def continuallyUpdateTrayIcon(self):
        while True:
            self.updateTrayIconText.emit()
            time.sleep(1)

    def setTrayText(self):
        timenow = datetime.datetime.now()
        trayIconPixmap = QPixmap(100,100)
        trayIconPixmap.fill( Qt.GlobalColor.transparent )

        # QFont::Thin
        # QFont::ExtraLight
        # QFont::Light
        # QFont::Normal
        # QFont::Medium
        # QFont::DemiBold
        # QFont::Bold
        # QFont::ExtraBold
        # QFont::Black
        # https://doc.qt.io/qt-5/qfont.html#Weight-enum
        trayIconFont = QFont( "SansSerif" )
        trayIconFont.setWeight( QFont.Thin )
        trayIconFont.setPointSize( 73 )

        trayIconPainter = QPainter( trayIconPixmap )
        trayIconPainter.setPen( Qt.white )
        trayIconPainter.setFont( trayIconFont )
        trayIconPainter.drawText( QPoint( -5, 79 ), "%02d" % timenow.date().day )

        # file = QFile( "yourFile.png" )
        # file.open( QIODevice.WriteOnly )
        # trayIconPixmap.save( file, "PNG" )

        trayIcon = QIcon( trayIconPixmap )
        self.setIcon( trayIcon )
        self.setToolTip( str( timenow )[:-7] )
        self.setVisible( True )

        if self.trayIconPainter:
            self.trayIconPainter.end()

        self.trayIconPixmap = trayIconPixmap
        self.trayIconFont = trayIconFont
        self.trayIconPainter = trayIconPainter
        self.trayIcon = trayIcon

    def createTrayMenu(self):
        self.exitAction = QAction( "&Exit" )
        self.mainWindowAction = QAction( "&Main Window" )

        self.trayMenu = QMenu()
        self.trayMenu.addAction( self.mainWindowAction )
        self.trayMenu.addAction( self.exitAction )

        self.mainWindowAction.triggered.connect( mainWin.showUp )
        self.exitAction.triggered.connect( mainWin.exitApplication )
        self.setContextMenu( self.trayMenu )

        self.activated.connect(self.systemIconClick)

    def systemIconClick(self, reason):
        if reason == QSystemTrayIcon.Trigger:
            if mainWin.isVisible():
                mainWin.hide()
            else:
                mainWin.showUp()


if __name__ == "__main__":
    main()

