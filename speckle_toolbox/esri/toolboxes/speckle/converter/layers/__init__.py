"""
Contains all Layer related classes and methods.
"""
from datetime import datetime
import os
from typing import Any, List, Tuple, Union


#from speckle_toolbox.esri.toolboxes.speckle.speckle_arcgis import SpeckleGIS

#from regex import D

import inspect

try:
    from speckle.converter.layers.CRS import CRS
    from speckle.converter.layers.Layer import Layer, VectorLayer, RasterLayer
    from speckle.converter.layers.symbology import vectorRendererToNative, rasterRendererToNative, rendererToSpeckle, cadBimRendererToNative 
    from speckle.converter.layers.feature import featureToNative, featureToSpeckle, cadFeatureToNative, bimFeatureToNative, rasterFeatureToSpeckle
    from speckle.plugin_utils.helpers import findOrCreatePath, findFeatColors

    from speckle.converter.geometry.mesh import constructMeshFromRaster, meshToNative, writeMeshToShp
    from speckle.converter.layers.utils import findTransformation
    from speckle.converter.layers.utils import getLayerAttributes, newLayerGroupAndName, validate_path
    from speckle.plugin_utils.helpers import validateNewFclassName, removeSpecialCharacters
    from speckle.ui.logger import logToUser

except: 
    from speckle_toolbox.esri.toolboxes.speckle.converter.layers.CRS import CRS
    from speckle_toolbox.esri.toolboxes.speckle.converter.layers.Layer import Layer, VectorLayer, RasterLayer
    from speckle_toolbox.esri.toolboxes.speckle.converter.layers.symbology import vectorRendererToNative, rasterRendererToNative, rendererToSpeckle, cadBimRendererToNative 
    from speckle_toolbox.esri.toolboxes.speckle.converter.layers.feature import featureToNative, featureToSpeckle, cadFeatureToNative, bimFeatureToNative, rasterFeatureToSpeckle
    from speckle_toolbox.esri.toolboxes.speckle.plugin_utils.helpers import findOrCreatePath, findFeatColors 

    from speckle_toolbox.esri.toolboxes.speckle.converter.geometry.mesh import constructMeshFromRaster, meshToNative, writeMeshToShp
    from speckle_toolbox.esri.toolboxes.speckle.converter.layers.utils import findTransformation
    from speckle_toolbox.esri.toolboxes.speckle.converter.layers.utils import getLayerAttributes, newLayerGroupAndName, validate_path
    from speckle_toolbox.esri.toolboxes.speckle.plugin_utils.helpers import validateNewFclassName, removeSpecialCharacters
    from speckle_toolbox.esri.toolboxes.speckle.ui.logger import logToUser

from specklepy.objects import Base
from specklepy.objects.geometry import Mesh

import arcgisscripting
import pandas as pd
import arcpy
from arcpy._mp import ArcGISProject, Map, Layer as arcLayer
from arcpy.management import (CreateFeatureclass, MakeFeatureLayer,
                              AddFields, AlterField, DefineProjection )

import numpy as np

GEOM_LINE_TYPES = ["Objects.Geometry.Line", "Objects.Geometry.Polyline", "Objects.Geometry.Curve", "Objects.Geometry.Arc", "Objects.Geometry.Circle", "Objects.Geometry.Ellipse", "Objects.Geometry.Polycurve"]

def getAllProjLayers(project: ArcGISProject) -> List[arcLayer]:
    print("get all project layers")
    #print(project)
    #print(project.activeMap)
    layers = []
    try:
        if project.activeMap is not None and isinstance(project.activeMap, Map): # if project loaded
            print(type(project.activeMap))
            #print(project.activeMap.listLayers())
            for layer in project.activeMap.listLayers(): 
                if (layer.isFeatureLayer) or layer.isRasterLayer: 
                    layers.append(layer) #type: 'arcpy._mp.Layer'
                    #print(layers)
                    #path = layer.dataSource
        else: 
            print(type(project.activeMap))
            logToUser("Cannot get Project layers, Project Active Map not loaded or not selected", level=1, func = inspect.stack()[0][3])
            return []
    except Exception as e:
        logToUser(str(e), level=2, func = inspect.stack()[0][3])
    return layers 


def getLayers(plugin, bySelection = False ) -> List[arcLayer]:
    """Gets a list of all layers in the map"""
    layers = []
    try:
        print("___ get layers list ___")

        # issue with getting selected layers: https://community.esri.com/t5/python-questions/determining-selected-layers-in-the-table-of/td-p/252098

        self = plugin.dockwidget
        project = plugin.gis_project
        all_layers = getAllProjLayers(project)
        
        if bySelection is True: # by selection 
            print("get selected layers")
            for layer in project.activeMap.listLayers(): 
                
                print(layer.longName)
                if layer.visible and ( (layer.isFeatureLayer) or layer.isRasterLayer ): 
                    
                    # find possible nested groups
                    layerGroupsHidden = 0
                    for group in project.activeMap.listLayers(): 
                        if group.isGroupLayer and layer.longName.startswith(group.longName + "\\"): 
                            if not group.visible: 
                                layerGroupsHidden += 1
                                break 
                    if layerGroupsHidden == 0: 
                        layers.append(layer)
            print("layers selected and saved") 
        else: # from project data 
            #all_layers_ids = [l.id() for l in project.mapLayers().values()]
            for item in plugin.current_layers:
                try: 
                    layerPath = item[1].dataSource
                    
                    found = 0
                    for l in all_layers:
                        if l.dataSource == layerPath:
                            layers.append(l)
                            found += 1
                            break 
                    if found == 0: 
                        logToUser(f'Saved layer not found: "{item[0]}"', level=1, func = inspect.stack()[0][3])

                except:
                    logToUser(f'Saved layer not found: "{item[0]}"', level=1, func = inspect.stack()[0][3])
                    continue
    except Exception as e:
        logToUser(str(e), level=2, func = inspect.stack()[0][3])
    return layers 
    
