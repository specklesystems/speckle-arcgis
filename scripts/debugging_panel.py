
from arcpy._mp import ArcGISProject, Map, Layer as arcLayer
import arcpy
import json
import os

try: 
    from speckle.speckle.converter.layers.CRS import CRS
    from specklepy.objects.GIS.layers import Layer, VectorLayer, RasterLayer
except: 
    from speckle_toolbox.esri.toolboxes.speckle.converter.layers.CRS import CRS
    from speckle_toolbox.esri.toolboxes.speckle.converter.layers.Layer import Layer, VectorLayer, RasterLayer

from arcpy._mp import ArcGISProject, Map, Layer as arcLayer
from arcpy.management import (CreateFeatureclass, MakeFeatureLayer,
                              AddFields, AlterField, DefineProjection, SelectLayerByAttribute, GetCount )

from specklepy.objects import Base

##################################################### get example layers from the project #######
project = ArcGISProject('CURRENT')
active_map = project.activeMap
all_layers = []

layerPolygon = None
layerPolyline = None
layerPoint = None
layerMultiPoint = None
layerRaster = None
#get layer of interest
for layer in active_map.listLayers(): 
   if layer.isFeatureLayer or layer.isRasterLayer: 
        all_layers.append(layer)
        data = arcpy.Describe(layer.dataSource)
        if layer.isRasterLayer and layerRaster is None: layerRaster = layer 
        if layer.isFeatureLayer:
            geomType = data.shapeType
            if geomType == "Polygon" and layerPolygon is None: layerPolygon = layer 
            if geomType == "Polyline" and layerPolyline is None: layerPolyline = layer 
            if geomType == "Point" and layerPoint is None: layerPoint = layer 
            if geomType == "Multipoint" and layerMultiPoint is None: layerMultiPoint = layer 

################################ select/ clear selection ###########################
for layer in project.activeMap.listLayers(): 
    if (layer.isFeatureLayer) or layer.isRasterLayer: 
        arcpy.SelectLayerByAttribute_management(layer.longName,"ADD_TO_SELECTION",'"OBJECTID" = 1')
        print(arcpy.GetCount_management(layer.longName).getOutput(0))
        arcpy.SelectLayerByAttribute_management(layer.longName, "CLEAR_SELECTION")

################## reset symbology if needed:
sym = layerPolygon.symbology
print(sym.renderer.type)
sym.updateRenderer('UniqueValueRenderer')
layerPolygon.symbology = sym
print(sym.updateRenderer('UniqueValueRenderer'))
print(layerPolygon.symbology.renderer.type)
# SimpleRenderer, GraduatedColorsRenderer, GraduatedSymbolsRenderer, UnclassedColorsRenderer, UniqueValueRenderer 

######################################### change symbology ################################# 

for k, grp in enumerate(sym.renderer.groups):
    for itm in grp.items:
        print(itm)
        print(itm.values)
        print(itm.symbol.color)
        transVal = itm.values[0][0] #Grab the first "percent" value in the list of potential values
        print(transVal)
        for i in range(len(cats)):
            label = cats[i]['value'] 
            print(label)
            if label is None or label=="": label = "<Null>"
            print(label)



from speckle.speckle.converter.layers.symbology import get_polygon_simpleRenderer 
from arcpy._mp import ArcGISProject

aprx = ArcGISProject('CURRENT')
root_path = "\\".join(aprx.filePath.split("\\")[:-1])

path_style = root_path + '\\layer_speckle_symbology.lyrx'
path_style2 = root_path + '\\layer_speckle_symbology2.lyrx'
#arcpy.management.SaveToLayerFile(layerPolygon, path_style, False)
print(layerPolygon.dataSource)
arcpy.management.ApplySymbologyFromLayer(
                        in_layer=layerPolygon.dataSource, 
                        in_symbology_layer=path_style2, 
                        update_symbology='UPDATE')



f = open(path_style, "r")
renderer = json.loads(f.read())

renderer["layerDefinitions"][0]["renderer"] = get_polygon_simpleRenderer(1,2,150)
f = open(path_style2, "w")
f.write(json.dumps(renderer, indent=4))
f.close()
arcpy.management.ApplySymbologyFromLayer(str(layerPolygon), path_style2)
os.remove(path_style)
os.remove(path_style2)

