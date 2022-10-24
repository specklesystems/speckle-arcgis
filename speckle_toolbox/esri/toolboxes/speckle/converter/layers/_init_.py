"""
Contains all Layer related classes and methods.
"""
import os
from typing import Any, List, Tuple, Union

from regex import D
from speckle.converter.layers.CRS import CRS
from speckle.converter.layers.Layer import Layer, VectorLayer, RasterLayer
from speckle.converter.layers.feature import featureToNative, featureToSpeckle, cadFeatureToNative, rasterFeatureToSpeckle
from specklepy.objects import Base

import arcgisscripting
import pandas as pd
import arcpy
from arcpy._mp import ArcGISProject, Map, Layer as arcLayer
from arcpy.management import (CreateFeatureclass, MakeFeatureLayer,
                              AddFields, AlterField, DefineProjection )

from speckle.converter.layers.utils import getLayerAttributes, newLayerGroupAndName, validate_path
import numpy as np


def convertSelectedLayers(all_layers: List[arcLayer], selected_layers: List[str], project: ArcGISProject) -> List[Union[VectorLayer,Layer]]:
    """Converts the current selected layers to Speckle"""
    print("________Convert Layers_________")
    result = []
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
            if newBaseLayer is not None: result.append(newBaseLayer)

            elif layerToSend.isRasterLayer: pass

    return result

def layerToSpeckle(layer: arcLayer, project: ArcGISProject) -> Union[VectorLayer, RasterLayer]: #now the input is QgsVectorLayer instead of qgis._core.QgsLayerTreeLayer
    """Converts a given QGIS Layer to Speckle"""
    print("________Convert Feature Layer_________")

    speckleLayer = None

    projectCRS = project.activeMap.spatialReference
    try: data = arcpy.Describe(layer.dataSource)
    except OSError as e: arcpy.AddWarning(str(e.args[0])); return

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
        #speckleLayer.datum = datum


        try: # https://pro.arcgis.com/en/pro-app/2.8/arcpy/get-started/the-spatial-reference-object.htm
            
            #print(data.datasetType) # FeatureClass
            if data.datasetType == "FeatureClass": #FeatureClass, ?Table Properties, ?Datasets
                
                # write feature attributes
                fieldnames = [field.name for field in data.fields]
                rows_shapes = arcpy.da.SearchCursor(layer.longName, "Shape@") # arcpy.da.SearchCursor(in_table, field_names, {where_clause}, {spatial_reference}, {explode_to_points}, {sql_clause})
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
                        print(feat)
                        rows_attributes = arcpy.da.SearchCursor(layer.longName, fieldnames)
                        row_attr = []
                        for k, attrs in enumerate(rows_attributes):
                            if i == k: row_attr = attrs; break

                        # if curves detected, createa new feature class, turn to segments and get the same feature but in straigt lines
                        #print(feat.hasCurves)
                        if feat.hasCurves:
                            #f_class_modified = curvedFeatureClassToSegments(layer)
                            #rows_shapes_modified = arcpy.da.SearchCursor(f_class_modified, "Shape@") 
                            #row_shapes_list_modified = [x for k, x in enumerate(rows_shapes_modified)]

                            feat = feat.densify("ANGLE", 1000, 0.12)
                            #print(feat)


                        b = featureToSpeckle(fieldnames, row_attr, feat, projectCRS, project, layer)
                        if b is not None: layerObjs.append(b)
                        
                    print("____End of Feature # " + str(i+1))
                    
                print("__ finish iterating features")
                speckleLayer.features=layerObjs
                speckleLayer.geomType = data.shapeType

                #layerBase.renderer = layerRenderer
                #layerBase.applicationId = selectedLayer.id()

        except OSError as e: 
            arcpy.AddWarning(str(e))
            return

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
        
        #speckleLayer.renderer = layerRenderer
        #speckleLayer.applicationId = selectedLayer.id()

    return speckleLayer

def layerToNative(layer: Union[Layer, VectorLayer, RasterLayer], streamBranch: str, project: ArcGISProject):

    if layer.type is None:
        # Handle this case
        return
    elif layer.type.endswith("VectorLayer"):
        return vectorLayerToNative(layer, streamBranch, project)
    elif layer.type.endswith("RasterLayer"):
        return rasterLayerToNative(layer, streamBranch, project)
    return None

