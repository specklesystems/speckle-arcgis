     
import sys

import threading
from typing import List
import arcpy
from PyQt5.QtWidgets import (QMainWindow, QLabel, QApplication)
from PyQt5.QtCore import Qt 
from PyQt5 import QtGui

from events import Events

class MainWindow(QMainWindow):
    instances = []
    def __init__(self, *args, **kwargs):
        print("START MAIN WINDOW")
        super(MainWindow, self).__init__(*args, **kwargs)
        self.setWindowTitle("Basic App")
        label = QLabel("The label")
        label.setAlignment(Qt.AlignCenter)
        self.setCentralWidget(label)
        self.instances.append(1)
    def closeEvent(self,event):
        print("Close event")
        Speckle.instances.pop()
        self.instances.pop()
        print(len(Speckle.instances)-len(self.instances))

def main(stop: int):
    print("MAIN function")
    app = QApplication(sys.argv)
    ex = MainWindow()
    ex.show()
    sys.exit(app.exec_())

def startThread(text: str): 
    print("START")
    t = threading.Thread(target=main, args=(1,))
    t.start()
    threads = threading.enumerate()
    print("__Total threads: " + str(len(threads)))

events: Events = Events()
events.on_change += startThread

class Toolbox:
    def __init__(self):
        """Define the toolbox (the name of the toolbox is the name of the .pyt file)."""
        print("___start_Toolbox")
        self.label = "Speckle Tools"
        self.alias = "speckle_toolbox_"  
        # List of tool classes associated with this toolbox
        self.tools = [Speckle]  

class Speckle:
    instances = []
    def __init__(self):  
        
        print("___start speckle tool_________")
        difference = len(self.instances)-len(MainWindow.instances)
        print(difference)

        self.label       = "Speckle"
        self.description = "Allows you to send and receive your layers " + \
                           "to/from other software using Speckle server." 
        
        if difference == 0: 
            self.instances.append(1)
            events.on_change("some text") 
            print("event called") 

    def getParameterInfo(self):
        return []

    def isLicensed(self): #optional
        return True

    def updateParameters(self, parameters: List, toRefresh = False): #optional
        return 

