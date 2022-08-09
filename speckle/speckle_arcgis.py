# -*- coding: utf-8 -*-

from collections import defaultdict
from typing import Any, Callable, List, Optional
from xmlrpc.client import Boolean
import arcpy
from arcpy._mp import ArcGISProject, Map, Layer as arcLayer

from specklepy.api.models import Branch, Stream, Streams
from speckle.converter.layers.Layer import Layer, RasterLayer

from speckle.converter.layers._init_ import convertSelectedLayers, layerToNative
from arcgis.features import FeatureLayer
import os.path

import specklepy
from specklepy.transports.server.server import ServerTransport
from specklepy.api.credentials import get_local_accounts
from specklepy.api.client import SpeckleClient
from specklepy.api import operations
from specklepy.logging.exceptions import (
    SpeckleException,
    SpeckleWarning,
)
from specklepy.api.credentials import StreamWrapper
from specklepy.objects import Base
from specklepy.api.wrapper import StreamWrapper

from speckle.converter.layers.emptyLayerTemplates import createGroupLayer

def traverseObject(
        base: Base,
        callback: Optional[Callable[[Base], bool]],
        check: Optional[Callable[[Base], bool]],
    ):
        if check and check(base):
            res = callback(base) if callback else False
            if res:
                return
        memberNames = base.get_member_names()
        for name in memberNames:
            try:
                if ["id", "applicationId", "units", "speckle_type"].index(name):
                    continue
            except:
                pass
            traverseValue(base[name], callback, check)
            
def traverseValue(
    value: Any,
    callback: Optional[Callable[[Base], bool]],
    check: Optional[Callable[[Base], bool]],
):
    if isinstance(value, Base):
        traverseObject(value, callback, check)
    if isinstance(value, List):
        for item in value:
            traverseValue(item, callback, check)


class Toolbox(object):
    def __init__(self):
        """Define the toolbox (the name of the toolbox is the name of the
        .pyt file)."""
        self.label = "Speckle Toolbox"
        self.alias = "speckle_toolbox"  
        # List of tool classes associated with this toolbox
        self.tools = [Speckle]    
        self.toolboxInputs = uiInputs() # initialize once together with a toolbox

        
        print(self.toolboxInputs.selected_layers)
        #try: 
        # https://pro.arcgis.com/en/pro-app/2.8/arcpy/mapping/alphabeticallistofclasses.htm#except: print("something happened")

class uiInputs(object):
    speckle_client: Any
    streams: Optional[Streams]
    active_stream: Optional[Stream]
    active_branch: Optional[Branch]
    all_layers: List[arcLayer]
    selected_layers: List[Any]
    messageSpeckle: str
    project: ArcGISProject
    action: int
    instances = []

    def __init__(self):
        print("start UI inputs________")
        self.instances.append(self)
        accounts = get_local_accounts()
        account = None
        for acc in accounts:
            if acc.isDefault: account = acc; break
        #account.userInfo.name, account.serverInfo.url
        self.speckle_client = SpeckleClient(account.serverInfo.url, account.serverInfo.url.startswith("https"))
        self.speckle_client.authenticate(token=account.token)

        self.streams = self.speckle_client.stream.search("")
        self.active_stream = None
        self.active_branch = None
        self.all_layers = []
        self.selected_layers = []
        self.messageSpeckle = ""
        self.project = aprx = None
        self.action = 1 #send

        try: aprx = ArcGISProject('CURRENT') 
        except: 
            print(arcpy.env.workspace) # None
            #arcpy.env.workspace = ""
            #proj_path = "\\".join(arcpy.env.workspace.split("\\")[:-1]) + "\\"
            #aprx = ArcGISProject(proj_path)
            #print(aprx)
            print("Project not found")
        self.project = aprx
        active_map = aprx.activeMap

        if active_map is not None and isinstance(active_map, Map): # if project loaded
            for layer in active_map.listLayers(): 
                print(layer)
                if layer.isFeatureLayer: self.all_layers.append(layer) #type: 'arcpy._mp.Layer'
        

