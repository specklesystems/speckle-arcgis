from specklepy.objects import Base
import arcpy 
from arcpy.management import CreateCustomGeoTransformation

from speckle.converter.geometry._init_ import convertToSpeckle, convertToNative, convertToNativeMulti
from speckle.converter.layers.utils import getVariantFromValue

def featureToSpeckle(fieldnames, attr_list, f_shape, projectCRS: arcpy.SpatialReference, project: arcpy.mp.ArcGISProject, selectedLayer):
    print("___________Feature to Speckle____________")
    b = Base(units = "m")
    data = arcpy.Describe(selectedLayer.dataSource)
    layer_sr = data.spatialReference # if sr.type == "Projected":
    geomType = data.shapeType #Polygon, Point, Polyline, Multipoint, MultiPatch
    featureType = data.featureType # Simple,SimpleJunction,SimpleJunction,ComplexEdge,Annotation,CoverageAnnotation,Dimension,RasterCatalogItem 

    print(layer_sr.name)
    print(projectCRS.name)

    #apply transformation if needed
    if layer_sr.name != projectCRS.name:

        #ptgeo1 = f_shape.projectAs(projectCRS)
        #f_shape = ptgeo1
        
        tr0 = tr1 = tr2 = tr_custom = None
        transformations = arcpy.ListTransformations(layer_sr, projectCRS)
        print(transformations)
        customTransformName = "layer_sr.name"+"_To_"+ projectCRS.name
        if len(transformations) == 0:
            midSr = arcpy.SpatialReference("WGS 1984") # GCS_WGS_1984
            try:
                tr1 = arcpy.ListTransformations(layer_sr, midSr)[0]
                tr2 = arcpy.ListTransformations(midSr, projectCRS)[0]
                print(tr1)
                print(tr2)
            except: 
                #customGeoTransfm = "GEOGTRAN[METHOD['Geocentric_Translation'],PARAMETER['X_Axis_Translation',''],PARAMETER['Y_Axis_Translation',''],PARAMETER['Z_Axis_Translation','']]"
                #CreateCustomGeoTransformation(customTransformName, layer_sr, projectCRS)
                tr_custom = customTransformName
        else: 
            print("else")
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
            print(tr0)

        if geomType != "Point" and geomType != "Polyline" and geomType != "Polygon" and geomType != "Multipoint":
            print(geomType)
            arcpy.AddWarning("Unsupported or invalid geometry in layer " + selectedLayer.name)

        # reproject geometry using chosen transformstion(s)
        if tr0 is not None:
            ptgeo1 = f_shape.projectAs(projectCRS, tr0)
            f_shape = ptgeo1
        elif tr1 is not None and tr2 is not None:
            print("else")
            print(tr1)
            print(tr2)
            ptgeo1 = f_shape.projectAs(midSr, tr1)
            ptgeo2 = ptgeo1.projectAs(projectCRS, tr2)
            f_shape = ptgeo2
        else:
            ptgeo1 = f_shape.projectAs(projectCRS)
            f_shape = ptgeo1
        
             
        print(f_shape)

    ######################################### Convert geometry
    try:
        geom = convertToSpeckle(f_shape, selectedLayer, geomType, featureType)
        if geom is not None:
            b["geometry"] = geom
    except Exception as error:
        arcpy.AddError("Error converting geometry: " + str(error))

    #print(attr_list)
    #print(fieldnames)
    for i, name in enumerate(fieldnames):
        corrected = name.replace("/", "_").replace(".", "-")
        if corrected != "Shape" and corrected != "Shape@": 
            if corrected == "FID": 
                b["applicationId"] = str(attr_list[i])
            else: b[corrected] = attr_list[i]
    print("_____________________")
    return b


def featureToNative(feature: Base, fields: dict, sr: arcpy.SpatialReference):
    feat = {}
    try: speckle_geom = feature["geometry"] # for created in QGIS / ArcGIS Layer type
    except:  speckle_geom = feature # for created in other software

    if isinstance(speckle_geom, list):
        arcGisGeom = convertToNativeMulti(speckle_geom, sr)
    else:
        arcGisGeom = convertToNative(speckle_geom, sr)

    if arcGisGeom is not None:
        feat.update({"arcGisGeomFromSpeckle": arcGisGeom})

    #try: 
    #    if "id" not in fields.keys() and feature["applicationId"]: fields.update(QgsField("id", QVariant.String))
    #except: pass
    
    #feat.setFields(fields)  
    for key, variant in fields.items():
        if key == "FID": feat.update({key: str(feature["applicationId"]) })
        elif key != "Shape" and key != "Shape@" and key != "arcGisGeomFromSpeckle": 
            #print(feature[key])
            value = feature[key]
            if variant == "TEXT": value = str(feature[key]) 
            r'''
            if isinstance(value, str) and variant == QVariant.Date:  # 14
                y,m,d = value.split("(")[1].split(")")[0].split(",")[:3]
                value = QDate(int(y), int(m), int(d) ) 
            elif isinstance(value, str) and variant == QVariant.DateTime: 
                y,m,d,t1,t2 = value.split("(")[1].split(")")[0].split(",")[:5]
                value = QDateTime(int(y), int(m), int(d), int(t1), int(t2) )
            '''
            if variant == getVariantFromValue(value) and value != "NULL" and value != "None": 
                feat.update({key: value})
            else: 
                if variant == "TEXT": feat.update({key: ""})
                if variant == "FLOAT": feat.update({key: None})
                if variant == "LONG": feat.update({key: None})
                if variant == "SHORT": feat.update({key: None})
    print(feat)
    return feat
