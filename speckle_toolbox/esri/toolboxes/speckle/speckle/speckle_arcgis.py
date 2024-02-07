from copy import copy
from datetime import datetime
import os
import os.path
import sys
from typing import Any, Callable, List, Optional, Tuple, Union

import threading
import inspect

from PyQt5.QtWidgets import QApplication
from PyQt5 import QtWidgets


from specklepy.api import operations
from specklepy.logging.exceptions import (
    SpeckleException,
    GraphQLException,
    SpeckleInvalidUnitException,
)


# from specklepy.api.credentials import StreamWrapper
from specklepy.api.models import Stream
from specklepy.api.wrapper import StreamWrapper
from specklepy.objects import Base
from specklepy.api.credentials import Account, get_local_accounts  # , StreamWrapper
from specklepy.api.client import SpeckleClient
from specklepy.logging import metrics
from specklepy.objects.other import Collection
import webbrowser

import arcpy
from arcpy._mp import ArcGISProject, Map
from arcpy._mp import Layer as arcLayer
from specklepy.objects.units import get_units_from_string

from speckle.speckle.plugin_utils.threads import KThread
from speckle.speckle.plugin_utils.object_utils import callback, traverseObject
from speckle.speckle.converter.layers import convertSelectedLayers, getLayers
from speckle.speckle.converter.layers.utils import findAndClearLayerGroup
from speckle.speckle.utils.validation import (
    tryGetStream,
    tryGetClient,
    validateBranch,
    validateCommit,
    validateStream,
    validateTransport,
)

from speckle.speckle.converter.layers.layer_conversions import (
    addBimMainThread,
    addCadMainThread,
    addExcelMainThread,
    addNonGeometryMainThread,
    addRasterMainThread,
    addVectorMainThread,
    convertSelectedLayersToSpeckle,
)

from speckle.specklepy_qt_ui.qt_ui.widget_add_stream import AddStreamModalDialog
from speckle.specklepy_qt_ui.qt_ui.widget_create_stream import CreateStreamModalDialog
from speckle.specklepy_qt_ui.qt_ui.widget_create_branch import CreateBranchModalDialog
from speckle.ui_widgets.main_window import SpeckleGISDialog
from speckle.speckle.utils.panel_logging import logToUser
from speckle.specklepy_qt_ui.qt_ui.utils.utils import constructCommitURL
from speckle.speckle.plugin_utils.helpers import removeSpecialCharacters, getAppName
from speckle.specklepy_qt_ui.qt_ui.DataStorage import DataStorage
from speckle.specklepy_qt_ui.qt_ui.widget_custom_crs import CustomCRSDialog

# Import the code for the dialog

SPECKLE_COLOR = (59, 130, 246)
SPECKLE_COLOR_LIGHT = (69, 140, 255)


def startThread(sp_class):
    print("START THREAD")
    t = threading.Thread(target=qtApp, args=(sp_class,))
    t.start()
    threads = threading.enumerate()
    print("__Total threads: " + str(len(threads)))


def qtApp(text: str):
    print("MAIN function")

    app = QApplication(sys.argv)
    ex = SpeckleGIS()
    # ex.show()
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
            version: str = arcpy.GetInstallInfo()["Version"]
            python_version: str = f"python {'.'.join(map(str, sys.version_info[:2]))}"
            metrics.set_host_app("ArcGIS", "ArcGIS " + version.split(".")[0])

        except:
            metrics.set_host_app("ArcGIS")


