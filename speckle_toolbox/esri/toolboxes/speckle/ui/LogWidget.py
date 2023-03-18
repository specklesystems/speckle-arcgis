
import time
from typing import List
from PyQt5 import QtCore
from PyQt5.QtCore import QCoreApplication, QSettings, Qt, QTranslator, QRect, QObject
from PyQt5.QtWidgets import QAction, QDockWidget, QVBoxLayout, QWidget, QPushButton
from PyQt5 import QtWidgets
import webbrowser

import inspect 

try:
    from speckle.ui.logger import logToUser
except:
    from speckle_toolbox.esri.toolboxes.speckle.ui.logger import logToUser

SPECKLE_COLOR = (59,130,246)
SPECKLE_COLOR_LIGHT = (69,140,255)

BACKGR_COLOR = f"background-color: rgb{str(SPECKLE_COLOR)};"
BACKGR_COLOR_LIGHT = f"background-color: rgb{str(SPECKLE_COLOR_LIGHT)};"

BACKGR_COLOR_GREY = f"background-color: Gainsboro;"

class LogWidget(QWidget):
    
    msgs: List[str] = []
    used_btns: List[int] = []
    btns: List[QPushButton]

    # constructor
    def __init__(self, parent=None):
        super(LogWidget, self).__init__(parent)
        print("start LogWidget")
        self.parentWidget = parent
        print(self.parentWidget)

        # create a temporary floating button 
        width = 0 #parent.frameSize().width()
        height = 0# parent.frameSize().height()
        
        self.setAttribute(QtCore.Qt.WA_StyledBackground, True)
        self.setStyleSheet("background-color: rgba(250,250,250,80);")
        
        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(10, 60, 10, 40)
        self.layout.setAlignment(Qt.AlignBottom) 
        self.setGeometry(0, 0, width, height)

        # generate 100 buttons to use later
        self.btns = []
        for i in range(10):
            button = QPushButton(f"👌 Error") # to '{streamName}' Sent , v
            button.setStyleSheet("QPushButton {color: black; border: 0px;border-radius: 17px;padding: 20px;height: 40px;text-align: left;"+ f"{BACKGR_COLOR_GREY}" + "}")
            button.clicked.connect(lambda: self.hide())
            self.btns.append(button)

        self.hide() 

    # overriding the mouseReleaseEvent method
    def mouseReleaseEvent(self, event):
        print("Mouse Release Event")
        self.hide() 
        #self.parentWidget.hideError()

    def hide(self):
        
        self.setGeometry(0, 0, 0, 0)

        # remove all buttons
        for i in reversed(range(self.layout.count())): 
           self.layout.itemAt(i).widget().setParent(None)

        # remove list of used btns
        self.used_btns.clear()
        self.msgs.clear()


    def addButton(self, text: str = "something went wrong", level: int = 2):
        print("Add button")

        self.setGeometry(0, 0, self.parentWidget.frameSize().width(), self.parentWidget.frameSize().height())
        
        # find index of the first unused button
        btn = self.getNextBtn()

        btn.setStyleSheet("QPushButton {color: black; border: 0px;border-radius: 17px;padding: 20px;height: 40px;text-align: left;"+ f"{BACKGR_COLOR_GREY}" + "}")
        btn.setText(text)
        self.resizeToText(btn)

        #btn.resize(btn.sizeHint())
        self.layout.addWidget(btn) #, alignment=Qt.AlignCenter) 

        self.msgs.append(text)
        self.used_btns.append(1)

    def addInfoButton(self, text: str = "link here", level: int = 2, url = ""):
        print("Add blue button")

        self.setGeometry(0, 0, self.parentWidget.frameSize().width(), self.parentWidget.frameSize().height())
        
        # find index of the first unused button
        btn: QPushButton = self.getNextBtn()
        
        # style the button
        btn.setStyleSheet("QPushButton {color: white;border: 0px;border-radius: 17px;padding: 20px;height: 40px;text-align: left;"+ f"{BACKGR_COLOR}" + "}")
        btn.setText(text)
        btn = self.resizeToText(btn)

        self.layout.addWidget(btn) #, alignment=Qt.AlignCenter) 

        self.msgs.append(text)
        self.used_btns.append(1)


    def addLinkButton(self, text: str = "link here", level: int = 2, url = ""):
        print("Add link button")

        self.setGeometry(0, 0, self.parentWidget.frameSize().width(), self.parentWidget.frameSize().height())
        
        # find index of the first unused button
        btn = self.getNextBtn()

        # style the button
        btn.setStyleSheet("QPushButton {color: white;border: 0px;border-radius: 17px;padding: 20px;height: 40px;text-align: left;"+ f"{BACKGR_COLOR}" + "} QPushButton:hover { "+ f"{BACKGR_COLOR_LIGHT}" + " }")
        btn.setText(text)
        self.resizeToText(btn)
        btn.clicked.connect(lambda: self.openLink(url))

        self.layout.addWidget(btn) #, alignment=Qt.AlignCenter) 

        self.msgs.append(text)
        self.used_btns.append(1)

    def openLink(self, url = ""):
        try:
            webbrowser.open(url, new=0, autoraise=True)
            self.hide()
        except Exception as e: 
            pass #logger.logToUser(str(e), level=2, func = inspect.stack()[0][3])

    def getNextBtn(self) -> QPushButton:
        index = len(self.used_btns)
        if index >= len(self.btns): 
            self.used_btns.clear()
            index = 0 
        btn = self.btns[index] # get the next "free" button 
        return btn 
    
    def resizeToText(self, btn):
        try:
            text = btn.text()
            if len(text.split("\n"))>=2:
                height = len(text.split("\n"))*25
                print(height)
                btn.setMinimumHeight(height)
            return btn 
        except Exception as e: 
            print(e) 
            return btn 
