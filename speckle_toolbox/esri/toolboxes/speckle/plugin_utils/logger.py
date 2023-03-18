
from PyQt5.QtWidgets import QMessageBox
from PyQt5 import QtCore

import inspect 

def logToUser(msg: str, func=None, level: int = 2):
      
      window = createWindow(msg, func, level)
      if window is not None: 
            window.exec_() 
      return

def createWindow(msg_old: str, func=None, level: int = 2):
      print("Create window")
      window = None
      try:
            # https://www.techwithtim.net/tutorials/pyqt5-tutorial/messageboxes/
            window = QMessageBox()
            #msg.setWindowFlag(QtCore.Qt.WindowStaysOnTopHint)

            msg = ""
            if len(msg_old)>80:
                  try:
                        for i, x in enumerate(msg_old):
                              msg += x
                              if i!=0 and i%80 == 0: msg += "\n"
                  except Exception as e: print(e)
            else: 
                  msg = msg_old

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

            if level>0 and func is not None:
                  window.setText(str(msg + "\n" + str(func)))
            else: 
                  window.setText(str(msg))
      
            print(window)
      except Exception as e: print(e)
      
      return window 
