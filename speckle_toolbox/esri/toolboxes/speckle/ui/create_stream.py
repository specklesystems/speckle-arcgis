import os
from typing import List, Tuple, Union
#import ui.speckle_qgis_dialog


from PyQt5 import QtWidgets, uic, QtCore
from PyQt5.QtCore import pyqtSignal

import arcpy

from specklepy.api.models import Stream
from specklepy.api.client import SpeckleClient
from specklepy.logging.exceptions import SpeckleException

from specklepy.api.credentials import Account, get_local_accounts #, StreamWrapper
from specklepy.api.wrapper import StreamWrapper
from gql import gql

# This loads your .ui file so that PyQt can populate your plugin with the elements from Qt Designer

ui_class = os.path.dirname(os.path.abspath(__file__)) + "/create_stream.ui"

class CreateStreamModalDialog(QtWidgets.QWidget):

    name_field: QtWidgets.QLineEdit = None
    description_field: QtWidgets.QLineEdit = None
    dialog_button_box: QtWidgets.QDialogButtonBox = None
    accounts_dropdown: QtWidgets.QComboBox
    public_toggle: QtWidgets.QCheckBox

    speckle_client: Union[SpeckleClient, None] = None

    #Events
    handleStreamCreate = pyqtSignal(Account, str, str, bool)

    def __init__(self, parent=None, speckle_client: SpeckleClient = None):
        super(CreateStreamModalDialog,self).__init__(parent,QtCore.Qt.WindowStaysOnTopHint)
        uic.loadUi(ui_class, self) # Load the .ui file
        self.show() 
        
        self.speckle_client = speckle_client
        
        self.setWindowTitle("Create New Stream")

        self.name_field.textChanged.connect(self.nameCheck)
        self.dialog_button_box.button(QtWidgets.QDialogButtonBox.Ok).setEnabled(True) 
        self.dialog_button_box.button(QtWidgets.QDialogButtonBox.Ok).clicked.connect(self.onOkClicked)
        self.dialog_button_box.button(QtWidgets.QDialogButtonBox.Cancel).clicked.connect(self.onCancelClicked)
        self.accounts_dropdown.currentIndexChanged.connect(self.onAccountSelected)
        self.populate_accounts_dropdown()

    def nameCheck(self):
        if len(self.name_field.text()) == 0 or len(self.name_field.text()) >= 3:
            self.dialog_button_box.button(QtWidgets.QDialogButtonBox.Ok).setEnabled(True) 
        else: 
            self.dialog_button_box.button(QtWidgets.QDialogButtonBox.Ok).setEnabled(False) 
        return

    def onOkClicked(self):
        try:
            acc = get_local_accounts()[self.accounts_dropdown.currentIndex()]
            name = self.name_field.text()
            description = self.description_field.text()
            public = self.public_toggle.isChecked()
            self.handleStreamCreate.emit(acc,name,description,public)
            self.close()
        except Exception as e:
            arcpy.addError(str(e))
            return 

    def onCancelClicked(self):
        #self.handleCancelStreamCreate.emit()
        self.close()

    def onAccountSelected(self, index):
        account = self.speckle_accounts[index]
        self.speckle_client = SpeckleClient(account.serverInfo.url, account.serverInfo.url.startswith("https"))
        self.speckle_client.authenticate_with_token(token=account.token)

    def populate_accounts_dropdown(self):
        # Populate the accounts comboBox
        self.speckle_accounts = get_local_accounts()
        self.accounts_dropdown.clear()
        self.accounts_dropdown.addItems(
            [
                f"{acc.userInfo.name}, {acc.userInfo.email} | {acc.serverInfo.url}"
                for acc in self.speckle_accounts
            ]
        )

