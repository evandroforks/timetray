#! /usr/bin/env python
# -*- coding: utf-8 -*-
import os
import sys
import time
import tempfile
import math

import argparse
import shlex
import pathlib
import subprocess
import datetime
import threading

import pytest
import inspect
from pytest import approx

# Python 3.8.1
# PyQt5
# python -m pip install pycaw pytest
# https://stackoverflow.com/questions/53026985/the-ordinal-242-could-not-be-located-in-the-dynamic-link-library-anaconda3-libra
os.environ["PATH"] = f'F:\\Python\\Library\\bin;{os.environ["PATH"]}'

from numbers import Number
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

g_run_tests = [False]
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
        args = [sys.argv[0], '-vvv', '-rP', '--capture=no']
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


@pytest.fixture(scope="session", autouse=True)
def enable_verbose(request):
    g_run_tests[0] = request.config.getoption("--verbose")


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


def run_process(command_line, directory=None, verbose=False):
    """ https://gist.github.com/evandrocoan/916976490aeecc7b93e658084bb2834d """
    stdout_lines = []
    stderr_lines = []
    command = shlex.split(command_line)

    if verbose:
        print('run_process command', command, directory, file=sys.stderr)

    with subprocess.Popen(
        command,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        cwd=directory,
        shell=True,
    ) as process:
        def capturestderr():
            while True:
                line = process.stderr.readline()
                if not line:
                    break
                line = line.decode("UTF-8", errors='replace')
                line = line.replace('\r\n', '\n').rstrip(' \n\r')
                stderr_lines.append(line)

                if verbose:
                    print(line, file=sys.stderr)

        thread = threading.Thread(target=capturestderr, daemon=True)
        thread.start()

        while True:
            line = process.stdout.readline()
            if not line:
                break

            line = line.decode("UTF-8", errors='replace')
            line = line.replace('\r\n', '\n').rstrip(' \n\r')
            stdout_lines.append(line)

            if verbose:
                print(line, file=sys.stderr)

        thread.join()

    return process, stdout_lines, stderr_lines


def runpython(text):
    with TemporaryFileContent(text) as filename:
        process, stdout, stderr = run_process(f'python -u "{filename}"', verbose=g_run_tests[0])
        stdout = "\n".join(stdout)
        stderr = "\n".join(stderr)
        assert process.returncode == 0, f"process.returncode {process.returncode}, {stdout}, {stderr}."
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


def test_set_system_volume():
    level = 0.20
    defaultSystemVolume = getSystemVolume()
    assert setSystemVolume(level) == approx(level)
    assert setSystemVolume(defaultSystemVolume) == approx(defaultSystemVolume)


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


def setSystemAndApplicationVolume(defaultSystemVolume, volumeIncrease, applicationName, reverse=False):
    result = runpython(f"""
{g_setVolumeBase}
import math
from itertools import zip_longest

defaultSystemVolume = {defaultSystemVolume}
volumeIncrease = {volumeIncrease}
applicationName = "{applicationName}"
reverse = {reverse}

{inspect.getsource(volumeConversion)}

sessions = AudioUtilities.GetAllSessions()
for session in sessions:
    # print(f"{{{{session.Process.name() if session.Process else session.Process}}}} volumeDevice.GetMute(): {{{{volumeDevice.GetMute()}}}}, volume {{{{volumeDevice.GetMasterVolume()}}}}.", file=sys.stderr)
    if session.Process and session.Process.name() == applicationName:
        volumeDevice = session.SimpleAudioVolume
        devices = AudioUtilities.GetSpeakers()
        interface = devices.Activate(IAudioEndpointVolume._iid_, CLSCTX_ALL, None)
        systemDevice = cast(interface, POINTER(IAudioEndpointVolume))
        systemRangeFull = volumeConversion(defaultSystemVolume, volumeIncrease, 0.3)

        if reverse:
            systemRangeFull = list(reversed(systemRangeFull))

        for systemVolume, applicationVolume in systemRangeFull:
            # print(f'systemVolume {{{{systemVolume:.2f}}}}, applicationVolume {{{{applicationVolume:.2f}}}}.', file=sys.stderr)
            if reverse:
                volumeDevice.SetMasterVolume(applicationVolume/100, None)
                systemDevice.SetMasterVolumeLevelScalar(systemVolume/100, None)
            else:
                systemDevice.SetMasterVolumeLevelScalar(systemVolume/100, None)
                volumeDevice.SetMasterVolume(applicationVolume/100, None)
            time.sleep(0.1)

        print(volumeDevice.GetMasterVolume())
        print(systemDevice.GetMasterVolumeLevelScalar())
        break
""".format())
    return result


