
from typing import Any, List, Optional, Tuple, Union
import arcpy
from arcpy._mp import ArcGISProject, Map, Layer as arcLayer
from arcpy.management import CreateTable

import os.path

from specklepy.api.credentials import Account, get_local_accounts
from specklepy.api.client import SpeckleClient
from specklepy.logging.exceptions import (
    GraphQLException,
    SpeckleException,
)
from specklepy.api.wrapper import StreamWrapper 
from specklepy.api.models import Branch, Stream, Streams
from specklepy.logging import metrics

from osgeo import osr

import inspect 

try: 
    from speckle.ui.validation import tryGetStream
    from speckle.speckle_arcgis import SpeckleGIS
    from speckle.converter.layers import getAllProjLayers
    from speckle.ui.logger import logToUser
except: 
    from speckle_toolbox.esri.toolboxes.speckle.ui.validation import tryGetStream
    from speckle_toolbox.esri.toolboxes.speckle.speckle_arcgis import SpeckleGIS
    from speckle_toolbox.esri.toolboxes.speckle.converter.layers import getAllProjLayers
    from speckle_toolbox.esri.toolboxes.speckle.ui.logger import logToUser

FIELDS = ["project_streams","project_layer_selection", "lat_lon"]

def get_project_streams(self: SpeckleGIS, content: str = None):
    try:
        print("get proj streams")
        
        print("GET proj streams")
        project = self.gis_project
        table = findOrCreateSpeckleTable(project)
        if table is None: return 

        rows = arcpy.da.SearchCursor(table, "project_streams") 
        saved_streams = []
        for x in rows:
            saved_streams.append(x[0])

        temp = []
        ######### need to check whether saved streams are available (account reachable)
        if len(saved_streams) > 0:
            for url in saved_streams:
                try:
                    sw = StreamWrapper(url)
                    try: 
                        stream = tryGetStream(sw)
                    except SpeckleException as e:
                        logToUser(e.message, level=2, func = inspect.stack()[0][3])
                        stream = None
                    #strId = stream.id # will cause exception if invalid
                    temp.append((sw, stream))
                except SpeckleException as e:
                    logToUser(e.message, 2)
                #except GraphQLException as e:
                #    logger.logToUser(e.message, Qgis.Warning)
        self.current_streams = temp
    except Exception as e: 
        logToUser(str(e), level=2, func = inspect.stack()[0][3])
    
def set_project_streams(self: SpeckleGIS):
    try:
        print("SET proj streams")
        project = self.gis_project
        table = findOrCreateSpeckleTable(project)
        print("SET proj streams 2")
        
        value = [stream[0].stream_url for stream in self.current_streams] #",".join()
        print(value)

        if table is not None:
            proj_layers = []
            lan_lot = ""
            with arcpy.da.UpdateCursor(table, FIELDS) as cursor: 
                for row in cursor: # just one row
                    if row[1] is not None and row[1] != "": proj_layers.append(row[1]) 
                    if row[2] is not None and row[2] != "": lan_lot = row[2] 
                    cursor.deleteRow()
            del cursor 
            if len(proj_layers) == 0: proj_layers.append("")
            if len(value) == 0: value.append("")
            
            cursor = arcpy.da.InsertCursor(table, FIELDS ) 
            length = max(len(proj_layers), len(value))

            for i in range(length): 
                if i==0: 
                    cursor.insertRow([value[i], proj_layers[i] , lan_lot]) 
                else: 
                    try:
                        cursor.insertRow([value[i], proj_layers[i] , ""]) 
                    except: 
                        if len(value) <= i: cursor.insertRow(["", proj_layers[i] , ""]) 
                        if len(proj_layers) <= i: cursor.insertRow([value[i], "" , ""])
            del cursor 
    except Exception as e: 
        logToUser(str(e), level=2, func = inspect.stack()[0][3])
  
def get_project_layer_selection(self: SpeckleGIS):
    try:
        print("GET project layer selection from the table")
        project = self.gis_project
        table = findOrCreateSpeckleTable(project)
        if table is None: return 
        
        rows = arcpy.da.SearchCursor(table, "project_layer_selection") 
        saved_layers = []
        for x in rows:
            saved_layers.append(x[0]) 

        
        temp = []
        proj_layers = getAllProjLayers(project)
        ######### need to check whether saved streams are available (account reachable)
        if len(saved_layers) > 0:
            for layerPath in saved_layers:
                if layerPath == "": continue
                found = 0
                for layer in proj_layers:
                    print(layer.dataSource)
                    if layer.dataSource == layerPath:
                        temp.append((layer.name, layer))
                        found += 1
                        break
                if found == 0: 
                    logToUser(f'Saved layer not found: "{layerPath}"', level=1, func = inspect.stack()[0][3])
        self.current_layers = temp
    except Exception as e: 
        logToUser(str(e), level=2, func = inspect.stack()[0][3])

