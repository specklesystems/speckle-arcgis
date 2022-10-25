
from typing import Any, List, Optional, Tuple, Union
import arcpy
from arcpy._mp import ArcGISProject, Map, Layer as arcLayer
from specklepy.api.models import Branch, Stream, Streams
import os.path

from specklepy.api.credentials import get_local_accounts
from specklepy.api.client import SpeckleClient
from specklepy.logging.exceptions import (
    GraphQLException,
    SpeckleException,
)
#from specklepy.api.credentials import StreamWrapper
from specklepy.api.wrapper import StreamWrapper
from osgeo import osr

class speckleInputsClass:
    #def __init__(self):
    print("CREATING speckle inputs first time________")
    instances = []
    accounts = get_local_accounts()
    account = None
    streams_default: None or Streams = None 

    project = None
    active_map = None
    saved_streams: List[Optional[Tuple[StreamWrapper, Stream]]] = []
    stream_file_path: str = ""
    all_layers: List[arcLayer] = []

    for acc in accounts:
        if acc.isDefault:
            account = acc
            break
    speckle_client = None
    if account:
        speckle_client = SpeckleClient(
            account.serverInfo.url,
            account.serverInfo.url.startswith("https")
    )
        speckle_client.authenticate_with_token(token=account.token)
        streams_default = speckle_client.stream.search("")

    def __init__(self) -> None:
        print("___start speckle inputs________")
        self.all_layers = []
        try:
            aprx = ArcGISProject('CURRENT')
            self.project = aprx
            self.active_map = aprx.activeMap
            
            if self.active_map is not None and isinstance(self.active_map, Map): # if project loaded
                for layer in self.active_map.listLayers(): 
                    #print(layer)
                    if layer.isFeatureLayer or layer.isRasterLayer: self.all_layers.append(layer) #type: 'arcpy._mp.Layer'
            self.stream_file_path: str = aprx.filePath.replace("aprx","gdb") + "\\speckle_streams.txt"

            if os.path.exists(self.stream_file_path): 
                try: 
                    f = open(self.stream_file_path, "r")
                    content = f.read()
                    self.saved_streams = self.getProjectStreams(content)
                    f.close()
                except: pass
                
            elif len(self.stream_file_path) >10: 
                f = open(self.stream_file_path, "x")
                f.close()
                f = open(self.stream_file_path, "w")
                content = ""
                f.write(content)
                f.close()
        except: self.project = None; print("Project not found")
        self.instances.append(self)

    def getProjectStreams(self, content: str = None):
        print("get proj streams")
        if not content: 
            content = self.stream_file_path
            try: 
                f = open(self.stream_file_path, "r")
                content = f.read()
                f.close()
            except: pass

        ######### need to check whether saved streams are available (account reachable)
        if content:
            streamsTuples = []
            for i, url in enumerate(content.split(",")):

                streamExists = 0
                index = 0
                try:
                    print(url)
                    sw = StreamWrapper(url)
                    stream = self.tryGetStream(sw)

                    for st in streamsTuples: 
                        if isinstance(stream, Stream) and st[0].stream_id == stream.id: 
                            streamExists = 1; 
                            break 
                        index += 1
                    if streamExists == 1: del streamsTuples[index]
                    streamsTuples.insert(0,(sw, stream))

                except SpeckleException as e:
                    arcpy.AddMessage(str(e.args))
            return streamsTuples
        else: return []

    def tryGetStream (self,sw: StreamWrapper) -> Stream:
        #print("Try get streams")

        steamId = sw.stream_id
        try: steamId = sw.stream_id.split("/streams/")[1].split("/")[0] 
        except: pass

        client = sw.get_client()
        stream = client.stream.get(steamId)
        if isinstance(stream, GraphQLException):
            raise SpeckleException(stream.errors[0]['message'])
        return stream


class toolboxInputsClass:
    #def __init__(self):
    print("CREATING UI inputs first time________")
    # self.instances.append(self)
    instances = []
    lat: float = 0.0
    lon: float = 0.0
    active_stream: Optional[Stream] = None
    active_branch: Optional[Branch] = None
    active_commit = None
    selected_layers: List[Any] = []
    messageSpeckle: str = ""
    action: int = 1 #send
    project = None
    stream_file_path: str = ""
    # Get the target item's Metadata object
    
    def __init__(self) -> None:
        print("___start UI inputs________")
        try:
            aprx = ArcGISProject('CURRENT')
            project = aprx
            self.stream_file_path: str = aprx.filePath.replace("aprx","gdb") + "\\speckle_streams.txt"
            if os.path.exists(self.stream_file_path): 
                try: 
                    f = open(self.stream_file_path, "r")
                    content = f.read()
                    self.lat, self.lon = self.get_survey_point(content)
                    f.close()
                except: pass
        except: print("Project not found")
        try:
            aprx = ArcGISProject('CURRENT')
            self.project = aprx
        except: self.project = None; print("Project not found")
        self.instances.append(self)

    def setProjectStreams(self, wr: StreamWrapper, add = True): 
        # ERROR 032659 Error queueing metrics request: 
        # Cannot parse  into a stream wrapper class - invalid URL provided.
        print("SET proj streams")

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
        elif len(self.stream_file_path) >10: 
            f = open(self.stream_file_path, "x")
            f.close()
            f = open(self.stream_file_path, "w")
            f.write(str(wr.stream_url) + ",")
            f.close()
 
    def get_survey_point(self, content = None) -> Tuple[float]:
        # get from saved project 
        print("get survey point")
        x = y = 0
        if not content: 
            content = self.stream_file_path
            try: 
                f = open(self.stream_file_path, "r")
                content = f.read()
                f.close()
            except: pass
        if content:
            temp = []
            for i, coords in enumerate(content.split(",")):
                if "speckle_sr_origin_" in coords: 
                    try:
                        x, y = [float(c) for c in coords.replace("speckle_sr_origin_","").split(";")]
                    except: pass
        return (x, y)

    def set_survey_point(self, coords: List[float]):
        # from widget (2 strings) to local vars + update SR of the map
        print("SET survey point")

        pt = "speckle_sr_origin_" + str(coords[0]) + ";" + str(coords[1]) 
        if os.path.exists(self.stream_file_path): 

            new_content = ""
            f = open(self.stream_file_path, "r")
            existing_content = f.read()
            f.close()

            f = open(self.stream_file_path, "w")
            if pt in existing_content: 
                new_content = existing_content.replace( pt , "")
            else: 
                new_content = existing_content 
            
            new_content += pt + "," # add point
            f.write(new_content)
            f.close()
        elif len(self.stream_file_path) >10: 
            f = open(self.stream_file_path, "x")
            f.close()
            f = open(self.stream_file_path, "w")
            f.write(pt + ",")
            f.close()
        
        # save to project; crearte SR
        self.lat, self.lon = coords[0], coords[1]
        newCrsString = "+proj=tmerc +ellps=WGS84 +datum=WGS84 +units=m +no_defs +lon_0=" + str(self.lon) + " lat_0=" + str(self.lat) + " +x_0=0 +y_0=0 +k_0=1"
        newCrs = osr.SpatialReference()
        newCrs.ImportFromProj4(newCrsString)
        print(newCrs.ExportToWkt())

        validate = True if len(newCrs.ExportToWkt())>10 else False

        if validate: 
            newProjSR = arcpy.SpatialReference()
            newProjSR.loadFromString(newCrs.ExportToWkt())
            self.project.activeMap.spatialReference =  newProjSR
            arcpy.AddWarning("Custom project CRS successfully applied")
        else:
            arcpy.AddWarning("Custom CRS could not be created")

        return True

    