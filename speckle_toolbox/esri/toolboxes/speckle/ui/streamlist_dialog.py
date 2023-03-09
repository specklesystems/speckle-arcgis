import os
from PyQt5 import QtWidgets, uic
from PyQt5.QtCore import pyqtSignal

# This loads your .ui file so that PyQt can populate your plugin with the elements from Qt Designer

ui_class = os.path.dirname(os.path.abspath(__file__)) + "/streamlist_dialog.ui"

class StreamListDialog(QtWidgets.QWidget):
    streams_add_button: QtWidgets.QPushButton
    streams_reload_button: QtWidgets.QPushButton
    streams_remove_button: QtWidgets.QPushButton


    def __init__(self, parent=None):
        super(StreamListDialog, self).__init__(parent)
        uic.loadUi(ui_class, self) # Load the .ui file
        self.show()

