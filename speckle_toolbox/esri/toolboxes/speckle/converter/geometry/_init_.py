
from regex import F
from specklepy.objects import Base
from specklepy.objects.geometry import Line, Mesh, Point, Polyline, Curve, Arc, Circle, Polycurve, Ellipse 

import arcpy 
from typing import Any, List, Union, Sequence
from speckle.converter.geometry.polygon import polygonToNative, polygonToSpeckle
from speckle.converter.geometry.polyline import arcToNative, ellipseToNative, circleToNative, curveToNative, lineToNative, polycurveToNative, polylineFromVerticesToSpeckle, polylineToNative, polylineToSpeckle
from speckle.converter.geometry.point import pointToCoord, pointToNative, pointToSpeckle, multiPointToSpeckle
from speckle.converter.geometry.polyline import speckleArcCircleToPoints, specklePolycurveToPoints
import numpy as np

def convertToSpeckle(feature, layer, geomType, featureType) -> Union[Base, Sequence[Base], None]:
    """Converts the provided layer feature to Speckle objects"""
    print("___convertToSpeckle____________")
    geom = feature
    #print(geom.isMultipart) # e.g. False 
    geomMultiType = geom.isMultipart
    hasCurves = feature.hasCurves 
    
    #print(featureType) # e.g. Simple 
    #print(geomType) # e.g. Polygon 
    #geomSingleType = (featureType=="Simple") # Simple,SimpleJunction,SimpleJunction,ComplexEdge,Annotation,CoverageAnnotation,Dimension,RasterCatalogItem 

    if geomType == "Point": #Polygon, Point, Polyline, Multipoint, MultiPatch
        for pt in geom:
            return pointToSpeckle(pt, feature, layer)
    elif geomType == "Polyline":
        #if geom.hasCurves: 
        #    geom, feature = curvesToSegments(geom, feature, layer, geomMultiType)
        #    geomMultiType = geom.isMultipart
        #    return polylineToSpeckle(geom, feature, layer, geomMultiType)
        #else:
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
    print("___Convert to Native SingleType___")
    #print(base)
    converted = None
    conversions = [
        (Point, pointToNative),
        (Line, lineToNative),
        (Polyline, polylineToNative),
        (Curve, curveToNative),
        (Arc, arcToNative),
        (Circle, circleToNative),
        (Ellipse, ellipseToNative),
        #(Mesh, meshToNative),
        (Polycurve, polycurveToNative),
        (Base, polygonToNative), # temporary solution for polygons (Speckle has no type Polygon yet)
    ]

    for conversion in conversions:
        if isinstance(base, conversion[0]):
            #print(conversion[0])
            converted = conversion[1](base, sr)
            break
    #print(converted)
    return converted

def multiPointToNative(items: List[Point], sr: arcpy.SpatialReference):
    print("___Create MultiPoint")
    all_pts = []
    # example https://pro.arcgis.com/en/pro-app/2.8/arcpy/classes/multipoint.htm
    for item in items:
        pt = pointToCoord(item) # [x, y, z]
        all_pts.append( arcpy.Point(pt[0], pt[1], pt[2]) )
    #print(all_pts)
    features = arcpy.Multipoint( arcpy.Array(all_pts) )
    #if len(features)==0: features = None
    return features

def multiPolylineToNative(items: List[Polyline], sr: arcpy.SpatialReference):
    print("_______Drawing Multipolylines____")
    #print(items)
    poly = None
    full_array_list = []
    for item in items: # will be 1 item
        pointsSpeckle = []
        try: pointsSpeckle = item.as_points()
        except: continue 
        pts = [pointToCoord(pt) for pt in pointsSpeckle]

        if item.closed is True: 
            pts.append( pointToCoord(item.as_points()[0]) )
        
        arr = [arcpy.Point(*coords) for coords in pts]
        full_array_list.append(arr)

    poly = arcpy.Polyline( arcpy.Array(full_array_list), sr, has_z=True )
    return poly

def multiPolygonToNative(items: List[Base], sr: arcpy.SpatialReference): #TODO fix multi features
    
    print("_______Drawing Multipolygons____")
    #print(items)
    full_array_list = []

    for item in items: # will be 1 item
        #print(item)
        #pts = [pointToCoord(pt) for pt in item["boundary"].as_points()]
        pointsSpeckle = []
        if isinstance(item["boundary"], Circle) or isinstance(item["boundary"], Arc): 
            pointsSpeckle = speckleArcCircleToPoints(item["boundary"]) 
        elif isinstance(item["boundary"], Polycurve): 
            pointsSpeckle = specklePolycurveToPoints(item["boundary"]) 
        elif isinstance(item["boundary"], Line): pass
        else: 
            try: pointsSpeckle = item["boundary"].as_points()
            except: pass # if Line

        pts = [pointToCoord(pt) for pt in pointsSpeckle]
        print(pts)

        outer_arr = [arcpy.Point(*coords) for coords in pts]
        outer_arr.append(outer_arr[0])
        geomPart = []
        try:
            for void in item["voids"]: 
                #print(void)
                #pts = [pointToCoord(pt) for pt in void.as_points()]
                pointsSpeckle = []
                if isinstance(void, Circle) or isinstance(void, Arc): 
                    pointsSpeckle = speckleArcCircleToPoints(void) 
                elif isinstance(void, Polycurve): 
                    pointsSpeckle = specklePolycurveToPoints(void) 
                elif isinstance(void, Line): pass
                else: 
                    try: pointsSpeckle = void.as_points()
                    except: pass # if Line
                pts = [pointToCoord(pt) for pt in pointsSpeckle]

                inner_arr = [arcpy.Point(*coords) for coords in pts]
                inner_arr.append(inner_arr[0])
                geomPart.append(arcpy.Array(inner_arr))
        except:pass
    
        geomPart.insert(0, arcpy.Array(outer_arr))
        full_array_list.extend(geomPart)

    geomPartArray = arcpy.Array(full_array_list)
    polygon = arcpy.Polygon(geomPartArray, sr, has_z=True)
    
    print(polygon)
    
    return polygon

def convertToNativeMulti(items: List[Base], sr: arcpy.SpatialReference): 
    print("___Convert to Native MultiType___")
    first = items[0]
    if isinstance(first, Point):
        return multiPointToNative(items, sr)
    elif isinstance(first, Line) or isinstance(first, Polyline):
        return multiPolylineToNative(items, sr)
    elif isinstance(first, Base): 
        try:
            if first["boundary"] is not None and first["voids"] is not None:
                return multiPolygonToNative(items, sr)
        except: return None 
