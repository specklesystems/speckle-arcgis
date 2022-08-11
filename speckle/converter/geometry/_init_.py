
from regex import F
from specklepy.objects import Base
from specklepy.objects.geometry import Line, Mesh, Point, Polyline, Curve, Arc, Circle, Polycurve

import arcpy 
from typing import Any, List, Union, Sequence
from speckle.converter.geometry.polygon import polygonToNative, polygonToSpeckle
from speckle.converter.geometry.polyline import arcToNative, circleToNative, curveToNative, lineToNative, polycurveToNative, polylineFromVerticesToSpeckle, polylineToNative, polylineToSpeckle
from speckle.converter.geometry.point import pointToCoord, pointToNative, pointToSpeckle, multiPointToSpeckle


def convertToSpeckle(feature, layer, geomType, featureType) -> Union[Base, Sequence[Base], None]:
    """Converts the provided layer feature to Speckle objects"""
    print("___convertToSpeckle____________")
    geom = feature
    print(geom.isMultipart) # e.g. False 
    geomMultiType = geom.isMultipart
    
    print(featureType) 
    print(geomType)
    #geomSingleType = (featureType=="Simple") # Simple,SimpleJunction,SimpleJunction,ComplexEdge,Annotation,CoverageAnnotation,Dimension,RasterCatalogItem 

    if geomType == "Point": #Polygon, Point, Polyline, Multipoint, MultiPatch
        for pt in geom:
            return pointToSpeckle(pt, feature, layer)
    elif geomType == "Polyline":
        return polylineToSpeckle(geom, feature, layer, geomMultiType)
    elif geomType == "Polygon":
        return polygonToSpeckle(geom, feature, layer, geomMultiType)
    elif geomType == "Multipoint":
        return multiPointToSpeckle(geom, feature, layer, geomMultiType)
    else:
        arcpy.AddWarning("Unsupported or invalid geometry in layer " + layer.name)
    return None


def convertToNative(base: Base, sr: arcpy.SpatialReference) -> Union[Any, None]:
    """Converts any given base object to QgsGeometry."""
    converted = None
    conversions = [
        (Point, pointToNative),
        (Line, lineToNative),
        (Polyline, polylineToNative),
        (Curve, curveToNative),
        (Arc, arcToNative),
        (Circle, circleToNative),
        #(Mesh, meshToNative),
        (Polycurve, polycurveToNative),
        (Base, polygonToNative), # temporary solution for polygons (Speckle has no type Polygon yet)
    ]

    for conversion in conversions:
        if isinstance(base, conversion[0]):
            #print(conversion[0])
            converted = conversion[1](base, sr)
            break

    return converted

def multiPointToNative(items: List[Point], sr: arcpy.SpatialReference):
    print("Create MultiPoint")
    all_pts = []
    # example https://pro.arcgis.com/en/pro-app/2.8/arcpy/classes/multipoint.htm
    for item in items:
        pt = pointToCoord(item) # [x, y, z]
        all_pts.append( arcpy.Point(pt[0], pt[1], pt[2]) )
    print(all_pts)
    features = arcpy.Multipoint( arcpy.Array(all_pts) )
    #if len(features)==0: features = None
    return features

def multiPolylineToNative(items: List[Polyline], sr: arcpy.SpatialReference):
    print("_______Drawing Multipolylines____")
    print(items)
    all_pts = []
    # example https://community.esri.com/t5/python-questions/creating-a-multipolygon-polygon/td-p/392918
    for item in items:
        pts = [] 
        for pt in item.as_points(): #[[x,y,z],[x,y,z],..]
            pt = pointToCoord(pt)
            pts.append(arcpy.Point(pt[0], pt[1], pt[2]) )
        all_pts.append(arcpy.Array(pts))
    poly = arcpy.Polygon(arcpy.Array(all_pts), sr)
    return poly

def multiPolygonToNative(items: List[Base], sr: arcpy.SpatialReference): #TODO fix multi features
    
    print("_______Drawing Multipolygons____")
    print(items)
    for item in items: # will be 1 item
        print(item)
        pts = [pointToCoord(pt) for pt in item["boundary"].as_points()]
        outer_arr = [arcpy.Point(*coords) for coords in pts]
        outer_arr.append(outer_arr[0])
        list_of_arrs = []
        try:
            for void in item["voids"]: 
                print(void)
                pts = [pointToCoord(pt) for pt in void.as_points()]
                print(pts)
                inner_arr = [arcpy.Point(*coords) for coords in pts]
                inner_arr.append(inner_arr[0])
                list_of_arrs.append(arcpy.Array(inner_arr))
        except:pass
    
    list_of_arrs.insert(0, arcpy.Array(outer_arr))
    array = arcpy.Array(list_of_arrs)
    polygon = arcpy.Polygon(array, sr)

    r'''
    all_pts = []
    # example https://community.esri.com/t5/python-questions/creating-a-multipolygon-polygon/td-p/392918
    for item in items:
        pts = [] 
        for pt in item["boundary"].as_points(): #[[x,y,z],[x,y,z],..]
            pt = pointToCoord(pt)
            pts.append(arcpy.Point(pt[0], pt[1], pt[2]) )
        pts.append(pts[0])
        all_pts.append(arcpy.Array(pts))
    polygon = arcpy.Polygon(arcpy.Array(all_pts), sr)
    '''
    return polygon

def convertToNativeMulti(items: List[Base], sr: arcpy.SpatialReference): 
    first = items[0]
    if isinstance(first, Point):
        return multiPointToNative(items, sr)
    elif isinstance(first, Line) or isinstance(first, Polyline):
        return multiPolylineToNative(items, sr)
    elif first["boundary"] is not None and first["voids"] is not None:
        return multiPolygonToNative(items, sr)