def cadLayerToNative(layerContentList:Base, layerName: str, streamBranch: str, project: ArcGISProject) :
    print("01______Cad vector layer to native")
    print(layerName)
    geom_points = []
    geom_polylines = []
    geom_polygones = []
    geom_meshes = []
    #filter speckle objects by type within each layer, create sub-layer for each type (points, lines, polygons, mesh?)
    for geom in layerContentList:
        #print(geom)
        if geom.speckle_type == "Objects.Geometry.Point": 
            geom_points.append(geom)
        if geom.speckle_type == "Objects.Geometry.Line" or geom.speckle_type == "Objects.Geometry.Polyline" or geom.speckle_type == "Objects.Geometry.Curve" or geom.speckle_type == "Objects.Geometry.Arc" or geom.speckle_type == "Objects.Geometry.Circle" or geom.speckle_type == "Objects.Geometry.Ellipse" or geom.speckle_type == "Objects.Geometry.Polycurve":
            geom_polylines.append(geom)
    
    if len(geom_points)>0: layer_points = cadVectorLayerToNative(geom_points, layerName, "Points", streamBranch, project)
    if len(geom_polylines)>0: layer_polylines = cadVectorLayerToNative(geom_polylines, layerName, "Polylines", streamBranch, project)

    return [layer_points, layer_polylines]

def cadVectorLayerToNative(geomList, layerName: str, geomType: str, streamBranch: str, project: ArcGISProject): 
    print("02_________CAD vector layer to native_____")
    #get Project CRS, use it by default for the new received layer
    vl = None
    layerName = layerName.replace("[","_").replace("]","_").replace(" ","_").replace("-","_").replace("(","_").replace(")","_").replace(":","_").replace("\\","_").replace("/","_").replace("\"","_").replace("&","_").replace("@","_").replace("$","_").replace("%","_").replace("^","_")
    layerName = layerName + "_" + geomType
    
    sr = arcpy.SpatialReference(project.activeMap.spatialReference.name)
    active_map = project.activeMap
    path = project.filePath.replace("aprx","gdb") #"\\".join(project.filePath.split("\\")[:-1]) + "\\speckle_layers\\" #arcpy.env.workspace + "\\" #
    
    if sr.type == "Geographic": 
        arcpy.AddMessage(f"Project CRS is set to Geographic type, and objects in linear units might not be received correctly")

    #CREATE A GROUP "received blabla" with sublayers
    layerGroup = None
    newGroupName = f'{streamBranch}'
    #print(newGroupName)
    for l in active_map.listLayers():
        if l.longName == newGroupName: layerGroup = l; break 
    
    #find ID of the layer with a matching name in the "latest" group 
    newName = f'{streamBranch.split("_")[len(streamBranch.split("_"))-1]}_{layerName}'

    all_layer_names = []
    layerExists = 0
    for l in project.activeMap.listLayers(): 
        if l.longName.startswith(newGroupName + "\\"):
            all_layer_names.append(l.longName)
    #print(all_layer_names)

    longName = streamBranch + "\\" + newName 
    if longName in all_layer_names: 
        for index, letter in enumerate('234567890abcdefghijklmnopqrstuvwxyz'):
            if (longName + "_" + letter) not in all_layer_names: newName += "_"+letter; layerExists +=1; break 

    # particularly if the layer comes from ArcGIS
    if "polygon" in geomType.lower(): geomType = "Polygon"
    if "line" in geomType.lower(): geomType = "Polyline"
    if "multipoint" in geomType.lower(): geomType = "Multipoint"
    elif "point" in geomType.lower(): geomType = "Point"
    #print(geomType)
    
    #print(newName)
    #path = r"C:\Users\username\Documents\ArcGIS\Projects\MyProject-test\MyProject-test.gdb\\"
    #https://community.esri.com/t5/arcgis-pro-questions/is-it-possible-to-create-a-new-group-layer-with/td-p/1068607

    #print("Create feature class (cad): ")
    # should be created inside the workspace to be a proper Feature class (not .shp) with Nullable Fields
    class_name = ("f_class_" + newName)
    f_class = CreateFeatureclass(path, class_name, geomType, has_z="ENABLED", spatial_reference = sr)
    #print(f_class)
    #print(geomList)

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
    for f in geomList[:]: 
        new_feat = cadFeatureToNative(f, newFields, sr)
        if new_feat != "" and new_feat != None: 
            fets.append(new_feat)
    #print("features created")
    #print(fets)
    
    if len(fets) == 0: return None
    count = 0
    rowValues = []
    for feat in fets:
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
    #print(heads)
    cur = arcpy.da.InsertCursor(str(f_class), tuple(heads) )
    for row in rowValues: 
        #print(tuple(heads))
        #print(tuple(row))
        cur.insertRow(tuple(row))
    del cur 
    #print(f_class)
    vl = MakeFeatureLayer(str(f_class), newName).getOutput(0)

    #adding layers from code solved: https://gis.stackexchange.com/questions/344343/arcpy-makefeaturelayer-management-function-not-creating-feature-layer-in-arcgis
    #active_map.addLayer(new_layer)
    active_map.addLayerToGroup(layerGroup, vl)

    return vl

