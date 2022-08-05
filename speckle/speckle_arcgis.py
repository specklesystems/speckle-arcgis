# -*- coding: utf-8 -*-

from typing import List
import arcpy

from speckle.converter.layers._init_ import convertSelectedLayers
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

class Toolbox(object):
    def __init__(self):
        """Define the toolbox (the name of the toolbox is the name of the
        .pyt file)."""
        self.label = "Speckle Toolbox"
        self.alias = "speckle_toolbox"  
        # List of tool classes associated with this toolbox
        self.tools = [SpeckleSender]     
    
class SpeckleSender(object):
    def __init__(self):
        print("resetting plugin")   
        self.label       = "Speckle Sender"
        self.description = "Allows you to send your layers " + \
                           "to other software using Speckle server." 
        #self.stylesheet 
        #self.attributes= os.path.dirname(__file__) + "/plugin_utils/speckle.png"
        #print(self.attributes)

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
        try: 
            # https://pro.arcgis.com/en/pro-app/2.8/arcpy/mapping/alphabeticallistofclasses.htm
            aprx = arcpy.mp.ArcGISProject('current') 
            active_map = aprx.activeMap
            self.project = aprx

            if active_map is not None: # if project loaded
                for layer in active_map.listLayers(): 
                    if layer.isFeatureLayer: self.all_layers.append(layer) #type: 'arcpy._mp.Layer'
        except: pass

        
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
        stream.filter.list = [ (st.name + " | " + st.id) for st in self.streams ]
        
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
        selected_layers.filter.list = [str(i) + "-" + l.name for i,l in enumerate(self.all_layers)] #"Polyline"

        
        '''
        refresh = arcpy.Parameter(
            displayName="Refresh",
            name="refresh",
            datatype="GPBoolean",
            parameterType="Optional",
            #category="Sending data",
            direction="Input"
            )
        refresh.filter.type = "ValueList"   
        refresh.value = False 
        '''

        action = arcpy.Parameter(
            displayName="",
            name="action",
            datatype="GPString",
            parameterType="Required",
            #category="Sending data",
            direction="Input"
            )
        action.value = "Send" 
        action.filter.type = 'ValueList'
        action.filter.list = ["Send", "Receive"]  

        parameters = [stream, branch, selected_layers, msg, action]
        return parameters

    def isLicensed(self): #optional
        return True

    def updateParameters(self, parameters: List): #optional
        if parameters[0].altered:
            parameters[1].value = "main"

            # Search for the stream by name
            if parameters[0].valueAsText is not None:
                selected_stream_name = parameters[0].valueAsText[:]
                self.active_stream = None
                for st in self.streams:
                    if st.name == selected_stream_name.split(" | ")[0]: 
                        self.active_stream = st
                        break

                parameters[1].filter.list = [branch.name for branch in self.active_stream.branches.items]
                
                #if self.active_stream is None: 
                #    print("Choose a valid stream")
                #    arcpy.AddMessage("Choose a valid stream")
                #    return

        if parameters[1].altered:
            # Search for the stream by name
            if parameters[1].valueAsText is not None:
                selected_branch_name = parameters[1].valueAsText[:]
                self.active_branch = None
                if self.active_stream is not None:
                    for br in self.active_stream.branches.items:
                        if br.name == selected_branch_name: #.split(" | ")[0]: 
                            self.active_branch = br
                            break
        
        if parameters[2].altered: # selected layers
            if parameters[2].valueAsText is not None:
                self.selected_layers = parameters[2].values

        if parameters[3].altered:
            self.messageSpeckle = parameters[3].valueAsText

        '''
        if parameters[4].altered: # refresh btn
            print("Refresh")
            if parameters[4].value == True:
                self.__init__()
                #self.streams = self.speckle_client.stream.search("")
                params_new = []
                for i,p in enumerate(parameters):
                    params_new.append(p)
                    params_new[i].value = None
                params_new[4].value = False
                params_new[0].filter.list = [ (st.name + " | " + st.id) for st in self.streams ]
                params_new[2].filter.list = [str(i) + "-" + l.name for i,l in enumerate(self.all_layers)]
                self.updateParameters(params_new)
        '''

        if parameters[4].altered:
            if parameters[4].valueAsText == "Send": self.action = 1
            else: self.action = 0
                  
        return 

    def updateMessages(self, parameters): #optional
        return

    def execute(self, parameters: List, messages): 
        # https://pro.arcgis.com/en/pro-app/latest/arcpy/get-started/what-is-arcpy-.htm
        #Warning if any of the fields is invalid/empty 
        print("_______________________Run__________________________")
        if self.action == 1: self.onSend(parameters)
        elif self.action == 0: self.onReceive(parameters)

    def validateStreamBranch(self, parameters: List):
        	
        self.updateParameters(parameters)
        if self.active_stream is None:
            arcpy.AddError("Choose a valid stream")
            return False
        if self.active_branch is None: 
            arcpy.AddError("Choose a valid branch")
            return False
        return True 

    def onSend(self, parameters: List):

        if self.validateStreamBranch(parameters) == False: return

        if len(self.selected_layers) == 0: 
            arcpy.AddError("No layers selected")
            return

        streamId = self.active_stream.id #stream_id
        client = self.speckle_client # ?
        
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
        base_obj.layers = convertSelectedLayers(self.all_layers, self.selected_layers, self.project)
        
        try:
            # this serialises the block and sends it to the transport
            objId = operations.send(base=base_obj, transports=[transport])
        except SpeckleException as error:
            arcpy.AddError("Error sending data")
            print("Error sending data")
            return
        except SpeckleWarning as warning:
            arcpy.AddMessage("SpeckleWarning: " + str(warning.args[0]))
            

        message = self.messageSpeckle
        if message is None or ( isinstance(message, str) and len(message) == 0):  message = "Sent from ArcGIS"
        try:
            # you can now create a commit on your stream with this object
            client.commit.create(
                stream_id=streamId,
                object_id=objId,
                branch_name=self.active_branch.name,
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

        streamId = self.active_stream.id #stream_id
        client = self.speckle_client # 

        # get last commit 
        try: 
            commit = self.active_branch.commits.items[0]
        except: 
            arcpy.AddError("Failed to find a commit")
            return

        # next create a server transport - this is the vehicle through which you will send and receive
        try: transport = ServerTransport(client=client, stream_id=streamId)
        except: 
            arcpy.AddError("Make sure your account has access to the chosen stream")
            return