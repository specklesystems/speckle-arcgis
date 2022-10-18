
from typing import Any, Callable, List, Optional, Tuple
import arcpy
from arcpy._mp import ArcGISProject, Map, Layer as arcLayer
from specklepy.api.models import Branch, Stream, Streams
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

class uiInputs(object):
    speckle_client: Any
    saved_streams: List[Tuple[StreamWrapper, Stream]]
    stream_file_path: str
    streams_default: Optional[Streams]
    active_stream: Optional[Stream]
    active_branch: Optional[Branch]
    all_layers: List[arcLayer]
    selected_layers: List[Any]
    messageSpeckle: str
    project: ArcGISProject
    action: int
    instances = []

    def __init__(self):
        print("___start UI inputs________")
        self.instances.append(self)
        self.accounts = get_local_accounts()
        self.account = None
        for acc in self.accounts:
            if acc.isDefault: self.account = acc; break
        #account.userInfo.name, account.serverInfo.url
        self.speckle_client = SpeckleClient(self.account.serverInfo.url, self.account.serverInfo.url.startswith("https"))
        self.speckle_client.authenticate_with_token(token=self.account.token)
        #print("ping1")
        #print(self.speckle_client)
        #print("ping")
        self.saved_streams = []
        self.active_stream = None
        self.active_branch = None
        self.active_commit = None
        self.all_layers = []
        self.selected_layers = []
        self.messageSpeckle = ""
        self.project = aprx = None
        self.action = 1 #send
        #print(self.streams)
        try: aprx = ArcGISProject('CURRENT') 
        except: aprx = None; print("Project not found")
        self.project = aprx
        self.streams_default = self.speckle_client.stream.search("")
        #print("ping2")

        active_map = aprx.activeMap
        #print("ping3")

        if active_map is not None and isinstance(active_map, Map): # if project loaded
            for layer in active_map.listLayers(): 
                #print(layer)
                if layer.isFeatureLayer or layer.isRasterLayer: self.all_layers.append(layer) #type: 'arcpy._mp.Layer'
        #print("ping4")
        # Get the target item's Metadata object
        self.stream_file_path = aprx.filePath.replace("aprx","gdb") + "\\speckle_streams.txt"
        #print(path)
        if os.path.exists(self.stream_file_path): 
            try: 
                f = open(self.stream_file_path, "r")
                self.saved_streams = self.getProjectStreams(content = f.read())
                f.close()
            except: pass
            
        else: 
            f = open(self.stream_file_path, "w")
            content = ""
            f.write(content)
            f.close()
        
    def setProjectStreams(self, wr: StreamWrapper, add = True): 
        # ERROR 032659 Error queueing metrics request: 
        # Cannot parse  into a stream wrapper class - invalid URL provided.
        #print("___set proj streams__")

        if os.path.exists(self.stream_file_path): 

            new_content = ""

            f = open(self.stream_file_path, "r")
            existing_content = f.read()
            f.close()

            f = open(self.stream_file_path, "w")
            if str(wr.stream_url) in existing_content: 
                new_content = existing_content.replace(str(wr.stream_url) + "," , "")
            else: 
                new_content = existing_content 
            
            if add == True: new_content += str(wr.stream_url) + "," # add stream
            else: pass # remove stream

            f.write(new_content)
            f.close()
        else: 
            f = open(self.stream_file_path, "w")
            f.write(str(wr.stream_url) + ",")
            f.close()
  
    def getProjectStreams(self, content:str = None):
        #print("___get proj streams__")
        if not content: 
            content = self.stream_file_path
            try: 
                f = open(self.stream_file_path, "r")
                content = f.read()
                f.close()
            except: pass

        ######### need to check whether saved streams are available (account reachable)
        if content:
            temp = []
            for i, url in enumerate(content.split(",")):

                streamExists = 0
                index = 0
                try:
                    sw = StreamWrapper(url)
                    stream = self.tryGetStream(sw)

                    for st in temp: 
                        if isinstance(stream, Stream) and st[0].stream_id == stream.id: 
                            streamExists = 1; 
                            break 
                        index += 1
                    if streamExists == 1: del temp[index]
                    temp.insert(0,(sw, stream))

                except SpeckleException as e:
                    arcpy.AddMessage(str(e.args[0]))
            self.saved_streams = temp
        #print(self.saved_streams)
        #print("__return get proj streams___")
        return self.saved_streams
    
    def tryGetStream (self,sw: StreamWrapper) -> Stream:

        steamId = sw.stream_id
        try: steamId = sw.stream_id.split("/streams/")[1].split("/")[0] 
        except: pass

        client = sw.get_client()
        stream = client.stream.get(steamId)
        if isinstance(stream, GraphQLException):
            raise SpeckleException(stream.errors[0]['message'])
        return stream
      