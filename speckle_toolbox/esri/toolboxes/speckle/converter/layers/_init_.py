"""
Contains all Layer related classes and methods.
"""
import os
from typing import Any, List, Union

from regex import D
from speckle.converter.layers.CRS import CRS
from speckle.converter.layers.Layer import Layer, RasterLayer
from speckle.converter.layers.feature import featureToNative, featureToSpeckle, cadFeatureToNative
from specklepy.objects import Base

import arcgisscripting
import pandas as pd
import arcpy
from arcpy._mp import ArcGISProject, Map, Layer as arcLayer
from arcpy.management import (CreateFeatureclass, MakeFeatureLayer,
                              AddFields, AlterField, DefineProjection )

from speckle.converter.layers.utils import getLayerAttributes


def convertSelectedLayers(all_layers: List[arcpy._mp.Layer], selected_layers: List[str], project: arcpy.mp.ArcGISProject) -> List[Layer]:
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
            if layerToSend.isFeatureLayer: 
                newBaseLayer = layerToSpeckle(layerToSend, project)
                if newBaseLayer is not None: result.append(newBaseLayer)

            elif layerToSend.isRasterLayer: pass
            '''
            if layer.name() in selectedLayerNames:
                result.append(layerToSpeckle(layer, projectCRS, project))
            '''
    #print(result)
    return result

def layerToSpeckle(layer: arcLayer, project: ArcGISProject) -> Layer: #now the input is QgsVectorLayer instead of qgis._core.QgsLayerTreeLayer
    """Converts a given QGIS Layer to Speckle"""
    print("________Convert Feature Layer_________")

    projectCRS = project.activeMap.spatialReference
    try: data = arcpy.Describe(layer.dataSource)
    except OSError as e: arcpy.AddWarning(str(e.args[0])); return
    #print(projectCRS)
    #print(projectCRS.name)
    crs = CRS(name = projectCRS.name, wkt = projectCRS.exportToString(), units = "m")
    
    layer_geo_crs = None
    datum = None
    #if data.spatialReference.type == "Projected": 
    #    #layer_geo_crs =  
    #    datum = CRS(name = layer_geo_crs.name, wkt = layer_geo_crs.exportToString(), units = "m")
    
    speckleLayer = Layer()
    speckleLayer.type="VectorLayer"
    speckleLayer.name = layer.name
    speckleLayer.crs = crs
    speckleLayer.datum = datum
    
    try: # https://pro.arcgis.com/en/pro-app/2.8/arcpy/get-started/the-spatial-reference-object.htm
        layerObjs = []
        print(data.datasetType)
        if data.datasetType == "FeatureClass": #FeatureClass, ?Table Properties, ?Datasets
            # write feature attributes
            fieldnames = [field.name for field in data.fields]
            #print(layer.longName) # e.g. 17b0b76d13_custom_crs_04dcfaa936\04dcfaa936_Vector_lineGeom
            #print(fieldnames) # e.g. ['OBJECTID', 'Shape', 'Shape_Length', 'Speckle_ID', 'number', 'area']
            rows_shapes = arcpy.da.SearchCursor(layer.longName, "Shape@") # arcpy.da.SearchCursor(in_table, field_names, {where_clause}, {spatial_reference}, {explode_to_points}, {sql_clause})
            #print(rows_shapes) # <da.SearchCursor object at 0x00000172565E6C10>
            print("__ start iterating features")
            # write feature attributes
            for i, features in enumerate(rows_shapes):
                print("____Feature # " + str(i+1))
                if features[0] == None: continue 
                #print(features[0].hasCurves)
                if features[0].hasCurves: continue 
                rows_attributes = arcpy.da.SearchCursor(layer.longName, fieldnames)
                row_attr = []
                for k, attrs in enumerate(rows_attributes):
                    if i == k: row_attr = attrs; break

                #print(features) #(<Polygon object at 0x172592ae8c8[0x17258d2a600]>,)
                #print(features[0].pointCount)
                #print(features[0].partCount)
                if features[0]:
                    b = featureToSpeckle(fieldnames, row_attr, features[0], projectCRS, project, layer)
                    layerObjs.append(b)
                    #print(layerObjs)
                
            print("__ finish iterating features")
            speckleLayer.features=layerObjs
            speckleLayer.geomType = data.shapeType

    except OSError as e: 
        arcpy.AddWarning(str(e))
        return

    return speckleLayer

def layerToNative(layer: Union[Layer, RasterLayer], streamBranch: str, project: ArcGISProject):

    if layer.type is None:
        # Handle this case
        return
    elif layer.type.endswith("VectorLayer"):
        return vectorLayerToNative(layer, streamBranch, project)
    elif layer.type.endswith("RasterLayer"):
        return rasterLayerToNative(layer, streamBranch, project)
    return None

def cadLayerToNative(layerContentList:Base, layerName: str, streamBranch: str, project: ArcGISProject) :

    geom_points = []
    geom_polylines = []
    geom_polygones = []
    geom_meshes = []
    #filter speckle objects by type within each layer, create sub-layer for each type (points, lines, polygons, mesh?)
    for geom in layerContentList:
        #print(geom)
        if geom.speckle_type == "Objects.Geometry.Point": 
            geom_points.append(geom)
        if geom.speckle_type == "Objects.Geometry.Line" or geom.speckle_type == "Objects.Geometry.Polyline" or geom.speckle_type == "Objects.Geometry.Curve" or geom.speckle_type == "Objects.Geometry.Arc" or geom.speckle_type == "Objects.Geometry.Circle" or geom.speckle_type == "Objects.Geometry.Polycurve":
            geom_polylines.append(geom)
    
    if len(geom_points)>0: layer_points = cadVectorLayerToNative(geom_points, layerName, "Points", streamBranch, project)
    if len(geom_polylines)>0: layer_polylines = cadVectorLayerToNative(geom_polylines, layerName, "Polylines", streamBranch, project)

    return [layer_points, layer_polylines]