def convertSelectedLayers(layers: List[arcLayer], project: ArcGISProject) -> List[Union[VectorLayer,Layer]]:
    """Converts the current selected layers to Speckle"""
    print("________Convert Layers_________")
    result = []
    try:
        r'''
        for layer in selected_layers:
            layerToSend = None
            for c in range(len(all_layers)):
                if int(layer.split("-",1)[0]) == c:
                    layerToSend = all_layers[c]
                    break
            if layerToSend is not None: 
                ds = layerToSend.dataSource #file path
                #if layerToSend.isFeatureLayer: 
                newBaseLayer = layerToSpeckle(layerToSend, project)
                if newBaseLayer is not None: 
                    result.append(newBaseLayer)
                #elif layerToSend.isRasterLayer: pass
                print(result)
        '''
        for i, layer in enumerate(layers):
            result.append(layerToSpeckle(layer, project))
        
    except Exception as e:
        logToUser(str(e), level=2, func = inspect.stack()[0][3])
    return result

def layerToSpeckle(layer: arcLayer, project: ArcGISProject) -> Union[VectorLayer, RasterLayer]: #now the input is QgsVectorLayer instead of qgis._core.QgsLayerTreeLayer
    """Converts a given GIS Layer to Speckle"""
    print("________Convert Feature Layer_________")

    speckleLayer = None
    try:

        projectCRS = project.activeMap.spatialReference
        try: data = arcpy.Describe(layer.dataSource)
        except OSError as e: 
            logToUser(str(e.args[0]), level=2, func = inspect.stack()[0][3])
            return None

        layerName = layer.name
        crs = data.SpatialReference
        units = "m"
        layerObjs = []

        # Convert CRS to speckle, use the projectCRS
        speckleReprojectedCrs = CRS(name = projectCRS.name, wkt = projectCRS.exportToString(), units = units)
        layerCRS = CRS(name=crs.name, wkt=crs.exportToString(), units = units) 
        
        #renderer = selectedLayer.renderer()
        #layerRenderer = rendererToSpeckle(renderer) 
        
        if layer.isFeatureLayer: 
            print("VECTOR LAYER HERE")
            
            speckleLayer = VectorLayer(units = "m")
            speckleLayer.type="VectorLayer"
            speckleLayer.name = layerName
            speckleLayer.crs = speckleReprojectedCrs
            speckleLayer.renderer = rendererToSpeckle(project, project.activeMap, layer, None)
            #speckleLayer.datum = datum


            try: # https://pro.arcgis.com/en/pro-app/2.8/arcpy/get-started/the-spatial-reference-object.htm
                
                #print(data.datasetType) # FeatureClass
                if data.datasetType == "FeatureClass": #FeatureClass, ?Table Properties, ?Datasets
                    
                    # write feature attributes
                    fieldnames = [field.name for field in data.fields]
                    rows_shapes = arcpy.da.SearchCursor(layer.dataSource, "Shape@") # arcpy.da.SearchCursor(in_table, field_names, {where_clause}, {spatial_reference}, {explode_to_points}, {sql_clause})
                    print("__ start iterating features")
                    row_shapes_list = [x for k, x in enumerate(rows_shapes)]
                    for i, features in enumerate(row_shapes_list):

                        print("____error Feature # " + str(i+1)) # + " / " + str(sum(1 for _ in enumerate(rows_shapes))))
                        if features[0] is None: continue 
                        feat = features[0]
                        #print(feat) # <geoprocessing describe geometry object object at 0x000002A75D6A4BD0>
                        #print(feat.hasCurves)
                        #print(feat.partCount)

                        if feat is not None: 
                            print(feat) # <geoprocessing describe geometry object object at 0x0000026796C47780>
                            rows_attributes = arcpy.da.SearchCursor(layer.dataSource, fieldnames)
                            row_attr = []
                            for k, attrs in enumerate(rows_attributes):
                                if i == k: 
                                    row_attr = attrs
                                    break

                            # if curves detected, createa new feature class, turn to segments and get the same feature but in straigt lines
                            #print(feat.hasCurves)
                            if feat.hasCurves:
                                #f_class_modified = curvedFeatureClassToSegments(layer)
                                #rows_shapes_modified = arcpy.da.SearchCursor(f_class_modified, "Shape@") 
                                #row_shapes_list_modified = [x for k, x in enumerate(rows_shapes_modified)]

                                feat = feat.densify("ANGLE", 1000, 0.12)
                                #print(feat)


                            b = featureToSpeckle(fieldnames, row_attr, i, feat, projectCRS, project, layer)
                            if b is not None: 
                                layerObjs.append(b)
                                print(b)
                        
                        else: arcpy.AddError(f"Feature skipped due to invalid geometry")
                        print("____End of Feature # " + str(i+1))
                        
                    print("__ finish iterating features")
                    speckleLayer.features=layerObjs
                    speckleLayer.geomType = data.shapeType

                    if len(speckleLayer.features) == 0: return None

                    #layerBase.renderer = layerRenderer
                    #layerBase.applicationId = selectedLayer.id()

            except OSError as e: 
                logToUser(str(e), level=2, func = inspect.stack()[0][3])
                return None

        elif layer.isRasterLayer:
            print("RASTER IN DA HOUSE")
            print(layer.name) # London_square.tif
            print(arcpy.Describe(layer.dataSource)) # <geoprocessing describe data object object at 0x000002507C7F3BB0>
            print(arcpy.Describe(layer.dataSource).datasetType) # RasterDataset
            b = rasterFeatureToSpeckle(layer, projectCRS, project)
            if b is not None: layerObjs.append(b)

            speckleLayer = RasterLayer(units = "m", type="RasterLayer")
            speckleLayer.name = layerName
            speckleLayer.crs = speckleReprojectedCrs
            speckleLayer.rasterCrs = layerCRS
            speckleLayer.type="RasterLayer"
            #speckleLayer.geomType="Raster"
            speckleLayer.features = layerObjs
            
            speckleLayer.renderer = rendererToSpeckle(project, project.activeMap, layer, b)
            
            #speckleLayer.renderer = layerRenderer
            #speckleLayer.applicationId = selectedLayer.id()
    except Exception as e:
        logToUser(str(e), level=2, func = inspect.stack()[0][3])

    return speckleLayer

