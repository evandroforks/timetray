#! /usr/bin/env python
# -*- coding: utf-8 -*-
import os
import sys
import time
import tempfile

import argparse
import pathlib
import subprocess
import datetime
import threading

import pytest
from pytest import approx

# Python 3.8.1
# PyQt5
# python -m pip install pycaw pytest
# https://stackoverflow.com/questions/53026985/the-ordinal-242-could-not-be-located-in-the-dynamic-link-library-anaconda3-libra
os.environ["PATH"] = f'F:\\Python\\Library\\bin;{os.environ["PATH"]}'

from ctypes import cast, POINTER
from comtypes import CLSCTX_ALL
from pycaw.pycaw import AudioUtilities, IAudioEndpointVolume

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

ALARM_TIMEOUT = 4  # * 10
SHOW_WINDOW_INTERVAL = 1800
# ALARM_TIMEOUT = 2
# SHOW_WINDOW_INTERVAL = 2

g_setVolumeBase = """
import sys
import time

from ctypes import cast, POINTER
from comtypes import CLSCTX_ALL
from pycaw.pycaw import AudioUtilities, IAudioEndpointVolume

devices = AudioUtilities.GetSpeakers()
interface = devices.Activate(
    IAudioEndpointVolume._iid_, CLSCTX_ALL, None
)"""

def main():
    argumentsNamespace = g_argumentParser.parse_args()

    run_tests = argumentsNamespace.run_tests
    if isinstance(run_tests, list):
        args = [sys.argv[0], '-vv', '-rP']
        if run_tests:
            args.append(f"-k {' '.join(run_tests)}")
        print(f'Running tests {args}')
        pytest.main(args)
        return

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
        a = subprocess.Popen(f'wscript "{filename}"')
        ar = a.communicate()
        # print(f'ar {ar}.')
        threading.Timer( 10, os.unlink, args=(filename) )


def runpython(text):
    with TemporaryFileContent(text) as filename:
        process = subprocess.Popen(f'python "{filename}"', stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
        stdout, stderr = process.communicate()
        stdout = stdout.decode("UTF-8", errors='replace').replace('\r\n', '\n').rstrip(' \n\r')
        threading.Timer( 1, os.unlink, args=(filename) )
        stderr = stderr.decode("UTF-8", errors='replace').replace('\r\n', '\n').rstrip(' \n\r')
        assert process.returncode == 0, f"process.returncode {process.returncode}, {stderr}, {stdout}."
        if stderr:
            print(stderr, file=sys.stderr)
        return stdout


def getSystemVolume():
    result = runpython(f"""
{g_setVolumeBase}
volume = cast(interface, POINTER(IAudioEndpointVolume))
print(volume.GetMasterVolumeLevelScalar())
        """
    )
    return float(result)


def test_get_system_volume():
    assert type(getSystemVolume()) == float


def setSystemVolume(endVolume):
    result = runpython(f"""
{g_setVolumeBase}
systemVolume = cast(interface, POINTER(IAudioEndpointVolume))
startVolume = int(systemVolume.GetMasterVolumeLevelScalar() * 100)
endVolume = int({endVolume} * 100)
for volume in range(startVolume, endVolume, 5):
    # print(f'volume {{volume}}.', file=sys.stderr)
    systemVolume.SetMasterVolumeLevelScalar(volume/100, None)
    time.sleep(0.1)
systemVolume.SetMasterVolumeLevelScalar({endVolume}, None)
print(systemVolume.GetMasterVolumeLevelScalar())
        """
    )
    return float(result)


def test_get_system_volume():
    level = 0.20
    assert setSystemVolume(level) == approx(level)


def setApplicationVolume(endVolume, processName):
    result = runpython(f"""
{g_setVolumeBase}
sessions = AudioUtilities.GetAllSessions()
for session in sessions:
    if session.Process and session.Process.name() == "{processName}":
        volumeDevice = session.SimpleAudioVolume
        # print(f"{{session.Process.name()}} volumeDevice.GetMute(): {{volumeDevice.GetMute()}}, volume {{volumeDevice.GetMasterVolume()}}.", file=sys.stderr)
        startVolume = int(volumeDevice.GetMasterVolume() * 100)
        endVolume = int({endVolume} * 100)
        for volume in range(startVolume, endVolume, 10):
            # print(f'volume {{volume}}.', file=sys.stderr)
            volumeDevice.SetMasterVolume(volume/100, None)
            time.sleep(0.1)
        volumeDevice.SetMasterVolume({endVolume}, None)
        print(volumeDevice.GetMasterVolume())
        """
    )
    return float(result)


def test_set_application_volume():
    level = 0.2
    assert setApplicationVolume(level, "AIMP.exe") == approx(level)
    level = 1
    assert setApplicationVolume(level, "AIMP.exe") == approx(level)


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
        self.defaultSystemVolume = None

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
        testtime = 10
        # testtime = 1
        seconds = self.eyeRestCounterValue
        if self.incrementEyeRestCounter:
            self.eyeRestCounterValue+= 1
            if seconds > int(ALARM_TIMEOUT * testtime) and not self.isEyeRestPlaying:
                self.isEyeRestPlaying = True
                filename = os.path.join(CURRENT_DIR, "Alarm06.wav")
                QtMultimedia.QSound.play(filename)
            if seconds == int(0.1 * testtime):
                self.defaultSystemVolume = getSystemVolume()
                setApplicationVolume(self.defaultSystemVolume * 0.7, "AIMP.exe")
                setSystemVolume(self.defaultSystemVolume + 0.5)
                # a = subprocess.Popen(r'''"D:\\User\Documents\\NirSoft\SoundVolumeView.exe" /ChangeVolume "AIMP3" -75''')
                # b = subprocess.Popen(r'''"D:\\User\Documents\\NirSoft\SoundVolumeView.exe" /ChangeVolume "Speakers" "+50"''')
                # ar = a.communicate()
                # br = b.communicate()
                # # print(f"ar {ar}, br {br}.")
            if seconds == int(1.0 * testtime):
                speak(f"{seconds} seconds")
            if seconds == int(2.0 * testtime):
                speak(f"{seconds} seconds")
            if seconds == int(3.0 * testtime):
                speak(f"{seconds} seconds")
            if seconds == int(4.6 * testtime):
                setSystemVolume(self.defaultSystemVolume)
                setApplicationVolume(1, "AIMP.exe")
                # a = subprocess.Popen(r'''"D:\\User\Documents\\NirSoft\SoundVolumeView.exe" /ChangeVolume "Speakers" "-50"''')
                # b = subprocess.Popen(r'''"D:\User\Documents\NirSoft\SoundVolumeView.exe" /ChangeVolume "AIMP3" "+75"''')
                # ar = a.communicate()
                # br = b.communicate()
                # # print(f"ar {ar}, br {br}.")
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

        if mainWin.incrementEyeRestCounter:
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


g_argumentParser = argparse.ArgumentParser(
        description = \
"""
Show the time as a tray icon.
""",
        formatter_class=argparse.RawTextHelpFormatter,
        add_help=False,
    )

# https://stackoverflow.com/questions/35847084/customize-argparse-help-message
g_argumentParser.add_argument( "-h", "--help", action="store_true",
help= """
Show this help message and exit.
""" )

g_argumentParser.add_argument( "-t", "--run-tests", action="store", nargs='*', default=None,
        help=
"""
Run tests instead of the main application. Accepts a pytest test filter to pass to -k pytest option.
""" )

if __name__ == "__main__":
    main()

