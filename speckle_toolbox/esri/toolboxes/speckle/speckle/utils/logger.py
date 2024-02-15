from PyQt5.QtWidgets import QMessageBox
from PyQt5 import QtCore
import arcpy

try:
    from speckle.speckle.plugin_utils.helpers import splitTextIntoLines
except:
    from speckle_toolbox.esri.toolboxes.speckle.speckle.plugin_utils.helpers import (
        splitTextIntoLines,
    )

import inspect


def logToUser(msg: str, func=None, level: int = 2, plugin=None, url="", blue=False):
    # print("Log to user")
    # print(msg)

    msg = str(msg)
    dockwidget = plugin

    try:
        if url == "" and blue is False:  # only for info messages
            msg = addLevelSymbol(msg, level)
            if func is not None:
                msg += "::" + str(func)
        writeToLog(msg, level)

        if dockwidget is None:
            return

        new_msg = splitTextIntoLines(msg, 70)

        dockwidget.msgLog.addButton(new_msg, level=level, url=url, blue=blue)

    except Exception as e:
        print(e)
        return


def logToUserWithAction(msg: str, level: int = 0, plugin=None, url=""):
    print("Log to user with action")
    return
    msg = str(msg)
    dockwidget = plugin
    if dockwidget is None:
        return
    try:
        new_msg = splitTextIntoLines(msg, 70)
        dockwidget.msgLog.addButton(new_msg, level=level, url=url)
        writeToLog(new_msg, level)
    except Exception as e:
        print(e)
        return


def addLevelSymbol(msg: str, level: int):
    if level == 0:
        msg = "🛈 " + msg
    if level == 1:
        msg = "⚠️ " + msg
    if level == 2:
        msg = "❗ " + msg
    return msg


def writeToLog(msg: str = "", level: int = 2):
    print(msg)
    if level == 0:
        arcpy.AddMessage(msg)
    if level == 1:
        arcpy.AddWarning(msg)
    if level == 2:
        arcpy.AddError(msg)
