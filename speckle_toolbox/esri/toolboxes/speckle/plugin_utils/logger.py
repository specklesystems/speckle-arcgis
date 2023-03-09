
from PyQt5.QtWidgets import QMessageBox
from PyQt5 import QtCore

def logToUser(msg: str, level: int):
        # https://www.techwithtim.net/tutorials/pyqt5-tutorial/messageboxes/
        window = QMessageBox()
        #msg.setWindowFlag(QtCore.Qt.WindowStaysOnTopHint)
        if level==0: 
              window.setWindowTitle("Info")
              window.setIcon(QMessageBox.Icon.Information)
        if level==1: 
              window.setWindowTitle("Warning")
              window.setIcon(QMessageBox.Icon.Warning)
        elif level==2: 
              window.setWindowTitle("Error")
              window.setIcon(QMessageBox.Icon.Critical)
        window.setFixedWidth(200)
        window.setText(str(msg))
        window.exec_() 
        
        return