###########################################################################
layer = all_layers[0] 
if isinstance(layer, arcLayer): 

    projectCRS = project.activeMap.spatialReference
    try: data = arcpy.Describe(layer.dataSource)
    except OSError as e: print(e)

    layerName = layer.name
    crs = data.SpatialReference
    units = "m"
    layerObjs = []

    # Convert CRS to speckle, use the projectCRS
    speckleReprojectedCrs = CRS(name = projectCRS.name, wkt = projectCRS.exportToString(), units = units)
    layerCRS = CRS(name=crs.name, wkt=crs.exportToString(), units = units) 

    if layer.isFeatureLayer: 
        print("VECTOR LAYER HERE")
        
        speckleLayer = VectorLayer(units = "m")
        speckleLayer.type="VectorLayer"
        speckleLayer.name = layerName
        speckleLayer.crs = speckleReprojectedCrs

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

                if feat is not None: 
                    print(feat)
                    rows_attributes = arcpy.da.SearchCursor(layer.longName, fieldnames)
                    row_attr = []
                    for k, attrs in enumerate(rows_attributes):
                        if i == k: row_attr = attrs; break
                    if feat.hasCurves: feat = feat.densify("ANGLE", 1000, 0.12)

                    print("___________Feature to Speckle____________")

                    b = Base(units = "m")
                    data = arcpy.Describe(layer.dataSource)
                    layer_sr = data.spatialReference # if sr.type == "Projected":
                    geomType = data.shapeType #Polygon, Point, Polyline, Multipoint, MultiPatch
                    featureType = data.featureType # Simple,SimpleJunction,SimpleJunction,ComplexEdge,Annotation,CoverageAnnotation,Dimension,RasterCatalogItem 
                    print(geomType)
                    print(hasattr(data, "isRevit")) 
                    print(hasattr(data, "isIFC")) 
                    print(hasattr(data, "bimLevels")) 
                    print(hasattr(data, "hasSpatialIndex")) 
                    if geomType == "MultiPatch" or hasattr(data, "isRevit") or hasattr(data, "isIFC") or hasattr(data, "bimLevels"): 
                        print(f"Layer {layer.name} has unsupported data type")

                        print("___convertToSpeckle____________")
                        geom = feat
                        print(geom.isMultipart) # e.g. False 
                        print(geom.hasCurves)
                        print(geom.partCount)
                        geomMultiType = geom.isMultipart
                        hasCurves = feat.hasCurves 

                        geomPart = []
                        for i,x in enumerate(feat): # [[x,x,x]
                            
                            if i==0:
                                print("Part # " + str(i+1))
                                print(x)

                                inner_arr = []
                                for k,ptn in enumerate(x):  
                                    if k<10: print(ptn) # e.g. 6.25128173828125 -9.42138671875 22.2768999999971 NaN

                                    inner_arr.append(ptn)
                                    #inner_arr.append(inner_arr[0]) #add first in the end
                                geomPart.append(arcpy.Array(inner_arr))

                                geomPartArray = arcpy.Array(inner_arr)
                                sr = project.activeMap.spatialReference

                                multipatch = arcpy.Multipatch(arcpy.Array(x), sr, has_z=True) # error 
                                print(multipatch)
                        
                    else:
                        print("___convertToSpeckle____________")
                        geom = feat
                        print(geom.isMultipart) # e.g. False 
                        print(geom.hasCurves)
                        print(geom.partCount)
                        geomMultiType = geom.isMultipart
                        hasCurves = feat.hasCurves 

                        for i,x in enumerate(feat): # [[x,x,x]
                            print("Part # " + str(i+1))
                            print(x)
                            for k,ptn in enumerate(x): 
                                if k<10: print(ptn) # e.g. 6.25128173828125 -9.42138671875 22.2768999999971 NaN


path: str = project.filePath.replace("aprx","gdb") 
sr = project.activeMap.spatialReference
print(sr)
f_class = CreateFeatureclass(path, "NewTestLayer", "Multipatch", has_z="ENABLED", spatial_reference = sr)
fets = []
print("04_____Feature To Native____________") 
new_feat = {}
new_feat.update({"arcGisGeomFromSpeckle": multipatch})
fets.append(new_feat)

vl = MakeFeatureLayer(str(f_class), "NewTestLayer").getOutput(0)



############################# write shapefile ##################################

import shapefile
from shapefile import TRIANGLE_STRIP, TRIANGLE_FAN

from arcpy._mp import ArcGISProject, Map, Layer as arcLayer
from arcpy.management import (CreateFeatureclass, MakeFeatureLayer,
                              AddFields, AlterField, DefineProjection )

