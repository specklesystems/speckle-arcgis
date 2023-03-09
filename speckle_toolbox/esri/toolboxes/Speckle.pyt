     
import os
import sys
import threading
from typing import List

from PyQt5.QtWidgets import (QMainWindow, QLabel, QApplication,
    QDockWidget, QVBoxLayout, QWidget)
from PyQt5.QtCore import Qt 
from PyQt5 import QtGui, uic
import arcpy

try: 
    from speckle.ui.speckle_qgis_dialog import SpeckleGISDialog
    from speckle.speckle_arcgis import SpeckleGIS 
except: 
    from speckle_toolbox.esri.toolboxes.speckle.ui.speckle_qgis_dialog import SpeckleGISDialog
    from speckle_toolbox.esri.toolboxes.speckle.speckle_arcgis import SpeckleGIS 

def startThread(sp_class): 
    print("START THREAD")
    t = threading.Thread(target=qtApp, args=(sp_class,))
    t.start()
    threads = threading.enumerate()
    print("__Total threads: " + str(len(threads)))

def qtApp(text: str):
    print("MAIN function")
    
    threads = threading.enumerate()
    print("__Total threads: " + str(len(threads)))
    app = QApplication(sys.argv)
    ex = SpeckleGIS()
    #ex.show()
    sys.exit(app.exec_())

class Toolbox:
    def __init__(self):
        """Define the toolbox (the name of the toolbox is the name of the .pyt file)."""
        print("___start_Toolbox")
        self.label = "Speckle Tools"
        self.alias = "speckle_toolbox_"  
        # List of tool classes associated with this toolbox
        self.tools = [Speckle]  

class Speckle:
    #instances = []
    def __init__(self):  
        
        print("___start speckle tool_________")

        self.label       = "Speckle"
        self.description = "Allows you to send and receive your layers " + \
                           "to/from other software using Speckle server." 

    def getParameterInfo(self):
        cat1 = "category 1"

        param0 = arcpy.Parameter(
            displayName="""▷ Run to launch Speckle Connector
""", #▶ 
            name="param0",
            datatype="GPString",
            parameterType="Optional",
            direction="Input",
            enabled="True",
            )
        param0.value = """This is an experimental version of plugin.

Save your work before using!

Report issues at https://speckle.community/"""
        return [param0]

    def isLicensed(self): #optional
        return True

    def updateParameters(self, parameters: List, toRefresh = False): #optional
        return 

    def execute(self, parameters: List, messages): 
        qtApp("")
        #startThread("")