def layerToNative(layer: Union[Layer, VectorLayer, RasterLayer], streamBranch: str) -> arcLayer:
    print("Layer to Native")
    try:
        project = arcpy.mp.ArcGISProject("CURRENT")

        sr = arcpy.SpatialReference().loadFromString(layer.crs.wkt)
        if layer.type is None:
            # Handle this case
            return
        elif layer.type.endswith("VectorLayer"):
            meshLayer = 0
            for f in layer.features:
                if meshLayer >0: break
                if isinstance (f["geometry"], Base):
                    try:
                        bound = f["geometry"].boundary # polygon found, default to receiving VectorLayer
                        break 
                    except: 
                        # skip the value if invalid
                        try: d = f["geometry"].displayValue
                        except: 
                            arcpy.AddError(f"Feature \"{f.id}\" skipped due to invalid geometry")
                            continue

                        for g in f["geometry"].displayValue:
                            if isinstance(g, Mesh):
                                try:
                                    bimLayerToNative(layer.features, layer.name, streamBranch, sr)
                                    meshLayer += 1
                                    break 
                                except: pass 
                elif isinstance (f["geometry"], List):
                    for v in f["geometry"]:
                        try:
                            bound = v.boundary # polygon found, default to receiving VectorLayer
                            break 
                        except: 
                            # skip the value if invalid
                            try: d = v.displayValue
                            except: 
                                arcpy.AddError(f"Feature \"{f.id}\" skipped due to invalid geometry")
                                continue

                            for g in v.displayValue:
                                if isinstance(g, Mesh):
                                    try:
                                        bimLayerToNative(layer.features, layer.name, streamBranch, sr)
                                        meshLayer += 1
                                        break 
                                    except: pass 
            if meshLayer==0:
                return vectorLayerToNative(layer, streamBranch, project)
        elif layer.type.endswith("RasterLayer"):
            return rasterLayerToNative(layer, streamBranch, project)
        return None
    except Exception as e:
        logToUser(str(e), level=2, func = inspect.stack()[0][3])
        return None 


def bimLayerToNative(layerContentList: List[Base], layerName: str, streamBranch: str, sr = None) :
    print("01______BIM layer to native")
    try:
        print(layerName)
        
        layerName = removeSpecialCharacters(layerName)

        project = ArcGISProject("CURRENT")
        geom_meshes = []
        layer_meshes = None
        #filter speckle objects by type within each layer, create sub-layer for each type (points, lines, polygons, mesh?)
        for geom_old in layerContentList:
            try: 
                geom: Base = geom_old["geometry"] # in case it was originally GIS layer
                fields_to_ignore = ["displayValue", "@displayValue", "displayMesh"]
                #print(geom_old.get_dynamic_member_names())
                for p in geom_old.get_dynamic_member_names():
                    if p not in fields_to_ignore:
                        geom[p] = geom_old[p]

            except: geom = geom_old

            if isinstance(geom, List): 
                for g in geom:
                    if g.speckle_type =='Objects.Geometry.Mesh':
                        geom_meshes.append(g)
                    else:
                        try: 
                            if g.displayValue: geom_meshes.append(g)
                        except:
                            try: 
                                if g["@displayValue"]: geom_meshes.append(g)
                            except: pass
                
            elif geom.speckle_type =='Objects.Geometry.Mesh':
                geom_meshes.append(geom)
            else:
                try: 
                    if geom.displayValue: geom_meshes.append(geom)
                except:
                    try: 
                        if geom["@displayValue"]: geom_meshes.append(geom)
                    except: pass

        if len(geom_meshes)>0: layer_meshes = bimVectorLayerToNative(geom_meshes, layerName, "Mesh", streamBranch, project, sr)

        return layer_meshes
    except Exception as e:
        logToUser(str(e), level=2, func = inspect.stack()[0][3])
        return False


