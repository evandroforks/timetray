#! /usr/bin/env python
# -*- coding: utf-8 -*-
import time
import datetime
import threading

# https://stackoverflow.com/questions/19723459/why-is-python-deque-initialized-using-the-last-maxlen-items-in-an-iterable
from collections import deque

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
from PyQt5.QtCore import Qt, QPoint, pyqtSignal, QFile
from PyQt5.QtWidgets import QApplication, QSystemTrayIcon, QMenu, QAction


def main():
    # create the application
    app = QApplication( [] )
    app.setQuitOnLastWindowClosed( False )

    # create the tray icon
    app.tray = QSystemTrayIconListener()

    # start application execution
    app.exec_()


class QSystemTrayIconListener(QSystemTrayIcon):
    update_tray_icon_text = pyqtSignal( [str] )

    def __init__(self, *args, **kwargs):
        self.pixmap = None
        self.font = None
        self.painter = None
        self.icon = None
        super(QSystemTrayIconListener, self).__init__( *args, **kwargs )

        self.create_menu()
        self.set_tray_text( "00" )

        self.update_tray_icon_text.connect( self.set_tray_text )
        threading.Thread( target=self.continually_update_tray_icon, daemon=True ).start()

    def continually_update_tray_icon(self):

        while True:
            now = datetime.datetime.now().date()
            self.update_tray_icon_text.emit( "%02d" % now.day )
            time.sleep(30)

    def set_tray_text(self, newdate):
        pixmap = QPixmap(100,100)
        pixmap.fill( Qt.GlobalColor.transparent )

        font = QFont( "SansSerif" )
        font.setWeight( QFont.Medium )
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
        self.setVisible( True )

        if self.painter:
            self.painter.end()

        self.pixmap = pixmap
        self.font = font
        self.painter = painter
        self.icon = icon

    def create_menu(self):
        # create the menu for tray icon
        self.menu = QMenu()

        # add one item to menu
        self.action = QAction( "This is menu item" )
        self.menu.addAction( self.action )
        self.action.triggered.connect( self.print_msg )

        # add exit item to menu
        self.exitAction = QAction( "&Exit" )
        self.menu.addAction( self.exitAction )
        self.exitAction.triggered.connect( exit )

        # add the menu to the tray
        self.setContextMenu( self.menu )

    def print_msg(self):
        print( "This action is triggered connect!" )


if __name__ == "__main__":
    main()