def cadVectorLayerToNative(geomList, layerName: str, geomType: str, streamBranch: str, project: ArcGISProject): 
    print("_________CAD vector layer to native_____")
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

    print("_________create feature class (cad)___________________________________")
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

def vectorLayerToNative(layer: Layer, streamBranch: str, project: ArcGISProject):
    print("_________Vector Layer to Native_________")
    vl = None
    layerName = layer.name.replace(" ","_").replace("-","_").replace("(","_").replace(")","_").replace(":","_").replace("\\","_").replace("/","_").replace("\"","_").replace("&","_").replace("@","_").replace("$","_").replace("%","_").replace("^","_")
    
    print(layerName)
    sr = arcpy.SpatialReference(text=layer.crs.wkt) 
    active_map = project.activeMap
    path = project.filePath.replace("aprx","gdb") #"\\".join(project.filePath.split("\\")[:-1]) + "\\speckle_layers\\" #arcpy.env.workspace + "\\" #
    #if not os.path.exists(path): os.makedirs(path)
    #print(path) 

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
    count = 0
    rowValues = []
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

    raster_layer = None
    '''
    crs = QgsCoordinateReferenceSystem.fromWkt(layer.crs.wkt) #moved up, because CRS of existing layer needs to be rewritten
    # try, in case of older version "rasterCrs" will not exist 
    try: crsRaster = QgsCoordinateReferenceSystem.fromWkt(layer.rasterCrs.wkt) #moved up, because CRS of existing layer needs to be rewritten
    except: 
        crsRaster = crs
        logger.logToUser(f"Raster layer {layer.name} might have been sent from the older version of plugin. Try sending it again for more accurate results.", Qgis.Warning)
    
    #CREATE A GROUP "received blabla" with sublayers
    newGroupName = f'{streamBranch}'
    root = QgsProject.instance().layerTreeRoot()
    layerGroup = QgsLayerTreeGroup(newGroupName)

    if root.findGroup(newGroupName) is not None:
        layerGroup = root.findGroup(newGroupName)
    else:
        root.addChildNode(layerGroup)
    layerGroup.setExpanded(True)
    layerGroup.setItemVisibilityChecked(True)

    #find ID of the layer with a matching name in the "latest" group 
    newName = f'{streamBranch}/{layer.name}'

    ######################## testing, only for receiving layers #################
    source_folder = QgsProject.instance().absolutePath()

    if(source_folder == ""):
        logger.logToUser(f"Raster layers can only be received in an existing saved project. Layer {layer.name} will be ignored", Qgis.Warning)
        return None

    project = QgsProject.instance()
    projectCRS = QgsCoordinateReferenceSystem.fromWkt(layer.crs.wkt)
    crsid = crsRaster.authid()
    try: epsg = int(crsid.split(":")[1]) 
    except: 
        epsg = int(str(projectCRS).split(":")[len(str(projectCRS).split(":"))-1].split(">")[0])
        logger.logToUser(f"CRS of the received raster cannot be identified. Project CRS will be used.", Qgis.Warning)
    
    feat = layer.features[0]
    bandNames = feat["Band names"]
    bandValues = [feat["@(10000)" + name + "_values"] for name in bandNames]

    #newName = f'{streamBranch}_latest_{layer.name}'

    ###########################################################################

    ## https://opensourceoptions.com/blog/pyqgis-create-raster/
    # creating file in temporary folder: https://stackoverflow.com/questions/56038742/creating-in-memory-qgsrasterlayer-from-the-rasterization-of-a-qgsvectorlayer-wit

    fn = source_folder + '/' + newName.replace("/","_") + '.tif' #'_received_raster.tif'
    driver = gdal.GetDriverByName('GTiff')
    # create raster dataset
    ds = driver.Create(fn, xsize=feat["X pixels"], ysize=feat["Y pixels"], bands=feat["Band count"], eType=gdal.GDT_Float32)

    # Write data to raster band
    for i in range(feat["Band count"]):
        rasterband = np.array(bandValues[i])
        rasterband = np.reshape(rasterband,(feat["Y pixels"], feat["X pixels"]))
        ds.GetRasterBand(i+1).WriteArray(rasterband) # or "rasterband.T"

    # create GDAL transformation in format [top-left x coord, cell width, 0, top-left y coord, 0, cell height]
    pt = pointToNative(feat["displayValue"][0])
    xform = QgsCoordinateTransform(crs, crsRaster, project)
    pt.transform(xform)
    ds.SetGeoTransform([pt.x(), feat["X resolution"], 0, pt.y(), 0, feat["Y resolution"]])
    # create a spatial reference object
    srs = osr.SpatialReference()
    #  For the Universal Transverse Mercator the SetUTM(Zone, North=1 or South=2)
    srs.ImportFromEPSG(epsg) # from https://gis.stackexchange.com/questions/34082/creating-raster-layer-from-numpy-array-using-pyqgis
    ds.SetProjection(srs.ExportToWkt())
    # close the rater datasource by setting it equal to None
    ds = None

    raster_layer = QgsRasterLayer(fn, newName, 'gdal')
    QgsProject.instance().addMapLayer(raster_layer, False)
    layerGroup.addLayer(raster_layer)

    dataProvider = raster_layer.dataProvider()
    rendererNew = rasterRendererToNative(layer, dataProvider)

    try: raster_layer.setRenderer(rendererNew)
    except: pass
    '''
    return raster_layer
