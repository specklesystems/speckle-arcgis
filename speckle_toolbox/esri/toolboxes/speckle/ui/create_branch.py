import os
from typing import List, Tuple, Union
#import ui.speckle_qgis_dialog

from PyQt5 import QtWidgets, uic, QtCore
from PyQt5.QtCore import pyqtSignal
from specklepy.api.models import Stream
from specklepy.api.client import SpeckleClient
from specklepy.logging.exceptions import SpeckleException

from specklepy.api.credentials import Account, get_local_accounts #, StreamWrapper
from specklepy.api.wrapper import StreamWrapper
from gql import gql

import arcpy 
try:
    from speckle.plugin_utils.logger import logToUser
except:
    from speckle_toolbox.esri.toolboxes.speckle.plugin_utils.logger import logToUser

# This loads your .ui file so that PyQt can populate your plugin with the elements from Qt Designer

ui_class = os.path.dirname(os.path.abspath(__file__)) + "/create_branch.ui"

class CreateBranchModalDialog(QtWidgets.QWidget):

    name_field: QtWidgets.QLineEdit = None
    description_field: QtWidgets.QLineEdit = None
    dialog_button_box: QtWidgets.QDialogButtonBox = None
    speckle_client: Union[SpeckleClient, None] = None

    #Events
    handleBranchCreate = pyqtSignal(str,str)

    def __init__(self, parent=None, speckle_client: SpeckleClient = None):
        super(CreateBranchModalDialog,self).__init__(parent,QtCore.Qt.WindowStaysOnTopHint)
        uic.loadUi(ui_class, self) # Load the .ui file
        self.show() 
        try:
        
            self.speckle_client = speckle_client
            
            self.setWindowTitle("Create New Branch")

            self.name_field.textChanged.connect(self.nameCheck)
            self.dialog_button_box.button(QtWidgets.QDialogButtonBox.Ok).setEnabled(False) 
            self.dialog_button_box.button(QtWidgets.QDialogButtonBox.Ok).clicked.connect(self.onOkClicked)
            self.dialog_button_box.button(QtWidgets.QDialogButtonBox.Cancel).clicked.connect(self.onCancelClicked)
        except Exception as e:
            logToUser(e)

    def nameCheck(self):
        try:
            if len(self.name_field.text()) >= 3:
                self.dialog_button_box.button(QtWidgets.QDialogButtonBox.Ok).setEnabled(True) 
            else: 
                self.dialog_button_box.button(QtWidgets.QDialogButtonBox.Ok).setEnabled(False) 
            return
        except Exception as e: 
            logToUser(str(e)) 

    def onOkClicked(self):
        try:
            name = self.name_field.text()
            description = self.description_field.text()
            self.handleBranchCreate.emit(name, description)
            self.close()
        except Exception as e:
            logToUser(str(e))
            return 

    def onCancelClicked(self):
        self.close()

    def onAccountSelected(self, index):
        try:
            account = self.speckle_accounts[index]
            self.speckle_client = SpeckleClient(account.serverInfo.url, account.serverInfo.url.startswith("https"))
            self.speckle_client.authenticate_with_token(token=account.token)
        except Exception as e: 
            logToUser(str(e)) 
