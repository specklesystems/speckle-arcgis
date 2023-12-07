
import os
import os.path
import sys
from typing import Any, Callable, List, Optional, Tuple, Union

import threading
import inspect

from PyQt5.QtCore import QCoreApplication, QSettings, Qt, QTranslator, QRect 
from PyQt5.QtGui import QIcon
from PyQt5.QtWidgets import QApplication, QAction, QDockWidget, QVBoxLayout, QWidget
from PyQt5 import QtWidgets


from specklepy.api import operations
from specklepy.logging.exceptions import SpeckleException, GraphQLException
#from specklepy.api.credentials import StreamWrapper
from specklepy.api.models import Stream
from specklepy.api.wrapper import StreamWrapper
from specklepy.objects import Base
from specklepy.api.credentials import Account, get_local_accounts #, StreamWrapper
from specklepy.api.client import SpeckleClient
from specklepy.logging import metrics
import webbrowser

import arcpy
from arcpy._mp import ArcGISProject, Map
from arcpy._mp import Layer as arcLayer

try: 
    from speckle.speckle.plugin_utils.object_utils import callback, traverseObject
    from speckle.speckle.converter.layers.Layer import (Layer, VectorLayer, RasterLayer) 
    from speckle.speckle.converter.layers import convertSelectedLayers, getLayers
    from speckle.speckle.converter.layers.utils import findAndClearLayerGroup
    from speckle.speckle.ui.validation import tryGetStream, tryGetClient, validateBranch, validateCommit, validateStream, validateTransport 
    from speckle.speckle.ui.add_stream_modal import AddStreamModalDialog
    from speckle.speckle.ui.create_stream import CreateStreamModalDialog
    from speckle.speckle.ui.create_branch import CreateBranchModalDialog
    from speckle.speckle.ui.speckle_qgis_dialog import SpeckleGISDialog
    from speckle.speckle.ui.logger import logToUser, logToUserWithAction
    from speckle.speckle.plugin_utils.helpers import removeSpecialCharacters, getAppName
    from speckle.specklepy_qt_ui.qt_ui.DataStorage import DataStorage

except: 
    from speckle_toolbox.esri.toolboxes.speckle.speckle.plugin_utils.object_utils import callback, traverseObject
    from speckle_toolbox.esri.toolboxes.speckle.speckle.converter.layers.Layer import (Layer, VectorLayer, RasterLayer)
    from speckle_toolbox.esri.toolboxes.speckle.speckle.converter.layers import convertSelectedLayers, getLayers
    from speckle_toolbox.esri.toolboxes.speckle.speckle.converter.layers.emptyLayerTemplates import createGroupLayer
    from speckle_toolbox.esri.toolboxes.speckle.speckle.converter.layers.utils import findAndClearLayerGroup
    from speckle_toolbox.esri.toolboxes.speckle.speckle.ui.validation import tryGetStream, tryGetClient, validateBranch, validateCommit, validateStream, validateTransport 
    from speckle_toolbox.esri.toolboxes.speckle.speckle.ui.add_stream_modal import AddStreamModalDialog
    from speckle_toolbox.esri.toolboxes.speckle.speckle.ui.create_stream import CreateStreamModalDialog
    from speckle_toolbox.esri.toolboxes.speckle.speckle.ui.create_branch import CreateBranchModalDialog
    from speckle_toolbox.esri.toolboxes.speckle.speckle.ui.speckle_qgis_dialog import SpeckleGISDialog
    from speckle_toolbox.esri.toolboxes.speckle.speckle.ui.logger import logToUser, logToUserWithAction
    from speckle_toolbox.esri.toolboxes.speckle.speckle.plugin_utils.helpers import removeSpecialCharacters, getAppName
    from speckle_toolbox.esri.toolboxes.speckle.specklepy_qt_ui.qt_ui.DataStorage import DataStorage

# Import the code for the dialog

SPECKLE_COLOR = (59,130,246)
SPECKLE_COLOR_LIGHT = (69,140,255)

