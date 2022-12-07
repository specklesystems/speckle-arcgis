#python speckle_toolbox\esri\toolboxes\speckle\plugin_utils\testing_from_file.py
import arcpy
from arcpy._mp import ArcGISProject, Map, Layer as arcLayer

import json
import os

from arcpy._mp import ArcGISProject, Map, Layer as arcLayer
from arcpy.management import (CreateFeatureclass, MakeFeatureLayer,
                              AddFields, AlterField, DefineProjection )

##################################################### get example layers from the project #######
path = r'C:\Users\katri\Documents\ArcGIS\Projects\MyProject\MyProject.gdb'
arcpy.env.workspace = path
project = ArcGISProject(path.replace("gdb","aprx"))
active_map = project.listMaps()[0] #.activeMap
all_layers = []

layerPolygon = None
layerPolyline = None
layerPoint = None
layerMultiPoint = None
#get layer of interest
for layer in active_map.listLayers(): 
   if layer.isFeatureLayer or layer.isRasterLayer: 
        all_layers.append(layer)
        data = arcpy.Describe(layer.dataSource)
        if layer.isFeatureLayer:
            geomType = data.shapeType
            if geomType == "Polygon" and layerPolygon is None: layerPolygon = layer 
            if geomType == "Polyline" and layerPolyline is None: layerPolyline = layer 
            if geomType == "Point" and layerPoint is None: layerPoint = layer 
            if geomType == "Multipoint" and layerMultiPoint is None: layerMultiPoint = layer 

root_path = "\\".join(project.filePath.split("\\")[:-1])
#path_style = root_path + '\\layer_speckle_symbology.lyrx'
path_style2 = root_path + '\\layer_speckle_symbology2.lyrx'

for layer in active_map.listLayers(): 
    if layer.longName == layerPolygon.longName:
        layerPolygon = layer
        break

print(layerPolygon.dataSource)

arcpy.ApplySymbologyFromLayer_management(
                        in_layer=layerPolygon.dataSource, 
                        in_symbology_layer=path_style2, 
                        update_symbology='UPDATE')

#vl2 = MakeFeatureLayer(layerPolygon.dataSource, 'someName').getOutput(0)
active_map.addLayer(arcpy.mp.LayerFile(path_style2))

################## reset symbology if needed:
r'''
sym = layerPolygon.symbology
print(sym.renderer.type)
sym.updateRenderer('UniqueValueRenderer')
layerPolygon.symbology = sym
print(sym.updateRenderer('UniqueValueRenderer'))
print(layerPolygon.symbology.renderer.type)
# SimpleRenderer, GraduatedColorsRenderer, GraduatedSymbolsRenderer, UnclassedColorsRenderer, UniqueValueRenderer 
'''
project.save() 