def bimVectorLayerToNative(geomList: List[Base], layerName: str, geomType: str, streamBranch: str, project: ArcGISProject, sr = None): 
    # no support for mltipatches, maybe in 3.1: https://community.esri.com/t5/arcgis-pro-ideas/better-support-for-multipatches-in-arcpy/idi-p/953614/page/2#comments
    print("02_________BIM vector layer to native_____")
    try:
        #get Project CRS, use it by default for the new received layer
        
        vl = None
        
        layerName = removeSpecialCharacters(layerName)
        layerName = layerName + "_" + geomType
        #if not "__Structural_Foundations_Mesh" in layerName: return None
        
        active_map = project.activeMap
        if sr is None: sr = arcpy.SpatialReference(text = active_map.spatialReference.exportToString())
                
        if sr.type == "Geographic": 
            logToUser(f"Project CRS is set to Geographic type, and objects in linear units might not be received correctly", level=1, func = inspect.stack()[0][3])

        #CREATE A GROUP "received blabla" with sublayers
        layerGroup = None
        newGroupName = f'{streamBranch}'
        #print(newGroupName)
        for l in active_map.listLayers():
            if l.longName == newGroupName: layerGroup = l; break 
        
        #find ID of the layer with a matching name in the "latest" group 
        newName = f'{streamBranch.split("_")[len(streamBranch.split("_"))-1]}_{layerName}'
        print(newName)

        all_layer_names = []
        for l in project.activeMap.listLayers(): 
            if l.longName.startswith(newGroupName + "\\"):
                all_layer_names.append(l.longName)
        #print(all_layer_names)

        longName = streamBranch + "\\" + newName 
        newName = validateNewFclassName(newName, streamBranch + "\\", all_layer_names)


        path = project.filePath.replace("aprx","gdb") #

        p: str = os.path.expandvars(r'%LOCALAPPDATA%') + "\\Temp\\Speckle_ArcGIS_temp\\" + datetime.now().strftime("%Y-%m-%d %H-%M")
        #findOrCreatePath(p)
        path_bim = p + "\\Layers_Speckle\\BIM_layers\\" + streamBranch+ "\\" + newName + "\\" #arcpy.env.workspace + "\\" #
        findOrCreatePath(path_bim)
        print(path_bim)
        
        # particularly if the layer comes from ArcGIS
        if "mesh" in geomType.lower(): geomType = "Multipatch"

        #print("Create feature class (cad): ")
        # should be created inside the workspace to be a proper Feature class (not .shp) with Nullable Fields
        class_name = ("f_class_" + newName)
        #f_class = CreateFeatureclass(path, class_name, geomType, has_z="ENABLED", spatial_reference = sr)


        #shp = meshToNative(geomList, path_bim + newName)
        shp = writeMeshToShp(geomList, path_bim + newName)
        print("____ meshes saved___")
        #print(shp)

        
        cursor = arcpy.da.SearchCursor(shp, "Speckle_ID")
        class_shapes = [shp_id[0] for n, shp_id in enumerate(cursor)]
        del cursor 
        #print(class_shapes)
        #print(len(class_shapes))

        #print(path)
        #print(class_name)
        validated_class_path = validate_path(class_name)
        #print(validated_class_path)
        validated_class_name = validated_class_path.split("\\")[len(validated_class_path.split("\\"))-1]
        #print(validated_class_name)
        f_class = arcpy.conversion.FeatureClassToFeatureClass(shp, path, validated_class_name)
        # later replace with:
        # f_class = path + "\\" + validated_class_name
        # arcpy.conversion.ExportFeatures(shp, f_class)

        print(f_class)
        arcpy.management.DefineProjection(f_class, sr)
        #print(geomList)

        # get and set Layer attribute fields
        # example: https://resource.esriuk.com/blog/an-introductory-slice-of-arcpy-in-arcgis-pro/
        newFields = getLayerAttributes(geomList)
        
        fields_to_ignore = ["arcgisgeomfromspeckle", "shape", "objectid", "displayMesh"]
        matrix = []
        matrix_no_id = []
        all_keys = []
        all_key_types = []
        max_len = 52

        print("___ after layer attributes: ___________")
        #print(newFields.items())
        #try:
        for key, value in newFields.items(): 
            existingFields = [fl.name for fl in arcpy.ListFields(validated_class_name)]
            #print(existingFields)
            if key not in existingFields  and key.lower() not in fields_to_ignore: # exclude geometry and default existing fields
                #print(key)
                # signs that should not be used as field names and table names: https://support.esri.com/en/technical-article/000005588
                key = key.replace(" ","_").replace("-","_").replace("(","_").replace(")","_").replace(":","_").replace("\\","_").replace("/","_").replace("\"","_").replace("&","_").replace("@","_").replace("$","_").replace("%","_").replace("^","_") 
                if key[0] in ['0','1','2','3','4','5','6','7','8','9']: key = "_"+key
                if len(key)>max_len: key = key[:max_len]
                #print(all_keys)
                if key in all_keys:
                    for index, letter in enumerate('1234567890abcdefghijklmnopqrstuvwxyz'):
                        if len(key)<max_len and (key+letter) not in all_keys: key+=letter; break 
                        if len(key) == max_len and (key[:9] + letter) not in all_keys: key=key[:9] + letter; break 
                if key not in all_keys: 
                    all_keys.append(key)
                    all_key_types.append(value)
                    #print(all_keys)
                    if key.lower() =="speckle_id": 
                        matrix.append(["Speckle_ID", value, "Speckle_ID", 255])
                    else:
                        matrix.append([key, value, key, 255])
                        matrix_no_id.append([key, value, key, 255])
        #51.5019052°N  0.1076614°W 51.5020862°N  51.5019596,-0.1077379
        print(len(all_keys))
        #print(matrix)
        try:
            if len(matrix)>0: AddFields(str(f_class), matrix_no_id)
        except Exception as e: print(e)
        #print(matrix)
        
        fets = []
        fetIds = []
        fetColors = []
        rows_delete = []

        cursor = arcpy.da.SearchCursor(f_class, "Speckle_ID")
        class_shapes = [shp_id[0] for n, shp_id in enumerate(cursor)]
        del cursor 
        #print(class_shapes)
        print(len(class_shapes))
        print(len(geomList))
            
        print("_________BIM FeatureS To Native___________")
        for f in geomList[:]: 
            try:
                exist_feat = None
                shape_id = None
                n = None
                for n, shape_id in enumerate(class_shapes):
                    #print(shape_id[0])
                    if shape_id == f.id:
                        exist_feat = f
                        break
                
                
                if exist_feat is None: 
                    arcpy.AddError(f"Feature \"{shape_id}\" skipped due to invalid geometry")
                    print(shape_id)
                    rows_delete.append(n)
                    continue 

                new_feat = bimFeatureToNative(exist_feat, newFields, sr, path_bim)
                if new_feat is not None and new_feat != "": 
                    fetColors = findFeatColors(fetColors, f)

                    fets.append(new_feat)
                    fetIds.append(f.id)
                    #print(len(fets))
                else:
                    arcpy.AddError(f"Feature \"{shape_id}\" skipped due to invalid geometry")
                    
            except Exception as e: print(e)
        
        #print(len(geomList))
        print(rows_delete)
        cursor = arcpy.da.UpdateCursor(f_class, "Speckle_ID")
        for n, row in enumerate(cursor):
            if n in rows_delete: cursor.deleteRow()
        del cursor
        print(n)

        if len(fets) == 0: return None
        count = 0
        rowValues = []
        for i, feat in enumerate(fets):

            row = []
            heads = []
            for key in all_keys:
                try:
                    row.append(feat[key])
                    heads.append(key)
                except Exception as e: 
                    row.append(None)
                    heads.append(key)

            rowValues.append(row)
            count += 1
        print(heads)
        print(len(heads))
        
        if len(heads) > 0:
            with arcpy.da.UpdateCursor(f_class, heads) as cur:
                # For each row, evaluate the WELL_YIELD value (index position 
                # of 0), and update WELL_CLASS (index position of 1)
                shp_num = 0
                try:
                    for rowShape in cur: 
                        for i,r in enumerate(rowShape):
                            rowShape[i] = rowValues[shp_num][i]
                            if matrix[i][1] == 'TEXT' and rowShape[i] is not None: rowShape[i] = str(rowValues[shp_num][i]) 
                            if isinstance(rowValues[shp_num][i], str): # cut if string is too long
                                rowShape[i] = rowValues[shp_num][i][:255]
                        cur.updateRow(rowShape)
                        shp_num += 1
                except Exception as e: 
                    print("Layer attr error: " + str(e))
                    print(shp_num)
                    print(len(rowValues))
                    logToUser("Layer attribute error: " + e, level=2, func = inspect.stack()[0][3])
            del cur 
        
        print("create layer:")
        vl = MakeFeatureLayer(str(f_class), newName).getOutput(0)

        active_map.addLayerToGroup(layerGroup, vl)
        print("created2")
        
        vl2 = None
        print(newName)
        for l in project.activeMap.listLayers(): 
            if l.longName == layerGroup.longName + "\\" + newName:
                vl2 = l 
                break

        path_lyr = cadBimRendererToNative(project, active_map, layerGroup, fetColors, vl2, f_class, heads)
        
        #os.remove(path_bim)

        return vl2 #last one
    except Exception as e:
        logToUser(str(e), level=2, func = inspect.stack()[0][3])
        return False