class Speckle(object):
    def __init__(self):
        print("resetting script tool_____")   
        self.label       = "Speckle"
        self.description = "Allows you to send and receive your layers " + \
                           "to/from other software using Speckle server." 
        self.toolboxInputs = None

        for instance in uiInputs.instances:
            if instance is not None: self.toolboxInputs = instance
        if self.toolboxInputs is None: self.toolboxInputs = uiInputs() #in case Toolbox class was not initialized 
        # TODO react on project changes

    def getParameterInfo(self):
        #data types: https://pro.arcgis.com/en/pro-app/2.8/arcpy/geoprocessing_and_python/defining-parameter-data-types-in-a-python-toolbox.htm
        # parameter details: https://pro.arcgis.com/en/pro-app/latest/arcpy/geoprocessing_and_python/customizing-tool-behavior-in-a-python-toolbox.htm
        print("Get parameter values")

        stream = arcpy.Parameter(
            displayName="Stream",
            name="stream",
            datatype="GPString",
            parameterType="Required",
            #category="Sending data",
            direction="Input")
        stream.filter.type = 'ValueList'
        stream.filter.list = [ (st.name + " | " + st.id) for st in self.toolboxInputs.streams ]
        
        branch = arcpy.Parameter(
            displayName="Branch",
            name="branch",
            datatype="GPString",
            parameterType="Required",
            #category="Sending data",
            direction="Input")
        branch.value = "main"
        branch.filter.type = 'ValueList'

        ################################################################
        msg = arcpy.Parameter(
            displayName="Message",
            name="message",
            datatype="GPString",
            parameterType="Optional",
            direction="Input",
            multiValue=False)
        msg.value = ""

        selected_layers = arcpy.Parameter(
            displayName="Selected Layers",
            name="selected_layers",
            datatype="GPString",
            parameterType="Optional",
            direction="Input",
            multiValue=True
            )
        selected_layers.filter.list = [str(i) + "-" + l.longName for i,l in enumerate(self.toolboxInputs.all_layers)] #"Polyline"

        
        
        refresh = arcpy.Parameter(
            displayName="Refresh",
            name="refresh",
            datatype="GPBoolean",
            parameterType="Optional",
            #category="Sending data",
            direction="Input"
            )
        #refresh.filter.type = "ValueList"   
        refresh.value = False 
        

        action = arcpy.Parameter(
            displayName="",
            name="action",
            datatype="GPString",
            parameterType="Required",
            #category="Sending data",
            direction="Input",
            multiValue=False
            )
        action.value = "Send" 
        #action.filter.type = 'ValueList'
        action.filter.list = ["Send", "Receive"]  

        parameters = [stream, branch, selected_layers, msg, action, refresh]
        return parameters

    def isLicensed(self): #optional
        return True

    def updateParameters(self, parameters: List): #optional
        if parameters[0].altered:
            parameters[1].value = "main"

            # Search for the stream by name
            if parameters[0].valueAsText is not None:
                selected_stream_name = parameters[0].valueAsText[:]
                self.toolboxInputs.active_stream = None
                for st in self.toolboxInputs.streams:
                    if st.name == selected_stream_name.split(" | ")[0]: 
                        self.toolboxInputs.active_stream = st
                        break

                parameters[1].filter.list = [branch.name for branch in self.toolboxInputs.active_stream.branches.items]
                
                #if self.active_stream is None: 
                #    print("Choose a valid stream")
                #    arcpy.AddMessage("Choose a valid stream")
                #    return

        if parameters[1].altered:
            # Search for the stream by name
            if parameters[1].valueAsText is not None:
                selected_branch_name = parameters[1].valueAsText[:]
                self.toolboxInputs.active_branch = None
                if self.toolboxInputs.active_stream is not None:
                    for br in self.toolboxInputs.active_stream.branches.items:
                        if br.name == selected_branch_name: #.split(" | ")[0]: 
                            self.toolboxInputs.active_branch = br
                            break
        
        if parameters[2].altered: # selected layers
            if parameters[2].valueAsText is not None:
                self.toolboxInputs.selected_layers = parameters[2].values

        if parameters[3].altered:
            self.toolboxInputs.messageSpeckle = parameters[3].valueAsText


        if parameters[4].altered:
            if parameters[4].valueAsText == "Send": self.toolboxInputs.action = 1
            else: self.toolboxInputs.action = 0

        if parameters[5].altered: # refresh btn
            print("Refresh")
            if parameters[5].value == True:
                uiInputs()
                self.__init__()
                #self.streams = self.speckle_client.stream.search("")
                params_new = []
                for i,p in enumerate(parameters):
                    params_new.append(p)
                    if i==1: params_new[i].value = "main"
                    elif i ==3: params_new[i].value = ""
                    elif i ==4: params_new[i].value = "Send"
                    elif i ==5: params_new[i].value = False
                    else: params_new[i].value = None
                
                params_new[0].filter.list = [ (st.name + " | " + st.id) for st in self.toolboxInputs.streams ]
                params_new[2].filter.list = [str(i) + "-" + l.longName for i,l in enumerate(self.toolboxInputs.all_layers)]
                
                self.updateParameters(params_new)
                  
        return 

    def updateMessages(self, parameters): #optional
        return

    def execute(self, parameters: List, messages): 
        # https://pro.arcgis.com/en/pro-app/latest/arcpy/get-started/what-is-arcpy-.htm
        #Warning if any of the fields is invalid/empty 
        print("_______________________Run__________________________")
        print(self.toolboxInputs.action)
        if self.toolboxInputs.action == 1: self.onSend(parameters)
        elif self.toolboxInputs.action == 0: self.onReceive(parameters)

    def validateStreamBranch(self, parameters: List):
        	
        self.updateParameters(parameters)
        if self.toolboxInputs.active_stream is None:
            arcpy.AddError("Choose a valid stream")
            return False
        if self.toolboxInputs.active_branch is None: 
            arcpy.AddError("Choose a valid branch")
            return False
        return True 

    def onSend(self, parameters: List):

        if self.validateStreamBranch(parameters) == False: return

        if len(self.toolboxInputs.selected_layers) == 0: 
            arcpy.AddError("No layers selected")
            return

        streamId = self.toolboxInputs.active_stream.id #stream_id
        client = self.toolboxInputs.speckle_client # ?
        
        # Get the stream wrapper
        #streamWrapper = StreamWrapper(None)
        #client = streamWrapper.get_client()
        # Ensure the stream actually exists
        #try:
        #    client.stream.get(streamId)
        #except SpeckleException as error:
        #    print(str(error))
        #    return

        # next create a server transport - this is the vehicle through which you will send and receive
        transport = ServerTransport(client=client, stream_id=streamId)

        ##################################### conversions ################################################
        base_obj = Base()
        base_obj.layers = convertSelectedLayers(self.toolboxInputs.all_layers, self.toolboxInputs.selected_layers, self.toolboxInputs.project)
        
        try:
            # this serialises the block and sends it to the transport
            objId = operations.send(base=base_obj, transports=[transport])
        except SpeckleException as error:
            arcpy.AddError("Error sending data")
            print("Error sending data")
            return
        except SpeckleWarning as warning:
            arcpy.AddMessage("SpeckleWarning: " + str(warning.args[0]))
            

        message = self.toolboxInputs.messageSpeckle
        if message is None or ( isinstance(message, str) and len(message) == 0):  message = "Sent from ArcGIS"
        try:
            # you can now create a commit on your stream with this object
            client.commit.create(
                stream_id=streamId,
                object_id=objId,
                branch_name=self.toolboxInputs.active_branch.name,
                message=message,
                source_application="ArcGIS",
            )
            arcpy.AddMessage("Successfully sent data to stream: " + streamId)
            print("Successfully sent data to stream: " + streamId)
            #parameters[2].value = ""
        except:
            arcpy.AddError("Error creating commit")

    def onReceive(self, parameters: List): 
        
        if self.validateStreamBranch(parameters) == False: return

        try: 
            streamId = self.toolboxInputs.active_stream.id #stream_id
            client = self.toolboxInputs.speckle_client # 
        except SpeckleWarning as warning: 
            arcpy.AddWarning(str(warning.args[0]))

        # get last commit 
        try: 
            commit = self.toolboxInputs.active_branch.commits.items[0]
        except: 
            arcpy.AddError("Failed to find a commit")
            return

        # next create a server transport - this is the vehicle through which you will send and receive
        try: transport = ServerTransport(client=client, stream_id=streamId)
        except: 
            arcpy.AddError("Make sure your account has access to the chosen stream")
            return

        try:
            objId = commit.referencedObject
            commitDetailed = client.commit.get(streamId, commit.id)
            app = commitDetailed.sourceApplication
            if objId is None:
                return
            commitObj = operations.receive(objId, transport, None)
            
            if app != "QGIS" and app != "ArcGIS": 
                if self.toolboxInputs.project.activeMap.spatialReference.type == "Geographic" or self.toolboxInputs.project.activeMap.spatialReference is None: #TODO test with invalid CRS
                    arcpy.AddMessage("It is advisable to set the project Spatial reference to Projected type before receiving CAD geometry (e.g. EPSG:32631), or create a custom one from geographic coordinates")
                    print("It is advisable to set the project Spatial reference to Projected type before receiving CAD geometry (e.g. EPSG:32631), or create a custom one from geographic coordinates")
            print(f"Succesfully received {objId}")

            # Clear 'latest' group
            streamBranch = streamId + "_" + self.toolboxInputs.active_branch.name + "_" + str(commit.id)
            newGroupName = f'{streamBranch}'
            
            groupExists = 0
            for l in self.toolboxInputs.project.activeMap.listLayers(): 
                if l.longName.startswith(newGroupName + "\\"):
                    print(l.longName)
                    self.toolboxInputs.project.activeMap.removeLayer(l)
                    groupExists+=1
            if groupExists == 0:
                # create empty group layer file 
                path = "\\".join(self.toolboxInputs.project.filePath.split("\\")[:-1]) + "\\speckle_layers\\"
                #path = "\\".join(project.filePath.split("\\")[:-1]) + "\\speckle_layers\\" #arcpy.env.workspace + "\\" #
                if not os.path.exists(path): os.makedirs(path)
                f = open(path + newGroupName + ".lyrx", "w")
                content = createGroupLayer().replace("TestGroupLayer", newGroupName)
                f.write(content)
                f.close()
                smth = arcpy.mp.LayerFile(path + newGroupName + ".lyrx")
                print(smth)
                layerGroup = self.toolboxInputs.project.activeMap.addLayer(smth)[0]
                layerGroup.name = newGroupName

            if app == "QGIS" or app == "ArcGIS": check: Callable[[Base], bool] = lambda base: isinstance(base, Layer) or isinstance(base, RasterLayer)
            else: check: Callable[[Base], bool] = lambda base: isinstance(base, Base)

            def callback(base: Base) -> bool:
                print("callback")
                print(base)
                if isinstance(base, Layer) or isinstance(base, RasterLayer):
                    layer = layerToNative(base, streamBranch, self.toolboxInputs.project)
                    if layer is not None:
                        print("Layer created: " + layer.name)
                #else:
                #    loopObj(base, "")
                return True
            '''
            def loopObj(base: Base, baseName: str):
                memberNames = base.get_member_names()
                for name in memberNames:
                    if name in ["id", "applicationId", "units", "speckle_type"]: continue
                    try: loopVal(base[name], baseName + "/" + name)
                    except: pass

            def loopVal(value: Any, name: str): # "name" is the parent object/property/layer name
                if isinstance(value, Base): 
                    try: # dont go through parts of Speckle Geometry object
                        if value.speckle_type.startswith("Objects.Geometry."): pass #.Brep") or value.speckle_type.startswith("Objects.Geometry.Mesh") or value.speckle_type.startswith("Objects.Geometry.Surface") or value.speckle_type.startswith("Objects.Geometry.Extrusion"): pass
                        else: loopObj(value, name)
                    except: loopObj(value, name)

                if isinstance(value, List):
                    for item in value:
                        loopVal(item, name)
                        if item.speckle_type and item.speckle_type.startswith("Objects.Geometry."): 
                            pt, pl = cadLayerToNative(value, name, streamBranch)
                            if pt is not None: print("Layer group created: " + pt.name())
                            if pl is not None: print("Layer group created: " + pl.name())
                            break
                '''
            traverseObject(commitObj, callback, check)
                
        except SpeckleException as e:
            print("Receive failed")
            return
    