def set_project_layer_selection(plugin: SpeckleGIS):
    try:
        print("SET project layer selection function")
        project = plugin.gis_project
        value: List[str] = [layer[1].dataSource for layer in plugin.current_layers] #",".join([layer[1].dataSource for layer in plugin.current_layers]) 
        print(value)

        table = findOrCreateSpeckleTable(project)
        #print(table)
        if table is not None:
            lan_lot = ""
            proj_streams = []
            with arcpy.da.UpdateCursor(table, FIELDS) as cursor:
                for row in cursor: # just one row
                    if row[0] is not None and row[0] != "": proj_streams.append(row[0]) 
                    if row[2] is not None and row[2] != "": lan_lot = row[2]
                    cursor.deleteRow()
            del cursor 
            if len(proj_streams) == 0: proj_streams.append("")
            if len(value) == 0: value.append("")
            #print(proj_streams)
            
            cursor = arcpy.da.InsertCursor(table, FIELDS )
            length = max(len(proj_streams), len(value))
            #print(length)
            for i in range(length): 
                #print(i)
                if i==0: 
                    cursor.insertRow([proj_streams[i], value[i] , lan_lot]) 
                    print(i)
                else: 
                    try:
                        cursor.insertRow([proj_streams[i], value[i] , ""]) 
                    except: 
                        if len(proj_streams) <= i: cursor.insertRow(["", value[i] , ""]) 
                        if len(value) <= i: cursor.insertRow([proj_streams[i], "" , ""])
                #print(i)
            del cursor 

            try:
                metrics.track("Connector Action", plugin.active_account, {"name": "Save Layer Selection", "connector_version": str(plugin.version)})
            except Exception as e:
                logToUser(e, level = 2, func = inspect.stack()[0][3], plugin=plugin.dockwidget )

            #print(table)
    except Exception as e: 
        logToUser(str(e), level=2, func = inspect.stack()[0][3])

    print("SET project layer selection 2")

def get_survey_point(plugin: SpeckleGIS, content = None):
    try:
        print("get survey point")
        project = plugin.gis_project
        table = findOrCreateSpeckleTable(project)
        if table is None: return 

        rows = arcpy.da.SearchCursor(table, "lat_lon") 
        points = ""
        for x in rows:
            points = x[0]
            break

        if points != "": 
            vals: List[str] = points.replace(" ","").split(";")[:2]
            plugin.lat, plugin.lon = [float(i) for i in vals]

    except Exception as e: 
        logToUser(str(e), level=2, func = inspect.stack()[0][3])
    
def set_survey_point(plugin: SpeckleGIS):

    try:
        # from widget (2 strings) to local vars + update SR of the map
        print("SET survey point")
        
        project = plugin.gis_project
        vals =[ str(plugin.dockwidget.surveyPointLat.text()), str(plugin.dockwidget.surveyPointLon.text()) ]

        plugin.lat, plugin.lon = [float(i.replace(" ","")) for i in vals]
        
        if plugin.lat>180 or plugin.lat<-180 or plugin.lon >180 or plugin.lon<-180:
            logToUser("LAT LON values must be within (-180, 180). You can right-click on the canvas location to copy coordinates in WGS 84", level = 1, plugin=self.dockwidget)
            return True 
        pt = str(plugin.lat) + ";" + str(plugin.lon) 

        table = findOrCreateSpeckleTable(project)
        if table is not None:
            with arcpy.da.UpdateCursor(table, ["lat_lon"]) as cursor:
                for row in cursor: # just one row
                    cursor.updateRow([pt])
                    break
            del cursor   
        
        setProjectReferenceSystem(plugin)
        
        try:
            metrics.track("Connector Action", plugin.active_account, {"name": "Set As Center Point", "connector_version": str(plugin.version)})
        except Exception as e:
            logToUser(e, level = 2, func = inspect.stack()[0][3], plugin=plugin.dockwidget )
        
        return True

    except Exception as e:
        plugin.dockwidget.surveyPointLat.setText(str(plugin.lat))
        plugin.dockwidget.surveyPointLon.setText(str(plugin.lon))
        logToUser("Lat, Lon values invalid: " + str(e), level=2, func = inspect.stack()[0][3])
        return False 

