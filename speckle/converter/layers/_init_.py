"""
Contains all Layer related classes and methods.
"""
from typing import Any, List, Union

from regex import D
from speckle.converter.layers.CRS import CRS
from speckle.converter.layers.Layer import Layer, RasterLayer
from speckle.converter.layers.feature import featureToSpeckle
from specklepy.objects import Base

import pandas as pd
import arcpy


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

def layerToSpeckle(layer: arcpy._mp.Layer, project: arcpy.mp.ArcGISProject) -> Layer: #now the input is QgsVectorLayer instead of qgis._core.QgsLayerTreeLayer
    """Converts a given QGIS Layer to Speckle"""
    print("________Convert Feature Layer_________")

    projectCRS = project.activeMap.spatialReference
    crs = CRS(name = projectCRS.name, wkt = projectCRS.exportToString(), units = "m")
    
    speckleLayer = Layer()
    speckleLayer.type="VectorLayer"
    speckleLayer.name = layer.name
    speckleLayer.crs = crs

    try: # https://pro.arcgis.com/en/pro-app/2.8/arcpy/get-started/the-spatial-reference-object.htm
        layerObjs = []
        data = arcpy.Describe(layer.dataSource)

        if data.datasetType == "FeatureClass": #FeatureClass, ?Table Properties, ?Datasets
            
            # write feature attributes
            fieldnames = [field.name for field in data.fields]
            rows_shapes = arcpy.da.SearchCursor(layer.name, "Shape@") # arcpy.da.SearchCursor(in_table, field_names, {where_clause}, {spatial_reference}, {explode_to_points}, {sql_clause})
            print(rows_shapes) # <da.SearchCursor object at 0x00000172565E6C10>

            # write feature attributes
            for i, features in enumerate(rows_shapes):
                rows_attributes = arcpy.da.SearchCursor(layer.name, fieldnames)
                row_attr = []
                for k, attrs in enumerate(rows_attributes):
                    if i == k: row_attr = attrs; break

                print(features) #(<Polygon object at 0x172592ae8c8[0x17258d2a600]>,)
                #print(features[0]) # <geoprocessing describe geometry object object at 0x000001B3278E5AB0>
                print(row_attr) # 
                b = featureToSpeckle(fieldnames, row_attr, features[0], projectCRS, project, layer)
                layerObjs.append(b)
                
            speckleLayer.features=layerObjs
            speckleLayer.geomType = data.shapeType

    except OSError as e: 
        arcpy.AddWarning(str(e))
        return
    
    #renderer = layer.symbology
    #speckleLayer.renderer = renderer
    #speckleLayer.applicationId = layer.id()

    return speckleLayer