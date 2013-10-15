#!/usr/bin/python3

""" The GUI main class. """

try:
    from PyQt4.QtGui import QApplication
except ImportError:
    print("PyQt modules not found.  Cannot start graphical interface.")
    exit(1)

import sys
from . import Gui

class GraphicalUI:
    def __init__(self, path=None):
        app = QApplication(sys.argv)
        mainwindow = Gui.TaglinesWindow(path)
        mainwindow.show()
        sys.exit(app.exec_())