def test_set_volume_evenly():
    defaultSystemVolume = getSystemVolume()
    setSystemAndApplicationVolume(defaultSystemVolume, 0.5, "AIMP.exe")
    time.sleep(2)
    setSystemAndApplicationVolume(defaultSystemVolume, 0.5, "AIMP.exe", reverse=True)


def volumeConversion(defaultSystemVolume, volumeIncrease, factor):
    # https://en.wikipedia.org/wiki/Sigmoid_function
    # https://www.desmos.com/calculator/lew1cvqu91
    def sigmoid(number):
        number = number
        reverse = abs(number - 100)
        extra = math.sin( number / 100 + 1.5 ) - 0.6
        # print("extra %s, reverse %s." % (extra, reverse), file=sys.stderr)
        extra = extra if extra > 0 and factor else 0
        number = number + reverse * factor - extra * 100
        if number > 100: return 100
        if number < 0: return 0
        return int(number * 100) / 100

    def ceiling(number):
        if number > 100: return 100
        return int(number * 100) / 100

    if defaultSystemVolume > 1: defaultSystemVolume = 1
    if defaultSystemVolume < 0: defaultSystemVolume = 0

    increase = defaultSystemVolume + volumeIncrease
    if increase > 1: volumeIncrease = 1 - defaultSystemVolume
    if increase < 0: volumeIncrease = -defaultSystemVolume

    stepSystem = 500
    startSystemVolume = int(defaultSystemVolume * 10_000)
    endSystemVolume = int((defaultSystemVolume + volumeIncrease) * 10_000)

    if endSystemVolume < startSystemVolume: 
        stepSystem *= -1
        endSystemVolume -= 1
    else:
        endSystemVolume += 1

    systemRangeFull = []
    for volume in range(startSystemVolume, endSystemVolume, stepSystem):
        if volume > 0:
            systemRangeFull.append((ceiling(volume/100), sigmoid(defaultSystemVolume / volume * 1_000_000 )))
        else:
            systemRangeFull.append((0, 100))
    return systemRangeFull


def test_volume_convertion_from01to99():
    assert volumeConversion(0.01, 0.99, 0) == [
        (1.0, 100.0),
        (6.0, 16.66),
        (11.0, 9.09),
        (16.0, 6.25),
        (21.0, 4.76),
        (26.0, 3.84),
        (31.0, 3.22),
        (36.0, 2.77),
        (41.0, 2.43),
        (46.0, 2.17),
        (51.0, 1.96),
        (56.0, 1.78),
        (61.0, 1.63),
        (66.0, 1.51),
        (71.0, 1.4),
        (76.0, 1.31),
        (81.0, 1.23),
        (86.0, 1.16),
        (91.0, 1.09),
        (96.0, 1.04),
    ]


def test_volume_convertion_from10to60_factor03():
    assert volumeConversion(0.1, 0.5, 0.3) == [
        (10.0, 100.0),
        (15.0, 53.9),
        (20.0, 34.07),
        (25.0, 23.36),
        (30.0, 16.75),
        (35.0, 12.3),
        (40.0, 9.1),
        (45.0, 6.69),
        (50.0, 4.83),
        (55.0, 3.34),
        (60.0, 2.12),
    ]


def test_volume_convertion_from01to99_factor03():
    assert volumeConversion(0.01, 0.99, 0.3) == [
        (1.0, 100.0),
        (6.0, 2.12),
        (11.0, 0),
        (16.0, 0),
        (21.0, 0),
        (26.0, 0),
        (31.0, 0),
        (36.0, 0),
        (41.0, 0),
        (46.0, 0),
        (51.0, 0),
        (56.0, 0),
        (61.0, 0),
        (66.0, 0),
        (71.0, 0),
        (76.0, 0),
        (81.0, 0),
        (86.0, 0),
        (91.0, 0),
        (96.0, 0),
    ]