def cadLayerToNative(layerContentList: List[Base], layerName: str, streamBranch: str) :
    print("01______Cad vector layer to native")
    layer_points = []
    layer_polylines = []
    try:
        geom_points = []
        geom_polylines = []
        project = ArcGISProject("CURRENT")
        print(layerName)
        geom_polygones = []
        geom_meshes = []
        #filter speckle objects by type within each layer, create sub-layer for each type (points, lines, polygons, mesh?)
        print(layerContentList)
        for geom in layerContentList:
            #print(geom)
            if geom.speckle_type == "Objects.Geometry.Point": 
                geom_points.append(geom)
            elif geom.speckle_type in GEOM_LINE_TYPES:
                geom_polylines.append(geom)
            try:
                if geom.speckle_type.endswith(".ModelCurve") and geom["baseCurve"].speckle_type in GEOM_LINE_TYPES:
                    geom_polylines.append(geom["baseCurve"])
            except: pass
        
        if len(geom_points)>0: layer_points = cadVectorLayerToNative(geom_points, layerName, "Points", streamBranch, project)
        if len(geom_polylines)>0: layer_polylines = cadVectorLayerToNative(geom_polylines, layerName, "Polylines", streamBranch, project)
    except Exception as e:
        logToUser(str(e), level=2, func = inspect.stack()[0][3])

    return [layer_points, layer_polylines]