def vectorLayerToNative(layer: Union[Layer, VectorLayer], streamBranch: str, project: ArcGISProject):
    print("_________Vector Layer to Native_________")
    vl = None
    layerName = layer.name.replace(" ","_").replace("-","_").replace("(","_").replace(")","_").replace(":","_").replace("\\","_").replace("/","_").replace("\"","_").replace("&","_").replace("@","_").replace("$","_").replace("%","_").replace("^","_")
    
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
    
    print(fets)
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
        print(tuple(heads))
        print(tuple(row))
        cur.insertRow(tuple(row))
    del cur 

    vl = MakeFeatureLayer(str(f_class), newName).getOutput(0)

    #adding layers from code solved: https://gis.stackexchange.com/questions/344343/arcpy-makefeaturelayer-management-function-not-creating-feature-layer-in-arcgis
    #active_map.addLayer(new_layer)
    active_map.addLayerToGroup(layerGroup, vl)
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
    return vl

def rasterLayerToNative(layer: RasterLayer, streamBranch: str, project: ArcGISProject):

    rasterLayer = None

    layerName = layer.name.replace(" ","_").replace("-","_").replace("(","_").replace(")","_").replace(":","_").replace("\\","_").replace("/","_").replace("\"","_").replace("&","_").replace("@","_").replace("$","_").replace("%","_").replace("^","_")
    
    print(layerName)
    sr = arcpy.SpatialReference(text=layer.crs.wkt) 
    print(layer.crs.wkt)
    active_map = project.activeMap
    path = project.filePath.replace("aprx","gdb")
    #path = '.'.join(path.split("\\")[:-1])
    print(path)

    try: 
        crsRasterWkt = str(layer.rasterCrs.wkt)
        print(layer.rasterCrs.wkt)
        crsRaster = arcpy.SpatialReference(text=crsRasterWkt) # by native raster SR
    except: 
        crsRasterWkt = str(layer.crs.wkt)
        crsRaster: arcpy.SpatialReference = sr # by layer
    print(layer.rasterCrs.wkt)
    print(crsRaster)

    newName, layerGroup = newLayerGroupAndName(layerName, streamBranch, project)
    print(newName)
    if "." in newName: newName = '.'.join(newName.split(".")[:-1])
    print(newName)
    
    feat = layer.features[0]
    bandNames = feat["Band names"]
    bandValues = [feat["@(10000)" + name + "_values"] for name in bandNames]

    xsize= int(feat["X pixels"])
    ysize= int(feat["Y pixels"])
    bandsCount=int(feat["Band count"])
    originPt = arcpy.Point(feat['displayValue'][0].x, feat['displayValue'][0].y, feat['displayValue'][0].z)

    bandDatasets = ""
    rastersToMerge = []

    arcpy.env.workspace = path 
    arcpy.env.overwriteOutput = True
    # https://pro.arcgis.com/en/pro-app/latest/tool-reference/data-management/composite-bands.htm
    
    
    for i in range(bandsCount):
        print(i)
        print(bandNames[i])
        rasterbandPath = path + "\\" + newName + "_Band_" + str(i+1) #+ ".tif"
        bandDatasets += rasterbandPath + ";"
        rasterband = np.array(bandValues[i])
        rasterband = np.reshape(rasterband,(xsize, ysize))
        print(rasterband)
        leftLowerCorner = arcpy.Point(originPt.X, originPt.Y - (ysize*feat["Y pixels"]), originPt.Z)
        upperRightCorner = arcpy.Point(originPt.X + (xsize*feat["X pixels"]), originPt.Y, originPt.Z)
        print(leftLowerCorner)
        print(xsize)
        print(ysize)

        # # Convert array to a geodatabase raster, add to layers 
        try: myRaster = arcpy.NumPyArrayToRaster(rasterband, leftLowerCorner, xsize, ysize, float(feat["NoDataVal"][i]) ) 
        except: myRaster = arcpy.NumPyArrayToRaster(rasterband, leftLowerCorner, xsize, ysize) 
        #print(myRaster)

        myRaster.setProperty("spatialReference", crsRaster)
        rastersToMerge.append(myRaster)
        print(rasterbandPath)

    mergedRaster = arcpy.ia.Merge(rastersToMerge)
    print(path + "\\" + newName)

    #mergedRaster.setProperty("spatialReference", crsRaster)

    full_path = validate_path(path + "\\" + newName) #solved file saving issue 
    print(full_path)
    mergedRaster.save(full_path) # similar errors: https://community.esri.com/t5/python-questions/error-010240-could-not-save-raster-dataset/td-p/321690
    
    arcpy.management.DefineProjection(full_path, crsRaster)

    rasterLayer = arcpy.management.MakeRasterLayer(full_path, newName + "_").getOutput(0)
    print(layerGroup)
    active_map.addLayerToGroup(layerGroup, rasterLayer)

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

    return rasterLayer