def test_volume_convertion_invalid_increase():
    assert volumeConversion(0.2, 0.9, 0) == [
        (20.0, 100.0),
        (25.0, 80.0),
        (30.0, 66.66),
        (35.0, 57.14),
        (40.0, 50.0),
        (45.0, 44.44),
        (50.0, 40.0),
        (55.0, 36.36),
        (60.0, 33.33),
        (65.0, 30.76),
        (70.0, 28.57),
        (75.0, 26.66),
        (80.0, 25.0),
        (85.0, 23.52),
        (90.0, 22.22),
        (95.0, 21.05),
        (100.0, 20.0),
    ]


def test_volume_convertion_invalid_decrease():
    assert volumeConversion(0.8, -0.9, 0) == [
        (80.0, 100.0),
        (75.0, 100),
        (70.0, 100),
        (65.0, 100),
        (60.0, 100),
        (55.0, 100),
        (50.0, 100),
        (45.0, 100),
        (40.0, 100),
        (35.0, 100),
        (30.0, 100),
        (25.0, 100),
        (20.0, 100),
        (15.0, 100),
        (10.0, 100),
        (5.0, 100),
        (0, 100)
    ]


def test_volume_convertion_from20_to80():
    assert volumeConversion(0.2, 0.8, 0) == [
        (20.0, 100.0),
        (25.0, 80.0),
        (30.0, 66.66),
        (35.0, 57.14),
        (40.0, 50.0),
        (45.0, 44.44),
        (50.0, 40.0),
        (55.0, 36.36),
        (60.0, 33.33),
        (65.0, 30.76),
        (70.0, 28.57),
        (75.0, 26.66),
        (80.0, 25.0),
        (85.0, 23.52),
        (90.0, 22.22),
        (95.0, 21.05),
        (100.0, 20.0),
    ]


def test_volume_convertion_from20_factor01():
    assert volumeConversion(0.2, 0.8, 0.1) == [
        (20.0, 100.0),
        (25.0, 67.42),
        (30.0, 47.23),
        (35.0, 33.7),
        (40.0, 24.07),
        (45.0, 16.89),
        (50.0, 11.36),
        (55.0, 6.98),
        (60.0, 3.42),
        (65.0, 0.48),
        (70.0, 0),
        (75.0, 0),
        (80.0, 0),
        (85.0, 0),
        (90.0, 0),
        (95.0, 0),
        (100.0, 0),
    ]


def test_volume_convertion_from20_factor02():
    assert volumeConversion(0.2, 0.8, 0.2) == [
        (20.0, 100.0),
        (25.0, 69.42),
        (30.0, 50.56),
        (35.0, 37.98),
        (40.0, 29.07),
        (45.0, 22.45),
        (50.0, 17.36),
        (55.0, 13.34),
        (60.0, 10.09),
        (65.0, 7.4),
        (70.0, 5.15),
        (75.0, 3.24),
        (80.0, 1.6),
        (85.0, 0.17),
        (90.0, 0),
        (95.0, 0),
        (100.0, 0),
    ]



def test_volume_convertion_from20_factor03():
    assert volumeConversion(0.2, 0.8, 0.3) == [
        (20.0, 100.0),
        (25.0, 71.42),
        (30.0, 53.9),
        (35.0, 42.27),
        (40.0, 34.07),
        (45.0, 28.01),
        (50.0, 23.36),
        (55.0, 19.71),
        (60.0, 16.75),
        (65.0, 14.33),
        (70.0, 12.3),
        (75.0, 10.57),
        (80.0, 9.1),
        (85.0, 7.82),
        (90.0, 6.69),
        (95.0, 5.71),
        (100.0, 4.83),
    ]


def test_volume_convertion_from50_factor03():
    assert volumeConversion(0.5, 0.8, 0.3) == [
        (50.0, 100.0),
        (55.0, 86.76),
        (60.0, 76.02),
        (65.0, 67.26),
        (70.0, 59.99),
        (75.0, 53.9),
        (80.0, 48.71),
        (85.0, 44.26),
        (90.0, 40.41),
        (95.0, 37.03),
        (100.0, 34.07),
    ]


def test_volume_convertion_from80_factor03():
    assert volumeConversion(0.8, 0.8, 0.3) == [
        (80.0, 100.0),
        (85.0, 91.42),
        (90.0, 83.86),
        (95.0, 77.24),
        (100.0, 71.42),
    ]