def cadVectorLayerToNative(geomList, layerName: str, geomType: str, streamBranch: str, project: ArcGISProject): 
    print("02_________CAD vector layer to native_____")
    vl = None
    try:
        #get Project CRS, use it by default for the new received layer
        layerName = removeSpecialCharacters(layerName)
        layerName = layerName + "_" + geomType
        print(layerName)
        
        sr = arcpy.SpatialReference(text = project.activeMap.spatialReference.exportToString())
        active_map = project.activeMap
        path = project.filePath.replace("aprx","gdb") #"\\".join(project.filePath.split("\\")[:-1]) + "\\speckle_layers\\" #arcpy.env.workspace + "\\" #
        
        print(path)
        print(streamBranch)
        if sr.type == "Geographic": 
            logToUser(f"Project CRS is set to Geographic type, and objects in linear units might not be received correctly", level=1, func = inspect.stack()[0][3])

        #CREATE A GROUP "received blabla" with sublayers
        layerGroup = None
        newGroupName = f'{streamBranch}'
        print(newGroupName)
        #print(newGroupName)
        for l in active_map.listLayers():
            if l.longName == newGroupName: layerGroup = l; break 
        
        #find ID of the layer with a matching name in the "latest" group 
        newName = f'{streamBranch.split("_")[len(streamBranch.split("_"))-1]}_{layerName}'

        all_layer_names = []
        for l in project.activeMap.listLayers(): 
            if l.longName.startswith(newGroupName + "\\"):
                all_layer_names.append(l.longName)
        #print(all_layer_names)

        longName = streamBranch + "\\" + newName 
        newName = validateNewFclassName(newName, streamBranch + "\\", all_layer_names)

        # particularly if the layer comes from ArcGIS
        if "polygon" in geomType.lower(): geomType = "Polygon"
        elif "line" in geomType.lower(): geomType = "Polyline"
        elif "multipoint" in geomType.lower(): geomType = "Multipoint"
        elif "point" in geomType.lower(): geomType = "Point"
        #print(geomType)
        
        #print(newName)
        #path = r"C:\Users\username\Documents\ArcGIS\Projects\MyProject-test\MyProject-test.gdb\\"
        #https://community.esri.com/t5/arcgis-pro-questions/is-it-possible-to-create-a-new-group-layer-with/td-p/1068607

        #print("Create feature class (cad): ")
        # should be created inside the workspace to be a proper Feature class (not .shp) with Nullable Fields
        class_name = ("f_class_" + newName)
        f_class = CreateFeatureclass(path, class_name, geomType, has_z="ENABLED", spatial_reference = sr)
        print(f_class)
        #print(geomList)
        print(f_class)
        arcpy.management.DefineProjection(f_class, sr)

        # get and set Layer attribute fields
        # example: https://resource.esriuk.com/blog/an-introductory-slice-of-arcpy-in-arcgis-pro/
        newFields = getLayerAttributes(geomList)
        
        fields_to_ignore = ["arcgisgeomfromspeckle", "shape", "objectid"]
        matrix = []
        all_keys = []
        all_key_types = []
        max_len = 52
        for key, value in newFields.items(): 
            existingFields = [fl.name for fl in arcpy.ListFields(class_name)]
            if key not in existingFields  and key.lower() not in fields_to_ignore: # exclude geometry and default existing fields
                # signs that should not be used as field names and table names: https://support.esri.com/en/technical-article/000005588
                key = key.replace(" ","_").replace("-","_").replace("(","_").replace(")","_").replace(":","_").replace("\\","_").replace("/","_").replace("\"","_").replace("&","_").replace("@","_").replace("$","_").replace("%","_").replace("^","_") 
                if key[0] in ['0','1','2','3','4','5','6','7','8','9']: key = "_"+key
                if len(key)>max_len: key = key[:max_len]
                #print(all_keys)
                if key in all_keys:
                    for index, letter in enumerate('1234567890abcdefghijklmnopqrstuvwxyz'):
                        if len(key)<max_len and (key+letter) not in all_keys: key+=letter; break 
                        if len(key) == max_len and (key[:9] + letter) not in all_keys: key=key[:9] + letter; break 
                if key not in all_keys: 
                    all_keys.append(key)
                    all_key_types.append(value)
                    #print(all_keys)
                    matrix.append([key, value, key, 255])
                    #print(matrix)
        if len(matrix)>0: AddFields(str(f_class), matrix)

        fets = []
        fetColors = []
        for f in geomList[:]: 
            new_feat = cadFeatureToNative(f, newFields, sr)
            if new_feat != "" and new_feat != None: 
                fetColors = findFeatColors(fetColors, f)
                fets.append(new_feat)
            else:
                arcpy.AddError(f"Feature skipped due to invalid geometry")
        print("features created")
        print(len(fets))
        print(all_keys)
        
        if len(fets) == 0: return None
        count = 0
        rowValues = []
        for feat in fets:
            try: feat['applicationId'] 
            except: feat.update({'applicationId': count})

            row = [feat['arcGisGeomFromSpeckle'], feat['applicationId']]
            heads = [ 'Shape@', 'OBJECTID']

            for key,value in feat.items(): 
                #print(key, str(value))
                if key in all_keys and key.lower() not in fields_to_ignore: 
                    heads.append(key)
                    row.append(value)
            rowValues.append(row)
            count += 1
        cur = arcpy.da.InsertCursor(str(f_class), tuple(heads) )
        #print(heads)
        for row in rowValues: 
            try:
                #print(row)
                cur.insertRow(tuple(row))
            except Exception as e:
                print(e)
        del cur 
        vl = MakeFeatureLayer(str(f_class), newName).getOutput(0)

        #adding layers from code solved: https://gis.stackexchange.com/questions/344343/arcpy-makefeaturelayer-management-function-not-creating-feature-layer-in-arcgis
        #active_map.addLayer(new_layer)
        active_map.addLayerToGroup(layerGroup, vl)
        print("Layer created")

        vl2 = None
        print(newName)
        for l in project.activeMap.listLayers(): 
            if l.longName == layerGroup.longName + "\\" + newName:
                vl2 = l 
                break
        path_lyr = cadBimRendererToNative(project, active_map, layerGroup, fetColors, vl2, f_class, heads)

    except Exception as e:
        logToUser(str(e), level=2, func = inspect.stack()[0][3])

    return vl

