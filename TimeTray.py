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
    run_next_timeloop = pyqtSignal( [] )

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

        # https://www.geeksforgeeks.org/pyqt5-digital-stopwatch/
        self.time_counter = 0
        self.is_to_increment_counter = False
        self.label = QLabel(self)
        self.label.setGeometry(75, 100, 250, 70)

        self.label.setStyleSheet("border : 4px solid black;")
        self.label.setText(str(self.time_counter))
        self.label.setFont(QFont('Arial', 25))
        self.label.setAlignment(Qt.AlignCenter)

        start = QPushButton("Start", self)
        start.setGeometry(125, 250, 150, 40)
        start.pressed.connect(self.Start)

        pause = QPushButton("Pause", self)
        pause.setGeometry(125, 300, 150, 40)
        pause.pressed.connect(self.Pause)

        reset = QPushButton("Reset", self)
        reset.setGeometry(125, 350, 150, 40)
        reset.pressed.connect(self.Re_set)

        timer = QTimer(self)
        timer.timeout.connect(self.updateTime)
        timer.start(1000)
        self.is_playing = False

    def connectTray(self):
        self.run_next_timeloop.connect( mainTray.next_timeloop )
        self.run_next_timeloop.emit()

    def clickMethod(self):
        QMessageBox.about(self, "Title", "Message")

    def closeEvent(self, event):
        self.run_next_timeloop.emit()
        event.accept()

    def showUp(self):
        self.show()
        self.raise_()
        self.activateWindow()

    def exitApplication(self):
        self.settings.setValue("size", self.size())
        self.settings.setValue("pos", self.pos())
        exit()

    def updateTime(self):
        seconds = self.time_counter
        if self.is_to_increment_counter:
            self.time_counter+= 1
            if seconds > ALARM_TIMEOUT and not self.is_playing:
                self.is_playing = True
                filename = os.path.join(CURRENT_DIR, "Alarm06.wav")
                QtMultimedia.QSound.play(filename)
            if seconds == 10:
                speak(f"{seconds} seconds")
            if seconds == 20:
                speak(f"{seconds} seconds")
            if seconds == 30:
                speak(f"{seconds} seconds")
            self.label.setText(str(seconds))

    def Start(self):
        self.is_to_increment_counter = True
        self.label.setStyleSheet("background-color:lightgreen")

    def Pause(self):
        self.is_to_increment_counter = False
        self.label.setStyleSheet("background-color:lightblue")

    def Re_set(self):
        self.is_playing = False
        self.time_counter = 0
        self.label.setText(str(self.time_counter))

        if self.is_to_increment_counter:
            self.label.setStyleSheet("background-color:lightgreen")
        else:
            self.label.setStyleSheet("background-color:")


class QSystemTrayIconListener(QSystemTrayIcon):
    update_tray_icon_text = pyqtSignal( [str] )
    show_main_window = pyqtSignal( [] )

    def __init__(self, *args, **kwargs):
        self.pixmap = None
        self.font = None
        self.painter = None
        self.icon = None
        super(QSystemTrayIconListener, self).__init__( *args, **kwargs )

        self.create_menu()
        self.set_tray_text( "00" )

        self.update_tray_icon_text.connect( self.set_tray_text )
        self.show_main_window.connect( mainWin.show )

        threading.Thread( target=self.continually_update_tray_icon, daemon=True ).start()

    def next_timeloop(self):
        timer = Timer( SHOW_WINDOW_INTERVAL, self.show_main_window.emit )
        timer.start()
        # last_show_up = datetime.datetime.now().date()
        # while True:
        #     now = datetime.datetime.now().date()
        #     if now - last_show_up > datetime.timedelta(minutes=30):
        #         last_show_up = now
        #         self.show_main_window.emit()

    def continually_update_tray_icon(self):
        while True:
            now = datetime.datetime.now().date()
            self.update_tray_icon_text.emit( "%02d" % now.day )
            time.sleep(30)

    def set_tray_text(self, newdate):
        pixmap = QPixmap(100,100)
        pixmap.fill( Qt.GlobalColor.transparent )

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
        font = QFont( "SansSerif" )
        font.setWeight( QFont.Thin )
        font.setPointSize( 73 )

        painter = QPainter( pixmap )
        painter.setPen( Qt.white )
        painter.setFont( font )
        painter.drawText( QPoint( -5, 79 ), newdate )

        # file = QFile( "yourFile.png" )
        # file.open( QIODevice.WriteOnly )
        # pixmap.save( file, "PNG" )

        icon = QIcon( pixmap )
        self.setIcon( icon )
        self.setToolTip( str( datetime.datetime.now() )[:-7] )
        self.setVisible( True )

        if self.painter:
            self.painter.end()

        self.pixmap = pixmap
        self.font = font
        self.painter = painter
        self.icon = icon

    def create_menu(self):
        self.exitAction = QAction( "&Exit" )
        self.mainWindowAction = QAction( "&Main Window" )

        self.menu = QMenu()
        self.menu.addAction( self.mainWindowAction )
        self.menu.addAction( self.exitAction )

        self.mainWindowAction.triggered.connect( mainWin.showUp )
        self.exitAction.triggered.connect( mainWin.exitApplication )
        self.setContextMenu( self.menu )

        self.activated.connect(self.systemIcon)

    def systemIcon(self, reason):
        if reason == QSystemTrayIcon.Trigger:
            if mainWin.isVisible():
                mainWin.hide()
            else:
                mainWin.showUp()

    def print_msg(self):
        print( "This action is triggered connect!" )


if __name__ == "__main__":
    main()

