
from PyQt5.QtWidgets import QMessageBox
from PyQt5 import QtCore
import arcpy 
try: 
    from speckle.plugin_utils.helpers import splitTextIntoLines
except:
    from speckle_toolbox.esri.toolboxes.speckle.plugin_utils.helpers import splitTextIntoLines

import inspect 

def logToUser(msg: str, func=None, level: int = 2, plugin = None, blue = False):
      print("Log to user")

      msg = str(msg)
      dockwidget = plugin

      try: 
            if func is not None: msg += "::" + str(func)
            print(msg)
            writeToLog(msg, level)
            if dockwidget is None: return

            new_msg = splitTextIntoLines(msg, 70)

            if blue is True: 
                  dockwidget.msgLog.addInfoButton(new_msg, level=level)
            else:
                  new_msg = addLevelSymbol(new_msg, level)
                  dockwidget.msgLog.addButton(new_msg, level=level)
            
      except Exception as e: print(e); return 

def logToUserWithAction(msg: str, level: int = 0, plugin = None, url = ""):
      print("Log to user with action")
      
      msg = str(msg)
      dockwidget = plugin
      if dockwidget is None: return
      try:             
            new_msg = splitTextIntoLines(msg, 70)
            dockwidget.msgLog.addLinkButton(new_msg, level=level, url=url)
            writeToLog(new_msg, level)
      except Exception as e: print(e); return 

def addLevelSymbol(msg: str, level: int):
      if level == 0: msg = "🛈 " + msg
      if level == 1: msg = "⚠️ " + msg
      if level == 2: msg = "❗ " + msg
      return msg 

def writeToLog(msg: str = "", level: int = 2):
      print("write log")
      if level == 0: arcpy.AddMessage(msg)
      if level == 1: arcpy.AddWarning(msg)
      if level == 2: arcpy.AddError(msg)