def setProjectReferenceSystem(plugin: SpeckleGIS):
    try: 
        # save to project; create SR
        newCrsString = "+proj=tmerc +ellps=WGS84 +datum=WGS84 +units=m +no_defs +lon_0=" + str(plugin.lon) + " lat_0=" + str(plugin.lat) + " +x_0=0 +y_0=0 +k_0=1"
        newCrs = osr.SpatialReference()
        newCrs.ImportFromProj4(newCrsString)
        newCrs.MorphToESRI() # converts the WKT to an ESRI-compatible format
        
        validate = True if len(newCrs.ExportToWkt())>10 else False

        if validate: 
            newProjSR = arcpy.SpatialReference()
            newProjSR.loadFromString(newCrs.ExportToWkt())

            #source = osr.SpatialReference() 
            #source.ImportFromWkt(plugin.project.activeMap.spatialReference.exportToString())
            #transform = osr.CoordinateTransformation(source, newCrs)

            plugin.gis_project.activeMap.spatialReference =  newProjSR
            logToUser("Custom project Spatial Reference successfully applied", level=0, func = inspect.stack()[0][3])
        else:
            logToUser("Custom Spatial Reference could not be created", level=1, func = inspect.stack()[0][3])

        return True
    except Exception as e: 
        logToUser(str(e), level=2, func = inspect.stack()[0][3])
        return False

def findOrCreateSpeckleTable(project: ArcGISProject) -> Union[str, None]:
    try:
        path = project.filePath.replace("aprx","gdb") #"\\".join(project.filePath.split("\\")[:-1]) + "\\speckle_layers\\" #arcpy.env.workspace + "\\" #
    
        if 'speckle_gis' not in arcpy.ListTables():
            try: 
                table = CreateTable(path, "speckle_gis")
                arcpy.management.AddField(table, "project_streams", "TEXT")
                arcpy.management.AddField(table, "project_layer_selection", "TEXT")
                arcpy.management.AddField(table, "lat_lon", "TEXT")

                cursor = arcpy.da.InsertCursor(table, FIELDS )
                cursor.insertRow(["",""])
                del cursor
            
            except Exception as e:
                logToUser("Error creating a table: " + str(e), level=1, func = inspect.stack()[0][3])
                return None
        else: 
            #print("table already exists")
            # make sure fileds exist 
            table = path + "\\speckle_gis" 
            findOrCreateTableField(table, FIELDS[0])
            findOrCreateTableField(table, FIELDS[1])
            findOrCreateTableField(table, FIELDS[2])
            
            findOrCreateRow(table, FIELDS)

        return table
    
    except Exception as e: 
        logToUser(str(e), level=2, func = inspect.stack()[0][3])
        return None 

def findOrCreateTableField(table: str, field: str):
    try: 
        with arcpy.da.UpdateCursor(table, [field]) as cursor:
            value = None
            for row in cursor:
                value = row # tuple(val,)
                if value[0] is None: cursor.updateRow("")
                break # look at the 1st row only 
        del cursor

        #if value is None: # if there are no rows 
        #    cursor = arcpy.da.InsertCursor(table, [field])
        #    cursor.insertRow([""]) 
        #    del cursor
    
    except: # if field doesn't exist
        arcpy.management.AddField(table, field, "TEXT")
        #cursor = arcpy.da.InsertCursor(table, [field] )
        #cursor.insertRow([""])
        del cursor

def findOrCreateRow(table:str, fields: List[str]):
    try:
        # check if the row exists 
        cursor = arcpy.da.SearchCursor(table, fields)
        k=-1
        for k, row in enumerate(cursor): 
            #print(row)
            break
        del cursor
        
        # if no rows
        if k == -1:
            cursor = arcpy.da.InsertCursor(table, fields)
            cursor.insertRow(["", "", ""]) 
            del cursor
        else: 
            with arcpy.da.UpdateCursor(table, fields) as cursor:
                for row in cursor:
                    if None in row: cursor.updateRow(["","",""])
                    break # look at the 1st row only 
            del cursor
    
    except Exception as e: 
        logToUser(str(e), level=2, func = inspect.stack()[0][3])