def vectorLayerToNative(layer: Union[Layer, VectorLayer], streamBranch: str, project: ArcGISProject):
    print("_________Vector Layer to Native_________")
    vl = None
    try:
        layerName = removeSpecialCharacters(layer.name)

        print(layerName)
        sr = arcpy.SpatialReference(text=layer.crs.wkt) 
        active_map = project.activeMap
        path = project.filePath.replace("aprx","gdb") #"\\".join(project.filePath.split("\\")[:-1]) + "\\speckle_layers\\" #arcpy.env.workspace + "\\" #
        #if not os.path.exists(path): os.makedirs(path)
        #print(path) 

        newName, layerGroup = newLayerGroupAndName(layerName, streamBranch, project)

        # particularly if the layer comes from ArcGIS
        geomType = layer.geomType # for ArcGIS: Polygon, Point, Polyline, Multipoint, MultiPatch
        print(geomType)
        if "polygon" in geomType.lower(): geomType = "Polygon"
        if "line" in geomType.lower(): geomType = "Polyline"
        if "multipoint" in geomType.lower(): geomType = "Multipoint"
        elif "point" in geomType.lower(): geomType = "Point"
        #print(geomType)
        
        #print(newName)
        #path = r"C:\Users\username\Documents\ArcGIS\Projects\MyProject-test\MyProject-test.gdb\\"
        #https://community.esri.com/t5/arcgis-pro-questions/is-it-possible-to-create-a-new-group-layer-with/td-p/1068607
        #print(project.filePath.replace("aprx","gdb"))
        #print("_________create feature class___________________________________")
        # should be created inside the workspace to be a proper Feature class (not .shp) with Nullable Fields
        class_name = "f_class_" + newName
        #print(class_name)
        try: f_class = CreateFeatureclass(path, class_name, geomType, has_z="ENABLED", spatial_reference = sr)
        except arcgisscripting.ExecuteError: class_name+="_"; f_class = CreateFeatureclass(path, class_name, geomType, has_z="ENABLED", spatial_reference = sr)

        # get and set Layer attribute fields
        # example: https://resource.esriuk.com/blog/an-introductory-slice-of-arcpy-in-arcgis-pro/
        newFields = getLayerAttributes(layer.features)
        fields_to_ignore = ["arcgisgeomfromspeckle", "shape", "objectid"]
        matrix = []
        all_keys = []
        all_key_types = []
        max_len = 52
        for key, value in newFields.items(): 
            existingFields = [fl.name for fl in arcpy.ListFields(class_name)]
            if key not in existingFields  and key.lower() not in fields_to_ignore: # exclude geometry and default existing fields
                # signs that should not be used as field names and table names: https://support.esri.com/en/technical-article/000005588
                key = key.replace(" ","_").replace("-","_").replace("(","_").replace(")","_").replace(":","_").replace("\\","_").replace("/","_").replace("\"","_").replace("&","_").replace("@","_").replace("$","_").replace("%","_").replace("^","_") 
                if key[0] in ['0','1','2','3','4','5','6','7','8','9']: key = "_"+key
                if len(key)>max_len: key = key[:max_len]
                #print(all_keys)
                if key in all_keys:
                    for index, letter in enumerate('1234567890abcdefghijklmnopqrstuvwxyz'):
                        if len(key)<max_len and (key+letter) not in all_keys: key+=letter; break 
                        if len(key) == max_len and (key[:9] + letter) not in all_keys: key=key[:9] + letter; break 
                if key not in all_keys: 
                    all_keys.append(key)
                    all_key_types.append(value)
                    #print(all_keys)
                    matrix.append([key, value, key, 255])
                    #print(matrix)
        if len(matrix)>0: AddFields(str(f_class), matrix)

        fets = []
        for f in layer.features: 
            new_feat = featureToNative(f, newFields, geomType, sr)
            if new_feat != "" and new_feat!= None: fets.append(new_feat)
            else: arcpy.AddError(f"Feature skipped due to invalid geometry")
        
        #print(fets)
        if len(fets) == 0: return None
        count = 0
        rowValues = []
        heads = None
        for feat in fets:
            #print(feat)
            try: feat['applicationId'] 
            except: feat.update({'applicationId': count})

            row = [feat['arcGisGeomFromSpeckle'], feat['applicationId']]
            heads = [ 'Shape@', 'OBJECTID']

            for key,value in feat.items(): 
                if key in all_keys and key.lower() not in fields_to_ignore: 
                    heads.append(key)
                    row.append(value)
            rowValues.append(row)
            count += 1
        cur = arcpy.da.InsertCursor(str(f_class), tuple(heads) )
        for row in rowValues: 
            #print(tuple(heads))
            #print(tuple(row))
            cur.insertRow(tuple(row))
        del cur 

        vl = MakeFeatureLayer(str(f_class), newName).getOutput(0)

        #adding layers from code solved: https://gis.stackexchange.com/questions/344343/arcpy-makefeaturelayer-management-function-not-creating-feature-layer-in-arcgis
        
        active_map.addLayerToGroup(layerGroup, vl)
        vl2 = None
        print(newName)
        for l in project.activeMap.listLayers(): 
            #print(l.longName)
            if l.longName == layerGroup.longName + "\\" + newName:
                vl2 = l 
                break
        path_lyr = vectorRendererToNative(project, active_map, layerGroup, layer, vl2, f_class, heads)
        #if path_lyr is not None: 
        #    active_map.removeLayer(path_lyr)    

        r'''
        # rename back the layer if was renamed due to existing duplicate
        if layerExists:  
            vl.name = newName[:len(newName)-2]
            for lyr in project.activeMap.listLayers():
                print(lyr.longName)
                if (streamBranch + "\\" + newName) == lyr.longName: 
                    lyr.name = lyr.name.replace( lyr.name, lyr.name[:len(lyr.name)-2] )
                    lyr.longName = lyr.longName.replace( lyr.longName, lyr.longName[:len(newName)-2] )
                    break
        '''

        r'''
        pr.addFeatures(fets)
        vl.updateExtents()
        vl.commitChanges()
        #layerGroup.addLayer(vl)

        rendererNew = vectorRendererToNative(layer)
        if rendererNew is None:
            symbol = QgsSymbol.defaultSymbol(QgsWkbTypes.geometryType(QgsWkbTypes.parseType(geomType)))
            rendererNew = QgsSingleSymbolRenderer(symbol)

        try: vl.setRenderer(rendererNew)
        except: pass
        '''
    except Exception as e:
        logToUser(str(e), level=2, func = inspect.stack()[0][3])
    return vl

