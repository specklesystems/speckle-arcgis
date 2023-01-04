
# -*- coding: utf-8 -*-

from typing import Any, Callable, List, Optional, Tuple
#r'''
from collections import defaultdict

import arcpy
#from arcpy import toolbox
from arcpy._mp import ArcGISProject, Map, Layer as arcLayer
from arcpy import metadata as md

from specklepy.api.models import Branch, Stream, Streams
try:
    from speckle.converter.layers.Layer import Layer, RasterLayer
    from speckle.converter.layers._init_ import convertSelectedLayers, layerToNative, cadLayerToNative, bimLayerToNative
    from speckle.ui.project_vars import toolboxInputsClass, speckleInputsClass
    from speckle.converter.layers.emptyLayerTemplates import createGroupLayer
    from speckle.converter.layers.Layer import VectorLayer
except: 
    from speckle_toolbox.esri.toolboxes.speckle.converter.layers.Layer import Layer, RasterLayer
    from speckle_toolbox.esri.toolboxes.speckle.converter.layers._init_ import convertSelectedLayers, layerToNative, cadLayerToNative, bimLayerToNative
    from speckle_toolbox.esri.toolboxes.speckle.ui.project_vars import toolboxInputsClass, speckleInputsClass
    from speckle_toolbox.esri.toolboxes.speckle.converter.layers.emptyLayerTemplates import createGroupLayer
    from speckle_toolbox.esri.toolboxes.speckle.converter.layers.Layer import VectorLayer
    
from arcgis.features import FeatureLayer
import os
import os.path

import specklepy
from specklepy.transports.server.server import ServerTransport
from specklepy.api.credentials import get_local_accounts
from specklepy.api.client import SpeckleClient
from specklepy.api import operations
from specklepy.logging.exceptions import (
    GraphQLException,
    SpeckleException,
    SpeckleWarning,
)
#from specklepy.api.credentials import StreamWrapper
from specklepy.api.wrapper import StreamWrapper
from specklepy.objects import Base
from specklepy.logging import metrics

#'''

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


class Toolbox:
    def __init__(self):
        """Define the toolbox (the name of the toolbox is the name of the
        .pyt file)."""
        print("___ping_Toolbox")
        self.label = "Speckle Tools"
        self.alias = "speckle_toolbox_"  
        # List of tool classes associated with this toolbox
        self.tools = [Speckle]  
        metrics.set_host_app("ArcGIS")  

        # https://pro.arcgis.com/en/pro-app/2.8/arcpy/mapping/alphabeticallistofclasses.htm#except: print("something happened")

