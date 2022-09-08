from specklepy.objects import Base
import arcpy 
from arcpy.management import CreateCustomGeoTransformation
from arcpy._mp import ArcGISProject, Map, Layer as arcLayer

from speckle.converter.geometry._init_ import convertToSpeckle, convertToNative, convertToNativeMulti
from speckle.converter.layers.utils import getVariantFromValue
from speckle.converter.layers.utils import traverseDict

def featureToSpeckle(fieldnames, attr_list, f_shape, projectCRS: arcpy.SpatialReference, project: ArcGISProject, selectedLayer: arcLayer):
    print("___________Feature to Speckle____________")
    b = Base(units = "m")
    data = arcpy.Describe(selectedLayer.dataSource)
    layer_sr = data.spatialReference # if sr.type == "Projected":
    geomType = data.shapeType #Polygon, Point, Polyline, Multipoint, MultiPatch
    featureType = data.featureType # Simple,SimpleJunction,SimpleJunction,ComplexEdge,Annotation,CoverageAnnotation,Dimension,RasterCatalogItem 

    #print(layer_sr.name)
    #print(projectCRS.name)

    #apply transformation if needed
    if layer_sr.name != projectCRS.name:
        tr0 = tr1 = tr2 = tr_custom = None
        transformations = arcpy.ListTransformations(layer_sr, projectCRS)
        customTransformName = "layer_sr.name"+"_To_"+ projectCRS.name
        if len(transformations) == 0:
            midSr = arcpy.SpatialReference("WGS 1984") # GCS_WGS_1984
            try:
                tr1 = arcpy.ListTransformations(layer_sr, midSr)[0]
                tr2 = arcpy.ListTransformations(midSr, projectCRS)[0]
            except: 
                #customGeoTransfm = "GEOGTRAN[METHOD['Geocentric_Translation'],PARAMETER['X_Axis_Translation',''],PARAMETER['Y_Axis_Translation',''],PARAMETER['Z_Axis_Translation','']]"
                #CreateCustomGeoTransformation(customTransformName, layer_sr, projectCRS)
                tr_custom = customTransformName
        else: 
            #print("else")
            # choose equation based instead of file-based/grid-based method, 
            # to be consistent with QGIS: https://desktop.arcgis.com/en/arcmap/latest/map/projections/choosing-an-appropriate-transformation.htm
            selecterTr = {}
            for tr in transformations:
                if "NTv2" not in tr and "NADCON" not in tr: 
                    set1 = set( layer_sr.name.split("_") + projectCRS.name.split("_") )
                    set2 = set( tr.split("_") )
                    diff = len( set(set1).symmetric_difference(set2) )
                    selecterTr.update({tr: diff})
            selecterTr = dict(sorted(selecterTr.items(), key=lambda item: item[1]))
            tr0 = list(selecterTr.keys())[0]
            #print(tr0)

        if geomType != "Point" and geomType != "Polyline" and geomType != "Polygon" and geomType != "Multipoint":
            #print(geomType)
            arcpy.AddWarning("Unsupported or invalid geometry in layer " + selectedLayer.name)

        # reproject geometry using chosen transformstion(s)
        if tr0 is not None:
            ptgeo1 = f_shape.projectAs(projectCRS, tr0)
            f_shape = ptgeo1
        elif tr1 is not None and tr2 is not None:
            ptgeo1 = f_shape.projectAs(midSr, tr1)
            ptgeo2 = ptgeo1.projectAs(projectCRS, tr2)
            f_shape = ptgeo2
        else:
            ptgeo1 = f_shape.projectAs(projectCRS)
            f_shape = ptgeo1
        

    ######################################### Convert geometry ##########################################
    try:
        geom = convertToSpeckle(f_shape, selectedLayer, geomType, featureType) 
        if geom is not None: print(geom); b["geometry"] = geom 
    except Exception as error:
        print("Error converting geometry: " + str(error))
        print(selectedLayer)
        arcpy.AddError("Error converting geometry: " + str(error))
    #print(geomType) 
    #print(featureType) 
    for i, name in enumerate(fieldnames):
        corrected = name.replace("/", "_").replace(".", "-")
        if corrected != "Shape" and corrected != "Shape@": 
            # different ID behaviors: https://support.esri.com/en/technical-article/000010834 
            # save all attribute, duplicate one into applicationId 
            b[corrected] = attr_list[i]
            if corrected == "FID" or corrected == "OID" or corrected == "OBJECTID": b["applicationId"] = str(attr_list[i])
    #print(b)
    print("______end of __Feature to Speckle____________________")
    return b

def featureToNative(feature: Base, fields: dict, geomType: str, sr: arcpy.SpatialReference):
    print("04_____Feature To Native____________") 
    feat = {}
    try: speckle_geom = feature["geometry"] # for created in QGIS / ArcGIS Layer type
    except:  speckle_geom = feature # for created in other software
    print(speckle_geom)
    if isinstance(speckle_geom, list):
        if len(speckle_geom)>1 or geomType == "Multipoint": arcGisGeom = convertToNativeMulti(speckle_geom, sr)
        else: arcGisGeom = convertToNative(speckle_geom[0], sr)
    else:
        arcGisGeom = convertToNative(speckle_geom, sr)

    if arcGisGeom is not None:
        feat.update({"arcGisGeomFromSpeckle": arcGisGeom})
    else:
        return None

    for key, variant in fields.items(): 

        value = feature[key]
        if variant == "TEXT": value = str(feature[key]) 
        if variant == getVariantFromValue(value) and value != "NULL" and value != "None": 
            feat.update({key: value})
        else: 
            if variant == "TEXT": feat.update({key: None})
            if variant == "FLOAT": feat.update({key: None})
            if variant == "LONG": feat.update({key: None})
            if variant == "SHORT": feat.update({key: None})
    return feat

def cadFeatureToNative(feature: Base, fields: dict, sr: arcpy.SpatialReference):
    print("04_________CAD Feature To Native____________")
    feat = {}
    try: speckle_geom = feature["geometry"] # for created in QGIS Layer type
    except:  speckle_geom = feature # for created in other software

    if isinstance(speckle_geom, list):
        if len(speckle_geom)>1: arcGisGeom = convertToNativeMulti(speckle_geom, sr)
        else: arcGisGeom = convertToNative(speckle_geom[0], sr) 
    else:
        arcGisGeom = convertToNative(speckle_geom, sr)
    print(feat)
    if arcGisGeom is not None:
        feat.update({"arcGisGeomFromSpeckle": arcGisGeom})
    else: return None
    print(feat)
    try: 
        if "Speckle_ID" not in fields.keys() and feature["id"]: feat.update("Speckle_ID", "TEXT")
    except: pass
    print(feat)
    #### setting attributes to feature
    for key, variant in fields.items(): 
        #value = feature[key]
        #print()
        if key == "Speckle_ID": 
            value = str(feature["id"])
            feat[key] = value 
        else:
            try: value = feature[key]
            except:
                rootName = key.split("_")[0]
                newF, newVals = traverseDict({}, {}, rootName, feature[rootName][0])
                for i, (k,v) in enumerate(newVals.items()):
                    if k == key: value = v; break
        # for all values: 
        if variant == "TEXT": value = str(value) 

        if variant == getVariantFromValue(value) and value != "NULL" and value != "None": 
            feat.update({key: value})   
        else: 
            if variant == "TEXT": feat.update({key: None})
            if variant == "FLOAT": feat.update({key: None})
            if variant == "LONG": feat.update({key: None})
            if variant == "SHORT": feat.update({key: None})
            
    print(feat) 
    return feat
    