class Speckle:
    # instances = []
    def __init__(self):

        print("___start speckle tool_________")

        self.label = "Speckle"
        self.description = (
            "Allows you to send and receive your layers "
            + "to/from other software using Speckle server."
        )

    def getParameterInfo(self):
        cat1 = "category 1"

        param0 = arcpy.Parameter(
            displayName="""▷ Run to launch Speckle Connector
""",  # ▶
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

    def isLicensed(self):  # optional
        return True

    def updateParameters(self, parameters: List, toRefresh=False):  # optional
        return

    def execute(self, parameters: List, messages):
        qtApp("")


class SpeckleGIS:
    """Speckle Connector Plugin for ArcGIS"""

    workspace: Any
    version: str
    gis_version: str
    dataStorage: DataStorage
    dockwidget: Optional[SpeckleGISDialog]
    add_stream_modal: AddStreamModalDialog
    create_stream_modal: CreateStreamModalDialog
    current_streams: List[Tuple[StreamWrapper, Stream]]  # {id:(sw,st),id2:()}
    current_layers: List[Tuple[str, arcLayer]] = []

    active_stream: Optional[Tuple[StreamWrapper, Stream]]

    project: ArcGISProject  # QgsProject

    lat: float
    lon: float

    default_account: Account
    accounts: List[Account]
    active_account: Account

    def __init__(self):
        """Constructor."""
        print("Start SpeckleGIS")
        self.version = "0.0.99"
        try:
            version = arcpy.GetInstallInfo()["Version"]
            python_version = f"python {'.'.join(map(str, sys.version_info[:2]))}"
            full_version = " ".join([f"{version}", python_version])
        except:
            full_version = arcpy.GetInstallInfo()["Version"]

        self.workspace = arcpy.env.workspace
        self.gis_version = full_version
        # Save reference to the QGIS interface
        self.dataStorage = None
        self.dockwidget = None
        # self.iface = None
        self.project = ArcGISProject("CURRENT")  # QgsProject.instance()
        self.current_streams = []
        self.active_stream = None
        self.active_branch = None
        self.active_commit = None
        self.receive_layer_tree = None
        # self.default_account = None
        # self.accounts = []
        # self.active_account = None
        self.theads_total = 0
        self.btnAction = 0

        self.lat = 0.0
        self.lon = 0.0
        # initialize plugin directory
        self.plugin_dir = os.path.dirname(__file__)

        # Declare instance attributes
        self.actions = []

        # Check if plugin was started the first time in current QGIS session
        # Must be set in initGui() to survive plugin reloads
        self.pluginIsActive = False
        self.run()

    def onClosePlugin(self):
        """Cleanup necessary items here when plugin dockwidget is closed"""
        try:
            # disconnects
            if self.dockwidget:
                try:
                    self.dockwidget.closingPlugin.disconnect(self.onClosePlugin)
                    self.dockwidget.close()
                except:
                    pass

            self.pluginIsActive = False
            # remove this statement if dockwidget is to remain
            # for reuse if plugin is reopened
        except Exception as e:
            logToUser(str(e), func=inspect.stack()[0][3])

    def unload(self):
        """Removes the plugin menu item and icon from GIS GUI."""
        return

    def onRunButtonClicked(self):

        try:
            all_threads = threading.enumerate()

            for t in all_threads:
                if t.name.startswith("speckle"):
                    name = ""
                    if "receive" in t.name:
                        name = "Receive"
                    if "send" in t.name:
                        name = "Send"
                    logToUser(
                        f"Previous {name} operation is still running \nClick here to cancel",
                        level=2,
                        url="cancel",
                        plugin=self.dockwidget,
                    )
                    return

            # set the project instance
            self.project = ArcGISProject("CURRENT")
            self.dataStorage.project = self.project
            self.dockwidget.msgLog.setGeometry(
                0,
                0,
                self.dockwidget.frameSize().width(),
                self.dockwidget.frameSize().height(),
            )
            self.dockwidget.reportBtn.setEnabled(True)

            # send
            if self.btnAction == 0:
                # Reset Survey point
                # self.dockwidget.populateSurveyPoint(self)
                # Get and clear message
                message = str(self.dockwidget.messageInput.text())
                self.dockwidget.messageInput.setText("")

                try:
                    streamWrapper = self.active_stream[0]
                    client = streamWrapper.get_client()
                    self.dataStorage.active_account = client.account
                    logToUser(
                        f"Sending data... \nClick here to cancel",
                        level=0,
                        url="cancel",
                        plugin=self.dockwidget,
                    )
                    t = KThread(
                        target=self.onSend, name="speckle_send", args=(message,)
                    )
                    t.start()
                except:
                    self.onSend(message)

            # receive
            elif self.btnAction == 1:
                ################### repeated
                try:
                    if not self.dockwidget:
                        return
                    # Check if stream id/url is empty
                    if self.active_stream is None:
                        logToUser(
                            "Please select a stream from the list",
                            level=2,
                            func=inspect.stack()[0][3],
                            plugin=self.dockwidget,
                        )
                        return

                    # Get the stream wrapper
                    streamWrapper = self.active_stream[0]
                    streamId = streamWrapper.stream_id

                    # client = streamWrapper.get_client()
                    client, stream = tryGetClient(
                        streamWrapper, self.dataStorage, False, self.dockwidget
                    )
                    stream = validateStream(stream, self.dockwidget)
                    if stream == None:
                        return
                except Exception as e:
                    logToUser(
                        e, level=2, func=inspect.stack()[0][3], plugin=self.dockwidget
                    )
                    return

                # Ensure the stream actually exists
                try:
                    branchName = str(self.dockwidget.streamBranchDropdown.currentText())
                    branch = validateBranch(stream, branchName, True, self.dockwidget)
                    if branch == None:
                        return

                    commitId = str(self.dockwidget.commitDropdown.currentText())
                    commit = validateCommit(branch, commitId, self.dockwidget)
                    if commit == None:
                        return

                    # If group exists, remove layers inside
                    newGroupName = streamId + "_" + branch.name + "_" + commit.id
                    newGroupName = removeSpecialCharacters(newGroupName)
                    findAndClearLayerGroup(self.project, newGroupName, self)

                except Exception as e:
                    logToUser(
                        str(e),
                        level=2,
                        func=inspect.stack()[0][3],
                        plugin=self.dockwidget,
                    )
                    return
                ########################################### end of repeated

                try:
                    streamWrapper = self.active_stream[0]
                    client = streamWrapper.get_client()
                    self.dataStorage.active_account = client.account
                    logToUser(
                        "Receiving data... \nClick here to cancel",
                        level=0,
                        url="cancel",
                        plugin=self.dockwidget,
                    )

                    t = KThread(target=self.onReceive, name="speckle_receive", args=())
                    t.start()
                except:
                    self.onReceive()
        except Exception as e:
            logToUser(e, level=2, plugin=self.dockwidget)

    def onSend(self, message: str):
        """Handles action when Send button is pressed."""
        try:
            if not self.dockwidget:
                return
            print("On Send")

            bySelection = True
            if self.dockwidget.layerSendModeDropdown.currentIndex() == 1:
                bySelection = False
            layers = getLayers(self, bySelection)  # List[QgsLayerTreeNode]

            # Check if stream id/url is empty
            if self.active_stream is None:
                logToUser(
                    "Please select a stream from the list.",
                    level=1,
                    func=inspect.stack()[0][3],
                    plugin=self.dockwidget,
                )
                return
            current_active_stream = copy(self.active_stream)

            # Check if no layers are selected
            if layers is None or (
                isinstance(layers, list) and len(layers) == 0
            ):  # len(selectedLayerNames) == 0:
                logToUser(
                    "No layers selected",
                    level=1,
                    func=inspect.stack()[0][3],
                    plugin=self.dockwidget,
                )
                return
            print(layers)
            self.dataStorage.latestActionLayers = [l.name() for l in layers]

            # TODO: get layer tree
            # root = self.dataStorage.project.layerTreeRoot()
            # self.dataStorage.all_layers = getAllLayers(root)
            self.dataStorage.all_layers = layers

            # self.project = ArcGISProject("CURRENT")
            if self.project.activeMap is None:
                logToUser(
                    "Project Active Map not loaded or not selected",
                    level=1,
                    func=inspect.stack()[0][3],
                    plugin=self.dockwidget,
                )
                return

            units = str(self.project.activeMap.spatialReference.linearUnitName)
            self.dataStorage.latestActionUnits = units
            try:
                units = get_units_from_string(units)
            except SpeckleInvalidUnitException:
                units = "none"
            self.dataStorage.currentUnits = units

            if (
                self.dataStorage.crs_offset_x is not None
                and self.dataStorage.crs_offset_x
            ) != 0 or (
                self.dataStorage.crs_offset_y is not None
                and self.dataStorage.crs_offset_y
            ):
                logToUser(
                    f"Applying CRS offsets: x={self.dataStorage.crs_offset_x}, y={self.dataStorage.crs_offset_y}",
                    level=0,
                    plugin=self.dockwidget,
                )
            if (
                self.dataStorage.crs_rotation is not None
                and self.dataStorage.crs_rotation
            ) != 0:
                logToUser(
                    f"Applying CRS rotation: {self.dataStorage.crs_rotation}°",
                    level=0,
                    plugin=self.dockwidget,
                )

            print("On Send 2")
            # creating our parent base object
            project = self.project
            # projectCRS = project.Sp
            # layerTreeRoot = project.layerTreeRoot()

            self.dataStorage.latestActionReport = []
            self.dataStorage.latestActionFeaturesReport = []
            base_obj = Collection(
                units=units,
                collectionType="ArcGIS commit",
                name="ArcGIS commit",
                elements=[],
            )

            print("On Send 3")
            # conversions
            time_start_conversion = datetime.now()
            base_obj.layers = convertSelectedLayers(layers, project)
            time_end_conversion = datetime.now()

            if (
                base_obj is None
                or base_obj.elements is None
                or (isinstance(base_obj.elements, List) and len(base_obj.elements) == 0)
            ):
                logToUser(f"No data to send", level=2, plugin=self.dockwidget)
                return

            logToUser(f"Sending data to the server...", level=0, plugin=self.dockwidget)

            streamWrapper = current_active_stream[0]
            streamName = current_active_stream[1].name
            streamId = streamWrapper.stream_id

            client, stream = tryGetClient(
                streamWrapper, self.dataStorage, True, self.dockwidget
            )
            if not isinstance(client, SpeckleClient) or not isinstance(stream, Stream):
                return

            stream = validateStream(stream, self.dockwidget)
            if not isinstance(stream, Stream):
                return

            branchName = str(self.dockwidget.streamBranchDropdown.currentText())
            branch = validateBranch(stream, branchName, False, self.dockwidget)
            branchId = branch.id
            if branch == None:
                return

            transport = validateTransport(client, streamId)
            if transport == None:
                return

        except Exception as e:
            logToUser(
                str(e), level=2, func=inspect.stack()[0][3], plugin=self.dockwidget
            )
            return

        try:
            self.dockwidget.signal_remove_btn_url.emit("cancel")
            time_start_transfer = datetime.now()
            # this serialises the block and sends it to the transport
            objId = operations.send(base=base_obj, transports=[transport])
        except SpeckleException as e:
            logToUser(
                "Error sending data: " + str(e),
                level=2,
                func=inspect.stack()[0][3],
                plugin=self.dockwidget,
            )
            time_end_transfer = datetime.now()
            return

        try:
            # you can now create a commit on your stream with this object
            commit_id = client.commit.create(
                stream_id=streamId,
                object_id=objId,
                branch_name=branchName,
                message="Sent objects from ArcGIS" if len(message) == 0 else message,
                source_application="ArcGIS " + self.gis_version.split(".")[0],
            )
            r"""
            try:
                metr_filter = "Visible" if bySelection is True else "Saved"
                metr_main = True if branchName=="main" else False
                metr_saved_streams = len(self.current_streams)
                metr_branches = len(self.active_stream[1].branches.items)
                metr_collab = len(self.active_stream[1].collaborators)
                metr_projected = True if self.project.activeMap.spatialReference.type != "Geographic" else False 
                if self.project.activeMap.spatialReference is None: metr_projected = None

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
            """

            # add time stats to the report
            self.dataStorage.latestActionTime = str(
                datetime.now().strftime("%d/%m/%Y, %H:%M:%S")
            )
            self.dataStorage.latestTransferTime = str(
                time_end_transfer - time_start_transfer
            )
            self.dataStorage.latestConversionTime = str(
                time_end_conversion - time_start_conversion
            )

            if isinstance(commit_id, SpeckleException):
                logToUser(
                    "Error creating commit: " + str(commit_id.message),
                    level=2,
                    func=inspect.stack()[0][3],
                    plugin=self.dockwidget,
                )
                return

            url: str = constructCommitURL(streamWrapper, branchId, commit_id)

            if str(self.dockwidget.commitDropdown.currentText()).startswith("Latest"):
                stream = client.stream.get(
                    id=streamId, branch_limit=100, commit_limit=100
                )
                branch = validateBranch(stream, branchName, False, self.dockwidget)
                self.active_commit = branch.commits.items[0]

            if self.project.activeMap.spatialReference.type == "Geographic":
                logToUser(
                    "Data has been sent in the units 'degrees'. It is advisable to set the project CRS to Projected type (e.g. EPSG:32631) to be able to receive geometry correctly in CAD/BIM software. You can also create a custom CRS by setting geographic coordinates and using 'Set as a project center' function.",
                    level=1,
                    plugin=self.dockwidget,
                )

            arcpy.AddMessage("Successfully sent data to stream: " + streamId)

            self.dockwidget.msgLog.dataStorage = self.dataStorage

            logToUser(
                "Data sent to '"
                + str(streamName)
                + "'"
                + "\nClick to view commit online",
                level=0,
                plugin=self.dockwidget,
                url=url,
                report=True,
            )

        except SpeckleException as e:
            logToUser(
                "Error creating commit:" + e,
                level=2,
                func=inspect.stack()[0][3],
                plugin=self.dockwidget,
            )

    def onReceive(self):
        """Handles action when the Receive button is pressed"""
        try:
            print("ON RECEIVE")
            if not self.dockwidget:
                return

            # Check if stream id/url is empty
            if self.active_stream is None:
                logToUser(
                    "Please select a stream from the list.",
                    level=1,
                    func=inspect.stack()[0][3],
                    plugin=self.dockwidget,
                )
                return

            # self.project = ArcGISProject("CURRENT")
            if self.project.activeMap is None:
                logToUser("No active Map", level=1, func=inspect.stack()[0][3])
                return

            # Get the stream wrapper
            streamWrapper = self.active_stream[0]
            streamId = streamWrapper.stream_id
            # client = streamWrapper.get_client()

            client, stream = tryGetClient(
                streamWrapper, self.dataStorage, False, self.dockwidget
            )
            # Ensure the stream actually exists
            print("ON RECEIVE 2")
        except Exception as e:
            logToUser(
                str(e), level=2, func=inspect.stack()[0][3], plugin=self.dockwidget
            )
            return
        try:

            stream = validateStream(stream, self.dockwidget)
            if stream == None:
                return

            branchName = str(self.dockwidget.streamBranchDropdown.currentText())
            branch = validateBranch(stream, branchName, True, self.dockwidget)
            if branch == None:
                return

            commitId = str(self.dockwidget.commitDropdown.currentText())
            commit = validateCommit(branch, commitId, self.dockwidget)
            if commit == None:
                return

        except SpeckleException as e:
            logToUser(
                str(e),
                level=2,
                func=inspect.stack()[0][3],
                plugin=self.dockwidget,
            )
            return

        transport = validateTransport(client, streamId)
        if transport == None:
            return
        print("ON RECEIVE 3")
        try:
            objId = commit.referencedObject

            if branch.name is None or commit.id is None or objId is None:
                return

            # commitDetailed = client.commit.get(streamId, commit.id)
            app_full = commit.sourceApplication
            app = getAppName(commit.sourceApplication)
            client_id = client.account.userInfo.id

            commitObj = operations._untracked_receive(objId, transport, None)
            self.dockwidget.signal_remove_btn_url.emit("cancel")

            try:
                crs_lat = self.project.activeMap.spatialReference.latitudeOfOrigin
                crs_lon = self.project.activeMap.spatialReference.centralMeridian
                metr_crs = (
                    True
                    if self.lat != 0
                    and self.lon != 0
                    and crs_lat == self.lat
                    and crs_lon == self.lon
                    else False
                )
                metr_projected = (
                    True
                    if self.project.activeMap.spatialReference.type != "Geographic"
                    else False
                )
                if self.project.activeMap.spatialReference is None:
                    metr_projected = None
            except:
                metr_crs = False

            try:
                python_version: str = (
                    f"python {'.'.join(map(str, sys.version_info[:2]))}"
                )
                metrics.track(
                    metrics.RECEIVE,
                    self.dataStorage.active_account,
                    {
                        "hostAppFullVersion": self.gis_version,
                        "pythonVersion": python_version,
                        "sourceHostAppVersion": app_full,
                        "sourceHostApp": app,
                        "isMultiplayer": commit.authorId != client_id,
                        "connector_version": str(self.version),
                        "projectedCRS": metr_projected,
                        "customCRS": metr_crs,
                    },
                )
            except:
                metrics.track(metrics.RECEIVE, self.dataStorage.active_account)

            client.commit.received(
                streamId,
                commit.id,
                source_application="ArcGIS " + self.gis_version.split(".")[0],
                message="Received commit in ArcGIS",
            )

            if app.lower() != "qgis" and app.lower() != "arcgis":
                if (
                    self.project.activeMap.spatialReference.type == "Geographic"
                    or self.project.activeMap.spatialReference is None
                ):  # TODO test with invalid CRS
                    logToUser(
                        "Conversion from metric units to DEGREES not supported. It is advisable to set the project Spatial reference to Projected type before receiving CAD geometry (e.g. EPSG:32631), or create a custom one from geographic coordinates",
                        level=0,
                        func=inspect.stack()[0][3],
                        plugin=self.dockwidget,
                    )
            arcpy.AddMessage(f"Succesfully received {objId}")

            # If group exists, remove layers inside
            newGroupName = streamId + "_" + branch.name + "_" + commit.id
            newGroupName = removeSpecialCharacters(newGroupName)
            findAndClearLayerGroup(self.project, newGroupName, self)

            print("after create group")
            if app.lower() == "qgis" or app.lower() == "arcgis":
                check: Callable[[Base], bool] = lambda base: base.speckle_type and (
                    base.speckle_type.endswith("VectorLayer")
                    or base.speckle_type.endswith("Layer")
                    or base.speckle_type.endswith("RasterLayer")
                )
            else:
                check: Callable[[Base], bool] = lambda base: (
                    base.speckle_type and base.speckle_type.endswith("Base")
                )
            traverseObject(self, commitObj, callback, check, str(newGroupName), "")
            logToUser("👌 Data received", level=0, plugin=self.dockwidget, blue=True)
            return

        except SpeckleException as e:
            logToUser(
                "Receive failed: " + e.message,
                level=2,
                func=inspect.stack()[0][3],
                plugin=self.dockwidget,
            )
            return

    def reloadUI(self):

        from speckle.speckle.utils.project_vars import (
            get_project_streams,
            get_survey_point,
            get_project_layer_selection,
            get_project_saved_layers,
        )

        self.dataStorage = DataStorage()
        self.dataStorage.plugin_version = self.version

        self.is_setup = self.dataStorage.check_for_accounts()
        if self.dockwidget is not None:
            self.active_stream = None
            get_project_streams(self)
            get_survey_point(self)
            # get_project_saved_layers(self)
            # get_project_layer_selection(self)

            self.dockwidget.reloadDialogUI(self)
            get_project_saved_layers(self)
            self.dockwidget.populateSavedLayerDropdown(self, False)

    def run(self):
        """Run method that performs all the real work"""
        print("run plugin")
        try:
            from speckle.ui_widgets.main_window import SpeckleGISDialog
            from speckle.speckle.utils.project_vars import (
                get_project_streams,
                get_survey_point,
                get_rotation,
                get_crs_offsets,
                get_project_saved_layers,
            )

            # Create the dialog with elements (after translation) and keep reference
            # Only create GUI ONCE in callback, so that it will only load when the plugin is started

            self.dataStorage = DataStorage()
            self.dataStorage.plugin_version = self.version
            self.dataStorage.project = self.project

            self.is_setup = self.dataStorage.check_for_accounts()

            if self.pluginIsActive:
                self.reloadUI()
            else:
                print("Plugin inactive, launch")
                self.workspace = arcpy.env.workspace
                self.pluginIsActive = True
                print("run plugin 100")
                if self.dockwidget is None:
                    self.dockwidget = SpeckleGISDialog()

                    self.dockwidget.addDataStorage(self)
                    self.dockwidget.runSetup(self)

                    self.dockwidget.runButton.clicked.connect(self.onRunButtonClicked)
                    self.dockwidget.crsSettings.clicked.connect(
                        self.customCRSDialogCreate
                    )

                    self.dockwidget.signal_1.connect(addVectorMainThread)
                    self.dockwidget.signal_2.connect(addBimMainThread)
                    self.dockwidget.signal_3.connect(addCadMainThread)
                    self.dockwidget.signal_4.connect(addRasterMainThread)
                    self.dockwidget.signal_5.connect(addNonGeometryMainThread)
                    self.dockwidget.signal_6.connect(addExcelMainThread)
                    self.dockwidget.signal_remove_btn_url.connect(
                        self.dockwidget.msgLog.removeBtnUrl
                    )
                    self.dockwidget.signal_cancel_operation.connect(
                        self.dockwidget.cancelOperations
                    )
                else:
                    self.dockwidget.addDataStorage(self)

            get_project_streams(self)
            get_rotation(self)
            get_survey_point(self)
            get_crs_offsets(self)

            self.dockwidget.run(self)
            self.dockwidget.saveLayerSelection.clicked.connect(
                lambda: self.dockwidget.populateSavedLayerDropdown(self, True)
            )
            self.dockwidget.enableElements(self)

            # move to the end to display warning if needed
            get_project_saved_layers(self)
            self.dockwidget.populateSavedLayerDropdown(self, False)

        except Exception as e:
            logToUser(str(e), level=2, func=inspect.stack()[0][3])

    def onStreamAddButtonClicked(self):
        try:
            self.add_stream_modal = AddStreamModalDialog(None)
            self.add_stream_modal.dataStorage = self.dataStorage
            self.add_stream_modal.connect()
            self.add_stream_modal.handleStreamAdd.connect(self.handleStreamAdd)
            self.add_stream_modal.show()
        except Exception as e:
            logToUser(str(e), level=2, func=inspect.stack()[0][3])

    def onStreamCreateClicked(self):
        self.create_stream_modal = CreateStreamModalDialog(None)
        self.create_stream_modal.handleStreamCreate.connect(self.handleStreamCreate)
        # self.create_stream_modal.handleCancelStreamCreate.connect(lambda: self.dockwidget.populateProjectStreams(self))
        self.create_stream_modal.show()

    def handleStreamCreate(self, account, str_name, description, is_public):
        try:
            new_client = SpeckleClient(
                account.serverInfo.url, account.serverInfo.url.startswith("https")
            )
            try:
                new_client.authenticate_with_token(token=account.token)
            except SpeckleException as ex:
                if "already connected" in ex.message:
                    logToUser(
                        "Dependencies versioning error.\nClick here for details.",
                        url="dependencies_error",
                        level=2,
                        plugin=self.dockwidget,
                    )
                    return
                else:
                    raise ex

            str_id = new_client.stream.create(
                name=str_name, description=description, is_public=is_public
            )

            try:
                metrics.track(
                    "Connector Action",
                    self.dataStorage.active_account,
                    {
                        "name": "Stream Create",
                        "connector_version": str(self.dataStorage.plugin_version),
                    },
                )
            except Exception as e:
                logToUser(
                    e, level=2, func=inspect.stack()[0][3], plugin=self.dockwidget
                )

            if isinstance(str_id, GraphQLException) or isinstance(
                str_id, SpeckleException
            ):
                logToUser(str_id.message, level=2, plugin=self.dockwidget)
                return
            else:
                sw = StreamWrapper(account.serverInfo.url + "/streams/" + str_id)
                self.handleStreamAdd((sw, None, None))
            return
        except Exception as e:
            logToUser(e, level=2, func=inspect.stack()[0][3], plugin=self.dockwidget)
            return

    def onBranchCreateClicked(self):
        self.create_stream_modal = CreateBranchModalDialog(None)
        self.create_stream_modal.handleBranchCreate.connect(self.handleBranchCreate)
        self.create_stream_modal.show()

    def handleBranchCreate(self, br_name, description):
        # if len(br_name)<3:
        #    logger.logToUser("Branch Name should be at least 3 characters", Qgis.Warning)
        #    return
        try:
            br_name = br_name.lower()
            sw: StreamWrapper = self.active_stream[0]
            account = sw.get_account()
            new_client = SpeckleClient(
                account.serverInfo.url, account.serverInfo.url.startswith("https")
            )
            new_client.authenticate_with_token(token=account.token)
            # description = "No description provided"
            br_id = new_client.branch.create(
                stream_id=sw.stream_id, name=br_name, description=description
            )
            if isinstance(br_id, GraphQLException):
                logToUser(br_id.message, level=2, func=inspect.stack()[0][3])

            self.active_stream = (sw, tryGetStream(sw, self.dataStorage))
            self.current_streams[0] = self.active_stream

            self.dockwidget.populateActiveStreamBranchDropdown(self)
            self.dockwidget.populateActiveCommitDropdown(self)
            self.dockwidget.streamBranchDropdown.setCurrentText(
                br_name
            )  # will be ignored if branch name is not in the list

            return
        except Exception as e:
            logToUser(str(e), level=2, func=inspect.stack()[0][3])

    def handleStreamAdd(self, objectPacked: Tuple):
        try:
            from speckle.speckle.utils.project_vars import set_project_streams
        except:
            from speckle_toolbox.esri.toolboxes.speckle.speckle.utils.project_vars import (
                set_project_streams,
            )
        try:
            sw, branch, commit = objectPacked
            # print(sw)
            # print(branch)
            # print(commit)
            streamExists = 0
            index = 0

            self.dataStorage.check_for_accounts()
            stream = sw.get_client().stream.get(
                id=sw.stream_id, branch_limit=100, commit_limit=100
            )
            # stream = tryGetStream(sw, self.dataStorage, False, self.dockwidget)
            # print(stream)

            if stream is not None and branch in stream.branches.items:
                self.active_branch = branch
                self.active_commit = commit
            else:
                self.active_branch = None
                self.active_commit = None

            # try: print(f"ACTIVE BRANCH NAME: {self.active_branch.name}")
            # except: print("ACTIVE BRANCH IS NONE")
            for st in self.current_streams:
                # if isinstance(st[1], SpeckleException) or isinstance(stream, SpeckleException): pass
                if isinstance(stream, Stream) and st[0].stream_id == stream.id:
                    streamExists = 1
                    break
                index += 1
        except SpeckleException as e:
            logToUser(e, level=1, plugin=self.dockwidget)
            stream = None

        try:
            if streamExists == 0:
                self.current_streams.insert(0, (sw, stream))
            else:
                del self.current_streams[index]
                self.current_streams.insert(0, (sw, stream))
            try:
                self.add_stream_modal.handleStreamAdd.disconnect(self.handleStreamAdd)
            except:
                pass
            # set_project_streams(self)
            self.dockwidget.populateProjectStreams(self)
        except Exception as e:
            logToUser(e, level=2, func=inspect.stack()[0][3], plugin=self.dockwidget)
            return

    def customCRSDialogCreate(self):
        try:
            if self.dataStorage.project.activeMap is None:
                logToUser(
                    "Project Active Map not loaded or not selected",
                    level=1,
                    func=inspect.stack()[0][3],
                    plugin=self.dockwidget,
                )
                return 

            self.dataStorage.currentCRS = (
                self.dataStorage.project.activeMap.spatialReference
            )
            units = str(self.project.activeMap.spatialReference.linearUnitName)
            self.dataStorage.currentOriginalUnits = units

            if units is None or units == "degrees":
                units = "m"
            self.dataStorage.currentUnits = units

            self.dockwidget.custom_crs_modal = CustomCRSDialog(None)
            self.dockwidget.custom_crs_modal.dataStorage = self.dataStorage
            self.dockwidget.custom_crs_modal.populateModeDropdown()
            self.dockwidget.custom_crs_modal.populateSurveyPoint()
            self.dockwidget.custom_crs_modal.populateOffsets()
            self.dockwidget.custom_crs_modal.populateRotation()

            self.dockwidget.custom_crs_modal.dialog_button_box.button(
                QtWidgets.QDialogButtonBox.Apply
            ).clicked.connect(self.customCRSApply)
            crs_info_url = "https://speckle.guide/user/qgis.html#custom-project-center"
            self.dockwidget.custom_crs_modal.dialog_button_box.button(
                QtWidgets.QDialogButtonBox.Cancel
            ).clicked.connect(lambda: self.openUrl(crs_info_url))

            self.dockwidget.custom_crs_modal.show()

        except Exception as e:
            logToUser(e, level=2, func=inspect.stack()[0][3], plugin=self.dockwidget)
            return

    def openUrl(self, url: str = ""):
        import webbrowser

        # url = "https://speckle.guide/user/qgis.html#custom-project-center"
        try:
            if "/commits/" in url or "/models/" in url:
                metrics.track(
                    "Connector Action",
                    self.dataStorage.active_account,
                    {
                        "name": "Open In Web",
                        "connector_version": str(self.dataStorage.plugin_version),
                        "data": "Commit",
                    },
                )
            else:
                metrics.track(
                    "Connector Action",
                    self.dataStorage.active_account,
                    {
                        "name": "Open In Web",
                        "connector_version": str(self.dataStorage.plugin_version),
                    },
                )
        except Exception as e:
            logToUser(e, level=2, func=inspect.stack()[0][3])

        if url is not None and url != "":
            webbrowser.open(url, new=0, autoraise=True)

    def customCRSApply(self):
        index = self.dockwidget.custom_crs_modal.modeDropdown.currentIndex()
        if index == 1:  # add offsets
            self.customCRSCreate()
        if index == 0:  # create custom CRS
            self.crsOffsetsApply()
        self.applyRotation()
        self.dockwidget.custom_crs_modal.close()

    def applyRotation(self):
        try:
            from speckle.speckle.utils.project_vars import set_crs_offsets, set_rotation

            rotate = self.dockwidget.custom_crs_modal.rotation.text()
            if rotate is not None and rotate != "":
                try:
                    rotate = float(rotate)
                    if not -360 <= rotate <= 360:
                        logToUser(
                            "Angle value must be within the range (-360, 360)",
                            level=1,
                            plugin=self.dockwidget,
                        )
                    else:
                        # warning only if the value changed
                        if self.dataStorage.crs_rotation != float(rotate):
                            self.dataStorage.crs_rotation = float(rotate)
                            logToUser(
                                "Rotation successfully applied",
                                level=0,
                                plugin=self.dockwidget,
                            )

                            try:
                                metrics.track(
                                    "Connector Action",
                                    self.dataStorage.active_account,
                                    {
                                        "name": "CRS Rotation Add",
                                        "connector_version": str(
                                            self.dataStorage.plugin_version
                                        ),
                                    },
                                )
                            except Exception as e:
                                logToUser(e, level=2, func=inspect.stack()[0][3])

                except:
                    logToUser("Invalid Angle value", level=2, plugin=self.dockwidget)

            else:
                # warning only if the value changed
                if self.dataStorage.crs_rotation is not None:
                    self.dataStorage.crs_rotation = None
                    logToUser(
                        "Rotation successfully removed", level=0, plugin=self.dockwidget
                    )

                    try:
                        metrics.track(
                            "Connector Action",
                            self.dataStorage.active_account,
                            {
                                "name": "CRS Rotation Remove",
                                "connector_version": str(
                                    self.dataStorage.plugin_version
                                ),
                            },
                        )
                    except Exception as e:
                        logToUser(e, level=2, func=inspect.stack()[0][3])

            set_rotation(self)

        except Exception as e:
            logToUser(e, level=2, func=inspect.stack()[0][3], plugin=self.dockwidget)

    def crsOffsetsApply(self):
        try:
            from speckle.speckle.utils.project_vars import set_crs_offsets, set_rotation

            offX = self.dockwidget.custom_crs_modal.offsetX.text()
            offY = self.dockwidget.custom_crs_modal.offsetY.text()
            if offX is not None and offX != "" and offY is not None and offY != "":
                try:
                    # warning only if the value changed
                    if self.dataStorage.crs_offset_x != float(
                        offX
                    ) or self.dataStorage.crs_offset_y != float(offY):
                        self.dataStorage.crs_offset_x = float(offX)
                        self.dataStorage.crs_offset_y = float(offY)
                        logToUser(
                            "X and Y offsets successfully applied",
                            level=0,
                            plugin=self.dockwidget,
                        )

                        try:
                            metrics.track(
                                "Connector Action",
                                self.dataStorage.active_account,
                                {
                                    "name": "CRS Offset Add",
                                    "connector_version": str(
                                        self.dataStorage.plugin_version
                                    ),
                                },
                            )
                        except Exception as e:
                            logToUser(e, level=2, func=inspect.stack()[0][3])

                except:
                    logToUser("Invalid Offset values", level=2, plugin=self.dockwidget)

            else:
                # warning only if the value changed
                if (
                    self.dataStorage.crs_offset_x != None
                    or self.dataStorage.crs_offset_y != None
                ):
                    self.dataStorage.crs_offset_x = None
                    self.dataStorage.crs_offset_y = None
                    logToUser(
                        "X and Y offsets successfully removed",
                        level=0,
                        plugin=self.dockwidget,
                    )

                    try:
                        metrics.track(
                            "Connector Action",
                            self.dataStorage.active_account,
                            {
                                "name": "CRS Offset Remove",
                                "connector_version": str(
                                    self.dataStorage.plugin_version
                                ),
                            },
                        )
                    except Exception as e:
                        logToUser(e, level=2, func=inspect.stack()[0][3])

            set_crs_offsets(self)

        except Exception as e:
            logToUser(e, level=2, func=inspect.stack()[0][3], plugin=self.dockwidget)

    def customCRSCreate(self):
        try:
            from speckle.speckle.utils.project_vars import (
                set_survey_point,
                set_crs_offsets,
                setProjectReferenceSystem,
            )

            vals = [
                str(self.dockwidget.custom_crs_modal.surveyPointLat.text()),
                str(self.dockwidget.custom_crs_modal.surveyPointLon.text()),
            ]
            try:
                custom_lat, custom_lon = [float(i.replace(" ", "")) for i in vals]

                if (
                    custom_lat > 180
                    or custom_lat < -180
                    or custom_lon > 180
                    or custom_lon < -180
                ):
                    logToUser(
                        "LAT LON values must be within (-180, 180). You can right-click on the canvas location to copy coordinates in WGS 84",
                        level=1,
                        plugin=self.dockwidget,
                    )
                    return
                else:
                    self.dockwidget.dataStorage.custom_lat = custom_lat
                    self.dockwidget.dataStorage.custom_lon = custom_lon

                    set_survey_point(self)
                    setProjectReferenceSystem(self)

                    # remove offsets if custom crs applied
                    if (
                        self.dataStorage.crs_offset_x != None
                        and self.dataStorage.crs_offset_x != 0
                    ) or (
                        self.dataStorage.crs_offset_y != None
                        and self.dataStorage.crs_offset_y != 0
                    ):
                        self.dataStorage.crs_offset_x = None
                        self.dataStorage.crs_offset_y = None
                        self.dockwidget.custom_crs_modal.offsetX.setText("")
                        self.dockwidget.custom_crs_modal.offsetY.setText("")
                        set_crs_offsets(self)
                        logToUser(
                            "X and Y offsets removed", level=0, plugin=self.dockwidget
                        )

                    try:
                        metrics.track(
                            "Connector Action",
                            self.dataStorage.active_account,
                            {
                                "name": "CRS Custom Create",
                                "connector_version": str(
                                    self.dataStorage.plugin_version
                                ),
                            },
                        )
                    except Exception as e:
                        logToUser(e, level=2, func=inspect.stack()[0][3])

            except Exception as e:
                logToUser("Invalid Lat/Lon values", level=2, plugin=self.dockwidget)

        except Exception as e:
            logToUser(e, level=2, func=inspect.stack()[0][3], plugin=self.dockwidget)
            return