class Speckle:
    def __init__(self):
        #print("________________reset_______________")   
        self.label       = "Speckle"
        self.description = "Allows you to send and receive your layers " + \
                           "to/from other software using Speckle server." 

        self.toRefresh = False
        self.speckleInputs = None
        self.toolboxInputs = None
        #print("ping_Speckle1")
        
        #print(speckleInputsClass.instances)
        total = len(speckleInputsClass.instances)
        #print(total)
        for i in range(total):
            #print(i)
            #print(speckleInputsClass.instances[total-i-1])
            if speckleInputsClass.instances[total-i-1] is not None: 
                try: 
                    #print(speckleInputsClass.instances[total-i-1].streams_default)
                    y = speckleInputsClass.instances[total-i-1].streams_default # in case not initialized properly 
                    self.speckleInputs = speckleInputsClass.instances[total-i-1] # take latest (first in reverted list)
                    #print("FOUND INSTANCE")
                    break
                except: pass
        #print(self.speckleInputs)
        if self.speckleInputs is None: self.speckleInputs = speckleInputsClass()


        #print(toolboxInputsClass.instances)
        #print("TOTAL = ...................") 
        total = len(toolboxInputsClass.instances)
        #print(total)
        for i in range(total):
            if toolboxInputsClass.instances[total-i-1] is not None: 
                self.toolboxInputs = toolboxInputsClass.instances[total-i-1] # take latest (first in reverted list)
                #print("FOUND INSTANCE")
                break
        #print(self.toolboxInputs)
        if self.toolboxInputs is None: self.toolboxInputs = toolboxInputsClass()
        
        #print("ping_Speckle2")

    def getParameterInfo(self):
        #data types: https://pro.arcgis.com/en/pro-app/2.8/arcpy/geoprocessing_and_python/defining-parameter-data-types-in-a-python-toolbox.htm
        # parameter details: https://pro.arcgis.com/en/pro-app/latest/arcpy/geoprocessing_and_python/customizing-tool-behavior-in-a-python-toolbox.htm
        print("Get parameter values")
        cat1 = "Add Streams"
        cat2 = "Send/Receive"
        cat3 = "Create custom Spatial Reference"

        streamsDefalut = arcpy.Parameter(
            displayName="Add stream from default account",
            name="streamsDefalut",
            datatype="GPString",
            parameterType="Optional",
            #category="Sending data",
            direction="Input",
            category=cat1
            )
        streamsDefalut.filter.type = 'ValueList'
        streamsDefalut.filter.list = [ (st.name + " - " + st.id) for st in self.speckleInputs.streams_default ]

        addDefStreams = arcpy.Parameter(
            displayName="Add",
            name="addDefStreams",
            datatype="GPBoolean",
            parameterType="Optional",
            #category="Sending data",
            direction="Input",
            category=cat1
            )
        addDefStreams.value = False 

        streamUrl = arcpy.Parameter(
            displayName="Add stream by URL",
            name="streamUrl",
            datatype="GPString",
            parameterType="Optional",
            direction="Input",
            category=cat1
            )
        streamUrl.value = ""

        addUrlStreams = arcpy.Parameter(
            displayName="Add",
            name="addUrlStreams",
            datatype="GPBoolean",
            parameterType="Optional",
            direction="Input",
            category=cat1
            )
        addUrlStreams.value = False 

        ############################################################################
        
        lat = arcpy.Parameter(
            displayName="Origin point LAT",
            name="lat",
            datatype="GPString",
            parameterType="Optional",
            direction="Input",
            category=cat3
            )
        lat.value = str(self.toolboxInputs.lat)

        lon = arcpy.Parameter(
            displayName="Origin point LON",
            name="lon",
            datatype="GPString",
            parameterType="Optional",
            direction="Input",
            category=cat3
            )
        lon.value = str(self.toolboxInputs.lon)
        
        setLatLon = arcpy.Parameter(
            displayName="Create and apply",
            name="setLatLon",
            datatype="GPBoolean",
            parameterType="Optional",
            direction="Input",
            category=cat3
            )
        setLatLon.value = False
        
        ####################################################################################################

        savedStreams = arcpy.Parameter(
            displayName="Select Stream",
            name="savedStreams",
            datatype="GPString",
            parameterType="Required",
            direction="Input",
            multiValue=False,
            #category=cat2
            )
        savedStreams.filter.list = [f"Stream not accessible - {stream[0].stream_id}" if stream[1] is None or isinstance(stream[1], SpeckleException) else f"{stream[1].name} - {stream[1].id}" for i,stream in enumerate(self.speckleInputs.saved_streams)] 

        removeStream = arcpy.Parameter(
            displayName="Remove",
            name="removeStream",
            datatype="GPBoolean",
            parameterType="Optional",
            direction="Input"
            )
        removeStream.value = False 

        branch = arcpy.Parameter(
            displayName="Branch",
            name="branch",
            datatype="GPString",
            parameterType="Required",
            #category="Sending data",
            direction="Input",
            #category=cat2
            )
        branch.value = ""
        branch.filter.type = 'ValueList'

        commit = arcpy.Parameter(
            displayName="Commit",
            name="commit",
            datatype="GPString",
            parameterType="Optional",
            #category="Sending data",
            direction="Input",
            #category=cat2
            )
        commit.value = ""
        commit.filter.type = 'ValueList'

        msg = arcpy.Parameter(
            displayName="Message",
            name="msg",
            datatype="GPString",
            parameterType="Optional",
            direction="Input",
            multiValue=False,
            #category=cat2
            )
        msg.value = ""

        selectedLayers = arcpy.Parameter(
            displayName="Selected Layers",
            name="selectedLayers",
            datatype="GPString",
            parameterType="Optional",
            direction="Input",
            multiValue=True,
            #category=cat2
            )
        selectedLayers.filter.list = [str(i) + "-" + l.longName for i,l in enumerate(self.speckleInputs.all_layers)] #"Polyline"

        
        action = arcpy.Parameter(
            displayName="",
            name="action",
            datatype="GPString",
            parameterType="Required",
            #category="Sending data",
            direction="Input",
            multiValue=False,
            #category=cat2
            )
        action.value = "Send" 
        #action.filter.type = 'ValueList'
        action.filter.list = ["Send", "Receive"]  

        refresh = arcpy.Parameter(
            displayName="Refresh",
            name="refresh",
            datatype="GPBoolean",
            parameterType="Optional",
            direction="Input"
            )
        #refresh.filter.type = "ValueList"   
        refresh.value = False 

        parameters = [streamsDefalut, addDefStreams, streamUrl, addUrlStreams, lat, lon, setLatLon, savedStreams, removeStream, branch, commit, selectedLayers, msg, action, refresh]
        return parameters

    def isLicensed(self): #optional
        return True

    def updateParameters(self, parameters: List, toRefresh = False): #optional
        print("UPDATING PARAMETERS")
        
        for i, par in enumerate(parameters): 
            

            if par.name == "addDefStreams" and par.altered and par.value == True: 
                for p in parameters:
                    if p.name == "streamsDefalut" and p.valueAsText is not None:
                        # add value from streamsDefault to saved streams
                        selected_stream_name = p.valueAsText[:]
                        #print(selected_stream_name)
                        for stream in self.speckleInputs.streams_default:
                            #print(stream)
                            if stream.name == selected_stream_name.split(" - ")[0]:
                                print("_____Add from list___")
                                wr = StreamWrapper(f"{self.speckleInputs.account.serverInfo.url}/streams/{stream.id}?u={self.speckleInputs.account.userInfo.id}")
                                self.toolboxInputs.setProjectStreams(wr)
                                
                                for p_saved in parameters:
                                    if p_saved.name == "savedStreams": 
                                        saved_streams = self.speckleInputs.getProjectStreams()
                                        self.speckleInputs.saved_streams = saved_streams
                                        p_saved.filter.list = [f"Stream not accessible - {stream[0].stream_id}" if stream[1] is None or isinstance(stream[1], SpeckleException) else f"{stream[1].name} - {stream[1].id}" for i,stream in enumerate(saved_streams)] 
                                        if len(p_saved.filter.list)>0: print(p_saved.filter.list); p_saved.value = p_saved.filter.list[0]
                                break
                        p.value = None
                par.value = False
            
            if par.name == "addUrlStreams" and par.altered and par.value == True: 
                for p in parameters:
                    if p.name == "streamUrl" and p.valueAsText is not None:

                        # add value from streamsDefault to saved streams
                        query = p.valueAsText[:]
                        if "http" in query and len(query.split("/")) >= 3: # URL
                            steamId = query
                            try: steamId = query.split("/streams/")[1].split("/")[0] 
                            except: pass
                            # quesry stream, add to saved
                            stream = self.speckleInputs.speckle_client.stream.get(steamId)
                            if isinstance(stream, Stream): 
                                print("_____Add by URL___")
                                wr = StreamWrapper(f"{self.speckleInputs.account.serverInfo.url}/streams/{stream.id}?u={self.speckleInputs.account.userInfo.id}")
                                self.toolboxInputs.setProjectStreams(wr)
                                
                                for p_saved in parameters:
                                    if p_saved.name == "savedStreams": 
                                        saved_streams = self.speckleInputs.getProjectStreams()
                                        self.speckleInputs.saved_streams = saved_streams
                                        p_saved.filter.list = [f"Stream not accessible - {st[0].stream_id}" if st[1] is None or isinstance(st[1], SpeckleException) else f"{st[1].name} - {st[1].id}" for i,st in enumerate(saved_streams)] 
                                        if len(p_saved.filter.list)>0: print(p_saved.filter.list); p_saved.value = p_saved.filter.list[0]
                            else: pass

                        p.value = None
                        break
                par.value = False


            if par.name == "removeStream" and par.altered and par.value == True: 
                for p in parameters:
                    if p.name == "savedStreams" and p.valueAsText is not None:

                         # get value from savedStreams 
                        selected_stream_name = p.valueAsText[:]
                        #print(selected_stream_name)
                        for streamTup in self.speckleInputs.saved_streams:
                            #print(stream)
                            stream = streamTup[1]
                            if stream.name == selected_stream_name.split(" - ")[0]:
                                print("_____Remove stream___")
                                wr = StreamWrapper(f"{self.speckleInputs.account.serverInfo.url}/streams/{stream.id}?u={self.speckleInputs.account.userInfo.id}")
                                self.toolboxInputs.setProjectStreams(wr, False)
                                
                                for p_saved in parameters:
                                    if p_saved.name == "savedStreams": 
                                        saved_streams = self.speckleInputs.getProjectStreams()
                                        self.speckleInputs.saved_streams = saved_streams
                                        p_saved.filter.list = [f"Stream not accessible - {st[0].stream_id}" if st[1] is None or isinstance(st[1], SpeckleException) else f"{st[1].name} - {st[1].id}" for i,st in enumerate(saved_streams)] 
                                        p_saved.value = None
                                break
                        p.value = None
                par.value = False

            ####################################################################### 
            if par.name == "setLatLon" and par.altered and par.value == True: 
                lat = lon = 0
                for p in parameters:
                    if p.name == "lat" and p.valueAsText is not None:
                        # add value from the UI to saved lat
                        lat = p.valueAsText[:].replace(",","").replace(" ","").replace(";","").replace("_","")
                        try: lat = float(lat)
                        except: lat = 0; p.value = "0.0"
                    if p.name == "lon" and p.valueAsText is not None:
                        # add value from the UI to saved lat
                        lon = p.valueAsText[:].replace(",","").replace(" ","").replace(";","").replace("_","")
                        try: lon = float(lon)
                        except: lon = 0; p.value = "0.0"
                    coords = [lat, lon]
                    self.toolboxInputs.set_survey_point(coords)
                par.value = False
            
            ####################################################################### 

            if par.name == "savedStreams" and par.altered:
                # Search for the stream by name
                if par.value is not None and "Stream not accessible" not in par.valueAsText[:]:
                    #print("SAVED STREAMS - selection")
                    selected_stream_name = par.valueAsText[:]
                    self.toolboxInputs.active_stream = None
                    for st in self.speckleInputs.saved_streams:
                        if st[1].name == selected_stream_name.split(" - ")[0]: 
                            self.toolboxInputs.active_stream = st[1]
                            break

                    # edit branches: globals and UI 
                    branch_list = [branch.name for branch in self.toolboxInputs.active_stream.branches.items]
                    for p in parameters:
                        if p.name == "branch":
                            p.filter.list = branch_list

                            if p.valueAsText not in branch_list: 
                                p.value = "main"
                            for b in self.toolboxInputs.active_stream.branches.items:
                                if b.name == p.value: 
                                    self.toolboxInputs.active_branch = b
                                    break 
                    
                    # setting commit value and list 
                    for p in parameters:
                        if p.name == "commit":
                            try: 
                                p.filter.list = [f"{commit.id}"+ " - " + f"{commit.message}" for commit in self.toolboxInputs.active_branch.commits.items]
                                if p.valueAsText not in p.filter.list:
                                    p.value = self.toolboxInputs.active_branch.commits.items[0].id + " - " + self.toolboxInputs.active_branch.commits.items[0].message 
                                    self.toolboxInputs.active_commit = self.toolboxInputs.active_branch.commits.items[0] 
                            except: 
                                p.filter.list = []
                                p.value = None
                                self.toolboxInputs.active_commit = None 
                else: par.value = None
                #print(self.toolboxInputs.action)

            if par.name == "branch" and par.altered: # branches
                if par.value is not None:
                    selected_branch_name = par.valueAsText[:]
                    self.toolboxInputs.active_branch = None
                    if self.toolboxInputs.active_stream is not None:
                        for br in self.toolboxInputs.active_stream.branches.items:
                            if br.name == selected_branch_name:
                                self.toolboxInputs.active_branch = br
                                break
                # edit commit values 
                if self.toolboxInputs.active_branch is not None: 
                    for p in parameters:
                        if p.name == "commit":
                            try: 
                                p.filter.list = [f"{commit.id}"+ " - " + f"{commit.message}" for commit in self.toolboxInputs.active_branch.commits.items]
                                if p.valueAsText not in p.filter.list:
                                    p.value = self.toolboxInputs.active_branch.commits.items[0].id + " - " + self.toolboxInputs.active_branch.commits.items[0].message 
                                    self.toolboxInputs.active_commit = self.toolboxInputs.active_branch.commits.items[0]
                            except: 
                                p.filter.list = []
                                p.value = None
                                self.toolboxInputs.active_commit = None 

            if par.name == "commit" and par.altered: # commits
                if par.value is not None:
                    selected_commit_id = par.valueAsText[:].split(" - ")[0]
                    self.toolboxInputs.active_commit = None
                    if self.toolboxInputs.active_branch is not None:
                        for c in self.toolboxInputs.active_branch.commits.items:
                            if c.id == selected_commit_id: 
                                self.toolboxInputs.active_commit = c 
                                break
            
            if par.name == "selectedLayers" and par.altered: # selected layers
                if par.value is not None:
                    self.toolboxInputs.selected_layers = par.values

                    #print("selected layers changed")
                    #print(self.toolboxInputs.action)
                    #print(self.toolboxInputs.selected_layers)

            if par.name == "msg" and par.altered and par.valueAsText is not None:
                self.toolboxInputs.messageSpeckle = par.valueAsText
                print(self.toolboxInputs.messageSpeckle)

            if par.name == "action" and par.altered:
                #print("action changed")
                #print(par.valueAsText)
                if par.valueAsText == "Send": self.toolboxInputs.action = 1
                else: self.toolboxInputs.action = 0

                #print(self.toolboxInputs.action)
                #print(self.toolboxInputs.selected_layers)

            if par.name == "refresh" and par.altered: # refresh btn
                if par.value == True: 
                    self.refresh(parameters) 
            if self.toRefresh == True:
                self.refresh(parameters) 
                self.toRefresh = False
        
        print("____________________________parameters___________________________")
        #[print(str(x.name) + " - " + str(x.valueAsText)) for x in parameters]
        #[x.clearMessage() for x in parameters] # https://pro.arcgis.com/en/pro-app/latest/arcpy/geoprocessing_and_python/programming-a-toolvalidator-class.htm
        #[print(x.valueAsText) for x in parameters]
        return 
    
    def refresh(self, parameters: List[Any]): 
        print("Refresh______")
        self.speckleInputs: speckleInputsClass = speckleInputsClass()
        self.toolboxInputs: toolboxInputsClass = toolboxInputsClass()
        
        for par in parameters: 
            if par.name == "streamUrl": par.value = None
            if par.name == "streamsDefalut": par.value = None
            if par.name == "savedStreams": par.value = None
            if par.name == "branch": par.value = ""; par.filter.list = []
            if par.name == "commit": par.value = None; par.filter.list = []
            if par.name == "selectedLayers": par.value = None
            if par.name == "msg": par.value = ""
            if par.name == "action": par.value = "Send"
            if par.name == "refresh": par.value = False
            
            if par.name == "lat": par.value = str(self.toolboxInputs.get_survey_point()[0])
            if par.name == "lon": par.value = str(self.toolboxInputs.get_survey_point()[1])
            if par.name == "streamsDefalut": par.filter.list = [ (st.name + " - " + st.id) for st in self.speckleInputs.streams_default ]
            if par.name == "savedStreams": 
                #print("par.name")
                saved_streams = self.speckleInputs.getProjectStreams()
                #print(saved_streams)
                par.filter.list = [f"Stream not accessible - {stream[0].stream_id}" if stream[1] is None or isinstance(stream[1], SpeckleException) else f"{stream[1].name} - {stream[1].id}" for i,stream in enumerate(saved_streams)] 
            if par.name == "selectedLayers": par.filter.list = [str(i) + "-" + l.longName for i,l in enumerate(self.speckleInputs.all_layers)]
        
        return parameters

    def updateMessages(self, parameters): #optional
        return

    def execute(self, parameters: List, messages): 
        # https://pro.arcgis.com/en/pro-app/latest/arcpy/get-started/what-is-arcpy-.htm
        #Warning if any of the fields is invalid/empty 
        print("___________________________Run___________________________")
        check = self.validateStreamBranch(parameters) # apparently pdate needed to assign proper self.values
        
        print(self.toolboxInputs.selected_layers)
        print(self.toolboxInputs.action)
        
        if self.toolboxInputs.action == 1 and check is True: self.onSend(parameters)
        elif self.toolboxInputs.action == 0 and check is True: self.onReceive(parameters)
        print("__________________________Run_end___________________________")

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

        print("______________SEND_______________")

        #if self.validateStreamBranch(parameters) == False: return

        if len(self.toolboxInputs.selected_layers) == 0: 
            arcpy.AddError("No layers selected for sending")
            return

        streamId = self.toolboxInputs.active_stream.id #stream_id
        client = self.speckleInputs.speckle_client # ?
        
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
        base_obj = Base(units = "m")
        base_obj.layers = convertSelectedLayers(self.speckleInputs.all_layers, self.toolboxInputs.selected_layers, self.speckleInputs.project)
        
        if len(base_obj.layers) == 0: 
            arcpy.AddMessage("No data sent to stream " + streamId)
            return 
        try:
            # this serialises the block and sends it to the transport
            objId = operations.send(base=base_obj, transports=[transport])
        except SpeckleException as error:
            arcpy.AddError("Error sending data")
            #print("Error sending data")
            return
        except SpeckleWarning as warning:
            arcpy.AddMessage("SpeckleWarning: " + str(warning.args[0]))
            

        message = self.toolboxInputs.messageSpeckle
        print(message)
        if message is None or ( isinstance(message, str) and len(message) == 0):  message = "Sent from ArcGIS"
        print(message)
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
        except:
            arcpy.AddError("Error creating commit")

    def onReceive(self, parameters: List[Any]): 
        
        print("______________RECEIVE_______________")

        #if self.validateStreamBranch(parameters) == False: return

        try: 
            streamId = self.toolboxInputs.active_stream.id #stream_id
            client = self.speckleInputs.speckle_client # 
        except SpeckleWarning as warning: 
            arcpy.AddWarning(str(warning.args[0]))

        # get commit 
        commit = None 
        try: 
            #commit = self.toolboxInputs.active_branch.commits.items[0]
            commit = self.toolboxInputs.active_commit
            commitId = commit.id # text to make sure commit exists 
        except: 
            try: 
                commit = self.toolboxInputs.active_branch.commits.items[0]
                commitId = commit.id 
                arcpy.AddWarning("Failed to find a commit. Getting the last commit of the branch")
            except:
                arcpy.AddError("Failed to find a commit")
                return

        # next create a server transport - this is the vehicle through which you will send and receive
        try: 
            transport = ServerTransport(client=client, stream_id=streamId)
            
            client.commit.received(
            streamId,
            commit.id,
            source_application="ArcGIS",
            message="Received commit in ArcGIS",
            )
        except: 
            arcpy.AddError("Make sure your account has access to the chosen stream")
            return

        try:
            #print(commit)
            objId = commit.referencedObject
            commitDetailed = client.commit.get(streamId, commit.id)
            app = commitDetailed.sourceApplication
            if objId is None:
                return
            commitObj = operations.receive(objId, transport, None)
            
            if app != "QGIS" and app != "ArcGIS": 
                if self.speckleInputs.project.activeMap.spatialReference.type == "Geographic" or self.speckleInputs.project.activeMap.spatialReference is None: #TODO test with invalid CRS
                    arcpy.AddMessage("It is advisable to set the project Spatial reference to Projected type before receiving CAD geometry (e.g. EPSG:32631), or create a custom one from geographic coordinates")
                    print("It is advisable to set the project Spatial reference to Projected type before receiving CAD geometry (e.g. EPSG:32631), or create a custom one from geographic coordinates")
            print(f"Successfully received {objId}")

            # Clear 'latest' group
            streamBranch = streamId + "_" + self.toolboxInputs.active_branch.name + "_" + str(commit.id)
            newGroupName = f'{streamBranch}'
            
            groupExists = 0
            print(newGroupName)
            for l in self.speckleInputs.project.activeMap.listLayers(): 
                #print(l.longName)
                if l.longName.startswith(newGroupName + "\\"):
                    #print(l.longName)
                    self.speckleInputs.project.activeMap.removeLayer(l)
                    groupExists+=1
                elif l.longName == newGroupName: 
                    groupExists+=1
            print(newGroupName)
            if groupExists == 0:
                # create empty group layer file 
                path = self.speckleInputs.project.filePath.replace("aprx","gdb") #"\\".join(self.toolboxInputs.project.filePath.split("\\")[:-1]) + "\\speckle_layers\\"
                print(path)
                try:
                    f = open(path + "\\" + newGroupName + ".lyrx", "w")
                    content = createGroupLayer().replace("TestGroupLayer", newGroupName)
                    f.write(content)
                    f.close()
                    newGroupLayer = arcpy.mp.LayerFile(path + "\\" + newGroupName + ".lyrx")
                    layerGroup = self.speckleInputs.project.activeMap.addLayer(newGroupLayer)[0]
                except: # for 3.0.0
                    if self.speckleInputs.active_map is not None:
                        layerGroup = self.speckleInputs.active_map.createGroupLayer(newGroupName)
                    else:
                        arcpy.AddWarning("The map didn't fully load, try refreshing the plugin.")
                        return

                print(layerGroup)
                print("layer added")
                layerGroup.name = newGroupName
                print(newGroupName)

            if app == "QGIS" or app == "ArcGIS": check: Callable[[Base], bool] = lambda base: isinstance(base, Layer) or isinstance(base, VectorLayer) or isinstance(base, RasterLayer)
            else: check: Callable[[Base], bool] = lambda base: isinstance(base, Base)

            def callback(base: Base) -> bool:
                print("callback")
                #print(base)
                if isinstance(base, Layer) or isinstance(base, VectorLayer) or isinstance(base, RasterLayer):
                    layer = layerToNative(base, streamBranch, self.speckleInputs.project)
                    if layer is not None:
                        print("Layer created: " + layer.name)
                else:
                    loopObj(base, "")
                return True
            
            def loopObj(base: Base, baseName: str):
                memberNames = base.get_member_names()
                for name in memberNames:
                    if name in ["id", "applicationId", "units", "speckle_type"]: continue
                    try: loopVal(base[name], baseName + "/" + name) # loop properties not included above
                    except: pass

            def loopVal(value: Any, name: str): # "name" is the parent object/property/layer name
                if isinstance(value, Base): 
                    try: # dont go through parts of Speckle Geometry object
                        print("objects to loop through: " + value.speckle_type)
                        if value.speckle_type.startswith("Objects.Geometry."): pass #.Brep") or value.speckle_type.startswith("Objects.Geometry.Mesh") or value.speckle_type.startswith("Objects.Geometry.Surface") or value.speckle_type.startswith("Objects.Geometry.Extrusion"): pass
                        else: loopObj(value, name)
                    except: loopObj(value, name)

                if isinstance(value, List):
                    for item in value:
                        loopVal(item, name)
                        #print(item)
                        pt = None
                        if item.speckle_type and item.speckle_type.startswith("Objects.Geometry."): 

                            pt, pl = cadLayerToNative(value, name, streamBranch, self.speckleInputs.project)
                            if pt is not None: print("Layer group created: " + pt.name())
                            if pl is not None: print("Layer group created: " + pl.name())
                            break
                        
                        if item.speckle_type and "Revit" in item.speckle_type and item.speckle_type.startswith("Objects.BuiltElements."): 

                            msh_bool = bimLayerToNative(value, name, streamBranch, self.speckleInputs.project)
                            #if msh is not None: print("Layer group created: " + msh.name())
                            break
                
            traverseObject(commitObj, callback, check)
      
        except (SpeckleException, GraphQLException) as e:
            print("Receive failed: " + str(e))
            arcpy.AddError("Receive failed: " + str(e))
            return
        
        print("received")
        #self.updateParameters(parameters, True)
        #self.refresh(parameters)
    
    
#__all__ = ["Toolbox", "Speckle"]