from specklepy.objects import Base

project = ArcGISProject('CURRENT')
path: str = project.filePath.replace("aprx","gdb") 

#with shapefile.Writer(path + "\contextwriter") as w:
#    w.field('field1', 'C')
#    pass

w = shapefile.Writer(path + '\\dtype')
w.field('TEXT', 'C')
w.field('SHORT_TEXT', 'C', size=5)
w.field('LONG_TEXT', 'C', size=250)
w.null()
w.record('Hello', 'World', 'World'*50)
w.close()

r = shapefile.Reader(path + '\\dtype')
assert r.record(0) == ['Hello', 'World', 'World'*50]
################################################################### WORKS #################################

w = shapefile.Writer(path + '\\dtype')
w.field('INT', 'N')
w.field('LOWPREC', 'N', decimal=2)
w.field('MEDPREC', 'N', decimal=10)
w.field('HIGHPREC', 'N', decimal=30)
w.field('FTYPE', 'F', decimal=10)
w.field('LARGENR', 'N', 101)
w.field('FIRST_FLD','C','40')
w.field('SECOND_FLD','C','40')
nr = 1.3217328
w.null()
w.null()
w.record(INT=nr, LOWPREC=nr, MEDPREC=nr, HIGHPREC=-3.2302e-25, FTYPE=nr, LARGENR=int(nr)*10**100, FIRST_FLD='First', SECOND_FLD='Line')
w.record(None, None, None, None, None, None, '', '')
w.close()

r = shapefile.Reader(path + '\\dtype')
assert r.record(0) == [1, 1.32, 1.3217328, -3.2302e-25, 1.3217328, 10000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000, 'First', 'Line']
assert r.record(1) == [None, None, None, None, None, None, '', '']

################################################################# Add point ####################

w = shapefile.Writer(path + '\\dtypeShapes')
w.field('name', 'C')

w.point(122, 37) 
w.record('point1')

w.close()

################################################################# Add Multipatch ####################

w = shapefile.Writer(path + '\\MultipatchTest2')
w.field('name', 'C')

w.multipatch([
			 [[0,0,0],[0,0,3],[5,0,0],[5,0,3],[5,5,0],[5,5,3],[0,5,0],[0,5,3],[0,0,0],[0,0,3]], # TRIANGLE_STRIP for house walls
			 [[2.5,2.5,5],[0,0,3],[5,0,3],[5,5,3],[0,5,3],[0,0,3]], # TRIANGLE_FAN for pointed house roof
			 ],
			 partTypes=[TRIANGLE_STRIP, TRIANGLE_FAN]) # one type for each part

w.record('house1')
w.close()

r = shapefile.Reader(path + '\\MultipatchTest2')
assert r.record(0) == ['house1']


active_map.addDataFromPath(path + '\\MultipatchTest2.shp')

########################################################################## reader 
sf = shapefile.Reader(path + '\\MultipatchTest2.shp')
sf.shapeType # e.g. 31 - multipatch
sf.bbox # e.g. [0.0, 0.0, 5.0, 5.0]
shapefile.Shape


##################################################### cerate multipatch layer #################################
result = arcpy.management.CreateFeatureclass(arcpy.env.scratchGDB, "test_multipatch", "MULTIPATCH", has_z="ENABLED", spatial_reference=4326)
feature_class = result[0]


################################# reading shapefile - works ####################

fc = r'C:\Users\katri\Documents\ArcGIS\Projects\MyProject\Layers_Speckle\BIM_layers_speckle\00f70159b9104180f622cca87f5dd2cb.shp'
rows = arcpy.da.SearchCursor(fc, 'Shape@')
for r in rows:
        if r is not None: shape = r
print(shape)
cl = arcpy.conversion.FeatureClassToFeatureClass(r'C:\Users\katri\Documents\ArcGIS\Projects\MyProject\Layers_Speckle\BIM_layers_speckle\16d73b756a_main_2f8cfa8644\__Floors_Mesh\00c7696966e4cfda2bd8c03860a414a6', r'C:\Users\katri\Documents\ArcGIS\tests', 'copyclass')

##################################### update rows in feature class - working #############
with arcpy.da.UpdateCursor('f_class_2f8cfa8644___Structural_Framing_Mesh', 'name') as cursor:
    # For each row, evaluate the WELL_YIELD value (index position 
    # of 0), and update WELL_CLASS (index position of 1)
    for row in cursor: 
        row[0] = "newName"
        cursor.updateRow(row)

