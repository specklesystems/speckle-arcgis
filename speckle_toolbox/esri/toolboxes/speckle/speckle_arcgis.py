
import os.path
from typing import Any, Callable, List, Optional, Tuple, Union

from PyQt5.QtCore import QCoreApplication, QSettings, Qt, QTranslator, QRect 
from PyQt5.QtGui import QIcon
from PyQt5.QtWidgets import QAction, QDockWidget, QVBoxLayout, QWidget
from PyQt5 import QtWidgets

from specklepy.api import operations
from specklepy.logging.exceptions import SpeckleException, GraphQLException
#from specklepy.api.credentials import StreamWrapper
from specklepy.api.models import Stream
from specklepy.api.wrapper import StreamWrapper
from specklepy.objects import Base
from specklepy.transports.server import ServerTransport
from specklepy.api.credentials import Account, get_local_accounts #, StreamWrapper
from specklepy.api.client import SpeckleClient
import webbrowser

import arcpy
from arcpy._mp import ArcGISProject, Map
from arcpy._mp import Layer as arcLayer

try: 
    from speckle.plugin_utils.object_utils import callback, traverseObject
    from speckle.converter.layers.Layer import (Layer, VectorLayer, RasterLayer) 
    from speckle.converter.layers import convertSelectedLayers, getLayers
    from speckle.converter.layers.utils import findAndClearLayerGroup
    from speckle.ui.validation import tryGetStream, validateBranch, validateCommit, validateStream, validateTransport 
    from speckle.ui.add_stream_modal import AddStreamModalDialog
    from speckle.ui.create_stream import CreateStreamModalDialog
    from speckle.ui.create_branch import CreateBranchModalDialog
except: 
    from speckle_toolbox.esri.toolboxes.speckle.plugin_utils.object_utils import callback, traverseObject
    from speckle_toolbox.esri.toolboxes.speckle.converter.layers.Layer import (Layer, VectorLayer, RasterLayer)
    from speckle_toolbox.esri.toolboxes.speckle.converter.layers import convertSelectedLayers, getLayers
    from speckle_toolbox.esri.toolboxes.speckle.converter.layers.emptyLayerTemplates import createGroupLayer
    from speckle_toolbox.esri.toolboxes.speckle.converter.layers.utils import findAndClearLayerGroup
    from speckle_toolbox.esri.toolboxes.speckle.ui.validation import tryGetStream, validateBranch, validateCommit, validateStream, validateTransport 
    from speckle_toolbox.esri.toolboxes.speckle.ui.add_stream_modal import AddStreamModalDialog
    from speckle_toolbox.esri.toolboxes.speckle.ui.create_stream import CreateStreamModalDialog
    from speckle_toolbox.esri.toolboxes.speckle.ui.create_branch import CreateBranchModalDialog


# Import the code for the dialog


SPECKLE_COLOR = (59,130,246)
SPECKLE_COLOR_LIGHT = (69,140,255)