def startThread(sp_class): 
    print("START THREAD")
    t = threading.Thread(target=qtApp, args=(sp_class,))
    t.start()
    threads = threading.enumerate()
    print("__Total threads: " + str(len(threads)))

def qtApp(text: str):
    print("MAIN function")
    
    #threads = threading.enumerate()
    #print("__Total threads: " + str(len(threads)))
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
        try: 
            version: str = arcpy.GetInstallInfo()['Version']
            python_version: str = f"python {'.'.join(map(str, sys.version_info[:2]))}"
            #metrics.set_host_app("ArcGIS", "ArcGIS " + ', '.join([f"{version}", python_version])) 
            metrics.set_host_app("ArcGIS", "ArcGIS " + version.split(".")[0])

        except: 
            metrics.set_host_app("ArcGIS")

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

class SpeckleGIS:
    """Speckle Connector Plugin for ArcGIS"""

    version: str
    gis_version: str
    dataStorage: DataStorage
    dockwidget: Optional[SpeckleGISDialog]
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
    active_account: Account

    def __init__(self):
        """Constructor. 
        """
        print("Start SpeckleGIS")
        self.version = "0.0.99"
        try:
            version = arcpy.GetInstallInfo()['Version']
            python_version = f"python {'.'.join(map(str, sys.version_info[:2]))}"
            full_version = ' '.join([f"{version}", python_version])
        except: full_version = arcpy.GetInstallInfo()['Version']

        self.gis_version = full_version
        # Save reference to the QGIS interface
        self.dataStorage = None
        self.dockwidget = None
        #self.iface = None
        self.gis_project = ArcGISProject('CURRENT') #QgsProject.instance()
        self.current_streams = []
        self.active_stream = None
        self.default_account = None 
        self.active_account = None
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
        try:
            # disconnects
            if self.dockwidget:
                try: 
                    self.dockwidget.closingPlugin.disconnect(self.onClosePlugin)
                    self.dockwidget.close()
                except: pass 

            self.pluginIsActive = False
            # remove this statement if dockwidget is to remain
            # for reuse if plugin is reopened    
        except Exception as e: 
            logToUser(str(e), func = inspect.stack()[0][3])    
        

    def unload(self):
        """Removes the plugin menu item and icon from GIS GUI."""
        return
        #for action in self.actions:
        #    self.iface.removePluginWebMenu(self.tr("&SpeckleQGIS"), action)
        #    self.iface.removeToolBarIcon(action)

    def onRunButtonClicked(self):
        self.dockwidget.msgLog.setGeometry(0, 0, self.dockwidget.frameSize().width(), self.dockwidget.frameSize().height())
        try:
            streamWrapper = self.active_stream[0]
            client = streamWrapper.get_client()
            self.active_account = client.account 
        except:
            pass        

        if self.btnAction == 0: self.onSend()
        elif self.btnAction == 1: self.onReceive()

    def onSend(self):
        """Handles action when Send button is pressed."""
        try:
            if not self.dockwidget: return
            print("On Send")

            # Check if stream id/url is empty
            if self.active_stream is None:
                logToUser("Please select a stream from the list.", level=1, func = inspect.stack()[0][3], plugin = self.dockwidget)
                return

            self.gis_project = ArcGISProject("CURRENT")
            if self.gis_project.activeMap is None: 
                logToUser("No active Map", level=1, func = inspect.stack()[0][3], plugin = self.dockwidget)
                return 

            print("On Send 2")
            # creating our parent base object
            project = self.gis_project
            #projectCRS = project.Sp
            #layerTreeRoot = project.layerTreeRoot()

            bySelection = True
            if self.dockwidget.layerSendModeDropdown.currentIndex() == 1: bySelection = False 
            layers = getLayers(self, bySelection) # List[QgsLayerTreeNode]
            
            # Check if no layers are selected
            if len(layers) == 0: #len(selectedLayerNames) == 0:
                logToUser("No layers selected", level=1, func = inspect.stack()[0][3], plugin = self.dockwidget)
                return
            print(layers)
            print("On Send 3")
            base_obj = Base(units = "m")
            base_obj.layers = convertSelectedLayers(layers, project)
            if base_obj.layers is None:
                return 

            # Reset Survey point
            self.dockwidget.populateSurveyPoint(self)

            # Get the stream wrapper
            streamWrapper = self.active_stream[0]
            streamName = self.active_stream[1].name
            streamId = streamWrapper.stream_id
            
            # client = streamWrapper.get_client()
            client, stream = tryGetClient(
                    streamWrapper, self.dataStorage, False, self.dockwidget
                )

            stream = validateStream(stream, self.dockwidget)
            if stream == None: return
            
            branchName = str(self.dockwidget.streamBranchDropdown.currentText())
            branch = validateBranch(stream, branchName, False)
            if branch == None: return

            transport = validateTransport(client, streamId)
            if transport == None: return
        except Exception as e: 
            logToUser(str(e), level=2, func = inspect.stack()[0][3], plugin = self.dockwidget) 
            return
    
        try:
            # this serialises the block and sends it to the transport
            objId = operations.send(base=base_obj, transports=[transport])
        except SpeckleException as e:
            logToUser("Error sending data: " + str(e.message), level=2, func = inspect.stack()[0][3], plugin = self.dockwidget)
            return

        try:
            message = str(self.dockwidget.messageInput.text())
            # you can now create a commit on your stream with this object
            commit_id = client.commit.create(
                stream_id=streamId,
                object_id=objId,
                branch_name=branchName,
                message="Sent objects from ArcGIS" if len(message) == 0 else message,
                source_application="ArcGIS " + self.gis_version.split(".")[0],
            )
            r'''
            try:
                metr_filter = "Visible" if bySelection is True else "Saved"
                metr_main = True if branchName=="main" else False
                metr_saved_streams = len(self.current_streams)
                metr_branches = len(self.active_stream[1].branches.items)
                metr_collab = len(self.active_stream[1].collaborators)
                metr_projected = True if self.gis_project.activeMap.spatialReference.type != "Geographic" else False 
                if self.gis_project.activeMap.spatialReference is None: metr_projected = None

                python_version: str = f"python {'.'.join(map(str, sys.version_info[:2]))}"
                try:
                    crs_lat = project.activeMap.spatialReference.latitudeOfOrigin
                    crs_lon = project.activeMap.spatialReference.centralMeridian
                    metr_crs = True if self.lat!=0 and self.lon!=0 and crs_lat == self.lat and crs_lon == self.lon else False
                except:
                    metr_crs = False

                metrics.track(metrics.SEND, self.active_account, {"hostAppFullVersion":self.gis_version, "pythonVersion": python_version,"branches":metr_branches, "collaborators":metr_collab,"connector_version": str(self.version), "filter": metr_filter, "isMain": metr_main, "savedStreams": metr_saved_streams, "projectedCRS": metr_projected, "customCRS": metr_crs})
            except:
                metrics.track(metrics.SEND, self.active_account)
            '''
            
            if isinstance(commit_id, SpeckleException):
                logToUser("Error creating commit: "+str(commit_id.message), level = 2, func = inspect.stack()[0][3], plugin=self.dockwidget)
                return
            arcpy.AddMessage("Successfully sent data to stream: " + streamId)

            url = streamWrapper.stream_url.split("?")[0] + "/commits/" + commit_id

            self.dockwidget.messageInput.setText("")
            logToUser(f"👌 Data sent to \"{streamName}\" \n View it online", level = 0, plugin=self.dockwidget, url = url)

        except SpeckleException as e:
            logToUser("Error creating commit:" + e.message, level=2, func = inspect.stack()[0][3], plugin = self.dockwidget)
    
    def onReceive(self):
        """Handles action when the Receive button is pressed"""
        try:
            print("ON RECEIVE")
            if not self.dockwidget: return

            # Check if stream id/url is empty
            if self.active_stream is None:
                logToUser("Please select a stream from the list.", level=1, func = inspect.stack()[0][3], plugin = self.dockwidget)
                return

            self.gis_project = ArcGISProject("CURRENT")
            if self.gis_project.activeMap is None: 
                logToUser("No active Map", level=1, func = inspect.stack()[0][3])
                return 

            # Get the stream wrapper
            streamWrapper = self.active_stream[0]
            streamId = streamWrapper.stream_id
            #client = streamWrapper.get_client()
            
            client, stream = tryGetClient(
                    streamWrapper, self.dataStorage, False, self.dockwidget
                )
            # Ensure the stream actually exists
            print("ON RECEIVE 2")
        except Exception as e: 
            logToUser(str(e), level=2, func = inspect.stack()[0][3], plugin = self.dockwidget) 
            return
        try:

            stream = validateStream(stream, self.dockwidget)
            if stream == None: return
            
            branchName = str(self.dockwidget.streamBranchDropdown.currentText())
            branch = validateBranch(stream, branchName, True)
            if branch == None: return

            commitId = str(self.dockwidget.commitDropdown.currentText())
            commit = validateCommit(branch, commitId)
            if commit == None: return

        except SpeckleException as e:
            logToUser(str(e.message), level=2, func = inspect.stack()[0][3], plugin = self.dockwidget)
            return

        transport = validateTransport(client, streamId)
        if transport == None: return 
        print("ON RECEIVE 3")
        try:
            objId = commit.referencedObject
            
            if branch.name is None or commit.id is None or objId is None: 
                return 
            
            #commitDetailed = client.commit.get(streamId, commit.id)
            app_full = commit.sourceApplication
            app = getAppName(commit.sourceApplication)
            client_id = client.account.userInfo.id

            commitObj = operations._untracked_receive(objId, transport, None)
            
            try:
                crs_lat = self.gis_project.activeMap.spatialReference.latitudeOfOrigin
                crs_lon = self.gis_project.activeMap.spatialReference.centralMeridian
                metr_crs = True if self.lat!=0 and self.lon!=0 and crs_lat == self.lat and crs_lon == self.lon else False
                metr_projected = True if self.gis_project.activeMap.spatialReference.type != "Geographic" else False 
                if self.gis_project.activeMap.spatialReference is None: metr_projected = None
            except:
                metr_crs = False

            try:
                python_version: str = f"python {'.'.join(map(str, sys.version_info[:2]))}"
                metrics.track(metrics.RECEIVE, self.active_account, {"hostAppFullVersion":self.gis_version,"pythonVersion": python_version,"sourceHostAppVersion": app_full, "sourceHostApp": app, "isMultiplayer": commit.authorId != client_id,"connector_version": str(self.version), "projectedCRS": metr_projected, "customCRS": metr_crs})
            except:
                metrics.track(metrics.RECEIVE, self.active_account)

            client.commit.received(
            streamId,
            commit.id,
            source_application="ArcGIS " + self.gis_version.split(".")[0],
            message="Received commit in ArcGIS",
            )

            if app.lower() != "qgis" and app.lower() != "arcgis":
                if self.gis_project.activeMap.spatialReference.type == "Geographic" or self.gis_project.activeMap.spatialReference is None: #TODO test with invalid CRS
                    logToUser("Conversion from metric units to DEGREES not supported. It is advisable to set the project Spatial reference to Projected type before receiving CAD geometry (e.g. EPSG:32631), or create a custom one from geographic coordinates", level=0, func = inspect.stack()[0][3], plugin = self.dockwidget)
            arcpy.AddMessage(f"Succesfully received {objId}")

            # If group exists, remove layers inside  
            newGroupName = streamId + "_" + branch.name + "_" + commit.id
            newGroupName = removeSpecialCharacters(newGroupName)
            findAndClearLayerGroup(self.gis_project, newGroupName)
            
            print("after create group")
            if app.lower() == "qgis" or app.lower() == "arcgis": check: Callable[[Base], bool] = lambda base: base.speckle_type and (base.speckle_type.endswith("VectorLayer") or base.speckle_type.endswith("Layer") or base.speckle_type.endswith("RasterLayer") )
            else: check: Callable[[Base], bool] = lambda base: (base.speckle_type and base.speckle_type.endswith("Base") )
            traverseObject(commitObj, callback, check, str(newGroupName), self)

            logToUser("👌 Data received", level = 0, plugin = self.dockwidget, blue = True)
            return 
            
        except SpeckleException as e:
            logToUser("Receive failed: "+ e.message, level=2, func = inspect.stack()[0][3], plugin = self.dockwidget)
            return

    def reloadUI(self):
        
        try:
            from speckle.ui.project_vars import get_project_streams, get_survey_point, get_project_layer_selection
        except: 
            from speckle_toolbox.esri.toolboxes.speckle.speckle.ui.project_vars import get_project_streams, get_survey_point, get_project_layer_selection
        
        self.dataStorage = DataStorage()
        self.dataStorage.plugin_version = self.version

        self.is_setup = self.dataStorage.check_for_accounts()
        if self.dockwidget is not None:
            self.active_stream = None
            get_project_streams(self)
            get_survey_point(self)
            get_project_layer_selection(self)

            self.dockwidget.reloadDialogUI(self)

    def check_for_accounts(self):
        def go_to_manager():
            webbrowser.open("https://speckle-releases.netlify.app/")
        try:
            accounts = get_local_accounts()
            self.accounts = accounts
            if len(accounts) == 0:
                logToUser("No accounts were found. Please remember to install the Speckle Manager and setup at least one account", level=1, url="https://speckle-releases.netlify.app/", func = inspect.stack()[0][3])
                return False
            for acc in accounts:
                if acc.isDefault: 
                    self.default_account = acc 
                    self.active_account = acc
                    break
            return True
        except Exception as e: 
            logToUser(str(e), level=2, func = inspect.stack()[0][3]) 
            return False

    def run(self):
        """Run method that performs all the real work"""
        print("run plugin")
        try:
            from speckle.speckle.ui.speckle_qgis_dialog import SpeckleGISDialog
            from speckle.speckle.ui.project_vars import get_project_streams, get_survey_point, get_project_layer_selection
        except: 
            from speckle_toolbox.esri.toolboxes.speckle.speckle.ui.speckle_qgis_dialog import SpeckleGISDialog
            from speckle_toolbox.esri.toolboxes.speckle.speckle.ui.project_vars import get_project_streams, get_survey_point, get_project_layer_selection
        try: 
            # Create the dialog with elements (after translation) and keep reference
            # Only create GUI ONCE in callback, so that it will only load when the plugin is started
            self.is_setup = self.check_for_accounts()
            
            if self.pluginIsActive:
                self.reloadUI()
            else:
                
                self.dataStorage = DataStorage()
                self.dataStorage.plugin_version = self.version
                self.is_setup = self.dataStorage.check_for_accounts()

                self.pluginIsActive = True
                if self.dockwidget is None:
                    self.dockwidget = SpeckleGISDialog()
                    self.dockwidget.addLabel(self)
                    self.dockwidget.addProps(self)
                    self.dockwidget.show()
                    #self.gis_project.fileNameChanged.connect(self.reloadUI)
                    #self.gis_project.homePathChanged.connect(self.reloadUI)
                print("run plugin 2")
                get_project_streams(self)
                print("run plugin 3")
                get_survey_point(self)
                print("run plugin 4")
                get_project_layer_selection(self)
                print("run plugin 5")

                self.dockwidget.run(self)

                # show the dockwidget
                #self.iface.addDockWidget(Qt.RightDockWidgetArea, self.dockwidget)
                self.dockwidget.enableElements(self)
        except Exception as e: 
            logToUser(str(e), level=2, func = inspect.stack()[0][3]) 

    def onStreamAddButtonClicked(self):
        self.add_stream_modal = AddStreamModalDialog(None)
        self.add_stream_modal.handleStreamAdd.connect(self.handleStreamAdd)
        self.add_stream_modal.show()

    def set_survey_point(self): 
        try:
            from speckle.ui.project_vars import set_survey_point
        except: 
            from speckle_toolbox.esri.toolboxes.speckle.speckle.ui.project_vars import set_survey_point
        set_survey_point(self)

    def onStreamCreateClicked(self):
        self.create_stream_modal = CreateStreamModalDialog(None)
        self.create_stream_modal.handleStreamCreate.connect(self.handleStreamCreate)
        #self.create_stream_modal.handleCancelStreamCreate.connect(lambda: self.dockwidget.populateProjectStreams(self))
        self.create_stream_modal.show()
    
    def handleStreamCreate(self, account, str_name, description, is_public): 
        try: 
            #if len(str_name)<3 and len(str_name)!=0: 
            #    logger.logToUser("Stream Name should be at least 3 characters", Qgis.Warning)
            new_client = SpeckleClient(
                account.serverInfo.url,
                account.serverInfo.url.startswith("https")
            )
            new_client.authenticate_with_token(token=account.token)

            str_id = new_client.stream.create(name=str_name, description = description, is_public = is_public) 
            if isinstance(str_id, GraphQLException) or isinstance(str_id, SpeckleException):
                logToUser(str_id.message, level=2, func = inspect.stack()[0][3])
                return
            else:
                sw = StreamWrapper(account.serverInfo.url + "/streams/" + str_id)
                self.handleStreamAdd(sw) 
            return 
        except Exception as e: 
            logToUser(str(e), level=2, func = inspect.stack()[0][3])
            return 

    def onBranchCreateClicked(self):
        self.create_stream_modal = CreateBranchModalDialog(None)
        self.create_stream_modal.handleBranchCreate.connect(self.handleBranchCreate)
        self.create_stream_modal.show()
    
    def handleBranchCreate(self, br_name, description):
        #if len(br_name)<3: 
        #    logger.logToUser("Branch Name should be at least 3 characters", Qgis.Warning)
        #    return 
        try:
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
                logToUser(br_id.message, level=2, func = inspect.stack()[0][3])

            self.active_stream = (sw, tryGetStream(sw, self.dataStorage))
            self.current_streams[0] = self.active_stream

            self.dockwidget.populateActiveStreamBranchDropdown(self)
            self.dockwidget.populateActiveCommitDropdown(self)
            self.dockwidget.streamBranchDropdown.setCurrentText(br_name) # will be ignored if branch name is not in the list 

            return 
        except Exception as e: 
            logToUser(str(e), level=2, func = inspect.stack()[0][3]) 

    def handleStreamAdd(self, sw: StreamWrapper):
        try:
            from speckle.speckle.ui.project_vars import set_project_streams
        except:
            from speckle_toolbox.esri.toolboxes.speckle.speckle.ui.project_vars import set_project_streams
           
        streamExists = 0
        index = 0
        try: 
            stream = tryGetStream(sw, self.dataStorage)
            
            for st in self.current_streams: 
                if isinstance(stream, Stream) and st[0].stream_id == stream.id: 
                    streamExists = 1; 
                    break 
                index += 1
        except SpeckleException as e:
            logToUser(e.message, level=2, func = inspect.stack()[0][3])
            stream = None
        try:
            if streamExists == 0: 
                self.current_streams.insert(0,(sw, stream))
            else: 
                del self.current_streams[index]
                self.current_streams.insert(0,(sw, stream))
            try: self.add_stream_modal.handleStreamAdd.disconnect(self.handleStreamAdd)
            except: pass 
            set_project_streams(self)
            self.dockwidget.populateProjectStreams(self)
        
            return 
        except Exception as e: 
            logToUser(str(e), level=2, func = inspect.stack()[0][3]) 