r'''
class speckleInputsClass:
    #def __init__(self):
    print("CREATING speckle inputs first time________")
    instances = []
    accounts: List[Account] = get_local_accounts()
    account = None
    streams_default: Optional[List[Stream]] = None

    project = None
    active_map = None
    saved_streams: List[Optional[Tuple[StreamWrapper, Stream]]] = []
    stream_file_path: str = ""
    all_layers: List[arcLayer] = []
    clients: List[SpeckleClient] = []

    for acc in accounts:
        if acc.isDefault: account = acc
        new_client = SpeckleClient(
            acc.serverInfo.url,
            acc.serverInfo.url.startswith("https")
        )
        new_client.authenticate_with_token(token=acc.token)
        clients.append(new_client)

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
            # following will fail if no project found 
            self.active_map = aprx.activeMap
            
            if self.active_map is not None and isinstance(self.active_map, Map): # if project loaded
                for layer in self.active_map.listLayers(): 
                    try: geomType = arcpy.Describe(layer.dataSource).shapeType.lower()
                    except: geomType = '' #print(arcpy.Describe(layer.dataSource)) #and arcpy.Describe(layer.dataSource).shapeType.lower() != "multipatch")
                    if (layer.isFeatureLayer and geomType != "multipatch") or layer.isRasterLayer: self.all_layers.append(layer) #type: 'arcpy._mp.Layer'
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
                    #print(url)
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
        if isinstance(sw, StreamWrapper):
            steamId = sw.stream_id
            try: steamId = sw.stream_id.split("/streams/")[1].split("/")[0] 
            except: pass

            client = sw.get_client()
            stream = client.stream.get(id = steamId, branch_limit = 100, commit_limit = 100)
            if isinstance(stream, GraphQLException):
                raise SpeckleException(stream.errors[0]['message'])
            return stream
        else: 
            raise SpeckleException('Invalid StreamWrapper provided')

class toolboxInputsClass:

    print("CREATING UI inputs first time________")
    instances = []
    lat: float = 0.0
    lon: float = 0.0
    active_stream: Optional[Stream] = None
    active_stream_wrapper: Optional[StreamWrapper] = None
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
        except: self.project = None; print("Project not found"); arcpy.AddWarning("Project not found")
        self.instances.append(self)

    def setProjectStreams(self, wr: StreamWrapper, add = True): 
        # ERROR 032659 Error queueing metrics request: 
        print("SET proj streams")

        if os.path.exists(self.stream_file_path) and ".gdb\\speckle_streams.txt" in self.stream_file_path: 

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
        elif ".gdb\\speckle_streams.txt" in self.stream_file_path: 
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
            content = None 
            if os.path.exists(self.stream_file_path) and ".gdb\\speckle_streams.txt" in self.stream_file_path: 
                try: 
                    f = open(self.stream_file_path, "r")
                    content = f.read()
                    f.close()
                except: pass
        if content:
            for i, coords in enumerate(content.split(",")):
                if "speckle_sr_origin_" in coords: 
                    try:
                        x, y = [float(c) for c in coords.replace("speckle_sr_origin_","").split(";")]
                    except: pass
        return (x, y) 

    def set_survey_point(self, coords: List[float]):
        # from widget (2 strings) to local vars + update SR of the map
        print("SET survey point")

        if len(coords) == 2: 
            pt = "speckle_sr_origin_" + str(coords[0]) + ";" + str(coords[1]) 
            if os.path.exists(self.stream_file_path) and ".gdb\\speckle_streams.txt" in self.stream_file_path: 

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
            elif ".gdb\\speckle_streams.txt" in self.stream_file_path: 
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
            newCrs.MorphToESRI() # converts the WKT to an ESRI-compatible format
            

            validate = True if len(newCrs.ExportToWkt())>10 else False

            if validate: 
                newProjSR = arcpy.SpatialReference()
                newProjSR.loadFromString(newCrs.ExportToWkt())

                #source = osr.SpatialReference() 
                #source.ImportFromWkt(self.project.activeMap.spatialReference.exportToString())
                #transform = osr.CoordinateTransformation(source, newCrs)

                self.project.activeMap.spatialReference =  newProjSR
                arcpy.AddMessage("Custom project CRS successfully applied")
            else:
                arcpy.AddWarning("Custom CRS could not be created")
        
        else:
            arcpy.AddWarning("Custom CRS could not be created: not enough coordinates provided")

        return True
'''
    