class SpeckleGIS:
    """Speckle Connector Plugin for ArcGIS"""

    dockwidget: Optional[QDockWidget]
    add_stream_modal: AddStreamModalDialog
    create_stream_modal: CreateStreamModalDialog
    current_streams: List[Tuple[StreamWrapper, Stream]]  #{id:(sw,st),id2:()}
    current_layers: List[Tuple[str, arcLayer]] = []

    active_stream: Optional[Tuple[StreamWrapper, Stream]] 

    gis_project: ArcGISProject #QgsProject

    lat: float
    lon: float

    default_account: Account
    accounts: List[Account]

    def __init__(self):
        """Constructor. 
        """
        print("Start SpeckleGIS")
        # Save reference to the QGIS interface
        self.dockwidget = None
        #self.iface = None
        self.gis_project = ArcGISProject('CURRENT') #QgsProject.instance()
        self.current_streams = []
        self.active_stream = None
        self.default_account = None 
        self.accounts = [] 

        self.btnAction = 0

        self.lat = 0.0
        self.lon = 0.0
        # initialize plugin directory
        self.plugin_dir = os.path.dirname(__file__)
        # initialize locale
        #locale = QSettings().value("locale/userLocale")[0:2]
        #locale_path = os.path.join(
        #    self.plugin_dir, "i18n", "SpeckleQGIS_{}.qm".format(locale)
        #)

        #if os.path.exists(locale_path):
        #    self.translator = QTranslator()
        #    self.translator.load(locale_path)
        #    QCoreApplication.installTranslator(self.translator)

        # Declare instance attributes
        self.actions = []
        self.menu = self.tr("&SpeckleArcGIS")

        # Check if plugin was started the first time in current QGIS session
        # Must be set in initGui() to survive plugin reloads
        self.pluginIsActive = False  
        self.run()

    # noinspection PyMethodMayBeStatic

    def tr(self, message: str):
        """Get the translation for a string using Qt translation API.

        We implement this ourselves since we do not inherit QObject.

        :param message: String for translation.
        :type message: str, QString

        :returns: Translated version of message.
        :rtype: QString
        """
        # noinspection PyTypeChecker,PyArgumentList,PyCallByClass
        return QCoreApplication.translate("SpeckleGIS", message)

    def add_action(
        self,
        icon_path: str,
        text,
        callback,
        enabled_flag=True,
        add_to_menu=True,
        add_to_toolbar=True,
        status_tip=None,
        whats_this=None,
        parent=None,
    ):
        """Add a toolbar icon to the toolbar.

        :param icon_path: Path to the icon for this action. Can be a resource
            path (e.g. ':/plugins/foo/bar.png') or a normal file system path.
        :type icon_path: str

        :param text: Text that should be shown in menu items for this action.
        :type text: str

        :param callback: Function to be called when the action is triggered.
        :type callback: function

        :param enabled_flag: A flag indicating if the action should be enabled
            by default. Defaults to True.
        :type enabled_flag: bool

        :param add_to_menu: Flag indicating whether the action should also
            be added to the menu. Defaults to True.
        :type add_to_menu: bool

        :param add_to_toolbar: Flag indicating whether the action should also
            be added to the toolbar. Defaults to True.
        :type add_to_toolbar: bool

        :param status_tip: Optional text to show in a popup when mouse pointer
            hovers over the action.
        :type status_tip: str

        :param parent: Parent widget for the new action. Defaults None.
        :type parent: QWidget

        :param whats_this: Optional text to show in the status bar when the
            mouse pointer hovers over the action.

        :returns: The action that was created. Note that the action is also
            added to self.actions list.
        :rtype: QAction
        """

        icon = QIcon(icon_path)
        action = QAction(icon, text, parent)
        action.triggered.connect(callback)
        action.setEnabled(enabled_flag)

        if status_tip is not None:
            action.setStatusTip(status_tip)

        if whats_this is not None:
            action.setWhatsThis(whats_this)

        #if add_to_toolbar:
        #    # Adds plugin icon to Plugins toolbar
        #    self.iface.addToolBarIcon(action)

        #if add_to_menu and self.menu:
        #    self.iface.addPluginToWebMenu(self.menu, action)

        self.actions.append(action)

        return action

    def initGui(self):
        """Create the menu entries and toolbar icons inside the QGIS GUI."""

        icon_path = "" #":/plugins/speckle_qgis/icon.png"
        self.add_action(
            icon_path,
            text=self.tr("SpeckleGIS"),
            callback=self.run,
            add_to_menu=False,
            add_to_toolbar=False,
            parent=None, #self.iface.mainWindow(),
        )

    def onClosePlugin(self):
        """Cleanup necessary items here when plugin dockwidget is closed"""

        

        # disconnects
        if self.dockwidget:
            try: 
                self.dockwidget.closingPlugin.disconnect(self.onClosePlugin)
                self.dockwidget.close()
            except: pass 

        self.pluginIsActive = False
        # remove this statement if dockwidget is to remain
        # for reuse if plugin is reopened
        # Commented next statement since it causes QGIS crashe
        # when closing the docked window:
        # self.dockwidget = None

        
        

    def unload(self):
        """Removes the plugin menu item and icon from GIS GUI."""
        return
        #for action in self.actions:
        #    self.iface.removePluginWebMenu(self.tr("&SpeckleQGIS"), action)
        #    self.iface.removeToolBarIcon(action)

    def onRunButtonClicked(self):
        if self.btnAction == 0: self.onSend()
        elif self.btnAction == 1: self.onReceive()

    def onSend(self):
        """Handles action when Send button is pressed."""
        if not self.dockwidget: return

        # creating our parent base object
        project = self.gis_project
        projectCRS = project.crs()
        #layerTreeRoot = project.layerTreeRoot()

        bySelection = True
        if self.dockwidget.layerSendModeDropdown.currentIndex() == 1: bySelection = False 
        layers = getLayers(self, bySelection) # List[QgsLayerTreeNode]

        # Check if stream id/url is empty
        if self.active_stream is None:
            arcpy.AddWarning("Please select a stream from the list.")
            return
        
        # Check if no layers are selected
        if len(layers) == 0: #len(selectedLayerNames) == 0:
            arcpy.AddWarning("No layers selected")
            return

        base_obj = Base(units = "m")
        base_obj.layers = convertSelectedLayers(layers, [],[], projectCRS, project)
        if base_obj.layers is None:
            return 

        # Reset Survey point
        self.dockwidget.populateSurveyPoint(self)

        # Get the stream wrapper
        streamWrapper = self.active_stream[0]
        streamName = self.active_stream[1].name
        streamId = streamWrapper.stream_id
        client = streamWrapper.get_client()

        stream = validateStream(streamWrapper)
        if stream == None: return
        
        branchName = str(self.dockwidget.streamBranchDropdown.currentText())
        branch = validateBranch(stream, branchName, False)
        if branch == None: return

        transport = validateTransport(client, streamId)
        if transport == None: return
        try:
            # this serialises the block and sends it to the transport
            objId = operations.send(base=base_obj, transports=[transport])
        except SpeckleException as e:
            arcpy.AddError("Error sending data: " + str(e.message))
            return

        message = str(self.dockwidget.messageInput.text())
        try:
            # you can now create a commit on your stream with this object
            commit_id = client.commit.create(
                stream_id=streamId,
                object_id=objId,
                branch_name=branchName,
                message="Sent objects from ArcGIS" if len(message) == 0 else message,
                source_application="ArcGIS",
            )
            arcpy.AddMessage("Successfully sent data to stream: " + streamId)
            self.dockwidget.messageInput.setText("")
            url = streamWrapper.stream_url.split("?")[0] + "/commits/" + commit_id

            # create a temporary floating button 
            width = self.dockwidget.frameSize().width()
            height = self.dockwidget.frameSize().height()
            backgr_color = f"background-color: rgb{str(SPECKLE_COLOR)};"
            backgr_color_light = f"background-color: rgb{str(SPECKLE_COLOR_LIGHT)};"
            commit_link_btn = QtWidgets.QPushButton(f"👌 Data sent \n Sent to '{streamName}', view it online")
            commit_link_btn.setStyleSheet("QPushButton {color: white;border: 0px;border-radius: 17px;padding: 20px;height: 40px;text-align: left;"+ f"{backgr_color}" + "} QPushButton:hover { "+ f"{backgr_color_light}" + " }")

            widget = QWidget()
            widget.setAccessibleName("commit_link")
            connect_box = QVBoxLayout(widget)
            connect_box.addWidget(commit_link_btn) #, alignment=Qt.AlignCenter) 
            connect_box.setContentsMargins(0, 0, 0, 0)
            connect_box.setAlignment(Qt.AlignBottom)  
            widget.setGeometry(0, 0, width, height)
            widget.mouseReleaseEvent = lambda event: self.closeWidget()
            self.dockwidget.link = widget 
            
            self.dockwidget.layout().addWidget(widget)
            commit_link_btn.clicked.connect(lambda: self.openLink(url))

        except SpeckleException as e:
            arcpy.AddError("Error creating commit")
    
    def openLink(self, url):
        webbrowser.open(url, new=0, autoraise=True)
        self.closeWidget()

    def closeWidget(self):
        # https://stackoverflow.com/questions/5899826/pyqt-how-to-remove-a-widget
        return 
        #self.dockwidget.layout().removeWidget(self.dockwidget.link)
        #sip.delete(self.dockwidget.link)
        #self.dockwidget.link = None

    def onReceive(self):
        """Handles action when the Receive button is pressed"""

        if not self.dockwidget: return

        # Check if stream id/url is empty
        if self.active_stream is None:
            arcpy.AddWarning("Please select a stream from the list.")
            return

        # Get the stream wrapper
        streamWrapper = self.active_stream[0]
        streamId = streamWrapper.stream_id
        client = streamWrapper.get_client()
        # Ensure the stream actually exists
        try:
            stream = validateStream(streamWrapper)
            if stream == None: return
            
            branchName = str(self.dockwidget.streamBranchDropdown.currentText())
            branch = validateBranch(stream, branchName, True)
            if branch == None: return

            commitId = str(self.dockwidget.commitDropdown.currentText())
            commit = validateCommit(branch, commitId)
            if commit == None: return

        except SpeckleException as error:
            arcpy.AddError(str(error))
            return

        transport = validateTransport(client, streamId)
        if transport == None: return 
        
        try:
            objId = commit.referencedObject
            #commitDetailed = client.commit.get(streamId, commit.id)
            app = commit.sourceApplication
            if branch.name is None or commit.id is None or objId is None: return 

            commitObj = operations.receive(objId, transport, None)

            client.commit.received(
            streamId,
            commit.id,
            source_application="ArcGIS",
            message="Received commit in ArcGIS",
            )

            if app != "QGIS" and app != "ArcGIS": 
                if self.gis_project.activeMap.spatialReference.type == "Geographic" or self.gis_project.activeMap.spatialReference is None: #TODO test with invalid CRS
                    arcpy.AddMessage("Conversion from metric units to DEGREES not supported. It is advisable to set the project Spatial reference to Projected type before receiving CAD geometry (e.g. EPSG:32631), or create a custom one from geographic coordinates")
            arcpy.AddMessage(f"Succesfully received {objId}")

            # If group exists, remove layers inside  
            newGroupName = streamId + "_" + branch.name + "_" + commit.id
            
            findAndClearLayerGroup(self.gis_project, newGroupName)

            if app == "QGIS" or app == "ArcGIS": check: Callable[[Base], bool] = lambda base: isinstance(base, VectorLayer) or isinstance(base, Layer) or isinstance(base, RasterLayer)
            else: check: Callable[[Base], bool] = lambda base: isinstance(base, Base)
            traverseObject(commitObj, callback, check, str(newGroupName))
            
        except SpeckleException as e:
            arcpy.AddWarning("Receive failed: "+ e.message)
            return

    def reloadUI(self):
        
        try:
            from speckle.ui.project_vars import get_project_streams, get_survey_point, get_project_layer_selection
        except: 
            from speckle_toolbox.esri.toolboxes.speckle.ui.project_vars import get_project_streams, get_survey_point, get_project_layer_selection

        self.is_setup = self.check_for_accounts()
        if self.dockwidget is not None:
            self.active_stream = None
            get_project_streams(self)
            get_survey_point(self)
            get_project_layer_selection(self)

            self.dockwidget.reloadDialogUI(self)

    def check_for_accounts(self):
        def go_to_manager():
            webbrowser.open("https://speckle-releases.netlify.app/")
        accounts = get_local_accounts()
        self.accounts = accounts
        if len(accounts) == 0:
            arcpy.AddWarning("No accounts were found. Please remember to install the Speckle Manager and setup at least one account")
            return False
        for acc in accounts:
            if acc.isDefault: 
                self.default_account = acc 
                break 
        return True

    def run(self):
        """Run method that performs all the real work"""
        print("run plugin")
        try:
            from speckle.ui.speckle_qgis_dialog import SpeckleGISDialog
            from speckle.ui.project_vars import get_project_streams, get_survey_point, get_project_layer_selection
        except: 
            from speckle_toolbox.esri.toolboxes.speckle.ui.speckle_qgis_dialog import SpeckleGISDialog
            from speckle_toolbox.esri.toolboxes.speckle.ui.project_vars import get_project_streams, get_survey_point, get_project_layer_selection

        # Create the dialog with elements (after translation) and keep reference
        # Only create GUI ONCE in callback, so that it will only load when the plugin is started
        self.is_setup = self.check_for_accounts()
            
        if self.pluginIsActive:
            self.reloadUI()
        else:
            self.pluginIsActive = True
            if self.dockwidget is None:
                self.dockwidget = SpeckleGISDialog()
                self.dockwidget.show()
                #self.gis_project.fileNameChanged.connect(self.reloadUI)
                #self.gis_project.homePathChanged.connect(self.reloadUI)

            get_project_streams(self)
            get_survey_point(self)
            get_project_layer_selection(self)

            self.dockwidget.run(self)

            # show the dockwidget
            #self.iface.addDockWidget(Qt.RightDockWidgetArea, self.dockwidget)
            self.dockwidget.enableElements(self)

    def onStreamAddButtonClicked(self):
        self.add_stream_modal = AddStreamModalDialog(None)
        self.add_stream_modal.handleStreamAdd.connect(self.handleStreamAdd)
        self.add_stream_modal.show()

    def set_survey_point(self): 
        try:
            from speckle.ui.project_vars import set_survey_point
        except: 
            from speckle_toolbox.esri.toolboxes.speckle.ui.project_vars import set_survey_point
        set_survey_point(self)

    def onStreamCreateClicked(self):
        self.create_stream_modal = CreateStreamModalDialog(None)
        self.create_stream_modal.handleStreamCreate.connect(self.handleStreamCreate)
        #self.create_stream_modal.handleCancelStreamCreate.connect(lambda: self.dockwidget.populateProjectStreams(self))
        self.create_stream_modal.show()
    
    def handleStreamCreate(self, account, str_name, description, is_public): 
        #if len(str_name)<3 and len(str_name)!=0: 
        #    logger.logToUser("Stream Name should be at least 3 characters", Qgis.Warning)
        new_client = SpeckleClient(
            account.serverInfo.url,
            account.serverInfo.url.startswith("https")
        )
        new_client.authenticate_with_token(token=account.token)

        str_id = new_client.stream.create(name=str_name, description = description, is_public = is_public) 
        if isinstance(str_id, GraphQLException) or isinstance(str_id, SpeckleException):
            arcpy.addWarning(str_id.message)
            return
        else:
            sw = StreamWrapper(account.serverInfo.url + "/streams/" + str_id)
            self.handleStreamAdd(sw)
        return 

    def onBranchCreateClicked(self):
        self.create_stream_modal = CreateBranchModalDialog(None)
        self.create_stream_modal.handleBranchCreate.connect(self.handleBranchCreate)
        self.create_stream_modal.show()
    
    def handleBranchCreate(self, br_name, description):
        #if len(br_name)<3: 
        #    logger.logToUser("Branch Name should be at least 3 characters", Qgis.Warning)
        #    return 
        br_name = br_name.lower()
        sw: StreamWrapper = self.active_stream[0]
        account = sw.get_account()
        new_client = SpeckleClient(
            account.serverInfo.url,
            account.serverInfo.url.startswith("https")
        )
        new_client.authenticate_with_token(token=account.token)
        #description = "No description provided"
        br_id = new_client.branch.create(stream_id = sw.stream_id, name = br_name, description = description) 
        if isinstance(br_id, GraphQLException):
            arcpy.addWarning(br_id.message)

        self.active_stream = (sw, tryGetStream(sw))
        self.current_streams[0] = self.active_stream

        self.dockwidget.populateActiveStreamBranchDropdown(self)
        self.dockwidget.populateActiveCommitDropdown(self)
        self.dockwidget.streamBranchDropdown.setCurrentText(br_name) # will be ignored if branch name is not in the list 

        return 

    def handleStreamAdd(self, sw: StreamWrapper):
        try:
            from speckle.ui.project_vars import set_project_streams
        except:
            from speckle_toolbox.esri.toolboxes.speckle.ui.project_vars import set_project_streams
           
        streamExists = 0
        index = 0
        try: 
            stream = tryGetStream(sw)
            
            for st in self.current_streams: 
                if isinstance(stream, Stream) and st[0].stream_id == stream.id: 
                    streamExists = 1; 
                    break 
                index += 1
        except SpeckleException as e:
            arcpy.addWarning(e.message)
            stream = None
        
        if streamExists == 0: 
            self.current_streams.insert(0,(sw, stream))
        else: 
            del self.current_streams[index]
            self.current_streams.insert(0,(sw, stream))
        try: self.add_stream_modal.handleStreamAdd.disconnect(self.handleStreamAdd)
        except: pass 
        set_project_streams(self)
        self.dockwidget.populateProjectStreams(self)