def rasterLayerToNative(layer: RasterLayer, streamBranch: str, project: ArcGISProject):

    rasterLayer = None
    try:

        layerName = removeSpecialCharacters(layer.name) + "_Speckle"

        print(layerName)
        sr = arcpy.SpatialReference(text=layer.crs.wkt) 
        print(layer.crs.wkt)
        active_map = project.activeMap
        path = project.filePath.replace("aprx","gdb")
        #path = '.'.join(path.split("\\")[:-1])
        rasterHasSr = False
        print(path)

        p: str = os.path.expandvars(r'%LOCALAPPDATA%') + "\\Temp\\Speckle_ArcGIS_temp\\" + datetime.now().strftime("%Y-%m-%d %H-%M")
        #findOrCreatePath(p)
        path_bands = p + "\\Layers_Speckle\\raster_bands\\" + streamBranch 
        findOrCreatePath(path_bands)

        try: 
            srRasterWkt = str(layer.rasterCrs.wkt)
            print(layer.rasterCrs.wkt)
            srRaster = arcpy.SpatialReference(text=srRasterWkt) # by native raster SR
            rasterHasSr = True
        except: 
            srRasterWkt = str(layer.crs.wkt)
            srRaster: arcpy.SpatialReference = sr # by layer
        #print(layer.rasterCrs.wkt)
        print(srRaster)

        newName, layerGroup = newLayerGroupAndName(layerName, streamBranch, project)
        print(newName)
        if "." in newName: newName = '.'.join(newName.split(".")[:-1])
        print(newName)
        
        feat = layer.features[0]
        bandNames = feat["Band names"]
        bandValues = [feat["@(10000)" + name + "_values"] for name in bandNames]

        xsize= int(feat["X pixels"])
        ysize= int(feat["Y pixels"])
        xres = float(feat["X resolution"])
        yres = float(feat["Y resolution"])
        bandsCount=int(feat["Band count"])
        originPt = arcpy.Point(feat['displayValue'][0].x, feat['displayValue'][0].y, feat['displayValue'][0].z)
        print(originPt)
        #if source projection is different from layer display projection, convert display OriginPt to raster source projection 
        if rasterHasSr is True and srRaster.exportToString() != sr.exportToString():
            originPt = findTransformation(arcpy.PointGeometry(originPt, sr, has_z = True), "Point", sr, srRaster, None).getPart()
        print(originPt)

        bandDatasets = ""
        rastersToMerge = []
        rasterPathsToMerge = []


        arcpy.env.workspace = path 
        arcpy.env.overwriteOutput = True
        # https://pro.arcgis.com/en/pro-app/latest/tool-reference/data-management/composite-bands.htm
        
        
        for i in range(bandsCount):
            print(i)
            print(bandNames[i])
            rasterbandPath = path_bands + "\\" + newName + "_Band_" + str(i+1) + ".tif"
            bandDatasets += rasterbandPath + ";"
            rasterband = np.array(bandValues[i])
            rasterband = np.reshape(rasterband,(ysize, xsize))
            print(rasterband)
            print(np.shape(rasterband))
            print(xsize)
            print(xres)
            print(ysize)
            print(yres)
            leftLowerCorner = arcpy.Point(originPt.X, originPt.Y + (ysize*yres), originPt.Z)
            #upperRightCorner = arcpy.Point(originPt.X + (xsize*xres), originPt.Y, originPt.Z)
            print(leftLowerCorner)
            #print(upperRightCorner)

            # # Convert array to a geodatabase raster, add to layers 
            try: myRaster = arcpy.NumPyArrayToRaster(rasterband, leftLowerCorner, abs(xres), abs(yres), float(feat["NoDataVal"][i]) ) 
            except: myRaster = arcpy.NumPyArrayToRaster(rasterband, leftLowerCorner, abs(xres), abs(yres)) 

            rasterbandPath = validate_path(rasterbandPath) #solved file saving issue 
            print(rasterbandPath)
            #mergedRaster = arcpy.ia.Merge(rastersToMerge) # glues all bands together
            myRaster.save(rasterbandPath)

            print(myRaster.width)
            print(myRaster.height)

            rastersToMerge.append(myRaster)
            rasterPathsToMerge.append(rasterbandPath)
            print(rasterbandPath)

        #mergedRaster.setProperty("spatialReference", crsRaster)

        full_path = validate_path(path + "\\" + newName) #solved file saving issue 
        print("RASTER FULL PATH")
        print(full_path)
        if os.path.exists(full_path):
            #print(full_path)
            for index, letter in enumerate('1234567890abcdefghijklmnopqrstuvwxyz'):
                print(full_path + letter)
                if os.path.exists(full_path + letter): pass
                else: full_path += letter; break 
        print("RASTER new PATH")
        print(full_path)
        #mergedRaster = arcpy.ia.Merge(rastersToMerge) # glues all bands together
        #mergedRaster.save(full_path) # similar errors: https://community.esri.com/t5/python-questions/error-010240-could-not-save-raster-dataset/td-p/321690
        
        try: 
            arcpy.management.CompositeBands(rasterPathsToMerge, full_path)
        except: # if already exists
            full_path += "_"
            arcpy.management.CompositeBands(rasterPathsToMerge, full_path)
        print(path + "\\" + newName)
        arcpy.management.DefineProjection(full_path, srRaster)

        rasterLayer = arcpy.management.MakeRasterLayer(full_path, newName).getOutput(0)
        print(layerGroup)
        active_map.addLayerToGroup(layerGroup, rasterLayer)

        rl2 = None
        for l in active_map.listLayers(): 
            if l.longName == layerGroup.longName + "\\" + newName:
                print(l.longName)
                rl2 = l 
                break
        rasterLayer = rasterRendererToNative(project, active_map, layerGroup, layer, rl2, rasterPathsToMerge, newName)

        try: os.remove(path_bands)
        except: pass

        r'''
        if arcpy.Exists(fileout):
            arcpy.management.Delete(fileout)
        arcpy.management.Rename(filelist[0], fileout)

        # Remove temporary files
        for fileitem in filelist:
            if arcpy.Exists(fileitem):
                arcpy.management.Delete(fileitem)

        # Release raster objects from memory
        del myRasterBlock
        del myRaster
        '''

        r'''
        rasterComposite = arcpy.management.CompositeBands(bandDatasets, path + "\\" + newName) # "band1.tif;band2.tif;band3.tif", "compbands.tif"
        
        # https://pro.arcgis.com/en/pro-app/latest/tool-reference/data-management/make-raster-layer.htm
        rasterLayer = arcpy.MakeRasterLayer_management(rasterComposite, newName)
        '''

        
        r'''
        # WORKS: 
        arcpy.CreateRasterDataset_management(r"C:\Users\Kateryna\Documents\ArcGIS\Projects\MyProject-test",
        "EmptyTIFF.tif",
        "2",
        "8_BIT_UNSIGNED",
        "PROJCS['DHDN_3_Degree_Gauss_Zone_3',GEOGCS['GCS_Deutsches_Hauptdreiecksnetz',DATUM['D_Deutsches_Hauptdreiecksnetz',SPHEROID['Bessel_1841',6377397.155,299.1528128]],PRIMEM['Greenwich',0.0],UNIT['Degree',0.0174532925199433]],PROJECTION['Gauss_Kruger'],PARAMETER['False_Easting',3500000.0],PARAMETER['False_Northing',0.0],PARAMETER['Central_Meridian',9.0],PARAMETER['Scale_Factor',1.0],PARAMETER['Latitude_Of_Origin',0.0],UNIT['Meter',1.0]]", "3", "", "PYRAMIDS -1 NEAREST JPEG", "128 128", "NONE", "")
        '''

    except Exception as e:
        logToUser(str(e), level=2, func = inspect.stack()[0][3])
    return rasterLayer