@pytest.mark.skip(reason="Comment this to plot the graphs")
def test_volume_convertion_plot_graphs():
    numbers = volumeConversion(0.2, 0.8, 0.1)
    numbers2 = volumeConversion(0.2, 0.8, 0.2)
    numbers3 = volumeConversion(0.2, 0.8, 0.0)

    print(f'\n{numbers}\n{numbers2}\n{numbers3}')

    #  Cannot mix incompatible Qt library (version 0x50907) with this library
    result = runpython(f"""
import matplotlib.pyplot as pyplot
numbers = {numbers}
numbers2 = {numbers2}
numbers3 = {numbers3}
x = [item[0] for item in numbers]
y = [item[1] for item in numbers]
x2 = [item[0] for item in numbers2]
y2 = [item[1] for item in numbers2]
x3 = [item[0] for item in numbers3]
y3 = [item[1] for item in numbers3]
pyplot.plot(x, y)
pyplot.plot(x2, y2)
pyplot.plot(x3, y3)
pyplot.xlabel('x - axis')
pyplot.ylabel('y - axis')
pyplot.title('My first graph!')
pyplot.show()
""" )


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

    def clickMethod(self):
        QMessageBox.about(self, "Title", "Message")

    def closeEvent(self, event):
        if mainTray.eyeRestTimer is None and self.incrementEyeRestCounter:
            self.runEyeRestLoop.emit()
        event.accept()

    def keyPressEvent(self, event):
        if event.key() == QtCore.Qt.Key_Escape:
            self.close()
        if event.key() in ( QtCore.Qt.Key_Return, QtCore.Qt.Key_Enter):
            self.resetEyeRest()
            threading.Thread(target=speak, args=(f"beep",), daemon=True).start()
            self.close()

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
                threading.Thread(target=setSystemAndApplicationVolume, 
                    args=(self.defaultSystemVolume, 0.5, "AIMP.exe"), daemon=True).start()
                # a = subprocess.Popen(r'''"D:\\User\Documents\\NirSoft\SoundVolumeView.exe" /ChangeVolume "AIMP3" -75''')
                # b = subprocess.Popen(r'''"D:\\User\Documents\\NirSoft\SoundVolumeView.exe" /ChangeVolume "Speakers" "+50"''')
                # ar = a.communicate()
                # br = b.communicate()
                # # print(f"ar {ar}, br {br}.")
            if seconds == int(1.0 * testtime):
                threading.Thread(target=speak, args=(f"{seconds} seconds",), daemon=True).start()
            if seconds == int(2.0 * testtime):
                threading.Thread(target=speak, args=(f"{seconds} seconds",), daemon=True).start()
            if seconds == int(3.0 * testtime):
                threading.Thread(target=speak, args=(f"{seconds} seconds",), daemon=True).start()
            if seconds == int(4.6 * testtime):
                threading.Thread(target=setSystemAndApplicationVolume, 
                    args=(self.defaultSystemVolume, 0.5, "AIMP.exe", True), daemon=True).start()
                # a = subprocess.Popen(r'''"D:\\User\Documents\\NirSoft\SoundVolumeView.exe" /ChangeVolume "Speakers" "-50"''')
                # b = subprocess.Popen(r'''"D:\User\Documents\NirSoft\SoundVolumeView.exe" /ChangeVolume "AIMP3" "+75"''')
                # ar = a.communicate()
                # br = b.communicate()
                # # print(f"ar {ar}, br {br}.")
            if seconds == int(5.6 * testtime):
                self.runEyeRestLoop.emit()
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

    def showMainWindowCallback(self):
        self.showMainWindow.emit()
        self.eyeRestTimer = None

        eyeRestTimer = Timer( 180, self.nextEyeRestLoop )
        eyeRestTimer.start()

    def nextEyeRestLoop(self):
        if self.eyeRestTimer:
            self.eyeRestTimer.cancel()

        if mainWin.incrementEyeRestCounter:
            self.eyeRestTimer = Timer( SHOW_WINDOW_INTERVAL, self.showMainWindowCallback )
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
    )

g_argumentParser.add_argument( "-t", "--run-tests", action="store", nargs='*', default=None,
        help=
"""
Run tests instead of the main application. Accepts a pytest test filter to pass to -k pytest option.
""" )

if __name__ == "__main__":
    main()

